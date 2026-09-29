---
title: "Wazuh SIEM Home Lab"
id: "lab-01-wazuh-siem"
category: "Threat Detection & SIEM"
type: "Lab"
status: "draft"
date: "2026-09-29"
time_to_reproduce: "1–2 days to build, plus one week of baseline"
skills: [Wazuh, Sysmon, auditd, pfSense, MITRE ATT&CK, Python, Bash]
frameworks: [MITRE ATT&CK, CIS Controls v8]
repo: "https://github.com/santorest/lab-01-wazuh-siem"
bundle: "Published on the portfolio site with its SHA-256 checksum"
---

# Wazuh SIEM Home Lab

> **TL;DR** — Design and build of a single-node Wazuh SIEM for a fictional 40-person company, collecting
> Windows (Sysmon), Linux (auditd) and firewall telemetry, with eight detection use cases mapped to MITRE
> ATT&CK. **Status: build in progress — lab results are pending and will be published only once measured.**

| | |
|---|---|
| **Role played** | Security engineer for a 40-person company with no SOC |
| **Environment** | Proxmox VE, 5 VMs, isolated lab network (3 VLANs) |
| **Tools** | Wazuh 4.14.8, Sysmon (sysmon-modular), auditd, pfSense CE, Python |
| **Key result** | Pending lab run |

---

## 1. Problem

- **Context:** a fictional 40-person professional-services company runs a Windows domain, a Linux server
  and a perimeter firewall. Logs stay on each machine and nobody reviews them.
- **Why it matters:** credential theft, persistence and privilege abuse would go unnoticed for weeks. The
  company can't afford a commercial SIEM or a 24/7 SOC.
- **Goals:**
    1. Centralise Windows, Linux and firewall telemetry in one open-source SIEM.
    2. Detect 8 attacker behaviours that matter for a company this size, mapped to MITRE ATT&CK.
    3. Keep alert volume low enough for one part-time person to review daily.
    4. Make the whole lab reproducible from this repository.
- **Scope & constraints:** open-source tooling only; evaluation licences for Windows; everything runs in an
  isolated lab with no route to any production network.
- **Success criteria:** every use case has a recorded detection result; daily alert volume measured before
  and after tuning; the build reproducible from the scripts in this repo.

## 2. Architecture

![Architecture diagram](diagrams/architecture.svg)

| Host | OS | Role | IP | Sizing |
|---|---|---|---|---|
| wazuh01 | Ubuntu 24.04 | Wazuh indexer + server + dashboard | 10.10.20.10 | 4 vCPU, 8 GB RAM, 80 GB |
| dc01 | Windows Server 2022 (eval) | Domain controller `lab.local`; agent + Sysmon | 10.10.20.11 | 2 vCPU, 4 GB, 60 GB |
| srv01 | Ubuntu 24.04 | Linux server; agent + auditd | 10.10.20.12 | 1 vCPU, 2 GB, 20 GB |
| ws01 | Windows 11 (eval) | Domain-joined workstation; agent + Sysmon | 10.10.30.21 | 2 vCPU, 4 GB, 60 GB |
| fw01 | pfSense CE | Inter-VLAN firewall; syslog to wazuh01 | 10.10.99.1 | 1 vCPU, 1 GB, 16 GB |

- **Data flows:** agents → wazuh01 on 1514/tcp (encrypted agent protocol); fw01 → wazuh01 syslog on 514/udp;
  analyst → Wazuh dashboard on 443/tcp from the management VLAN only.

| Decision | Alternatives considered | Why this one |
|---|---|---|
| Wazuh single-node, native install | Elastic Security; Wazuh in Docker | Free, includes agents, FIM, SCA and active response; native install matches how a small company would run it |
| Version pinned (4.14.8) with installer checksum | "Latest" installer | Reproducible builds; an unexpected upstream change stops the install instead of silently differing |
| Sysmon with sysmon-modular | SwiftOnSecurity config; no Sysmon | Maintained, modular, and tagged with ATT&CK techniques |
| pfSense now, FortiGate later | Wait for the FortiGate lab | Unblocks firewall telemetry; the syslog path stays the same when FortiGate replaces it |

## 3. Build

1. **Prerequisites** — Proxmox host with ≥32 GB RAM; isolated bridge/VLANs 20, 30, 99; Windows Server 2022
   and Windows 11 evaluation ISOs; Ubuntu 24.04 ISO; pfSense CE ISO.
2. **Wazuh server** — on wazuh01 run [`scripts/deploy/install-wazuh.sh`](scripts/deploy/install-wazuh.sh). It
   downloads the official 4.14.8 installer, **verifies its SHA-256**, and installs the indexer, server and
   dashboard. Store the generated admin password in a password manager.
3. **Agents** — enroll dc01, ws01 and srv01 following the official Wazuh 4.14 agent documentation; collection
   settings live in [`configs/agents/`](configs/agents/).
4. **Sysmon** — install on dc01 and ws01 with the pinned sysmon-modular configuration
   ([`configs/sysmon/README.md`](configs/sysmon/README.md)).
5. **Firewall logs** — point pfSense remote syslog at wazuh01.
6. **Baseline** — let the lab run with normal activity for one week and export daily alert counts with
   [`scripts/report/export_alert_metrics.py`](scripts/report/export_alert_metrics.py).

> **Gotchas:** recorded as the build progresses in [`docs/build-notes.md`](docs/build-notes.md).

## 4. Test / Validate

Each use case is exercised inside the isolated lab only (VM snapshot before, revert after), following the
upstream Atomic Red Team documentation for the pinned release. Results are recorded in
[`tests/test-plan.md`](tests/test-plan.md).

| # | Host | ATT&CK | Behaviour | Status |
|---|---|---|---|---|
| T1 | ws01 | T1059.001 | Obfuscated PowerShell | Pending lab run |
| T2 | ws01 | T1003.001 | LSASS credential access | Pending lab run |
| T3 | ws01 | T1547.001 | Registry Run-key persistence | Pending lab run |
| T4 | dc01 | T1136.002 / T1098 | New domain account added to a privileged group | Pending lab run |
| T5 | dc01 | T1070.001 | Security log cleared | Pending lab run |
| T6 | srv01 | T1110.001 | SSH password guessing | Pending lab run |
| T7 | srv01 | T1098.004 | SSH `authorized_keys` modification | Pending lab run |
| T8 | fw01 | T1046 | Network service discovery (scan) | Pending lab run |

## 5. Results

**Verified so far (reproducible from this repository):**
- The installer is pinned to Wazuh 4.14.8 and refuses to run if the upstream file changes (checksum check).
- The reporting pipeline is tested in CI: [`export_alert_metrics.py`](scripts/report/export_alert_metrics.py)
  and [`coverage_table.py`](scripts/report/coverage_table.py), including the rule that missing results are
  reported as *Pending*, never as a partial percentage.

**Lab metrics** — filled in from real lab exports with `python scripts/report/coverage_table.py`:

| Metric | Result |
|---|---|
| Detection coverage before tuning | Pending |
| Detection coverage after tuning | Pending |
| Average alerts per day (baseline → tuned) | Pending |

- **Evidence:** sanitized screenshots will be added to [`screenshots/`](screenshots/) after the lab run.
- **What didn't work / known gaps:** to be documented honestly after the run.

## 6. Lessons learned

To be written after the lab run.

## 7. Reproduce it yourself

- Clone: `git clone https://github.com/santorest/lab-01-wazuh-siem.git`
- Download bundle: from the portfolio site (SHA-256 shown next to the download).
- Estimated time: 1–2 days to build, plus one week of baseline.
- Teardown: delete the lab VMs and the isolated bridge; no cloud resources are used.

## 8. Mapping

| Control / technique | Framework | How this project addresses it |
|---|---|---|
| 8.2 Collect audit logs · 8.9 Centralize audit logs | CIS Controls v8 | Agents and syslog forward all telemetry to wazuh01 |
| 8.11 Conduct audit log reviews | CIS Controls v8 | Daily review workflow sized by the alert-volume metric |
| T1059.001, T1003.001, T1547.001, T1136.002, T1098, T1070.001, T1110.001, T1098.004, T1046 | MITRE ATT&CK | One use case each (section 4) |

---

*All testing is performed in an isolated lab environment I own. No real organization's data, hostnames or
configurations are included.*
