
from zeam.setup.base import new_setup

version = '1.0'

setup(name='zeam.setup',
      version=version,
      description="Installation tool",
      long_description="",
      classifiers=[],
      keywords="installation tool eggs",
      author="Sylvain Viollon",
      author_email="thefunny@gmail.com",
      url="",
      license="BSD",
      package_dir={'': 'src'},
      packages=find_packages('src'),
      install_requires=[
        ],
      entry_points = """
      [console_scripts]
      setup = zeam.setup.base.setup:setup
      """,
      )
