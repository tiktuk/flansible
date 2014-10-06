# coding: utf-8
import pytest
from jinja2 import nodes
from jinja2schema.config import Config

from jinja2schema.core import infer
from jinja2schema.exceptions import MergeException, UnexpectedExpression
from jinja2schema.model import List, Dictionary, Scalar, Unknown, String, Boolean, Tuple, Number
from jinja2schema.util import debug_repr


def test_may_be_defined():
    template = '''
    {% if x is undefined %}
        {% set x = 'atata' %}
    {% endif %}
    {{ x }}

    {% if y is defined %}
        {# pass #}
    {% else %}
        {% set y = 'atata' %}
    {% endif %}
    {{ y }}
    '''
    struct = infer(template)
    expected_struct = Dictionary({
        'x': String(linenos=[2, 3, 5], label='x',
                    constant=False, may_be_defined=True),
        'y': String(linenos=[7, 10, 12], label='y',
                    constant=False, may_be_defined=True),
    })
    assert struct == expected_struct

    template = '''
    {{ x }}
    {% if x is undefined %}
        {% set x = 'atata' %}
    {% endif %}
    {{ x }}
    '''
    struct = infer(template)
    expected_struct = Dictionary({
        'x': String(linenos=[2, 3, 4, 6], label='x',
                    constant=False, may_be_defined=False),
    })
    assert struct == expected_struct


def test_basics_1():
    template = '''
    {% set d = {'x': 123, a: z.qwerty} %}
    {{ d.x }}
    '''
    struct = infer(template)
    expected_struct = Dictionary({
        'a': Scalar(label='a', linenos=[2]),
        'z': Dictionary(label='z', data={
            'qwerty': Unknown(label='qwerty', linenos=[2]),
        }, linenos=[2]),
    })
    assert struct == expected_struct

    template = '''
    {% set d = {'x': 123, a: z.qwerty} %}
    {{ d.x.field }}
    '''
    with pytest.raises(MergeException):
        infer(template)

    template = '''
    {% set x = '123' %}
    {{ x.test }}
    '''
    with pytest.raises(MergeException):
        infer(template)

    template = '''
    {% set a = {'x': 123} %}
    {% set b = {a: 'test'} %}
    '''
    with pytest.raises(MergeException):
        infer(template)


def test_basics_2():
    template = '''
    {% if test1 %}
        {% if test2 %}
            {% set d = {'x': 123, a: z.qwerty} %}
        {% else %}
            {% set d = {'x': 456, a: z.gsom} %}
        {% endif %}
    {% endif %}
    {% if d %}
        {{ d.x }}
    {% endif %}
    {{ z.gsom }}
    '''
    struct = infer(template)
    expected_struct = Dictionary({
        'a': Scalar(label='a', linenos=[4, 6]),
        'test1': Unknown(label='test1', linenos=[2]),
        'test2': Unknown(label='test2', linenos=[3]),
        'z': Dictionary(data={
            'qwerty': Unknown(label='qwerty', linenos=[4]),
            'gsom': Scalar(label='gsom', linenos=[6, 12]),
        }, label='z', linenos=[4, 6, 12]),
    })
    assert struct == expected_struct


def test_basics_3():
    template = '''
    {% if x %}
        {% set x = '123' %}
    {% else %}
        {% set x = '456' %}
    {% endif %}
    {{ x }}
    '''
    struct = infer(template)
    expected_struct = Dictionary({
        'x': String(label='x', linenos=[2, 3, 5, 7]),
    })
    assert struct == expected_struct

    template = '''
    {% if z %}
        {% set x = '123' %}
    {% else %}
        {% set x = '456' %}
    {% endif %}
    {{ x }}
    '''
    struct = infer(template)
    expected_struct = Dictionary({
        'z': Unknown(label='z', linenos=[2]),
    })
    assert struct == expected_struct


def test_basics_4():
    template = '''
    {% set xys = [
        ('a', 0.3),
        ('b', 0.3),
    ] %}
    {% if configuration is undefined %}
        {% set configuration = 'prefix-' ~ timestamp %}
    {% endif %}
    queue: {{ queue if queue is defined else 'wizard' }}
    description: >-
    {% for x, y in xys %}
        {{ loop.index }}:
        {{ x }} {{ y }}
    {% endfor %}
    '''
    struct = infer(template)
    expected_struct = Dictionary({
        'configuration': String(label='configuration',
                                may_be_defined=True, checked_as_undefined=True, constant=False, linenos=[6, 7]),
        'queue': Scalar(label='queue', checked_as_defined=True, constant=False, linenos=[9]),
        'timestamp': String(label='timestamp', constant=False, linenos=[7])
    })
    assert struct == expected_struct


def test_basics_5():
    template = '''
    {% for row in items|batch(3, '&nbsp;') %}
        {% for column in row %}
            {{ column.x }}
        {% endfor %}
    {% endfor %}
    '''
    struct = infer(template)
    expected_struct = Dictionary({
        'items': List(Dictionary({
            'x': Scalar(label='x', linenos=[4])
        }, label='column', linenos=[4]), label='items', linenos=[2, 3]),
    })
    assert struct == expected_struct


def test_basics_6():
    template = '''
    {% for row in items|batch(3, '&nbsp;') %}
    {% endfor %}
    '''
    struct = infer(template)
    expected_struct = Dictionary({
        'items': List(Unknown(), label='items', linenos=[2]),
    })
    assert struct == expected_struct


def test_basics_7():
    template = '''
    {% for row in items|batch(3, '&nbsp;')|batch(1) %}
        {{ row[1][1].name }}
    {% endfor %}
    '''
    struct = infer(template)
    expected_struct = Dictionary({
        'items': List(Dictionary({
            'name': Scalar(label='name', linenos=[3]),
        }, linenos=[3]), label='items', linenos=[2, 3]),
    })
    assert struct == expected_struct


def test_basics_8():
    template = '''
    {% for row in items|batch(3, '&nbsp;')|batch(1) %}
        {{ row[1].name }}
    {% endfor %}
    '''
    with pytest.raises(UnexpectedExpression) as excinfo:
        infer(template)
    e = excinfo.value

    assert isinstance(e.actual_ast, nodes.Filter)
    assert e.expected_struct == List(
        Dictionary({
            'name': Scalar(label='name', constant=False, linenos=[3])
        }, constant=False, linenos=[3]),
        label='row', constant=False, linenos=[2, 3]
    )
    assert e.actual_struct == List(List(Unknown()))


def test_basics_9():
    template = '''
    {% set xs = items|batch(3, '&nbsp;') %}
    {{ xs[0][0] }}
    '''
    struct = infer(template)
    expected_struct = Dictionary({
        'items': List(Unknown(), label='items', linenos=[2]),  # TODO it should be Scalar
    })
    assert struct == expected_struct


def test_basics_10():
    template = '''
    {% set items = data|dictsort %}
    {% for x, y in items %}
    {% endfor %}
    '''
    struct = infer(template)
    expected_struct = Dictionary({
        'data': Dictionary({}, label='data', linenos=[2]),
    })
    assert struct == expected_struct


def test_basics_11():
    template = '''
    {{ a|xmlattr }}
    {{ a.attr1|join(',') }}
    {{ a.attr2|default([])|first }}
    {{ a.attr3|default('gsom') }}
    {% for x in xs|rejectattr('is_active') %}
        {{ x }}
    {% endfor %}
    '''
    struct = infer(template)
    expected_struct = Dictionary({
        'a': Dictionary({
            'attr1': List(String(), label='attr1', linenos=[3]),
            'attr2': List(Scalar(linenos=[4]), label='attr2', linenos=[4], used_with_default=True),
            'attr3': String(label='attr3', linenos=[5], used_with_default=True)
        }, label='a', linenos=[2, 3, 4, 5]),
        'xs': List(
            Scalar(label='x', linenos=[7]),  # TODO it should be Dictionary({'is_active': Unknown()})
            label='xs',
            linenos=[6]
        ),
    })
    assert struct == expected_struct


def test_basics_12():
    template = '''
    {% for k, v in data|dictsort %}
        {{ k }}
        {{ v }}
    {% endfor %}
    '''
    struct = infer(template)
    expected_struct = Dictionary({
        'data': Dictionary({}, label='data', linenos=[2]),
    })
    assert struct == expected_struct


def test_basics_13():
    config = Config()
    config.TYPE_OF_VARIABLE_INDEXED_WITH_INTEGER_TYPE = 'tuple'

    template = '''
    {% for x in xs %}
        {{ x[2] }}
        {{ x[3] }}
    {% endfor %}
    '''
    struct = infer(template, config)
    expected_struct = Dictionary({
        'xs': List(Tuple((
            Unknown(label=None, linenos=[]),
            Unknown(label=None, linenos=[]),
            Scalar(label=None, linenos=[3]),
            Scalar(label=None, linenos=[4]),
        ), label='x', linenos=[3, 4]), label='xs', linenos=[2])
    })
    assert struct == expected_struct


def test_basics_14():
    template = '''
    {{ section.FILTERS.test }}
    {%- for f in section.FILTERS.keys() %}
        {{ section.GEO }}
        {{ loop.index }}
    {%- endfor %}
    '''
    struct = infer(template)
    expected_struct = Dictionary({
        'section': Dictionary({
            'FILTERS': Dictionary({
                'test': Scalar(label='test', linenos=[2])
            }, label='FILTERS', linenos=[2, 3]),
            'GEO': Scalar(label='GEO', linenos=[4]),
        }, label='section', linenos=[2, 3, 4])
    })
    assert struct == expected_struct


def test_basics_15():
    template = '''
    {%- if x is undefined %}
        {{ test }}
    {%- endif %}

    {%- if y is undefined %}
        {% set y = 123 %}
    {%- endif %}

    {%- if y is defined %}
        {{ y }}
    {%- endif %}

    {%- if z is undefined %}
        {{ z }}
    {%- endif %}
    '''
    struct = infer(template)
    expected_struct = Dictionary({
        'x': Unknown(label='x', checked_as_undefined=True, linenos=[2]),
        'test': Scalar(label='test', linenos=[3]),
        'y': Number(label='y', may_be_defined=True, linenos=[6, 7, 10, 11]),
        'z': Scalar(label='z', checked_as_undefined=True, linenos=[14, 15]),
    })
    assert struct == expected_struct


def test_basics_16():
    config = Config()
    config.CONSIDER_CONDITIONS_AS_BOOLEAN = True
    template = '''
    {%- if new_configuration is undefined %}
      {%- if production is defined and production %}
        {% set new_configuration = 'prefix-' ~ timestamp %}
      {%- else %}
        {% set new_configuration = 'prefix-' ~ timestamp %}
      {%- endif %}
    {%- endif %}
    '''
    struct = infer(template, config)
    expected_struct = Dictionary({
        'new_configuration': String(label='new_configuration', may_be_defined=True, checked_as_undefined=True, linenos=[2, 4, 6]),
        'production': Boolean(label='production', checked_as_defined=True, linenos=[3]),
        'timestamp': String(label='timestamp', linenos=[4, 6]),
    })
    assert struct == expected_struct


def test_basics_17():
    template = '''{{ 'x and y' if x and y is defined else ':(' }}'''
    config = Config()
    config.CONSIDER_CONDITIONS_AS_BOOLEAN = True
    struct = infer(template, config)
    expected_struct = Dictionary({
        'x': Boolean(label='x', linenos=[1]),
        'y': Unknown(label='y', checked_as_defined=True, linenos=[1]),
    })
    assert struct == expected_struct

    template = '''
    {% if x is defined and x.a == 'a' %}
        {{ x.b }}
    {% endif %}
    '''
    struct = infer(template, config)
    expected_struct = Dictionary({
        'x': Dictionary({
            'a': Unknown(label='a', linenos=[2]),
            'b': Scalar(label='b', linenos=[3]),

        }, label='x', checked_as_defined=True, linenos=[2, 3])
    })
    assert struct == expected_struct

    template = '''
    {% if x is undefined and x.a == 'a' %}
        {{ x.b }}
    {% endif %}
    '''
    struct = infer(template, config)
    expected_struct = Dictionary({
        'x': Dictionary({
            'a': Unknown(label='a', linenos=[2]),
            'b': Scalar(label='b', linenos=[3]),

        }, label='x', linenos=[2, 3])
    })
    assert struct == expected_struct

    template = '''
    {% if x is undefined %}
        none
    {% endif %}
    {{ x }}
    '''
    struct = infer(template, config)
    expected_struct = Dictionary({
        'x': Scalar(label='x', linenos=[2, 5]),
    })
    assert struct == expected_struct

    template = '''
    {% if x is defined %}
        none
    {% endif %}
    {{ x }}
    '''
    struct = infer(template, config)
    expected_struct = Dictionary({
        'x': Scalar(label='x', linenos=[2, 5]),
    })
    assert struct == expected_struct

    template = '''
    queue: {{ queue if queue is defined else 'wizard' }}
    queue: {{ queue if queue is defined else 'wizard' }}
    '''
    struct = infer(template, config)
    expected_struct = Dictionary({
        'queue': Scalar(label='queue', linenos=[2, 3], checked_as_defined=True)
    })
    assert struct == expected_struct


def test_raw():
    template = '''
    {% raw %}
        {{ x }}
    {% endraw %}
    '''
    struct = infer(template)
    expected_struct = Dictionary()
    assert struct == expected_struct


def test_for():
    template = '''
    {% for number in range(10 - users|length) %}
        {{ number }}
    {% endfor %}
    '''
    struct = infer(template)
    expected_struct = Dictionary({
        'users': List(Unknown(), label='users', linenos=[2]),
    })
    assert struct == expected_struct

    template = '''
    {% for number in range(10 - users|length) %}
        {{ number.field }}
    {% endfor %}
    '''
    with pytest.raises(MergeException):
        infer(template)

    template = '{{ range(10 - users|length) }}'
    with pytest.raises(UnexpectedExpression):
        infer(template)


    template = '''
    {{ lipsum(n=a.field) }}
    '''
    struct = infer(template)
    expected_struct = Dictionary({
        'a': Dictionary({
            'field': Scalar(label='field', linenos=[2]),
        }, label='a', linenos=[2]),
    })
    assert struct == expected_struct

    template = '''
    {% for number in lipsum(n=10) %}
    {% endfor %}
    '''
    with pytest.raises(UnexpectedExpression):
        infer(template)

    template = '{{ lipsum(n=10).field }}'
    with pytest.raises(UnexpectedExpression):
        infer(template)

    template = '''
    {% for k, v in data|dictsort %}
        {{ k.x }}
        {{ v }}
    {% endfor %}
    '''
    with pytest.raises(UnexpectedExpression):
        infer(template)


def test_assignment():
    template = '''
    {% set args = ['foo'] if foo else [] %}
    {% set args = args + ['bar'] %}
    {% set args = args + (['zork'] if zork else []) %}
    f({{ args|join(sep) }});
    '''
    struct = infer(template)
    expected_struct = Dictionary({
        'foo': Unknown(label='foo', linenos=[2]),
        'zork': Unknown(label='zork', linenos=[4]),
        'sep': String(label='sep', linenos=[5])
    })
    assert struct == expected_struct


def test_consider_contitions_as_boolean_setting_1():
    template = '''
    {% if x %}
        Hello!
    {% endif %}
    {{ 'Hello!' if y else '' }}
    '''
    config_1 = Config()
    struct = infer(template, config_1)
    expected_struct = Dictionary({
        'x': Unknown(label='x', linenos=[2]),
        'y': Unknown(label='y', linenos=[5]),
    })
    assert struct == expected_struct

    infer('{% if [] %}{% endif %}', config_1)  # make sure it doesn't raise

    config_2 = Config()
    config_2.CONSIDER_CONDITIONS_AS_BOOLEAN = True
    struct = infer(template, config_2)
    expected_struct = Dictionary({
        'x': Boolean(label='x', linenos=[2]),
        'y': Boolean(label='y', linenos=[5]),
    })
    assert struct == expected_struct

    with pytest.raises(UnexpectedExpression) as e:
        infer('{% if [] %}{% endif %}', config_2)  # make sure this does raise
    assert str(e.value) == ('conflict on the line 1\n'
                            'got: AST node jinja2.nodes.List of structure [<unknown>]\n'
                            'expected structure: <boolean>')


def test_consider_contitions_as_boolean_setting_2():
    config = Config()
    config.CONSIDER_CONDITIONS_AS_BOOLEAN = True

    template = '''
    {% if x == 'test' %}
        Hello!
    {% endif %}
    '''
    struct = infer(template, config)
    expected_struct = Dictionary({
        'x': Unknown(label='x', linenos=[2]),
    })
    assert struct == expected_struct
