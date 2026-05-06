---
name: Attack Surface
description: Hook placement and content reflect the attack surface of settings.json (CVE-2025-59536).
paths:
  - "**/.claude/settings.json"
  - "**/.claude/settings.local.json"
---

Treat hooks in project `settings.json` as executable code in review; keep security-sensitive or personal-only hooks in `settings.local.json`; remove user-level hooks when CI may run the project.

**Why:** Project `settings.json` executes for every collaborator who opens the repo (CVE-2025-59536). A malicious or sloppy hook landed via PR runs on every reviewer's machine the moment they pull the branch. User-level hooks (`~/.claude/settings.json`) fire in CI automation too — enforcement designed for local ergonomics applies in GitHub Actions where the assumptions don't hold (different filesystem layout, different secrets, different network posture). Both vectors are silent: the hook is doing its job, just for the wrong audience. Severity: `warn`.

**How to apply:** personal-only enforcement → move to `.claude/settings.local.json` (gitignored). Team-wide enforcement in `settings.json` → require code review for any change to that file; document the policy in CONTRIBUTING or README. Remove user-level hooks (`~/.claude/settings.json`) when the project runs in CI environments where they would apply out of scope.

```json
// .claude/settings.local.json (gitignored — personal-only)
{
  "hooks": {
    "PostToolUse": [
      {"matcher": "Bash", "hooks": [{"type": "command", "command": "..."}]}
    ]
  }
}
```

**Common fail signals (audit guidance):**
- Security-sensitive hook (auth check, secret scanner, blocking gate) committed in `.claude/settings.json` with no documented review process.
- User-level `~/.claude/settings.json` hooks present on a project that runs in GitHub Actions / CI.
- New hook added to project `settings.json` without a corresponding CONTRIBUTING / CODEOWNERS update naming the review gate.
- Personal preferences (telemetry, ergonomics) in project `settings.json` instead of `settings.local.json`.
