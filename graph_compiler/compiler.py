from typing import Dict, List, Any, Callable
import numpy as np


class CompiledGraph:
    '''Скомпилированный граф - хранит состояние компилированной функции'''

    def __init__(self, calculator: Callable, input_ids: List[str], output_ids: List[str]):
        self.calculator = calculator
        self.input_ids = input_ids
        self.output_ids = output_ids

    def execute(self, input_values: Dict[str, Any]) -> Dict[str, Any]:
        return self.calculator(input_values)


def create_input_node_func(node: Dict) -> Callable:
    uid = node.uid

    def input_func(input_values: Dict[str, Any]) -> Any:
        return np.array(input_values[uid])
    return input_func


def create_output_node_func(input_sources: Dict[str, str]) -> Callable:
    source_id = next(iter(input_sources.values()))

    def output_func(results: Dict[str, Any]) -> Any:
        return results[source_id]
    return output_func


class GraphCompiler:
    '''
    Класс компилятора - хранит доступные функции

    Args:
        nodes_pool: Словарь доступных функций
        updater: Функция вызываемая в начале обработки каждой ноды (логер) получает как аргументы долю текущего прогресса и uid выполняемой функции
    '''

    def __init__(self, nodes_pool: Dict[str, Callable], updater=None):
        self.nodes_pool = nodes_pool
        self.updater = updater

    def compile(self, graph: 'Graph') -> 'CompiledGraph':
        '''Компилирует граф в исполняемую функцию'''

        compiled_nodes = self._compile_nodes(graph)
        node_count = len(graph.sort)
        node_list = [
            (node_id, graph.nodes[node_id], compiled_nodes[node_id])
            for node_id in graph.sort
        ]

        def calculator(input_values: Dict[str, Any]) -> Dict[str, Any]:
            results = {}
            outputs = {}

            for i, (node_id, node, node_func) in enumerate(node_list, 1):
                if self.updater:
                    self.updater(i / node_count, node_id)
                if node.type == 'in':
                    result = node_func(input_values)
                else:
                    result = node_func(results)

                if node.type == 'out':
                    outputs[node.uid] = result
                else:
                    results[node_id] = result

            return outputs

        return CompiledGraph(
            calculator=calculator,
            input_ids=graph.input_ids,
            output_ids=graph.output_ids
        )

    def _compile_nodes(self, graph: 'Graph') -> Dict[str, Callable]:
        '''Компилирует все узлы графа'''
        compiled_nodes = {}

        for node in graph:
            node_type = node.type
            input_sources = graph.connections.get(node.id, {})

            if node_type == 'in':
                compiled_nodes[node.id] = create_input_node_func(node)
            elif node_type == 'out':
                compiled_nodes[node.id] = create_output_node_func(input_sources)
            else:
                compiled_nodes[node.id] = self._create_computation_node_func(node, input_sources)

        return compiled_nodes

    def _create_computation_node_func(self, node: Dict, input_sources: Dict[str, str]) -> Callable:
        node_func = self.nodes_pool[node.uid]
        input_keys = list(input_sources.keys())
        source_ids = [input_sources[key] for key in input_keys]

        def computation_func(results: Dict[str, Any]) -> Any:
            inputs = {
                key: results[source_id]
                for key, source_id in zip(input_keys, source_ids)
            }
            return node_func(node=node, node_inputs=inputs, results=results)

        return computation_func
