---
name: Microsoft Graph API Research (Docs + Calendar)
description: Research findings on Microsoft Graph APIs for WOS platform integration
type: research
sources:
  - https://learn.microsoft.com/en-us/graph/api/user-findmeetingtimes?view=graph-rest-1.0
  - https://learn.microsoft.com/en-us/graph/findmeetingtimes-example
  - https://learn.microsoft.com/en-us/graph/api/calendar-getschedule?view=graph-rest-1.0
  - https://learn.microsoft.com/en-us/graph/api/user-list-calendarview?view=graph-rest-1.0
  - https://learn.microsoft.com/en-us/graph/api/driveitem-get-content?view=graph-rest-1.0
  - https://learn.microsoft.com/en-us/graph/api/driveitem-get-content-format?view=graph-rest-1.0
  - https://learn.microsoft.com/en-us/graph/api/resources/onedrive?view=graph-rest-1.0
  - https://learn.microsoft.com/en-us/graph/tutorials/python
  - https://learn.microsoft.com/en-us/graph/throttling
  - https://learn.microsoft.com/en-us/graph/throttling-limits
  - https://learn.microsoft.com/en-us/graph/permissions-reference
  - https://learn.microsoft.com/en-us/graph/outlook-get-shared-events-calendars
  - https://learn.microsoft.com/en-us/entra/msal/python/advanced/msal-python-token-cache-serialization
  - https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-device-code
  - https://learn.microsoft.com/en-us/entra/identity-platform/scenario-desktop-acquire-token-device-code-flow
  - https://learn.microsoft.com/en-us/entra/msal/python/
  - https://github.com/microsoftgraph/msgraph-sdk-python
  - https://github.com/Azure-Samples/ms-identity-python-devicecodeflow
  - https://github.com/AzureAD/microsoft-authentication-extensions-for-python
  - https://github.com/microsoft/markitdown
  - https://pypi.org/project/msal-extensions/
  - https://graphpermissions.merill.net/permission/Calendars.Read.Shared
  - https://graphpermissions.merill.net/permission/Files.Read.All
related:
  - docs/plans/2026-02-22-simplification-design.md
---

# Microsoft Graph API Research (Docs + Calendar)

Research for GitHub issue #46. This document covers everything needed to build
native Python skills in WOS that read documents from OneDrive/SharePoint, read
calendar events, check availability, and suggest optimal meeting times via
`findMeetingTimes`.

---

## 1. Python SDK Options

There are two viable approaches for calling Microsoft Graph from Python.

### Option A: Official SDK (`msgraph-sdk`)

**Installation:**

```bash
pip install azure-identity msgraph-sdk
```

**Characteristics:**

- Async-first (uses `asyncio` by default)
- Generated from Graph OpenAPI metadata -- full API coverage
- Typed request/response models via Kiota code generation
- Built-in retry handler that respects `Retry-After` headers
- Requires `azure-identity` for credential providers

**Example -- initialize client with device code:**

```python
from azure.identity import DeviceCodeCredential
from msgraph import GraphServiceClient

credential = DeviceCodeCredential(
    client_id="YOUR_CLIENT_ID",
    tenant_id="YOUR_TENANT_ID",
)

scopes = ["Files.Read", "Calendars.Read", "Calendars.Read.Shared"]
graph_client = GraphServiceClient(credential, scopes)
```

**Pros:**

- Strongly typed models for all Graph resources
- Automatic pagination support
- Built-in retry/throttle handling
- Auto-generated -- stays current with Graph API changes
- Official Microsoft support

**Cons:**

- Heavy dependency tree (kiota-abstractions, kiota-http, etc.)
- Async-only by default (need `asyncio.run()` wrapper for sync callers)
- Generated code can be deeply nested and harder to debug
- Python 3.8+ required

### Option B: Raw REST with `requests` + `msal`

**Installation:**

```bash
pip install msal requests
```

**Example -- basic GET with token:**

```python
import msal
import requests

app = msal.PublicClientApplication(
    "YOUR_CLIENT_ID",
    authority="https://login.microsoftonline.com/YOUR_TENANT_ID",
)

# Attempt silent first, fall back to device code
accounts = app.get_accounts()
result = None
if accounts:
    result = app.acquire_token_silent(
        ["Files.Read", "Calendars.Read"],
        account=accounts[0],
    )

if not result:
    flow = app.initiate_device_flow(
        scopes=["Files.Read", "Calendars.Read"]
    )
    print(flow["message"])  # "To sign in, use a web browser..."
    result = app.acquire_token_by_device_flow(flow)

headers = {"Authorization": f"Bearer {result['access_token']}"}
response = requests.get(
    "https://graph.microsoft.com/v1.0/me/drive/root/children",
    headers=headers,
)
data = response.json()
```

**Pros:**

- Minimal dependencies (just `msal` + `requests`)
- Full control over request construction
- Synchronous by default -- simpler for CLI tools
- Easier to debug (plain HTTP)

**Cons:**

- Must construct URLs, query parameters, and request bodies manually
- No built-in retry/throttle logic (must implement yourself)
- No typed response models
- Must manually handle pagination (`@odata.nextLink`)

### Recommendation for WOS

**Use raw REST with `msal` + `requests`**. Rationale:

1. WOS targets Python 3.9 and prefers minimal dependencies
2. WOS skills are synchronous scripts, not async services
3. The Graph endpoints needed (5-6 specific calls) are well-defined
4. Debugging raw HTTP is simpler for a plugin context
5. Avoids pulling in the entire kiota dependency tree

---

## 2. Document Access (OneDrive / SharePoint)

### 2.1 Endpoints for File Access

The Graph API uses two resource types: `drive` (logical container) and
`driveItem` (file or folder within a drive).

**Common base paths:**

| Path | Description |
|------|-------------|
| `/me/drive` | Current user's OneDrive |
| `/me/drive/root/children` | List files at root |
| `/me/drive/root:/{path}:/children` | List files at path |
| `/me/drive/items/{item-id}` | Access item by ID |
| `/me/drive/root:/{path}:` | Access item by path |
| `/users/{id}/drive` | Another user's OneDrive |
| `/sites/{site-id}/drive` | SharePoint site's default library |
| `/sites/{site-id}/drives` | All document libraries on a site |
| `/groups/{group-id}/drive` | Group's document library |
| `/shares/{shareIdOrEncodedSharingUrl}/driveItem` | Shared item |

**Path-based addressing** uses `:` as an escape character:

```
GET /me/drive/root:/Documents/Report.docx:
GET /me/drive/root:/Projects/2026:/children
```

### 2.2 Downloading File Content

**Endpoint:**

```
GET /me/drive/items/{item-id}/content
GET /me/drive/root:/{path}:/content
```

**Response:** Returns `302 Found` with a `Location` header pointing to a
preauthenticated download URL. Follow the redirect to get the file bytes.

**Python pattern with `requests`:**

```python
def download_file(access_token: str, item_id: str) -> bytes:
    """Download a file from OneDrive by item ID."""
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(
        f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}/content",
        headers=headers,
        allow_redirects=True,  # follow the 302
    )
    response.raise_for_status()
    return response.content
```

**Alternative -- get download URL without following redirect:**

```python
def get_download_url(access_token: str, item_id: str) -> str:
    """Get the preauthenticated download URL for a file."""
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(
        f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}"
        "?select=id,name,@microsoft.graph.downloadUrl",
        headers=headers,
    )
    response.raise_for_status()
    return response.json()["@microsoft.graph.downloadUrl"]
```

The `@microsoft.graph.downloadUrl` is a preauthenticated URL valid for a few
minutes. No `Authorization` header needed to fetch from it.

**Partial range downloads** are supported via the `Range` header on the
download URL (not on the Graph endpoint):

```python
download_url = get_download_url(token, item_id)
resp = requests.get(download_url, headers={"Range": "bytes=0-1023"})
# Returns HTTP 206 Partial Content
```

### 2.3 Server-Side Format Conversion

Graph can convert documents to PDF or HTML on the server, without downloading
the original format.

**Endpoint:**

```
GET /me/drive/items/{item-id}/content?format=pdf
GET /me/drive/items/{item-id}/content?format=html
```

**Supported source formats for PDF conversion:**

doc, docx, dot, dotx, dotm, dsn, dwg, eml, epub, htm, html, markdown, md,
msg, odp, ods, odt, pps, ppsx, ppt, pptx, rtf, tif, tiff, xls, xlsm, xlsx

**Supported source formats for HTML conversion:**

loop, fluid, wbtx (limited -- mostly Loop/Whiteboard content)

**Response:** Same `302 Found` redirect to a preauthenticated URL for the
converted content.

```python
def download_as_pdf(access_token: str, item_id: str) -> bytes:
    """Download a document converted to PDF."""
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(
        f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}"
        "/content?format=pdf",
        headers=headers,
        allow_redirects=True,
    )
    response.raise_for_status()
    return response.content
```

### 2.4 Converting Downloaded Content to Markdown

For WOS integration, documents need to become markdown/plain text. The
recommended pipeline:

**Approach 1: Microsoft `markitdown` library (recommended)**

```bash
pip install 'markitdown[pdf,docx,pptx]'
```

```python
from markitdown import MarkItDown

md = MarkItDown(enable_plugins=False)

# Convert from file path
result = md.convert("/tmp/downloaded-report.docx")
print(result.text_content)  # Markdown string

# Convert from bytes/stream
import io
result = md.convert_stream(io.BytesIO(file_bytes), file_extension=".docx")
print(result.text_content)
```

Supported formats: PDF, DOCX, PPTX, XLSX, HTML, CSV, JSON, XML, EML, MSG.

This is the simplest option. It is maintained by Microsoft and produces
LLM-friendly markdown output. Requires Python 3.10+, which is a version
constraint WOS would need to evaluate (WOS currently targets 3.9).

**Approach 2: `pypandoc` (requires Pandoc installed)**

```python
import pypandoc

# Convert DOCX to markdown
output = pypandoc.convert_file("report.docx", "markdown")

# Convert from string/bytes
output = pypandoc.convert_text(html_content, "markdown", format="html")
```

Requires the external `pandoc` binary. More format coverage than markitdown
but adds a system dependency.

**Approach 3: `mammoth` for DOCX specifically**

```python
import mammoth

with open("report.docx", "rb") as f:
    result = mammoth.convert_to_html(f)
    html = result.value

# Then convert HTML to markdown with markdownify
from markdownify import markdownify
markdown_text = markdownify(html)
```

**Recommended pipeline for WOS:**

1. Download file via Graph API (`/content` endpoint)
2. If DOCX/PPTX/XLSX: use `markitdown` directly on the bytes
3. If PDF: use `markitdown` (or download as HTML via `?format=html` if
   the source supports it, then convert)
4. If the source is already markdown/plain text: use as-is

### 2.5 Permissions for File Access

| Permission | Type | What It Covers |
|------------|------|----------------|
| `Files.Read` | Delegated | User's own OneDrive files only |
| `Files.Read.All` | Delegated | All files the user can access (shared files, SharePoint) |
| `Files.Read.All` | Application | All files in the entire tenant (no user context) |
| `Sites.Read.All` | Delegated/App | Read items in all site collections |
| `Files.SelectedOperations.Selected` | Both | Granular per-file/folder access (newer) |

**Recommendation for WOS:** Start with `Files.Read` (least privilege, user's
own files only). Upgrade to `Files.Read.All` only if SharePoint/shared file
access is needed. Avoid `Sites.Read.All` unless browsing site collections.

### 2.6 Searching for Files

```python
def search_files(access_token: str, query: str) -> list[dict]:
    """Search for files across the user's OneDrive."""
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(
        f"https://graph.microsoft.com/v1.0/me/drive/root/search(q='{query}')",
        headers=headers,
    )
    response.raise_for_status()
    return response.json().get("value", [])
```

Each result includes `id`, `name`, `webUrl`, `size`, `file` facet (with
`mimeType`), and `parentReference` with the path.

---

## 3. Calendar API

### 3.1 Listing Events (Calendar View)

The `calendarView` endpoint is the primary way to list events in a time range.
It automatically **expands recurring events** into individual occurrences.

**Endpoint:**

```
GET /me/calendarView?startDateTime={iso8601}&endDateTime={iso8601}
GET /me/calendars/{calendar-id}/calendarView?startDateTime=...&endDateTime=...
```

Both `startDateTime` and `endDateTime` are **required** query parameters.

**Permissions (least to most privileged):**

| Type | Permission |
|------|-----------|
| Delegated | `Calendars.ReadBasic` (least) |
| Delegated | `Calendars.Read` |
| Delegated | `Calendars.ReadWrite` |
| Application | `Calendars.ReadBasic` (least) |

**Python pattern:**

```python
def list_events(
    access_token: str,
    start: str,
    end: str,
    timezone: str = "UTC",
) -> list[dict]:
    """
    List calendar events in a time range.
    Recurring events are automatically expanded into occurrences.

    Args:
        start: ISO 8601 datetime, e.g. "2026-02-24T00:00:00"
        end: ISO 8601 datetime, e.g. "2026-02-28T23:59:59"
        timezone: IANA or Windows timezone name
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Prefer": f'outlook.timezone="{timezone}"',
    }
    params = {
        "startDateTime": start,
        "endDateTime": end,
        "$select": "subject,start,end,organizer,location,isAllDay,showAs",
        "$orderby": "start/dateTime",
        "$top": 50,
    }
    response = requests.get(
        "https://graph.microsoft.com/v1.0/me/calendarView",
        headers=headers,
        params=params,
    )
    response.raise_for_status()
    data = response.json()
    events = data.get("value", [])

    # Handle pagination
    while "@odata.nextLink" in data:
        response = requests.get(data["@odata.nextLink"], headers=headers)
        response.raise_for_status()
        data = response.json()
        events.extend(data.get("value", []))

    return events
```

**Event response shape:**

```json
{
    "id": "AAMkAD...",
    "subject": "Team Standup",
    "start": {
        "dateTime": "2026-02-24T09:00:00.0000000",
        "timeZone": "Pacific Standard Time"
    },
    "end": {
        "dateTime": "2026-02-24T09:30:00.0000000",
        "timeZone": "Pacific Standard Time"
    },
    "organizer": {
        "emailAddress": {
            "name": "Jane Doe",
            "address": "jane@contoso.com"
        }
    },
    "location": {
        "displayName": "Conference Room A"
    },
    "isAllDay": false,
    "showAs": "busy",
    "type": "occurrence",
    "seriesMasterId": "AAMkAD..."
}
```

### 3.2 Recurring Events

**Key behaviors:**

- `calendarView` automatically expands recurring series into individual
  occurrences within the requested time range
- Each occurrence has `type: "occurrence"` and a `seriesMasterId` pointing
  to the master event
- Exceptions (modified occurrences) have `type: "exception"`
- Single events have `type: "singleInstance"`
- The occurrence's own `recurrence` property is `null` -- to get the
  recurrence pattern, fetch the master event by `seriesMasterId`

**Getting the recurrence pattern:**

```python
def get_recurrence_pattern(access_token: str, series_master_id: str) -> dict:
    """Fetch the recurrence pattern from a series master event."""
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(
        f"https://graph.microsoft.com/v1.0/me/events/{series_master_id}"
        "?$select=subject,recurrence",
        headers=headers,
    )
    response.raise_for_status()
    return response.json().get("recurrence", {})
```

**Recurrence pattern shape:**

```json
{
    "pattern": {
        "type": "weekly",
        "interval": 1,
        "daysOfWeek": ["monday", "wednesday", "friday"],
        "firstDayOfWeek": "sunday"
    },
    "range": {
        "type": "endDate",
        "startDate": "2026-01-06",
        "endDate": "2026-06-30",
        "recurrenceTimeZone": "Pacific Standard Time"
    }
}
```

**Listing individual instances of a recurring event:**

```
GET /me/events/{seriesMasterId}/instances?startDateTime=...&endDateTime=...
```

### 3.3 Checking Availability (`getSchedule`)

The `getSchedule` endpoint returns free/busy information for multiple users
simultaneously. This is the foundation for availability checking.

**Endpoint:**

```
POST /me/calendar/getSchedule
```

**Request body:**

```json
{
    "schedules": ["alice@contoso.com", "bob@contoso.com"],
    "startTime": {
        "dateTime": "2026-02-24T09:00:00",
        "timeZone": "Pacific Standard Time"
    },
    "endTime": {
        "dateTime": "2026-02-24T18:00:00",
        "timeZone": "Pacific Standard Time"
    },
    "availabilityViewInterval": 30
}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `schedules` | `string[]` | Yes | SMTP addresses of users/rooms/DLs |
| `startTime` | `dateTimeTimeZone` | Yes | Start of the lookup window |
| `endTime` | `dateTimeTimeZone` | Yes | End of the lookup window |
| `availabilityViewInterval` | `int` | No | Slot size in minutes (5-1440, default 30) |

**Permissions:**

| Type | Least Privileged |
|------|-----------------|
| Delegated | `Calendars.ReadBasic` |
| Application | `Calendars.ReadBasic` |

**Response shape:**

```json
{
    "value": [
        {
            "scheduleId": "alice@contoso.com",
            "availabilityView": "000220130",
            "scheduleItems": [
                {
                    "isPrivate": false,
                    "status": "busy",
                    "subject": "Lunch Meeting",
                    "location": "Cafe",
                    "start": {
                        "dateTime": "2026-02-24T12:00:00.0000000",
                        "timeZone": "Pacific Standard Time"
                    },
                    "end": {
                        "dateTime": "2026-02-24T14:00:00.0000000",
                        "timeZone": "Pacific Standard Time"
                    }
                }
            ],
            "workingHours": {
                "daysOfWeek": ["monday", "tuesday", "wednesday", "thursday", "friday"],
                "startTime": "08:00:00.0000000",
                "endTime": "17:00:00.0000000",
                "timeZone": {"name": "Pacific Standard Time"}
            }
        }
    ]
}
```

**The `availabilityView` string encoding:**

Each character represents one time slot (at `availabilityViewInterval` minutes):

| Character | Meaning |
|-----------|---------|
| `0` | Free (or working elsewhere) |
| `1` | Tentative |
| `2` | Busy |
| `3` | Out of office |
| `4` | Working elsewhere (beta) |

Example: `"000220130"` with 60-minute intervals starting at 9 AM means:
9-10 free, 10-11 free, 11-12 free, 12-13 busy, 13-14 busy, 14-15 tentative,
15-16 OOF, 16-17 OOF, 17-18 free.

**Python implementation:**

```python
def check_availability(
    access_token: str,
    emails: list[str],
    start: str,
    end: str,
    timezone: str = "Pacific Standard Time",
    interval_minutes: int = 30,
) -> list[dict]:
    """
    Check free/busy availability for multiple users.

    Returns a list of scheduleInformation objects, one per email.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Prefer": f'outlook.timezone="{timezone}"',
    }
    body = {
        "schedules": emails,
        "startTime": {"dateTime": start, "timeZone": timezone},
        "endTime": {"dateTime": end, "timeZone": timezone},
        "availabilityViewInterval": interval_minutes,
    }
    response = requests.post(
        "https://graph.microsoft.com/v1.0/me/calendar/getSchedule",
        headers=headers,
        json=body,
    )
    response.raise_for_status()
    return response.json().get("value", [])


def parse_availability_view(
    availability_view: str,
    start_datetime: str,
    interval_minutes: int,
) -> list[dict]:
    """
    Parse the compact availabilityView string into structured slots.

    Returns list of {"start": str, "end": str, "status": str} dicts.
    """
    from datetime import datetime, timedelta

    status_map = {
        "0": "free",
        "1": "tentative",
        "2": "busy",
        "3": "out_of_office",
        "4": "working_elsewhere",
    }
    start = datetime.fromisoformat(start_datetime)
    delta = timedelta(minutes=interval_minutes)
    slots = []
    for char in availability_view:
        slot_end = start + delta
        slots.append({
            "start": start.isoformat(),
            "end": slot_end.isoformat(),
            "status": status_map.get(char, "unknown"),
        })
        start = slot_end
    return slots
```

**Known limitation:** If a user's calendar has more than 1000 entries in the
requested time range, the API returns error code `5006` with the message
"The result set contains too many calendar entries." Keep query time ranges
reasonable (a few days at most for busy calendars).

### 3.4 Finding Meeting Times (`findMeetingTimes`)

This is the primary endpoint for suggesting optimal meeting slots.

**Endpoint:**

```
POST /me/findMeetingTimes
```

**Permissions:**

| Type | Least Privileged |
|------|-----------------|
| Delegated (work/school) | `Calendars.Read.Shared` |
| Personal Microsoft | Not supported |
| Application | Not supported |

Note: `findMeetingTimes` is **delegated-only** and requires a work/school
account. It does not work with personal Microsoft accounts or application-only
auth.

**Complete request body schema:**

```python
def find_meeting_times(
    access_token: str,
    attendee_emails: list[str],
    duration_minutes: int = 60,
    start: str | None = None,
    end: str | None = None,
    timezone: str = "Pacific Standard Time",
    max_candidates: int = 5,
    min_attendee_pct: float = 100.0,
    is_organizer_optional: bool = False,
) -> dict:
    """
    Find optimal meeting times for a group of attendees.

    Args:
        attendee_emails: List of email addresses (all treated as required)
        duration_minutes: Meeting length (default 60)
        start/end: ISO 8601 datetime bounds for search window
        max_candidates: Max suggestions to return
        min_attendee_pct: Minimum % of attendees that must be free (0-100)
        is_organizer_optional: If True, organizer need not be free

    Returns:
        meetingTimeSuggestionsResult dict with 'meetingTimeSuggestions'
        and 'emptySuggestionsReason' keys.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Prefer": f'outlook.timezone="{timezone}"',
    }

    attendees = [
        {
            "type": "required",
            "emailAddress": {"address": email},
        }
        for email in attendee_emails
    ]

    body = {
        "attendees": attendees,
        "meetingDuration": f"PT{duration_minutes}M",
        "maxCandidates": max_candidates,
        "minimumAttendeePercentage": min_attendee_pct,
        "isOrganizerOptional": is_organizer_optional,
        "returnSuggestionReasons": True,
    }

    if start and end:
        body["timeConstraint"] = {
            "activityDomain": "work",
            "timeSlots": [
                {
                    "start": {"dateTime": start, "timeZone": timezone},
                    "end": {"dateTime": end, "timeZone": timezone},
                }
            ],
        }

    response = requests.post(
        "https://graph.microsoft.com/v1.0/me/findMeetingTimes",
        headers=headers,
        json=body,
    )
    response.raise_for_status()
    return response.json()
```

**Full request body parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `attendees` | `attendeeBase[]` | No | `[]` (organizer only) | People or resources |
| `meetingDuration` | ISO 8601 duration | No | `PT30M` | Length of meeting |
| `timeConstraint` | object | No | Next 2 business days | Search window + activity type |
| `locationConstraint` | object | No | None | Location requirements |
| `maxCandidates` | int | No | Unspecified | Max suggestions |
| `minimumAttendeePercentage` | float | No | 50.0 | Minimum confidence |
| `isOrganizerOptional` | bool | No | `false` | Organizer must attend? |
| `returnSuggestionReasons` | bool | No | `false` | Include `suggestionReason` |

**`activityDomain` values:**

| Value | Suggestion Scope |
|-------|-----------------|
| `work` | Within configured work hours (Mon-Fri, 8am-5pm default) |
| `personal` | Work hours + Saturday and Sunday |
| `unrestricted` | All hours, all days |

**Response shape:**

```json
{
    "@odata.context": "...$metadata#microsoft.graph.meetingTimeSuggestionsResult",
    "emptySuggestionsReason": "",
    "meetingTimeSuggestions": [
        {
            "confidence": 100.0,
            "order": 1,
            "organizerAvailability": "free",
            "suggestionReason": "Suggested because it is one of the nearest times when all attendees are available.",
            "attendeeAvailability": [
                {
                    "availability": "free",
                    "attendee": {
                        "emailAddress": {
                            "address": "alice@contoso.com"
                        }
                    }
                }
            ],
            "locations": [
                {"displayName": "Conf room Hood"}
            ],
            "meetingTimeSlot": {
                "start": {
                    "dateTime": "2026-02-25T10:00:00.0000000",
                    "timeZone": "Pacific Standard Time"
                },
                "end": {
                    "dateTime": "2026-02-25T11:00:00.0000000",
                    "timeZone": "Pacific Standard Time"
                }
            }
        }
    ]
}
```

**Confidence score calculation:**

The `confidence` property (0-100%) represents the average probability that
all attendees will attend:

| Attendee Status | Attendance Probability |
|----------------|----------------------|
| Free | 100% |
| Unknown | 49% |
| Busy | 0% |

Confidence = average of all attendee probabilities. For example, with 3
attendees (free=100%, unknown=49%, busy=0%), confidence = (100+49+0)/3 = 49.66%.

**Ranking:** Suggestions are ordered by:
1. Confidence (highest first)
2. Chronological order (earliest first, for equal confidence)

**`emptySuggestionsReason` values:**

| Value | Meaning |
|-------|---------|
| `""` (empty) | Suggestions were found |
| `AttendeesUnavailable` | No time when required attendees are free |
| `AttendeesUnavailableOrUnknown` | Same, but includes unknown status |
| `LocationsUnavailable` | No location available |
| `OrganizerUnavailable` | Organizer has no free time |
| `Unknown` | Unspecified reason |

### 3.5 Calendars.Read vs Calendars.Read.Shared

| Permission | Scope |
|------------|-------|
| `Calendars.Read` | Read events only from the signed-in user's own calendars |
| `Calendars.Read.Shared` | Read events from user's own calendars PLUS calendars shared/delegated to them by other users |

`Calendars.Read.Shared` is required for:
- `findMeetingTimes` (needs to see other attendees' calendars)
- Accessing delegated calendars (e.g., reading your manager's calendar)
- Reading shared calendars from other users

`Calendars.ReadBasic` is sufficient for:
- `getSchedule` (free/busy only, no event details)
- `calendarView` on the user's own calendar

**Recommendation for WOS:** Request `Calendars.Read.Shared` to cover both
availability checking and meeting time suggestions.

---

## 4. OAuth for CLI/Plugin Context

### 4.1 Authentication Flows for Non-Web Apps

**Device Code Flow (recommended for CLI):**

The device code flow is designed for devices/CLI apps that cannot open a
browser inline. The flow:

1. App requests a device code from Azure AD
2. Azure AD returns a `user_code` and a `verification_uri`
3. App displays: "Go to https://microsoft.com/devicelogin and enter code ABCD1234"
4. User authenticates in a browser on any device
5. App polls Azure AD until authentication completes
6. App receives tokens (access + refresh)

**Auth Code with localhost redirect (alternative):**

For CLI apps on machines with a browser, the app can start a local HTTP server,
open the system browser, and receive the auth code via `http://localhost:{port}`
redirect. Faster UX but requires a local browser.

For WOS, **device code flow** is the better choice because:
- Works on remote/headless machines
- Works over SSH
- No need to manage a localhost HTTP server
- Simpler implementation

### 4.2 Azure AD App Registration (Minimal Setup)

**Steps in the Microsoft Entra admin center:**

1. Go to https://entra.microsoft.com
2. Navigate: Identity > Applications > App registrations > New registration
3. Set name: e.g., "WOS Graph Plugin"
4. Set supported account types: "Accounts in this organizational directory only"
   (or "any organizational directory" for multi-tenant)
5. Leave Redirect URI **empty** (device code flow does not need one)
6. Click Register
7. Copy the **Application (client) ID** and **Directory (tenant) ID**
8. Go to Authentication > Advanced settings > **Allow public client flows** > Yes > Save

**Minimal API permissions (delegated):**

| Permission | Reason |
|------------|--------|
| `User.Read` | Read basic profile (always included) |
| `Files.Read` | Read user's OneDrive files |
| `Calendars.Read.Shared` | Read calendars + shared calendars + findMeetingTimes |

Additional permissions to add only if needed:

| Permission | Reason |
|------------|--------|
| `Files.Read.All` | Access SharePoint and shared files |
| `Calendars.ReadWrite` | Create/modify calendar events |
| `Sites.Read.All` | Browse SharePoint site collections |

**Dynamic consent:** With delegated permissions, scopes can be requested
at runtime. The user consents to each scope the first time it is requested.
You do not need to pre-configure all permissions in the portal if using
dynamic consent (though pre-configuring is clearer for admin consent).

### 4.3 Token Storage and Refresh

**MSAL token lifecycle:**

- **Access tokens** expire in ~60-90 minutes
- **Refresh tokens** are long-lived (days to weeks, depending on policy)
- MSAL automatically uses refresh tokens when `acquire_token_silent()` is called
- The `acquire_token_silent()` method checks the cache for a valid access
  token first, then tries the refresh token if expired

**In-memory cache (default):**

MSAL provides an in-memory `SerializableTokenCache` by default. Tokens are
lost when the process exits.

**Persistent cache with `msal-extensions`:**

```bash
pip install msal-extensions
```

```python
import msal
from msal_extensions import (
    PersistedTokenCache,
    FilePersistenceWithDataProtection,  # Windows
    KeychainPersistence,                # macOS
    LibsecretPersistence,               # Linux (GNOME)
    FilePersistence,                     # Fallback (unencrypted)
)
import sys
import os


def build_persistence(cache_path: str):
    """Build platform-appropriate encrypted token persistence."""
    if sys.platform == "darwin":
        return KeychainPersistence(
            cache_path,
            service_name="wos-graph-tokens",
            account_name="wos",
        )
    elif sys.platform == "win32":
        return FilePersistenceWithDataProtection(cache_path)
    else:
        # Linux -- try libsecret, fall back to plaintext file
        try:
            return LibsecretPersistence(
                cache_path,
                schema_name="wos.graph.tokens",
                attributes={"app": "wos"},
            )
        except Exception:
            return FilePersistence(cache_path)


def create_app(client_id: str, tenant_id: str) -> msal.PublicClientApplication:
    """Create an MSAL app with persistent token cache."""
    cache_dir = os.path.join(os.path.expanduser("~"), ".wos")
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, "token_cache.bin")

    persistence = build_persistence(cache_path)
    cache = PersistedTokenCache(persistence)

    return msal.PublicClientApplication(
        client_id,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
        token_cache=cache,
    )
```

**Complete authentication flow for WOS:**

```python
import msal
import sys
from typing import Optional


SCOPES = [
    "User.Read",
    "Files.Read",
    "Calendars.Read.Shared",
]


def get_access_token(
    app: msal.PublicClientApplication,
    scopes: list[str] | None = None,
) -> str:
    """
    Get an access token, using cached credentials if available.
    Falls back to device code flow for interactive auth.
    """
    scopes = scopes or SCOPES
    accounts = app.get_accounts()

    result = None
    if accounts:
        # Try silent acquisition first (uses cached refresh token)
        result = app.acquire_token_silent(scopes, account=accounts[0])

    if not result or "access_token" not in result:
        # Fall back to device code flow
        flow = app.initiate_device_flow(scopes=scopes)
        if "user_code" not in flow:
            raise ValueError(
                f"Failed to create device flow: {flow.get('error_description')}"
            )

        print(flow["message"])  # "To sign in, visit https://microsoft.com/devicelogin ..."
        sys.stdout.flush()

        result = app.acquire_token_by_device_flow(flow)

    if "access_token" not in result:
        error = result.get("error_description", result.get("error", "Unknown error"))
        raise ValueError(f"Authentication failed: {error}")

    return result["access_token"]
```

### 4.4 Auth Library Comparison

| Feature | `msal` | `azure-identity` |
|---------|--------|-------------------|
| Device code flow | Yes (direct) | Yes (via `DeviceCodeCredential`) |
| Token cache | `SerializableTokenCache` (manual persistence) | Automatic via `TokenCachePersistenceOptions` |
| Persistent storage | Via `msal-extensions` | Built-in (uses MSAL under the hood) |
| Dependencies | Standalone (~5 deps) | Larger (~15 deps, includes `msal`) |
| Control | Full (raw token access) | Abstracted (credential objects) |
| Graph SDK compat | Manual (pass token in headers) | Direct (pass credential to SDK) |

**Recommendation for WOS:** Use `msal` directly with `msal-extensions` for
persistent cache. This gives full control over the auth flow, minimal
dependencies, and works well with raw `requests` calls.

---

## 5. Rate Limits and Throttling

### 5.1 General Throttling Behavior

Microsoft Graph returns HTTP `429 Too Many Requests` when throttled. The
response includes a `Retry-After` header (in seconds).

**Global limit:** 130,000 requests per 10 seconds per app across all tenants.

Starting September 2025, per-app/per-user/per-tenant limits are further
reduced to half the total per-tenant limit to prevent a single user/app from
consuming all quota.

Throttling is **dynamic** -- it varies based on app, tenant, workload,
endpoint, and time of day. There are no fixed published numbers for most
services.

### 5.2 Service-Specific Limits

**OneDrive/SharePoint:** No published per-request limits in Graph
documentation. Governed by SharePoint-specific throttling (separate from
Graph). Best practice is to limit to a few requests per second per user.

**Outlook Calendar:** No published specific limits in the service-specific
throttling page. Falls under general Graph limits.

**findMeetingTimes:** This is a computationally expensive operation on
Microsoft's side. It checks multiple calendars and computes availability.
Expected to be slower and more rate-sensitive than simple GET operations.

### 5.3 Throttle Handling Pattern for WOS

```python
import time
import requests
from typing import Any


def graph_request(
    method: str,
    url: str,
    access_token: str,
    max_retries: int = 3,
    **kwargs: Any,
) -> requests.Response:
    """
    Make a Graph API request with automatic retry on 429 throttling.

    Respects the Retry-After header. Falls back to exponential backoff
    if no header is present.
    """
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {access_token}"

    for attempt in range(max_retries + 1):
        response = requests.request(
            method, url, headers=headers, **kwargs
        )

        if response.status_code != 429:
            return response

        # Throttled -- respect Retry-After header
        retry_after = int(response.headers.get("Retry-After", 2 ** attempt))
        if attempt < max_retries:
            time.sleep(retry_after)

    return response  # Return last response even if still 429
```

**Best practices:**

1. Always respect the `Retry-After` header
2. Spread requests over time rather than bursting
3. Use `$select` to request only needed fields (reduces server load)
4. Use `$top` to limit page sizes
5. Cache responses where appropriate (file metadata, calendar events)
6. The Graph SDK has built-in retry handling; with raw REST you must
   implement it yourself (as shown above)

---

## 6. Minimum Permissions Summary for WOS

For the full set of WOS calendar + documents skills:

| Permission | Type | Required For |
|------------|------|-------------|
| `User.Read` | Delegated | Basic profile, always included |
| `Files.Read` | Delegated | Download user's OneDrive files |
| `Calendars.Read.Shared` | Delegated | Calendar view, getSchedule, findMeetingTimes |

**Optional escalations:**

| Permission | When Needed |
|------------|-------------|
| `Files.Read.All` | SharePoint document library access |
| `Calendars.ReadWrite` | Creating/updating calendar events |
| `Sites.Read.All` | Browsing SharePoint site collections |

---

## 7. Implementation Recommendations for WOS

### Dependencies to add to WOS

```
msal>=1.28.0
msal-extensions>=1.1.0
requests>=2.28  (already a WOS dependency)
markitdown[pdf,docx,pptx]>=0.1.0  (for document conversion, needs Python 3.10+)
```

### Suggested module structure

```
wos/
  graph/
    __init__.py           # Public API
    auth.py               # MSAL device code flow + persistent cache
    client.py             # Base HTTP client with retry/throttle
    documents.py          # OneDrive/SharePoint file operations
    calendar.py           # Calendar events, getSchedule, findMeetingTimes
```

### Key constraints to be aware of

1. **`findMeetingTimes` is delegated-only** -- no application-level auth,
   no personal Microsoft accounts. Work/school accounts only.
2. **`markitdown` requires Python 3.10+** -- WOS currently targets 3.9.
   Either bump the minimum version or use `pypandoc`/`mammoth` as
   alternatives.
3. **Token persistence on Linux** without GNOME Keyring falls back to
   unencrypted file storage. Document this as a known limitation.
4. **`getSchedule` has a 1000-entry limit** per user per time range.
   Keep query windows small for busy calendars.
5. **No personal Microsoft account support** for `findMeetingTimes` or
   `getSchedule`. These require Microsoft 365 work/school mailboxes.
6. **Rate limits are dynamic and unpublished** for calendar/files endpoints.
   Build in retry logic from day one.
