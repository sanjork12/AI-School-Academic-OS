"""Original Topic 2 structural rules, extracted without changing expected sequences."""
from curriculum_schema import CurriculumTopic
from pydantic import ValidationError

EXPECTED = {
    "foundation": {
        "tier_source": "Foundation",
        "tier_code": "F",
        "topic_code": "2",
        "subtopics": {
            "2.1": ["A", "B", "C", "D"],
            "2.2": ["A", "B", "C", "D", "E", "F"],
            "2.3": ["A", "B", "C", "D", "E", "F"],
            "2.4": ["A", "B"],
            "2.5": [],
            "2.6": ["A"],
            "2.7": ["A"],
            "2.8": ["A", "B", "C", "D", "E"],
        },
    },
    "higher": {
        "tier_source": "Higher",
        "tier_code": "H",
        "topic_code": "2",
        "subtopics": {
            "2.1": ["A"],
            "2.2": ["A", "B", "C", "D", "E"],
            "2.3": ["A"],
            "2.4": [],
            "2.5": ["A"],
            "2.6": ["A", "B"],
            "2.7": ["A", "B", "C", "D"],
            "2.8": ["A", "B"],
        },
    },
}



def validate_curriculum(data, tier):
    if tier not in EXPECTED: raise ValueError("UNSUPPORTED_CURRICULUM_PROFILE")
    try:
        data=CurriculumTopic.model_validate(data).model_dump()
    except ValidationError:
        return dict(status="CURRICULUM_VALIDATION_FAILED",structure_valid=False,errors=["Curriculum schema invalid"],warnings=[],parser_warnings=[],objective_count=0,subtopic_count=0,source_ids_valid=False,validated_source_ids=0,official_text_confirmed=False)
    expected = EXPECTED[tier]
    
    errors = []
    warnings = []
    
    
    # --------------------------------
    # Basic metadata checks
    # --------------------------------
    
    if data.get("exam_board") != "Pearson Edexcel":
        errors.append(
            "exam_board must be 'Pearson Edexcel'."
        )
    
    if data.get("qualification") != "International GCSE":
        errors.append(
            "qualification must be 'International GCSE'."
        )
    
    if data.get("subject") != "Mathematics A":
        errors.append(
            "subject must be 'Mathematics A'."
        )
    
    if data.get("specification_code") != "4MA1":
        errors.append(
            "specification_code must be '4MA1'."
        )
    
    if data.get("tier_source") != expected["tier_source"]:
        errors.append(
            f"tier_source should be "
            f"'{expected['tier_source']}'."
        )
    
    if data.get("topic_code") != expected["topic_code"]:
        errors.append(
            "topic_code should be '2'."
        )
    
    
    # --------------------------------
    # Subtopic / objective checks
    # --------------------------------
    
    subtopics = data.get("subtopics")
    
    if not isinstance(subtopics, list):
        errors.append(
            "subtopics must be a list."
        )
        subtopics = []
    
    
    found_subtopic_codes = []
    all_source_ids = []
    
    
    for subtopic in subtopics:
    
        code = subtopic.get("code")
    
        if not code:
            errors.append(
                "Found subtopic without a code."
            )
            continue
    
        found_subtopic_codes.append(code)
    
        if code not in expected["subtopics"]:
            errors.append(
                f"Unexpected subtopic: {code}"
            )
            continue
    
        objectives = subtopic.get(
            "objectives",
            []
        )
    
        if not isinstance(objectives, list):
            errors.append(
                f"{code}: objectives must be a list."
            )
            continue
    
        found_objective_codes = []
    
        for objective in objectives:
    
            objective_code = objective.get("code")
    
            official_text = objective.get(
                "official_text"
            )
    
            source_id = objective.get(
                "source_id"
            )
    
            if not objective_code:
                errors.append(
                    f"{code}: objective missing code."
                )
                continue
    
            found_objective_codes.append(
                objective_code
            )
    
            if (
                not isinstance(official_text, str)
                or not official_text.strip()
            ):
                errors.append(
                    f"{code}{objective_code}: "
                    f"official_text is empty."
                )
    
            # Validate permanent source ID
    
            expected_source_id = (
                f"EDX-"
                f"{data.get('specification_code')}-"
                f"{expected['tier_code']}-"
                f"{code}-"
                f"{objective_code}"
            )
    
            if not source_id:
                errors.append(
                    f"{code}{objective_code}: "
                    f"source_id is missing."
                )
    
            elif source_id != expected_source_id:
                errors.append(
                    f"{code}{objective_code}: "
                    f"source_id should be "
                    f"'{expected_source_id}', "
                    f"found '{source_id}'."
                )
    
            else:
                all_source_ids.append(
                    source_id
                )
    
        # Duplicate objective codes
    
        if (
            len(found_objective_codes)
            != len(set(found_objective_codes))
        ):
            errors.append(
                f"{code}: duplicate objective codes."
            )
    
        expected_objective_codes = (
            expected["subtopics"][code]
        )
    
        if found_objective_codes != expected_objective_codes:
            errors.append(
                f"{code}: expected objectives "
                f"{expected_objective_codes}, "
                f"found {found_objective_codes}."
            )
    
    
    # --------------------------------
    # Subtopic sequence checks
    # --------------------------------
    
    expected_subtopic_codes = list(
        expected["subtopics"].keys()
    )
    
    if found_subtopic_codes != expected_subtopic_codes:
        errors.append(
            "Subtopic sequence mismatch. "
            f"Expected {expected_subtopic_codes}, "
            f"found {found_subtopic_codes}."
        )
    
    if (
        len(found_subtopic_codes)
        != len(set(found_subtopic_codes))
    ):
        errors.append(
            "Duplicate subtopic codes detected."
        )
    
    
    # --------------------------------
    # Global source ID uniqueness
    # --------------------------------
    
    if (
        len(all_source_ids)
        != len(set(all_source_ids))
    ):
        errors.append(
            "Duplicate source IDs detected."
        )
    
    
    # --------------------------------
    # Special boundary checks
    # --------------------------------
    
    subtopic_lookup = {
        item.get("code"): item
        for item in subtopics
        if item.get("code")
    }
    
    
    if tier == "foundation":
    
        proportion = subtopic_lookup.get("2.5")
    
        if proportion:
    
            if proportion.get("objectives"):
                errors.append(
                    "Foundation 2.5 must not contain "
                    "learning objectives."
                )
    
            notes_text = " ".join(
                proportion.get("notes", [])
            )
    
            if "Higher Tier only" not in notes_text:
                warnings.append(
                    "Foundation 2.5 does not contain "
                    "'Higher Tier only' in notes."
                )
    
    
    if tier == "higher":
    
        linear = subtopic_lookup.get("2.4")
    
        if linear:
    
            if linear.get("objectives"):
                errors.append(
                    "Higher 2.4 should not contain "
                    "directly extracted objectives."
                )
    
            notes_text = " ".join(
                linear.get("notes", [])
            )
    
            if "See Foundation Tier" not in notes_text:
                warnings.append(
                    "Higher 2.4 does not contain "
                    "'See Foundation Tier' in notes."
                )
    
    
    # --------------------------------
    # Parser warnings
    # --------------------------------
    
    parser_warnings = data.get(
        "warnings",
        []
    )
    
    if parser_warnings:
    
        warnings.append(
            f"Parser reported "
            f"{len(parser_warnings)} warning(s)."
        )
    
    
    
    return dict(status="STRUCTURE_VALID" if not errors else "CURRICULUM_VALIDATION_FAILED", structure_valid=not errors, errors=errors, warnings=warnings, parser_warnings=parser_warnings, objective_count=sum(len(s.get("objectives",[])) for s in subtopics), subtopic_count=len(subtopics), source_ids_valid=not any("source_id" in e or "source ID" in e for e in errors), validated_source_ids=len(all_source_ids), official_text_confirmed=False)
