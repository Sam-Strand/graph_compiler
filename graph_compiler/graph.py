from typing import Dict, List, Any, Set, Iterator, Optional, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass, field


def extract_node_id_from_source(source: str) -> str:
    """Извлекает ID ноды из source (может быть с портом или без)"""
    if ':' in source:
        return source.split(':')[0]
    return source


def build_reverse_graph(json_data: Dict[str, Any]) -> Dict[str, List[str]]:
    """Строит обратный граф с учетом портов"""
    reverse_graph = defaultdict(list)
    for conn in json_data['connections']:
        # source может быть в формате "node_id" или "node_id:port_name"
        reverse_graph[conn['target']].append(conn['source'])
    return reverse_graph


def find_reachable_nodes(start_nodes: Set[str], reverse_graph: Dict[str, List[str]]) -> Set[str]:
    """Находит все достижимые ноды из стартового множества"""
    visited = set()
    queue = deque(start_nodes)
    while queue:
        node_id = queue.popleft()
        if node_id in visited:
            continue
        visited.add(node_id)
        for dep in reverse_graph.get(node_id, []):
            dep_node_id = extract_node_id_from_source(dep)
            if dep_node_id not in visited:
                queue.append(dep_node_id)
    return visited


def process_variable_nodes(json_data: Dict[str, Any]) -> Dict[str, Any]:
    """Обрабатывает variable ноды с учетом портов"""
    variable_nodes = [node for node in json_data['nodes'] if node.get('type') == 'variable']
    
    variable_groups = defaultdict(list)
    for node in variable_nodes:
        label = node.get('data', {}).get('label', '')
        if label:
            variable_groups[label].append(node)
    
    # Организуем соединения для быстрого поиска
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
        
        # Находим соединения, которые идут В variable-ноду
        input_connections = connections_by_target.get(input_node['id'], [])
        
        # Находим соединения, которые идут ИЗ output variable-нод
        for output_node in output_nodes:
            output_connections = connections_by_source.get(output_node['id'], [])
            
            # Для каждого входа создаем соединения к каждому выходу
            for input_conn in input_connections:
                for output_conn in output_connections:
                    new_connections.append({
                        'source': input_conn['source'],
                        'target': output_conn['target'],
                        'targetInput': output_conn['targetInput']
                    })
            
            # Помечаем старые соединения для удаления
            connections_to_remove.extend(output_connections)
    
    # Удаляем старые соединения через variable-ноды
    connections_to_remove_ids = [
        (c['source'], c['target'], c['targetInput']) 
        for c in connections_to_remove
    ]
    
    json_data['connections'] = [
        conn for conn in json_data['connections']
        if (conn['source'], conn['target'], conn['targetInput']) not in connections_to_remove_ids
    ]
    
    # Добавляем новые соединения
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

    # Также добавляем все ноды, упомянутые в source соединений
    for conn in json_data['connections']:
        source_node_id = extract_node_id_from_source(conn['source'])
        used_nodes.add(source_node_id)

    # Добавляем все входные ноды
    input_nodes = {
        node['id'] for node in json_data['nodes']
        if node.get('type') == 'in'
    }
    used_nodes.update(input_nodes)

    optimized_nodes = [
        node for node in json_data['nodes']
        if node['id'] in used_nodes
    ]

    optimized_connections = [
        conn for conn in json_data['connections']
        if conn['target'] in used_nodes and extract_node_id_from_source(conn['source']) in used_nodes
    ]

    return {
        'nodes': optimized_nodes,
        'connections': optimized_connections
    }


@dataclass
class Node:
    id: str  # Уникальный идентификатор ноды
    uid: Optional[str] = None  # Уникальный идентификатор типа ноды
    type: Optional[str] = None  # Группа ноды (in, out, compute, variable)
    data: Dict[str, Any] = field(default_factory=dict)  # Дополнительные параметры
    output_ports: List[str] = field(default_factory=list)  # Список выходных портов


class Graph:
    '''Класс графа вычислений - хранит состояние графа с поддержкой портов'''
    
    def __init__(self, json_data: Dict[str, Any]):
        # Сохраняем исходные данные
        self.raw_json_data = json_data
        # Оптимизируем граф
        self.json_data = optimize_graph(json_data)
        
        # Создаем ноды с учетом портов
        self.nodes = {}
        for node_data in self.json_data['nodes']:
            node = Node(
                id=node_data['id'],
                uid=node_data.get('uid'),
                type=node_data.get('type'),
                data=node_data.get('data', {})
            )
            
            # Извлекаем информацию о портах из данных ноды
            node_data_dict = node_data.get('data', {})
            if 'output_ports' in node_data_dict:
                node.output_ports = node_data_dict['output_ports']
            elif node_data.get('type') in ['compute', 'function', 'variable']:
                # Для вычислительных нод задаем порт по умолчанию
                node.output_ports = ['default']
            
            self.nodes[node.id] = node
        
        # Строим карту соединений
        self.connections = defaultdict(dict)
        self.port_connections = defaultdict(lambda: defaultdict(list))
        
        for conn in self.json_data['connections']:
            target = conn['target']
            input_slot = conn['targetInput']
            source = conn['source']
            
            # Сохраняем соединение
            self.connections[target][input_slot] = source
            
            # Анализируем source на наличие порта
            source_node_id, source_port = self.split_port_id(source)
            if source_node_id in self.nodes:
                if source_port:
                    self.port_connections[source_node_id][source_port].append((target, input_slot))
                else:
                    # Без порта - используем порт по умолчанию
                    self.port_connections[source_node_id]['default'].append((target, input_slot))
        
        # Топологическая сортировка
        self.sort = self._topological_sort()
        self.input_ids = self._extract_input_ids()
        self.output_ids = self._extract_output_ids()
        self.all_ports = self._build_port_mapping()
    
    def _topological_sort(self) -> List[str]:
        """Топологическая сортировка с учетом портов"""
        in_degree = {node_id: 0 for node_id in self.nodes}
        graph = defaultdict(list)
        
        # Строим граф зависимостей
        for target_id, inputs in self.connections.items():
            for source in inputs.values():
                # Извлекаем id ноды из source (может быть с портом)
                source_node_id = self.split_port_id(source)[0]
                
                if source_node_id in self.nodes:
                    in_degree[target_id] += 1
                    graph[source_node_id].append(target_id)
        
        # Также учитываем ноды, которые ни от кого не зависят
        for node_id in self.nodes:
            if node_id not in in_degree:
                in_degree[node_id] = 0
        
        # Алгоритм Кана
        queue = deque(node_id for node_id in self.nodes if in_degree[node_id] == 0)
        sorted_order = []
        
        while queue:
            node_id = queue.popleft()
            sorted_order.append(node_id)
            
            for neighbor in graph.get(node_id, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        if len(sorted_order) != len(self.nodes):
            # Есть циклические зависимости
            print(f"Warning: Возможные циклические зависимости. Сортировано {len(sorted_order)} из {len(self.nodes)} нод")
            # Добавляем оставшиеся ноды в конец
            for node_id in self.nodes:
                if node_id not in sorted_order:
                    sorted_order.append(node_id)
        
        return sorted_order
    
    def _build_port_mapping(self) -> Dict[str, Dict[str, str]]:
        """Строит маппинг портов нод"""
        port_mapping = {}
        
        for node_id, node in self.nodes.items():
            if node.output_ports:
                port_mapping[node_id] = {
                    port_name: f"{node_id}:{port_name}"
                    for port_name in node.output_ports
                }
            else:
                # Ноды без явно заданных портов
                if node.type == 'in':
                    port_mapping[node_id] = {'default': node_id}
                elif node.type == 'out':
                    port_mapping[node_id] = {}
                else:
                    port_mapping[node_id] = {'default': node_id}
        
        return port_mapping
    
    def get_port_id(self, node_id: str, port_name: str = None) -> str:
        """Получает полный идентификатор порта"""
        if port_name:
            return f"{node_id}:{port_name}"
        return node_id
    
    def split_port_id(self, port_id: str) -> Tuple[str, Optional[str]]:
        """Разделяет идентификатор порта на ноду и имя порта"""
        if ':' in port_id:
            node_id, port_name = port_id.split(':', 1)
            return node_id, port_name
        return port_id, None
    
    def get_node_outputs(self, node_id: str) -> Dict[str, List[Tuple[str, str]]]:
        """Получает все выходные соединения ноды с указанием портов"""
        outputs = defaultdict(list)
        
        # Ищем в соединениях через port_connections
        if node_id in self.port_connections:
            for port_name, connections in self.port_connections[node_id].items():
                for target_id, input_name in connections:
                    outputs[port_name].append((target_id, input_name))
        
        return dict(outputs)
    
    def get_node_inputs(self, node_id: str) -> Dict[str, str]:
        """Получает все входные соединения ноды"""
        return dict(self.connections.get(node_id, {}))
    
    def get_input_nodes(self) -> List[str]:
        """Получает список входных нод"""
        return [node_id for node_id, node in self.nodes.items() if node.type == 'in']
    
    def get_output_nodes(self) -> List[str]:
        """Получает список выходных нод"""
        return [node_id for node_id, node in self.nodes.items() if node.type == 'out']
    
    def _extract_input_ids(self) -> List[str]:
        return [node.id for node in self.nodes.values() if node.type == 'in']
    
    def _extract_output_ids(self) -> List[str]:
        return [node.id for node in self.nodes.values() if node.type == 'out']
    
    def validate_connections(self) -> List[str]:
        """Проверяет корректность всех соединений"""
        errors = []
        
        for target_id, inputs in self.connections.items():
            if target_id not in self.nodes:
                errors.append(f"Целевая нода {target_id} не существует")
                continue
                
            target_node = self.nodes[target_id]
            
            for input_name, source in inputs.items():
                source_node_id, source_port = self.split_port_id(source)
                
                # Проверяем существование source ноды
                if source_node_id not in self.nodes:
                    errors.append(f"Source нода {source_node_id} не существует")
                    continue
                
                source_node = self.nodes[source_node_id]
                
                # Проверяем существование порта (если указан)
                if source_port and source_port not in source_node.output_ports:
                    errors.append(
                        f"Порт '{source_port}' не существует у ноды {source_node_id} "
                        f"(тип: {source_node.type}, uid: {source_node.uid}). "
                        f"Доступные порты: {source_node.output_ports}"
                    )
        
        return errors
    
    def __iter__(self) -> Iterator[Node]:
        '''Итерация по узлам графа в порядке топологической сортировки'''
        for node_id in self.sort:
            yield self.nodes[node_id]
    
    def __len__(self) -> int:
        '''Количество нод в графе'''
        return len(self.nodes)
    
    def __contains__(self, node_id: str) -> bool:
        '''Проверка наличия ноды'''
        return node_id in self.nodes
    
    def __getitem__(self, node_id: str) -> Node:
        '''Получение ноды по ID'''
        return self.nodes[node_id]
    
    def to_dict(self) -> Dict[str, Any]:
        """Экспорт графа в словарь"""
        return {
            'nodes': [
                {
                    'id': node.id,
                    'uid': node.uid,
                    'type': node.type,
                    'data': {
                        **node.data,
                        'output_ports': node.output_ports if node.output_ports else []
                    }
                }
                for node in self.nodes.values()
            ],
            'connections': [
                {
                    'source': source,
                    'target': target,
                    'targetInput': input_name
                }
                for target, inputs in self.connections.items()
                for input_name, source in inputs.items()
            ]
        }
