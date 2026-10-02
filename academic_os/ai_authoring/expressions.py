"""Bounded SL-10 expression grammar, exact arithmetic; no executable syntax."""
import re
from decimal import Decimal, localcontext
from fractions import Fraction
from ..authored_math import rational, root, summary_stats

VERSION = 'sl10-expression/1'
FIELDS = ('first_term', 'second_term', 'mean', 'variance')
SCALAR = re.compile(r'-?\d+(?:\.\d+|/\d+)?', re.ASCII)
TOKEN = re.compile(r'[ \t\r\n]+|Σx²|Σx|sum_x2|sum_x|first term|second term|radicand|sqrt|n|[0-9]+(?:\.[0-9]+)?|[()/÷\-²^]')
ALIASES = {'Σx':'sum_x', 'Σx²':'sum_x2', 'first term':'first_term', 'second term':'second_term'}
VARIABLES = {'sum_x','sum_x2','n','first_term','second_term','radicand'}


class ExpressionError(ValueError):
    def __init__(self, code): self.code=code;super().__init__(code)


def scalar(value):
    if not isinstance(value,str) or len(value)>128 or not SCALAR.fullmatch(value):
        raise ExpressionError('scalar_encoding_invalid')
    try:return rational(value)
    except ValueError:raise ExpressionError('scalar_value_invalid') from None


def parse(text):
    if not isinstance(text,str) or len(text)>256:raise ExpressionError('expression_limit')
    tokens=[];pos=0
    while pos<len(text):
        m=TOKEN.match(text,pos)
        if m is None:raise ExpressionError('unsupported_expression')
        token=m.group();pos=m.end()
        if not token.isspace():tokens.append(token)
    if not tokens:raise ExpressionError('parser_failure')
    if len(tokens)>128:raise ExpressionError('expression_limit')
    index=0;nodes=0
    def node(op,**values):
        nonlocal nodes
        nodes+=1
        if nodes>128:raise ExpressionError('expression_limit')
        return dict(op=op,**values)
    def peek():return tokens[index] if index<len(tokens) else None
    def take(expected=None):
        nonlocal index
        value=peek()
        if value is None or expected is not None and value!=expected:raise ExpressionError('parser_failure')
        index+=1;return value
    def atom(depth):
        if depth>16:raise ExpressionError('expression_limit')
        token=take()
        if token=='(':
            value=subtract(depth+1);take(')')
        elif token=='sqrt':
            take('(');value=node('sqrt',arg=subtract(depth+1));take(')')
        elif token=='-':
            number=take()
            if not re.fullmatch(r'[0-9]+(?:\.[0-9]+)?',number):raise ExpressionError('parser_failure')
            value=node('constant',value=str(scalar('-'+number)))
        elif re.fullmatch(r'[0-9]+(?:\.[0-9]+)?',token):
            value=node('constant',value=str(scalar(token)))
        elif ALIASES.get(token,token) in VARIABLES:
            value=node('variable',name=ALIASES.get(token,token))
        else:raise ExpressionError('parser_failure')
        if peek() in ('²','^'):
            if take()=='^' and take()!='2':raise ExpressionError('unsupported_expression')
            value=node('square',arg=value)
        return value
    def divide(depth):
        value=atom(depth)
        while peek() in ('/','÷'):
            take();value=node('divide',left=value,right=atom(depth))
        return value
    def subtract(depth):
        value=divide(depth)
        while peek()=='-':
            take();value=node('subtract',left=value,right=divide(depth))
        return value
    result=subtract(0)
    if index!=len(tokens):raise ExpressionError('parser_failure')
    return result


def bounded(value):
    if isinstance(value,Fraction) and max(value.numerator.bit_length(),value.denominator.bit_length())>2048:
        raise ExpressionError('arithmetic_limit')
    return value


def evaluate(ast, context, depth=0):
    """Only parser-produced canonical AST; a square root may be the outermost op."""
    if depth>128:raise ExpressionError('expression_limit')
    op=ast['op']
    if op=='constant':return bounded(rational(ast['value']))
    if op=='variable':return bounded(context[ast['name']])
    if op=='sqrt':
        if depth!=0:raise ExpressionError('unsupported_root_composition')
        value=evaluate(ast['arg'],context,depth+1)
        if value<0:raise ExpressionError('negative_radicand')
        return root(value)
    if op=='square':
        value=evaluate(ast['arg'],context,depth+1);return bounded(value*value)
    a=evaluate(ast['left'],context,depth+1);b=evaluate(ast['right'],context,depth+1)
    if op=='subtract':return bounded(a-b)
    if op=='divide':
        if not b:raise ExpressionError('division_by_zero')
        return bounded(a/b)
    raise ExpressionError('unsupported_expression')


def context_for(inputs):
    if type(inputs['n']) is not int or not 0<inputs['n']<=1000000:raise ExpressionError('input_invalid')
    total=scalar(inputs['sum_x']);squares=scalar(inputs['sum_x2']);n=inputs['n']
    mean,var,_=summary_stats(n,str(total),str(squares))
    return dict(n=Fraction(n),sum_x=total,sum_x2=squares,first_term=squares/n,
                second_term=mean*mean,radicand=var),dict(first_term=squares/n,second_term=mean*mean,mean=mean,variance=var)


def check(expression, value, inputs, expected=None):
    result=dict(expression=expression,claimed_value=value,valid=False,reason=None,ast=None)
    try:
        context,_=context_for(inputs)
        result['ast']=parse(expression)
        evaluated=evaluate(result['ast'],context)
        claimed=scalar(value)
        if isinstance(evaluated,Decimal):
            # Root results use the existing precision and absolute tolerance.
            with localcontext() as ctx:
                ctx.prec=50
                converted=Decimal(claimed.numerator)/Decimal(claimed.denominator)
                equal=abs(evaluated-converted)<=Decimal('1e-40')
                expected_equal=expected is None or abs(evaluated-Decimal(expected.numerator)/Decimal(expected.denominator))<=Decimal('1e-40')
            result['comparison']='decimal_absolute_tolerance_1e-40'
        else:
            equal=evaluated==claimed;expected_equal=expected is None or evaluated==expected
            result['comparison']='exact_rational'
        result['evaluated_value']=str(evaluated)
        result['valid']=equal and expected_equal
        if not result['valid']:result['reason']='expression_value_mismatch' if not equal else 'expression_expected_value_mismatch'
    except ExpressionError as exc:result['reason']=exc.code
    except (ValueError,ArithmeticError):result['reason']='expression_arithmetic_invalid'
    return result


def verify_solution_expressions(content):
    """Bindings use independently recomputed intermediates, never candidate claims."""
    inputs=content['proposed_math_inputs'];solution=content['proposed_solution']
    _,expected=context_for(inputs)
    checks={key:check(solution[key]['expression'],solution[key]['value'],inputs,expected[key]) for key in FIELDS}
    return dict(verifier_version=VERSION,expression_semantics_valid=all(c['valid'] for c in checks.values()),checks=checks)
