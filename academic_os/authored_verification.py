"""Recompute mathematics from authored data, ignoring stored verification labels."""
from .authored_math import verify_formula,verify_visual,verify_solution,result
from .authored_models import AuthoredTeachingPackage,VerificationSummary


def verify_package_math(package):
    package=AuthoredTeachingPackage.model_validate(package.model_dump() if isinstance(package,AuthoredTeachingPackage) else package)
    checks={}
    for formula in package.instructional_formulas:
        checks[formula.ref]=verify_formula(formula.expression,formula.display_expression)
    for block in package.content_blocks:
        if block.visual is not None:checks[block.ref]=verify_visual(block.visual)
    solutions={s.item_ref:s for s in package.solutions}
    for item in (*package.worked_examples,*package.practice_items,*package.learning_checks):
        if item.summary is not None:checks[item.ref]=verify_solution(item.summary,solutions[item.ref],item.question)
        elif item.kind!='concept_check':checks[item.ref]=result({'numerical_summary_present':False})
    passed=bool(checks) and all(v.status=='verified' for v in checks.values())
    return VerificationSummary(mathematical_checks_passed=passed,checks=dict(sorted(checks.items())),
        ready_for_downstream_content_validation=passed and all(r.populated for r in package.coverage_summary.values()))
