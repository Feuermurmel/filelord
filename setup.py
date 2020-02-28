import setuptools


setuptools.setup(
    name='filemaster',
    version='0.1',
    packages=['filemaster'],
    entry_points=dict(
        console_scripts=['filemaster = filemaster:entry_point']),
    install_requires=[])
