# Schemed YAML Config
Schemed YAML Config is a library to read and validate [YAML](https://yaml.org/) based configuration files against [JSON Schema](https://json-schema.org/) specifications.  

# Install
Schemed-yaml-config can be installed via PIP
```
# pip install schemed-yaml-config
```

# Under the hood
Schemed YAML Config works by converting YAML files into a dictionarie by mean of the well known [PyYAML framework](https://pyyaml.org/) and then by applying JSON Schema specifications before of returning it to rest of the script.  
The beauty of this approach is it combines the human friendly serialization of YAML with the power of JSON Schema.

![](https://github.com/lamehost/schemed-yaml-config/raw/master/images/venn_diagram.png)

A few tricks has been added to make the library even more human friendly. For instance when the a configuration file is missing and a default is created, order and comments of the keys from the schema are borrowed to the YAML file.

# Syntax
```
Python 3.7.4 (default, Aug 21 2019, 16:01:23)
[GCC 9.2.1 20190813] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>>
>>> from schemed_yaml_config import get_config
>>> config = get_config('config.yml', 'schema.yml')
>>> print(config)
{'listen': {'host': '192.0.2.1', 'port': 1025}, 'tmpdir': '/tmp'}
>>>
```

# TOML
Despite its name Schemed YAML Config also supports [TOML](https://toml.io/en/) configuration files as experimental feature since [v0.1.0](https://github.com/lamehost/schemed-yaml-config/releases/tag/v0.1.0). TOML schemas are not supported yet!
