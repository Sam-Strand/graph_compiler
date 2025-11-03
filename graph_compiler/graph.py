from typing import Dict, List, Any
from collections import defaultdict, deque

def topological_sort(nodes_dict: Dict[str, Dict], node_input_map) -> List[str]:
    in_degree = {node_id: 0 for node_id in nodes_dict}
    graph = defaultdict(list)
    for node_id in nodes_dict:
        deps = node_input_map.get(node_id, {})
        in_degree[node_id] = len(deps)
        for src in deps.values():
            graph[src].append(node_id)
    queue = deque(node_id for node_id in nodes_dict if in_degree[node_id] == 0)
    sorted_order = []
    while queue:
        node_id = queue.popleft()
        sorted_order.append(node_id)
        for neighbor in graph[node_id]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    return sorted_order

class Graph:
    """Класс плоского графа"""
    def __init__(self, json_data: Dict[str, Any]):
        self.nodes = {node['id']: node for node in json_data['nodes']}
        self.connections = defaultdict(dict)
        for conn in json_data['connections']:
            self.connections[conn['target']][conn['targetInput']] = conn['source']
        self.sort = topological_sort(self.nodes, self.connections)
        self.input_ids = [node['uid'] for node in json_data['nodes'] if node.get('type')=='in']
        self.output_ids = [node['uid'] for node in json_data['nodes'] if node.get('type')=='out']
