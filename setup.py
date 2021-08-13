from setuptools import setup, find_packages
import sys, os

from manifold.release import version

setup(name='Manifold',
      version=version,
      description="An SMF service manifest creation tool.",
      long_description="""\
A command-line tool to simplify creating custom service manifests for
SMF on Solaris systems.
""",
      classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: SunOS/Solaris",
        "Programming Language :: Python",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
      ], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='SMF manifest XML',
      author='Chris Miles',
      author_email='miles.chris@gmail.com',
      url='http://code.google.com/p/manifold/',
      license='MIT',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=True,
      install_requires=[
          # -*- Extra requirements: -*-
          "Genshi",
      ],
      entry_points = {
          'console_scripts': [
              'manifold = manifold.manifold:main',
          ],
      },
)
