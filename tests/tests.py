#!/usr/bin/env python2

"""
Tests of pvtools package.
"""

import unittest
import doctest
import os
import sys

sys.path.insert(0, os.path.abspath('..'))

import pvtools as pvt


class TestVtk(unittest.TestCase):
    def setUp(self):
        self.file1 = os.path.join(pvt.PVTOOLS_DIR,
                                  "tests/data/Cell1Structured.vtk")
        self.file2 = os.path.join(pvt.PVTOOLS_DIR,
                                  "tests/data/Cell2Unstructured.vtk")

    def test_get_variables(self):
        with pvt.dsopen(self.file2) as ds:
            self.assertEqual(ds.get_variables('cell'), [])
            self.assertEqual(sorted(ds.get_variables('point')),
                             ["PPressure", "PVelocity"])

    def test_probe(self):
        with pvt.dsopen(self.file2) as ds:
            self.assertAlmostEqual(ds.probe("PPressure", (1, 0.5, 0.5)),
                                   20.0)
            self.assertAlmostEqual(ds.probe("PVelocity X", (1, 0.5, 0.5)),
                                   0.0)
            self.assertAlmostEqual(ds.probe("PVelocity Z", (1, 0.5, 0.5)),
                                   2.0)
            self.assertAlmostEqual(ds.probe("PVelocity", (1, 0.5, 0.5)),
                                   2.0)
            self.assertAlmostEqual(ds.probe("Non existent", (1, 0.5, 0.5)),
                                   None)
            self.assertAlmostEqual(ds.probe("PPressure", (0, 0, -1)),
                                   None)
            self.assertAlmostEqual(ds.probe("Y", (1, 0.5, 0.5)),
                                   0.5)

    def test_line(self):
        with pvt.dsopen(self.file2) as ds:
            arr = ds.line("PPressure", ((0.0, 0.5, 0.5), (2.0, 0.5, 0.5)), 3)
            self.assertEqual(len(arr), 3)
            self.assertAlmostEqual(arr[0], 10.0)
            self.assertAlmostEqual(arr[1], 20.0)
            self.assertAlmostEqual(arr[2], 30.0)

            arr = ds.line("X", ((0.0, 0.5, 0.5), (2.0, 0.5, 0.5)), 3)
            self.assertEqual(len(arr), 3)
            self.assertAlmostEqual(arr[0], 0.0)
            self.assertAlmostEqual(arr[1], 1.0)
            self.assertAlmostEqual(arr[2], 2.0)

    def test_boundary_line(self):
        with pvt.dsopen(self.file2) as ds:
            point = (0.5, 0.5, 0.5)
            normal = (0, 0, 1)
            bbox = (0.5, None, None, 1.5, 0.5, None)

            arr = ds.boundary_line("X", point, normal, bbox)
            for xa, xb in zip(arr, [0.5, 1.0, 1.5]):
                self.assertAlmostEqual(xa, xb)

            arr = ds.boundary_line("Y", point, normal, bbox)
            for ya, yb in zip(arr, [0.0, 0.0, 0.0]):
                self.assertAlmostEqual(ya, yb)

            arr = ds.boundary_line("Z", point, normal, bbox)
            for za, zb in zip(arr, [0.5, 0.5, 0.5]):
                self.assertAlmostEqual(za, zb)

    def test_to_dict_probe(self):
        res = pvt.to_dict(
            "probe",
            filename=[(self.file1, "C1"), (self.file2, "C2")],
            variable=[("PVelocity Z", "uz"), ("PPressure", "p")],
            point=(0.5, 0.5, 0.5))

        self.assertEqual(res[("C1", "uz")], 1.5)
        self.assertEqual(res[("C2", "uz")], 1.5)
        self.assertEqual(res[("C1", "p")], 15.0)
        self.assertEqual(res[("C2", "p")], 15.0)

    def test_to_dict_line(self):
        res = pvt.to_dict(
            "line",
            filename=self.file2,
            variable=[("PVelocity Z", "uz"), ("PPressure", "p")],
            line=[(((0.0, 0.5, 0.5), (2.0, 0.5, 0.5)), "L1"),
                  (((2.0, 0.5, 0.5), (0.0, 0.5, 0.5)), "L2")],
            npoints=3)

        self.assertEqual(res[("p", "L1")][0], res[("p", "L2")][2])
        self.assertEqual(res[("uz", "L1")][0], res[("uz", "L2")][2])

    def test_to_dict_boundary_line(self):
        # Two lines, at y = 0 and at y = 1. Velocity Z (changing only in
        # the Z direction) should be equal.
        res = pvt.to_dict(
            "boundary_line",
            filename=self.file2,
            variable=[("PVelocity Z", "uz"), ("X", "X")],
            plane_point=(0.5, 0.5, 0.5),
            plane_normal=(0, 0, 1),
            bounding_box=[((0.5, None, None, 1.5, 0.5, None), "y0"),
                          ((0.5, 0.5, None, 1.5, None, None), "y1")])

        # Need to sort - we do not know how it will come
        inds0 = res[("X", "y0")].argsort()
        y0 = res[("uz", "y0")][inds0]
        inds1 = res[("X", "y1")].argsort()
        y1 = res[("uz", "y1")][inds1]

        self.assertEqual(len(y0), len(y1))
        for i in range(len(y0)):
            self.assertAlmostEqual(y0[i], y1[i])



if __name__ == '__main__':
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(TestVtk))
    test_suite.addTest(doctest.DocTestSuite(pvt.interface))

    unittest.TextTestRunner(verbosity=2, buffer=True).run(test_suite)
