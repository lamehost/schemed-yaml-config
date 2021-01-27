# MIT License

# Copyright (c) 2019, Marco Marzetti <marco@lamehost.it>

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import codecs

from os.path import abspath, dirname, join
from setuptools import setup


NAME = 'schemed-yaml-config'
MODULE = NAME.replace('-', '_')
HERE = abspath(dirname(__file__))

ABOUT = dict()
with open(join(MODULE, '__about__.py')) as _:
    exec(_.read(), ABOUT)

HERE = abspath(dirname(__file__))
with codecs.open(join(HERE, 'README.md'), encoding='utf-8') as _:
    README = _.read()

with open('requirements.txt') as file:
    REQS = [line.strip() for line in file if line and not line.startswith("#")]

setup(
    name=NAME,
    author=ABOUT['__author__'],
    author_email=ABOUT['__author_email__'],
    url=ABOUT['__url__'],
    version=ABOUT['__version__'],
    packages=[MODULE],
    package_data={MODULE: [
        '*.yml'
    ]},
    install_requires=REQS,
    include_package_data=True,
    long_description=README,
    entry_points={
        'console_scripts': [
            '%s = %s.__main__:main' % (NAME, 'schemed_yaml_config'),
        ],
    },
    long_description_content_type='text/markdown',
    zip_safe=False
)
