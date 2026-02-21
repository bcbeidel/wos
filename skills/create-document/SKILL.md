---
name: create-document
description: >
  This skill should be used when the user wants to "create a topic",
  "add a document", "write about", "investigate something", "research X",
  "plan how to", "document what I learned", "save this as a topic",
  "create an overview", "add content about", or any request to create a
  new structured context document in this project.
disable-model-invocation: true
argument-hint: "[what to create]"
---

# Create Document Skill

Create new structured context documents. Handles all document types through
free-text intent classification.

## Routing

**Step 1: Check for `/context/` directory.**
If absent, respond: "This project isn't set up for structured context yet.
Run `/wos:create-context` first."

**Step 2: Classify intent from the user's message:**

| Signal words | Document type | Path |
|---|---|---|
| "investigate", "research", "what do we know about", "look into" | research | Research path |
| "plan", "how to build", "steps for", "roadmap" | plan | Plan path |
| "add topic", "document", "guidance on", "write about" | topic | Topic path |
| "overview", "index for", "area summary" | overview | Overview path |

**Step 3: If ambiguous** (e.g., "save this"), ask:
"Should I create this as a **topic** (actionable guidance for agents),
a **research** note (investigation snapshot), or a **plan** (actionable steps)?"

**Step 4: Route to the create-document workflow** in `references/`.

## Document Type Quick Reference

| Type | Location | When to use |
|------|----------|------------|
| topic | `context/{area}/{slug}.md` | Actionable guidance with citations |
| overview | `context/{area}/_overview.md` | Area orientation and topic index |
| research | `artifacts/research/{date}-{slug}.md` | Investigation snapshot |
| plan | `artifacts/plans/{date}-{slug}.md` | Actionable work plan |

## Post-Write Protocol

After creating any document:

1. **Validate** the document passes `parse_document()` -- fix any issues
2. **If context type** (topic or overview): run discovery to update manifests
   ```bash
   python3 scripts/run_discovery.py --root .
   ```
3. **If artifact type** (research or plan): skip discovery (not in manifest)
4. **Confirm** to user: show file path and any manifest changes
