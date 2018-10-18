from setuptools import setup, find_packages

setup(
    name='PyRitz',
    version='0.1',
    author='Runar Borge',
    author_email='runar.borge@uninett.no',
    packages=find_packages(),
    python_requires='<=3.5',
    # scripts=['bin/ritz'],
    # package_data={'':['*.yml', '*.rst']},
    # data_files=[('/etc/',['ritz.conf'])],
    url=[''],
    license='LISENSE.txt',
    description="Python interface to Zino",
    long_description=open('README.md').read(),
    include_package_data=True,
    install_requires=[],
)
