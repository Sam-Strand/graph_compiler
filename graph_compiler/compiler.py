from typing import Dict, List, Any, Callable, Tuple, Optional
import numpy as np


class CompiledGraph:
    '''Скомпилированный граф - хранит состояние компилированной функции'''

    def __init__(self, calculator: Callable, input_ids: List[str], output_ids: List[str]):
        self.calculator = calculator
        self.input_ids = input_ids
        self.output_ids = output_ids

    def execute(self, input_values: Dict[str, Any]) -> Dict[str, Any]:
        return self.calculator(input_values)


def create_input_node_func(node) -> Callable:
    """Создает функцию для входной ноды"""
    node_id = node.id
    uid = node.uid or node_id

    def input_func(input_values: Dict[str, Any]) -> Any:
        value = input_values.get(uid)
        if value is None:
            raise KeyError(f"Входное значение для '{uid}' не предоставлено")
        return np.array(value) if not isinstance(value, np.ndarray) else value
    
    return input_func


def create_output_node_func(node, input_sources: Dict[str, str], graph) -> Callable:
    """Создает функцию для выходной ноды с поддержкой множественных входов"""
    
    def output_func(results: Dict[str, Any]) -> Any:
        if len(input_sources) == 1:
            # Один вход - возвращаем значение напрямую
            source_id = next(iter(input_sources.values()))
            return results.get(source_id)
        else:
            # Несколько входов - возвращаем словарь
            output_result = {}
            for input_name, source_id in input_sources.items():
                output_result[input_name] = results.get(source_id)
            return output_result
    
    return output_func


class GraphCompiler:
    '''
    Класс компилятора - хранит доступные функции
    
    Args:
        nodes_pool: Словарь доступных функций
        updater: Функция вызываемая в начале обработки каждой ноды
    '''
    
    def __init__(self, nodes_pool: Dict[str, Callable], updater=None):
        self.nodes_pool = nodes_pool
        self.updater = updater
    
    def compile(self, graph: 'Graph') -> 'CompiledGraph':
        '''Компилирует граф в исполняемую функцию'''
        
        # Создаем маппинг портов для быстрого доступа
        port_mapping = graph.all_ports
        compiled_nodes = self._compile_nodes(graph, port_mapping)
        node_count = len(graph.sort)
        
        # Создаем список нод в порядке выполнения
        node_list = [
            (node_id, graph.nodes[node_id], compiled_nodes[node_id])
            for node_id in graph.sort
        ]
        
        def calculator(input_values: Dict[str, Any]) -> Dict[str, Any]:
            # Хранилище результатов всех портов
            port_results = {}
            # Хранилище выходов графа
            outputs = {}
            
            for i, (node_id, node, node_func) in enumerate(node_list, 1):
                if self.updater:
                    self.updater(i / node_count, node_id)
                
                if node.type == 'in':
                    # Входные ноды получают данные из входных значений
                    result = node_func(input_values)
                    # Сохраняем результат в порт по умолчанию
                    default_port = f"{node_id}:default" if 'default' in port_mapping.get(node_id, {}) else node_id
                    port_results[default_port] = result
                else:
                    # Остальные ноды получают данные из результатов
                    result = node_func(port_results)
                
                # Обработка результатов ноды
                if node.type == 'out':
                    # Выходные ноды - сохраняем результат в outputs
                    if node.uid:
                        outputs[node.uid] = result
                    else:
                        outputs[node.id] = result
                else:
                    # Вычислительные ноды - сохраняем результаты портов
                    if isinstance(result, dict):
                        # Нода вернула словарь с несколькими выходами
                        for port_name, port_value in result.items():
                            port_id = f"{node_id}:{port_name}"
                            port_results[port_id] = port_value
                    else:
                        # Нода вернула одно значение
                        if node.output_ports:
                            # Если есть определенные порты, сохраняем в первый порт
                            if node.output_ports:
                                default_port_name = node.output_ports[0]
                                port_id = f"{node_id}:{default_port_name}"
                            else:
                                port_id = f"{node_id}:default"
                        else:
                            port_id = node_id
                        port_results[port_id] = result
            
            return outputs
        
        return CompiledGraph(
            calculator=calculator,
            input_ids=graph.input_ids,
            output_ids=graph.output_ids
        )
    
    def _compile_nodes(self, graph: 'Graph', port_mapping: Dict[str, Dict[str, str]]) -> Dict[str, Callable]:
        '''Компилирует все узлы графа'''
        compiled_nodes = {}
        
        for node in graph:
            node_type = node.type
            input_sources = graph.connections.get(node.id, {})
            
            if node_type == 'in':
                compiled_nodes[node.id] = create_input_node_func(node)
            elif node_type == 'out':
                compiled_nodes[node.id] = create_output_node_func(node, input_sources, graph)
            else:
                compiled_nodes[node.id] = self._create_computation_node_func(
                    node, input_sources, port_mapping, graph
                )
        
        return compiled_nodes
    
    def _create_computation_node_func(self, node, input_sources: Dict[str, str], 
                                    port_mapping: Dict[str, Dict[str, str]], graph: 'Graph') -> Callable:
        """Создает функцию для вычислительной ноды с поддержкой портов"""
        
        if node.uid not in self.nodes_pool:
            raise KeyError(f"Функция для ноды с uid='{node.uid}' не найдена в nodes_pool")
        
        node_func = self.nodes_pool[node.uid]
        input_keys = list(input_sources.keys())
        source_ids = [input_sources[key] for key in input_keys]
        
        def computation_func(port_results: Dict[str, Any]) -> Any:
            # Собираем входные данные
            inputs = {}
            for key, source_id in zip(input_keys, source_ids):
                # Ищем значение в портах
                if source_id in port_results:
                    inputs[key] = port_results[source_id]
                else:
                    # Пытаемся найти значение в альтернативных местах
                    # 1. Проверяем, есть ли source_id как node_id без порта
                    if source_id in port_results:
                        inputs[key] = port_results[source_id]
                    else:
                        # 2. Ищем все порты этой ноды
                        node_id, port_name = graph.split_port_id(source_id)
                        if node_id in port_mapping:
                            for port_full_id in port_mapping[node_id].values():
                                if port_full_id in port_results:
                                    if port_name and port_full_id.endswith(f":{port_name}"):
                                        inputs[key] = port_results[port_full_id]
                                        break
                                    elif not port_name and port_full_id == node_id:
                                        inputs[key] = port_results[port_full_id]
                                        break
            
            # Выполняем функцию ноды
            try:
                result = node_func(node=node, node_inputs=inputs, results=port_results)
                return result
            except Exception as e:
                raise RuntimeError(f"Ошибка в ноде '{node.id}' (uid='{node.uid}'): {str(e)}")
        
        return computation_func
