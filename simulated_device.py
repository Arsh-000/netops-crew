"""
simulated_device.py — a small, self-contained fake network device that can
randomly develop a fault. This is a deliberate design choice: unlike
NetSentry/ConfigGuard, NetOps Crew doesn't depend on a real sandbox being
reachable, which makes it fully demoable offline, on demand, in an interview.
"""

import random

_STATE = {
    "interfaces": {
        "GigabitEthernet1": {"status": "up", "errors": 0, "input_rate_mbps": 120},
        "GigabitEthernet2": {"status": "up", "errors": 0, "input_rate_mbps": 80},
        "GigabitEthernet3": {"status": "up", "errors": 0, "input_rate_mbps": 10},
    },
    "recent_config_changes": [],
}

FAULT_SCENARIOS = [
    {
        "interface": "GigabitEthernet2",
        "change": lambda: _STATE["interfaces"]["GigabitEthernet2"].update({"status": "down"}),
        "config_note": "interface GigabitEthernet2 shutdown  (applied 14 min ago by user 'jdoe')",
    },
    {
        "interface": "GigabitEthernet3",
        "change": lambda: _STATE["interfaces"]["GigabitEthernet3"].update({"errors": 4821}),
        "config_note": "duplex mismatch suspected — no recent config change logged",
    },
]


def inject_random_fault():
    """Simulates something going wrong on the network, for demo purposes."""
    scenario = random.choice(FAULT_SCENARIOS)
    scenario["change"]()
    if "config_note" in scenario:
        _STATE["recent_config_changes"].append(scenario["config_note"])
    return scenario["interface"]


def get_interface_status(interface: str = None):
    if interface:
        return {interface: _STATE["interfaces"].get(interface, "unknown interface")}
    return _STATE["interfaces"]


def get_recent_config_changes():
    return _STATE["recent_config_changes"] or ["No recent config changes logged."]


def reset():
    for iface in _STATE["interfaces"].values():
        iface.update({"status": "up", "errors": 0})
    _STATE["recent_config_changes"].clear()
