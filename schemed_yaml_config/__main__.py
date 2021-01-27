#!/usr/bin/env python

import argparse

from schemed_yaml_config import get_config, render_yaml, render_toml


def main():
    parser = argparse.ArgumentParser(
      description='Process some integers.'
    )
    parser.add_argument(
      '-l', '--language',
      metavar='LANGUAGE',
      type=str,
      default='yaml',
      choices=['yaml', 'toml'],
      help='Name of the file containing the schema'
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
      help='Name of the file schema has to be applied to'
    )

    args = parser.parse_args()
    try:
        config = get_config(args.config, args.schema, language=args.language)
        if args.language == 'yaml':
            text = render_yaml(config)
        elif args.language == 'toml':
            text = render_yaml(config)
        else:
            text = ""
    except SyntaxError as error:
      text = error

    print(text)


if __name__ == '__main__':
    main()
