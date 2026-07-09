"""
reporting_agent.py — deliberately a SINGLE LLM call, not a ReAct loop.
Drafting a ticket from an already-complete diagnosis doesn't require tool
use or multi-step reasoning — it's a formatting/writing task. Using a full
agent loop here would be over-engineering. This mirrors the same judgment
call as the Crest project: not every LLM step needs to be "agentic."
"""

from anthropic import Anthropic
from schemas import Diagnosis, IncidentReport
from audit_log import log_event

SYSTEM_PROMPT = """You draft concise, professional network incident tickets
for a NOC team. Given a diagnosis, write a short ticket title and a body
(3-5 sentences) covering: what's wrong, likely root cause, confidence level,
and recommended next action. Do not claim any fix has been applied — this
ticket is for human review before any change is made."""


def draft_report(diagnosis: Diagnosis, client: Anthropic = None) -> IncidentReport:
    client = client or Anthropic()
    prompt = (
        f"Interface: {diagnosis.incident.interface}\n"
        f"Root cause: {diagnosis.root_cause}\n"
        f"Confidence: {diagnosis.confidence}\n"
        f"Recommended action: {diagnosis.recommended_action}\n\n"
        "Draft the ticket now. First line = title, then a blank line, then the body."
    )
    response = client.messages.create(
        model="claude-sonnet-4-6", max_tokens=400,
        system=SYSTEM_PROMPT, messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in response.content if b.type == "text")
    title, _, body = text.partition("\n\n")

    report = IncidentReport(diagnosis=diagnosis, ticket_title=title.strip(), ticket_body=body.strip())
    log_event("reporting_agent", "report_drafted", {"title": report.ticket_title})
    return report
