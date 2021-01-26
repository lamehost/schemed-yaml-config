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
Main file for the package
"""


import os
import re

from collections import OrderedDict

from jsonschema import Draft7Validator, validators
from jsonschema.exceptions import best_match

import yaml
import yamlordereddictloader
yaml.add_representer(OrderedDict, yaml.representer.Representer.represent_dict)

import toml


def get_defaults(schema, with_description=False):
    """
    Gets default values from the schema
    Args:
        schema: jsonschema
        with_description: Wether or not include description from the schema
    Returns:
        dict: dict with default values
    """

    def get_description_key():
        return '__syc_description_prefix__%s' % uuid.uuid4()

    def make_default(schema, with_description):
        if "type" in schema:
            if schema['type'] == 'object':
                result = OrderedDict()
                try:
                    items = schema['properties'].items()
                except KeyError:
                    items = []
                for key, val in items:
                    if "anyOf" in val:
                        val = next(iter(val['anyOf']))
                    elif "oneOf" in val:
                        val = next(iter(val['oneOf']))
                    if with_description:
                        try:
                            description_key = get_description_key()
                            result[description_key] = val['description']
                        except (TypeError, KeyError):
                            pass
                    try:
                        result[key] = get_defaults(val, with_description)
                    except SyntaxError:
            elif schema['type'] == 'array':
                result = []

                if "anyOf" in schema['items']:
                    val = next(iter(schema['items']['anyOf']))
                elif "oneOf" in schema['items']:
                    val = next(iter(schema['items']['oneOf']))
                else:
                    val = schema['items']

                try:
                    result = [get_defaults(val, with_description)]
                except SyntaxError:
                    pass

                if with_description and 'description' in schema['items']:
                    description_key = get_description_key()
                    result = ["%s %s" % (description_key, schema['items']['description'])] + result
            else:
                if "anyOf" in schema:
                    val = next(iter(schema['anyOf']))
                elif "oneOf" in schema:
                    val = next(iter(schema['oneOf']))
                else:
                    val = schema

                try:
                    result = val['default']
                except (TypeError, KeyError) as error:
                    raise SyntaxError(
"""Error while parsing schema file
  Message: "default" keyword missing
  Schema: %s""" % schema
                    ) from error
        else:
            raise SyntaxError(
"""Error while parsing schema file.
  Message: "type", "anyOf" or "oneOf" keywords missing
  Schema: %s""" % schema
            )

        return result

    # Always try to return user provided default and description first if default is available
    if 'default' in schema:
        default = schema['default']
    else:
        default = make_default(schema, with_description)

    if isinstance(default, OrderedDict):
        result = OrderedDict()
        if with_description and 'description' in schema:
            description_key = get_description_key()
            result[description_key] = schema['description']
        for key, value in default.items():
            result[key] = value
    elif isinstance(default, list):
        result = default
        if with_description and 'description' in schema:
            description_key = get_description_key()
            result = ["%s %s" % (description_key, schema['description'])] + result
    else:
        result = default

    return result


def updatedict(original, updates):
    """
    Updates the original dictionary with items in updates.
    If key already exists it overwrites the values else it creates it
    Args:
        original: original dictionary
        updates: items to be inserted in the dictionary
    Returns:
        dict: updated dictionary
    """
    for key, value in updates.items():
        if key not in original or type(value) != type(original[key]):
            original[key] = value
        elif isinstance(value, dict):
            original[key] = updatedict(original[key], value)
        else:
            original[key] = value

    return original


def keys_to_lower(item):
    """
    Normalize dict keys to lowercase.
    Args:
        dict: dict to be normalized
    Returns:
        Normalized dict
    """
    result = False
    if isinstance(item, list):
        result = [keys_to_lower(v) for v in item]
    elif isinstance(item, dict):
        result = dict((k.lower(), keys_to_lower(v)) for k, v in item.items())
    else:
        result = item

    return result


def get_config(
        configuration_filename='config.yml',
        schema_filename='config_schema.yml',
        create_default=True,
        lower_keys=True,
        language='yaml'
    ):
    """
    Gets default config and overwrite it with the content of configuration_filename.
    If the file does not exist, it creates it.
    Default config is generated by applying get_defaults() to local file named configuration.yaml .
    Content of configuration_filename by assuming the content is formatted in YAML.
    Args:
        configuration_filename: name of the YAML configuration file
        schema_filename: name of the JSONSchema file
        create_default: create default filename if missing
        lower_keys: transform keys to uppercase
        language: Markup language of the file (either 'YAML' or 'TOML')
    Returns:
        dict: configuration statements
    """

    _ = str(language).upper()
    if _ not in ['YAML', 'TOML']:
        raise SyntaxError('Unsupported markup language: %s' % _)
    language = _

    with open(schema_filename) as stream:
        try:
            configschema = yaml.load(stream, Loader=yamlordereddictloader.Loader)
        except (yaml.scanner.ScannerError) as error:
            raise SyntaxError('Error while parsing configuration file: %s' % error)

    if os.path.exists(configuration_filename):
        with open(configuration_filename, 'r') as stream:
            defaults = get_defaults(configschema)
            if language == "YAML":
                config = yaml.load(stream, Loader=yaml.FullLoader) or {}
            else:
                config = toml.load(stream)
            def import_defaults(config, defaults):
                if isinstance(config, dict):
                    for key, val in config.items():
                        try:
                            config[key] = import_defaults(val, defaults[key])
                        except KeyError:
                            pass
                        except TypeError:
                            pass
                    if isinstance(defaults, OrderedDict):
                        for key, val in defaults.items():
                            if key not in config:
                                config[key] =  val

                elif isinstance(config, list):
                    try:
                        config = [import_defaults(item, next(iter(defaults))) for item in config]
                    except StopIteration:
                        pass
                return config
            config = import_defaults(config, defaults)
            if lower_keys:
                config = keys_to_lower(config)
    else:
        # Read defaults and include descriptions
        config = get_defaults(configschema, with_description=True)
        if language == 'YAML':
            content = yaml.dump(config, default_flow_style=False, sort_keys=False, width=9999)
            # Transform key preceding description lines to "# "
            content = content.splitlines()
            for _ in range(len(content)):
                content[_] = re.sub(r"- __description_\S+: '(.*)'", r"  # \1", content[_])
                content[_] = re.sub(r"__description_\S+: '(.*)'", r"# \1", content[_])
                content[_] = re.sub(r"- __description_\S+: ", "  # ", content[_])
                content[_] = re.sub(r"__description_\S+: ", "# ", content[_])
            content = '\n'.join(content) + '\n'
        else:
            content = toml.dumps(config)
            # Transform key preceding description lines to "# "
            content = content.splitlines()
            for _ in range(len(content)):
                content[_] = re.sub(r"- __description_\S+ = '(.*)'", r"  # \1", content[_])
                content[_] = re.sub(r"__description_\S+ = '(.*)'", r"# \1", content[_])
                content[_] = re.sub(r"- __description_\S+ =  ", "  # ", content[_])
                content[_] = re.sub(r"__description_\S+ = ", "# ", content[_])
            content = '\n'.join(content) + '\n'

        # Dump config to file
        try:
            if create_default:
                with open(configuration_filename, 'w') as stream:
                    stream.write(content)
                    print('Created configuration file: %s' % configuration_filename)
        except IOError:
            raise IOError('Unable to create configuration file: %s' % configuration_filename)

        # Reload defaults without descriptions
        config = get_defaults(configschema, with_description=False)

    error = best_match(Draft7Validator(configschema).iter_errors(config))
    if error:
        path = "Unknown"
        if error.path is not None:
            path = '/' + '/'.join([str(_) for _ in error.relative_path])
        elif error.parent is not None and error.parent.path is not None:
            path = '/' + '/'.join([str(_) for _ in error.parent.relative_path])

        raise SyntaxError(
            'Error while parsing configuration file.\n  Message: %s\n  Path: %s' % (
                error.message, path
            )
        )

    return config
