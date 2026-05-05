---
name: Stage-2 Dispatcher Subagent
description: Build the parameterized audit-dispatcher subagent that consumes per-rule files (in the unified Claude-rule shape) and produces structured `{rule_id, status, reasoning, recommended_changes}` output for both judgment-mode and recipe-mode invocations.
type: plan
status: executing
branch: refactor/check-bash-script-rule-decomposition  # stacked on the per-rule pilot branch
related:
  - .plans/2026-05-04-check-bash-script-rule-decomposition.plan.md
  - plugins/build/_shared/references/rule-best-practices.md
  - AGENTS.md
scope_adjustment_2026-05-04: |
  Original plan required ≥2 migrated skills before pilot was meaningful (one
  for recipe-mode, one for judgment-mode). Adjusted to a single-skill pilot
  on check-bash-script: its 32 Tier-1 rules exercise recipe-mode fully and
  its 7 Tier-2 dimensions exercise judgment-mode. Cross-skill template
  stability is a #408 concern, not Stage-2's. Task 5 (second-skill
  integration) and the comparison-across-skills aspect of Task 7 are
  deferred to a Stage-2-phase-2 follow-up filed when a second skill migrates.
---

# Stage-2 Dispatcher Subagent

## Goal

Build the parameterized **audit-dispatcher subagent** — one subagent
definition that any check-* skill can invoke to score artifacts against
a single rule. The subagent reads a per-rule file in the unified
Claude-rule shape (per
[`rule-best-practices.md`](../plugins/build/_shared/references/rule-best-practices.md))
and produces structured output via tool use:

```json
{
  "rule_id": "<derived-from-filename>",
  "overall_status": "pass | warn | fail | inapplicable",
  "findings": [
    {
      "location": {"line": <int>, "context": "<snippet>"},
      "status": "warn | fail",
      "reasoning": "<paragraph>",
      "recommended_changes": "<paragraph>"
    }
  ]
}
```

Two invocation modes share one input contract:

- **Judgment mode** — `(rule_md, artifact)`: subagent decides compliance from scratch (LLM judgment).
- **Recipe mode** — `(rule_md, artifact, findings: [...])`: a script already detected violations; subagent localizes recipes to each finding's location.

Mode is determined by whether `findings` is non-empty. Same input shape; same output shape.

This pilot is downstream of:
- `.plans/2026-05-04-check-bash-script-rule-decomposition.plan.md` (per-rule files in unified shape) — landed; provides 40 rule files this dispatcher consumes.

**Scope: single-skill pilot on check-bash-script.** Its 32 Tier-1 rules
exercise recipe-mode (script fires → subagent localizes recipe); its 7
Tier-2 dimensions exercise judgment-mode (subagent does end-to-end LLM
evaluation). Cross-skill template stability is `#408`'s concern, not
Stage-2's.

## Scope

### Must have

- **One subagent definition** at `plugins/build/agents/audit-dispatcher.md` (or similar) — parameterized by `(rule_md, artifact, findings)` inputs. No per-rule subagents; the rule body's known structure is the parameterization.
- **Stable system prompt** that instructs the subagent on rule body structure (imperative + Why + How to apply + optional example + optional Exception), input modes, output schema, and tool-call discipline.
- **Tool-use enforced output** — subagent's only valid response is calling the `report_audit_finding` tool with the structured JSON. Text-only responses are retry-once-then-fail.
- **Pilot integration** — wire the subagent into `check-bash-script`'s audit script. The audit script orchestrates: enumerates rules, invokes scripts for deterministic detection, invokes subagent for judgment OR for recipe-localization. Second-skill integration (Task 5 in the original plan) deferred to a Stage-2-phase-2 follow-up filed when `#408` migrates a second skill.
- **Evaluation harness** — measure dispatcher accuracy against expected labels on real artifacts (8–12 fixtures for `check-bash-script`). Report per-rule agreement scores. The comparison-vs-monolithic-Tier-2-baseline aspect from the original plan is deferred — there's no pre-existing Tier-2 baseline run captured for this skill, and building one retroactively expands scope.
- **Caching** — Anthropic prompt caching (`cache_control` block on the artifact and the rule body) to amortize per-rule invocation cost across an audit run.
- **Failure modes documented** — subagent doesn't call the tool: retry once with explicit reminder, then fail with structured error. Subagent times out: fail with timeout error. Subagent returns invalid JSON in tool input: parser raises, audit reports the malformed result.

### Won't have

- **No per-rule subagent files.** One generic subagent; per-rule specialization comes from the rule body, not from N subagent definitions.
- **No changes to per-rule file shape.** The subagent consumes whatever `.plans/2026-05-04-check-bash-script-rule-decomposition.plan.md` produces. If the shape needs revision after Stage-2 evaluation, that's a separate plan.
- **No update to monolithic Tier-2 path.** The existing single-LLM-call Tier-2 scoring stays as the baseline. Stage-2 is additive — it provides a dispatcher option, not a replacement. The choice between monolithic and dispatcher per skill is made after evaluation.
- **No production rollout.** Stage-2 is a pilot with a measurement deliverable. If accuracy is unacceptable, the dispatcher pattern doesn't ship; if acceptable, a follow-up plan handles rollout to remaining check-* skills.
- **No second-skill integration in this pilot.** `check-bash-script` is the only migrated skill; Task 5 (second-skill wiring) defers to a follow-up issue filed when `#408` migrates a second skill. Cross-skill stability validation also defers.
- **No comparison-vs-monolithic baseline.** The original plan called for a side-by-side comparison against the existing Tier-2 single-LLM-call path. There's no pre-pilot baseline run captured for `check-bash-script`, and constructing one retroactively expands scope. The eval harness measures dispatcher accuracy against hand-labeled expected findings; comparison-vs-baseline is deferred to phase 2.
- **No new frontmatter fields.** The subagent works with the unified `name + description + paths` schema. Anything it can't infer from body structure stays inferred (or unsupported).
- **No multi-rule batching in one call.** A subagent invocation is always one rule against one artifact. Multi-finding aggregation within the rule is handled by the `findings: [...]` input parameter; multi-rule batching across rules is the audit script's orchestration concern, not the subagent's.
- **No streaming.** Synchronous request → tool-call response.
- **No subagent self-reflection or chain-of-thought beyond what the prompt requires.** Minimal context per call; structured output via tool use; no extended-thinking mode in the pilot.

## Approach

### The subagent definition

`plugins/build/agents/audit-dispatcher.md` (Claude Code subagent format):

```markdown
---
name: audit-dispatcher
description: Audits a code artifact against a single rule (in unified Claude-rule shape). Returns structured findings via the report_audit_finding tool. Used by check-* skills to score artifacts during audit.
tools:
  - Read
---

You audit code artifacts against a single rule. The rule file has this shape:

---
name: <Title>
description: <Summary>
paths: <globs>
---

<Imperative statement of what to do>

**Why:** <reason — failure cost>
**How to apply:** <procedure, edge cases>

<Optional example showing compliant pattern>
**Exception:** <Optional exemptions>

## Your inputs

- `rule_md`: the rule file content (frontmatter + body).
- `artifact`: the code artifact to audit (file content).
- `findings` (optional): if a deterministic script already detected violations, an array of `{line, context}` locations focusing your attention.

## Your job

1. Parse the rule. Note: imperative, Why (failure cost), How to apply (procedure), optional example, optional Exception.

2. Determine applicability:
   - If artifact's path doesn't match the rule's `paths:` glob → status="inapplicable"; skip remaining steps.
   - If preconditions in the body don't apply (e.g., "this rule applies to scripts using X feature" and the artifact doesn't use X) → status="inapplicable".

3. If `findings` is provided: you are in **recipe mode**. Treat each finding as a known violation. For each finding, generate a localized recipe grounded in How-to-apply. Status for each finding is "fail" (or "warn" if an exception applies at that location). The overall_status is derived: "fail" if any finding is "fail", else "warn" if any is "warn", else "pass" (no findings to report).

4. If `findings` is not provided: you are in **judgment mode**. Examine the artifact end-to-end for compliance with the imperative. Cite specific lines/locations. Determine status:
   - PASS: artifact follows the rule throughout.
   - WARN: technically violates, but borderline OR an Exception applies with caveats.
   - FAIL: violates and no exception applies.
   - In judgment mode, populate `findings: []` with each location you identify, plus the overall_status.

5. For every WARN/FAIL finding: generate `recommended_changes`. Quote the rule's example if useful. Localize to specific lines.

## Output discipline

You may not respond with prose. Your only valid response is calling the `report_audit_finding` tool with the structured result. If the tool response indicates malformed input, fix and retry once.

## Reasoning style

- Cite specific lines from the artifact ("line 12: `$var` unquoted").
- Reference the rule's Why for stakes ("[Why says: pipe failures are invisible without pipefail]").
- Quote the rule's example as the compliant pattern.
- Don't restate the entire rule in reasoning — assume the caller has it.
- Keep reasoning under 5 sentences per finding. Recipe paragraphs under 10.
```

### The tool definition

```python
TOOL = {
    "name": "report_audit_finding",
    "description": "Report the audit result for one rule against one artifact.",
    "input_schema": {
        "type": "object",
        "required": ["rule_id", "overall_status", "findings"],
        "properties": {
            "rule_id": {
                "type": "string",
                "description": "Kebab-case rule id, derived from the rule file's filename (drop 'rule-' prefix and '.md' suffix)."
            },
            "overall_status": {
                "enum": ["pass", "warn", "fail", "inapplicable"]
            },
            "findings": {
                "type": "array",
                "description": "List of findings. Empty for pass or inapplicable. One or more for warn/fail.",
                "items": {
                    "type": "object",
                    "required": ["status", "reasoning"],
                    "properties": {
                        "location": {
                            "type": "object",
                            "properties": {
                                "line": {"type": "integer"},
                                "context": {"type": "string"}
                            }
                        },
                        "status": {"enum": ["warn", "fail"]},
                        "reasoning": {"type": "string"},
                        "recommended_changes": {"type": "string"}
                    }
                }
            }
        }
    }
}
```

### The orchestrator (audit script)

Each migrated check-* skill's audit script:

```python
def audit(artifact_path: str) -> list[dict]:
    artifact = read(artifact_path)
    results = []
    rules = enumerate_rules(this_skill_dir)  # all rule-*.md files

    for rule in rules:
        rule_md = read(rule)
        rule_id = derive_rule_id(rule.filename)

        if has_script_implementation(rule_id, this_skill_dir):
            # Deterministic — script detects, subagent localizes recipes
            findings = run_script_check(rule_id, artifact_path)
            if findings:
                result = invoke_subagent(rule_md, artifact, findings=findings)
            else:
                result = {"rule_id": rule_id, "overall_status": "pass", "findings": []}
        else:
            # Judgment — subagent does end-to-end evaluation
            result = invoke_subagent(rule_md, artifact, findings=None)

        results.append(result)

    return results
```

### Caching

Each subagent invocation has three input components:

1. **System prompt** — same across all invocations. Cache eternally.
2. **Rule body** — varies per rule, stable across artifacts. Cache per-rule (TTL 5min suits a single audit run).
3. **Artifact** — varies per call within an audit run. Cache per-artifact (TTL 5min suits the audit run).

Anthropic's `cache_control` markers go on (1) and (2) and (3). Across an N-rule audit of one artifact:
- First invocation: pays full cost.
- Invocations 2..N: cache-hit on system prompt + artifact (saved repeatedly); cold cost only on the new rule body.

Estimated cost reduction: ~70–80% of input tokens cached after the first invocation.

### Evaluation harness

`plugins/build/agents/audit-dispatcher/eval/`:

- `fixtures/<skill>/<artifact>.{sh,py,...}` — real artifacts from the toolkit and from a small public corpus (e.g., 5 GitHub repos with diverse bash scripts).
- `expected/<skill>/<artifact>.json` — human-curated expected findings. Each artifact has manual labels: which rules pass, which fail, expected severity per finding location.
- `run_eval.py` — for each (artifact, rule) pair: run dispatcher subagent, compare output to expected. Compute per-rule precision/recall, overall agreement.
- `compare_baseline.py` — for the same artifacts, run the existing monolithic Tier-2 path. Compute the same metrics. Report side-by-side.

Output: a markdown report `eval-results.md` with:
- Per-rule agreement scores (dispatcher vs. expected).
- Per-rule comparison (dispatcher vs. monolithic).
- Aggregate accuracy across all artifacts × rules.
- Cost comparison (tokens, latency).

This report is the deliverable that decides whether the dispatcher pattern ships.

## File Changes

**Create:**

- `plugins/build/agents/audit-dispatcher.md` — subagent definition
- `plugins/build/agents/audit-dispatcher/scripts/invoke_subagent.py` — Python wrapper that calls the Anthropic API with the subagent prompt + tool definition + caching
- `plugins/build/agents/audit-dispatcher/scripts/orchestrator.py` — reusable audit orchestrator (a check-* skill's audit script imports this)
- `plugins/build/agents/audit-dispatcher/eval/run_eval.py`
- `plugins/build/agents/audit-dispatcher/eval/compare_baseline.py`
- `plugins/build/agents/audit-dispatcher/eval/fixtures/check-bash-script/` — pilot artifacts
- `plugins/build/agents/audit-dispatcher/eval/expected/check-bash-script/` — expected labels
- `plugins/build/agents/audit-dispatcher/eval/eval-results.md` — final report (committed at end of pilot)

**Modify:**

- `plugins/build/skills/check-bash-script/scripts/<orchestrator>.py` — wire the dispatcher subagent in
- `plugins/build/skills/<second-skill>/scripts/<orchestrator>.py` — same wiring on a second migrated skill (skill TBD, likely from sweep #408)

**Branch:** `feat/stage-2-dispatcher-subagent` (cut from `main`)

## Tasks

Eight tasks. Tasks 1–3 build the subagent and orchestrator; Tasks 4–5 wire it into pilot skills; Tasks 6–7 build and run the evaluation harness; Task 8 writes the report.

---

### Task 1: Subagent definition + tool schema

**Files:**
- Create: `plugins/build/agents/audit-dispatcher.md`

- [ ] **Step 1:** Author the subagent definition with frontmatter (`name`, `description`, `tools: [Read]`) and the system prompt as drafted in the Approach section.
- [ ] **Step 2:** Write the tool definition (`report_audit_finding`) in `plugins/build/agents/audit-dispatcher/scripts/invoke_subagent.py` (next task) — but lock the schema here as a docstring or constants module.
- [ ] **Step 3:** Validate the subagent definition passes `/build:check-subagent`.
- [ ] **Step 4:** Commit: `feat(agents): add audit-dispatcher subagent definition`.

---

### Task 2: Subagent invocation wrapper (Python + Anthropic SDK + caching)

**Files:**
- Create: `plugins/build/agents/audit-dispatcher/scripts/invoke_subagent.py`

**Depends on:** Task 1

- [ ] **Step 1:** Implement `invoke_subagent(rule_md: str, artifact: str, findings: list | None) -> dict` using the Anthropic Python SDK. Use `claude-sonnet-4-6` for cost/quality balance (revisit per `consider:pick-model`).
- [ ] **Step 2:** Apply prompt caching: `cache_control` markers on the system prompt block and on the rule_md block. Artifact gets a separate cache marker per artifact.
- [ ] **Step 3:** Enforce tool-use output: include `tool_choice={"type": "tool", "name": "report_audit_finding"}` so the subagent must call the tool. Parse the tool input as the structured result.
- [ ] **Step 4:** Failure handling: if response is text-only (model didn't call tool), retry once with an appended user message ("You must call the tool. Retrying."). On second failure, raise `SubagentToolCallError` with the response text for debugging.
- [ ] **Step 5:** Add a `--dry-run` mode that prints the prompt + tool definition without calling the API (useful for fixture authoring).
- [ ] **Step 6:** Add basic unit tests in `plugins/build/agents/audit-dispatcher/tests/test_invoke_subagent.py` — at minimum: dry-run produces expected prompt structure; mock-API call returns parsed result; retry-then-fail path raises.
- [ ] **Step 7:** Commit: `feat(agents): add audit-dispatcher invocation wrapper with tool-use and caching`.

---

### Task 3: Orchestrator (reusable across check-* skills)

**Files:**
- Create: `plugins/build/agents/audit-dispatcher/scripts/orchestrator.py`

**Depends on:** Task 2

- [ ] **Step 1:** Implement `audit(artifact_path: str, skill_dir: str) -> list[dict]`: enumerate rule files, derive rule_ids from filenames, detect script implementations by naming convention (`check_<rule_id>` in `<skill_dir>/scripts/check_*.py` or `<skill_dir>/scripts/check_*.sh`), run script checks for deterministic rules, invoke subagent in recipe mode for fired findings, invoke subagent in judgment mode for non-deterministic rules.
- [ ] **Step 2:** Add a `--rules <id1,id2>` filter for running a subset (eval harness uses this).
- [ ] **Step 3:** Add basic unit test that orchestrator correctly classifies a rule as deterministic vs. judgment-only based on script presence.
- [ ] **Step 4:** Commit: `feat(agents): add audit orchestrator that wires scripts + subagent dispatcher`.

---

### Task 4: Pilot integration — `check-bash-script`

**Files:**
- Modify: `plugins/build/skills/check-bash-script/scripts/<orchestrator>.py` (replace ad-hoc orchestration with the new dispatcher)

**Depends on:** Task 3, plus the per-rule pilot landed (`.plans/2026-05-04-check-bash-script-rule-decomposition.plan.md`)

- [ ] **Step 1:** Replace `check-bash-script`'s existing audit script entry point with a thin wrapper that invokes the new orchestrator: `audit_bash_script(path) → orchestrator.audit(path, skill_dir=__file__.parent.parent)`.
- [ ] **Step 2:** Run the audit on a known artifact end-to-end. Confirm output is the structured `[{rule_id, overall_status, findings}]` list.
- [ ] **Step 3:** Commit: `feat(check-bash-script): integrate audit-dispatcher subagent`.

---

### Task 5: Pilot integration — second skill (DEFERRED to Stage-2 phase 2)

**Status: deferred.** This task is held until `#408` migrates a second skill to the unified per-rule shape. A Stage-2-phase-2 follow-up issue will be filed when that prerequisite lands. The single-skill pilot on `check-bash-script` (Task 4) is sufficient to validate the dispatcher pattern; cross-skill stability is `#408`'s concern.

---

### Task 6: Evaluation harness (single-skill scope)

**Files:**
- Create: `plugins/build/agents/audit-dispatcher/eval/run_eval.py`
- Create: `plugins/build/agents/audit-dispatcher/eval/fixtures/check-bash-script/`
- Create: `plugins/build/agents/audit-dispatcher/eval/expected/check-bash-script/`

**Depends on:** Task 4

- [ ] **Step 1:** Curate fixtures: 8–12 real bash scripts (mix of toolkit-internal scripts and 2–3 small public repos via WebFetch — sourced from MIT/BSD-licensed projects only). Include diverse artifacts: clean, single-violation, multi-violation, edge cases, exception cases.
- [ ] **Step 2:** Hand-label each fixture: per rule, expected status (pass/warn/fail/inapplicable) and per-finding location/severity. This is the manual ground truth — high-quality but tedious; budget ~1 hour per 5 fixtures.
- [ ] **Step 3:** Implement `run_eval.py`: invoke dispatcher on each (fixture, rule) pair; compare to expected; emit per-rule precision/recall + overall agreement.
- [ ] **Step 4:** `compare_baseline.py` deferred to Stage-2 phase 2. There's no captured pre-pilot Tier-2 baseline run for `check-bash-script`; constructing one retroactively expands scope. Phase 2 will re-introduce comparison-vs-baseline once a fresh baseline run is captured.
- [ ] **Step 5:** Commit each: `feat(agents-eval): <component>`.

---

### Task 7: Run evaluation, gather results

**Files:**
- Create: `plugins/build/agents/audit-dispatcher/eval/eval-results.md`

**Depends on:** Task 6

- [ ] **Step 1:** Run `run_eval.py` on `check-bash-script` fixtures. Save output.
- [ ] **Step 2:** Tally: aggregate accuracy of dispatcher per-rule (precision/recall against expected labels); cost (input/output tokens, latency, dollar cost per audit run).
- [ ] **Step 3:** Commit (after Task 8 finalizes the report): `eval(audit-dispatcher): run evaluation against expected labels for check-bash-script`.

---

### Task 8: Write evaluation report

**Files:**
- Modify: `plugins/build/agents/audit-dispatcher/eval/eval-results.md`

**Depends on:** Task 7

- [ ] **Step 1:** Write the report. Sections: (a) methodology — fixtures, labeling protocol, metrics; (b) headline result — does dispatcher meet target accuracy on `check-bash-script`'s rules; (c) per-rule outliers (rules where dispatcher significantly disagrees with expected labels); (d) cost analysis; (e) recommendation — ship dispatcher to second skill in phase 2, ship with caveats, or don't ship.
- [ ] **Step 2:** Include a section on the **RULERS prior** — the original "11.5 points lower" citation across the codebase is unverified; dispatch is closer to MTS-style decomposition than RULERS' unified rubric. Report whether our pilot's empirical results support, contradict, or are silent on the RULERS direction. Single-skill data is preliminary; phase 2 strengthens the verdict.
- [ ] **Step 3:** Commit: `docs(agents-eval): add Stage-2 phase-1 evaluation report and recommendation`.

---

## Validation

- [ ] `plugins/build/agents/audit-dispatcher.md` passes `/build:check-subagent`.
- [ ] `plugins/build/agents/audit-dispatcher/scripts/invoke_subagent.py --dry-run` emits expected prompt + tool definition.
- [ ] Unit tests pass: `python -m pytest plugins/build/agents/audit-dispatcher/tests/ -v`.
- [ ] Tool-call enforcement: subagent's response is always a tool call (no text-only responses); failure mode hits retry-once-then-fail in tests.
- [ ] Caching works: second invocation in same run hits cache for system prompt + artifact (verifiable via API response cache statistics).
- [ ] `check-bash-script` audit produces structured `[{rule_id, overall_status, findings}]` output via dispatcher.
- [ ] Second skill's audit produces same shape.
- [ ] Eval harness runs end-to-end on both skills' fixtures without errors.
- [ ] `eval-results.md` exists and contains all six sections (methodology, headline, per-skill, outliers, cost, recommendation).
- [ ] Report explicitly addresses the RULERS prior: does dispatcher agreement support or contradict the unified-rubric direction?
- [ ] Aggregate dispatcher agreement on labeled fixtures ≥ 75% (sanity threshold; report flags if below).
- [ ] Cost per audit run is within 3× the monolithic baseline cost (above 3× signals caching is misconfigured or the dispatcher pattern needs revisiting).

## Notes

- **Why one generic subagent, not N per-rule subagents.** The rule body's known structure (per `rule-best-practices.md`) provides the parameterization. Authoring 40+ subagents per skill is a maintenance disaster. One subagent + N rule files is the correct factoring — the rule body IS the prompt specialization.

- **The RULERS prior is soft.** The "11.5 points lower for per-criterion calls" citation across the codebase ([6 places](https://github.com/bcbeidel/toolkit) at last check) is not verifiable from the paper's accessible content. The paper itself (Hong et al. 2026, "Rulers: Locked Rubrics and Evidence-Anchored Scoring", arXiv 2601.08654) is real and supports unified rubrics over decomposition (MTS) in general. The specific number is not findable in the abstract or HTML. Stage-2's evaluation harness is the empirical test; the report's recommendation supersedes the prior.

- **Two-skill pilot, not one.** A single-skill pilot might exercise only recipe-mode (if the skill is mostly script-bound, like `check-bash-script`) or only judgment-mode (if mostly Tier-2, like `check-skill`). Two skills with complementary balances ensure both modes get exercised. Three+ skills is overkill for the pilot; each adds eval-harness curation cost without adding test coverage.

- **Fixture curation is the costliest part.** Hand-labeling artifacts is labor-intensive (~1 hour per 5 artifacts). Budget accordingly. PILOT-NOTES from the per-rule decomposition pilot may surface some shortcuts (artifacts already used in equivalence tests).

- **Why retry-once-then-fail on tool-call drift.** Anthropic API can return text instead of a tool call when the model is uncertain or the prompt confuses it. One retry with explicit reminder ("You must call the tool") catches transient confusion; failures beyond that signal a prompt or API issue worth surfacing as a hard error rather than masking with infinite retries.

- **Caching strategy is critical.** Without caching, an N-rule audit costs N × (system prompt + rule body + artifact) input tokens. With per-rule and per-artifact caching, the marginal cost of rule N+1 is just the rule body delta. Estimated 70–80% input token reduction. For a 40-rule audit on a 1KB artifact, that's the difference between $0.30 and $0.06 per run.

- **`tools: [Read]` on subagent.** The subagent receives `rule_md` and `artifact` as inputs to its prompt; it doesn't need filesystem access for its core job. `tools: [Read]` is included for cases where the rule body cross-references another file ("see also: rule-shebang.md") and the subagent needs to load it. Bound minimally — no Bash, no Edit, no Write.

- **Anti-prescription: dispatcher is not always the right pattern.** If Stage-2's report shows dispatcher agreement significantly worse than monolithic, the conclusion is "don't ship the dispatcher pattern; per-rule files still serve their other purposes (Claude ambient guidance, single-rule readability) but the monolithic Tier-2 path stays canonical." Stage-2 is a fork in the road, not a foregone conclusion.

- **Stage-3 (rollout) is a separate plan.** If Stage-2 succeeds, rolling out the dispatcher to all 12 check-* skills is its own plan. Each skill needs its audit script wired in, fixtures curated for eval continuity, and a per-skill report. Don't conflate Stage-2 (validate the pattern) with Stage-3 (rollout).
