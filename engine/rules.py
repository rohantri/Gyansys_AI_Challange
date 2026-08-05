"""Step three. Plain rules, no model.

This is deliberately not AI. An architect who cannot read the logic will not
trust the output, and an architect who does not trust it will overrule it and
go back to deciding from memory. Then the tool has changed nothing.

Blockers are handled in code because they depend on retrieval results. The
rest live in tier_rules.yaml and can be edited without touching Python.
"""

import yaml
from .schemas import RuleVerdict


def load_rules(path: str):
    with open(path) as f:
        return yaml.safe_load(f)


def _matches(condition_list, facts):
    """Every field:value pair in the list must match the requirement facts."""
    for pair in condition_list:
        for field, expected in pair.items():
            if facts.get(field) != expected:
                return False
    return True


def evaluate(structured, simplification_flags, above_floor, standard_match_found, rules_cfg):
    """Returns (verdicts, decisive_verdict)."""

    facts = {
        "external_consumer": structured.external_consumer,
        "external_data": structured.external_data,
        "needs_custom_ui": structured.needs_custom_ui,
        "blocks_transaction": structured.blocks_transaction,
        "field_only": structured.field_only,
        "action_type": structured.action_type,
        "standard_match_found": standard_match_found,
    }

    verdicts = []

    # Blocker one. Objects in this requirement sit on a simplification item.
    if simplification_flags:
        ids = ", ".join(f["id"] for f in simplification_flags)
        verdicts.append(
            RuleVerdict(
                rule_id="BLOCK_SIMPLIFICATION",
                verdict="flag",
                severity="blocker",
                reason=(
                    f"Objects in this requirement appear on simplification items ({ids}). "
                    "Existing custom code may already be broken. Raise this before choosing a tier."
                ),
            )
        )

    # Blocker two. Nothing in the catalogue came close enough.
    non_blocker_hits = [h for h in above_floor if h["type"] != "simplification_item"]
    if not non_blocker_hits:
        verdicts.append(
            RuleVerdict(
                rule_id="BLOCK_NO_RELEASED_PATH",
                verdict="escalate",
                severity="blocker",
                reason=(
                    "No released extension point or standard capability was found for these "
                    "objects above the similarity floor. An architect must decide."
                ),
            )
        )
        return verdicts, "escalate"

    decisive = None
    for rule in rules_cfg["rules"]:
        all_of = rule.get("all_of", [])
        any_of = rule.get("any_of", [])

        fired = False
        if any_of:
            fired = any(_matches([pair], facts) for pair in any_of)
        elif all_of:
            fired = _matches(all_of, facts)
        else:
            fired = True  # DEFAULT_ESCALATE

        if fired:
            verdicts.append(
                RuleVerdict(
                    rule_id=rule["id"],
                    verdict=rule["verdict"],
                    severity=rule["severity"],
                    reason=rule["reason"].strip(),
                )
            )
            if rule["severity"] == "decisive" and decisive is None:
                decisive = rule["verdict"]
                break

    if decisive is None:
        decisive = "escalate"

    return verdicts, decisive
