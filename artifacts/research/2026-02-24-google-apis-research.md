---
name: Google APIs Research (Docs + Calendar)
description: Research findings on Google Docs and Calendar APIs for WOS platform integration
type: research
sources:
  - https://developers.google.com/workspace/docs/api/quickstart/python
  - https://developers.google.com/workspace/docs/api/concepts/structure
  - https://developers.google.com/workspace/docs/api/samples/extract-text
  - https://developers.google.com/workspace/docs/api/limits
  - https://developers.google.com/workspace/docs/api/reference/rest/v1/documents/batchUpdate
  - https://developers.google.com/workspace/docs/api/how-tos/suggestions
  - https://developers.google.com/workspace/docs/api/auth
  - https://developers.google.com/workspace/drive/api/guides/manage-comments
  - https://developers.google.com/workspace/drive/api/reference/rest/v3/comments
  - https://issuetracker.google.com/issues/287903901
  - https://issuetracker.google.com/issues/357985444
  - https://developers.google.com/workspace/calendar/api/v3/reference/freebusy/query
  - https://developers.google.com/workspace/calendar/api/v3/reference/events/list
  - https://developers.google.com/workspace/calendar/api/v3/reference/events
  - https://developers.google.com/workspace/calendar/api/guides/recurringevents
  - https://developers.google.com/workspace/calendar/api/guides/quota
  - https://developers.google.com/workspace/calendar/api/auth
  - https://developers.google.com/identity/protocols/oauth2
  - https://googleapis.github.io/google-api-python-client/docs/oauth-installed.html
  - https://googleapis.github.io/google-api-python-client/docs/oauth.html
  - https://github.com/googleapis/google-api-python-client
  - https://googleapis.dev/python/google-auth-oauthlib/latest/reference/google_auth_oauthlib.flow.html
related:
  - artifacts/plans/2026-02-22-simplification-design.md
---

# Google APIs Research (Docs + Calendar)

Research for GitHub issue #45 — building native Python skills for reading Google
Docs, adding comments, reading Google Calendar events, and checking free/busy
availability.

## 1. Python SDK Options

### Option A: `google-api-python-client` (Recommended)

The official Google discovery-based Python client. Dynamically builds service
objects from Google's API discovery documents.

**Packages needed:**

```
google-api-python-client>=2.0
google-auth-httplib2>=0.1.0
google-auth-oauthlib>=0.5.0
```

**Pros:**

- Official Google-maintained library with active development
- Discovery documents are cached in the library since 2.0 (no network fetch at
  import time)
- Single `build()` call creates typed service objects for any Google API
- Handles pagination, error retries, and media upload/download
- Consistent interface across Docs, Drive, and Calendar APIs
- Well-documented with official quickstart guides for each API

**Cons:**

- Dynamically generated — no static type stubs for IDE autocomplete
- Pulls in `httplib2` as a transport layer (heavier than `requests`)
- Discovery-based approach means API surface is not visible in source code

**Usage pattern:**

```python
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

creds = Credentials.from_authorized_user_file("token.json", SCOPES)

docs_service = build("docs", "v1", credentials=creds)
drive_service = build("drive", "v3", credentials=creds)
calendar_service = build("calendar", "v3", credentials=creds)
```

### Option B: `google-auth` + Raw REST

Use `google-auth` for authentication and `requests` for HTTP calls.

**Pros:**

- Full control over request/response handling
- Lighter dependency footprint (no `httplib2`)
- Easier to debug — you see the exact HTTP requests

**Cons:**

- Must manually construct URLs, handle pagination, parse responses
- No automatic retry/backoff
- Must track API version changes manually
- Significantly more boilerplate

**Recommendation:** Use `google-api-python-client`. The SDK handles pagination,
retries, and discovery. The dynamic nature is a minor inconvenience compared to
the boilerplate of raw REST. WOS already depends on `requests` but the SDK's
`httplib2` dependency is lightweight and isolated.

## 2. Google Docs API

### 2.1 Reading Document Content

**Scope:** `https://www.googleapis.com/auth/documents.readonly`

The `documents.get` method returns the complete document as structured JSON. This
is not plain text or HTML — it is a deeply nested tree of structural elements.

**API call:**

```python
doc = docs_service.documents().get(documentId=DOCUMENT_ID).execute()
title = doc.get("title")
body = doc.get("body", {}).get("content", [])
```

**Document structure hierarchy:**

```
Document
├── title: str
├── documentId: str
├── revisionId: str
├── body
│   └── content: list[StructuralElement]
│       ├── paragraph
│       │   ├── elements: list[ParagraphElement]
│       │   │   ├── textRun
│       │   │   │   ├── content: str
│       │   │   │   └── textStyle: {...}
│       │   │   ├── autoText
│       │   │   ├── pageBreak
│       │   │   └── inlineObjectElement
│       │   ├── paragraphStyle
│       │   │   └── namedStyleType: "NORMAL_TEXT" | "HEADING_1" | ...
│       │   └── bullet (if list item)
│       ├── table
│       │   └── tableRows[].tableCells[].content: list[StructuralElement]
│       ├── tableOfContents
│       └── sectionBreak
├── headers: dict
├── footers: dict
└── footnotes: dict
```

**Index system:** Every element has `startIndex` and `endIndex` fields
(zero-based, measured in UTF-16 code units). Surrogate pairs like emojis consume
two index positions. Text runs never cross paragraph boundaries.

**Text extraction helper (from official docs):**

```python
def read_paragraph_element(element):
    """Returns the text in the given ParagraphElement."""
    text_run = element.get("textRun")
    if not text_run:
        return ""
    return text_run.get("content")


def read_structural_elements(elements):
    """Recurses through StructuralElements to extract all text."""
    text = ""
    for value in elements:
        if "paragraph" in value:
            for elem in value["paragraph"]["elements"]:
                text += read_paragraph_element(elem)
        elif "table" in value:
            for row in value["table"]["tableRows"]:
                for cell in row["tableCells"]:
                    text += read_structural_elements(cell["content"])
    return text


# Usage:
doc = docs_service.documents().get(documentId=DOC_ID).execute()
text = read_structural_elements(doc["body"]["content"])
```

**SuggestionsViewMode parameter:** Controls how suggestions appear in the
response. Options:

| Mode | Behavior |
|------|----------|
| `DEFAULT_FOR_CURRENT_ACCESS` | Inline if editor, preview-without if viewer |
| `SUGGESTIONS_INLINE` | Shows suggested insertions/deletions inline with markers |
| `PREVIEW_SUGGESTIONS_ACCEPTED` | Returns doc as if all suggestions were accepted |
| `PREVIEW_WITHOUT_SUGGESTIONS` | Returns doc as if all suggestions were rejected |

Use `SUGGESTIONS_INLINE` when you need accurate `startIndex`/`endIndex` values
for subsequent `batchUpdate` calls.

### 2.2 Writing to Documents

**Scope:** `https://www.googleapis.com/auth/documents` (full read/write)

The Docs API uses `batchUpdate` for all mutations. Multiple operations can be
sent in a single request, applied atomically.

```python
requests = [
    {
        "insertText": {
            "location": {"index": 1},  # After the doc start
            "text": "Hello, World!\n"
        }
    },
    {
        "replaceAllText": {
            "containsText": {
                "text": "{{placeholder}}",
                "matchCase": True
            },
            "replaceText": "Actual value"
        }
    }
]

result = docs_service.documents().batchUpdate(
    documentId=DOC_ID,
    body={"requests": requests}
).execute()
```

### 2.3 Rate Limits

| Quota | Limit |
|-------|-------|
| Read requests per minute per project | 3,000 |
| Read requests per minute per user per project | 300 |
| Write requests per minute per project | 600 |
| Write requests per minute per user per project | 60 |

Exceeding limits returns HTTP 429. Recommended retry strategy: truncated
exponential backoff using `min(((2^n) + random_ms), max_backoff)`.

All Docs API usage is free — no billing impact from quota exceeded errors.

## 3. Anchored Comments on Google Docs

Comments on Google Docs are managed through the **Drive API v3** (not the Docs
API). The Docs API handles document content; the Drive API handles comments,
permissions, and file metadata.

### 3.1 Creating Comments

**Scope:** `https://www.googleapis.com/auth/drive` (or `drive.file` for files
the app created/opened)

```python
from googleapiclient.discovery import build

drive_service = build("drive", "v3", credentials=creds)

comment_body = {
    "content": "This paragraph needs revision."
}

comment = drive_service.comments().create(
    fileId=FILE_ID,
    fields="*",
    body=comment_body
).execute()
```

**Important:** The `fields="*"` parameter is mandatory for comments resource
methods (except delete). Without it, the response will be empty.

### 3.2 Anchored Comments — Current State

Anchored comments associate a comment with a specific location in a document.
The API provides an `anchor` field (JSON string) and a `quotedFileContent` field.

**Documented approach:**

```python
import json

anchor = json.dumps({
    "region": {
        "kind": "drive#commentRegion",
        "line": 10,        # Line number to anchor to
        "rev": "head"      # "head" for latest revision, or specific revision ID
    }
})

comment_body = {
    "content": "This section needs a citation.",
    "anchor": anchor,
    "quotedFileContent": {
        "mimeType": "text/html",
        "value": "the quoted text being commented on"
    }
}

comment = drive_service.comments().create(
    fileId=FILE_ID,
    fields="*",
    body=comment_body
).execute()
```

### 3.3 Anchored Comments — Known Issues

**Issue #357985444:** Anchored comments via the Drive API are currently
**broken for Google Docs**. The API accepts the anchor parameters but ignores
them during processing — comments are created as unanchored comments despite
including valid anchor data. The API response includes the anchor, but the
comment appears unanchored in the Google Docs UI.

**Issue #36763384:** Long-standing feature request (since 2016) to provide
proper anchor creation ability for Google Docs comments via the Drive API.

**Issue #292610078:** Reports that the anchor property returned when reading
comments created through the UI is opaque and undocumented, making it impossible
to reliably construct valid anchors programmatically.

**Practical impact:** As of February 2026, you can create unanchored (document-
level) comments on Google Docs via the Drive API, but anchoring to specific text
ranges is unreliable. Comments created through the UI do have anchors, but the
anchor format is not publicly documented for programmatic creation.

**Workaround options:**

1. **Unanchored comments with quoted text:** Create comments with
   `quotedFileContent` set to the target text. The comment won't be anchored in
   the sidebar, but the quoted text provides context for what's being
   referenced.

2. **Comment with explicit location reference:** Include the paragraph number,
   heading, or text excerpt in the comment body itself (e.g., "In the section
   'Background', the claim that...").

3. **Google Apps Script bridge:** Apps Script running within a Google Workspace
   context may have different anchoring behavior, but this requires a separate
   deployment and is not a native Python solution.

## 4. Suggestions (Suggested Edits) via API

### 4.1 Current Status

**Issue #287903901 — "Google Docs API Support for Suggested Edits"**

Status: **Open feature request.** The Docs API cannot create suggestions
programmatically. You can:

- **Read** existing suggestions via `suggestionsViewMode` parameter
- **Accept/reject** is not supported via API
- **Create** suggestions is not supported via API

The API supports full document editing (insert, delete, replace) in direct-edit
mode, but there is no suggestion mode equivalent.

### 4.2 Reading Existing Suggestions

When `suggestionsViewMode=SUGGESTIONS_INLINE` is used with `documents.get`,
suggested changes appear in the response with `suggestedInsertionIds` and
`suggestedDeletionIds` on affected text runs:

```python
doc = docs_service.documents().get(
    documentId=DOC_ID,
    suggestionsViewMode="SUGGESTIONS_INLINE"
).execute()

# Suggested text runs include:
# element["textRun"]["suggestedInsertionIds"]: list[str]
# element["textRun"]["suggestedDeletionIds"]: list[str]
# element["textRun"]["suggestedTextStyleChanges"]: dict
```

### 4.3 Best Workaround for "Suggest" Behavior

Since the API cannot create suggestions, the best alternative for a "review and
suggest" workflow is:

1. **Read the document** via Docs API
2. **Create unanchored comments** via Drive API with the proposed change
   described in the comment text (e.g., "Consider changing 'X' to 'Y' in
   paragraph 3")
3. **Let the human author** apply the changes manually after reviewing comments

This matches WOS's design principle of "read-only audit, opt-in fix" — the tool
observes and recommends, the human decides.

## 5. Google Calendar API

### 5.1 Reading Events

**Scope:** `https://www.googleapis.com/auth/calendar.events.readonly`
(narrowest scope for reading events; `calendar.readonly` is broader and includes
calendar metadata)

```python
from datetime import datetime, timezone

calendar_service = build("calendar", "v3", credentials=creds)

now = datetime.now(timezone.utc).isoformat()

events_result = calendar_service.events().list(
    calendarId="primary",
    timeMin=now,
    timeMax="2026-03-01T00:00:00Z",
    maxResults=50,
    singleEvents=True,       # Expand recurring events into instances
    orderBy="startTime"
).execute()

events = events_result.get("items", [])
```

**Event resource structure (key fields):**

```python
{
    "kind": "calendar#event",
    "id": "event_id_string",
    "status": "confirmed",           # confirmed | tentative | cancelled
    "summary": "Team Standup",       # Event title
    "description": "Daily sync...",
    "location": "Conference Room A",
    "start": {
        "dateTime": "2026-02-24T09:00:00-05:00",  # RFC3339
        "timeZone": "America/New_York"
    },
    "end": {
        "dateTime": "2026-02-24T09:30:00-05:00",
        "timeZone": "America/New_York"
    },
    "recurrence": ["RRULE:FREQ=DAILY;BYDAY=MO,TU,WE,TH,FR"],  # Only on parent
    "recurringEventId": "parent_event_id",   # Only on instances
    "attendees": [
        {
            "email": "user@example.com",
            "responseStatus": "accepted",    # accepted | declined | tentative | needsAction
            "self": True
        }
    ],
    "organizer": {"email": "organizer@example.com"},
    "creator": {"email": "creator@example.com"},
    "htmlLink": "https://calendar.google.com/...",
    "transparency": "opaque",    # opaque (busy) | transparent (free)
    "visibility": "default"      # default | public | private | confidential
}
```

**All-day events** use `date` instead of `dateTime`:

```python
"start": {"date": "2026-02-24"},   # No time component
"end": {"date": "2026-02-25"}      # Exclusive end date
```

### 5.2 Recurring Events Handling

The `singleEvents` parameter controls how recurring events appear:

| `singleEvents` | Behavior |
|-----------------|----------|
| `True` | Expands recurring events into individual instances. Each instance is a separate event with its own `start`/`end`. The parent recurring event is not returned. You can use `orderBy="startTime"` only with this mode. |
| `False` (default) | Returns the parent recurring event (with `recurrence` field containing RRULE strings) plus any exceptions. Individual instances are not returned. |

To get instances of a specific recurring event:

```python
instances = calendar_service.events().instances(
    calendarId="primary",
    eventId="recurring_event_id",
    timeMin=now,
    timeMax="2026-03-01T00:00:00Z"
).execute()
```

### 5.3 Free/Busy Endpoint

**Scope:** `https://www.googleapis.com/auth/calendar.readonly` (or full
`calendar` scope). The freebusy endpoint can also work with just an API key for
public calendars.

**Request:**

```python
from datetime import datetime, timezone, timedelta

now = datetime.now(timezone.utc)
end = now + timedelta(days=7)

body = {
    "timeMin": now.isoformat(),
    "timeMax": end.isoformat(),
    "timeZone": "America/New_York",
    "items": [
        {"id": "primary"},
        {"id": "colleague@example.com"}
    ]
}

freebusy = calendar_service.freebusy().query(body=body).execute()
```

**Response structure:**

```python
{
    "kind": "calendar#freeBusy",
    "timeMin": "2026-02-24T00:00:00.000Z",
    "timeMax": "2026-03-03T00:00:00.000Z",
    "calendars": {
        "primary": {
            "busy": [
                {
                    "start": "2026-02-24T14:00:00Z",   # Inclusive
                    "end": "2026-02-24T15:00:00Z"       # Exclusive
                },
                {
                    "start": "2026-02-24T16:00:00Z",
                    "end": "2026-02-24T17:00:00Z"
                }
            ]
        },
        "colleague@example.com": {
            "busy": [...],
            "errors": []    # Optional: notFound, internalError, etc.
        }
    },
    "groups": {}   # If querying group calendars
}
```

**Constraints:**

- `calendarExpansionMax`: Maximum 50 calendars
- `groupExpansionMax`: Maximum 100 group members
- Possible error reasons: `groupTooBig`, `tooManyCalendarsRequested`,
  `notFound`, `internalError`

**Deriving free slots from busy data:**

```python
def find_free_slots(busy_periods, time_min, time_max):
    """Invert busy periods to find free time windows."""
    free = []
    current = time_min
    for period in sorted(busy_periods, key=lambda p: p["start"]):
        busy_start = datetime.fromisoformat(period["start"])
        busy_end = datetime.fromisoformat(period["end"])
        if current < busy_start:
            free.append({"start": current.isoformat(), "end": busy_start.isoformat()})
        current = max(current, busy_end)
    if current < time_max:
        free.append({"start": current.isoformat(), "end": time_max.isoformat()})
    return free
```

### 5.4 Rate Limits

The Calendar API uses a sliding-window quota system per minute. Google does not
publish exact numeric quotas in documentation — they are configured per-project
in the Google Cloud Console under Quotas & System Limits.

General guidance from documentation:

- Quotas are enforced **per project** and **per user per project**
- Exceeding limits returns HTTP 403 (`usageLimits`) or 429 (`usageLimits`)
- Google recommends against increasing per-user quotas above defaults, as other
  operational limits may apply
- The daily project-level quota is reported as 1,000,000 queries per day in
  some sources
- Per-user rate is approximately 25,000 queries per 100 seconds in some sources

For WOS usage (a single user reading their own calendar), default quotas are
more than sufficient.

## 6. OAuth for CLI/Plugin Context

### 6.1 Installed App Flow

For desktop/CLI applications, Google provides the "installed application" OAuth
flow. This uses `google-auth-oauthlib` with `InstalledAppFlow`.

**Prerequisites:**

1. Create a Google Cloud project
2. Enable the Docs, Drive, and Calendar APIs
3. Create OAuth 2.0 Client ID credentials (type: "Desktop app")
4. Download `credentials.json` (the client secrets file)

**Complete auth flow:**

```python
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = [
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/drive",            # For comments
    "https://www.googleapis.com/auth/calendar.readonly", # Events + freebusy
]

TOKEN_PATH = os.path.expanduser("~/.config/wos/google-token.json")
CREDENTIALS_PATH = os.path.expanduser("~/.config/wos/credentials.json")


def get_google_credentials():
    """Get valid Google OAuth credentials, prompting for login if needed."""
    creds = None

    # Load existing token
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    # Refresh or re-authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_PATH, SCOPES
            )
            creds = flow.run_local_server(port=0)  # Opens browser, runs temp server

        # Persist for next run
        os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
        with open(TOKEN_PATH, "w") as token_file:
            token_file.write(creds.to_json())

    return creds
```

### 6.2 How `run_local_server()` Works

1. Starts a temporary HTTP server on localhost (random port with `port=0`)
2. Opens the user's default browser to Google's OAuth consent screen
3. User grants permissions
4. Google redirects to `http://localhost:{port}/` with an auth code
5. The library exchanges the auth code for access + refresh tokens
6. The local server shuts down

This works well for CLI tools. The browser interaction happens once; subsequent
runs use the stored refresh token.

### 6.3 Token Storage

`google-auth-oauthlib` does **not** provide built-in credential storage. You
must implement it yourself. Two common approaches:

**JSON (recommended for WOS):**

```python
# Save
with open(TOKEN_PATH, "w") as f:
    f.write(creds.to_json())

# Load
creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
```

**Pickle (legacy pattern, not recommended):**

```python
import pickle
# Save
with open("token.pickle", "wb") as f:
    pickle.dump(creds, f)
# Load
with open("token.pickle", "rb") as f:
    creds = pickle.load(f)
```

JSON is preferable because it is human-readable, auditable, and does not carry
pickle's security risks (arbitrary code execution on load).

**Recommended storage location:** `~/.config/wos/google-token.json` — follows
XDG conventions, keeps credentials out of the project directory, and avoids
accidental commits.

### 6.4 Refresh Token Lifecycle

| Condition | Token Lifetime |
|-----------|---------------|
| OAuth consent in **production** mode | Indefinite (no expiration) |
| OAuth consent in **testing** mode | **7 days** — then user must re-authenticate |
| Token unused for 6 months | Revoked by Google |
| More than 50 tokens per user per client | Oldest token auto-revoked |
| User manually revokes access | Immediate revocation |
| Password change (some account types) | May trigger revocation |

**Access tokens** (the short-lived bearer token) expire after 1 hour. The SDK
handles refresh automatically when you call API methods — you do not need to
manually refresh.

**For development:** Set OAuth consent screen to "Testing" mode (limited to
listed test users, 7-day token expiry). Move to "Production" before
distribution (requires Google review if using sensitive scopes).

### 6.5 Minimal Scopes for WOS Use Cases

| Use Case | Scope | Notes |
|----------|-------|-------|
| Read Google Docs | `documents.readonly` | Narrowest scope for doc content |
| Add comments to Docs | `drive` or `drive.file` | `drive.file` limits to files opened by the app; `drive` is broader but needed for commenting on arbitrary docs |
| Read calendar events | `calendar.events.readonly` | Narrower than `calendar.readonly` |
| Check free/busy | `calendar.readonly` | `events.readonly` may not suffice for freebusy; `calendar.readonly` covers both |

**Recommended scope set for WOS:**

```python
SCOPES = [
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/calendar.readonly",
]
```

Note: `drive` is a sensitive scope and will require Google OAuth verification
for production apps with more than 100 users. For a personal/small-team CLI
tool, testing mode with listed test users avoids this requirement.

## 7. Implementation Recommendations for WOS

### 7.1 Dependencies to Add

```toml
# In pyproject.toml [project.optional-dependencies]
google = [
    "google-api-python-client>=2.0",
    "google-auth-httplib2>=0.1.0",
    "google-auth-oauthlib>=0.5.0",
]
```

Keep these as optional dependencies — not all WOS users will need Google
integration.

### 7.2 Suggested Module Structure

```
wos/
├── google/
│   ├── __init__.py
│   ├── auth.py          # OAuth flow, token storage, credential management
│   ├── docs.py          # Read doc content, extract text, list suggestions
│   ├── comments.py      # Create/read comments via Drive API
│   └── calendar.py      # Events listing, freebusy queries
```

### 7.3 Key Constraints to Design Around

1. **Anchored comments are broken** — design the comment skill to create
   unanchored comments with explicit text references in the comment body.
   Monitor issue #357985444 for fixes.

2. **Suggestions cannot be created via API** — the "suggest changes" workflow
   must use comments as the feedback mechanism. Monitor issue #287903901.

3. **OAuth requires browser interaction** — first-time auth cannot happen
   headlessly. The skill should detect missing credentials and guide the user
   through setup.

4. **Token storage is manual** — implement JSON-based storage at
   `~/.config/wos/google-token.json` with appropriate file permissions (0600).

5. **Testing mode tokens expire in 7 days** — document this clearly for
   contributors using development OAuth credentials.

6. **Write rate limit is 60/min/user** — batch comment creation if reviewing
   an entire document to stay within limits.
