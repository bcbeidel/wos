# Context


Project context documents covering domain knowledge, patterns, and conventions.

| File | Description |
| --- | --- |
| [agent-context-file-quality-over-completeness.context.md](agent-context-file-quality-over-completeness.context.md) | "Human-optimized READMEs can actively decrease LLM performance; minimal curated context files beat verbose auto-generated ones" |
| [agent-facing-document-structure.context.md](agent-facing-document-structure.context.md) | "Documents for LLM consumption: key insights at start and end, answer-first structure, explicit paths/commands over prose" |
| [confidence-calibration-and-self-correction.context.md](confidence-calibration-and-self-correction.context.md) | "LLM confidence severely miscalibrated; self-correction without external feedback yields +1.8pp; structured external feedback yields 21-32pp" |
| [context-rot-and-window-degradation.context.md](context-rot-and-window-degradation.context.md) | "LLM attention degrades non-linearly — performance drops begin as early as 500-750 tokens, worst when critical content sits in the middle" |
| [cot-and-self-consistency-tradeoffs.context.md](cot-and-self-consistency-tradeoffs.context.md) | "CoT yields diminishing/negative returns on frontier reasoning models; self-consistency reliably boosts fixed-answer tasks" |
| [format-sensitivity-and-cross-model-defaults.context.md](format-sensitivity-and-cross-model-defaults.context.md) | "Format sensitivity is real (up to 40% swing); XML optimal for Claude, Markdown safest cross-model default" |
| [instruction-capacity-and-context-file-length.context.md](instruction-capacity-and-context-file-length.context.md) | "Instruction capacity is finite and model-dependent; shorter higher-signal context files strictly better" |
| [llm-as-judge-biases-and-mitigations.context.md](llm-as-judge-biases-and-mitigations.context.md) | "LLM-as-judge: 14+ bias types; binary per-criterion rubrics + position swapping + sampling aggregation are best mitigations" |
| [llm-failure-modes-and-mitigations.context.md](llm-failure-modes-and-mitigations.context.md) | "Sycophancy, instruction attenuation, hallucination, mode collapse require architectural countermeasures; prompt-level fixes yield only ~14% improvement" |
| [portable-vs-model-specific-prompt-constructs.context.md](portable-vs-model-specific-prompt-constructs.context.md) | "Portable constructs: clear objectives, few-shot examples, numbered steps; model-specific tuning stays separate" |
| [production-reliability-gap-and-multi-agent-failures.context.md](production-reliability-gap-and-multi-agent-failures.context.md) | "No single model dominates all task types; benchmark scores overestimate production reliability by 20-40%; multi-agent failure rates 41-86%" |
| [prompt-design-principles-framing-and-emphasis.context.md](prompt-design-principles-framing-and-emphasis.context.md) | "Affirmative framing, context/motivation for rules, avoid ALL-CAPS on Claude 4.6 — most transferable prompt design principles" |
| [prompt-repetition-technique.context.md](prompt-repetition-technique.context.md) | "Prompt repetition: 47 wins vs. 0 losses across 70 benchmarks, no latency cost" |
| [rubric-specificity-and-deterministic-first-evaluation.context.md](rubric-specificity-and-deterministic-first-evaluation.context.md) | "Rubric specificity has large effect (0.666 vs 0.487 correlation); exhaust deterministic checks before LLM judgment" |
