"""
monitor_agent.py — deliberately NOT an LLM agent. Anomaly detection here is
simple, well-defined logic (is status != 'up'? are errors above a threshold?)
— exactly the kind of task that should stay deterministic code rather than
an LLM call. This is a good design point to raise in the interview: knowing
when NOT to use an LLM is as important as knowing when to use one.
"""

from schemas import Incident
import simulated_device as device
from audit_log import log_event

ERROR_THRESHOLD = 100


def scan_for_incidents():
    incidents = []
    statuses = device.get_interface_status()
    for iface, info in statuses.items():
        if info["status"] != "up":
            incidents.append(Incident(interface=iface, raw_status=info))
        elif info.get("errors", 0) > ERROR_THRESHOLD:
            incidents.append(Incident(interface=iface, raw_status=info))
    log_event("monitor_agent", "scan_complete", {"incidents_found": len(incidents)})
    return incidents
