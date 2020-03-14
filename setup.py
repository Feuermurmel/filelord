import setuptools

name = 'filemaster'
dependencies = []
console_scripts = ['fm = filemaster.cli:entry_point']

setuptools.setup(
    name=name,
    entry_points=dict(console_scripts=console_scripts),
    install_requires=dependencies,
    setup_requires=['setuptools>=42', 'wheel', 'setuptools_scm[toml]>=3.4'],
    use_scm_version=True,
    packages=setuptools.find_packages(exclude=['tests']))

