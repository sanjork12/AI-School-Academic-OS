from typing import Literal

from pydantic import BaseModel, Field


# ============================================================
# Canonical Learning Objective
# ============================================================

class CanonicalLearningObjective(BaseModel):

    canonical_id: str

    subject_domain: str

    skill_name: str

    description: str | None = None

    status: Literal[
        "draft",
        "reviewed",
        "approved",
    ] = "draft"


# ============================================================
# Official -> Canonical Mapping
# ============================================================

class OfficialToCanonicalMapping(BaseModel):

    official_source_id: str

    canonical_id: str

    relationship: Literal[
        "equivalent",
        "broader",
        "narrower",
        "partial",
    ]

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    mapping_method: Literal[
        "human",
        "ai",
        "rule",
    ]

    review_status: Literal[
        "pending",
        "approved",
        "rejected",
    ] = "pending"


# ============================================================
# AI Canonical Mapping Proposal
# ============================================================

class AICanonicalMappingProposal(BaseModel):

    official_source_id: str

    proposed_canonical_id: str

    action: Literal[
        "map_existing",
        "create_new",
    ]

    relationship: Literal[
        "equivalent",
        "broader",
        "narrower",
        "partial",
    ]

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    reasoning: str

    proposed_subject_domain: str | None = None

    proposed_skill_name: str | None = None

    proposed_description: str | None = None

    review_status: Literal[
        "pending",
        "approved",
        "rejected",
    ] = "pending"


# ============================================================
# Canonical Consolidation Proposal
# ============================================================

class CanonicalConsolidationProposal(BaseModel):

    source_canonical_ids: list[str]

    recommended_canonical_id: str

    action: Literal[
        "keep_separate",
        "merge",
    ]

    skill_name: str

    description: str

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    reasoning: str

    review_status: Literal[
        "pending",
        "approved",
        "rejected",
    ] = "pending"


# ============================================================
# Canonical Scope Metadata
# ============================================================

class CanonicalScopeMetadata(BaseModel):

    official_source_id: str

    canonical_id: str

    tier_source: Literal[
        "Foundation",
        "Higher",
    ]

    tier_applicability: list[
        Literal[
            "Foundation",
            "Higher",
        ]
    ] = Field(
        default_factory=list
    )

    scope_description: str | None = None

    constraints: list[str] = Field(
        default_factory=list
    )

    metadata_method: Literal[
        "human",
        "ai",
        "rule",
    ]

    review_status: Literal[
        "pending",
        "approved",
        "rejected",
    ] = "pending"


# ============================================================
# Human Review Decision
# ============================================================

class CanonicalReviewDecision(BaseModel):

    decision_id: str

    proposal_type: Literal[
        "mapping",
        "consolidation",
    ]

    source_ids: list[str] = Field(
        default_factory=list
    )

    decision: Literal[
        "approve",
        "reject",
        "modify",
    ]

    approved_canonical_id: str | None = None

    approved_subject_domain: str | None = None

    approved_skill_name: str | None = None

    approved_description: str | None = None

    approved_official_mappings: list[
        OfficialToCanonicalMapping
    ] = Field(
        default_factory=list
    )

    reviewer_notes: str | None = None

    reviewed_by: str = "human"
