"""Contracts between the model and the rest of the app.

Every model response is parsed through these. If the model returns something
that does not fit, we retry once and then fail loudly rather than passing
malformed data downstream.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class StructuredRequirement(BaseModel):
    """What the intake step turns free text into."""

    summary: str = Field(description="One sentence restatement of the ask")
    business_objects: List[str] = Field(
        default_factory=list,
        description="SAP business objects touched, e.g. PurchaseOrder, MaterialDocument",
    )
    trigger: str = Field(default="", description="What sets this off")
    action_type: str = Field(
        default="unknown",
        description="One of: read, create, update, validate, notify, approve, unknown",
    )
    external_consumer: Optional[bool] = Field(
        default=None, description="Does anyone outside the company see the output"
    )
    external_data: Optional[bool] = Field(
        default=None, description="Does this need data that does not live in SAP"
    )
    needs_custom_ui: Optional[bool] = Field(
        default=None, description="Is a new screen required, beyond standard SAP screens"
    )
    blocks_transaction: bool = Field(
        default=False, description="Must this stop a posting or save from completing"
    )
    field_only: bool = Field(
        default=False, description="Is the entire ask just storing extra data"
    )
    open_questions: List[str] = Field(
        default_factory=list,
        description="Facts the requirement did not state that change the answer",
    )


class RejectedAlternative(BaseModel):
    tier: str
    reason: str


class Decision(BaseModel):
    """What the decision step produces, before validation."""

    recommended_tier: str
    reasoning: str
    citations: List[str] = Field(
        default_factory=list, description="Catalogue ids that justify this"
    )
    rejected_alternatives: List[RejectedAlternative] = Field(default_factory=list)
    confidence: str = Field(default="medium", description="high, medium or low")


class RuleVerdict(BaseModel):
    rule_id: str
    verdict: str
    severity: str
    reason: str


TIER_LABELS = {
    "standard": "Standard — build nothing",
    "configuration": "Configuration — no code",
    "key_user": "Key user extension",
    "developer_in_app": "Developer extension inside S/4HANA",
    "side_by_side": "Side-by-side app on BTP",
    "modification": "Modification — not permitted",
    "escalate": "Escalate to architect",
}
