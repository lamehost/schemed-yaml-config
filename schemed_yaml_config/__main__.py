#!/usr/bin/env python

"""CLI entrypoint module for the package"""

# MIT License

# Copyright (c) 2021, Marco Marzetti <marco@lamehost.it>

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


import argparse
import sys

from schemed_yaml_config import get_config


def main():
    """CLI entrypoint function for the package"""

    parser = argparse.ArgumentParser(
      description='Process some integers.'
    )
    parser.add_argument(
      '-l', '--language',
      metavar='LANGUAGE',
      type=str,
      default='yaml',
      choices=['yaml', 'toml'],
      help="Either 'yaml' or 'toml'"
    )
    parser.add_argument(
      '-n', '--no-validate',
      action='store_true',
      default=False,
      help='Disable validation'
    )
    parser.add_argument(
      'schema',
      metavar='SCHEMA',
      type=str,
      help='Name of the file containing the schema'
    )
    parser.add_argument(
      'config',
      metavar='CONFIG',
      type=str,
      nargs='?',
      default=None,
      help='Name of the file schema has to be applied on'
    )

    args = parser.parse_args()
    config = get_config(args.config, args.schema, language=args.language)

    if not args.no_validate:
        try:
            config.validate()
        except RuntimeError as error:
            print(error)
            sys.exit(1)

    if args.language == 'yaml':
        if args.config:
            text = config.to_yaml()
        else:
            text = config.default_config_to_yaml()
    elif args.language == 'toml':
        if args.config:
            text = config.to_toml()
        else:
            text = config.default_config_to_toml()
    else:
        text = ""

    print(text)


if __name__ == '__main__':
    main()
