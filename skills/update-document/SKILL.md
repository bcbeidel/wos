---
name: update-document
description: >
  This skill should be used when the user wants to "update a topic",
  "revise a document", "edit a document", "fix a document",
  "update content", "refresh sources", or any request to modify an
  existing structured context document.
disable-model-invocation: true
argument-hint: "[what to update]"
---

# Update Document Skill

Update existing structured context documents while preserving frontmatter
integrity.

## Routing

**Step 1: Check for `/context/` directory.**
If absent, respond: "This project isn't set up for structured context yet.
Run `/wos:create-context` first."

**Step 2: Route to the update-document workflow** in `references/`.

## Key Rules

- Preserve existing frontmatter fields
- Update `last_updated` to today's date
- If content was revalidated, update `last_validated` too
- The updated document must pass `parse_document()`
