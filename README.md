# NetOps Crew — Multi-Agent Network Incident Response Orchestrator

A genuine multi-agent pipeline (not a single agent doing everything): a
Monitor agent detects an anomaly, hands off to a Diagnostic agent, which
hands off to a Reporting agent that drafts an incident ticket — coordinated
by an orchestrator, following the Orchestrator/Manager + Sequential Pipeline
patterns.

## Architecture
```
simulated_device.py (self-contained fake network device — fully offline-demoable)
        │
        ▼
monitor_agent.py   — deterministic anomaly detection (NOT an LLM call)
        │  Incident
        ▼
diagnostic_agent.py — ReAct loop: investigates, produces a Diagnosis
        │  Diagnosis
        ▼
reporting_agent.py — single LLM call: drafts an IncidentReport (ticket text)
        │
        ▼
orchestrator.py — sequences all three, prints ticket, awaits human approval
                   before anything would be filed/sent for real
```

## Why this project is distinct from a single-agent diagnostics tool
The interesting engineering decisions here are about **when to use what**:
- **Monitor agent is plain deterministic code, not an LLM** — anomaly
  detection here is well-defined (status != up, errors > threshold), so an
  LLM would add cost/latency/unpredictability for zero benefit.
- **Diagnostic agent is a full ReAct loop** — because root-causing a fault
  genuinely benefits from multi-step investigation and reasoning over
  ambiguous evidence.
- **Reporting agent is a single LLM call, not a loop** — drafting a ticket
  from an already-complete diagnosis is a formatting/writing task with no
  need for tool use or multi-step reasoning; wrapping it in a full agent
  loop would be over-engineering.

This "match the architecture to the actual complexity of the sub-task"
judgment is exactly the kind of reasoning a product-engineering interview
is trying to surface — it's a much stronger story than "I used an agent for
everything."

## Design choice: fully self-contained simulation
Unlike ConfigGuard/NetSentry, this project doesn't depend on a real device
being reachable — `simulated_device.py` is a small, self-contained fake
device that can develop a random fault on demand. This was a deliberate
choice so the whole pipeline can be demoed live, offline, at any time
(useful for an interview, a portfolio, or a CI pipeline) without depending
on external sandbox availability.

## Setup
```bash
pip install -r requirements.txt
export XAI_API_KEY="your-xai-key"

# Validate the full 3-agent handoff logic offline first, no API key needed:
python test_dry_run.py

# Run for real (uses the real xAI Grok API + the simulated device):
python orchestrator.py
```


