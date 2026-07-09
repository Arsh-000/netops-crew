import os
from openai import OpenAI
from schemas import Diagnosis, IncidentReport
from audit_log import log_event

MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You draft concise, professional network incident tickets
for a NOC team. Given a diagnosis, write a short ticket title and a body
(3-5 sentences) covering: what's wrong, likely root cause, confidence level,
and recommended next action. Do not claim any fix has been applied — this
ticket is for human review before any change is made."""


def _make_client():
    return OpenAI(
        api_key=os.environ.get("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1",
    )


def draft_report(diagnosis: Diagnosis, client=None) -> IncidentReport:
    client = client or _make_client()
    prompt = (
        f"Interface: {diagnosis.incident.interface}\n"
        f"Root cause: {diagnosis.root_cause}\n"
        f"Confidence: {diagnosis.confidence}\n"
        f"Recommended action: {diagnosis.recommended_action}\n\n"
        "Draft the ticket now. First line = title, then a blank line, then the body."
    )
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    text = response.choices[0].message.content
    title, _, body = text.partition("\n\n")

    report = IncidentReport(diagnosis=diagnosis, ticket_title=title.strip(), ticket_body=body.strip())
    log_event("reporting_agent", "report_drafted", {"title": report.ticket_title})
    return report