from typing import Dict, Any, Set, Iterator, Optional, List
from collections import defaultdict, deque
from dataclasses import dataclass, field


def build_reverse_graph(connections: List[Dict[str, Any]]) -> Dict[str, Set[str]]:
    '''
    Строит обратный граф (target → sources) для обхода в ширину.

    Args:
    connections: Список соединений, где каждое соединение содержит ключи 'source' и 'target'

    Returns:
    Словарь, где ключ - ID целевого узла, значение - множество ID исходных узлов
    '''
    reverse_graph = defaultdict(set)
    for conn in connections:
        reverse_graph[conn['target']].add(conn['source'])
    return reverse_graph


def find_reachable_nodes(start_nodes: Set[str], reverse_graph: Dict[str, Set[str]]) -> Set[str]:
    '''
    Находит все узлы, достижимые из начальных узлов через обратный граф.

    Args:
    start_nodes: Множество начальных узлов (обычно выходные узлы графа)
    reverse_graph: Обратный граф, построенный функцией build_reverse_graph

    Returns:
    Множество ID всех узлов, достижимых из start_nodes
    '''
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
    '''
    Обрабатывает variable-ноды, заменяя их реальными соединениями.

    Variable-ноды группируются по label. Для каждой группы:
    1. Находим input-ноду (is_input=True) и output-ноды (is_input=False)
    2. Создаем прямые соединения от источников input-ноды к целям output-нод
    3. Удаляем старые соединения через variable-ноды

    Args:
    json_data: Граф с variable-нодами в формате {'nodes': [...], 'connections': [...]}

    Returns:
    Оптимизированный граф без variable-нод
    '''
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
    '''
    Оптимизирует граф: удаляет variable-ноды и недостижимые узлы.

    Процесс оптимизации:
    1. Удаление variable-нод (process_variable_nodes)
    2. Построение обратного графа от выходных узлов
    3. Поиск достижимых узлов
    4. Удаление недостижимых узлов и соединений

    Args:
    json_data: Исходный граф для оптимизации

    Returns:
    Оптимизированный граф только с достижимыми узлами
    '''    
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
    '''
    Выполняет топологическую сортировку графа (алгоритм Кана).

    Args:
    nodes: Словарь всех узлов {node_id: node_data}
    inputs: Словарь входных соединений {target_id: {input_slot: source_id}}
    outputs: Словарь выходных соединений {source_id: {output_slot: {target_ids}}}

    Returns:
    Список ID узлов в топологическом порядке (от входов к выходам)
    '''
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
        '''
        Инициализирует граф из JSON данных.
        Процесс инициализации:
        1. Оптимизация графа (удаление variable-нод и недостижимых узлов)
        2. Создание объектов Node для каждого узла
        3. Построение структур inputs/outputs
        4. Топологическая сортировка
        5. Извлечение ID входных и выходных узлов

        Args:
        json_data: Граф в формате {'nodes': [...], 'connections': [...]}
        '''
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
        '''
        Извлекает UID всех входных узлов (type='in').

        Returns:
        Список UID входных узлов
        '''
        return [n['uid'] for n in self.json_data['nodes'] if n.get('type') == 'in']

    def _extract_output_ids(self) -> List[str]:
        '''
        Извлекает UID всех выходных узлов (type='out').

        Returns:
        Список UID выходных узлов
        '''
        return [n['uid'] for n in self.json_data['nodes'] if n.get('type') == 'out']
