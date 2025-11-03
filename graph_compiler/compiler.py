from typing import Dict, List, Any, Callable
import numpy as np
from graph import Graph


class CompiledGraph:
    def __init__(self, calculator: Callable, input_ids: List[str], output_ids: List[str]):
        self.calculator = calculator
        self.input_ids = input_ids
        self.output_ids = output_ids

    def execute(self, input_values: Dict[str, Any]) -> Dict[str, Any]:
        return self.calculator(input_values)


def create_input_node_func(node: Dict) -> Callable:
    uid = node['uid']

    def input_func(input_values):
        return np.array(input_values[uid])
    return input_func


def create_output_node_func(input_sources: Dict[str, str]) -> Callable:
    source_id = next(iter(input_sources.values()))

    def output_func(results):
        return results[source_id]
    return output_func


class GraphCompiler:
    """Компилятор графа"""

    def __init__(self, nodes_pool: Dict[str, Callable], updater=None):
        self.nodes_pool = nodes_pool
        self.updater = updater

    def compile(self, graph: Graph, subgraphs: Dict[str, Graph] = None) -> CompiledGraph:
        compiled_nodes = {}
        for node_id in graph.sort:
            node = graph.nodes[node_id]
            ntype = node.get('type')
            input_sources = graph.connections.get(node_id, {})
            if ntype == 'in':
                compiled_nodes[node_id] = create_input_node_func(node)
            elif ntype == 'out':
                compiled_nodes[node_id] = create_output_node_func(
                    input_sources)
            elif ntype == 'if':
                compiled_nodes[node_id] = self._create_if_node_func(
                    node, input_sources, subgraphs)
            else:
                compiled_nodes[node_id] = self._create_computation_node_func(
                    node, input_sources)

        node_list = [(nid, graph.nodes[nid], compiled_nodes[nid])
                     for nid in graph.sort]
        node_count = len(node_list)

        def calculator(input_values):
            results = {}
            outputs = {}
            for i, (node_id, node, func) in enumerate(node_list, 1):
                if self.updater:
                    self.updater(i/node_count, node_id)
                ntype = node.get('type')
                if ntype == 'in':
                    result = func(input_values)
                else:
                    result = func(results)
                if ntype == 'out':
                    outputs[node['uid']] = result
                else:
                    if isinstance(result, dict):
                        results.update(result)
                    else:
                        results[node_id] = result
            return outputs

        return CompiledGraph(calculator, graph.input_ids, graph.output_ids)

    def _create_computation_node_func(self, node, input_sources):
        node_func = self.nodes_pool[node['uid']]
        keys = list(input_sources.keys())
        src_ids = [input_sources[k] for k in keys]

        def comp_func(results):
            node_inputs = {k: results[sid] for k, sid in zip(keys, src_ids)}
            return node_func(node, node_inputs, results)
        return comp_func


    def _create_if_node_func(self, node, input_sources, subgraphs: Dict[str, Graph]):
        cond_src = input_sources['cond']

        true_graph = subgraphs.get(f"{node['id']}_true") if subgraphs else None
        false_graph = subgraphs.get(f"{node['id']}_false") if subgraphs else None

        compiled_true = self.compile(true_graph, subgraphs) if true_graph else None
        compiled_false = self.compile(false_graph, subgraphs) if false_graph else None

        def if_func(results):
            mask = results[cond_src]
            shared_inputs = dict(results)

            # True-ветка
            res_true = None
            if compiled_true and np.any(mask):
                inputs_true = {k: v.copy() if isinstance(v, np.ndarray) else v
                            for k, v in shared_inputs.items()}
                for k in inputs_true:
                    if isinstance(inputs_true[k], np.ndarray):
                        inputs_true[k] = np.where(mask, inputs_true[k], np.nan)
                tmp_true = compiled_true.execute(inputs_true)
                res_true = next(iter(tmp_true.values()))  # берём единственный output

            # False-ветка
            res_false = None
            if compiled_false and np.any(~mask):
                inputs_false = {k: v.copy() if isinstance(v, np.ndarray) else v
                                for k, v in shared_inputs.items()}
                for k in inputs_false:
                    if isinstance(inputs_false[k], np.ndarray):
                        inputs_false[k] = np.where(~mask, inputs_false[k], 0)
                tmp_false = compiled_false.execute(inputs_false)
                res_false = next(iter(tmp_false.values()))  # берём единственный output

            # Объединяем ветви в один массив
            if res_true is None: res_true = np.zeros_like(mask, dtype=float)
            if res_false is None: res_false = np.zeros_like(mask, dtype=float)
            merged = np.where(mask, res_true, res_false)

            return {node['id']: merged}

        return if_func
