import numpy as np
from graph import Graph
from compiler import GraphCompiler

# === основной граф ===
json_main = {
    'nodes': [
        {'id':'a','uid':'a','type':'in'},
        {'id':'b','uid':'b','type':'in'},
        {'id':'c','uid':'c','type':'in'},
        {'id':'if','uid':'if','type':'if'},
        {'id':'d','uid':'d','type':'out'}
    ],
    'connections': [
        {'source':'a','target':'if','targetInput':'cond'},
        {'source':'b','target':'if','targetInput':'true'},
        {'source':'c','target':'if','targetInput':'false'},
        {'source':'if','target':'d','targetInput':'val'}
    ]
}

# === подграфы IF ===
json_true = {
    'nodes': [
        {'id':'b','uid':'b','type':'in'},
        {'id':'t_if','uid':'b_plus_10','type':'calc'},
        {'id':'t_out','uid':'t_out','type':'out'}
    ],
    'connections': [
        {'source':'b','target':'t_if','targetInput':'x'},
        {'source':'t_if','target':'t_out','targetInput':'val'}
    ]
}

json_false = {
    'nodes': [
        {'id':'c','uid':'c','type':'in'},
        {'id':'f_if','uid':'c_times_2','type':'calc'},
        {'id':'f_out','uid':'f_out','type':'out'}
    ],
    'connections': [
        {'source':'c','target':'f_if','targetInput':'x'},
        {'source':'f_if','target':'f_out','targetInput':'val'}
    ]
}

# функции нод
def add_10(node, inputs, results):
    return inputs['x'] + 10

def mul_2(node, inputs, results):
    print(inputs['x'])
    return inputs['x'] * 2

nodes_pool = {
    'b_plus_10': add_10,
    'c_times_2': mul_2
}

# === создание графов ===
main_graph = Graph(json_main)
subgraphs = {
    'if_true': Graph(json_true),
    'if_false': Graph(json_false)
}

# === компиляция ===
compiler = GraphCompiler(nodes_pool)
compiled = compiler.compile(main_graph, subgraphs=subgraphs)

# === входные данные ===
inputs = {
    'a': np.array([True, True, True, False]),
    'b': np.array([1, 2, 3, 4]),
    'c': np.array([10, 20, 30, 40])
}

# === выполнение ===
result = compiled.execute(inputs)
print('Выход d:', result)
