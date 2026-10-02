"""Bounded original SD examples, not AI inference; never reads Gold fixtures."""
from .profiled_content_models import NewContent,NewSolution
from .authored_models import SummaryStatistics
from .authored_math import (summary_stats,raw_stats,rational,display,solution_steps,question_text,verify_solution,result)

CASES={('full_worked_examples',2):(12,'96','816'),('guided_practice',1):(6,'30','174'),
       ('guided_practice',2):(5,'30','190'),('independent_practice',3):(16,'160','1664'),('exit_check',1):(4,'20','116')}


def raw_summary(values):
    numbers=tuple(rational(v) for v in values)
    return SummaryStatistics(n=len(numbers),sum_x=str(sum(numbers)),sum_x2=str(sum(v*v for v in numbers)))


def verify_new_content(item,solution):
    """Adapter to the existing P4A engine, including raw-data consistency checks."""
    checks={}
    try:
        checks['separate_solution_identity']=solution.item_ref==item.ref
        if item.raw_values:
            summary=raw_summary(item.raw_values);mean,variance,_=raw_stats(item.raw_values)
            verified=verify_solution(summary,solution)
            checks.update(verified.checks)
            checks['raw_mean_variance']=rational(solution.mean)==mean and rational(solution.variance)==variance
            deviations=tuple(rational(v)-mean for v in item.raw_values)
            checks['raw_deviations']=solution.deviations==tuple(str(v) for v in deviations)
            checks['raw_squared_deviations']=solution.squared_deviations==tuple(str(v*v) for v in deviations)
            checks['raw_instructional_only']=item.instructional_demonstration_only and not item.task_form_refs and not item.assesses_learning_requirement_refs
            checks['raw_prompt_values']=item.question=='Calculate the population standard deviation of these observations: '+', '.join(item.raw_values)+'.'
            return result(checks,verified.errors)
        if item.summary:
            verified=verify_solution(item.summary,solution,item.question);checks.update(verified.checks)
            if item.concept_prompt:checks['concept_response_separate']=bool(solution.expected_meaning and solution.key_semantic_elements)
            return result(checks,verified.errors)
        checks['concept_response_separate']=bool(solution.expected_meaning and solution.key_semantic_elements)
        checks['no_numeric_answer']=all(getattr(solution,k) is None for k in ('mean','variance','numeric_answer','display_answer','exact_answer'))
        return result(checks)
    except (ValueError,TypeError,ArithmeticError) as exc:return result(checks,(str(exc),))


def author(role,ordinal,learning):
    kind=role.kind
    lr={r.type:r.ref for r in learning.learning_requirements}
    task=next(r for r in learning.learning_requirements if r.type=='capability_under_task_form')
    task_refs=tuple(r for r in task.source_refs if r.startswith('task-form-'))
    base=dict(ref=f'authored-sd-p5b-v1-{kind}-{ordinal}',semantic_role=kind,learning_requirement_refs=role.learning_requirement_refs,
        assesses_learning_requirement_refs=role.assesses_learning_requirement_refs,support_mode=role.support_mode)
    if kind=='early_concept_retrieval' and ordinal==1:
        item=NewContent(**base,question='Two datasets have the same mean. One is more dispersed around that mean. Which has the larger standard deviation?')
        solution=NewSolution(ref=item.ref+'-solution',item_ref=item.ref,expected_meaning='The more dispersed dataset has the larger standard deviation.',key_semantic_elements=('more spread or dispersion','larger standard deviation'))
        return item,solution
    if kind=='mini_worked_example' and ordinal==1:
        values=('2','4','4','6');summary=raw_summary(values)
        item=NewContent(**base,question='Calculate the population standard deviation of these observations: '+', '.join(values)+'.',raw_values=values,instructional_demonstration_only=True)
    elif (kind,ordinal) in CASES:
        n,total,squares=CASES[kind,ordinal];summary=SummaryStatistics(n=n,sum_x=total,sum_x2=squares)
        scaffolding=()
        if kind=='guided_practice':
            scaffolding=('Calculate Σx² / n.','Calculate (Σx / n)².','Subtract the second result from the first.','Take the square root.') if ordinal==1 else ('Use σ = sqrt(Σx² / n - (Σx / n)²).',)
        item=NewContent(**base,question=question_text(summary),summary=summary,task_form_refs=task_refs,scaffolding=scaffolding,
            concept_learning_requirement_refs=(lr['conceptual_understanding'],) if kind=='exit_check' else (),
            calculation_learning_requirement_refs=tuple(sorted((lr['capability'],lr['capability_under_task_form']))),
            concept_prompt='In one sentence, what does standard deviation measure?' if kind=='exit_check' else None)
    else:return None
    mean,variance,sd=summary_stats(summary.n,summary.sum_x,summary.sum_x2)
    deviations=tuple(rational(v)-mean for v in item.raw_values)
    solution=NewSolution(ref=item.ref+'-solution',item_ref=item.ref,method_steps=solution_steps(summary),mean=str(mean),variance=str(variance),
        exact_answer=dict(op='sqrt',radicand=str(variance)),numeric_answer=str(sd),display_answer=display(sd),
        deviations=tuple(str(v) for v in deviations),squared_deviations=tuple(str(v*v) for v in deviations),
        expected_meaning='It measures the spread of observations around the mean.' if kind=='exit_check' else None,
        key_semantic_elements=('spread or dispersion','around the mean') if kind=='exit_check' else ())
    return item,solution
