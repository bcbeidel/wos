# Update Document Workflow

Update an existing document while preserving frontmatter integrity.

## Steps

1. **Identify the document** to update
   - User may provide a path or describe the document
   - Read and parse the existing document via `parse_document()`

2. **Understand the changes**
   - Ask the user what needs updating
   - Determine which sections are affected

3. **Apply updates**
   - Preserve existing frontmatter fields
   - Update `last_updated` to today's date
   - If content was revalidated, update `last_validated` too
   - Make the requested content changes

4. **Re-validate**
   - The updated document must pass `parse_document()`
   - Fix any validation errors before writing

5. **Write the file** back to its original path

6. **Follow Post-Write Protocol**
   - If the `description` frontmatter field changed AND it's a context type:
     run discovery to refresh manifest entries
   - If content changed but description unchanged: skip discovery
   - Confirm changes to the user
