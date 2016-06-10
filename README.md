
pvtools
=======

pvtools offers a simplified and very limited Python interface to Paraview,
aimed at straighforward extracting numerical data from datasets openable
by Paraview.

pvtools runs under Python 2, and for everything to work, Paraview modules
must be accessible in the Python interpreter. This means that `PYTHONPATH` and
`LD_LIBRARY_PATH` should be extended by appropriate paths, see
[Python Scripting](http://www.paraview.org/Wiki/ParaView/Python_Scripting) at
Paraview wiki.
Or you can use it under `pvpython` and `pvbatch`.

Currently, only legacy VTK files are supported (but only because I have not
needed anything else).


Brief overview
--------------
Class `pvtools.DataSource` provides access to a data file. Data file can be
opened and closed using `__init__()` and `close()` methods, or through a context
manager:
```python
with pvtools.dsopen("myfile.vtk") as datasource:
    # ...
```
When open, you can ask for a value of a variable at a given point
(`DataSource.probe()`) or on a line (`DataSource.line()`).

Functions `pvtools.to_dict()` and `pvtools.to_json()` help when you deal with
a set of similar queries.

For more info and examples, see the docstrings and tests.


License
-------
pvtools package is licensed under MIT license.
