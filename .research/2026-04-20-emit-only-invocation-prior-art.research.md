---
name: "Emit-Only Invocation — Prior Art and Naming Candidates"
description: "Landscape survey finds strong cross-framework convergence on the 'agent-as-tool' / 'skill-as-tool' metaphor (OpenAI Agents SDK, LangGraph, Semantic Kernel) and MCP's tools/call as the closest protocol-level shape match. Recommends --as-tool as the flag name, with output shape inheriting MCP field vocabulary (inputSchema, outputSchema, structuredContent, isError)."
type: research
sources:
  - https://modelcontextprotocol.io/specification/2025-06-18/server/tools
  - https://code.claude.com/docs/en/headless
  - https://openai.github.io/openai-agents-python/tools/
  - https://openai.github.io/openai-agents-python/handoffs/
  - https://docs.langchain.com/oss/python/langgraph/use-subgraphs
  - https://learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/agent-functions
  - https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/framework/agent-and-agent-runtime.html
  - https://git-scm.com/docs/git-status
  - https://git-scm.com/book/en/v2/Git-Internals-Plumbing-and-Porcelain
  - https://www.baeldung.com/ops/kubectl-output-format
related:
  - .context/skill-handoff-contracts-and-state-design.context.md
  - .context/skill-chaining-definition-and-vocabulary.context.md
  - .context/skill-chain-sequential-and-recursive-design-rules.context.md
  - .context/skill-chain-handoff-signaling-and-evidence-packs.context.md
---

# Emit-Only Invocation — Prior Art and Naming Candidates

## Key Findings (top-of-page summary)

1. **The pattern is not novel.** MCP's `tools/call` (with `inputSchema` / `outputSchema` / `structuredContent` / `isError`) is a near-exact protocol-level match; OpenAI Agents SDK's `Agent.as_tool()` is the closest named equivalent at the agent-framework level; LangGraph, Semantic Kernel, and AutoGen each have analogues under different method names. (HIGH)

2. **The highest-recognition metaphor is "agent as tool" / "skill as tool."** OpenAI, LangGraph, and Semantic Kernel all use variants of this phrase at T1 sources. Method names differ (`as_tool`, `invoke`, `add_plugin`, `send_message`); the metaphor converges. (HIGH)

3. **"Handoff" is reserved.** Both OpenAI's SDK and toolkit's own `.context/` docs use "handoff" for the *opposite* case (transferring the user-facing conversation). We must not reuse it for our pattern. (HIGH)

4. **Anthropic's vocabulary is distributed, not unified.** `-p` / `--print` (non-interactive), `--output-format json` / `--json-schema` (structured output), `--bare` (ceremony suppression), `--allowedTools` (approval suppression). No single Anthropic term names the combined pattern. `--bare` is the closest single-flag match for ceremony suppression and is "recommended for scripted and SDK calls." (HIGH)

5. **`--porcelain` is a terminology trap.** Git's `--porcelain` flag has the right stability-contract DNA ("will remain stable across Git versions") but the porcelain/plumbing metaphor inverts in ways the community has documented as confusing. Do not reuse the word. (HIGH)

6. **Recommendation (LCD): rename the flag `--as-tool`; adopt MCP field vocabulary for the structured output.** Flag name inherits the strongest cross-framework recognition signal. Output shape (`inputSchema`, `outputSchema`, `structuredContent`, `isError`) inherits MCP's protocol-level legibility without requiring JSON-RPC or a tool catalog — we cite the shape, we don't implement the transport. This gives any future skill author familiar with OpenAI Agents SDK, MCP, LangGraph, or Semantic Kernel a way to locate our pattern via concepts they already know. (MODERATE — recommendation, not an observed convention.)

## Research Question

Does the pattern we are tentatively calling "emit-only invocation contract" — one agent/skill invokes another at runtime with structured arguments plus a sentinel flag that suppresses UI ceremony (intake prompts, approval gates, file writes) and forces the callee to return structured output — already exist under another name in prior art? Favor the least-common-denominator name.

## Sources

| # | URL | Title | Author/Org | Date | Tier | Status |
|---|-----|-------|------------|------|------|--------|
| 1 | https://modelcontextprotocol.io/specification/2025-06-18/server/tools | Tools (MCP spec 2025-06-18) | Model Context Protocol / Anthropic | 2025-06-18 | T1 (standards body / official spec) | verified |
| 2 | https://code.claude.com/docs/en/headless | Run Claude Code programmatically (formerly "Headless Mode") | Anthropic | 2026 | T1 (official docs) | verified (redirect from docs.anthropic.com) |
| 4 | https://openai.github.io/openai-agents-python/tools/ | Tools — Agents as Tools (`as_tool`) | OpenAI | 2025 | T1 (official docs) | verified |
| 5 | https://openai.github.io/openai-agents-python/handoffs/ | Handoffs | OpenAI | 2025 | T1 (official docs) | verified |
| 7 | https://docs.langchain.com/oss/python/langgraph/use-subgraphs | LangGraph — Use Subgraphs | LangChain | 2025 | T1 (official docs) | verified |
| 8 | https://learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/agent-functions | Configuring Agents with Semantic Kernel Plugins | Microsoft | 2026-02-23 | T1 (official docs) | verified |
| 9 | https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/framework/agent-and-agent-runtime.html | Agent and Agent Runtime | Microsoft (AutoGen) | 2025 | T1 (official docs) | verified |
| 10 | https://git-scm.com/docs/git-status | git-status (--porcelain) | Git / Software Freedom Conservancy | 2025 | T1 (official docs) | verified |
| 11 | https://git-scm.com/book/en/v2/Git-Internals-Plumbing-and-Porcelain | Pro Git — Plumbing and Porcelain | Chacon & Straub / Git | 2014+ | T1 (canonical community reference, endorsed by git-scm.com) | verified |
| 12 | https://www.baeldung.com/ops/kubectl-output-format | Guide to kubectl Output Formatting | Baeldung | 2024 | T4 (expert practitioner, non-official) | verified |
| I-1 | .context/skill-chaining-definition-and-vocabulary.context.md | Skill Chaining — Definition and Vocabulary | toolkit `.context/` (synthesized from Anthropic / OpenAI primaries) | 2026 | T1 (internal authoritative, derived from T1 web sources) | verified |
| I-2 | .context/skill-handoff-contracts-and-state-design.context.md | Skill Handoff Contracts and State Design | toolkit `.context/` (synthesized from Anthropic / OpenAI / Semantic Kernel / LangChain primaries) | 2026 | T1 (internal authoritative) | verified |
| I-3 | .context/skill-chain-sequential-and-recursive-design-rules.context.md | Skill Chain Sequential and Recursive Design Rules | toolkit `.context/` | 2026 | T1 (internal authoritative) | verified |
| I-4 | .context/skill-chain-handoff-signaling-and-evidence-packs.context.md | Skill Chain Handoff Signaling and Evidence Packs | toolkit `.context/` (synthesized from Copilot Studio, Nielsen Norman, academic sources) | 2026 | T1 (internal authoritative) | verified |

## Extracts by Sub-Question

### 1. Anthropic / Claude Code surface

Source [2] — **Claude Code Headless / Programmatic Invocation** (`https://code.claude.com/docs/en/headless`, Anthropic, 2026).

Re: naming and the fact that the pattern exists as first-class API:
> "The CLI was previously called 'headless mode.' The `-p` flag and all CLI options work the same way."

Re: non-interactive invocation:
> "Add the `-p` (or `--print`) flag to any `claude` command to run it non-interactively."

Re: structured JSON return:
> "Use `--output-format` to control how responses are returned: `text` (default): plain text output; `json`: structured JSON with result, session ID, and metadata; `stream-json`: newline-delimited JSON for real-time streaming."

Re: forcing schema-conforming structured output:
> "To get output conforming to a specific schema, use `--output-format json` with `--json-schema` and a [JSON Schema] definition. The response includes metadata about the request (session ID, usage, etc.) with the structured output in the `structured_output` field."

Re: a second, separate flag that suppresses discovery / ceremony — this is the flag whose mental model matches "emit-only":
> "Add `--bare` to reduce startup time by skipping auto-discovery of hooks, skills, plugins, MCP servers, auto memory, and CLAUDE.md. Without it, `claude -p` loads the same context an interactive session would."

> "Bare mode is useful for CI and scripts where you need the same result on every machine. A hook in a teammate's `~/.claude` or an MCP server in the project's `.mcp.json` won't run, because bare mode never reads them. Only flags you pass explicitly take effect."

> "`--bare` is the recommended mode for scripted and SDK calls, and will become the default for `-p` in a future release."

Re: explicit note that user-invoked skills are UI-only in `-p` mode (so the UI surface actually collapses away):
> "User-invoked [skills](/en/skills) like `/commit` and [built-in commands](/en/commands) are only available in interactive mode. In `-p` mode, describe the task you want to accomplish instead."

Re: tool auto-approval (ceremony suppression):
> "Use `--allowedTools` to let Claude use certain tools without prompting."

> "`dontAsk` denies anything not in your `permissions.allow` rules or the read-only command set, which is useful for locked-down CI runs."

**Anthropic's own labels for this pattern:** "headless mode" (legacy), "run programmatically", `-p` / `--print`, `--bare`, `--output-format json`, `--json-schema`, `--allowedTools`, `dontAsk` permission mode. No single named contract; the pattern is assembled from three orthogonal flags (non-interactive + structured-output + ceremony-suppressed).

### 2. MCP contract semantics

Source [1] — **MCP Specification 2025-06-18, Server/Tools** (`https://modelcontextprotocol.io/specification/2025-06-18/server/tools`).

Re: what a tool call is:
> "The Model Context Protocol (MCP) allows servers to expose tools that can be invoked by language models. Tools enable models to interact with external systems, such as querying databases, calling APIs, or performing computations. Each tool is uniquely identified by a name and includes metadata describing its schema."

Re: tool-is-model-controlled (no UI by default):
> "Tools in MCP are designed to be **model-controlled**, meaning that the language model can discover and invoke tools automatically based on its contextual understanding and the user's prompts. However, implementations are free to expose tools through any interface pattern that suits their needs—the protocol itself does not mandate any specific user interaction model."

Re: structured args in (`tools/call` request):
> "To invoke a tool, clients send a `tools/call` request ... `method`: `tools/call`, `params`: `{ name, arguments }`."

Re: structured output type (`structuredContent`):
> "**Structured** content is returned as a JSON object in the `structuredContent` field of a result. For backwards compatibility, a tool that returns structured content SHOULD also return the serialized JSON in a TextContent block."

Re: output schema contract:
> "Tools may also provide an output schema for validation of structured results. If an output schema is provided: Servers **MUST** provide structured results that conform to this schema. Clients **SHOULD** validate structured results against this schema."

Re: error reporting inside the structured result (not a thrown exception):
> "Tool Execution Errors: Reported in tool results with `isError: true`: API failures, Invalid input data, Business logic errors."

Re: UI is a client concern, **not** a protocol concern (the suppression is the default direction of the spec):
> "However, implementations are free to expose tools through any interface pattern that suits their needs—the protocol itself does not mandate any specific user interaction model."

**MCP's labels for this pattern:** "tool", "tool call" (`tools/call`), "inputSchema", "outputSchema", "structuredContent", "isError", "model-controlled". MCP's tool-call semantics are almost exactly the user's "emit-only invocation": structured args in, structured content out, error-as-field, UI explicitly not mandated.

### 3. Agent-framework equivalents

Source [4] — **OpenAI Agents SDK — Tools (agents as tools)** (`https://openai.github.io/openai-agents-python/tools/`, OpenAI, 2025).

Re: the named pattern:
> "In some workflows, you may want a central agent to orchestrate a network of specialized agents, instead of handing off control. You can do this by modeling agents as tools."

Re: the method name:
> "The method to expose an agent as a tool is `agent.as_tool()`, which accepts parameters like `tool_name` and `tool_description` to customize how the sub-agent appears to the orchestrating agent."

Re: structured inputs:
> "By default, `Agent.as_tool()` expects a single string input (`{\"input\": \"...\"}`), but you can expose a structured schema by passing `parameters` (a Pydantic model or dataclass type)."

Re: structured output extraction:
> "The `custom_output_extractor` argument enables modification of tool-agent outputs before returning to the central agent, allowing extraction of specific information, reformatting, or validation of responses."

Source [5] — **OpenAI Agents SDK — Handoffs** (`https://openai.github.io/openai-agents-python/handoffs/`, OpenAI, 2025).

Re: agent-as-tool vs handoff — the SDK's *own* distinction:
> "Handoffs allow an agent to delegate tasks to another agent."

> "If you want structured input for a nested specialist without transferring the conversation, prefer `Agent.as_tool(parameters=...)`"

Interpretation: OpenAI's documented vocabulary explicitly uses "**agent as tool**" (method: `as_tool()`) for the case where a caller wants structured input to a nested agent without handing off the user-facing conversation. "Handoff" is the *opposite* case (transfer control). This maps almost 1:1 to the user's pattern name.

Web search result summary (Source [4] parent page):
> "Agents as tools are used when a specialist should help with a bounded subtask but should not take over the user-facing conversation. Handoffs are used when routing itself is part of the workflow..."

Source [7] — **LangGraph — Use Subgraphs** (`https://docs.langchain.com/oss/python/langgraph/use-subgraphs`, LangChain, 2025).

Re: invocation shape (structured state in, structured state out):
> "invoke the subgraph inside a node function. This is common when you want to keep a private message history"

> "Transform the state to the subgraph state before invoking the subgraph, and transforms the results back to the parent state before returning"

Re: literal method:
> "subgraph_output = subgraph.invoke({\"bar\": state[\"foo\"]})"

Re: subgraphs-as-tools (the variant that matches "emit-only invocation"):
> "Wrap subagent as a tool for the outer agent"

> "response = fruit_agent.invoke({\"messages\": [{\"role\": \"user\", \"content\": question}]})"

LangGraph's native terminology for this pattern is `invoke()` / "subgraph as tool" / "subagent as tool". UI is not mentioned because LangGraph has no UI layer to suppress — it's purely a library, so every call is de-facto emit-only.

Source [8] — **Semantic Kernel — Configuring Agents with Plugins** (`https://learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/agent-functions`, Microsoft, updated 2026-02-23).

Re: agents as invokable functions:
> "Function calling is a powerful tool that allows developers to add custom functionalities and expand the capabilities of AI applications. The Semantic Kernel Plugin architecture offers a flexible framework to support Function Calling. For an `Agent`, integrating Plugins and Function Calling is built on this foundational Semantic Kernel feature."

Re: manual-mode (suppress auto-invoke — caller decides):
> "Manual function invocation provides more control over the function execution process. When this mode is enabled, the Semantic Kernel does not automatically invoke the functions chosen by the AI model. Instead, it returns a list of chosen functions to the caller, who can then decide which functions to invoke, handle exceptions, and manage the order of function calls." (from web search summary of the Function Calling sibling page)

Re: agent-as-KernelFunction:
> "As of SK Python 1.27.0, there's a way to create a plugin from an agent. Although the agent can be run as a Plugin/KernelFunction ... You'd need to create a prompt function, add the agent to the kernel like kernel.add_plugin(my_agent), and enable auto function calling, which could call into the Agent." (search summary; example: `chat_completion_agent_as_kernel_function.py`)

Semantic Kernel's term is `KernelFunction` / "agent as KernelFunction" / "plugin from an agent". No native sentinel flag for UI suppression because SK has no default UI; the equivalent toggle is `FunctionChoiceBehavior.Auto(auto_invoke=False)`.

Source [9] — **AutoGen Core — Agent and Agent Runtime** (`https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/framework/agent-and-agent-runtime.html`, Microsoft, 2025).

Re: agent-to-agent invocation primitive:
> "Within a message handler, you can use the `autogen_core.BaseAgent.send_message()` method, and from the runtime use the `autogen_core.AgentRuntime.send_message()` method. Awaiting calls to these methods will return the return value of the receiving agent's message handler." (summary of docs)

Re: structured messages:
> "Messages are serializable objects that can be defined using dataclasses, such as TextMessage with content and source attributes, or ImageMessage with url and source attributes."

Re: UI absence in the primitive:
> "The documentation contains no discussion of UI interaction as part of the Agent and Agent Runtime framework. The focus remains entirely on programmatic agent-to-agent and application-to-agent communication patterns."

AutoGen's terms: `send_message`, `AgentRuntime`, typed message dataclasses. Closest match to "emit-only invocation" but not named as a pattern; it's simply how the runtime works.

### 4. CLI flag naming precedent

Source [10] — **git-status manual** (`https://git-scm.com/docs/git-status`).

Re: the stability contract that defines the "porcelain" mental model:
> "`--porcelain[=<version>]` — Give the output in an easy-to-parse format for scripts. This is similar to the short output, but will remain stable across Git versions and regardless of user configuration."

Re: contrast with human-readable output:
> "The output from this command is designed to be used as a commit template comment. The default, long format, is designed to be human readable, verbose and descriptive. Its contents and format are subject to change at any time."

Re: stability guarantee:
> "Version 1 porcelain format is similar to the short format, but is guaranteed not to change in a backwards-incompatible way between Git versions or based on user configuration. This makes it ideal for parsing by scripts."

Re: config suppression (ceremony suppression) — what `--porcelain` specifically disables:
> "1. The user's `color.status` configuration is not respected; color will always be off. 2. The user's `status.relativePaths` configuration is not respected; paths shown will always be relative to the repository root."

Source [11] — **Pro Git Book — Plumbing and Porcelain** (`https://git-scm.com/book/en/v2/Git-Internals-Plumbing-and-Porcelain`).

Re: origin of the terminology we might reuse:
> "Git was initially a toolkit for a version control system rather than a full user-friendly VCS, it has a number of subcommands that do low-level work and were designed to be chained together UNIX-style or called from scripts. These commands are generally referred to as Git's 'plumbing' commands, while the more user-friendly commands are called 'porcelain' commands."

> "Many of these commands aren't meant to be used manually on the command line, but rather to be used as building blocks for new tools and custom scripts."

**Caveat for LCD naming:** In Git's vocabulary, "porcelain" is the *human-friendly* side and "plumbing" is the *machine-callable* side. Confusingly, the `--porcelain` FLAG on a porcelain command means "give me plumbing-shaped output." This overloading is a documented source of confusion (see Stefan Judis TIL, Oreate AI Blog search result titles). A naming that leans on "porcelain" will inherit this ambiguity.

Source [12] — **Baeldung — Guide to kubectl Output Formatting** (`https://www.baeldung.com/ops/kubectl-output-format`).

Re: the `-o json` / `-o yaml` mental model (structured output for automation):
> "The json and yaml output formats retrieve the entire representation of the resources from the Kubernetes cluster. This is in contrast to the default tabular format, which is more human-readable but limited in scope."

> "Both JSON and YAML are ideal for scripting because they provide consistent, parseable structured data that can be reliably processed by automation tools, unlike the human-friendly tabular output."

**CLI flag naming summary:**

| Flag | What it actually does | Mental model match |
|------|----------------------|---------------------|
| `git --porcelain` | Stable script-parseable output; suppresses color & user config | Strong: stability + ceremony suppression + parseable. But terminology is inverted vs. Git's plumbing/porcelain dichotomy. |
| `kubectl -o json` / `-o yaml` | Full resource representation in structured format; contrasts with default tabular | Medium: output-shape only; does not suppress approval or interactivity. |
| `curl --silent` / `-s` | Suppresses progress meter / error messages | Narrow: suppression only; no structured output guarantee. |
| `--non-interactive` (wget, apt, ssh) | No prompts; fail rather than ask | Narrow: suppression only; overloaded across tools with slightly different meanings. |
| `--headless` (chrome, claude code legacy) | Run without UI; produce final result | Strong but device/context-specific; Anthropic explicitly deprecated the label ("CLI was previously called 'headless mode'"). |
| `--batch` (gpg, various) | No tty, no prompts, machine-consumable output | Strong; inherits from Unix batch-processing tradition. |
| `-p` / `--print` (claude code) | Non-interactive, prints result and exits | Strong but ambiguous — "print" overloaded. |
| `--bare` (claude code) | Skip auto-discovery of hooks/skills/plugins/MCP | Strong for the *ceremony suppression* axis specifically. |

### 5. Internal toolkit adjacency

Source [I-1] — `.context/skill-chaining-definition-and-vocabulary.context.md` (toolkit repo).

Re: already-established terms:
> "The dominant practical vocabulary is 'prompt chaining' or 'sequential orchestration': decomposing a task into subtasks where each LLM call processes the output of the previous one."

> "Terms used interchangeably in practice: prompt chaining, skill chaining, agent pipeline, sequential orchestration, chain-of-thought, workflow composition."

> "Anthropic: 'workflows' where 'LLMs and tools are orchestrated through predefined code paths,' with prompt chaining as 'sequential steps where each LLM call processes the output of the previous one.'"

Source [I-2] — `.context/skill-handoff-contracts-and-state-design.context.md` (toolkit repo).

Re: **committed vocabulary we would contradict or overlap**:
> "Three components are necessary for clean skill handoffs: output contracts, shared state, and an orchestrator (HIGH confidence, T1 sources converge)."

> "**Output contracts** — each skill declares what structured fields it produces and what it requires as input."

> "**Shared state** — a single source of truth persists across skill invocations."

> "**Orchestrator** — reads state, identifies the current stage, invokes the appropriate skill, validates the output, and advances to the next step."

Re: how outputs are already specified:
> "Plain text outputs are fragile. Every major framework (Anthropic, OpenAI, Microsoft Semantic Kernel, LlamaIndex) provides typed schema mechanisms for inter-skill communication."

> "Define required output fields; allow additional fields freely. Compact returns: pass only what the next step needs, not a full transcript of the skill's internal state."

Re: error-handling convention (matches MCP `isError` and our proposal):
> "Error fields, not exceptions, are the standard at skill boundaries. When a skill fails: 1. Write an error field with a plain-language description into the state object. 2. The orchestrator reads the error and decides: retry, skip, or escalate."

Source [I-3] — `.context/skill-chain-sequential-and-recursive-design-rules.context.md` (toolkit repo).

Re: established validation/idempotency vocabulary:
> "**1. Follow the complexity ladder.** Direct model call → single agent with tools → multi-agent sequential chain."

> "**2. Validate at every boundary.** The orchestrator checks output quality before passing to the next skill. Malformed, low-confidence, or off-topic outputs must be retried or halted — not propagated."

> "**3. Use error fields, not exceptions.** Skills write failure state into their output so the orchestrator can decide whether to retry, skip, or escalate."

> "**4. Design for idempotency.** Side-effectful skills should accept idempotency tokens and check already-completed steps before re-executing."

Source [I-4] — `.context/skill-chain-handoff-signaling-and-evidence-packs.context.md` (toolkit repo).

Re: the user-facing handoff model (which "emit-only" would *bypass*):
> "Three Required Elements at Every Skill Boundary ... 1. Closure signal — what this skill accomplished ... 2. Intent preview — what the next skill will do, with explicit user choices ... 3. Provenance tag — which skill produced the output."

Re: the two-channel distinction we are effectively choosing between:
> "The two-channel model (Copilot Studio): user-facing messages should be concise and decision-focused; skill-facing state should carry the full structured output. These are separate channels with separate audiences."

**Toolkit vocabulary we would need to reconcile with:**

| Committed term | Location | "Emit-only invocation" relationship |
|----------------|----------|--------------------------------------|
| **handoff** | I-2, I-4 | Handoff implies a user-facing gate with closure signal + intent preview. Emit-only explicitly suppresses this. We'd contradict "handoff" if we reuse the word. |
| **orchestrator** | I-2, I-3 | Orchestrator is the *caller* in the emit-only pattern. No contradiction; emit-only is one invocation style the orchestrator may choose. |
| **output contract** | I-2 | Direct superset. Emit-only is an output contract plus an input contract plus a UI-suppression flag. |
| **shared state** | I-2 | Potential conflict: emit-only returns structured output directly (no shared file). The pattern could be framed as "skip shared state for this call" or as a degenerate shared state. |
| **skill chaining / chain** | I-1 | Emit-only is the *unit invocation* inside a chain. Compatible. |
| **two-channel model** | I-4 | Direct match. Emit-only is the skill-facing channel with the user-facing channel collapsed. |

## Challenge

### Assumptions

| Assumption | Supporting Evidence | Counter-Evidence | Impact if False |
|------------|--------------------|-----------------|-----------------|
| MCP's `tools/call` is "near-exact" prior art for our pattern. | Source [1]: structured args in, structured content out, `isError` field, explicit "no UI mandated by protocol." Shape maps 1:1 with emit-only semantics. | MCP operates at a JSON-RPC transport layer with tool registration and a server component. Our pattern operates at the SKILL.md markdown layer (no catalog, no server, no JSON-RPC). MCP's "not mandating UI" is about the protocol, not about a caller suppressing a callee's UI. | If we claim "this is just MCP," users expect JSON-RPC and server conventions; the gap confuses rather than clarifies. Safer framing: "analogous to MCP tool-call semantics at the SKILL level." |
| OpenAI Agents SDK's `Agent.as_tool()` is the closest *named* match. | Source [4]: SDK's own prose contrasts `as_tool` with `handoff` on exactly our axis ("keep user conversation" vs "transfer control"). Method name + parameter type + output extractor map cleanly. | OpenAI's `as_tool` is a Python method; ours is a runtime flag on a markdown skill. The SDK registers tools explicitly; we rely on the invoking LLM's interpretation of SKILL.md prose. | If we borrow only the word "as-tool" without the registration ergonomics, users may expect introspection that isn't there. Safer: borrow the *term* but document the delta. |
| "Handoff" is off-limits because the toolkit already uses it for user-facing gates. | Sources [I-2], [I-4]: "handoff" is the word used for closure-signal + intent-preview + provenance-tag at user-facing boundaries. OpenAI's SDK uses "handoff" for the same (user-transfer) sense. | None found. Both external (OpenAI) and internal (`.context/`) vocabularies converge. | Low risk — conventions align. |
| `--porcelain` carries a useful stability-contract mental model. | Source [10]: "will remain stable across Git versions." Source [11]: design intent explicitly for "chained ... or called from scripts." | Source [11] inverts the terminology — `--porcelain` flag outputs plumbing-shaped data from porcelain commands. This overloading is documented as a source of confusion in Git community writing. | If we adopt `--porcelain` literally, we inherit Git's inversion trap. Better: cite `--porcelain`'s stability-contract *idea* without reusing the word. |
| The community is converging on "agent as tool" / "skill as tool". | OpenAI `as_tool`, LangGraph "subgraph as tool", Semantic Kernel "agent as KernelFunction" / "plugin from an agent" all use the same metaphor. | Each framework names the operation differently at method level (`as_tool`, `invoke`, `add_plugin`). Only the *metaphor* converges, not the API. | The metaphor is the LCD, not the API name. Adopting "as-tool" conveys intent; adopting any one SDK's method name overclaims API compatibility. |

### Premortem

**Scenario: six months from now, the `--emit-only` convention failed.** What went wrong?

1. **Name collision with another tool.** We ship `--emit-only` in toolkit; a plugin author integrates an external CLI that already uses `--emit-only` for a different semantic (e.g., "emit logs only, no results"). Two meanings in one prompt context confuse the LLM. Mitigation: pick a name that is either namespaced (no single widely-used CLI has it) or so domain-specific it can't collide.

2. **Users expect MCP compatibility that isn't there.** We ship the pattern with language like "similar to MCP tool-call." Users then try to expose a toolkit skill over an actual MCP server and find no JSON-RPC layer exists. Mitigation: describe the pattern in its own terms; cite MCP as *analogy*, not *implementation*.

3. **The word "emit" is too narrow.** It foregrounds *output* only. Users with write-only side-effect skills (e.g., "update a database record") can't model their skill as "emitting" anything structured. They retrofit unrelated return shapes just to fit the name. Mitigation: the name should foreground *invocation mode*, not output — e.g., `--as-tool`, `--pure`, `--invoke-only`.

4. **Framework drift.** OpenAI or LangChain renames their term; we stay pinned to old vocabulary. We either chase their renames or diverge silently. Mitigation: anchor our vocabulary in a stable reference (MCP spec, or a concept name that predates these SDKs) rather than any single SDK's method name.

5. **Users can't find it in prompt context.** Future skills want to adopt the pattern but can't figure out what to search for — it's not in MCP vocabulary, not in Anthropic's vocabulary, not in any framework's. Mitigation: pick a name from the already-known vocabulary so future authors Googling "agent as tool" or "invoke skill as function" land on our docs.

## Findings

### Q1 — Anthropic / Claude Code surface

**Anthropic has the full pattern vocabulary, but distributed across three orthogonal flags, not a single term.** (HIGH — T1 source [2] is Anthropic's own docs; the vocabulary is explicit.)

- `-p` / `--print` is Anthropic's non-interactive flag (what was formerly "headless mode"). It makes the CLI non-interactive but still loads the full environment (hooks, skills, plugins, MCP servers, auto memory, CLAUDE.md).
- `--output-format json` + optional `--json-schema` guarantees structured output.
- `--bare` is the ceremony-suppression flag specifically: "reduces startup time by skipping auto-discovery of hooks, skills, plugins, MCP servers, auto memory, and CLAUDE.md."
- `--allowedTools` and the `dontAsk` permission mode handle approval suppression.

Anthropic explicitly retired "headless" as a label ("The CLI was previously called 'headless mode'") in favor of "run programmatically." And "bare mode is useful for CI and scripts where you need the same result on every machine ... `--bare` is the recommended mode for scripted and SDK calls, and will become the default for `-p` in a future release."

**LCD implication:** Anthropic does not have a single word for the combined pattern. `--bare` is the closest single-flag match for ceremony suppression specifically; `-p` for non-interactive; `--output-format json --json-schema` for structured output. No single Anthropic term maps directly to "emit-only invocation."

### Q2 — MCP contract semantics

**MCP's `tools/call` is a near-exact *shape* match but operates at a protocol (JSON-RPC) layer, not at a SKILL.md runtime layer.** (HIGH — T1 source [1], MCP spec 2025-06-18, Anthropic-backed.)

MCP tools: structured `arguments` in, `structuredContent` out (optionally conforming to `outputSchema`), `isError: true` for failures reported as a result field (not an exception), and the spec is explicit that "implementations are free to expose tools through any interface pattern that suits their needs — the protocol itself does not mandate any specific user interaction model."

**Shape match:** `{ args-in, structured-out, isError, no-UI-mandated }` is exactly the user's emit-only contract.

**Structural gap:** MCP requires a JSON-RPC transport, a registered tool catalog (`tools/list`), and a client/server split. Our pattern sits inside SKILL.md prose — no transport, no catalog, no server. So MCP is a semantic analogue, not a literal standard we can cite-and-reuse.

**LCD implication:** "MCP tool call" vocabulary (`inputSchema`, `outputSchema`, `structuredContent`, `isError`) is the *most widely adopted* set of terms for "this thing computes a structured result and does not own the UI." Reusing the *field names* (not the transport) gives us immediate cross-ecosystem legibility.

### Q3 — Agent-framework equivalents

**Cross-framework convergence is on the metaphor "agent as tool" / "skill as tool," not on a specific method name.** (HIGH — T1 sources [4], [7], [8], [9] all use variants of the same metaphor; OpenAI and LangGraph use the phrase directly.)

- **OpenAI Agents SDK** — `Agent.as_tool(tool_name, tool_description, parameters=<Pydantic model>, custom_output_extractor=...)`. The SDK's own docs contrast this with handoffs: "If you want structured input for a nested specialist without transferring the conversation, prefer `Agent.as_tool(parameters=...)`." [4][5] The axis OpenAI uses to distinguish as-tool from handoff is exactly ours: keep the user-facing conversation with the caller (as-tool) vs. transfer control (handoff).
- **LangGraph** — literal phrase "wrap subagent as a tool for the outer agent"; invocation is `subgraph.invoke(...)` or `fruit_agent.invoke(...)`. UI is a non-issue because LangGraph is a library. [7]
- **Semantic Kernel** — "agent as KernelFunction" / "plugin from an agent" via `kernel.add_plugin(my_agent)`. Manual mode (`FunctionChoiceBehavior.Auto(auto_invoke=False)`) returns the list of chosen functions to the caller without invoking, which is the equivalent ceremony-suppression knob. [8]
- **AutoGen** — `runtime.send_message()` with typed message dataclasses. No named pattern; it *is* how the runtime works. [9]

**"Handoff" is reserved across ecosystems.** OpenAI uses it for user-transfer; toolkit's own `.context/` uses it for user-facing boundary ceremony (closure signal + intent preview + provenance tag). [I-2, I-4] Reusing "handoff" for our pattern would contradict both.

**LCD implication:** The phrase "**agent as tool**" / "**skill as tool**" is the single highest-recognition description across the four major agent frameworks surveyed. Method names diverge (`as_tool`, `invoke`, `add_plugin`, `send_message`); the metaphor converges.

### Q4 — CLI flag naming precedent

**No single existing flag captures both "structured output" and "ceremony suppression" cleanly; each axis has precedent, but they're usually orthogonal flags.** (HIGH — direct reading of T1 sources [10], [11] for porcelain, T4 source [12] for kubectl, Anthropic [2] for `--bare`.)

| Axis | Best precedent | Notes |
|------|----------------|-------|
| Script-parseable structured output | `git --porcelain` (stable across versions), `kubectl -o json`, `--output-format json` (Anthropic) | `--porcelain` carries a stability guarantee; `-o json` carries none but is widely recognized. |
| Ceremony suppression (no prompts, no config pollution) | `--bare` (Anthropic, explicitly recommended for SDK calls), `--batch` (gpg, Unix tradition), `--non-interactive` (wget/apt/ssh — overloaded) | `--bare` is the strongest single-flag match for "skip discovery, give me a reproducible environment." |
| Combined (both axes) | None universal. Convention: two orthogonal flags. | Frameworks that bundle both typically do so through a mode, not a flag (e.g., MCP's `tools/call` is a *protocol* choice, not a flag). |

**`--porcelain` terminology trap:** Pro Git Book [11] documents that Git's internal vocabulary inverts the everyday sense — plumbing commands are the low-level/machine-facing ones, porcelain commands are the user-facing ones. The `--porcelain` flag on porcelain commands produces plumbing-shaped output. This overloading is a known source of confusion and we should avoid the word.

**LCD implication:** If we want a single recognizable flag, `--bare` (ceremony axis) or `-o json` (output axis) has prior art. If we want to capture both axes in one name, we have to coin — but coining with "as-tool" / "as-function" wording connects to the agent-framework convergence in Q3 rather than to a CLI-flag convergence.

### Q5 — Internal toolkit adjacency

**Toolkit's existing vocabulary commits us to a specific semantic for "handoff" that emit-only must not collide with, but otherwise is compatible.** (HIGH — direct reading of T1-internal sources I-1 through I-4.)

| Committed term | Source | Emit-only relationship |
|----------------|--------|-------------------------|
| **handoff** | I-2, I-4 | **Reserved for user-facing gates.** "Three required elements at every skill boundary: closure signal, intent preview, provenance tag." Emit-only explicitly bypasses all three. If we call our pattern a "handoff," we contradict a HIGH-confidence committed definition. |
| **orchestrator** | I-2, I-3 | The caller. Emit-only is an invocation style the orchestrator may choose. Compatible. |
| **output contract** | I-2 | Direct superset. Emit-only is (input contract + output contract + UI-suppression). |
| **shared state** | I-2 | Potential minor conflict — emit-only returns structured output *directly*, not via a shared state file. Reconcilable as "shared state collapsed to the return value for this call." |
| **two-channel model (Copilot Studio)** | I-4 | Direct match. Emit-only is the skill-facing channel; the user-facing channel is owned by the caller. |
| **error fields, not exceptions** | I-2, I-3 | Direct match with MCP's `isError` and our proposed structured output. |

**LCD implication:** Our pattern needs a term that (a) does not reuse "handoff," (b) reads as a mode/style rather than a boundary event, and (c) connects to the two-channel model from [I-4]. Candidates from existing vocabulary: "skill-facing invocation," "structured invocation," "invoke-as-tool," "pure invocation." Avoid: "handoff," "transfer," "delegate."

## Claims

| # | Claim | Type | Source | Status |
|---|-------|------|--------|--------|
| 1 | Anthropic retired "headless mode" as a label in favor of `--print` / "run programmatically" | attribution | [2] | verified — direct quote: "The CLI was previously called 'headless mode.'" |
| 2 | `--bare` is Anthropic's recommended mode for SDK/scripted calls | attribution | [2] | verified — direct quote: "`--bare` is the recommended mode for scripted and SDK calls, and will become the default for `-p` in a future release." |
| 3 | MCP's protocol does not mandate any user interaction model | attribution | [1] | verified — direct quote: "the protocol itself does not mandate any specific user interaction model." |
| 4 | MCP reports tool execution errors via `isError: true` field, not exceptions | attribution | [1] | verified — direct quote: "Tool Execution Errors: Reported in tool results with `isError: true`." |
| 5 | OpenAI Agents SDK's documentation contrasts `as_tool` with `handoff` on the "keep user conversation" vs "transfer control" axis | attribution | [4], [5] | verified — [5] direct quote: "If you want structured input for a nested specialist without transferring the conversation, prefer `Agent.as_tool(parameters=...)`" |
| 6 | OpenAI's `Agent.as_tool()` accepts a `parameters` argument for typed structured input | attribution | [4] | verified — direct quote: "you can expose a structured schema by passing `parameters` (a Pydantic model or dataclass type)." |
| 7 | LangGraph uses the phrase "wrap subagent as a tool for the outer agent" | attribution | [7] | verified — direct quote from [7] |
| 8 | Semantic Kernel exposes an agent as a `KernelFunction` via `kernel.add_plugin(my_agent)` | attribution | [8] | verified — direct quote from [8] |
| 9 | AutoGen does not have a named "agent-as-tool" pattern; it is simply how `runtime.send_message()` works | interpretation | [9] | verified — [9] documents `send_message` as the primary primitive with no chat/UI axis referenced |
| 10 | Git's `--porcelain` flag produces output guaranteed to be stable across Git versions | attribution | [10] | verified — direct quote: "will remain stable across Git versions and regardless of user configuration." |
| 11 | Git's "porcelain" terminology for commands inverts the everyday sense (porcelain = user-facing; plumbing = machine-facing) | attribution | [11] | verified — Pro Git Book defines plumbing = low-level / scriptable, porcelain = user-friendly |
| 12 | Toolkit `.context/` reserves "handoff" for user-facing boundary ceremony with closure-signal + intent-preview + provenance-tag | attribution | [I-4] | verified — direct quote from `.context/skill-chain-handoff-signaling-and-evidence-packs.context.md` |
| 13 | Toolkit `.context/` commits to "output contracts, shared state, and an orchestrator" as required skill-handoff components | attribution | [I-2] | verified — direct quote from `.context/skill-handoff-contracts-and-state-design.context.md` |
| 14 | OpenAI, LangGraph, and Semantic Kernel all converge on the "agent as tool" / "skill as tool" metaphor (each with a different method name) | superlative / synthesis | [4], [7], [8] | verified — each framework's T1 docs independently use variants of the phrase; method names (as_tool, invoke, add_plugin) differ |

### Summary — LCD pattern candidates

Three naming strategies surface from the findings:

1. **Adopt "agent-as-tool" / "skill-as-tool" metaphor.** Highest recognition across agent frameworks (OpenAI, LangGraph, Semantic Kernel all use variants). Flag form: `--as-tool`. Signals to a skill author "this skill can be invoked like a function." (HIGH recognition; MODERATE risk of collision with OpenAI's method-level `as_tool` that returns a tool *definition*, not an invocation flag.)

2. **Adopt MCP field-vocabulary without the protocol.** Frame our pattern as "SKILL-level equivalent of MCP tool-call." Use MCP's terms for the output shape (`inputSchema`, `outputSchema`, `structuredContent`, `isError`). Flag form unchanged (could be `--as-tool` or anything else). This buys legibility for anyone who has seen MCP — a growing and Anthropic-backed ecosystem. (HIGH recognition; MODERATE implementation cost — our SKILLs aren't JSON-RPC servers and we'd need to document the gap.)

3. **Keep `--emit-only` but document the cross-walk.** Our term is novel but specific. The shared reference contract doc includes a "prior art" section that maps `--emit-only` to OpenAI's `as_tool`, MCP's `tools/call`, LangGraph's subgraph-as-tool, Semantic Kernel's agent-as-KernelFunction. Users familiar with any of those frameworks can locate our pattern. (LOW risk of collision; LOW recognition boost; clear mental model for ceremony suppression via the word "only.")

A synthesis path: **use `--as-tool` as the flag name** (because the metaphor is the strongest LCD) **AND** document MCP-shape field names for the structured output (`inputSchema`, `outputSchema`, `structuredContent`, `isError`) so the output contract inherits MCP legibility. The flag captures the intent; the output shape inherits the vocabulary.

## Takeaways

### What to adopt

- **Flag name: `--as-tool`.** Reason: highest cross-framework recognition (OpenAI, LangGraph, Semantic Kernel all use variants of the "agent/skill as tool" metaphor). Connects any future skill author from those ecosystems to our pattern immediately.
- **Output-shape vocabulary: MCP's field names.** `inputSchema`, `outputSchema`, `structuredContent`, `isError`. We are not implementing MCP (no JSON-RPC, no tool catalog), but we inherit the vocabulary so the output contract reads as familiar.
- **Conceptual framing from toolkit `.context/`:** "two-channel model" — emit-only is the skill-facing channel; the caller owns the user-facing channel. This is already committed vocabulary in `.context/skill-chain-handoff-signaling-and-evidence-packs.context.md`.

### What to avoid

- **Do not reuse "handoff."** Reserved by OpenAI SDK and by `.context/` for user-transfer semantics.
- **Do not reuse "porcelain."** The Git overload (`--porcelain` flag on porcelain commands emits plumbing-shaped output) is a known confusion vector. Our pattern has the stability-contract DNA but not the naming legacy.
- **Do not claim MCP compatibility.** We reuse MCP's *shape* and *field names*, not its transport. Be explicit: "SKILL-level analogue of MCP tool-call semantics."
- **Do not couple to any single SDK's method name.** OpenAI's `as_tool` is a Python method that returns a tool definition, not an invocation flag. Using `--as-tool` as our flag is a metaphor-level borrow, not an API-level one — say so in the contract doc.

### Limitations of this research

- **Scope was landscape.** Per-framework depth is one to three T1 quotes; a deeper feasibility study would verify, e.g., whether an actual MCP server could be derived from an `--as-tool` skill, or whether OpenAI's `as_tool` serializer would accept our output shape unchanged.
- **LangChain Runnable docs could not be fetched cleanly** (308 redirect, no usable substitute). LangGraph was fetched in its place; the claim that "LangChain's `Runnable.invoke()` is the underlying primitive" is based on common knowledge of the library rather than a verbatim T1 quote.
- **No vendor-neutral standards body consulted.** There is no IETF or W3C standard for agent-to-agent invocation. MCP is the closest de-facto spec; everything else is per-vendor.

### Follow-ups worth considering

- **Stability contract for the `--as-tool` output shape.** Git's `--porcelain` earns trust because the output is *guaranteed stable*. Our contract doc should make an equivalent promise for `structuredContent` fields across toolkit plugin versions — otherwise skill callers can't rely on it.
- **Alignment with `/build:check-skill-chain`.** The chain-manifest skill already audits input/output contracts at declared skill boundaries. Consider whether `--as-tool` SKILLs should be introspectable by check-skill-chain as first-class chain components.
- **MCP export path.** If we adopt MCP field vocabulary, at some future point wrapping an `--as-tool` skill as an actual MCP server becomes a thin translation layer. Worth capturing as a latent option.

## Search Protocol

17 searches total (14 WebFetch + 3 WebSearch); all yielded usable T1 or T4 sources.

| Query | Source | Found | Used |
|-------|--------|-------|------|
| WebFetch modelcontextprotocol.io/specification/2025-06-18/server/tools | webfetch | 1 | 1 |
| WebFetch docs.anthropic.com/en/docs/claude-code/headless | webfetch | 1 | 1 (301 → code.claude.com) |
| WebFetch code.claude.com/docs/en/headless | webfetch | 1 | 1 |
| WebFetch openai.github.io/openai-agents-python/tools/ | webfetch | 1 | 1 |
| WebFetch openai.github.io/openai-agents-python/handoffs/ | webfetch | 1 | 1 |
| agent as tool OpenAI Agents SDK as_tool structured output | google | 10 | 1 |
| WebFetch python.langchain.com/docs/concepts/runnables/ | webfetch | 0 | 0 (308 redirect; replacement unusable) |
| LangGraph subgraph invoke as_tool structured state 2025 | google | 10 | 1 |
| WebFetch docs.langchain.com/oss/python/langgraph/use-subgraphs | webfetch | 1 | 1 |
| Semantic Kernel "agent as function" KernelFunction invoke structured | google | 10 | 1 |
| WebFetch learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/agent-functions | webfetch | 1 | 1 |
| AutoGen "agent as tool" send_message runtime structured Microsoft | google | 10 | 1 |
| WebFetch microsoft.github.io/autogen/stable/.../agent-and-agent-runtime | webfetch | 1 | 1 |
| WebFetch git-scm.com/docs/git-status | webfetch | 1 | 1 |
| git "porcelain" stable format "scripts" design intent | google | 10 | 1 |
| WebFetch git-scm.com/book/en/v2/Git-Internals-Plumbing-and-Porcelain | webfetch | 1 | 1 |
| kubectl "-o json" "-o yaml" scripting non-interactive structured output rationale | google | 10 | 1 |

Plus 4 local Grep/Read passes against `.context/` (skill-handoff-contracts-and-state-design, skill-chaining-definition-and-vocabulary, skill-chain-sequential-and-recursive-design-rules, skill-chain-handoff-signaling-and-evidence-packs).
