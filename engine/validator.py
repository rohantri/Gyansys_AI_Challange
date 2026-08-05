"""Step five. Delete anything the model invented.

No model runs here. Every id the model cited is checked against the real
catalogue. Unknown ids are stripped. If stripping leaves the recommendation
without support, the decision drops to escalate.

This exists because the characteristic failure of a language model is
inventing something that sounds exactly right. A made-up BAdI reads perfectly
to a junior developer, who builds on it and finds out three days later that it
was never real. The model is not allowed to be the authority on what SAP
offers. It can only point at things that exist.
"""

SELF_SUPPORTING_TIERS = {"escalate", "standard"}


def validate(decision, catalogue, rule_verdict):
    known_ids = {e["id"]: e for e in catalogue["entries"]}

    kept, stripped = [], []
    for cid in decision.citations:
        if cid in known_ids:
            kept.append(cid)
        else:
            stripped.append(cid)

    notes = []
    final_tier = decision.recommended_tier
    downgraded = False

    if stripped:
        notes.append(
            f"Removed {len(stripped)} citation(s) that do not exist in the catalogue: "
            + ", ".join(stripped)
        )

    if not kept and final_tier not in SELF_SUPPORTING_TIERS:
        final_tier = "escalate"
        downgraded = True
        notes.append(
            "No surviving citation supports this recommendation, so it was downgraded "
            "to escalate. The tool will not recommend a build path it cannot evidence."
        )

    # Does the tier of the cited objects actually match the recommended tier?
    tier_mismatch = [
        cid for cid in kept
        if known_ids[cid]["tier"] not in (final_tier, "modification")
        and known_ids[cid]["type"] != "simplification_item"
    ]
    if tier_mismatch and not downgraded:
        notes.append(
            "Cited objects sit at a different tier than the recommendation: "
            + ", ".join(f"{c} ({known_ids[c]['tier']})" for c in tier_mismatch)
            + ". Worth a look."
        )

    disagreement = None
    if rule_verdict != final_tier and not downgraded:
        disagreement = (
            f"The rule engine said {rule_verdict}. The model said {final_tier}. "
            "Both are shown. This is not resolved automatically."
        )

    return {
        "final_tier": final_tier,
        "kept_citations": kept,
        "stripped_citations": stripped,
        "downgraded": downgraded,
        "notes": notes,
        "disagreement": disagreement,
        "citation_valid": len(stripped) == 0,
    }
