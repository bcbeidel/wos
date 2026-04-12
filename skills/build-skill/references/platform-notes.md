# Platform-Specific Notes

The core workflow (draft → test → review → improve → repeat) is the same everywhere.
The mechanics change based on what the runtime supports.

---

## Claude.ai

Claude.ai has no subagents and may have no browser/display.

**Running test cases**: No parallel execution. For each test case, read the skill's SKILL.md, then follow its instructions to accomplish the test prompt yourself, one at a time. This is less rigorous than independent subagents (you wrote the skill and are also running it), but it's a useful sanity check — human review compensates. Skip baseline runs — just use the skill as requested.

**Reviewing results**: If no browser is available, skip the viewer entirely. Present results directly in the conversation: show the prompt and the output for each test case. If the output is a file (e.g., .docx, .xlsx), save it to the filesystem and tell the user where to find it. Ask for feedback inline: "How does this look? Anything you'd change?"

**Benchmarking**: Skip quantitative benchmarking — baseline comparisons aren't meaningful without subagents. Focus on qualitative feedback.

**The iteration loop**: Same as always — improve the skill, rerun test cases, ask for feedback — without the browser viewer in the middle. You can still organize results into iteration directories on the filesystem.

**Description optimization**: Requires the `claude` CLI tool (`claude -p`), available only in Claude Code. Skip it on Claude.ai.

**Blind comparison**: Requires subagents. Skip it.

**Packaging**: `package_skill.py` works anywhere with Python and a filesystem. The user can download the resulting `.skill` file.

**Updating an existing skill**: The user might be asking you to update an existing skill, not create a new one. In this case:
- **Preserve the original name.** Use the skill's directory name and `name` frontmatter field unchanged. E.g., if the installed skill is `research-helper`, output `research-helper.skill` (not `research-helper-v2`).
- **Copy to a writeable location before editing.** The installed skill path may be read-only. Copy to `/tmp/skill-name/`, edit there, and package from the copy.
- **If packaging manually, stage in `/tmp/` first**, then copy to the output directory — direct writes may fail due to permissions.

---

## Cowork

Cowork has subagents but no browser or display.

- Subagents work, so the full parallel workflow (spawn test cases, run baselines, grade) applies. If timeouts are severe, it's OK to run test prompts in series.
- No browser/display: use `--static <output_path>` when generating the eval viewer to write a standalone HTML file. Proffer a link the user can click to open it.
- Generate the eval viewer before revising the skill yourself — human review must come before self-evaluation, because having written the skill biases your judgment. Get results in front of the human before making any changes.
- Feedback works differently: "Submit All Reviews" downloads `feedback.json` as a file rather than posting to a server. Read it from there (you may need to request access first).
- Packaging works — `package_skill.py` just needs Python and a filesystem.
- Description optimization (`run_loop.py` / `run_eval.py`) works fine via subprocess. Save it until the skill is fully finished and the user agrees it's in good shape.
- **Updating an existing skill**: Follow the update guidance in the Claude.ai section above.
