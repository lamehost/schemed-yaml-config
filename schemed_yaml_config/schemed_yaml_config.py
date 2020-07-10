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


from __future__ import absolute_import
from __future__ import print_function

import os
import re

from collections import OrderedDict

from jsonschema import Draft4Validator, validators
from jsonschema.exceptions import best_match

import yaml
import yamlordereddictloader
yaml.add_representer(OrderedDict, yaml.representer.Representer.represent_dict)


def extend_with_default(validator_class):
    """
    Wrapper around jsonschema validator_class to add support for default values.
    Returns:
        Extended validator_class
    """
    validate_properties = validator_class.VALIDATORS["properties"]

    def set_defaults(validator, properties, instance, schema):
        """
        Function to set default values
        """
        for _property, subschema in properties.items():
            if "default" in subschema:
                instance.setdefault(_property, subschema["default"])

        for error in validate_properties(validator, properties, instance, schema):
            yield error

    return validators.extend(
        validator_class, {"properties" : set_defaults},
    )

DefaultValidatingDraft4Validator = extend_with_default(Draft4Validator)


def get_defaults(schema, with_description=False):
    """
    Gets default values from the schema
    Args:
        schema: jsonschema
        with_description: Wether or not include description from the schema
    Returns:
        dict: dict with default values
    """
    result = ""
    try:
        _type = schema['type']
    except KeyError:
        return result
    except TypeError:
        raise SyntaxError('Error while parsing configuration file: "type" keyword missing in:\n %s' % yaml.dump(schema))

    if _type == 'object':
        result = OrderedDict()
        try:
            items = schema['properties'].items()
        except KeyError:
            items = schema['patternProperties'].items()
        for key, val in items:
            if with_description:
                try:
                    pos = 0
                    for _ in schema['properties'][key]['description'].splitlines():
                        result['__description__%s_%d' % (key, pos)] = _
                        pos = pos + 1
                except KeyError:
                    pass
            result[key] = get_defaults(val, with_description)
    elif _type == 'array':
        result = [get_defaults(schema['items'], with_description)]
    else:
        try:
            result = schema['default']
        except KeyError:
            result = result

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
        lower_keys=True
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
    Returns:
        dict: configuration statements
    """

    with open(schema_filename) as stream:
        try:
            configschema = yaml.load(stream, Loader=yamlordereddictloader.Loader)
        except (yaml.scanner.ScannerError) as error:
            raise SyntaxError('Error while parsing configuration file: %s' % error)

    if os.path.exists(configuration_filename):
        with open(configuration_filename, 'r') as stream:
            defaults = get_defaults(configschema)
            config = yaml.load(stream, Loader=yaml.FullLoader) or {}
            config = updatedict(defaults, config)
            if lower_keys:
                config = keys_to_lower(config)
    else:
        # Read defaults and include descriptions
        config = get_defaults(configschema, with_description=True)
        content = yaml.dump(config, default_flow_style=False, sort_keys=False, width=9999)

        # Transform key preceding description lines to "# "
        content = content.splitlines()
        for _ in range(len(content)):
            content[_] = re.sub(r"- __description_\S+: '(.*)'", r"  # \1", content[_])
            content[_] = re.sub(r"__description_\S+: '(.*)'", r"# \1", content[_])
            content[_] = re.sub(r"- __description_\S+: ", "  # ", content[_])
            content[_] = re.sub(r"__description_\S+: ", "# ", content[_])
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

    error = best_match(DefaultValidatingDraft4Validator(configschema).iter_errors(config))
    if error:
        if error.path:
            path = '/'.join([str(relative_path) for relative_path in error.relative_path])
            raise SyntaxError(
                'Error while parsing configuration file, not a valid value for: %s' % path
            )
        raise SyntaxError('Error while parsing configuration file: %s' % error.message)


    return config
