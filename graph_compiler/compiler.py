from typing import Dict, List, Any, Callable
import numpy as np


class CompiledGraph:
    '''Скомпилированный граф - хранит состояние компилированной функции'''

    def __init__(self, calculator: Callable, input_ids: List[str], output_ids: List[str]):
        '''
        Инициализирует скомпилированный граф.

        Args:
        calculator: Исполняемая функция графа, принимает входные значения и возвращает выходные
        input_ids: Список идентификаторов входных узлов (их UID)
        output_ids: Список идентификаторов выходных узлов (их UID)
        '''
        self.calculator = calculator
        self.input_ids = input_ids
        self.output_ids = output_ids

    def execute(self, input_values: Dict[str, Any]) -> Dict[str, Any]:
        '''
        Выполняет вычисления на графе.

        Args:
        input_values: Словарь входных значений вида {input_uid: value}

        Returns:
        Словарь выходных значений вида {output_uid: value}

        Example:
        python result = compiled_graph.execute({'input1': 5, 'input2': 10})
        '''
        return self.calculator(input_values)


def create_input_node_func(node) -> Callable:
    '''
    Создает функцию для входного узла.

    Args:
    node: Объект узла Graph.Node, должен содержать uid

    Returns:
    Функция, которая извлекает значение из input_values по uid узла
    и преобразует его в numpy.ndarray
    '''
    uid = node.uid

    def input_func(input_values: Dict[str, Any]) -> Any:
        value = input_values[uid]
        if isinstance(value, np.ndarray):
            return value
        return np.array(value)

    return input_func


def create_output_node_func(input_sources: Dict[str, tuple]) -> Callable:
    '''
    Создает функцию для выходного узла (out).
    
    Особенности:
    - У выходного узла всегда один вход через слот 'input'
    - Нет выходов
    - Просто возвращает значение, пришедшее на вход
    
    Args:
        input_sources: Всегда содержит один ключ 'input': ('source_id', 'source_output')
    '''
    if 'input' not in input_sources:
        def output_func(results: Dict[str, Any]) -> Any:
            return None
        return output_func

    source_id, source_output = input_sources['input']
    
    def output_func(results: Dict[str, Any]) -> Any:
        value = results[source_id]
        
        if isinstance(value, dict):
            return value[source_output]
        
        return value
    
    return output_func


class GraphCompiler:
    '''
    Класс компилятора - хранит доступные функции
    '''

    def __init__(self, nodes_pool: Dict[str, Callable], updater=None):
        '''
        Инициализирует компилятор.

        Args:
        nodes_pool: Словарь доступных вычислительных функций.
        Ключи - UID типов узлов, значения - функции вычисления.
        Формат функции: func(node, node_inputs, results) -> Any
        updater: Опциональная функция обратного вызова для отслеживания прогресса.
        Вызывается для каждого узла с аргументами (progress, node_uid),
        где progress от 0.0 до 1.0
        '''
        self.nodes_pool = nodes_pool
        self.updater = updater

    def compile(self, graph: 'Graph') -> CompiledGraph:
        '''
        Компилирует граф в исполняемую функцию.

        Args:
        graph: Объект Graph, представляющий оптимизированный граф вычислений

        Returns:
        Объект CompiledGraph, готовый к выполнению

        Process:
        1. Компилирует все узлы графа в отдельные функции
        2. Создает общую функцию-калькулятор, которая:
        - Принимает входные значения
        - Последовательно вычисляет узлы в топологическом порядке
        - Собирает результаты
        - Возвращает выходные значения
        3. Возвращает CompiledGraph с калькулятором и метаданными

        Note:
        Порядок вычислений определяется топологической сортировкой графа
        '''
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
        '''
        Внутренний метод: компилирует все узлы графа.

        Args:
        graph: Объект Graph

        Returns:
        Словарь {node_id: compiled_function} для всех узлов графа

        Node types:
        - 'in': Создается функция ввода (create_input_node_func)
        - 'out': Создается функция вывода (create_output_node_func)
        - другие: Создается вычислительная функция (_create_computation_node_func)
        '''
        compiled_nodes = {}

        for node in graph:
            input_sources = graph.inputs.get(node.id, {})

            if node.type == 'in':
                compiled_nodes[node.id] = create_input_node_func(node)

            elif node.type == 'out':
                compiled_nodes[node.id] = create_output_node_func(input_sources)

            else:
                compiled_nodes[node.id] = self._create_computation_node_func(
                    node,
                    input_sources
                )

        return compiled_nodes

    def _create_computation_node_func(self, node, input_sources: Dict[str, tuple]) -> Callable:
        '''
        Создает функцию для вычислительного узла.

        Args:
        node: Объект узла
        input_sources: Словарь входных соединений узла

        Returns:
        Функция, которая:
        1. Извлекает входные значения из результатов предыдущих вычислений
        2. Подготавливает словарь входов для узла
        3. Вызывает оригинальную функцию из nodes_pool
        4. Возвращает результат

        Note:
        Поддерживает извлечение значений из вложенных словарей, когда
        предыдущий узел возвращает несколько выходов
        '''       
        node_func = self.nodes_pool[node.uid]
        slots = dict(input_sources)

        def computation_func(results: Dict[str, Any]) -> Any:
            inputs = {}
            for slot, (source_id, source_output) in slots.items():
                value = results[source_id]
                if isinstance(value, dict):
                    value = value[source_output]
                inputs[slot] = value

            return node_func(
                node=node,
                node_inputs=inputs,
                results=results
            )

        return computation_func
