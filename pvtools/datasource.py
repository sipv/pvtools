#!/usr/bin/env python2

"""
Implements DataSource class for accessing datafiles through Paraview.
"""

import os
import sys
from contextlib import contextmanager
import cStringIO

import numpy as np
import paraview.simple as pvs
import vtk.numpy_interface.dataset_adapter as dsa


_COORDS = {"X": 0, "Y": 1, "Z": 2}


@contextmanager
def _nostdout():
    save_stdout = sys.stdout
    sys.stdout = cStringIO.StringIO()
    yield
    sys.stdout = save_stdout


def _get_variable_array(pvobject, variable, skip_invalid=True):
    """Get numerical array for given variable.

    Returns:
         numpy.ndarray: Array of the variable values. If it does not exist,
                        returns None.
    """

    # Paraview prints unwanted messages, such as "use append poly data filter".
    # We might possibly lose something of interest here.
    with _nostdout():
        rawdata = pvs.servermanager.Fetch(pvobject)

    data = dsa.WrapDataObject(rawdata)

    if variable in data.PointData.keys():
        # Scalar or vector
        results = data.PointData[variable]
        if results.ndim == 2 and results.shape[1] == 3:
            # Vector: Calculate its magnitude
            results = np.sqrt(np.sum(results**2, axis=1))
    elif variable in ["X", "Y", "Z"]:
        # Coordinate
        idx = _COORDS[variable]
        results = data.Points[:, idx]
    elif (variable[-2:] in [" X", " Y", " Z"]
          and variable[:-2] in data.PointData.keys()):
        # Vector component
        idx = _COORDS[variable[-1]]
        results = data.PointData[variable[:-2]][:, idx]
    else:
        return None

    if skip_invalid:
        valid = data.PointData["vtkValidPointMask"]
        results = results[valid == 1]

    return np.array(results) if (results is not None) else None



class DataSource:
    """Class for accessing datafiles through Paraview"""

    reader = None
    fullpath = None

    def __init__(self, filename):
        """Open the data source.

        Args:
            filename (str): Name of the file to be opened.
        """

        if not os.path.isfile(filename):
            raise ValueError("File %s does not exist" % filename)

        extension = os.path.splitext(filename)[1].lower()
        if extension == ".vtk":
            self.reader = pvs.LegacyVTKReader(FileNames=[filename])
        else:
            raise ValueError("Unsupported format: %s" % extension)

        self.fullpath = os.path.abspath(filename)

    def __str__(self):
        if self.reader:
            status = "open, \"%s\"" % self.fullpath
        else:
            status = "closed"

        return "DataSource (%s)" % status

    def close(self):
        """Close the data source."""

        pvs.Delete(self.reader)
        self.reader = None
        self.fullpath = None

    # Information queries

    def get_variables(self, loc):
        """Return list of variables defined in the data source.

        Args:
             loc (string): Either 'point' or 'cell'
        Returns:
              List[str]: List of the present variables.
        """
        if loc == 'point':
            return self.reader.PointData.keys()
        elif loc == 'cell':
            return self.reader.CellData.keys()



    # Data access methods

    def probe(self, variable, point):
        """Return the value of a variable at a given point.

        Args:
            variable (str): Name of the variable.
                Probing a vector return its magnitude.
                Components of the vector are available by adding a suffix
                ' X', ' Y' or ' Z' to the vector name.
                Physical coordinates are available under the name 'X', 'Y' or 'Z'.
            point (tuple): x, y and z coordinates.

        Returns:
            float: Queried value or None.
                None is returned if the variable does not exist or the point is not
                defined at the given point.
        """


        pvs.SetActiveSource(self.reader)
        prob_loc = pvs.ProbeLocation(ProbeType="Fixed Radius Point Source")
        prob_loc.ProbeType.Center = point
        array = _get_variable_array(prob_loc, variable)

        pvs.Delete(prob_loc)

        if array is None or len(array) == 0:
            return None
        elif len(array) != 1:
            raise Exception("Unexpected length of the array.")
        else:
            return array[0]

    def line(self, variable, line, npoints=100, only_inside=True):
        """Return a list of the variable values along the line.

        Args:
            variable (str): Name of the variable.
                See :py:meth:`DataSource.probe` for details.
            line (tuple): Tuple (point1, point2), where point1 and point2 are
                three-float tuples representing the coordinates of the start
                and end point of the line.
            npoints (int): Number of points along the line.

        Returns:
            numpy.ndarray: Variable values or None, if the variable
                does not exist.

            only_inside (bool): True if the values outside of the defined data
                should be excluded. Otherwise, return NaN for these points.
                If True, length of the returned array could differ from npoints.
        """
        pvs.SetActiveSource(self.reader)
        pol = pvs.PlotOverLine(Source="High Resolution Line Source")
        pol.Source.Resolution = npoints - 1
        pol.Source.Point1 = line[0]
        pol.Source.Point2 = line[1]

        array = _get_variable_array(pol, variable, only_inside)
        return array
