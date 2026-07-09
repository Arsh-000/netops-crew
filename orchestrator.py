"""
orchestrator.py — the "manager" agent in the Orchestrator/Manager multi-agent
pattern. It doesn't do any diagnostic reasoning itself — it just sequences
the three specialists and passes state (Incident -> Diagnosis -> IncidentReport)
between them, exactly like the sequential pipeline pattern in the prep guide.

Guardrail: the final report is only ever printed/logged for human review.
Nothing here files a real ticket or sends a real notification automatically.
"""

from openai import OpenAI
import os
import monitor_agent
import diagnostic_agent
import reporting_agent
from audit_log import log_event


def _make_client():
    return OpenAI(
        api_key=os.environ.get("XAI_API_KEY"),
        base_url="https://api.x.ai/v1",
    )


def run_netops_pipeline(client=None):
    client = client or _make_client()
    incidents = monitor_agent.scan_for_incidents()

    if not incidents:
        print("NetOps Crew: no incidents detected. All interfaces nominal.")
        return []

    reports = []
    for incident in incidents:
        print(f"\n[Monitor] Incident detected on {incident.interface}")
        diagnosis = diagnostic_agent.diagnose(incident, client=client)
        print(f"[Diagnostic] Root cause: {diagnosis.root_cause} (confidence: {diagnosis.confidence})")

        report = reporting_agent.draft_report(diagnosis, client=client)
        print(f"[Reporting] Drafted ticket: {report.ticket_title}")
        print(f"--- AWAITING HUMAN APPROVAL BEFORE FILING ---\n{report.ticket_body}\n")

        log_event("orchestrator", "pipeline_complete_for_incident", {"interface": incident.interface})
        reports.append(report)

    return reports


if __name__ == "__main__":
    import simulated_device as device
    device.reset()
    device.inject_random_fault()  # simulate something going wrong, for the demo
    run_netops_pipeline()
