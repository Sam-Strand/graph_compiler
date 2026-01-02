from typing import Dict, Any, Set, Iterator, Optional, List
from collections import defaultdict, deque
from dataclasses import dataclass, field


def build_reverse_graph(connections: List[Dict[str, Any]]) -> Dict[str, Set[str]]:
    reverse_graph = defaultdict(set)
    for conn in connections:
        reverse_graph[conn['target']].add(conn['source'])
    return reverse_graph


def find_reachable_nodes(start_nodes: Set[str], reverse_graph: Dict[str, Set[str]]) -> Set[str]:
    visited = set()
    queue = deque(start_nodes)

    while queue:
        node_id = queue.popleft()
        if node_id in visited:
            continue
        visited.add(node_id)
        queue.extend(reverse_graph.get(node_id, set()) - visited)

    return visited


def process_variable_nodes(json_data: Dict[str, Any]) -> Dict[str, Any]:
    '''Обрабатывает variable ноды, заменяя их реальными соединениями'''
    
    variable_nodes = [n for n in json_data['nodes'] if n.get('type') == 'variable']

    groups = defaultdict(list)
    for node in variable_nodes:
        label = node.get('data', {}).get('label')
        if label:
            groups[label].append(node)

    by_target = defaultdict(list)
    by_source = defaultdict(list)

    for conn in json_data['connections']:
        by_target[conn['target']].append(conn)
        by_source[conn['source']].append(conn)

    new_connections = []
    to_remove = set()

    for nodes in groups.values():
        input_node = next((n for n in nodes if n.get('data', {}).get('is_input')), None)
        output_nodes = [n for n in nodes if not n.get('data', {}).get('is_input')]

        if not input_node or not output_nodes:
            continue

        input_conns = by_target.get(input_node['id'], [])

        for out_node in output_nodes:
            output_conns = by_source.get(out_node['id'], [])

            for ic in input_conns:
                for oc in output_conns:
                    new_connections.append({
                        'source': ic['source'],
                        'target': oc['target'],
                        'targetInput': oc['targetInput']
                    })

            to_remove.update(map(id, input_conns))
            to_remove.update(map(id, output_conns))

    json_data['connections'] = [
        c for c in json_data['connections'] if id(c) not in to_remove
    ]
    json_data['connections'].extend(new_connections)

    return json_data


def optimize_graph(json_data: Dict[str, Any]) -> Dict[str, Any]:
    json_data = process_variable_nodes(json_data)

    output_nodes = {
        n['id'] for n in json_data['nodes'] if n.get('type') == 'out'
    }

    reverse_graph = build_reverse_graph(json_data['connections'])
    used_nodes = find_reachable_nodes(output_nodes, reverse_graph)

    return {
        'nodes': [n for n in json_data['nodes'] if n['id'] in used_nodes],
        'connections': [
            c for c in json_data['connections']
            if c['source'] in used_nodes and c['target'] in used_nodes
        ]
    }


def topological_sort(
    nodes: Dict[str, Any],
    inputs: Dict[str, Dict[str, str]],
    outputs: Dict[str, Dict[str, Set[str]]]
) -> List[str]:
    in_degree = {node_id: 0 for node_id in nodes}

    for target, slots in inputs.items():
        in_degree[target] = len(slots)

    queue = deque(node_id for node_id, d in in_degree.items() if d == 0)
    order = []

    while queue:
        node_id = queue.popleft()
        order.append(node_id)

        for targets in outputs.get(node_id, {}).values():
            for target_id in targets:
                in_degree[target_id] -= 1
                if in_degree[target_id] == 0:
                    queue.append(target_id)

    return order


@dataclass
class Node:
    id: str
    uid: Optional[str] = None
    type: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)


class Graph:
    '''Класс графа вычислений - хранит состояние графа'''

    def __init__(self, json_data: Dict[str, Any]):
        self.json_data = optimize_graph(json_data)

        self.nodes = {
            n['id']: Node(
                id=n['id'],
                uid=n.get('uid'),
                type=n.get('type'),
                data=n.get('data', {})
            )
            for n in self.json_data['nodes']
        }

        self.inputs = defaultdict(dict)
        self.outputs = defaultdict(lambda: defaultdict(set))

        for conn in self.json_data['connections']:
            source = conn['source']
            target = conn['target']
            input_slot = conn['targetInput']
            output_slot = conn.get('sourceOutput', 'default')

            source_output = conn.get('sourceOutput', 'default')
            self.inputs[target][input_slot] = (source, source_output)
            self.outputs[source][output_slot].add(target)

        self.sort = topological_sort(self.nodes, self.inputs, self.outputs)
        self.input_ids = self._extract_input_ids()
        self.output_ids = self._extract_output_ids()

    def __iter__(self) -> Iterator[Node]:
        for node_id in self.sort:
            yield self.nodes[node_id]

    def _extract_input_ids(self) -> List[str]:
        return [n['uid'] for n in self.json_data['nodes'] if n.get('type') == 'in']

    def _extract_output_ids(self) -> List[str]:
        return [n['uid'] for n in self.json_data['nodes'] if n.get('type') == 'out']
