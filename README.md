# Lab 01 — Wazuh SIEM Home Lab

[![CI](https://github.com/santorest/lab-01-wazuh-siem/actions/workflows/ci.yml/badge.svg)](https://github.com/santorest/lab-01-wazuh-siem/actions/workflows/ci.yml)

Detection-engineering lab for a fictional 40-person company: centralized logging with Wazuh, Windows
telemetry with Sysmon, Linux telemetry with auditd, firewall logs from pfSense, and eight use cases mapped to
MITRE ATT&CK.

**Category:** Threat Detection & SIEM · **Status:** reference design — ready to build ·
**Write-up:** [WRITEUP.md](WRITEUP.md)

![Architecture](diagrams/architecture.svg)

## Lab topology
| Host | OS | Role | IP |
|---|---|---|---|
| wazuh01 | Ubuntu 24.04 | Wazuh indexer + server + dashboard | 10.10.20.10 |
| dc01 | Windows Server 2022 | Domain controller (agent + Sysmon) | 10.10.20.11 |
| srv01 | Ubuntu 24.04 | Linux server (agent + auditd) | 10.10.20.12 |
| ws01 | Windows 11 | Workstation (agent + Sysmon) | 10.10.30.21 |
| fw01 | pfSense CE | Firewall, syslog source | 10.10.99.1 |

All addresses are lab-only. The lab network has no route to production networks.

## Pinned versions
| Component | Version |
|---|---|
| Wazuh (installer, server, agents) | 4.14.8 — installer SHA-256 `9adb693c474317644358fef74e629b0fab782bcb9c1a411e967a8348e3830bc1` |
| Sysmon configuration | [sysmon-modular](https://github.com/olafhartong/sysmon-modular) commit `082cba5` (MIT) |
| Atomic Red Team | commit `388942a` (MIT) · Invoke-AtomicRedTeam v2.3.0 |

## Repository layout
```
configs/
  wazuh/rules/        custom detection rules (local_rules.xml)
  wazuh/decoders/     custom decoders
  agents/windows/     ossec.conf snippets for Windows agents
  agents/linux/       ossec.conf snippets for Linux agents
  sysmon/             Sysmon config reference (upstream + local changes)
scripts/
  deploy/             pinned, checksum-verified Wazuh installer
  simulate/           test runbook (isolated lab only)
  report/             alert metrics export + coverage table for the write-up
tests/
  test-plan.md        detection test matrix
  unit/               tests for the report scripts (run in CI)
  results/            exported results per run
diagrams/             architecture.svg (+ Mermaid source)
screenshots/          sanitized evidence
docs/                 build notes and gotchas
```

## Quick start
1. Build the VMs from the topology table on an isolated network.
2. On wazuh01: `sudo bash scripts/deploy/install-wazuh.sh`.
3. Enroll agents (see `configs/agents/` and the official Wazuh 4.14 docs).
4. Follow `tests/test-plan.md`; export metrics with `scripts/report/export_alert_metrics.py`.
5. Generate the results table: `python scripts/report/coverage_table.py`.

## Development
```bash
python -m pip install -r requirements-dev.txt
python -m pytest
ruff check .
```

> Testing is performed only in an isolated lab environment I own. No real organization's data is included.

## License
[MIT](LICENSE)
