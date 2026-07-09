"""
test_dry_run.py — validates the full monitor -> diagnostic -> reporting
handoff chain without needing a real xAI API key.
"""

import sys
import json

sys.path.insert(0, ".")
import simulated_device as device
import monitor_agent
import diagnostic_agent
import reporting_agent


class FakeFunction:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class FakeToolCall:
    def __init__(self, id_, name, arguments_dict):
        self.id = id_
        self.function = FakeFunction(name, json.dumps(arguments_dict))


class FakeMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls

    def model_dump(self, exclude_none=True):
        d = {"role": "assistant", "content": self.content}
        if self.tool_calls:
            d["tool_calls"] = [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in self.tool_calls
            ]
        return d


class FakeChoice:
    def __init__(self, message):
        self.message = message


class FakeResponse:
    def __init__(self, message):
        self.choices = [FakeChoice(message)]


class FakeDiagnosticCompletions:
    """Simulates the diagnostic agent: one tool call, then a final answer."""
    def __init__(self):
        self.call_count = 0

    def create(self, **kwargs):
        self.call_count += 1
        if self.call_count == 1:
            tool_call = FakeToolCall("d1", "get_recent_config_changes", {})
            return FakeResponse(FakeMessage(content=None, tool_calls=[tool_call]))
        return FakeResponse(FakeMessage(content=(
            "ROOT_CAUSE: Interface was administratively shut down by a recent config change\n"
            "CONFIDENCE: high\n"
            "RECOMMENDED_ACTION: Run 'no shutdown' on the affected interface after confirming with the change owner"
        )))


class FakeReportingCompletions:
    """Simulates the reporting agent: single call producing ticket text."""
    def create(self, **kwargs):
        return FakeResponse(FakeMessage(content=(
            "Interface GigabitEthernet2 administratively down\n\n"
            "Monitoring detected GigabitEthernet2 is down. Diagnostic investigation found it was "
            "administratively shut down by a recent config change, with high confidence. "
            "Recommended action: run 'no shutdown' after confirming with the change owner. "
            "No changes have been applied automatically; this ticket is for review."
        )))


class DiagClient:
    def __init__(self):
        self.chat = type("Chat", (), {"completions": FakeDiagnosticCompletions()})()


class ReportClient:
    def __init__(self):
        self.chat = type("Chat", (), {"completions": FakeReportingCompletions()})()


def main():
    device.reset()
    device.inject_random_fault()

    incidents = monitor_agent.scan_for_incidents()
    assert len(incidents) >= 1, "Monitor agent should have detected the injected fault"
    print(f"✅ Monitor agent detected {len(incidents)} incident(s): {[i.interface for i in incidents]}")

    diagnosis = diagnostic_agent.diagnose(incidents[0], client=DiagClient())
    assert diagnosis.confidence == "high"
    print(f"✅ Diagnostic agent produced diagnosis: {diagnosis.root_cause} (confidence: {diagnosis.confidence})")

    report = reporting_agent.draft_report(diagnosis, client=ReportClient())
    assert "review" in report.ticket_body.lower() or "not" in report.ticket_body.lower()
    print(f"✅ Reporting agent drafted ticket: '{report.ticket_title}'")
    print("\nFull ticket body:\n" + report.ticket_body)

    print("\n✅ Dry run passed: Monitor -> Diagnostic -> Reporting handoff chain works end-to-end with the Grok/OpenAI-style API format.")


if __name__ == "__main__":
    main()
