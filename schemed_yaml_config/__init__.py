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

"""
Validate YAML based configuration files against JSON Schema specifications.

Primary method is get_config() from module schemed_yaml_config.
It reads a YAML file andvalidates it against a given JSON schema.
Eventually it returns a dictionary with the content.

Example:
>>> from schemed_yaml_config import get_config()
>>> config = get_config('basic_config.yml', 'basic_schema.yml')
>>> print(config)
{'listen': {'host': '192.0.2.1', 'port': 1025}, 'tmpdir': '/tmp'}
>>>
"""

from __future__ import absolute_import

from .schemed_yaml_config import get_config, render_yaml, render_toml

from .__about__ import (
    __version__,
    __author__,
    __author_email__,
    __url__,
    __description__,
    __license__,
    __classifiers__
)
