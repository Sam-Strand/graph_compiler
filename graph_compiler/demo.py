from typing import Dict, Any

from graph import Graph
from compiler import GraphCompiler

# 1. Определение функций

def add_node(node: Dict, node_inputs: Dict, results: Dict) -> Any:
    '''Узел сложения'''
    a = node_inputs['a']
    b = node_inputs['b']
    print(f"        Сложение: {a} + {b} = {a + b}")
    return a + b

def multiply_node(node: Dict, node_inputs: Dict, results: Dict) -> Any:
    '''Узел умножения'''
    x = node_inputs['x']
    y = node_inputs['y']
    result = x * y
    print(f"        Умножение: {x} * {y} = {result}")
    return result

# 2. Пул функций
nodes_pool = {
    'add': add_node,
    'multiply': multiply_node
}

# 3. JSON граф
graph_data = {
    'nodes': [
        {'id': 'a', 'type': 'in', 'uid': 'a'},
        {'id': 'b', 'type': 'in', 'uid': 'b'},
        {'id': 'c', 'type': 'in', 'uid': 'c'},
        {'id': 'add', 'type': 'compute', 'uid': 'add'},
        {'id': 'mult', 'type': 'compute', 'uid': 'multiply'},
        {'id': 'result', 'type': 'out', 'uid': 'result'}
    ],
    'connections': [
        {'source': 'a', 'target': 'add', 'targetInput': 'a'},
        {'source': 'b', 'target': 'add', 'targetInput': 'b'},
        {'source': 'add', 'target': 'mult', 'targetInput': 'x'},
        {'source': 'c', 'target': 'mult', 'targetInput': 'y'},
        {'source': 'mult', 'target': 'result', 'targetInput': 'value'}
    ]
}

# 1. Создаем граф
graph = Graph(graph_data)

# 2. Добавляем логирование
def update(progress, uid):
    print(f'    Выполнено {progress*100:.3f}%, начат: {uid}')

# 2. Подготавливаем компилятор
compiler = GraphCompiler(nodes_pool, update)

# 3. Компилируем
compiled_graph = compiler.compile(graph)

# 4. Расчеты с разным дано
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
