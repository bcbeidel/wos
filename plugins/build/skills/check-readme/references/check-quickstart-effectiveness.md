---
name: Quickstart Effectiveness
description: The Quickstart must show one minimal command demonstrating core value plus the expected output a reader can compare against.
paths:
  - "**/README.md"
  - "**/Readme.md"
---

Reduce the Quickstart to one primary command or call that demonstrates the project's core value, and follow it with an expected-output block matching what a reader would actually see.

**Why:** Silence after a command breeds doubt — readers who run the example and see no output cannot tell whether it worked, hung, or silently failed. "Minimal" means smallest thing that demonstrates value, not smallest thing that runs without erroring; a feature tour covering three use cases or a fifteen-line setup is not a Quickstart. An example whose output is mocked or aspirational is worse than no example, because the reader's confusion turns into mistrust. Source principles: *Minimal runnable example in Quickstart*; *Forgetting expected output in Quickstart* (anti-pattern).

**How to apply:** Verify the Quickstart has one primary command or call. Verify an expected-output block follows and matches what a reader would see. Verify the example demonstrates the project's core value, not a tangent. If the Quickstart is a feature tour or has no expected output, trim the example to one command or call that demonstrates the core value and add an expected-output block beneath.

````markdown
## Quickstart
```bash
lff serve --port 3000
```
Expected output:
```
LFF listening on :3000 (pid 1234)
```
````

**Common fail signals (audit guidance):** Quickstart is a feature tour covering three use cases; no expected output shown; the "minimal" example requires fifteen lines of setup code; the example's output is mocked or aspirational.
