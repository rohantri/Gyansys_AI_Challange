"""Step four. The model writes the recommendation.

It gets the structured requirement, what retrieval found, and what the rules
said. It is told plainly that it may only cite ids from the list it was given.
That instruction is not the safeguard on its own. The safeguard is the
validator that runs afterwards and deletes anything invented.
"""

from .schemas import Decision
from .llm import generate_json

PROMPT = """You are a senior SAP S/4HANA architect deciding how a change should be built.

Choose one tier:
- standard: SAP already does this, build nothing
- configuration: set up via IMG or a Fiori config app, no code
- key_user: business user adds a field or restricted logic, no developer
- developer_in_app: ABAP developer extension inside S/4HANA using released objects
- side_by_side: separate app on BTP consuming released APIs
- escalate: no clean path exists, an architect must decide

Hard rules:
- You may only cite ids that appear in the candidate list below. Never invent an
  id, a BAdI name, an API name or a CDS view name. If nothing in the list
  supports your answer, choose escalate with empty citations.
- If the rule engine returned a decisive verdict and you disagree, you may still
  give your own answer, but say plainly in your reasoning why you disagree.
- If a simplification item was flagged, mention it in your reasoning regardless
  of which tier you choose.
- Give at least two rejected alternatives with a real reason each. "Not
  applicable" is not a reason.
- confidence is low if the requirement left important things unstated.

Structured requirement:
{structured}

Open questions the analyst could not answer:
{open_questions}

Candidate catalogue entries (the only ids you may cite):
{candidates}

Rule engine verdict: {rule_verdict}
Rule engine reasons:
{rule_reasons}

Return JSON with exactly these keys:
recommended_tier, reasoning, citations, rejected_alternatives, confidence

rejected_alternatives is a list of objects with keys: tier, reason
"""


def run(structured, above_floor, rule_verdict, rule_verdicts):
    candidates = "\n".join(
        f"- {h['id']} | tier={h['tier']} | {h['name']} | {h['capability']}"
        for h in above_floor
    ) or "- (nothing above the similarity floor)"

    rule_reasons = "\n".join(f"- {v.rule_id}: {v.reason}" for v in rule_verdicts) or "- none"
    open_questions = "\n".join(f"- {q}" for q in structured.open_questions) or "- none"

    prompt = PROMPT.format(
        structured=structured.model_dump_json(indent=2),
        open_questions=open_questions,
        candidates=candidates,
        rule_verdict=rule_verdict,
        rule_reasons=rule_reasons,
    )
    return generate_json(prompt, Decision, temperature=0.2)
