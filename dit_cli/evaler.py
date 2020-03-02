"""Runs code in any language, given correct configs"""

import os
import subprocess
from typing import Type

from dit_cli import CONFIG, traverse
from dit_cli.tree import Node, Tree
from dit_cli.parser import prep_code
from dit_cli.exceptions import ValidationError


def validate_object(obj: Node, tree: Tree):
    for contain in obj.contains:
        if contain['id_'] != -1:
            for list_item in traverse(contain['data']):  # In case it's a list
                validate_object(list_item, tree)

    _run_validator(tree.nodes[obj.extends[0]], obj, tree)


def _run_validator(class_: Node, obj: Node, tree: Tree):
    for extend in class_.extends:
        _run_validator(tree.nodes[extend], obj, tree)

    if class_.validator:
        path = _get_file_path(class_, 'Validator')
        _build_file(path, class_, obj, tree)
        result = _run_file(path, class_.validator['language'])
        if result != 'true':
            raise ValidationError(result, obj.name)


def _get_file_path(class_: Node, purpose: str) -> str:
    """Generate file name and path to file"""
    file_name = class_.name + '-' + purpose + '.' \
        + CONFIG[class_.validator['language']]['file_extension']
    return os.path.join(CONFIG['general']['tmp_dir'], file_name)


def _build_file(path: str, class_: Node, obj: Node, tree: Tree):
    lang = CONFIG[class_.validator['language']]
    code = prep_code(class_.validator['code'], class_, obj, tree)
    file_string = lang['function_string'].replace('@@CODE', code)
    file_string += lang['call_string']
    file_string = file_string.replace(r'\n', '\n')
    file_string += '\n'

    with open(path, 'w') as code_file:
        code_file.write(file_string)


def _run_file(file_name, language: str):
    """Run the file in a subprocess and return the result"""
    cmd = [CONFIG[language]['path'], file_name]
    output = subprocess.run(cmd, check=True, capture_output=True)
    raw = str(output.stdout)
    begin = 'begin--'
    end = '--end'
    return raw[raw.find(begin) + len(begin):raw.find(end)]


'''
def run_scripts(node_id: int, graph: Type[nx.DiGraph], payload: str):
    """Run the validator of an object if it has one,
    then recurse through extensions and overrisions"""
    node = graph.nodes[node_id]
    if 'validator' in node:
        file_path = get_file_path(node, 'Validator')
        build_file(file_path, node['validator'], payload, node['language'], )
        result = run_file(file_path, node['language'])
        if result != 'true':
            raise ValidationError(result, node['name'])

    for parent_id in graph.successors(node_id):
        relationship = graph[node_id][parent_id]['relationship']

        if relationship == 'extends':
            run_scripts(parent_id, graph, payload)
        elif relationship == 'overrides':
            converter = graph[node_id][parent_id]['converter']
            file_path = get_file_path(node, 'Converter')
            build_file(file_path, converter,
                       payload, node['language'])
            result = run_file(file_path, node['language'])
            run_scripts(parent_id, graph, result)

def build_file(file_path: str, code: str, payload: str, language: str) -> str:
    """Create file in /tmp/ and fill with correct paramenters"""
    file_string = ''
    mod_payload = payload.replace('"', r'\"')
    file_string += str(CONFIG[language]['variable_string']).replace(
        '@@NAME', 'PAYLOAD').replace('@@VALUE', '"' + mod_payload + '"')

    file_string += str(CONFIG[language]['function_string']).replace(
        '@@CODE', code)
    file_string += CONFIG[language]['call_string']
    file_string = file_string.replace(r'\n', '\n')
    file_string += '\n'

    with open(file_path, 'w') as code_file:
        code_file.write(file_string)
'''
