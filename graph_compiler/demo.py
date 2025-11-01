from typing import Dict, Any

from graph import Graph
from compiler import GraphCompiler

# 1. ОПРЕДЕЛЯЕМ ФУНКЦИИ ДЛЯ УЗЛОВ ГРАФА
def add_node(node: Dict, node_inputs: Dict, results: Dict) -> Any:
    """Узел сложения"""
    a = node_inputs['a']
    b = node_inputs['b']
    print(f"        Сложение: {a} + {b} = {a + b}")
    return a + b

def multiply_node(node: Dict, node_inputs: Dict, results: Dict) -> Any:
    """Узел умножения"""
    x = node_inputs['x']
    y = node_inputs['y']
    result = x * y
    print(f"        Умножение: {x} * {y} = {result}")
    return result


# 2. СОЗДАЕМ ПУЛ ФУНКЦИЙ
nodes_pool = {
    'add': add_node,
    'multiply': multiply_node
}

# 3. СОЗДАЕМ ДАННЫЕ ГРАФА В JSON ФОРМАТЕ
graph_data = {
    'nodes': [
        {'id': 'a', 'type': 'in', 'MyID': 'a'},
        {'id': 'b', 'type': 'in', 'MyID': 'b'},
        {'id': 'c', 'type': 'in', 'MyID': 'c'},
        {'id': 'add', 'type': 'compute', 'MyID': 'add'},
        {'id': 'mult', 'type': 'compute', 'MyID': 'multiply'},
        {'id': 'result', 'type': 'out', 'MyID': 'result'}
    ],
    'connections': [
        {'source': 'a', 'target': 'add', 'targetInput': 'a'},
        {'source': 'b', 'target': 'add', 'targetInput': 'b'},
        {'source': 'add', 'target': 'mult', 'targetInput': 'x'},
        {'source': 'c', 'target': 'mult', 'targetInput': 'y'},
        {'source': 'mult', 'target': 'result', 'targetInput': 'value'}
    ]
}

# 1. СОЗДАЕМ ГРАФ
graph = Graph(graph_data)

# 2. СОЗДАЕМ КОМПИЛЯТОР
compiler = GraphCompiler(nodes_pool)

# 3. КОМПИЛИРУЕМ ГРАФ
compiled_graph = compiler.compile(graph)

# 4. ВЫПОЛНЯЕМ ВЫЧИСЛЕНИЯ
# Тестовые данные
test_cases = [
    {'a': 2, 'b': 3, 'c': 4},  # (2+3)*4 = 20
    {'a': 5, 'b': [1, 2, 3], 'c': 2},  # (5 + [1 2 3]) * 2 = [12 14 16]
    {'a': 10, 'b': 20, 'c': 0.5}  # (10+20)*0.5 = 15
]
for i, inputs in enumerate(test_cases, 1):
    print(f"\n📊 ТЕСТ {i}:")
    print(f"    Входные данные: {inputs}")
    print("    Процесс вычислений:")
    # Выполняем граф
    results = compiled_graph.execute(inputs)
    print(f"    РЕЗУЛЬТАТ: {results}")
