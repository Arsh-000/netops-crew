"""
diagnostic_agent.py — the ReAct-style specialist agent in the pipeline.
Uses xAI's Grok API via the OpenAI-compatible client. Takes an Incident
handed off from monitor_agent, investigates using its own tools (querying
the simulated device for more detail), and produces a Diagnosis object
handed off to reporting_agent. This is the "specialist worker" in the
orchestrator/manager multi-agent pattern.
"""

import json
import os
from openai import OpenAI
from schemas import Incident, Diagnosis, InterfaceQueryInput, ConfigHistoryInput
import simulated_device as device
from audit_log import log_event

MAX_ITERATIONS = 6
MODEL = "grok-4-fast"

TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "get_interface_status",
            "description": "Get current status/error count for a specific interface.",
            "parameters": InterfaceQueryInput.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_config_changes",
            "description": "Get a log of recent configuration changes on the device.",
            "parameters": ConfigHistoryInput.model_json_schema(),
        },
    },
]

SYSTEM_PROMPT = """You are a network diagnostic specialist agent. You've been
handed an incident (an interface with a problem). Investigate using your
tools, then respond with a final plain-text diagnosis in exactly this format:
ROOT_CAUSE: <one sentence>
CONFIDENCE: <low|medium|high>
RECOMMENDED_ACTION: <one sentence, the specific fix>
Do not call more tools once you have enough information to answer."""


def _make_client():
    return OpenAI(
        api_key=os.environ.get("XAI_API_KEY"),
        base_url="https://api.x.ai/v1",
    )


def _tool_dispatch(name, args):
    if name == "get_interface_status":
        return device.get_interface_status(args.get("interface"))
    elif name == "get_recent_config_changes":
        return device.get_recent_config_changes()
    return f"Unknown tool: {name}"


def diagnose(incident: Incident, client=None) -> Diagnosis:
    client = client or _make_client()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Incident: interface {incident.interface} reported status {incident.raw_status}. Investigate and diagnose."},
    ]

    final_text = None
    for _ in range(MAX_ITERATIONS):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOL_SPECS,
        )
        message = response.choices[0].message
        messages.append(message.model_dump(exclude_none=True) if hasattr(message, "model_dump") else message)

        if not getattr(message, "tool_calls", None):
            final_text = message.content
            break

        for call in message.tool_calls:
            args = json.loads(call.function.arguments)
            result = _tool_dispatch(call.function.name, args)
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": str(result),
            })

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
