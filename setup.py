from setuptools import setup, find_packages
setup(
    use_scm_version={
        'write_to': 'src/ritz/version.py',
    },
    setup_requires=['setuptools_scm'],
    install_requires=[],
    name='PyRitz',
    author='Runar Borge',
    author_email='runar.borge@uninett.no',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    python_requires='>=3.7',
    url=[''],
    license='LISENSE.txt',
    description="Python interface to Zino",
    long_description=open('README.md').read(),
    include_package_data=True,
    scripts=['bin/curitz'],
    py_modules=['culistbox'],
    extras_require = {
        'DNS':  ["dnspython"]
    },
)
