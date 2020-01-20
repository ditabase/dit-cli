"""Handle the config file"""

import os
import toml


def get_config() -> dict:
    """Get the config, or generate it if not present"""
    path = get_path()
    if not os.path.isfile(path):
        print('No config file found. Generating one at {}'.format(path))
        generate_config()

    return toml.load(path)


def generate_config():
    """Generate the config file in the home directory"""
    toml_string = """
    [DEFAULT]
    # language is otherwise specified with '<language>' tags
    language = 'Javascript'

    [general]
    tmp_dir = '/tmp/dit/'

    [Javascript]
    path = '/usr/bin/nodejs'
    file_extension = 'js'
    variable_string = 'const @@NAME = @@VALUE;\\n'
    function_string = 'function run() {@@CODE}\\n'
    call_string = 'console.log(`begin--${run()}--end`);'


    [Python]
    path = '/usr/bin/python'
    file_extension = 'py'
    variable_string = '@@NAME = @@VALUE\\n'
    function_string = 'def run():@@CODE\\n'
    call_string = 'print("begin--{}--end".format(run()))'
    """

    parsed_toml = toml.loads(toml_string)

    with open(get_path(), 'w') as config_file:
        toml.dump(parsed_toml, config_file)


def get_path() -> str:
    """Get a path to the config file in the home directory"""
    # Could have multiple sources in the future, but not important rn
    # dir_path = os.path.join(os.getcwd(), file_name)
    return os.path.join(os.path.expanduser('~'), '.dit-languages')
