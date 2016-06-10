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




if __name__ == '__main__':
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(TestVtk))
    test_suite.addTest(doctest.DocTestSuite(pvt.interface))

    unittest.TextTestRunner(verbosity=2, buffer=True).run(test_suite)
