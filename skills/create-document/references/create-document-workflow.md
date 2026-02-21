# Create Document Workflow

Create a new document of any type.

## Common Steps (all types)

1. **Confirm document type** from SKILL.md routing
2. **Gather input** from the user:
   - Title / subject
   - Key points or content to include
   - For topics/research: sources to cite
3. **Generate the document** using template functions:
   ```bash
   python3 -c "from wos.templates import TEMPLATES; ..."
   ```
   Or construct the document following the template structure.
4. **Validate** the draft passes `parse_document()`
5. **Write** the file to the correct location
6. Follow the **Post-Write Protocol** from SKILL.md

## Topic Path

- Ask which area this topic belongs to (must exist under `context/`)
- Generate slug from title: lowercase, hyphenated (e.g., "Error Handling" -> `error-handling.md`)
- Research sources: gather 2+ sources from different domains
- Use `render_topic()` template with section content
- Path: `context/{area}/{slug}.md`
- After writing: run discovery (context type)

## Overview Path

- Ask which area this overview describes
- Use `render_overview()` template
- Path: `context/{area}/_overview.md`
- After writing: run discovery (context type)

## Research Path

- Frame the research question with the user
- Propose filename: `{date}-{slug}.md` (e.g., `2026-02-17-error-handling-patterns.md`)
- Gather sources during investigation
- Use `render_research()` template with findings
- Path: `artifacts/research/{date}-{slug}.md`
- After writing: do NOT run discovery (artifact type)

## Plan Path

- Clarify the objective with the user
- Propose filename: `{date}-{slug}.md`
- Use `render_plan()` template
- Path: `artifacts/plans/{date}-{slug}.md`
- After writing: do NOT run discovery (artifact type)

## URL Ingest

If the user provides a URL:

1. Fetch and read the content
2. Evaluate source quality using the source hierarchy:
   Official docs > Institutional research > Peer-reviewed >
   Expert practitioners > Community content > AI-generated
3. Use the content as input for the document, citing the URL as a source
4. Proceed with the appropriate type path above
