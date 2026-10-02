"""Bounded Standard deviation v1 language checks, not a semantic AI evaluator.

Structured targets, item data and semantic elements are checked elsewhere.
These rules check the remaining prose in the frozen P4A contract.
"""
import re


def normal(text):return ' '.join(str(text or '').lower().replace('’',"'").split())


def actual(text):
    text=normal(text)
    return bool(text) and not re.match(r'^(?:todo\b|tbd\b|placeholder\b|provide\b|add\b|insert\b|explain standard deviation\.?$|worked example\.?$|learning check\.?$)',text)


def meaning(text,units=False):
    text=normal(text)
    # Negated/contradictory meaning never counts just because keywords occur.
    if re.search(r'\b(?:not|never|neither|unrelated|different units)\b',text):return False
    spread=bool(re.search(r'\b(?:spread|dispersion|dispersed)\b',text))
    mean=bool(re.search(r'\b(?:around|about|relative to) (?:the |their )?(?:mean|average)\b',text))
    same_units=bool(re.search(r'\b(?:same units|units of)\b',text) and re.search(r'\b(?:observations|data|values|measurements)\b',text))
    return actual(text) and spread and mean and (same_units or not units)


def method(text):
    text=normal(text)
    text=re.sub(r'students do not need to memori[sz]e (?:it|the formula)\.?','',text)
    if not actual(text) or re.search(r'\b(?:not|never|skip|omit)\b',text):return False
    # Ordered actions, not merely a bag of words. This profile is intentionally
    # conservative; unsupported wording needs review rather than automatic approval.
    patterns=(r'\bmean\b',r'\bdeviation',r'\bsquare\b',r'\b(?:average|mean)\b',r'\bsquare root\b')
    for pattern in patterns:
        match=re.search(pattern,text)
        if not match:return False
        text=text[match.end():]
    return True


RULES={
    'formula_memorisation':r'\b(?:must|shall|need to|required to)\s+(?:be able to\s+)?memori[sz]e|formula.{0,25}memori[sz]ation\s+(?:is\s+)?(?:required|mandatory)',
    'calculator_method':r'\b(?:must|shall|need to|required to).{0,65}(?:calculator|button sequence)|calculator[- ]only|specific calculator.{0,30}(?:required|mandatory)',
    'difficulty':r'\b(?:easy|medium|hard|advanced)[- ]difficulty\b|difficulty\s*(?:is|:|=)\s*(?:easy|medium|hard|advanced)|\b(?:easy|medium|hard|advanced) (?:question|topic|task|lesson)|(?:question|topic|task|lesson) is (?:easy|medium|hard|advanced)',
    'common_mistakes':r'students commonly|common (?:student )?mistakes?|most students confuse|typical misconceptions?',
    'prerequisites':r'must be mastered (?:first|before)|(?:is|as|a) (?:formal )?prerequisite|prerequisite\s*:',
    'frequency':r'frequently tested|commonly tested|high frequency|often appears|rarely appears',
    'typical_marks':r'usually\s+\d+\s+marks|typically (?:worth )?\d+\s+marks',
    'exam_prediction':r'likely to appear|expected next year|will appear.{0,25}exam',
    'unsupported_task_form':r'(?:must|required to|calculate).{0,60}(?:raw data|frequency table|grouped data)|additional task forms? (?:is|are) required',
    'sample_comparison':r'\bn\s*[-−]\s*1\b|(?:compare|comparison of).{0,45}population.{0,30}sample|sample standard deviation (?:uses|requires)',
    'originality_claim':r'(?:this|an|a|original) (?:is )?(?:an? )?(?:pearson|edexcel) (?:past[- ]paper )?question|this (?:exact )?question appeared',
    'concept_contradiction':r'(?:higher|larger) (?:sd|standard deviation).{0,25}(?:higher mean|always bad)|(?:lower|smaller) (?:sd|standard deviation).{0,25}(?:better data|always good)|standard deviation is (?:the )?(?:mean|average)',
}


def boundary_findings(text):
    results=[]
    for clause in re.split(r'[.;\n]|\bbut\b|\bhowever\b|\band\b',normal(text)):
        if re.fullmatch(r'no [a-z ,/-]+ (?:is|are) claimed',clause.strip()):continue
        for code,pattern in RULES.items():
            for match in re.finditer(pattern,clause):
                prefix=clause[:match.start()].strip()
                # Only direct local negation suppresses a match, not an unrelated
                # "no" elsewhere in the same sentence.
                if re.search(r'(?:\bno|\bnot|\bnever|\bwithout)(?: a| an| any| requiring)?$',prefix):continue
                results.append((code,clause.strip()))
    return sorted(set(results))
