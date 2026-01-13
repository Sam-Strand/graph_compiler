# GraphCompiler

Python библиотека для компиляции и выполнения графов вычислений.
Библиотека предназначена для использования как бэкенд систем построения графов типа Rete.js

## Особенности
- **Производительность** - Предварительная компиляция графов в оптимизированные функции

- **Автоматическая оптимизация** - Удаление неиспользуемых узлов и зависимостей

- **Гибкая архитектура** - Поддержка пользовательских функций вычислений

- **Векторизация** - Встроенная поддержка NumPy для работы с массивами

## Формат узлов

```JSON
{
    "id": "Уникальный идентификатор",
    "type": "Тип узла in|out|Any",
    "uid": "Идентификатор функции"
}
```

## Формат соединений

```JSON
{
    "source": "Узел-источник",
    "target": "Узел-получатель",
    "targetInput": "Имя выходного получателя"
}
```

## Сигнатура функций

```python
def node_function(node: Dict, node_inputs: Dict, results: Dict) -> Any:
    # node - конфигурация узла
    # node_inputs - входные данные {input_name: value}  
    # results - результаты выполнения предыдущих узлов
    return computation_result
```

## Установка
### Способ 1: Установка из репозитория (требуется Git)
```bash
pip install git+https://github.com/Sam-Strand/graph_compiler.git
```

### Способ 2: Установка готового пакета (без Git)
```bash
pip install https://github.com/Sam-Strand/graph_compiler/releases/download/v1.0.1/graph_compiler-1.0.1-py3-none-any.whl
```

## Быстрый старт
```python
from graph_compiler import Graph, GraphCompiler

# 1. Определяем функции узлов
def add_node(node, node_inputs, results):
    return node_inputs['a'] + node_inputs['b']

# 2. Создаем пул функций
nodes_pool = {
    'add': add_node
}

# 3. Описываем граф вычислений
graph_data = {
    'nodes': [
        {'id': 'a', 'type': 'in', 'uid': 'a'},
        {'id': 'b', 'type': 'in', 'uid': 'b'},
        {'id': 'add', 'type': 'compute', 'uid': 'add'},
        {'id': 'result', 'type': 'out', 'uid': 'result'}
    ],
    'connections': [
        {'source': 'a', 'target': 'add', 'targetInput': 'a'},
        {'source': 'b', 'target': 'add', 'targetInput': 'b'},
        {'source': 'add', 'target': 'result', 'targetInput': 'value'}
    ]
}

# 4. Компилируем и выполняем
graph = Graph(graph_data)
compiler = GraphCompiler(nodes_pool)
compiled = compiler.compile(graph)

results = compiled.execute({'a': 2, 'b': 3})
print(results)  # {'result': 5}
```
