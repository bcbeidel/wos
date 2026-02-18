# Maintain Lifecycle Workflow

Manage document lifecycle transitions — primarily for plan documents.

## Steps

1. **List documents with status fields**
   - Plans always have `status` (draft, active, complete, abandoned)
   - Show current status and `last_updated` date for each

2. **User selects document and new status**
   - Present valid transitions for the selected document:

   | Current | Can become |
   |---------|-----------|
   | draft | active, abandoned |
   | active | complete, abandoned |
   | complete | active (reopen) |
   | abandoned | draft (resurrect) |

3. **Validate the transition**
   - Use `transition_status()` from `wos.auto_fix`
   - Returns None if invalid — show error and valid options

4. **Preview the change**
   - Show the frontmatter before and after
   - `last_updated` will be set to today's date

5. **Apply with user confirmation**
   - Write the updated file
   - Confirm the new status to the user

## Implementation

```python
from wos.auto_fix import transition_status
from wos.document_types import PlanStatus

result = transition_status(path, content, PlanStatus.ACTIVE)
if result is None:
    # Invalid transition — show allowed options
else:
    fixed_content, description = result
    # Show preview, get confirmation, write file
```
