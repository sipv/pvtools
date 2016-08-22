#!/usr/bin/env python2

"""
High-level access function of pvtools package.
"""

import os
from contextlib import contextmanager
import inspect
import itertools
import json

import numpy as np
import paraview.simple as pvs

from .datasource import DataSource

PVTOOLS_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                           os.pardir)

@contextmanager
def dsopen(filename):
    """Return the DataSource object for the given filename.

    Args:
        filename (str): Name of the file to be opened.
    """

    ds = DataSource(filename)
    yield ds
    ds.close()

def _standardize_args(argdict):
    stdargs = {}
    for k, v in argdict.iteritems():
        if isinstance(v, list):
            # Furthermore, it should be a list of tuples, but we are
            # not checking that.
            stdargs[k] = v
        else:
            stdargs[k] = [(v, v)]

    return stdargs

def to_dict(function, filename, **kwargs):
    """Return a dict with the data obtained by a method of DataSource object.

    This function serves as a wrapper around the methods of the DataSource class,
    allowing querying all elements of the product of the parameter sets.

    Args:
        function (str): One of: 'probe', 'line'
        filename (List[tuple]): Files to be processes, in the format as the rest
            of the arguments (see below). The filename is then passed to
            :py:meth:`pvtools.datasource.DataSource.__init__`.
        **kwargs: Arguments as taken by the desired method.
            Each argument is to be given as a list of tuples. Each element of the
            list is a 2-tuple, where the first element is the argument passed
            to the method, and the second is the key under which the respective
            result appears in the returned dict.
            When there is only one element in the argument list, it can be given
            as is, i.e. not in the list and just the argument, not a tuple
            (as the key won't be included in the returned dict anyway, see below).

    Returns:
        dict: Results in a dict. The keys are n-tuples, with elements as given
              by the input arguments.
              When the list of arguments contains only one element, the
              relevant key is not included in the tuple.
              Keys are in the order of the arguments in the respective methods,
              with the filename preceeding them all.

    Examples:
        >>> print(to_dict(
        ...       "probe",
        ...       filename=os.path.join(PVTOOLS_DIR,"tests/data/Cell1Structured.vtk"),
        ...       variable=[("PVelocity Z", "uz"), ("PPressure", "p")],
        ...       point=[((0.0, 0.5, 0.5), "P1"), ((1.0, 0.5, 0.5), "P2")]))
        {('uz', 'P1'): 1.0, ('p', 'P2'): 20.0, ('p', 'P1'): 10.0, ('uz', 'P2'): 2.0}
    """
    if function not in ["probe", "line", "boundary_line"]:
        raise ValueError("Unsupported function %s" % function)

    kwargs.update({"filename": filename})
    kwargs = _standardize_args(kwargs)

    method = getattr(DataSource, function)
    arg_spec = inspect.getargspec(method)

    if arg_spec.defaults is None:
        oblig_args = arg_spec.args[1:]
    else :
        oblig_args = arg_spec.args[1: -len(arg_spec.defaults)]

    for arg in oblig_args:
        if arg not in kwargs:
            raise ValueError("Missing argument: %s." % arg)

    arg_lists = [kwargs[arg_name]
                 for arg_name in (["filename"] + arg_spec.args[1:])
                 if arg_name in kwargs]
    include_in_key = [len(arg_list) > 1 for arg_list in arg_lists]

    res = {}
    for filename, filename_key in kwargs["filename"]:
        with dsopen(filename) as ds:
            for arg_tuple_combination in itertools.product(*arg_lists[1:]):
                combination_args = [t[0] for t in arg_tuple_combination]
                val = method(ds, *combination_args)

                combination_keys = tuple(itertools.compress(
                    [filename_key] + [t[1] for t in arg_tuple_combination],
                    include_in_key))

                res[combination_keys] = val

    return res

def _insert_to_hdict(hdict, key, val):
    if len(key) == 1:
        hdict[key[0]] = val
    else:
        if not key[0] in hdict:
            hdict[key[0]] = {}
        _insert_to_hdict(hdict[key[0]], key[1:], val)

def _hierarchize(fdict):
    """Convert flat dict to a hierarchic one.

    Examples:
        >>> _hierarchize({(1, 1): 'A', (1, 2): 'B', (2, 1): 'C', (2, 2): 'D'})
        {1: {1: 'A', 2: 'B'}, 2: {1: 'C', 2: 'D'}}
    """
    hdict = {}
    for key, val in fdict.iteritems():
        _insert_to_hdict(hdict, key, val)
    return hdict

def to_json(json_file, function, filename, **kwargs):
    """Save the data obtained by a method of DataSource object to a json file.

    This function works just as :func:`to_dict`, except
    the result is directly saved to json file, and the numpy arrays (if present)
    are converted to plain lists. Furthermore, the dict is stored not as a flat
    one (indexed by tuples), but as a hierarchical one.

    Args:
        json_file (str): name of the json file to be created.
        function (str): See :func:`to_dict`.
        filename (List[tuple]): See :func:`to_dict`.
        **kwargs: See :func:`to_dict`.
    """

    res = to_dict(function, filename, **kwargs)

    for k, v in res.iteritems():
        if isinstance(v, np.ndarray):
            res[k] = v.tolist()

    res = _hierarchize(res)

    with open(json_file, 'w') as f:
        json.dump(res, f, indent=4)
