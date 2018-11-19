from setuptools import setup, find_packages
from ritz import __version__
setup(
    name='PyRitz',
    version=__version__,
    author='Runar Borge',
    author_email='runar.borge@uninett.no',
    packages=find_packages(),
    python_requires='<=3.5',
    url=[''],
    license='LISENSE.txt',
    description="Python interface to Zino",
    long_description=open('README.md').read(),
    include_package_data=True,
    install_requires=[],
    CLASSIFIERS=[
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    scripts=['bin/curitz'],
    py_modules=['culistbox']
)
