---
name: Python Utilities Reference
description: CLI commands for lint and URL checking during research sessions
stage: shared
pipeline: research
---

# Python Utilities Reference

CLI commands for research sessions. `<plugin-scripts-dir>` refers to
the `scripts/` directory at the root of the `wiki` plugin (`plugins/wiki/scripts/`).

## Validate a Document

```bash
python <plugin-scripts-dir>/lint.py <file> --root . [--urls]
```

## Check URL Reachability

```bash
python <plugin-scripts-dir>/check_url.py URL1 URL2 ...
```
