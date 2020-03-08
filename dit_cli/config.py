"""Handle the config file"""

import os
import toml


def get_config() -> dict:
    """Get the config, or generate it if not present"""
    path = get_path()
    if not os.path.isfile(path):
        print('No config file found. Generating one at {}'.format(path))
        generate_config(path)
    parsed_toml = toml.load(path)
    # TODO: the toml parser has a bug which makes single quotes not parse
    # correctly, so these are absolutes. Fix this somehow
    parsed_toml['Javascript']['str_open'] = '"'
    parsed_toml['Javascript']['str_close'] = '"'
    parsed_toml['Python']['str_open'] = '"'
    parsed_toml['Python']['str_close'] = '"'
    return parsed_toml


def generate_config(path: str):
    """Generate the config file in the home directory"""
    toml_string = """
    [general]
    tmp_dir = '/tmp/dit/'
    serializer = 'Javascript'

    [Javascript]
    name = 'Javascript'
    path = '/usr/bin/nodejs'
    file_extension = 'js'
    function_string = 'function run() {@@CODE}\\n'
    call_string = 'console.log(`begin--${run()}--end`);\\n'

    null_type = 'null'
    str_open = '"'
    str_close = '"'
    str_escape = '\\'

    list_open = '['
    list_delimiter = ','
    list_close = ']'

    obj_open = '{'
    obj_colon = ':'
    obj_delimiter = ','
    obj_close = '}'

    [Python]
    name = 'Python'
    path = '/usr/bin/python'
    file_extension = 'py'
    function_string = 'def run():@@CODE\\n'
    call_string = 'print("begin--{}--end".format(run()))'
    
    null_type = 'None'
    str_open = '"'
    str_close = '"'
    str_escape = '\\'

    list_open = '['
    list_delimiter = ','
    list_close = ']'

    obj_open = '{'
    obj_colon = ':'
    obj_delimiter = ','
    obj_close = '}'
    """

    parsed_toml = toml.loads(toml_string)

    with open(path, 'w') as config_file:
        toml.dump(parsed_toml, config_file)


def get_path() -> str:
    """Get a path to the config file in the home directory"""
    # Could have multiple sources in the future, but not important rn
    # dir_path = os.path.join(os.getcwd(), file_name)
    return os.path.join(os.path.expanduser('~'), '.dit-languages')
