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


def _to_vtkarray(pvobject):
    """Convert object to VTKArray, which we known how to work with."""
    if isinstance(pvobject, dsa.VTKCompositeDataArray):
        arrs = pvobject.GetArrays()
        if len(arrs) != 1:
            raise ValueError("Cannot deal with VTKCompositeDataArray of length %s."
                             % len(arrs))
        else:
            return arrs[0]
    elif isinstance(pvobject, dsa.VTKArray):
        return pvobject
    else:
        raise ValueError("Cannot deal with %s." % type(pvobject))


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
        results = _to_vtkarray(data.PointData[variable])

        if results.ndim == 2 and results.shape[1] == 3:
            # Vector: Calculate its magnitude
            results = np.sqrt(np.sum(results**2, axis=1))
    elif variable in ["X", "Y", "Z"]:
        # Coordinate
        idx = _COORDS[variable]
        results = _to_vtkarray(data.Points)[:, idx]
    elif (variable[-2:] in [" X", " Y", " Z"]
          and variable[:-2] in data.PointData.keys()):
        # Vector component
        idx = _COORDS[variable[-1]]
        results = _to_vtkarray(data.PointData[variable[:-2]])[:, idx]
    else:
        return None

    if skip_invalid and "vtkValidPointMask" in data.PointData.keys():
        valid = data.PointData["vtkValidPointMask"]
        results = results[valid == 1]

    return np.array(results) if (results is not None) else None


def _add_clip(pv_input, origin, normal):
    clip = pvs.Clip(Input=pv_input)
    clip.ClipType = 'Plane'
    clip.ClipType.Origin = origin
    clip.ClipType.Normal = normal
    return clip

def _add_bounding_box(pv_input, bounding_box):
    (minx, miny, minz, maxx, maxy, maxz) = bounding_box
    latest = pv_input

    if minx: latest = _add_clip(latest, [minx, 0, 0], [1, 0, 0])
    if miny: latest = _add_clip(latest, [0, miny, 0], [0, 1, 0])
    if minz: latest = _add_clip(latest, [0, 0, minz], [0, 0, 1])
    if maxx: latest = _add_clip(latest, [maxx, 0, 0], [-1, 0, 0])
    if maxy: latest = _add_clip(latest, [0, maxy, 0], [0, -1, 0])
    if maxz: latest = _add_clip(latest, [0, 0, maxz], [0, 0, -1])

    return latest


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
            only_inside (bool): True if the values outside of the defined data
                should be excluded. Otherwise, return NaN for these points.
                If True, length of the returned array could differ from npoints.

        Returns:
            numpy.ndarray: Variable values or None, if the variable
                does not exist.
        """
        pvs.SetActiveSource(self.reader)
        pol = pvs.PlotOverLine(Source="High Resolution Line Source")
        pol.Source.Resolution = npoints - 1
        pol.Source.Point1 = line[0]
        pol.Source.Point2 = line[1]

        array = _get_variable_array(pol, variable, only_inside)
        return array


    def boundary_line(self, variable, plane_point, plane_normal,
                      bounding_box=None):
        """ Return a list of the variable values along the intersection of the
        domain boundary with a plane.

        Args:
            variable (str): Name of the variable.
                See :py:meth:`DataSource.probe` for details.
            plane_point (tuple): three-float tuple representing the point on
                the plane.
            plane_normal (tuple): three-float tuple representing the normal of
                the plane.
            bounding_box (tuple): Tuple (minx, miny, minz, maxx, maxy, maxz),
                where the values are the limits of the bounding box. Each point
                can be replaced by None if the appropriate bound is missing.


        Returns:
            numpy.ndarray: Variable values or None, if the variable
                does not exist.
        """
        pvs.SetActiveSource(self.reader)

        poic = pvs.PlotOnIntersectionCurves(Input=self.reader)
        poic.SliceType = 'Plane'
        poic.SliceType.Origin = plane_point
        poic.SliceType.Normal = plane_normal

        latest = poic
        if bounding_box:
            latest = _add_bounding_box(latest, bounding_box)

        array = _get_variable_array(latest, variable, True)
        return array
