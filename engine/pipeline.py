"""Runs the five steps in order.

`run_streaming` yields after each step so the UI can paint as it goes. The
work takes the same time either way, but a screen that fills in stages feels
far faster than one that sits on a spinner and then dumps everything at once.

`run` is the blocking version, used by the evaluation script.
"""

import time
from . import intake, retrieval, rules as rules_mod, decision as decision_mod, validator


def run_streaming(requirement_text, catalogue, matrix, rules_cfg):
    t0 = time.time()
    trace = {"errors": []}

    structured, err = intake.run(requirement_text)
    if err:
        trace["errors"].append(f"Intake failed: {err}")
        yield "done", trace
        return
    trace["structured"] = structured
    yield "structured", trace

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
    yield "retrieval_and_rules", trace

    decision, err = decision_mod.run(structured, above_floor, rule_verdict, verdicts)
    if err:
        trace["errors"].append(f"Decision failed: {err}")
        yield "done", trace
        return
    trace["decision"] = decision
    trace["validation"] = validator.validate(decision, catalogue, rule_verdict)
    trace["elapsed"] = round(time.time() - t0, 1)
    yield "done", trace


def run(requirement_text, catalogue, matrix, rules_cfg):
    trace = {}
    for _, trace in run_streaming(requirement_text, catalogue, matrix, rules_cfg):
        pass
    return trace
