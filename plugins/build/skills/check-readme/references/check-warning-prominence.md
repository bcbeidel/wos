---
name: Warning Prominence
description: Destructive and security-sensitive operations must carry warnings visually prominent enough that a scanning reader sees them — callouts, blockquotes, or bold, not buried prose.
paths:
  - "**/README.md"
  - "**/Readme.md"
---

Promote warnings on destructive or security-sensitive steps to blockquotes, bold callouts, or a dedicated `⚠ Warning` prefix immediately adjacent to the block — not inline prose the reader's eye skims.

**Why:** Readers scan; warnings must catch a scanning eye, not a careful read. "Note: this will delete all your data" in a normal sentence after an `rm -rf` block fails the proportionality test — the prominence of the warning must match the cost of the mistake. A pipe-to-shell installer with no manual alternative pushes the reader into a security posture they should opt into. A sudo-requiring step with no explanation of why is a request for trust the reader has no basis to grant. Source principles: *Destructive commands without a warning callout* (anti-pattern); *Piped-to-shell installers with no manual alternative* (anti-pattern); *Hard safety rules*.

**How to apply:** When destructive or security-sensitive operations appear (destructive commands, pipe-to-shell installers, privilege-requiring steps), verify warnings are visually prominent — callouts, blockquotes, bold, or `⚠ Warning` prefix — and proportional to the risk. Verify pipe-to-shell installers list a manual alternative within the same section. If warnings are inline prose, promote them to blockquotes or bold callouts immediately adjacent to the block.

````markdown
> ⚠ **Warning:** this deletes all local project data.
```bash
rm -rf /var/lib/project
```
````

**Common fail signals (audit guidance):** "Note: this will delete all your data" in a normal sentence after the `rm -rf` block; pipe-to-shell installer with no manual alternative; a sudo-requiring step with no explanation of why.
