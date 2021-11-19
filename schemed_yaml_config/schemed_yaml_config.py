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


"""
Main file for the package
"""

import re
import uuid
from collections import OrderedDict
from copy import deepcopy

from jsonschema import Draft7Validator
from jsonschema.exceptions import best_match

import toml
import yaml
import yamlordereddictloader
yaml.add_representer(OrderedDict, yaml.representer.Representer.represent_dict)


class NoAliasDumper(yaml.Dumper):
    """Wrapper around yaml.Dumper that statically disables aliases"""
    def ignore_aliases(self, data):
        return True


class Config():
    """
    Validates configuration against the provided JSONSchema.

    Parameters:
    ----------
        schema_filename: str
            Name (along with path) of the file containting the jsonschema specification formatted
            in YAML.
        config: (str, list or dict)
            Configuration object to be validated (default: None)
        schema_subtree: str
            List of schema object names or id joined by '/'
            For instance /properties/listen/properties/.
            Allow user to import just a part of the schema (default: False)
    """
    def __init__(self, schema_filename, config=None, schema_subtree=False):
        # Init Schema and Validator from schema_filename
        with open(schema_filename, encoding="utf-8") as stream:
            try:
                self.schema = yaml.load(stream, Loader=yamlordereddictloader.Loader)
                # Allow user to consume just a substree in the schema file
                if schema_subtree:
                    for key in schema_subtree.split('/'):
                        self.schema = self.schema[key]
            except (yaml.scanner.ScannerError) as error:
                raise RuntimeError(f'Error while parsing configuration file: {error}') from error
        self.validator = Draft7Validator(self.schema)

        ### I hate this hack and i should find a more elegant way to handle it ###

        # Get default config (includes comments)
        if self.schema['type'] == 'object':
            empty_config = OrderedDict()
        elif self.schema['type'] == 'array':
            empty_config = []
        else:
            empty_config = None

        self.__default_tree = self.__get_default_values(self.schema,  with_description=False)

        default_values = self.__get_default_values(self.schema,  with_description=True)
        self.__default_config = self.__import_default_values(
            config=deepcopy(empty_config),
            default_values=default_values,
            populate_arrays=True
        )

        default_values = self.__get_default_values(self.schema,  with_description=False)
        self.__default_values = self.__import_default_values(
            config=deepcopy(empty_config),
            default_values=default_values,
            populate_arrays=True
        )

        if config is None:
            self.__config = deepcopy(self.__default_values)
        else:
            self.config = config

       ###########################################################################


    @staticmethod
    def __generate_description_prefix():
        """
        Generates random strings used to make descriptions within internal data structure unique.

        Returns:
          string: Random text
        """
        return f'__syc_description_prefix__{uuid.uuid4()}'

    @property
    def config(self):
        """ Returns config object """
        return self.__config

    @config.setter
    def config(self, config):
        """ Set config object """
        # Import default values into config
        self.__config = self.__import_default_values(
            config, self.__default_tree, populate_arrays=False
        )

    # Methods related to validation

    @property
    def is_valid(self):
        """
        Returns true if config is valid

        Returns:
          bool: True if string is valid, false otherwise
        """
        return self.validator.is_valid(self.config)

    @property
    def validation_errors(self):
        """
        Yields validation errors

        Returns:
          geneator: Collection of jsonschema.exceptions.ValidationError
        """
        # Look for errors
        yield self.validator.iter_errors(self.config)

    def validate(self):
        """
        Raises errors if validation fails

        Raises:
            RuntimeError: Text representation of the validation errors
        """
        def walk_path(config, path):
            try:
                item = path.popleft()
                return walk_path(config[item], path)
            except IndexError:
                return config

        error = best_match(self.validator.iter_errors(self.config))

        if error:
            path = "Unknown"
            if error.path is not None:
                path = '/' + '/'.join([str(item) for item in error.relative_path])
                malformed_object = walk_path(self.config,  error.relative_path)
            elif error.parent is not None and error.parent.path is not None:
                path = '/' + '/'.join([str(item) for item in error.parent.relative_path])
                malformed_object = walk_path(self.config,  error.parent.relative_path)

            raise RuntimeError(f"""
Error while parsing configuration file.
  Message: {error.message}
  Path: {path}
  Malformed object: {malformed_object}
            """)

    ### TOML methods ###

    @staticmethod
    def __render_toml(data):
        """ Returns rendered config object in TOML format

        Args:
            data: iterable

        Returns:
            str: rendered text
        """

        text = toml.dumps(data)

        # Handle descriptions
        lines = []
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

        return '\n'.join(lines) + '\n'

    def from_toml(self, text):
        """
        Reads and parse configuation by assuming it is formatted as TOML

        Parameters:
        ----------
            text: Configuration text in TOML format
        """
        self.config = toml.loads(text)

    def to_toml(self):
        """ Returns rendered config object in TOML format """
        return self.__render_toml(self.config)

    def from_toml_file(self, filename):
        """
        Reads from a file and parse configuration by assuming it is formatted as TOML

        Parameters:
        ----------
            filename: Nome of the TOML file containting configuration
        """
        with open(filename, encoding="utf-8") as stream:
            self.from_toml(stream.read())

    def to_toml_file(self, filename):
        """
        Write configuration in TOML format to a file

        Parameters:
        ----------
            filename: Name of the TOML file to write configuration on
        """
        with open(filename, 'w', encoding="utf-8") as stream:
            stream.write(self.to_toml())

    ### YAML methods ###

    @staticmethod
    def __render_yaml(data):
        """ Returns rendered config object in YAML format

        Args:
            data: iterable

        Returns:
            str: rendered text
        """

        text = yaml.dump(
            data,
            default_flow_style=False,
            sort_keys=False,
            width=9999,
            Dumper=NoAliasDumper
        )

        # Handle descriptions
        lines = []
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

        return '\n'.join(lines) + '\n'

    def from_yaml(self, text):
        """
        Reads and parse configuation by assuming it is formatted as YAML

        Parameters:
        ----------
            text: Configuration text in YAML format
        """
        self.config = yaml.load(text, Loader=yaml.FullLoader) or {}

    def to_yaml(self):
        """ Returns rendered config object in YAML format """
        return self.__render_yaml(self.config)

    def from_yaml_file(self, filename):
        """
        Reads from a file and parse configuration by assuming it is formatted as YAML

        Parameters:
        ----------
            filename: Nome of the YAML file containting configuration
        """
        with open(filename, encoding="utf-8") as stream:
            self.from_yaml(stream.read())

    def to_yaml_file(self, filename):
        """
        Write configuration in YAML format to a file

        Parameters:
        ----------
            filename: Name of the YAML file to write configuration on
        """
        with open(filename, 'w', encoding="utf-8") as stream:
            stream.write(self.to_yaml())

    ### Methods related to default values ###

    def default_values(self):
        """ Returns default configuration as specified by the schema """
        return self.__default_values

    def default_config_to_yaml(self):
        """ Returns default configuration as specified by the schema formatted as YAML """
        return self.__render_yaml(self.__default_config)

    def default_config_to_toml(self):
        """ Returns default configuration as specified by the schema formatted as TOML """
        return self.__render_toml(self.__default_config)

    def __get_default_values(self, schema, with_description=False):
        """
        Gets default values from the schema

        Parameters:
        -----------
            schema: dict
                Dictionary containing the json schema
            with_description: bool
                Wether or not include description from the schema (default: False)
        Returns:
        --------
            mixed: Default values
        """
        # Get defaults from template
        try:
            default_values = schema['default']
        except KeyError:
            default_values = self.__make_default_values(
                schema,
                with_description
            )

        # Default can be OrderedDict or list.
        # In that case have to insert description
        if isinstance(default_values, (dict, OrderedDict)):
            if with_description and 'description' in schema:
                description_key = self.__generate_description_prefix()
                default_values[description_key] = schema['description']
                default_values.move_to_end(description_key, False)
        elif isinstance(default_values, list):
            if with_description and 'description' in schema:
                description_key = self.__generate_description_prefix()
                default_values = [f"{description_key} {schema['description']}"] + default_values

        return default_values

    def __make_default_values(self, schema, with_description=False):
        """
        Parses schema and returns default values

        Parameters:
        -----------
        schema: dict
            Dictionary containing the json schema
        with_description: bool
            Wether or not include description from the schema (default: False)

        Returns:
        --------
            mixed: Default values
        """
        if 'type' not in schema:
            raise RuntimeError(
f"""Unable to infer default value from schema.
Message: "type" keywords missing
Schema: {self.__render_yaml(schema)}"""
            )

        # Parse objects
        if schema['type'] == 'object':
            default_values = OrderedDict()

            # Find all properties and patternPriorities
            try:
                properties = list(schema['properties'].items())
            except KeyError:
                properties = []
            try:
                for pattern, value in schema['patternProperties'].items():
                    # Compile regex so that we can use it later
                    pattern = re.compile(pattern)
                    properties.append([pattern, value])
            except KeyError:
                pass

            if not properties:
                raise RuntimeError(
f"""Error while parsing schema file.
Message: Both "properties" and "patternPriorities" missing
Schema {self.__render_yaml(schema)}"""
)

            # Loop over properties
            for _property, subschema in properties:
                # Import description
                if with_description:
                    try:
                        description_key = self.__generate_description_prefix()
                        default_values[description_key] = subschema['description']
                    except (TypeError, KeyError):
                        pass

                # Value might have children, so we run get_defaults over value
                default_values[_property] = self.__get_default_values(
                    subschema, with_description
                )

            return default_values

        # Parse arrays
        if schema['type'] == 'array':
            # Value might have children, so we run get_defaults over value
            default_values = [self.__get_default_values(schema['items'], with_description)]

            # Try to put description at the top of the list
            if with_description and 'description' in schema['items']:
                description_key = self.__generate_description_prefix()
                default_values = [
                    f"{description_key} {schema['items']['description']}"
                ] + default_values

            return default_values

        # Fallback for all of the other objects
        try:
            default_values = schema['default']
        except (TypeError, KeyError):
#             raise RuntimeError(
# f"""Error unable to infer default config.
# Message: "default" keyword missing
# Schema: {self.__render_yaml(schema)}"""
#             ) from error
            default_values = None

        return default_values


    def __import_default_values(self, config, default_values, populate_arrays=False):
        """
        Imports default values into config

        Parameters:
        -----------
        config: mixed
            Configuration to import values into. Can be either list or dict
        default_values: mixed
            Default values to be imported into configuration. Can be either list or dict
        populate_arrays: bool
            Forces function to populate empty arrays

        Returns:
        --------
            mixed: Config with default values imported
        """

        # Remove patternPriorities keys from default
        def remove_patterns(tree):
            if not isinstance(tree, (dict, OrderedDict)):
                return tree

            clean_tree = OrderedDict()
            for key, value in tree.items():
                if isinstance(key, re.Pattern):
                    continue
                if isinstance(value, (dict, OrderedDict)):
                    value = remove_patterns(value)
                clean_tree[key] = value

            return clean_tree

        # Handle dicts
        if isinstance(config, (dict, OrderedDict)):
            # Recursively import defaults into existing keys
            for key, value in config.items():
                if isinstance(key, re.Pattern):
                    continue
                try:
                    config[key] = self.__import_default_values(
                        value, default_values[key], populate_arrays
                    )
                except KeyError:
                    # Unexpected keys
                    continue

            # Recursively import defaults into keys that match with patterns (patternPriorities)
            for pattern, default_value in default_values.items():
                if not isinstance(pattern, re.Pattern):
                    continue
                for key, value in config.items():
                    if pattern.match(key):
                        # Import default_value into value
                        config[key] = self.__import_default_values(
                            value, default_value, populate_arrays
                        )

            # Import missing keys
            for key, default_value in default_values.items():
                # Skip existing keys
                if key in config:
                    continue

                # Skip patterns (patternPriorities)
                if isinstance(key, re.Pattern):
                    continue

                default_value = remove_patterns(default_value)

                if isinstance(default_value, (dict, OrderedDict)):
                    empty_config = OrderedDict()
                elif isinstance(default_value, list):
                    empty_config = []
                else:
                    empty_config = None

                config[key] = self.__import_default_values(
                    empty_config, default_value, populate_arrays
                )

            return config

        # Handle lists
        if isinstance(config, list):
            try:
                item = next(iter(config))
            except StopIteration:
                item = None

            try:
                default_value = next(iter(default_values))
                # First item *could* be description
                if isinstance(default_value, str):
                    if default_value.startswith('__syc_description_prefix__'):
                        default_value = default_values[1]
            except (StopIteration, IndexError):
                if isinstance(item, (dict, OrderedDict)):
                    default_value = OrderedDict()
                elif isinstance(item, list):
                    default_value = []
                else:
                    default_value = None

            for item in config:
                item = self.__import_default_values(item, default_value, populate_arrays)

            if populate_arrays and default_value is not None:
                config = [self.__import_default_values(item, default_value, populate_arrays)]

            return config

        # Fallback for everything else
        if config is None:
            return default_values

        return config


def get_config(
        configuration_filename='config.yml',
        schema_filename='config_schema.yml',
        create_default=True,
        language='yaml'
    ):
    """
    Reproduces schemed_yaml_config v0.x behavior by reading config and schema from files.

    Parameters:
    -----------
    configuration_filename: string
        Path to the filename containing configuration settings (default: config.yml)
    schema_filename: string
        Path to the filename containing jsonschema formatted in YAML (default: config_schema.yml)
    create_default: bool
        If set to true and configuration_filename is missing, then fill it with default settings.
        (default: True)
    language: string
        Defines the language the content of configuration_filename is formatted with.
        Can be either 'yaml' or 'toml'. (default: yaml)
    """

    if language.lower() not in ['yaml', 'toml']:
        raise RuntimeError(f'Unsupported language: {language}')
    language = language.lower()

    config = Config(schema_filename)

    try:
        if configuration_filename is not None:
            if language == 'yaml':
                config.from_yaml_file(configuration_filename)
            else:
                config.from_toml_file(configuration_filename)
    except FileNotFoundError:
        if create_default:
            try:
                if language == 'yaml':
                    with open(configuration_filename, "w", encoding="utf-8") as file:
                        file.write(config.default_config_to_yaml())
                else:
                    with open(configuration_filename, "w", encoding="utf-8") as file:
                        file.write(config.default_config_to_toml())
            except (PermissionError, OSError) as error:
                raise RuntimeError(f'Unable to create configuration file: {error}') from error

    return config
