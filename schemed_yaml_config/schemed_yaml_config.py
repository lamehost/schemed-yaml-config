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
import uuid
from collections import OrderedDict
from copy import deepcopy

import toml
from jsonschema import Draft7Validator
from jsonschema.exceptions import best_match

import yaml
import yamlordereddictloader
yaml.add_representer(OrderedDict, yaml.representer.Representer.represent_dict)


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
            # Parse objects
            if schema['type'] == 'object':
                result = OrderedDict()
                # Find all properties
                try:
                    properties = list(schema['properties'].items())
                except KeyError:
                    properties = []

                # Find all patternProperties
                try:
                    for pattern, value in schema['patternProperties'].items():
                        # Compile regex so that we can use it later
                        pattern = re.compile(pattern)
                        properties.append([pattern, value])
                except KeyError:
                    pass

                for _property, value in properties:
                    # There can be multiple subschemas defined under anyOf and oneOf
                    # We only take the first one in the list and we import key into schema
                    # (only missing keys are imported).
                    if "anyOf" in value:
                        for subkey, subvalue in next(iter(value['anyOf'])).items():
                            if subkey not in value:
                                value[subkey] = subvalue
                    elif "oneOf" in value:
                        for subkey, subvalue in next(iter(value['oneOf'])).items():
                            if subkey not in value:
                                value[subkey] = subvalue

                    # Try to import description
                    if with_description:
                        try:
                            description_key = get_description_key()
                            result[description_key] = value['description']
                        except (TypeError, KeyError):
                            pass

                    # Run get_defaults over value
                    try:
                        result[_property] = get_defaults(value, with_description)
                    except SyntaxError as error:
                        # No default value was found, thus we skip the key
                        pass
            # Parse arrays
            elif schema['type'] == 'array':
                result = []
                # Every array has a items key that define the subschema
                # There can be multiple subschemas defined under anyOf and oneOf
                # We only take the first one in the list and we use it as subschema
                if "anyOf" in schema['items']:
                    subschema = next(iter(schema['items']['anyOf']))
                elif "oneOf" in schema['items']:
                    subschema = next(iter(schema['items']['oneOf']))
                else:
                    subschema = schema['items']

                try:
                    result = [get_defaults(subschema, with_description)]
                except SyntaxError as error:
                    # No default value was found
                    pass

                # Try to put description at the top of the list
                if with_description and 'description' in subschema['items']:
                    description_key = get_description_key()
                    result = [
                        "%s %s" % (description_key, subschema['items']['description'])
                    ] + result
            # Fallback for all fo the other objects
            else:
                # There can be a schema defined under every item
                # And there can be multiple subschemas defined under anyOf and oneOf
                # We only take the first one in the list and we use it as subschema
                if "anyOf" in schema:
                    subschema = next(iter(schema['anyOf']))
                elif "oneOf" in schema:
                    subschema = next(iter(schema['oneOf']))
                else:
                    subschema = schema

                # Try to return default value
                try:
                    result = subschema['default']
                except (TypeError, KeyError) as error:
                    raise SyntaxError(
"""Error while parsing schema file
  Message: "default" keyword missing
  Schema: %s""" % render_yaml(schema)
                    ) from error
        else:
            raise SyntaxError(
"""Error while parsing schema file.
  Message: "type", "anyOf" or "oneOf" keywords missing
  Schema: %s""" % render_yaml(schema)
            )

        return result

    # If user defined default is not there, then create one
    _schema = deepcopy(schema)
    if 'default' in _schema:
        default = _schema['default']
    else:
        default = make_default(_schema, with_description)

    # Import default and descriptions into result
    if isinstance(default, OrderedDict):
        result = OrderedDict()
        if with_description and 'description' in _schema:
            description_key = get_description_key()
            result[description_key] = _schema['description']
        for key, value in default.items():
            result[key] = value
    elif isinstance(default, list):
        result = default
        if with_description and 'description' in _schema:
            description_key = get_description_key()
            result = ["%s %s" % (description_key, _schema['description'])] + result
    else:
        result = default

    return result


def render_yaml(config):
    """ Returns rendered config object in YAML format Args:
        config: config object
    Returns:
        str: rendered text
    """

    text = yaml.dump(config, default_flow_style=False, sort_keys=False, width=9999)

    # Handle descriptions
    lines = list()
    for line in text.splitlines():
        new_line = re.sub(
            r"- __syc_description_prefix__\S+: '(.*)'", r"  # \1", line
        )
        if new_line != line:
            lines.append(new_line)
            continue

        new_line = re.sub(
            r"- __syc_description_prefix__\S+: (.*)", r"  # \1", line
        )
        if new_line != line:
            lines.append(new_line)
            continue

        new_line = re.sub(
            r"- __syc_description_prefix__\S+ (.+)", r"# \1", line
        )
        if new_line != line:
            lines.append(new_line)
            continue

        new_line = re.sub(
            r"__syc_description_prefix__\S+: '(.*)'", r"# \1", line
        )
        if new_line != line:
            lines.append(new_line)
            continue

        new_line = re.sub(
            r"__syc_description_prefix__\S+: (.*)", r"# \1", line
        )
        if new_line != line:
            lines.append(new_line)
            continue

        lines.append(line)
    text = '\n'.join(lines) + '\n'
    return text


def render_toml(config):
    """ Returns rendered config object in TOML format Args:
        config: config object
    Returns:
        str: rendered text
    """

    text = yaml.dump(config, default_flow_style=False, sort_keys=False, width=9999)

    # Handle descriptions
    lines = list()
    for line in text.splitlines():
        new_line = re.sub(
            r"- __syc_description_prefix__\S+ = '(.*)'", r"  # \1", line
        )
        if new_line != line:
            lines.append(new_line)
            continue

        new_line = re.sub(
            r"- __syc_description_prefix__\S+ = (.*)", r"  # \1", line
        )
        if new_line != line:
            lines.append(new_line)
            continue

        new_line = re.sub(
            r"- __syc_description_prefix__\S+ (.+)", r"# \1", line
        )
        if new_line != line:
            lines.append(new_line)
            continue

        new_line = re.sub(
            r"__syc_description_prefix__\S+ = '(.*)'", r"# \1", line
        )
        if new_line != line:
            lines.append(new_line)
            continue

        new_line = re.sub(
            r"__syc_description_prefix__\S+ = (.*)", r"# \1", line
        )
        if new_line != line:
            lines.append(new_line)
            continue

        lines.append(line)
    text = '\n'.join(lines) + '\n'
    return text


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
            raise SyntaxError('Error while parsing configuration file: %s' % error) from error
    validator = Draft7Validator(configschema)

    if os.path.exists(configuration_filename):
        with open(configuration_filename, 'r') as stream:
            if language == "YAML":
                config = yaml.load(stream, Loader=yaml.FullLoader) or {}
            else:
                config = toml.load(stream)

            def import_defaults(config, defaults):
                if isinstance(config, dict):
                    # Recursively import defaults into existing keys
                    for key, value in config.items():
                        try:
                            config[key] = import_defaults(value, defaults[key])
                        except (KeyError, TypeError):
                            pass

                    if isinstance(defaults, OrderedDict):
                        # Recursively import defaults into keys that match with patterns
                        for pattern, default in defaults.items():
                            if not isinstance(pattern, re.Pattern):
                                continue
                            for key, value in config.items():
                                if pattern.match(key):
                                    config[key] = import_defaults(value, default)

                        # Import missing keys
                        for key, default in defaults.items():
                            # Skip existing keys
                            if key in config:
                                continue
                            # Skip patterns
                            if isinstance(key, re.Pattern):
                                continue

                            # Remove patternPriorities keys from default
                            def remove_patterns(tree):
                                if not isinstance(tree, OrderedDict):
                                    return tree

                                clean_tree = OrderedDict()
                                for _key, _val in tree.items():
                                    if isinstance(_key, re.Pattern):
                                        continue
                                    if isinstance(_val, OrderedDict):
                                        _val = remove_patterns(_val)
                                    clean_tree[_key] = _val
                                return clean_tree

                            config[key] = remove_patterns(default)

                elif isinstance(config, list):
                    try:
                        config = [
                            import_defaults(item, next(iter(defaults)))
                            for item in config
                        ]
                    except StopIteration:
                        pass

                return config

            # Get default values
            defaults = get_defaults(configschema)

            # Import default values into config
            config = import_defaults(config, defaults)
    elif create_default:
        # Read defaults and include descriptions
        config = get_defaults(configschema, True)

        # Render text
        if language == 'YAML':
            text = render_yaml(config)
        elif language == 'TOML':
            text = render_toml(config)
        else:
            text = ""

        # Dump config to file
        try:
            with open(configuration_filename, 'w') as stream:
                stream.write(text)
                print('Created configuration file: %s' % configuration_filename)
        except IOError as error:
            raise IOError(
                'Unable to create configuration file: %s' % configuration_filename
            ) from error

    # Turn keys to lowercase if requested
    if lower_keys:
        config = keys_to_lower(config)

    # Look for errors
    error = best_match(validator.iter_errors(config))
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

    # Return config
    return config
