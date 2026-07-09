"""
diagnostic_agent.py — the ReAct-style specialist agent in the pipeline.
Takes an Incident handed off from monitor_agent, investigates using its own
tools (querying the simulated device for more detail), and produces a
Diagnosis object handed off to reporting_agent. This is the "specialist
worker" in the orchestrator/manager multi-agent pattern.
"""

import json
from anthropic import Anthropic
from schemas import Incident, Diagnosis, InterfaceQueryInput, ConfigHistoryInput
import simulated_device as device
from audit_log import log_event

MAX_ITERATIONS = 6

TOOL_SPECS = [
    {
        "name": "get_interface_status",
        "description": "Get current status/error count for a specific interface.",
        "input_schema": InterfaceQueryInput.model_json_schema(),
    },
    {
        "name": "get_recent_config_changes",
        "description": "Get a log of recent configuration changes on the device.",
        "input_schema": ConfigHistoryInput.model_json_schema(),
    },
]

SYSTEM_PROMPT = """You are a network diagnostic specialist agent. You've been
handed an incident (an interface with a problem). Investigate using your
tools, then respond with a final plain-text diagnosis in exactly this format:
ROOT_CAUSE: <one sentence>
CONFIDENCE: <low|medium|high>
RECOMMENDED_ACTION: <one sentence, the specific fix>
Do not call more tools once you have enough information to answer."""


def _tool_dispatch(name, args):
    if name == "get_interface_status":
        return device.get_interface_status(args.get("interface"))
    elif name == "get_recent_config_changes":
        return device.get_recent_config_changes()
    return f"Unknown tool: {name}"


def diagnose(incident: Incident, client: Anthropic = None) -> Diagnosis:
    client = client or Anthropic()
    messages = [{
        "role": "user",
        "content": f"Incident: interface {incident.interface} reported status {incident.raw_status}. Investigate and diagnose."
    }]

    final_text = None
    for _ in range(MAX_ITERATIONS):
        response = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=500,
            system=SYSTEM_PROMPT, tools=TOOL_SPECS, messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})
        tool_uses = [b for b in response.content if b.type == "tool_use"]
        if not tool_uses:
            final_text = "".join(b.text for b in response.content if b.type == "text")
            break
        results = []
        for block in tool_uses:
            result = _tool_dispatch(block.name, block.input)
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(result)})
        messages.append({"role": "user", "content": results})

    root_cause, confidence, action = _parse_diagnosis_text(final_text or "")
    diagnosis = Diagnosis(incident=incident, root_cause=root_cause,
                           confidence=confidence, recommended_action=action)
    log_event("diagnostic_agent", "diagnosis_complete", diagnosis.model_dump())
    return diagnosis


def _parse_diagnosis_text(text: str):
    root_cause = confidence = action = "unknown"
    for line in text.splitlines():
        if line.startswith("ROOT_CAUSE:"):
            root_cause = line.split(":", 1)[1].strip()
        elif line.startswith("CONFIDENCE:"):
            confidence = line.split(":", 1)[1].strip()
        elif line.startswith("RECOMMENDED_ACTION:"):
            action = line.split(":", 1)[1].strip()
    return root_cause, confidence, action
