from typing import Dict, Any
import numpy as np
from graph import Graph
from compiler import GraphCompiler



def add_node(node, node_inputs: Dict, results: Dict) -> Any:
    a = node_inputs['a']
    b = node_inputs['b']
    result = a + b
    print(f'        add: {a} + {b} = {result}')
    return result


def split_node(node, node_inputs: Dict, results: Dict) -> Dict[str, Any]:
    x = node_inputs['x']
    result = {
        'double': x * 2,
        'square': x ** 2
    }
    print(f'        split: {x} → {result}')
    return result


def multiply_node(node, node_inputs: Dict, results: Dict) -> Any:
    x = node_inputs['x']
    y = node_inputs['y']
    result = x * y
    print(f'        multiply: {x} * {y} = {result}')
    return result


nodes_pool = {
    'add': add_node,
    'split': split_node,
    'multiply': multiply_node
}


graph_data = {
    'nodes': [
        {'id': 'a', 'type': 'in', 'uid': 'a'},
        {'id': 'b', 'type': 'in', 'uid': 'b'},

        {'id': 'add', 'type': 'compute', 'uid': 'add'},
        {'id': 'split', 'type': 'compute', 'uid': 'split'},
        {'id': 'mult', 'type': 'compute', 'uid': 'multiply'},

        {'id': 'out_double', 'type': 'out', 'uid': 'double'},
        {'id': 'out_square', 'type': 'out', 'uid': 'square'}
    ],
    'connections': [
        {'source': 'a', 'sourceOutput': 'value', 'target': 'add', 'targetInput': 'a'},
        {'source': 'b', 'sourceOutput': 'value', 'target': 'add', 'targetInput': 'b'},

        {'source': 'add', 'sourceOutput': 'value', 'target': 'split', 'targetInput': 'x'},

        {'source': 'split', 'sourceOutput': 'double', 'target': 'mult', 'targetInput': 'x'},
        {'source': 'split', 'sourceOutput': 'square', 'target': 'mult', 'targetInput': 'y'},

        {'source': 'mult', 'sourceOutput': 'value', 'target': 'out_double', 'targetInput': 'value'},
        {'source': 'split', 'sourceOutput': 'square', 'target': 'out_square', 'targetInput': 'value'}
    ]
}


graph = Graph(graph_data)


def update(progress, uid):
    print(f'    {progress * 100:.1f}% → {uid}')


compiler = GraphCompiler(nodes_pool, update)
compiled = compiler.compile(graph)


inputs = {
    'a': np.array([1, 2, 3]),
    'b': 2
}

print('\n▶️ ВЫЧИСЛЕНИЕ')
outputs = compiled.execute(inputs)

print('\n✅ РЕЗУЛЬТАТ')
for k, v in outputs.items():
    print(f'    {k}: {v}')
