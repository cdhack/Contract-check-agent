from __future__ import annotations
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, field_validator

Severity = Literal["high", "medium", "low"]
Jurisdiction = Literal["Auto", "CN", "JP", "CN-JP"]
ReviewStance = Literal["Auto", "buyer", "seller", "neutral"]
StanceAssessment = Literal["unfavorable", "favorable", "neutral", "uncertain"]
ReviewDepth = Literal["standard", "deep"]

class Party(BaseModel):
    name: str | None = None
    role: str | None = None

class ContractFacts(BaseModel):
    title: str | None = None
    contract_type: str | None = None
    language: Literal["zh", "ja", "bilingual", "unknown"] = "unknown"
    parties: list[Party] = []
    amount: str | None = None
    currency: str | None = None
    payment_terms: str | None = None
    effective_date: str | None = None
    delivery_date: str | None = None
    acceptance_date: str | None = None
    renewal_terms: str | None = None
    termination_terms: str | None = None
    governing_law: str | None = None
    dispute_resolution: str | None = None
    language_priority: str | None = None
    clause_summaries: list[str] = []
    focus_topics: list[str] = []

class ComparisonItem(BaseModel):
    chinese_location: str | None = None
    chinese_text: str | None = None
    japanese_location: str | None = None
    japanese_text: str | None = None
    comparison_type: Literal["consistent", "missing", "numeric_conflict", "semantic_difference", "obligation_strength_difference"]
    explanation: str
    severity: Severity
    recommendation: str
    stance_assessment: StanceAssessment = "uncertain"
    stance_reason: str = ""

class KnowledgeChunk(BaseModel):
    chunk_id: str
    source_id: str
    title: str
    jurisdiction: str
    section: str
    source_url: str
    text: str

class KnowledgeSource(BaseModel):
    source_id: str
    title: str
    jurisdiction: Literal["CN", "JP", "CN-JP"]
    source_url: str
    effective_date: str
    document_type: str
    path: str
    enabled: bool = True
    preview: str
    content_length: int
    uploaded: bool = False
    can_delete: bool = False

class KnowledgeSourceUpdate(BaseModel):
    title: str | None = None
    jurisdiction: Literal["CN", "JP", "CN-JP"] | None = None
    source_url: str | None = None
    effective_date: str | None = None
    document_type: str | None = None
    enabled: bool | None = None

class ToolCallRecord(BaseModel):
    query: str
    jurisdiction: str
    results: list[KnowledgeChunk]

class ReviewIssue(BaseModel):
    title: str
    severity: Severity
    category: str
    contract_location: str
    contract_excerpt: str
    issue: str
    impact: str
    recommendation: str
    suggested_clause: str | None = None
    basis_chunk_ids: list[str] = []
    stance_assessment: StanceAssessment = "uncertain"
    stance_reason: str = ""

class ReviewResult(BaseModel):
    issues: list[ReviewIssue] = []
    missing_clauses: list[str] = []
    overall_summary: str = ""

class ParsedContract(BaseModel):
    filename: str
    text: str
    locations: list[str] = []

class ReviewResponse(BaseModel):
    review_id: str
    created_at: datetime | None = None
    stance: ReviewStance = "Auto"
    depth: ReviewDepth = "standard"
    contract: ParsedContract
    facts: ContractFacts
    comparison: list[ComparisonItem] = []
    comparison_skipped: bool = False
    tool_calls: list[ToolCallRecord] = []
    review: ReviewResult
    report_markdown: str

class ReviewHistoryItem(BaseModel):
    review_id: str
    created_at: datetime
    filename: str
    title: str | None = None
    language: str
    stance: ReviewStance = "Auto"
    depth: ReviewDepth = "standard"
    issue_count: int
    high_risk_count: int

class AskSelectionRequest(BaseModel):
    review_id: str
    selected_text: str = Field(min_length=1, max_length=12000)
    task: str
    question: str | None = None
    jurisdiction: Jurisdiction = "Auto"

class AskSelectionResponse(BaseModel):
    selected_text: str
    task: str
    answer: str
    model: str
    prompt: str

class VerifyRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=12000)

class VerificationResult(BaseModel):
    conclusion: str
    basis: list[str] = []
    recommendations: list[str] = []
    suggested_text: str | None = None

class VerifyResponse(BaseModel):
    prompt: str
    result: VerificationResult
