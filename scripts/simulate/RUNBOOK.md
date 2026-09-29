# Simulation runbook (isolated lab only)

Tool: Atomic Red Team (Invoke-AtomicRedTeam) on ws01 / dc01.

For each technique:
1. Snapshot the VM.
2. Run the atomic test by ID; note the exact time.
3. Check Wazuh for an alert within 5 minutes.
4. Record the result in `tests/test-plan.md`.
5. Run the test's cleanup, then revert the snapshot.
