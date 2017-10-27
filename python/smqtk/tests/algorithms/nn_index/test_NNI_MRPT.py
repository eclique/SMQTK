from __future__ import absolute_import, division
from __future__ import print_function, unicode_literals

import random
import os.path as osp
import unittest

import numpy as np
from six.moves import range, zip

from smqtk.representation.descriptor_element.local_elements import \
    DescriptorMemoryElement
from smqtk.algorithms import get_nn_index_impls
from smqtk.algorithms.nn_index.mrpt import MRPTNearestNeighborsIndex
from smqtk.exceptions import ReadOnlyError
from smqtk.representation.descriptor_index.memory import MemoryDescriptorIndex


class TestMRPTIndex (unittest.TestCase):

    RAND_SEED = 42

    def _make_inst(self, **kwargs):
        """
        Make an instance of MRPTNearestNeighborsIndex
        """
        if 'random_seed' not in kwargs:
            kwargs.update(random_seed=self.RAND_SEED)
        return MRPTNearestNeighborsIndex(
            MemoryDescriptorIndex(), **kwargs)

    def test_configuration(self):
        index_filepath = osp.abspath(osp.expanduser('index_filepath'))
        para_filepath = osp.abspath(osp.expanduser('param_fp'))

        # Make configuration based on default
        c = MRPTNearestNeighborsIndex.get_default_config()
        c['index_filepath'] = index_filepath
        c['parameters_filepath'] = para_filepath
        c['descriptor_set']['type'] = 'MemoryDescriptorIndex'

        # Build based on configuration
        index = MRPTNearestNeighborsIndex.from_config(c)
        self.assertEqual(index._index_filepath, index_filepath)
        self.assertEqual(index._index_param_filepath, para_filepath)

        # Test that constructing a new instance from ``index``'s config yields
        # an index with the same configuration (idempotent).
        index2 = MRPTNearestNeighborsIndex.from_config(index.get_config())
        self.assertEqual(index.get_config(), index2.get_config())

    def test_many_descriptors(self):
        np.random.seed(0)

        n = 10 ** 4
        dim = 256
        depth = 5
        num_trees = 10

        d_index = [DescriptorMemoryElement('test', i) for i in range(n)]
        [d.set_vector(np.random.rand(dim)) for d in d_index]
        q = DescriptorMemoryElement('q', -1)
        q.set_vector(np.zeros((dim,)))

        di = MemoryDescriptorIndex()
        mrpt = MRPTNearestNeighborsIndex(
            di, num_trees=num_trees, depth=depth, random_seed=0)
        mrpt.build_index(d_index)

        nbrs, dists = mrpt.nn(q, 10)
        self.assertEqual(len(nbrs), len(dists))
        self.assertEqual(len(nbrs), 10)

    def test_small_leaves(self):
        np.random.seed(0)

        n = 10 ** 4
        dim = 256
        depth = 10
        # L ~ n/2**depth = 10^4 / 2^10 ~ 10
        k = 200
        # 3k/L = 60
        num_trees = 60

        d_index = [DescriptorMemoryElement('test', i) for i in range(n)]
        [d.set_vector(np.random.rand(dim)) for d in d_index]
        q = DescriptorMemoryElement('q', -1)
        q.set_vector(np.zeros((dim,)))

        di = MemoryDescriptorIndex()
        mrpt = MRPTNearestNeighborsIndex(
            di, num_trees=num_trees, depth=depth, random_seed=0)
        mrpt.build_index(d_index)

        nbrs, dists = mrpt.nn(q, k)
        self.assertEqual(len(nbrs), len(dists))
        self.assertEqual(len(nbrs), k)

    def test_pathological_example(self):
        n = 10 ** 4
        dim = 256
        depth = 10
        # L ~ n/2**depth = 10^4 / 2^10 ~ 10
        k = 200
        # 3k/L = 60
        num_trees = 60

        d_index = [DescriptorMemoryElement('test', i) for i in range(n)]
        # Put all descriptors on a line so that different trees get same
        # divisions
        [d.set_vector(np.full(dim, d.uuid(), dtype=np.float64))
         for d in d_index]
        q = DescriptorMemoryElement('q', -1)
        q.set_vector(np.zeros((dim,)))

        di = MemoryDescriptorIndex()
        mrpt = MRPTNearestNeighborsIndex(
            di, num_trees=num_trees, depth=depth, random_seed=0)
        mrpt.build_index(d_index)

        nbrs, dists = mrpt.nn(q, k)
        self.assertEqual(len(nbrs), len(dists))
        # We should get about 10 descriptors back instead of the requested
        # 200
        self.assertLess(len(nbrs), 20)

    def test_impl_findable(self):
        self.assertIn(MRPTNearestNeighborsIndex.__name__,
                      get_nn_index_impls())

    def test_known_descriptors_euclidean_unit(self):
        dim = 5

        ###
        # Unit vectors -- Equal distance
        #
        index = self._make_inst()
        test_descriptors = []
        for i in range(dim):
            v = np.zeros(dim, float)
            v[i] = 1.
            d = DescriptorMemoryElement('unit', i)
            d.set_vector(v)
            test_descriptors.append(d)
        index.build_index(test_descriptors)
        # query descriptor -- zero vector
        # -> all modeled descriptors should be equally distant (unit
        # corners)
        q = DescriptorMemoryElement('query', 0)
        q.set_vector(np.zeros(dim, float))
        r, dists = index.nn(q, n=dim)
        self.assertEqual(len(dists), dim)
        # All dists should be 1.0, r order doesn't matter
        for d in dists:
            self.assertEqual(d, 1.)

    def test_read_only(self):
        v = np.zeros(5, float)
        v[0] = 1.
        d = DescriptorMemoryElement('unit', 0)
        d.set_vector(v)
        test_descriptors = [d]

        index = self._make_inst(read_only=True)
        self.assertRaises(
            ReadOnlyError,
            index.build_index, test_descriptors
        )

    def test_known_descriptors_nearest(self):
        dim = 5

        ###
        # Unit vectors -- Equal distance
        #
        index = self._make_inst()
        test_descriptors = []
        vectors = np.eye(dim, dtype=np.float32)
        for i in range(dim):
            d = DescriptorMemoryElement('unit', i)
            d.set_vector(vectors[i])
            test_descriptors.append(d)
        index.build_index(test_descriptors)
        # query descriptor -- first point
        q = DescriptorMemoryElement('query', 0)
        q.set_vector(vectors[0])
        r, dists = index.nn(q)
        self.assertEqual(len(dists), 1)
        # Distance should be zero
        self.assertEqual(dists[0], 0.)
        self.assertItemsEqual(r[0].vector(), vectors[0])

    def test_known_descriptors_euclidean_ordered(self):
        index = self._make_inst()

        # make vectors to return in a known euclidean distance order
        i = 100
        test_descriptors = []
        for j in range(i):
            d = DescriptorMemoryElement('ordered', j)
            d.set_vector(np.array([j, j*2], float))
            test_descriptors.append(d)
        random.shuffle(test_descriptors)
        index.build_index(test_descriptors)

        # Since descriptors were build in increasing distance from (0,0),
        # returned descriptors for a query of [0,0] should be in index
        # order.
        q = DescriptorMemoryElement('query', 99)
        q.set_vector(np.array([0, 0], float))
        r, dists = index.nn(q, n=i)
        # Because the data is one-dimensional, all of the cells will have
        # the same points (any division will just correspond to a point on
        # the line), and a cell can't have more than half of the points
        self.assertEqual(len(dists), i//2)
        for j, d, dist in zip(range(i), r, dists):
            self.assertEqual(d.uuid(), j)
            np.testing.assert_equal(d.vector(), [j, j*2])
