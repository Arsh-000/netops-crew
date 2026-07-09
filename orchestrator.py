from openai import OpenAI
import os
import monitor_agent
import diagnostic_agent
import reporting_agent
from audit_log import log_event


def _make_client():
    return OpenAI(
        api_key=os.environ.get("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1",
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
    device.inject_random_fault()
    run_netops_pipeline()