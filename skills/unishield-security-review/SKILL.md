---
name: unishield-security-review
description: On-demand security review of a PR diff or file list — faster than a full SCR workflow run. Runs identification and parallel false-positive filtering sub-tasks. Use /unishield-security-review for quick ad-hoc analysis.
metadata: {"openclaw": {"requires": {"bins": ["git"], "env": ["ANTHROPIC_API_KEY"]}, "primaryEnv": "ANTHROPIC_API_KEY", "user-invocable": true}}
---

# UniShield Security Review — On-Demand Slash Command

Use this skill for quick, ad-hoc security review of a PR diff or specific files. This is faster than triggering a full SCR workflow. Use it when you want a quick second opinion on a code change without running the full 10-stage pipeline.

## How to invoke

```
/unishield-security-review <pr_url_or_file_paths>
```

Examples:

```
/unishield-security-review https://github.com/meridian/payments/pull/142
/unishield-security-review src/payments/TransactionService.java
/unishield-security-review src/auth/ src/swift/
```

## What this does

This review runs in 3 steps as parallel sub-tasks — identical methodology to the Anthropic claude-code-security-review GitHub Action:

### Step 1 — Vulnerability identification sub-task

Launch a sub-task with this prompt:

You are a senior security engineer reviewing code changes for a BFSI (banking/financial services) client. Analyze the provided diff or files for security vulnerabilities.

Focus ONLY on HIGH and MEDIUM severity findings.
MINIMIZE FALSE POSITIVES: Only flag issues where you are >80% confident of actual exploitability.
AVOID: theoretical issues, style concerns, low-impact findings, DoS, rate limiting, resource leaks, open redirects.
FOCUS ON: unauthorized access, data breach, payment fraud, credential theft, SWIFT/FIX protocol injection, PAN/CVV exposure.

For each finding output JSON:

```json
{
  "title": "",
  "severity": "HIGH|MEDIUM",
  "file_path": "",
  "line_start": 0,
  "description": "",
  "attack_scenario": "",
  "fix": ""
}
```

### Step 2 — False positive filtering sub-tasks (parallel)

For EACH finding from Step 1, launch a SEPARATE parallel sub-task:

You are filtering false positives from a security review.
Finding: `<finding JSON>`
Assign confidence 1-10 of actual exploitability in a BFSI context.
Consider: Is this exploitable in production? Does it lead to real harm?
Report JSON: `{"confidence": <1-10>, "keep": <true/false>, "reason": ""}`

Filter out any finding where confidence < 8.

### Step 3 — Output

Report surviving findings (confidence >= 8) as a structured summary.
For each finding include: severity, file, line, description, attack scenario, and recommended fix.

## Important

This is a quick scan, NOT a replacement for the full UniShield-SCR workflow. It does not:

- Run Semgrep or other SAST tools
- Generate a SBOM
- Scan git history for secrets
- Write to shared memory or trigger other agents
- Require orchestrator involvement

For a full platform scan, use the workflow trigger from the dashboard.
