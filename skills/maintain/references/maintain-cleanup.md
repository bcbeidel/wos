# Maintain Cleanup Workflow

Identify and handle orphaned or broken files in the project.

## Steps

1. **Scan for unparseable files**
   - Find all `.md` files in `context/` and `artifacts/` directories
   - Run `parse_document()` on each
   - Report files that fail to parse with the error message

2. **Scan for dead internal links**
   - Run health check and filter for `check_link_graph` failures
   - These are `related` paths pointing to files that don't exist

3. **Present cleanup candidates** with context:
   - For unparseable files: show the error and suggest fix or removal
   - For dead links: show which document has the broken link and what it
     points to

4. **Execute with user confirmation**
   - For unparseable files: user decides to fix, move, or delete
   - For dead links: user decides to update the path or remove the link
   - Never delete without explicit approval

## Implementation

```python
from wos.auto_fix import find_unparseable_files

# Get list of all md files in context/ and artifacts/
results = find_unparseable_files(root, file_list)
for r in results:
    print(f"  {r['file']}: {r['error']}")
```

## Safety

- **Never auto-delete files.** Always present candidates and wait for
  confirmation.
- Show enough context for the user to make an informed decision.
- If a file can be fixed rather than deleted, suggest the fix first.
