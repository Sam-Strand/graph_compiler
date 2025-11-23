from typing import Dict, List, Any, Set, Iterator, Optional
from collections import defaultdict, deque
from dataclasses import dataclass, field


def build_reverse_graph(json_data: Dict[str, Any]) -> Dict[str, List[str]]:
    reverse_graph = defaultdict(list)
    for conn in json_data['connections']:
        reverse_graph[conn['target']].append(conn['source'])
    return reverse_graph


def find_reachable_nodes(start_nodes: Set[str], reverse_graph: Dict[str, List[str]]) -> Set[str]:
    visited = set()
    queue = deque(start_nodes)
    while queue:
        node_id = queue.popleft()
        if node_id in visited:
            continue
        visited.add(node_id)
        for dep in reverse_graph.get(node_id, []):
            if dep not in visited:
                queue.append(dep)
    return visited


def process_variable_nodes(json_data: Dict[str, Any]) -> Dict[str, Any]:
    '''Обрабатывает variable ноды, заменяя их реальными соединениями'''
    variable_nodes = [node for node in json_data['nodes'] if node.get('type') == 'variable']
    
    variable_groups = defaultdict(list)
    for node in variable_nodes:
        label = node.get('data', {}).get('label', '')
        if label:
            variable_groups[label].append(node)
    
    connections_by_target = defaultdict(list)
    connections_by_source = defaultdict(list)
    
    for conn in json_data['connections']:
        connections_by_target[conn['target']].append(conn)
        connections_by_source[conn['source']].append(conn)
    
    new_connections = []
    connections_to_remove = []
    
    for label, nodes in variable_groups.items():
        input_node = next((node for node in nodes if node.get('data', {}).get('is_input')), None)
        output_nodes = [node for node in nodes if not node.get('data', {}).get('is_input')]
        
        if not input_node or not output_nodes:
            continue
        
        input_connections = connections_by_target.get(input_node['id'], [])
        
        for output_node in output_nodes:
            output_connections = connections_by_source.get(output_node['id'], [])
            
            for input_conn in input_connections:
                for output_conn in output_connections:
                    new_connections.append({
                        'source': input_conn['source'],
                        'target': output_conn['target'],
                        'targetInput': output_conn['targetInput']
                    })
            
            connections_to_remove.extend(input_connections)
            connections_to_remove.extend(output_connections)
    
    json_data['connections'] = [
        conn for conn in json_data['connections'] 
        if conn not in connections_to_remove
    ]
    
    json_data['connections'].extend(new_connections)
    
    return json_data


def optimize_graph(json_data: Dict[str, Any]) -> Dict[str, Any]:
    '''Оптимизирует граф, удаляя неиспользуемые узлы'''
    json_data = process_variable_nodes(json_data)
    
    output_nodes = {
        node['id'] for node in json_data['nodes']
        if node.get('type') == 'out'
    }

    reverse_graph = build_reverse_graph(json_data)
    used_nodes = find_reachable_nodes(output_nodes, reverse_graph)

    optimized_nodes = [
        node for node in json_data['nodes']
        if node['id'] in used_nodes
    ]

    optimized_connections = [
        conn for conn in json_data['connections']
        if conn['target'] in used_nodes and conn['source'] in used_nodes
    ]

    return {
        'nodes': optimized_nodes,
        'connections': optimized_connections
    }


def topological_sort(nodes_dict: Dict[str, Dict], node_input_map) -> List[str]:
    in_degree = {node_id: 0 for node_id in nodes_dict}
    graph = defaultdict(list)

    for node_id in nodes_dict:
        dependencies = node_input_map.get(node_id, {})
        in_degree[node_id] = len(dependencies)
        for source_id in dependencies.values():
            graph[source_id].append(node_id)

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


@dataclass
class Node:
    id: str # Уникальный идентификатор ноды
    uid: Optional[str] = None # Уникальный идентификатор типа ноды
    type: Optional[str] = None # Группа ноды
    data: Dict[str, Any] = field(default_factory=dict) # Дополнительные параметры


class Graph:
    '''Класс графа вычислений - хранит состояние графа'''

    def __init__(self, json_data: Dict[str, Any]):
        self.json_data = optimize_graph(json_data)

        self.nodes = {
            node['id']: Node(
                id=node['id'],
                uid=node.get('uid'),
                type=node.get('type'),
                data=node.get('data', {})
            ) 
            for node in self.json_data['nodes']
        }

        self.connections = defaultdict(dict)

        for conn in self.json_data['connections']:
            target = conn['target']
            input_slot = conn['targetInput']
            self.connections[target][input_slot] = conn['source']

        self.sort = topological_sort(self.nodes, self.connections)
        self.input_ids = self._extract_input_ids()
        self.output_ids = self._extract_output_ids()

    def __iter__(self) -> Iterator[Dict[str, Any]]:
        '''Итерация по узлам графа в порядке топологической сортировки'''
        for node_id in self.sort:
            yield self.nodes[node_id]

    def _extract_input_ids(self) -> List[str]:
        return [node['uid'] for node in self.json_data['nodes'] if node.get('type') == 'in']

    def _extract_output_ids(self) -> List[str]:
        return [node['uid'] for node in self.json_data['nodes'] if node.get('type') == 'out']