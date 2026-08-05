"""Runs the five steps in order and returns everything, including the
intermediate results. The app and the evaluation script both call this, so
what gets measured is exactly what gets demonstrated.
"""

import time
from . import intake, retrieval, rules as rules_mod, decision as decision_mod, validator


def run(requirement_text, catalogue, matrix, rules_cfg):
    t0 = time.time()
    trace = {"errors": []}

    structured, err = intake.run(requirement_text)
    if err:
        trace["errors"].append(f"Intake failed: {err}")
        return trace
    trace["structured"] = structured

    hits, above_floor, simplification_flags, standard_match = retrieval.search(
        structured, catalogue, matrix
    )
    trace["hits"] = hits
    trace["above_floor"] = above_floor
    trace["simplification_flags"] = simplification_flags
    trace["standard_match_found"] = standard_match

    verdicts, rule_verdict = rules_mod.evaluate(
        structured, simplification_flags, above_floor, standard_match, rules_cfg
    )
    trace["rule_verdicts"] = verdicts
    trace["rule_verdict"] = rule_verdict

    decision, err = decision_mod.run(structured, above_floor, rule_verdict, verdicts)
    if err:
        trace["errors"].append(f"Decision failed: {err}")
        return trace
    trace["decision"] = decision

    trace["validation"] = validator.validate(decision, catalogue, rule_verdict)
    trace["elapsed"] = round(time.time() - t0, 1)
    return trace
