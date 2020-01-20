"""Runs code in any language, given correct configs"""

import os
import subprocess
from typing import Type

import networkx as nx

from dit_cli import CONFIG
from dit_cli.exceptions import ValidationError


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


def run_file(file_name, language: str):
    """Run the file in a subprocess and return the result"""
    cmd = [
        CONFIG[language]['path'],
        file_name
    ]
    output = subprocess.run(cmd, check=True, capture_output=True)
    raw = str(output.stdout)
    begin = 'begin--'
    end = '--end'
    return raw[raw.find(begin) + len(begin):raw.find(end)]


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

    with open(file_path, 'w+') as code_file:
        code_file.write(file_string)


def get_file_path(node, purpose: str) -> str:
    """Generate file name and path to file"""
    file_name = node['name'] + '-' + purpose + '.' + \
        CONFIG[node['language']]['file_extension']
    return os.path.join(CONFIG['general']['tmp_dir'], file_name)
