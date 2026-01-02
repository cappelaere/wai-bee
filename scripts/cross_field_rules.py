"""
cross_field_rules.py

Cross-field governance validation rules for scholarship configuration.

These rules enforce constraints that cannot be expressed using JSON Schema
alone and MUST be executed after schema validation.

If any rule fails, a ValueError is raised with a clear, human-readable message.
"""

def validate_cross_field_constraints(config: dict):
    errors = []

    # ------------------------------------------------------------
    # Rule 1: Aggregation weights must sum to 1.0
    # ------------------------------------------------------------
    weights = config.get("aggregation", {}).get("weights", {})
    total_weight = sum(weights.values())

    if abs(total_weight - 1.0) > 1e-6:
        errors.append(
            f"Aggregation weights must sum to 1.0 (found {total_weight})"
        )

    # ------------------------------------------------------------
    # Rule 2: Weights may only reference enabled artifacts
    # ------------------------------------------------------------
    artifacts = config.get("artifacts", {})
    enabled_artifacts = {
        name for name, cfg in artifacts.items()
        if cfg.get("enabled", False)
    }

    for artifact in weights.keys():
        if artifact not in enabled_artifacts:
            errors.append(
                f"Weight defined for disabled or unknown artifact: '{artifact}'"
            )

    # ------------------------------------------------------------
    # Rule 3: Enabled artifacts must have submission requirements
    # ------------------------------------------------------------
    submission = config.get("scholarship", {}).get("submission_requirements", {})

    for artifact in enabled_artifacts:
        if artifact == "application":
            continue  # application form is implicit
        if artifact == "attachment":
            continue  # attachment is preprocessing, not a submission requirement

        if artifact not in submission:
            errors.append(
                f"Enabled artifact '{artifact}' has no submission_requirements defined"
            )
        else:
            if not submission[artifact].get("required", False):
                errors.append(
                    f"Enabled artifact '{artifact}' must be marked as required "
                    f"in submission_requirements"
                )

    # ------------------------------------------------------------
    # Rule 4: Recommendation-specific constraints
    # ------------------------------------------------------------
    if "recommendation" in enabled_artifacts:
        rec_cfg = submission.get("recommendation", {})
        count = rec_cfg.get("count", 0)

        if count < 1:
            errors.append(
                "Recommendation artifact enabled but recommendation.count < 1"
            )

    # ------------------------------------------------------------
    # Rule 5: Essay-specific constraints
    # ------------------------------------------------------------
    if "essay" in enabled_artifacts:
        essay_cfg = submission.get("essay", {})
        if essay_cfg.get("max_words", 0) <= 0:
            errors.append(
                "Essay artifact enabled but essay.max_words is not valid"
            )

    # ------------------------------------------------------------
    # Rule 6: Locked configuration immutability (placeholder)
    # ------------------------------------------------------------
    status = config.get("scholarship", {}).get("status")

    if status == "locked":
        # NOTE:
        # In a full implementation, this would compare the current config
        # to a previously stored baseline hash or canonical version.
        # This hook is intentionally present for future enforcement.
        pass

    # ------------------------------------------------------------
    # Final decision
    # ------------------------------------------------------------
    if errors:
        raise ValueError("Cross-field validation failed:\n- " + "\n- ".join(errors))
