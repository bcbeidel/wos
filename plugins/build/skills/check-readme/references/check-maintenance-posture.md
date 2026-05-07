---
name: Maintenance Posture
description: The README must show no staleness indicators (dated roadmaps, pasted `--help`, stale version pins) and must point to detailed docs rather than duplicating them.
paths:
  - "**/README.md"
  - "**/Readme.md"
---

Keep the README a pointer to detailed docs rather than a duplicate; remove drift indicators (dated roadmaps, pasted `--help` output, pinned versions out of date, "coming soon" links, content duplicated from `CONTRIBUTING.md` or `ARCHITECTURE.md`).

**Why:** Stale docs cost reader trust; one stale line taints nearby correct ones. A "Roadmap" with items marked "Q3 2023" or a pasted `--help` block three years old signals that nothing here is current. Hand-maintained duplicates of `--help` and copies of `CONTRIBUTING.md` content drift silently from their authoritative source — and the README, by virtue of being where readers look first, becomes the version they trust.
**How to apply:** Scan for staleness indicators visible in the text: commands referring to renamed flags or removed subcommands, pinned version numbers that look out of date, hand-maintained `--help` output, "coming soon" links, content duplicated from `CONTRIBUTING.md` or `ARCHITECTURE.md`, references to features the project has moved past. If found, update version references, replace pasted `--help` with a link to `tool --help` or a generated docs page, and prune roadmap items completed or abandoned.

```markdown
## Usage
See `lff --help` for the full command reference.

## Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md).
```

**Common fail signals (audit guidance):** A "Roadmap" section with items marked "Q3 2023"; a pasted `--help` block three years old; "See CONTRIBUTING below" followed by 200 lines of contributing guidelines that also live in `CONTRIBUTING.md`.
