# GraphCompiler

Python библиотека для компиляции и выполнения графов вычислений.
Библиотека предназначена для использования как бэкенд систем построения графов

## Особенности
- **Производительность** - Предварительная компиляция графов в оптимизированные функции

- **Автоматическая оптимизация** - Удаление неиспользуемых узлов и зависимостей

- **Гибкая архитектура** - Поддержка пользовательских функций вычислений

- **Векторизация** - Встроенная поддержка NumPy для работы с массивами

## Формат узлов

```JSON
{
    "id": "unique_node_id",  # Уникальный идентификатор
    "type": "in|out|Any",    # Тип узла
    "MyID": "function_name"  # Идентификатор функции
}
```

## Формат соединений

```JSON
{
    "source": "source_node_id",  # Узел-источник
    "target": "target_node_id",  # Узел-получатель
    "targetInput": "input_name"  # Имя входного параметра
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
pip install https://github.com/Sam-Strand/graph_compiler/releases/download/v1.0.0/graph_compiler-1.0.0-py3-none-any.whl
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
        {'id': 'a', 'type': 'in', 'MyID': 'a'},
        {'id': 'b', 'type': 'in', 'MyID': 'b'},
        {'id': 'add', 'type': 'compute', 'MyID': 'add'},
        {'id': 'result', 'type': 'out', 'MyID': 'result'}
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
