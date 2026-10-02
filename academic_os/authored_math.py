"""Small exact population-statistics verifier. No stored approval flag is trusted."""
from decimal import Decimal,localcontext,ROUND_HALF_UP
from fractions import Fraction
from typing import Literal
from .product_models import ProductModel


class MathVerification(ProductModel):
    status:Literal['verified','failed']
    checks:dict[str,bool]
    errors:tuple[str,...]=()


def result(checks,errors=()):
    return MathVerification(status='verified' if checks and all(checks.values()) and not errors else 'failed',checks=checks,errors=tuple(errors))


def rational(value):
    if isinstance(value,bool):raise ValueError('Boolean is not a numerical observation')
    try:return Fraction(str(value))
    except (ValueError,ZeroDivisionError,OverflowError) as exc:raise ValueError('Expected a finite rational number') from exc


def root(value):
    value=rational(value)
    if value<0:raise ValueError('Negative population variance')
    with localcontext() as ctx:
        ctx.prec=50
        return (Decimal(value.numerator)/Decimal(value.denominator)).sqrt()


def display(value):
    value=Decimal(str(value))
    if not value.is_finite():raise ValueError('Display value must be finite')
    with localcontext() as ctx:
        ctx.prec=50
        return format(value.quantize(Decimal('0.01'),rounding=ROUND_HALF_UP),'f')


def summary_stats(n,sum_x,sum_x2):
    if isinstance(n,bool) or not isinstance(n,int) or n<=0:raise ValueError('n must be a positive integer')
    total=rational(sum_x);squares=rational(sum_x2)
    mean=total/n;variance=squares/n-mean*mean
    if variance<0:raise ValueError('Inconsistent summaries: negative implied population variance')
    if n==1 and variance!=0:raise ValueError('One observation must have zero variance')
    return mean,variance,root(variance)


def raw_stats(values):
    values=tuple(rational(x) for x in values)
    if not values:raise ValueError('At least one observation is required')
    mean=sum(values)/len(values)
    variance=sum((x-mean)**2 for x in values)/len(values)
    return mean,variance,root(variance)


def evaluate_rational(expression,variables):
    """Closed arithmetic AST, never Python eval or an executable expression string."""
    if not isinstance(expression,dict):raise ValueError('Expression must be an object')
    op=expression.get('op')
    if op=='variable':
        if set(expression)!={'op','name'} or expression['name'] not in variables:raise ValueError('Unknown mathematical variable')
        return rational(variables[expression['name']])
    if set(expression)!={'op','args'}:raise ValueError('Invalid expression shape')
    args=expression['args']
    if op=='square' and len(args)==1:return evaluate_rational(args[0],variables)**2
    if op in ('divide','subtract') and len(args)==2:
        a=evaluate_rational(args[0],variables);b=evaluate_rational(args[1],variables)
        return a/b if op=='divide' else a-b
    raise ValueError('Unsupported mathematical operation or arity')


def formula_variance(expression,variables):
    if set(expression)!={'op','args'} or expression['op']!='sqrt' or len(expression['args'])!=1:
        raise ValueError('Standard-deviation formula must have one square-root argument')
    return evaluate_rational(expression['args'][0],variables)


def render_expression(expression):
    if not isinstance(expression,dict):raise ValueError('Expression must be an object')
    op=expression.get('op')
    if op=='variable':return expression['name']
    args=[render_expression(x) for x in expression.get('args',[])]
    if op=='sqrt' and len(args)==1:return 'sqrt('+args[0]+')'
    if op=='square' and len(args)==1:return '('+args[0]+')^2'
    if op in ('divide','subtract') and len(args)==2:return '('+args[0]+(' / ' if op=='divide' else ' - ')+args[1]+')'
    raise ValueError('Cannot render unsupported formula')


FORMULA_TEST_DATASETS=(('8','9','10','11','12'),('2','6','10','14','18'),('-3','0','7'),('0.1','0.2','0.8'),('5',),('4','4','4'))


def verify_formula(expression,display_text,datasets=FORMULA_TEST_DATASETS):
    checks={}
    try:
        checks['display_matches_expression']=display_text==render_expression(expression)
        for i,values in enumerate(datasets):
            values=tuple(rational(x) for x in values);mean,variance,_=raw_stats(values)
            variables=dict(n=len(values),sum_x=sum(values),sum_x2=sum(x*x for x in values),sum_squared_deviations=sum((x-mean)**2 for x in values))
            claimed=formula_variance(expression,variables)
            checks['population_identity_dataset_'+str(i)]=claimed==variance
        if not datasets:checks['test_datasets_present']=False
        return result(checks)
    except (ValueError,TypeError,KeyError,ZeroDivisionError,ArithmeticError) as exc:return result(checks,(str(exc),))


def question_text(summary):
    return f'A dataset contains {summary.n} observations. The sum of the observations is {summary.sum_x}, and the sum of their squares is {summary.sum_x2}. Calculate the standard deviation.'


def solution_steps(summary):
    mean,variance,sd=summary_stats(summary.n,summary.sum_x,summary.sum_x2)
    return (f'mean = {summary.sum_x}/{summary.n} = {mean}',
        f'population variance = {rational(summary.sum_x2)/summary.n} - ({mean})^2 = {variance}',
        f'population SD = sqrt({variance})',f'Display to 2 decimal places: {display(sd)}')


def verify_solution(summary,solution,question=None):
    checks={}
    try:
        mean,variance,sd=summary_stats(summary.n,summary.sum_x,summary.sum_x2)
        checks['summaries_feasible']=True
        checks['mean_recomputed']=rational(solution.mean)==mean
        checks['variance_recomputed']=rational(solution.variance)==variance
        checks['exact_answer_recomputed']=isinstance(solution.exact_answer,dict) and solution.exact_answer.get('op')=='sqrt' and set(solution.exact_answer)=={'op','radicand'} and rational(solution.exact_answer['radicand'])==variance
        numeric=Decimal(solution.numeric_answer)
        checks['numeric_answer_recomputed']=numeric.is_finite() and abs(numeric-sd)<=Decimal('1e-40')
        checks['rounding_recomputed']=solution.display_answer==display(sd)
        checks['method_steps_recomputed']=tuple(solution.method_steps)==solution_steps(summary)
        if question is not None:checks['question_values_match']=question==question_text(summary)
        return result(checks)
    except (ValueError,TypeError,KeyError,ArithmeticError) as exc:return result(checks,(str(exc),))


def visual_brief(claims):
    return f'Show both datasets around a marked mean of {claims["A"]["mean"]}. Dataset B is more dispersed than Dataset A. Use the original observations as plotted points.'


def verify_visual(visual):
    checks={}
    try:
        if set(visual.datasets)!={'A','B'} or set(visual.claims)!={'A','B'}:raise ValueError('Visual requires datasets A and B with their claims')
        stats={k:raw_stats(v) for k,v in visual.datasets.items()}
        for label,(mean,variance,sd) in stats.items():
            claim=visual.claims[label]
            checks[label+'_mean']=rational(claim['mean'])==mean
            checks[label+'_variance']=rational(claim['variance'])==variance
            numeric=Decimal(claim['sd'])
            checks[label+'_sd']=numeric.is_finite() and abs(numeric-sd)<=Decimal('1e-40')
        checks['same_mean']=visual.same_mean is True and stats['A'][0]==stats['B'][0]
        checks['sd_order']=tuple(visual.sd_order)==('A','B') and stats['A'][1]<stats['B'][1]
        checks['brief_matches_claims']=visual.brief==visual_brief(visual.claims)
        return result(checks)
    except (ValueError,TypeError,KeyError,ArithmeticError) as exc:return result(checks,(str(exc),))
