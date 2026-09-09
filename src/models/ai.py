from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CausalityLevel(str, Enum):
    OBSERVED = "OBSERVED"
    CORRELATED = "CORRELATED"
    LIKELY_CAUSAL = "LIKELY_CAUSAL"
    HYPOTHESIS = "HYPOTHESIS"
    UNKNOWN = "UNKNOWN"


class LLMExecutionMode(str, Enum):
    LIVE_LLM = "LIVE_LLM"
    EXPLICIT_MOCK = "EXPLICIT_MOCK"
    FALLBACK_DETERMINISTIC = "FALLBACK_DETERMINISTIC"


class LLMStatus(BaseModel):
    mode: LLMExecutionMode
    model_name: str
    latency_ms: float
    fallback_reason: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None


class DeterministicRCACandidate(BaseModel):
    """Rule-generated RCA candidate produced deterministically before LLM invocation."""
    candidate_id: str
    primary_hypothesis: str
    causality_level: CausalityLevel
    confidence_score: float = Field(ge=0.0, le=1.0)
    supporting_anomaly_ids: List[str]
    inferred_mechanisms: List[str]
    rule_signature: str


class RemediationItem(BaseModel):
    action: str
    priority: str = Field(description="IMMEDIATE, SHORT_TERM, LONG_TERM")
    rationale: str
    risk: str = "LOW"


class StructuredRCAResult(BaseModel):
    root_cause_summary: str
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_reason: str
    causality_assessment: CausalityLevel
    observed_facts: List[str]
    inferred_mechanisms: List[str]
    symptoms: List[str]
    operational_impact: str
    business_impact: str = Field(
        default="Business impact cannot be quantified from available technical log telemetry without business metrics."
    )
    immediate_remediation: List[RemediationItem]
    preventative_remediation: List[RemediationItem]
    uncertainties: List[str]
    additional_telemetry_required: List[str]
    deterministic_candidate: Optional[DeterministicRCACandidate] = None
    llm_status: LLMStatus
