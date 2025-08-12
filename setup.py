from setuptools import setup, find_packages
from fylang.version import __version__

setup(
  name="fylang",
  version=__version__,
  packages=find_packages(),
  include_package_data=True,
  entry_points={
    "console_scripts": [
      "fy = fylang.fy:main"
    ]
  },
)
