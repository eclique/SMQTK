from __future__ import division, print_function
import inspect
import os
import pickle
import unittest

import PIL.Image
import mock
import nose.tools
import numpy

from smqtk.algorithms.descriptor_generator import get_descriptor_generator_impls
from smqtk.algorithms.descriptor_generator.pytorch_descriptor import \
     PytorchDescriptorGenerator
from smqtk.representation.data_element import from_uri
from smqtk.representation.data_element.url_element import DataUrlElement
from smqtk.tests import TEST_DATA_DIR

from torchvision import models, transforms


if PytorchDescriptorGenerator.is_usable():

    class TestPytorchDesctriptorGenerator (unittest.TestCase):

        # lenna_image_fp = os.path.join(TEST_DATA_DIR, 'Lenna.png')
        # lenna_alexnet_fc7_descr_fp = \
        #     os.path.join(TEST_DATA_DIR, 'Lenna.alexnet_fc7_output.npy')
        #
        # # Dummy Caffe configuration files + weights
        # # - weights is actually an empty file (0 bytes), which caffe treats
        # #   as random/zero values (not sure exactly what's happening, but
        # #   always results in a zero-vector).
        # dummy_net_topo_fp = \
        #     os.path.join(TEST_DATA_DIR, 'caffe.dummpy_network.prototxt')
        # dummy_caffe_model_fp = \
        #     os.path.join(TEST_DATA_DIR, 'caffe.empty_model.caffemodel')
        # dummy_img_mean_fp = \
        #     os.path.join(TEST_DATA_DIR, 'caffe.dummy_mean.npy')
        #
        # www_uri_alexnet_prototxt = \
        #     'https://data.kitware.com/api/v1/file/57e2f3fd8d777f10f26e532c/download'
        # www_uri_alexnet_caffemodel = \
        #     'https://data.kitware.com/api/v1/file/57dae22f8d777f10f26a2a86/download'
        # www_uri_image_mean_proto = \
        #     'https://data.kitware.com/api/v1/file/57dae0a88d777f10f26a2a82/download'

        def setUp(self):
            transform = transforms.Compose([transforms.ToTensor()])
            self.expected_params = {
                'model_cls': models.resnet50(pretrained=True),
                # 'model_cls': None,
                'model_uri': None,
                'transform': transform,
                'resize_val': 224,
                'batch_size': 8,
                'use_gpu': False,
                'gpu_device_id': None,
            }

        def test_impl_findable(self):
            self.assertIn(PytorchDescriptorGenerator.__name__,
                                 get_descriptor_generator_impls())

        @mock.patch('smqtk.algorithms.descriptor_generator.pytorch_descriptor'
                    '.PytorchDescriptorGenerator._setup_network')
        def test_get_config(self, m_cdg_setupNetwork):
            # Mocking set_network so we don't have to worry about actually
            # initializing any pytorch things for this test.

            # make sure that we're considering all constructor parameter options
            expected_param_keys = \
                set(inspect.getfullargspec(PytorchDescriptorGenerator.__init__)
                           .args[1:])
            self.assertSetEqual(set(self.expected_params.keys()),
                                        expected_param_keys)
            g = PytorchDescriptorGenerator(**self.expected_params)
            self.assertEqual(g.get_config(), self.expected_params)


        @mock.patch('smqtk.algorithms.descriptor_generator.pytorch_descriptor'
                    '.PytorchDescriptorGenerator._setup_network')
        def test_pickle_save_restore(self, m_cdg_setupNetwork):

            g = PytorchDescriptorGenerator(**self.expected_params)
            # Initialization sets up the network on construction.
            self.assertEqual(m_cdg_setupNetwork.call_count, 1)

            g_pickled = pickle.dumps(g, -1)
            g2 = pickle.loads(g_pickled)
            # Network should be setup for second class class just like in
            # initial construction.
            self.assertEqual(m_cdg_setupNetwork.call_count, 2)

            self.assertIsInstance(g2, PytorchDescriptorGenerator)
            # print(g.__dict__)
            # print('--------------------------')
            # print(g2.__dict__)

            # self.assertEqual(g.get_config(), g2.get_config())

        @mock.patch('smqtk.algorithms.descriptor_generator.pytorch_descriptor'
                    '.PytorchDescriptorGenerator._setup_network')
        def test_invalid_datatype(self, m_cdg_setupNetwork):
            self.assertRaises(
                ValueError,
                PytorchDescriptorGenerator,
                None, None, None
            )

        # def test_process_load_img(self):
        #     # using image shape, meaning no transformation should occur
        #     test_data_layer = 'data'
        #     test_transformer = \
        #         caffe.io.Transformer({test_data_layer: (1, 3, 512, 512)})
        #
        #     lenna_elem = from_uri(self.lenna_image_fp)
        #     a_expected = numpy.asarray(PIL.Image.open(self.lenna_image_fp),
        #                                numpy.float32)
        #     a = _process_load_img_array((
        #         lenna_elem, test_transformer, test_data_layer, None, None
        #     ))
        #     numpy.testing.assert_allclose(a, a_expected)
        #
        # @mock.patch('smqtk.algorithms.descriptor_generator.caffe_descriptor'
        #             '.CaffeDescriptorGenerator._setup_network')
        # def test_no_internal_compute_descriptor(self, m_cdg_setupNetwork):
        #     # This implementation's descriptor computation logic sits in async
        #     # method override due to caffe's natural multi-element computation
        #     # interface. Thus, ``_compute_descriptor`` should not be
        #     # implemented.
        #
        #     # dummy network setup because _setup_network is mocked out
        #     g = CaffeDescriptorGenerator(0, 0, 0)
        #     nose.tools.assert_raises(
        #         NotImplementedError,
        #         g._compute_descriptor, None
        #     )
        #
        # def test_compute_descriptor_dummy_model(self):
        #     # Caffe dummy network interaction test Lenna image)
        #
        #     # Construct network with an empty model just to see that our
        #     # interaction with the Caffe API is successful. We expect a
        #     # zero-valued descriptor vector.
        #     g = CaffeDescriptorGenerator(self.dummy_net_topo_fp,
        #                                  self.dummy_caffe_model_fp,
        #                                  self.dummy_img_mean_fp,
        #                                  return_layer='fc', use_gpu=False)
        #     d = g.compute_descriptor(from_uri(self.lenna_image_fp))
        #     nose.tools.assert_almost_equal(d.vector().sum(), 0., 12)
        #
        # @unittest.skipUnless(DataUrlElement.is_usable(),
        #                      "URL resolution not functional")
        # def test_compute_descriptor_from_url_lenna_description(self):
        #     # Caffe AlexNet interaction test (Lenna image)
        #     # This is a long test since it has to download data for remote URIs
        #     d = CaffeDescriptorGenerator(
        #         self.www_uri_alexnet_prototxt,
        #         self.www_uri_alexnet_caffemodel,
        #         self.www_uri_image_mean_proto,
        #         return_layer='fc7',
        #         use_gpu=False,
        #     )
        #     lenna_elem = from_uri(self.lenna_image_fp)
        #     expected_descr = numpy.load(self.lenna_alexnet_fc7_descr_fp)
        #     descr = d.compute_descriptor(lenna_elem).vector()
        #     numpy.testing.assert_allclose(descr, expected_descr, atol=1e-5)
        #
        # def test_compute_descriptor_async_no_data(self):
        #     # Should get a ValueError when given no descriptors to async method
        #     g = CaffeDescriptorGenerator(self.dummy_net_topo_fp,
        #                                  self.dummy_caffe_model_fp,
        #                                  self.dummy_img_mean_fp,
        #                                  return_layer='fc', use_gpu=False)
        #     nose.tools.assert_raises(
        #         ValueError,
        #         g.compute_descriptor_async, []
        #     )
