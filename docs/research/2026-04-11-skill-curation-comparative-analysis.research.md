---
name: "Skill Curation Comparative Analysis"
description: "Comparative analysis of skill authoring and curation approaches across Anthropic/WOS, OpenAI, GitHub Copilot, and open-source frameworks — benchmarked against WOS with a prioritized gap analysis and implementation mapping targeting build-skill, check-skill, skill-authoring-guide, and context docs"
type: research
created: 2026-04-11
sources:
  - https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
  - https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
  - https://code.claude.com/docs/en/skills
  - https://github.com/anthropics/skills/tree/main/skills/skill-creator
  - https://developers.openai.com/api/docs/guides/function-calling
  - https://developers.openai.com/blog/eval-skills
  - https://developers.openai.com/cookbook/examples/evaluation/getting_started_with_openai_evals
  - https://docs.github.com/en/copilot/customizing-copilot/adding-custom-instructions-for-github-copilot
  - https://www.allaboutken.com/posts/20260408-mini-guide-claude-copilot-skills/
  - https://python.langchain.com/docs/concepts/tools/
  - https://docs.crewai.com/concepts/tools
  - https://arxiv.org/abs/2602.11988
  - https://arxiv.org/abs/2310.11324
  - https://arxiv.org/abs/2304.06597
  - https://www.promptfoo.dev/docs/integrations/ci-cd/
  - https://best.openssf.org/Security-Focused-Guide-for-AI-Code-Assistant-Instructions.html
  - https://www.mindstudio.ai/blog/agent-skills-open-standard-claude-openai-google
  - https://github.com/openai/skills/tree/main/skills/.system/skill-creator
  - https://yarmoluk.github.io/custom-skill-developer/
related:
  - docs/prompts/skill-curation-comparative-analysis.prompt.md
  - docs/context/instruction-file-authoring-anti-patterns.context.md
  - docs/context/instruction-file-non-inferable-specificity.context.md
  - skills/lint/references/skill-authoring-guide.md
  - skills/build-skill/SKILL.md
  - skills/check-skill/SKILL.md
  - docs/context/intent-routing-convergent-pattern-five-steps.context.md
  - docs/context/tier-aware-skill-authoring-guidance-and-directive-calibration.context.md
  - docs/context/skill-behavioral-testing-layer-gap.context.md
  - docs/context/skill-format-portability-floor-vs-wos-extensions.context.md
  - docs/context/skill-success-criteria-four-axes.context.md
---

# Skill Curation Comparative Analysis

**Primary deliverable:** Implementation Mapping table (Section 7) — thirteen gaps mapped to specific, implementable changes in build-skill, check-skill, skill-authoring-guide, context docs, or marked out-of-scope.

**Status:** Analysis complete. Includes deep comparison with [Anthropic's skill-creator](https://github.com/anthropics/skills/tree/main/skills/skill-creator) (Section 2, Gaps G9–G10), [OpenAI Codex skill-creator](https://github.com/openai/skills/tree/main/skills/.system/skill-creator) (Section 2, Gaps G11–G12), and [Yarmoluk Custom Skill Developer guide](https://yarmoluk.github.io/custom-skill-developer/) (Section 2, Gap G13). Ready for `/wos:distill` to convert findings into context docs, or direct implementation against the four curation artifacts.

---

## 1. Comparative Analysis Table

| Platform | Authoring Workflow | Curation & Update | Quality Controls | Discovery & Reuse | WOS Comparison |
|---|---|---|---|---|---|
| **Anthropic / WOS** | 6-field structured elicitation; reads anti-pattern context before drafting; 6-step sequential workflow with lint gate before write | check-skill on-demand audit; opt-in repair loop with per-change confirmation; no versioning or deprecation mechanism | 2 static (lint.py) + 8 LLM criteria; removal test, vagueness, persona checks; separation of deterministic vs. judgment layers | L1/L2/L3 progressive loading; 250-char description truncation window; description-driven routing with pushy heuristic | Baseline |
| **Anthropic skill-creator** (reference impl) | Loose intent capture (goal, trigger, expected outputs, eval needed?); free-form SKILL.md body; no required structural sections | Iterative iter-N directories track improvement history; history.json records pass rates per version | Parallel with/without-skill eval runs; grader agents; benchmark.json; trigger evaluation loop with precision/recall measurement; `quick_validate.py` for structural pre-flight | Description routing optimized via `run_loop.py` (train/test split, up to 5 iterations); no L2/L3 distinction | WOS exceeds in structural authoring contracts; skill-creator exceeds in behavioral evaluation and description iteration |
| **OpenAI (GPTs / Assistants / Functions)** | No structured scaffolding; "intern test" as primary heuristic; JSON Schema function definitions; 2-level namespace+function hierarchy | GPT configuration UI; no versioning of function definitions; no audit tooling | No automated checks; OpenAI Evals framework for behavioral testing (4-axis: outcome/process/style/efficiency goals) | Function-calling description routing; namespace descriptions for selection, function descriptions for usage; role prompting frames scope | WOS exceeds in authoring structure and static QA; OpenAI leads in behavioral evaluation infrastructure |
| **GitHub Copilot** | Agent Skills spec minimum (name + description + body); `.github/copilot-instructions.md` for workspace context | Plain file edits; no versioning beyond git; no audit tooling | No automated skill quality checks | Description-driven at spec minimum; no subagent inheritance; explicit `/skill-name` invocation; no L2/L3 | WOS has substantially more structure; Copilot provides the only empirically confirmed cross-runtime portability evidence |
| **OpenAI Codex skill-creator** | 6-step workflow: concrete examples → plan resources → init_skill.py → edit → validate → iterate; explicit trigger-oriented intake ("what would a user say to trigger this?"); assets/ directory for output-bound files | Script-based init_skill.py template; quick_validate.py; iterate on real usage | quick_validate.py for YAML/naming checks; no quality criteria; no audit tooling | Description-driven; description must contain all "when to use" — body is trigger-blind; agents/openai.yaml for UI-facing metadata | WOS exceeds in structural quality contracts; Codex leads on assets/ directory pattern and trigger-first intake; same freedom ↔ fragility principle |
| **Yarmoluk (Custom Skill Developer)** | 10-section standard body structure including embedded quality scoring rubric; skills as SOPs (exact steps, checkpoints); meta-skill routers for consolidation | Version in git; no dedicated audit tooling | Embedded Bloom's Taxonomy–aligned self-assessment rubric inside skill body; external Skill Quality Analyzer tool (100-point rubric) | Filesystem-based discovery; 30-skill session limit managed via meta-skill routers | WOS external audit model (check-skill) vs. Yarmoluk embedded rubric model; Yarmoluk adds 30-skill limit awareness WOS lacks |
| **LangChain** | Python docstring is the tool description; no structured authoring guide; no trigger phrase conventions | Code-review only; no versioning beyond git | No skill quality validation; routing failures addressed via Pydantic schema fixes, not description improvement | Schema-first routing (Pydantic); selection by parameter schema, not description text | WOS exceeds in all dimensions; LangChain schema-first model is a different architectural assumption |
| **CrewAI / AutoGPT** | Agent+Task+Crew triplet (YAML/Python); no description authoring guide; role/goal descriptions drive task matching | No dedicated tooling | No quality validation; testing via standard unit tests | Task-matching via agent role and goal; no discovery abstraction | WOS exceeds in all dimensions; no comparable concept of skill quality audit |

---

## 2. Platform Profiles

### Anthropic / WOS

WOS implements the most structured skill curation system found across all platforms in scope. The `build-skill` workflow elicits six fields before drafting, reads two anti-pattern context documents, and enforces a lint gate before write. The `check-skill` auditor assesses ten criteria — two static (body length, ALL-CAPS density), eight LLM-level — covering the highest-evidence anti-patterns from practitioner research [Tier 1: `instruction-file-authoring-anti-patterns.context.md`].

The L1/L2/L3 progressive loading model is architecturally unique to Claude Code. L1 (~100 tokens, always loaded) is cost-free at runtime; L2 and L3 load on-demand via Bash tool calls from Claude's VM. This design has no equivalent on GPT, Gemini CLI, or any open-source runtime [Tier 1: Claude Code official documentation, platform.claude.com]. No other runtime replicates on-demand file dispatch during execution.

Anthropic publishes the only major-framework tier-specific authoring guidance, differentiating Haiku ("does the skill provide enough guidance?"), Sonnet ("is it clear and efficient?"), and Opus ("does it avoid over-explaining?") [Tier 2: Anthropic Skill Authoring Best Practices]. This guidance is directional heuristic, not empirically benchmarked. Directive calibration inverts with capability — Anthropic explicitly deprecated ALL-CAPS and MUST-style directives for Opus 4.5+.

Current gaps in WOS: no behavioral testing layer (stops at Layer 1 structural lint); no versioning or deprecation mechanics; no portability annotations in the authoring guide; criterion #2 not tier-aware; no won't-do enforcement in check-skill; no contradiction detection criterion.

### Anthropic skill-creator (github.com/anthropics/skills)

The Anthropic skill-creator is the reference implementation for skill authoring in the Agent Skills ecosystem. It is architecturally an *eval-first* system — evaluation infrastructure is built alongside the skill, not after. The authoring workflow is: capture intent → write SKILL.md → write test cases (evals.json) → run parallel with/without-skill evaluation → grade results → iterate → optimize description → package [Tier 1: github.com/anthropics/skills/skill-creator/SKILL.md, directly inspected].

**What WOS has that skill-creator lacks.** skill-creator has no required structural sections — no `## Anti-Pattern Guards`, no `## Handoff`, no `## Key Instructions`. Won't-dos are not elicited at creation time. The skill body is free-form. There is no removal test ("would removing this line cause a mistake?"). There is no systematic anti-pattern audit comparable to check-skill. Quality is validated empirically (does it produce good outputs?) rather than structurally (does it encode its contract correctly?).

**What skill-creator has that WOS lacks.** Three capabilities are substantially more developed in skill-creator: (1) **Behavioral evaluation** — parallel with/without-skill runs, grader agents that assess outputs against `evals.json` expectations, `benchmark.json` aggregate performance tracking, and `history.json` iteration versioning across iter-0/iter-1/iter-2 directories; (2) **Trigger evaluation** — `run_loop.py` generates 8–10 should-trigger and 8–10 should-NOT-trigger queries, splits them into train/test sets, and iteratively optimizes the description via precision/recall measurement across up to 5 iterations with `improve_description.py`; (3) **Environment-specific degraded modes** — skill-creator explicitly documents lightweight workflows for Claude.ai (skip subagent evaluation, skip grader agents, skip browser viewer, present results inline) and Cowork (subagents supported but generate static HTML). WOS skills assume Claude Code environment throughout and provide no guidance on degraded operation.

**Rationale-over-rigidity — specific transformation pattern.** Both WOS and skill-creator identify that rigid directives ("ALWAYS use markdown") underperform rationale-based instructions. However, skill-creator provides a concrete rewrite pattern: *"Instead of 'ALWAYS use markdown,' try 'Use markdown for readability since the user will review the output.'"* WOS's skill-authoring-guide says "Rationale over rigidity" in the judgment check table but gives no transformation example. The specific before/after pattern is more actionable than the general principle.

**Packaging and distribution.** skill-creator includes `package_skill.py` which creates a distributable `.skill` file (ZIP archive), validating SKILL.md structure and excluding temp directories. WOS has `scripts/deploy.py` for exporting to `.agents/` — a different distribution model targeting cross-platform deployment rather than single-file packaging.

### OpenAI (GPTs / Assistants API / Function Calling)

OpenAI's skill definition is structured around JSON Schema function definitions rather than markdown instruction files. The primary quality heuristic is the "intern test": "Could an intern use this function knowing only its description?" [Tier 1: OpenAI Function Calling documentation]. Required description elements: purpose, parameters, formats, outputs, and when and when *not* to use. The two-level hierarchy — concise namespace descriptions for selection, detailed function descriptions for usage — separates routing signal from usage context.

A critical divergence from Anthropic: OpenAI explicitly warns that adding examples to descriptions *may hurt performance for reasoning models* (o3, o4-mini) [Tier 1: OpenAI Function Calling documentation]. Anthropic recommends examples freely. This split is consequential for teams building cross-platform skills.

OpenAI has the most mature behavioral evaluation infrastructure in scope. The OpenAI Evals framework requires pre-committing to four goal categories before evaluation: outcome goals (did the skill complete the task?), process goals (did it follow the intended steps?), style goals (does output match conventions?), and efficiency goals (is it avoiding unnecessary work?) [Tier 1: OpenAI Evals framework documentation]. Pre-commitment prevents post-hoc rationalization. No equivalent framework exists in WOS. However, OpenAI Evals targets model-level behavioral evaluation, not skill-file quality assessment — the artifact type differs from check-skill's structural audit scope.

OpenAI has no structured skill scaffolding workflow, no equivalent to check-skill, no removal test, no anti-pattern guards requirement, and no formalized won't-do elicitation.

### GitHub Copilot

GitHub Copilot's skills implement the Agent Skills spec minimum: `name`, `description`, and a markdown body [Tier 2: Ken Hawkins, April 2026 empirical confirmation — single minimal SKILL.md verified to run on both Claude Code and Copilot CLI without modification]. The spec minimum has been adopted by Copilot CLI, Gemini CLI, and Cursor. Copilot workspace context lives in `.github/copilot-instructions.md` — an analogous pattern to CLAUDE.md for repository-level instructions [Tier 1: GitHub Copilot official documentation].

Copilot has documented limitations above the spec minimum: subagents cannot inherit repository-level skills (Copilot CLI architecture), dynamic context injection is unavailable, and L2/L3 loading does not occur [Tier 3: inferred from platform architecture and confirmed by multi-runtime behavioral comparison in research]. No equivalent to check-skill, build-skill, or any skill quality validation exists in Copilot tooling. The implicit model is that skill quality is a general prompting problem, not a structured authoring problem.

### OpenAI Codex skill-creator (github.com/openai/skills)

The OpenAI Codex skill-creator is the parallel implementation for the Codex runtime. Its six-step workflow is: understand with concrete examples → plan reusable contents → initialize (`init_skill.py`) → edit → validate (`quick_validate.py`) → iterate [Tier 1: github.com/openai/skills/.system/skill-creator/SKILL.md, directly inspected].

**Trigger-first intake.** Step 1 explicitly asks "What would a user say that should trigger this skill?" before any drafting begins. This is a stronger framing than WOS's description elicitation — the trigger vocabulary question is foregrounded, not derived from the description field.

**Critical description guidance that WOS lacks.** The Codex skill-creator states explicitly: *"Include all 'when to use' information in the description — Not in the body. The body is only loaded after triggering, so 'When to Use This Skill' sections in the body are not helpful to Codex."* This means any routing or trigger guidance written inside the skill body is unreachable at routing time. WOS's skill-authoring-guide does not call this out. This is a new anti-pattern: body-embedded "When to Use" sections create a false impression of completeness while contributing nothing to routing.

**`assets/` directory as a first-class primitive.** Codex skill-creator adds a third directory type alongside `scripts/` and `references/`: `assets/` for files not loaded into context but used in output (templates, images, boilerplate code, fonts). WOS's skill-authoring-guide recognizes only `references/`. The distinction matters — a template included as an output artifact should not consume context window tokens; a reference document should. WOS conflates these into a single `references/` model.

**UI-facing metadata separation.** `agents/openai.yaml` carries display-facing metadata (display_name, short_description, default_prompt) separate from the routing metadata in frontmatter. The Codex runtime surfaces the `short_description` in UI chip components; the SKILL.md description drives model routing. WOS has no parallel — the single frontmatter `description` field serves both purposes. This creates authoring tension: pushy routing language ("Make sure to use this skill whenever...") conflicts with clean user-facing copy.

**Same freedom ↔ fragility principle, identical framing.** Both WOS and Codex skill-creator use the identical mental model: high freedom for low-fragility tasks, low freedom (specific scripts) for high-fragility tasks. This convergence across independent implementations is strong evidence the principle is correct.

No required structural sections (no Anti-Pattern Guards, Handoff, Key Instructions). No won't-do elicitation. No removal test. No LLM-level quality audit.

### Yarmoluk Custom Skill Developer (yarmoluk.github.io)

An independent 82,000-word practitioner guide for building production-grade Agent Skills, built from experience creating 20+ production skills [Tier 3: directly inspected, practitioner guide, no peer review]. Three additions materially relevant to WOS:

**Embedded quality scoring rubric.** The Yarmoluk standard 10-section body structure includes a "Quality Scoring" section — a rubric the model uses to self-assess output before writing files. Threshold-based: if output scores below threshold, produce a gap report instead of the final output. This is an *embedded* quality model, in contrast to WOS's *external* quality model (check-skill audits the skill definition; Yarmoluk's rubric audits skill execution outputs). The two approaches are complementary, not competing. WOS checks the skill file; the embedded rubric checks the skill's output.

**30-skill session limit.** Claude Code loads a maximum of 30 skills per session. This is a runtime constraint WOS does not document anywhere. When a project has more than 30 skills, some will not be loaded, and routing to them will silently fail. The Yarmoluk guide addresses this with meta-skill routers: a single routing skill consolidates up to 30 sub-skills into a router entry point via keyword-based dispatch tables. WOS's skill-authoring-guide says nothing about this limit.

**"Context window is a public good."** Yarmoluk (echoing OpenAI Codex): "Skills share the context window with everything else Codex needs: system prompt, conversation history, other Skills' metadata, and the actual user request." This frames the token-earning test as a shared-resource stewardship problem, not just a quality problem. The framing is more motivating than WOS's current "pulling its weight" language.

### LangChain / CrewAI / AutoGPT

LangChain's tool description is the Python function docstring. Official documentation states it "should be informative and concise" — no structured authoring guide, no trigger phrase pattern, no character limits, no negative trigger mechanism [Tier 1: LangChain official documentation]. When tools misroute, the community response is to improve Pydantic schemas rather than description text [Tier 3: inferred from LangChain community patterns and developer forums]. This signals a schema-first routing model fundamentally different from Anthropic's description-first model.

CrewAI uses an Agent+Task+Crew triplet where tools are Python functions attached to agents. Agent role and goal descriptions drive task matching [Tier 1: CrewAI official documentation]. No description authoring guide, no quality validation, no anti-pattern documentation. AutoGPT's plugin architecture defines capabilities with no quality rubric for instruction clarity.

Across all open-source frameworks: no platform maintains a separation between static and LLM-level quality checks. No framework has a documented removal test. No framework elicits won't-dos at creation time. No framework has a structured intake workflow.

---

## 3. What WOS Gets Right

**Structured elicitation before drafting.** The six-field intake (Name, Description, Receives, Produces, Won't do, Context files) forces the I/O contract and scope boundary to be defined before a word of the skill body is written. No other platform in scope elicits won't-dos at creation time — the absence of negative rules is anti-pattern #8 with MODERATE evidence. WOS builds prevention directly into the creation workflow.

**Separation of static and LLM checks.** Running `lint.py` (deterministic) before LLM criteria mirrors the empirically validated deterministic-first assertion layering pattern [Tier 2: Promptfoo, EvidentlyAI, `prompt-regression-deterministic-first-assertion-layering.context.md`]. LLM-as-judge has documented position bias (60–69% selection of "Response B"), rubric order effects (~3.5% penalty for last-evaluated criterion), and Fleiss' κ ≈ 0.3 in multilingual tasks. Using it as the foundation of a regression system is unsafe. WOS avoids this by running deterministic checks first and reserving LLM judgment for the checks that cannot be automated.

**Removal test as a first-class criterion.** Criterion #9 and the token-earning test encode the highest-signal specificity filter from the research literature. The ETH Zurich finding — LLM-generated context files reduce task success −0.5% to −2% and increase inference cost +20% from redundancy with existing docs [Tier 1: arXiv 2602.11988] — directly supports this design choice. No other platform in scope has a formalized removal test as an audit criterion.

**Persona framing prohibition.** Criterion #10 (no "act as X" constructions) is backed by OpenSSF's September 2025 finding that persona framing reduces performance on the intended tasks [Tier 2: OpenSSF Security-Focused Guide for AI Code Assistants]. This is an empirically grounded prohibition, not a stylistic preference.

**Anti-pattern guards as a required section.** Requiring `## Anti-Pattern Guards` with at least one guard surfaces the skill's own failure modes at authoring time. This is a WOS-original structural requirement with no equivalent in any other platform. It encodes the failure analysis directly into the artifact.

**Progressive disclosure architecture.** The L1/L2/L3 model provides token efficiency no other runtime replicates. All-or-nothing context loading (all other platforms) forces skill authors to either write thin skills or load heavy context unconditionally.

**Structural contract over empirical-only validation.** WOS defines a behavioral contract at authoring time (`## Anti-Pattern Guards`, `## Handoff`, `## Key Instructions`, won't-do requirement) that is verifiable without running the skill. Anthropic's skill-creator validates quality *empirically* — run the skill, grade the output, iterate. Both approaches are valid; WOS's contract-first model is faster (no evaluation runs required) and surfaces scope and failure mode documentation as a direct artifact. The skill-creator's empirical model catches behavioral failures that static analysis cannot. WOS's approach is not a fallback — it's a deliberate separation of concerns: static analysis catches structural failures cheaply; empirical testing (G8) catches behavioral failures.

---

## 4. Strengths and Weaknesses Per Platform

### Anthropic skill-creator
**Strengths vs. WOS:** Behavioral evaluation infrastructure (parallel with/without-skill runs, grader agents, benchmark.json, iteration history); trigger evaluation loop with precision/recall measurement and iterative description optimization; concrete rationale-over-rigidity transformation pattern ("Instead of X, try Y because Z"); environment-specific degraded mode guidance (Claude.ai, Cowork); `package_skill.py` for distributable `.skill` files.
**Weaknesses vs. WOS:** No required structural sections (`## Anti-Pattern Guards`, `## Handoff`, `## Key Instructions` absent); no won't-do elicitation at creation time; no removal test; no systematic static audit comparable to check-skill; free-form skill body with no contract enforcement; no anti-pattern guard requirement; no formal separation of static vs. judgment-based quality checks.

### OpenAI
**Strengths vs. WOS:** Most mature behavioral evaluation infrastructure (4-axis success criteria framework, golden datasets, CI/CD integration via Evals); 2-level description hierarchy separates routing signal from usage context; "intern test" is a practitioner-accessible quality heuristic; explicit warning about examples for reasoning models (no analogous guidance in WOS's skill-authoring-guide).
**Weaknesses vs. WOS:** No structured scaffolding workflow; no equivalent to check-skill or build-skill; no removal test; no anti-pattern guards requirement; no won't-do elicitation; no LLM-level quality criteria; JSON Schema-only structure misses skill-body quality assessment.

### GitHub Copilot
**Strengths vs. WOS:** Empirically confirmed portability at spec minimum (cross-runtime verified); simpler authoring surface reduces onboarding friction; `.github/copilot-instructions.md` provides a familiar entry point analogous to CLAUDE.md.
**Weaknesses vs. WOS:** No authoring workflow, no quality checks, no discovery infrastructure beyond spec minimum; L2/L3 unavailable; subagent skill inheritance absent.

### OpenAI Codex skill-creator
**Strengths vs. WOS:** Explicit trigger-first intake ("what would users say?"); clear prohibition on body "When to Use" sections (which are routing-blind); `assets/` directory pattern separates output resources from context resources; UI-facing metadata separation (`agents/openai.yaml`) decouples routing copy from display copy; `init_skill.py` script-based scaffolding generates a template with TODO placeholders.
**Weaknesses vs. WOS:** No required structural sections; no won't-do elicitation; no removal test; no LLM-level quality audit; no anti-pattern guards requirement; free-form body; quick_validate.py only checks syntax, not quality.

### Yarmoluk Custom Skill Developer
**Strengths vs. WOS:** Embedded quality scoring rubric (self-assessment before output); 30-skill session limit documentation and meta-skill router pattern; "context window as public good" framing for token efficiency; comprehensive practitioner guide for intermediate users.
**Weaknesses vs. WOS:** Tier 3 source (practitioner, no peer review); no static/LLM audit separation; no removal test; no won't-do concept; embedded rubric creates per-skill authoring overhead without the benefits of centralized criteria.

### LangChain / Open-Source
**Strengths vs. WOS:** Programmatic tool definitions (Pydantic schemas) enable IDE-level syntax validation; pytest integration applies natively; broad community template library.
**Weaknesses vs. WOS:** No description authoring guidance; no removal test; no anti-pattern checks; no won't-do concept; schema-first routing model is a different architectural assumption that partially sidesteps description quality.

---

## 5. Tradeoffs Discussion

**G1: Primitive routing confirmation in build-skill**
Adding a one-sentence routing label ("Building this as a skill — is that right, or did you mean a hook, script, subagent, or context doc?") before elicitation adds one turn. The five-step pattern's binding constraint quantifies the cost: automatic classification fails ~10% of cases at GPT-4 performance, with rare primitives (hook, subagent) the most systematically misclassified [Tier 1: arXiv 2304.06597, CHI 2023]. A misclassified primitive wastes the entire scaffolding session. A single confirmation turn costs seconds. Tension: **"Keep it simple"** — adds one step. Mitigation: the label is one sentence, not a wizard; user confirms or redirects without justification gate.

**G2: Success criteria elicitation in build-skill**
A seventh elicitation field ("How will you know this skill worked?") creates the surface for future behavioral assertions before the skill is written. Tension: **"When in doubt, leave it out"** — if behavioral testing infrastructure (Layer 2–3) doesn't yet exist in WOS, collecting success criteria is forward-looking overhead. Mitigation: mark the field optional; skip it for simple skills.

**G3: Won't-do criterion in check-skill**
Build-skill requires at least one explicit won't-do in `## Key Instructions`. Check-skill has no criterion verifying this for existing skills. Adding criterion #11 enforces the same contract at audit time. No principal tension with WOS design principles. Edge case: read-only or narrow-scope skills may have no meaningful exclusions — pass condition must accommodate this.

**G4: Tier-aware criterion #2 + `tested_with` frontmatter**
`tested_with` is the "most honest tier signal" — it describes what the author verified, not a forward-looking capability claim [Tier 2: Anthropic Skill Authoring Best Practices; Tier 1: arXiv 2310.11324]. Making criterion #2 tier-aware reduces false positives for sub-frontier–targeted skills without changing the default threshold. Tension: **"When in doubt, leave it out"** for the optional field. Mitigation: no lint enforcement.

**G5: Portability annotations in skill-authoring-guide**
The guide currently validates WOS-idiomatic patterns (`argument-hint`, `context: fork`, `allowed-tools`) without flagging them as Claude Code-specific. Cross-platform authors receive no guidance. Purely informational — no enforcement. Tension: **"Depend on nothing"** — WOS is Claude Code-native. Mitigation: frame as informational, not prescriptive.

**G6: Contradiction detection in check-skill**
Anti-pattern #7 (contradictory rules, MODERATE evidence) is documented in the baseline but absent from check-skill criteria. Challenge: contradiction detection is a judgment check scoped to explicit same-scenario/opposite-directive conflicts, not semantic tension. No tension with WOS principles; aligns with "Structure in code, quality in skills."

**G7: Staleness/lifecycle guidance in skill-authoring-guide**
Anti-pattern #5 (stale rules) is ranked fifth with HIGH evidence: "A stale rules file is worse than no rules file in some cases" [Tier 2: MindStudio]. The guide has no lifecycle section. Adding one costs nothing and addresses a known high-evidence failure mode.

**G8: Layer 2–3 behavioral testing**
Highest-impact gap but out-of-scope for the four artifacts. Tension: **"Keep it simple"** and **"When in doubt, leave it out"** — entirely new infrastructure layer. The counterargument: Layer 2–3 uses pre-trained classifiers and regex assertions, not LLM API calls, so marginal cost per run is near zero once built. **skill-creator confirms the design:** its grader agents, evals.json expectations, and benchmark.json are essentially a Layer 2–3 implementation. The reference architecture is available to adapt.

**G9: Description trigger evaluation guidance**
Check-skill criterion #7 assesses static properties of the description (first sentence front-loads trigger, no second-person/passive voice). When criterion #7 fails — or when routing behavior is uncertain in practice — there is no guidance on *how to fix it systematically*. skill-creator's `run_loop.py` provides the systematic fix: generate 8–10 should-trigger + 8–10 should-NOT-trigger queries, split into train/test sets, run iterative description improvement, measure precision/recall. WOS can adopt the *concept* (trigger query sets + precision/recall framing) without adopting the full script infrastructure. Adding trigger evaluation guidance to skill-authoring-guide and a recommendation to check-skill criterion #7 costs nothing. Tension: **"When in doubt, leave it out"** — this is guidance without enforcement. Mitigation: guidance only; no new tooling required.

**G10: Rationale-over-rigidity transformation pattern**
WOS's skill-authoring-guide says "Rationale over rigidity" in the judgment check table. Check-skill implicitly assesses this via criterion #2 (ALL-CAPS density). Neither provides a concrete transformation example. skill-creator provides one: *"Instead of 'ALWAYS use markdown,' try 'Use markdown for readability since the user will review the output.'"* Adding this pattern to both the skill-authoring-guide judgment check and the check-skill criterion #2 repair guidance makes the abstract principle actionable. No new criterion needed — this updates existing text. No tension with WOS principles; aligns with "Omit needless words" (directives are needlessly emphatic when rationale is available).

**G11: "When to Use This Skill" body section as anti-pattern**
The OpenAI Codex skill-creator explicitly prohibits body-embedded "When to Use This Skill" sections: the body is only loaded after triggering, so routing guidance there is routing-blind. WOS's baseline context docs document ten anti-patterns but not this one. The `instruction-file-authoring-anti-patterns.context.md` should gain this as anti-pattern #11. Impact is high because this anti-pattern creates a false sense of routing completeness — an author who writes "Use this skill when..." in the body believes they've addressed routing; they haven't. Tension: none. Aligns with "Single source of truth" — the description is the routing signal, full stop.

**G12: `assets/` directory pattern in skill-authoring-guide**
WOS's skill-authoring-guide recognizes `references/` (loaded into context) but has no concept of `assets/` (output-bound files not loaded into context). A template file, an icon, a boilerplate HTML project — these should not consume context window tokens but are currently either forced into `references/` (wrong tier) or omitted entirely. Adding an `assets/` section to the skill-authoring-guide costs nothing to document and resolves a real authoring ambiguity. Tension: **"When in doubt, leave it out"** — most WOS skills may not need it. Mitigation: document as optional alongside `references/`.

**G13: 30-skill session limit documentation**
Claude Code loads a maximum of 30 skills per session. WOS's skill-authoring-guide and build-skill have no mention of this constraint. A project exceeding 30 skills silently drops some from context, and routing to them fails without error. This is a high-stakes runtime constraint. Adding a note to the skill-authoring-guide and a check-skill criterion for detecting potential routing failures in large skill ecosystems costs nothing to document. Tension: none. Aligns with "Bottom line up front" — this constraint should be surfaced, not hidden.

---

## 6. Gap Analysis

Ordered by Impact descending, Effort ascending:

| Gap | Source Platform | Impact | Effort | Principle Fit |
|-----|----------------|--------|--------|---------------|
| G3: check-skill missing won't-do enforcement (build-skill requires; check-skill doesn't verify) | WOS internal consistency | H | L | aligns |
| G1: build-skill missing primitive routing confirmation before elicitation | Anthropic research (five-step intake pattern) | H | L | conflicts: Keep it simple |
| G8: Layer 2–3 behavioral testing (no test-skill, no scripts/test.py) | OpenAI Evals, Anthropic skill-creator | H | H | conflicts: Keep it simple |
| G11: "When to Use This Skill" body sections are routing-blind anti-pattern (missing from context docs) | OpenAI Codex skill-creator | H | L | aligns |
| G9: check-skill criterion #7 missing trigger evaluation guidance on failure | Anthropic skill-creator (run_loop.py, run_eval.py) | M | L | aligns |
| G10: rationale-over-rigidity transformation pattern absent from guide and repair loop | Anthropic skill-creator | M | L | aligns |
| G6: check-skill missing contradiction detection criterion (anti-pattern #7 uncovered) | WOS baseline anti-pattern #7 | M | L | aligns |
| G2: build-skill missing success criteria elicitation (pre-commitment before authoring) | OpenAI Evals 4-axis framework | M | L | conflicts: When in doubt, leave it out |
| G4: check-skill criterion #2 not tier-aware; no `tested_with` frontmatter | Anthropic tier-aware guidance | M | L | aligns |
| G5: skill-authoring-guide missing portability annotations (no floor vs. extensions distinction) | Agent Skills cross-platform evidence | M | L | aligns |
| G12: skill-authoring-guide missing `assets/` directory pattern (output-bound vs. context-loaded resources) | OpenAI Codex skill-creator | M | L | aligns |
| G13: 30-skill session limit undocumented in skill-authoring-guide and build-skill | Yarmoluk guide | M | L | aligns |
| G7: skill-authoring-guide missing staleness/lifecycle guidance (anti-pattern #5 uncovered) | WOS baseline anti-pattern #5 | M | L | aligns |

---

## 7. Implementation Mapping

| Gap | Target | Specific Change | Compatibility |
|-----|--------|-----------------|---------------|
| G3: Missing won't-do criterion | `check-skill` | New criterion #11: **Won't-do scope** — Pass condition: `## Key Instructions` contains at least one explicit scope exclusion ("Won't…", "Does not…", "Excluded:", or equivalent negative boundary statement); acceptable pass if the skill's entire Workflow is read-only and the Handoff's Receives/Produces fields unambiguously constrain scope with no plausible overreach | No conflict with existing criteria #1–#10; no lint.py change (judgment check); consistent with anti-pattern #8; adds one row to the LLM checks table |
| G1: Primitive routing confirmation | `build-skill` | Modify Step 1 (Elicit) — prepend a routing label before the elicitation table: surface "Building this as a **skill** (triggered instruction set). Right primitive? Or did you mean a hook, script, context doc, or subagent?" If the user's request is unambiguous, acknowledge and proceed to elicitation without a gate. If uncertain, ask one targeted clarification question. Do not require justification before proceeding. Add anti-pattern guard #6: **Routing without confirmation** — when user intent is plausibly a hook, script, or subagent, silently scaffolding a skill wastes the session; surface a routing label first. | No change to lint.py; no change to criteria numbering; adds one conditional exchange at the top of Step 1 and one row to the anti-pattern guards table; consistent with five-step pattern's anti-pattern list (no justification gate, no silent routing) |
| G6: Contradiction detection | `check-skill` | New criterion #12: **Contradiction-free** — Pass condition: no two rules in the skill body produce explicitly opposite directives for the same scenario; flag as fail only when Rule A says "always X" and Rule B says "never X" in the same or overlapping trigger context (within `## Key Instructions` or `## Anti-Pattern Guards`). Semantic tension and trade-off language ("prefer X unless Y") is not a contradiction. | No lint.py change (judgment check); no conflict with existing criteria #1–#11; assessment requires reading full Key Instructions and Anti-Pattern Guards sections |
| G2: Success criteria elicitation | `build-skill` | Add elicitation field **Success criteria** (optional, row 7 of elicitation table): "How will you know this skill worked? (e.g., 'A file is written to the expected path with correct frontmatter')" — If provided, write as `**Validates as:**` subfield under `## Handoff`. If omitted, proceed normally; do not block. | No lint.py change; adds one optional row to elicitation table; `## Handoff` gains optional `Validates as:` subfield; no conflict with existing criteria |
| G4: Tier-aware criterion #2 + `tested_with` | `skill-authoring-guide + check-skill` | **skill-authoring-guide:** Add `tested_with` to optional frontmatter table — `tested_with: [haiku, sonnet, opus]`; description: "Record of which models the author verified against. More honest than a forward-looking min_model_tier claim. Cross-tier skills should include at least one sub-frontier target." **check-skill:** Modify the note after criterion #2 — add: "If `tested_with` is present and includes only sub-frontier models (e.g., haiku), flag ALL-CAPS density ≥3 as informational rather than warn — stronger directives are calibrated differently for lower-tier targets. Default (no `tested_with`) retains the warn threshold." | No lint.py change (`tested_with` is metadata, not validated statically); modifies existing criterion #2 note without renumbering; no change to the ≥3 threshold; skill-authoring-guide frontmatter table gains one optional row |
| G5: Portability annotations | `skill-authoring-guide` | Add section **Cross-Platform Portability** after the Reference Files section: "The Agent Skills spec minimum (`name` + `description` + a flat markdown body that fits the initial context window) is confirmed portable across Claude Code and GitHub Copilot CLI. Every WOS-idiomatic extension above that floor — `context: fork`, `allowed-tools`, `references/` directories, `!<command>` injection, `model`/`effort` — is Claude Code-specific and will not function on other runtimes. If writing a cross-platform skill, author to the spec minimum and test on the target runtime before distributing. Writing to the spec minimum forfeits dynamic context injection, fork isolation, tool scoping, and progressive reference loading — the features that make WOS skills structurally powerful." | No lint.py change; no check-skill criterion needed (informational section); no conflict with existing sections; does not alter any automated check thresholds |
| G7: Staleness/lifecycle guidance | `skill-authoring-guide` | Add section **Skill Lifecycle and Staleness** after the Evaluation Criteria section: "Skills are not static documents. Three triggers for review: (1) a framework, API, or CLI tool referenced in the skill has changed version; (2) the skill was authored and `tested_with` a model tier that is no longer default; (3) a rule passes check-skill but is never followed in practice — confirm via removal test (would removing it cause a mistake today?). A stale rules file is actively harmful: it misleads agents toward deprecated patterns with more authority than silence. Schedule a check-skill audit at each major dependency upgrade. Add a `reviewed:` date to frontmatter after each audit." | No lint.py change; no check-skill criterion change (guidance only); consistent with anti-pattern #5 (HIGH evidence); `reviewed:` date recommendation is optional frontmatter |
| G8: Layer 2–3 behavioral testing | `out-of-scope` | Cannot be addressed in any of the four curation artifacts. Requires: (a) a new `test-skill` skill for authoring and running behavioral assertions; (b) a new `scripts/test.py` implementing Layer 2 deterministic assertions (regex matching for required patterns, JSON parse, word count bounds) and Layer 3 embedding similarity against a small golden output set; (c) a golden dataset convention for high-stakes skills. **Reference implementation:** Anthropic's skill-creator provides the architectural model — `evals/evals.json` (test case definitions), `agents/grader.md` (output evaluation), `scripts/aggregate_benchmark.py` (benchmark aggregation), and `scripts/run_loop.py` (trigger evaluation loop). A WOS adaptation would need to work within the existing `scripts/` and `skills/` conventions. If G2 (success criteria elicitation) is implemented, the `Validates as:` subfield provides the specification surface for behavioral assertions at Layer 2. |
| G9: Trigger evaluation guidance | `skill-authoring-guide + check-skill` | **skill-authoring-guide:** Add subsection **Trigger Evaluation** under the existing description section: "When description routing quality is uncertain or criterion #7 fails, validate empirically: generate 8–10 queries a user would say to trigger this skill (should-trigger) and 8–10 near-miss queries that should NOT trigger it (similar intent, different skill). Test each against the live skill. Calculate precision (correct activations / total activations) and recall (correct activations / total should-trigger queries). Adjust the description's trigger clause until both exceed 80%. Reference: Anthropic skill-creator `run_loop.py` for a full automated implementation." **check-skill:** Modify criterion #7's pass condition to add: "If routing behavior is uncertain after static assessment, flag as 'recommend trigger evaluation' — see skill-authoring-guide trigger evaluation subsection." | No new criterion number; modifies existing criterion #7 text; no lint.py change; skill-authoring-guide adds one subsection under description section |
| G10: Rationale-over-rigidity transformation pattern | `skill-authoring-guide + check-skill` | **skill-authoring-guide:** Update the "Rationale over rigidity" row in the Judgment checks table — add a transformation example: "Before: 'ALWAYS use markdown.' After: 'Use markdown — the user will review this output and markdown renders in the UI.' The transformation pattern: directive → same behavior + reason why the behavior matters." **check-skill:** Modify the note after criterion #2 (ALL-CAPS density) to add: "When flagging ALL-CAPS directives, suggest the transformation: convert 'ALWAYS X' to 'X — because [reason why X matters in this skill's context].' This produces more intelligent adaptation than compliance enforcement." | Modifies existing skill-authoring-guide judgment check table row (no new row); modifies existing criterion #2 note without renumbering; no lint.py change |
| G11: "When to Use This Skill" body section anti-pattern | `context-docs` | Update `instruction-file-authoring-anti-patterns.context.md`: add anti-pattern #11 — **Body-embedded routing guidance** — "Any 'When to Use This Skill' or trigger-condition guidance written in the SKILL.md body is routing-blind: the body is loaded only after the skill triggers, so routing guidance inside it is never seen at routing time. All trigger conditions must appear in the `description` frontmatter field. Evidence: OpenAI Codex skill-creator explicitly prohibits this pattern [Tier 1]; consistent with WOS's L1/L2/L3 loading model (L1 is the only pre-trigger signal). Severity: HIGH — creates false routing completeness." | Adds one row to the anti-patterns table; no lint.py change; no check-skill criterion change needed (criterion #7 already checks description routing quality; this anti-pattern is about misplacing routing guidance in the body, not about description quality) |
| G12: `assets/` directory pattern | `skill-authoring-guide` | Add subsection **`assets/` (optional)** after the Reference Files section: "A third directory type for output-bound files not loaded into context: templates, images, boilerplate code, icons, fonts, or any file used in skill output but not needed for Claude's reasoning. Unlike `references/` (loaded into context on demand), `assets/` files are referenced in output paths but never injected into the context window. Use `assets/` when the skill produces files (reports with images, code projects from templates) and the source material should not consume context tokens. One level deep from SKILL.md, same as `references/`." | No lint.py change; no check-skill criterion needed; new subsection under Reference Files; clarifies an authoring ambiguity without enforcing new constraints |
| G13: 30-skill session limit | `skill-authoring-guide` | Add a note in the Size Limits subsection of SKILL.md Body: "**Session limit:** Claude Code loads a maximum of 30 skills per session. In projects with more than 30 skills, some will not be loaded and routing to them will silently fail. If your project exceeds 30 skills, use a meta-skill router: a single routing skill that dispatches to sub-skills via keyword matching, consolidating multiple related skills into one entry point. Meta-routers count as one toward the 30-skill limit." | No lint.py change; no check-skill criterion needed; adds a factual note to an existing section; could optionally trigger a lint.py warning when `wos/discovery.py` detects >30 skill directories (future enhancement, not in scope for the four artifacts) |
