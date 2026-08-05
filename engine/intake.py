"""Step one. Free text in, structured requirement out.

The important behaviour here is what happens with missing information. The
model is told to leave a field null rather than guess, and to list what it
could not determine. Most bad tier decisions come from a requirement that
never said whether the audience was internal or external, and guessing that
silently is how you end up building the wrong thing confidently.
"""

from .schemas import StructuredRequirement
from .llm import generate_json

PROMPT = """You are an experienced SAP business analyst reading a change request.

Turn the request below into a structured requirement. Do not solve it. Do not
recommend how to build it. Only describe what is being asked.

Rules:
- If the request does not state something, set that field to null. Never guess.
- Anything you had to leave null, and that would change how this gets built,
  goes in open_questions.
- business_objects should use SAP business object names where you can identify
  them: PurchaseOrder, PurchaseRequisition, MaterialDocument, Product,
  ProductPlant, Supplier, MaterialStock, PhysicalInventoryDocument.
- external_consumer is true only if someone outside the company sees the output.
  An employee using Fiori is not an external consumer.
- external_data is true only if the requirement needs data that does not live
  in SAP.
- needs_custom_ui is true only if a new screen is required. Adding a field to
  an existing SAP screen is not a new screen.
- blocks_transaction is true only if the requirement must stop a posting or
  save from completing.
- field_only is true only if the entire ask is storing extra data, with no
  logic, no notification and no new screen.
- If the request bundles several asks, describe the whole thing. Do not answer
  only the first part.

Return JSON with exactly these keys:
summary, business_objects, trigger, action_type, external_consumer,
external_data, needs_custom_ui, blocks_transaction, field_only, open_questions

action_type must be one of: read, create, update, validate, notify, approve, unknown

Change request:
---
{requirement_text}
---
"""


def run(requirement_text: str):
    prompt = PROMPT.format(requirement_text=requirement_text)
    return generate_json(prompt, StructuredRequirement)
