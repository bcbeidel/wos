---
name: Existing Google/Microsoft Integration Patterns in AI Tools
description: Survey of how AI tools integrate with Google and Microsoft platforms — patterns, anti-patterns, and actionable lessons for WOS native skills
type: research
sources:
  - https://github.com/taylorwilsdon/google_workspace_mcp
  - https://github.com/elyxlz/microsoft-mcp
  - https://github.com/nspady/google-calendar-mcp
  - https://github.com/jgordley/GoogleCalendarAssistant
  - https://python.langchain.com/docs/integrations/tools/google_calendar/
  - https://python.langchain.com/api_reference/google_community/calendar/langchain_google_community.calendar.toolkit.CalendarToolkit.html
  - https://github.com/ComposioHQ/awesome-claude-skills
  - https://github.com/travisvn/awesome-claude-skills
  - https://github.com/hesreallyhim/awesome-claude-code
  - https://composio.dev/toolkits/gmail/framework/claude-code
  - https://composio.dev/toolkits/slack/framework/claude-code
  - https://learn.microsoft.com/en-us/graph/throttling
  - https://learn.microsoft.com/en-us/graph/resolve-auth-errors
  - https://learn.microsoft.com/en-us/graph/errors
  - https://learn.microsoft.com/en-us/entra/msal/python/advanced/msal-error-handling-python
  - https://developers.google.com/identity/protocols/oauth2/resources/best-practices
  - https://skywork.ai/blog/oauth-token-leakage-ai-chatgpt-gmail-security/
  - https://datatracker.ietf.org/doc/rfc9700/
  - https://www.cdata.com/blog/navigating-the-hurdles-mcp-limitations
  - https://www.cronofy.com/blog/best-calendar-apis
  - https://peps.python.org/pep-0544/
  - https://realpython.com/python-protocol/
  - https://jellis18.github.io/post/2022-01-11-abc-vs-protocol/
  - https://deepwiki.com/microsoftgraph/msgraph-sdk-python/4.2-user-authentication
  - https://cloud.google.com/blog/products/ai-machine-learning/learn-how-to-handle-429-resource-exhaustion-errors-in-your-llms
  - https://www.firecrawl.dev/blog/best-claude-code-plugins
related:
  - artifacts/plans/2026-02-22-simplification-design.md
---

# Existing Google/Microsoft Integration Patterns in AI Tools

This document surveys how existing AI tools, plugins, and open-source projects integrate
with Google and Microsoft platforms. The goal is to extract actionable lessons for WOS,
which is building native Python skills (not MCP servers) for Google/Microsoft integration.

---

## 1. Existing Implementations

### 1.1 MCP Servers (reference implementations)

Three notable MCP servers cover Google and Microsoft integrations comprehensively:

**[google_workspace_mcp](https://github.com/taylorwilsdon/google_workspace_mcp)** by Taylor Wilsdon
is the most feature-complete Google integration. It covers Gmail, Calendar, Docs, Sheets,
Slides, Chat, Forms, Tasks, Search, and Drive. Key architectural traits:

- **Per-service directories**: `gmail/`, `gcalendar/`, `gdocs/`, `gsheets/`, etc. Each
  service is a self-contained module with its own tools.
- **Tool tiers**: Core, Extended, and Complete tiers let users control how many tools are
  exposed — a pragmatic response to LLM context limits.
- **Read-only mode**: A `--read-only` flag requests only read-only OAuth scopes and
  disables write tools entirely. This is the closest pattern to what WOS wants.
- **OAuth 2.0/2.1**: Transport-aware callback handling (stdio mode spins up a minimal
  HTTP server on port 8000; HTTP mode uses the existing FastAPI server).

**[microsoft-mcp](https://github.com/elyxlz/microsoft-mcp)** by elyxlz covers Outlook,
Calendar, OneDrive, and Contacts via Microsoft Graph. Notable patterns:

- **Multi-account support**: Every tool takes an `account_id` parameter as its first
  argument, enabling personal/work/school accounts simultaneously.
- **Device code flow**: Uses OAuth 2.0 device code flow for authentication, which avoids
  redirect URI complexity but requires Azure app registration.
- **Token cache file**: Stores tokens at `~/.microsoft_mcp_token_cache.json`. Simple but
  raises questions about multi-user environments.

**[google-calendar-mcp](https://github.com/nspady/google-calendar-mcp)** by Nick Spady is
a focused Calendar-only server with 12 tools. Notable design decisions:

- **Multi-account merging**: Read-only tools merge results from all accounts automatically;
  write tools auto-select the appropriate account. This is a clever UX pattern.
- **Tool filtering via env var**: `ENABLED_TOOLS` lets operators restrict which tools are
  available — useful for security-constrained deployments.
- **Disabled tool visibility**: The system informs the AI which tools exist but are disabled,
  rather than hiding them entirely, which avoids confusion when users ask for capabilities
  that are present but restricted.

### 1.2 LangChain Integrations

**[LangChain CalendarToolkit](https://python.langchain.com/docs/integrations/tools/google_calendar/)**
(`langchain_google_community.calendar`) provides tools for Google Calendar:

- CalendarCreateEvent, CalendarSearchEvents, CalendarUpdateEvent, CalendarDeleteEvent
- Uses the `@tool` decorator pattern with type-hinted parameters
- **No built-in read/write separation** — all tools are exposed together. The documentation
  explicitly warns: "This toolkit contains tools that can read and modify the state of a
  service." Safety is left to the consuming application.

**[GoogleCalendarAssistant](https://github.com/jgordley/GoogleCalendarAssistant)** (Calvin)
is a Next.js + FastAPI + LangChain chatbot. It demonstrates the typical "full access" pattern
where the agent can read and write without confirmation gates. No safety patterns were
documented.

### 1.3 Claude Code Plugins and Skills

The Claude Code plugin ecosystem is growing rapidly. Notable examples relevant to external
API integration:

- **[Composio connect-apps](https://composio.dev/toolkits/gmail/framework/claude-code)**:
  A "Tool Router" that connects Claude to 500+ SaaS apps (Gmail, Slack, GitHub, Notion).
  Uses MCP under the hood but presents a unified skill interface. Auth is handled per-user
  with stored OAuth tokens. This is the closest existing example of a Claude Code skill
  doing external platform integration.
- **claude-code-safety-net**: A plugin that catches destructive git and filesystem commands
  before execution. Relevant as a pattern for write-safety in a different domain.
- No existing Claude Code plugins were found that implement read-only Google/Microsoft
  integration with explicit write confirmation — this is a gap WOS can fill.

### 1.4 Read-Only vs Write Safety Patterns

Across the surveyed implementations, three approaches to the read/write boundary emerge:

| Pattern | Used By | How It Works |
|---------|---------|-------------|
| **Flag-based restriction** | google_workspace_mcp | `--read-only` flag disables write tools and requests read-only OAuth scopes |
| **Tool filtering** | google-calendar-mcp | `ENABLED_TOOLS` env var whitelists specific tools |
| **No restriction** | LangChain CalendarToolkit, Calvin | All tools exposed; safety is the user's problem |

**No surveyed tool implements the WOS model** of "agent reads freely, surfaces information,
but never writes without explicit user confirmation." This is a differentiator. The closest
is google_workspace_mcp's `--read-only` mode, but that is all-or-nothing rather than
read-freely-with-confirmed-writes.

Microsoft's own Agent Framework documentation recommends "human-in-the-loop to approve
high-impact actions in a downstream system," but this is guidance, not an implemented
pattern in the MCP servers surveyed.

---

## 2. Adapter and Abstraction Patterns

### 2.1 How Multi-Platform Tools Abstract Differences

The calendar aggregation space has mature examples of cross-platform abstraction:

- **[Cronofy](https://www.cronofy.com/blog/best-calendar-apis)** is a commercial unified
  calendar API that abstracts Google, Microsoft, Apple, and others behind a single REST
  interface. It demonstrates that a thin adapter layer is viable, but also that edge cases
  (recurring events, all-day events, timezone handling) are where abstractions leak.
- **google_workspace_mcp** and **microsoft-mcp** do not abstract across platforms at all.
  Each is a standalone server for one platform. This is the simpler approach and avoids
  premature abstraction.

### 2.2 Recommended Adapter Pattern for WOS

Based on the survey, the **Protocol-based adapter** pattern (PEP 544 structural subtyping)
is the best fit for WOS:

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class CalendarReader(Protocol):
    """Structural interface for calendar read operations."""
    def list_events(self, start: str, end: str) -> list[dict]: ...
    def get_event(self, event_id: str) -> dict: ...
    def check_availability(self, start: str, end: str) -> list[dict]: ...

@runtime_checkable
class DocumentReader(Protocol):
    """Structural interface for document read operations."""
    def get_document(self, doc_id: str) -> dict: ...
    def search_documents(self, query: str) -> list[dict]: ...
```

Why Protocol over ABC:

- **Low coupling**: Platform adapters do not need to inherit from a shared base class.
  Google and Microsoft adapters can be completely independent modules that happen to
  satisfy the same structural interface.
- **Testability**: Test doubles satisfy the Protocol without inheriting anything.
- **Gradual adoption**: You can add the Protocol later without changing existing adapters.
- **WOS philosophy**: Consistent with "convention over enforcement" — the Protocol
  documents the expected shape, and type checkers verify compliance, but there is no
  runtime inheritance machinery.

When to use ABC instead: If WOS eventually supports third-party platform adapters (a plugin
API for platforms), ABC's runtime instantiation enforcement prevents incomplete
implementations from being loaded. But that is a future concern.

### 2.3 Handling Platform-Specific Capabilities

Key differences between Google Calendar API and Microsoft Graph Calendar API:

| Capability | Google Calendar | Microsoft Graph |
|-----------|----------------|-----------------|
| Scope | Calendar-only API | Unified API (mail, calendar, files, contacts) |
| Free/busy | Dedicated endpoint | `getSchedule` method |
| Recurring events | `exdate` rules + canceled occurrences | Exception occurrences with separate IDs |
| All-day events | `date` field (not `dateTime`) | `isAllDay` boolean |
| Permissions | Per-calendar ACLs | Delegated vs application permissions |

Recommended approach: **Do not hide these differences behind a forced abstraction.** Instead:

1. Define a shared Protocol for capabilities that genuinely overlap (list events, get
   event, check availability).
2. Let platform-specific capabilities live as platform-specific methods on the adapter.
3. Use a `capabilities` property or method so the skill layer can discover what a given
   adapter supports at runtime.

```python
class GoogleCalendarAdapter:
    @property
    def capabilities(self) -> set[str]:
        return {"list_events", "get_event", "check_availability", "list_calendars"}

    # Platform-specific: Google's color system
    def list_colors(self) -> dict: ...
```

This avoids the anti-pattern of lowest-common-denominator abstraction where platform
strengths are hidden.

---

## 3. Error Handling and UX

### 3.1 Surfacing API Failures

**Microsoft Graph** provides structured error responses with nested error codes. Best
practice: loop through all nested error codes and use the most detailed one the application
understands. The Python SDK wraps these in `APIError` from `kiota_abstractions.api_error`.

**Google APIs** return HTTP status codes with JSON error bodies. The `google-api-core`
library provides `google.api_core.exceptions` with specific exception types
(`ResourceExhausted`, `PermissionDenied`, `NotFound`, etc.).

For WOS, the recommended error taxonomy for user-facing messages:

| Category | Example | User Message Pattern |
|----------|---------|---------------------|
| **Auth failure** | Token expired, missing scopes | "Your Google Calendar access has expired. Run `/wos:connect google` to re-authenticate." |
| **Permission denied** | Insufficient OAuth scope | "WOS has read-only access to Calendar but this action requires write permission. You granted read-only access during setup." |
| **Rate limited** | 429 Too Many Requests | "Google Calendar API is temporarily throttling requests. Trying again in {N} seconds." |
| **Not found** | Event/document deleted | "Event '{id}' was not found. It may have been deleted." |
| **Platform unavailable** | 500/503 from upstream | "Google Calendar API is temporarily unavailable. Try again in a few minutes." |

Key principle: **Always tell the user what they can do about it**, not just what went wrong.

### 3.2 Rate Limiting Strategies

**Microsoft Graph** throttling:
- Returns HTTP 429 with a `Retry-After` header (in seconds).
- Service-specific limits vary (e.g., Outlook: 10,000 requests per 10 minutes per app per
  mailbox).
- The official Python SDK includes built-in retry handlers with exponential backoff.
- Best practice: Use `$select` to request only needed fields, use delta queries for change
  tracking, avoid polling (use change notifications instead).

**Google APIs** throttling:
- Returns HTTP 429 with exponential backoff formula: `min(((2^n) + random_ms), max_backoff)`.
- Per-user and per-project quotas.
- The `google-api-core` library supports automatic retries for transient errors.
- The `tenacity` library is commonly used for custom retry decorators.

For WOS, the recommended approach:

```python
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

@retry(
    wait=wait_exponential(multiplier=1, min=1, max=60),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type((RateLimitError, TransientError)),
)
def fetch_events(adapter, start, end):
    return adapter.list_events(start, end)
```

Use `tenacity` rather than hand-rolling retry logic. It is well-tested, widely adopted,
and handles jitter correctly.

### 3.3 Auth Failure vs API Error Distinction

The most common UX mistake across surveyed tools is conflating auth failures with API
errors. Users see "request failed" when the real problem is "your token expired." The
microsoft-mcp project's advice to "delete the cache file and re-authenticate" is functional
but poor UX.

WOS should:
1. Catch auth-specific exceptions (`InvalidGrantError`, `AuthenticationError`) separately
   from API exceptions.
2. Provide a recovery action: "Run `/wos:connect google` to re-authenticate."
3. Never expose raw HTTP status codes or OAuth error codes to users.

---

## 4. Anti-Patterns to Avoid

### 4.1 Google Docs/Calendar Integration Mistakes

1. **Requesting all OAuth scopes upfront.** Google's own best practice documentation
   recommends incremental authorization — request scopes only when the user triggers a
   feature that needs them. The google_workspace_mcp server requests all scopes at startup,
   which triggers Google's "unverified app" screen for broad scopes.

2. **Ignoring recurring event complexity.** Google Calendar represents recurring events with
   `exdate` rules and canceled occurrences that are difficult to parse. Many integrations
   treat recurring events as simple repeated events and break when exceptions exist.

3. **Not handling Google's API deprecation cycle.** Google occasionally changes APIs with
   relatively short deprecation windows. Integrations that pin to specific API versions
   without monitoring changelogs break silently.

4. **Treating all-day events like timed events.** Google uses a `date` field (not
   `dateTime`) for all-day events. Code that always expects `dateTime` will crash or
   produce wrong results.

### 4.2 Microsoft Graph Integration Mistakes

1. **Over-requesting permissions.** Azure app registrations make it easy to request
   `Mail.ReadWrite` when `Mail.Read` suffices. The 2025 Salesloft-Drift breach was caused
   by compromised OAuth tokens with overly broad scopes — the blast radius was 10x larger
   than necessary because of excessive permissions.

2. **Confusing delegated vs application permissions.** Delegated permissions act on behalf
   of a signed-in user; application permissions act as the app itself without a user. Many
   integrations request application permissions (which grant tenant-wide access) when
   delegated permissions would suffice.

3. **Not handling multi-account complexity.** Microsoft accounts can be personal, work, or
   school, each with different API behaviors. The microsoft-mcp server handles this with
   `account_id` parameters, which is the right approach but adds complexity.

4. **Ignoring pagination.** Microsoft Graph returns paginated results with `@odata.nextLink`.
   Integrations that only read the first page silently miss data.

### 4.3 Security Pitfalls

1. **Token storage in plaintext.** The microsoft-mcp server stores tokens at
   `~/.microsoft_mcp_token_cache.json` in plaintext. WOS should use the OS keychain
   (via `keyring` library) or encrypted storage.

2. **Logging tokens.** Access tokens appearing in application logs, error traces, or crash
   reports is a leading cause of token leakage. WOS should never log token values, even
   at DEBUG level.

3. **Not revoking tokens on disconnect.** When a user disconnects an integration, tokens
   should be revoked via the provider's revocation endpoint, not just deleted locally.

4. **Scopeless token requests.** Requesting an access token without specifying scopes is a
   severe anti-pattern. If the API does not check scopes, the token may grant full user
   permissions. Always request the minimum scopes needed.

5. **Using the implicit OAuth flow.** The implicit flow (response type `token`) exposes
   access tokens in URL fragments, browser history, and referrer headers. RFC 9700 (2025)
   explicitly deprecates this flow. Use the authorization code flow with PKCE instead.

### 4.4 Over-Abstraction

The most common architectural anti-pattern across surveyed tools is **lowest-common-denominator
abstraction** — hiding platform differences behind an interface so thin that useful features
are inaccessible. Cronofy's unified API demonstrates that this is possible but requires
significant ongoing maintenance as platforms evolve independently.

For WOS, the risk is building a `PlatformAdapter` ABC that forces Google and Microsoft into
identical shapes and loses the strengths of each:

- Google Calendar's color system has no Microsoft equivalent.
- Microsoft Graph's unified API means calendar + email queries can be correlated; Google
  requires separate API calls.
- Google Docs' collaborative editing model differs fundamentally from Microsoft's.

**Lesson: Abstract the 80% that overlaps. Expose the 20% that differs as platform-specific
capabilities.**

---

## 5. MCP Servers: Lessons for WOS (Why Native Skills)

### 5.1 What MCP Servers Do Well

- **Standardized tool discovery**: The MCP protocol lets AI hosts discover available tools
  dynamically.
- **Isolation**: Each server runs as a separate process, limiting blast radius.
- **Reusability**: One MCP server can serve multiple AI hosts (Claude Desktop, VS Code, etc.).

### 5.2 MCP Limitations That Motivate Native Skills

1. **Opaque code**: MCP servers are black boxes to the consuming AI. WOS skills are Python
   code that Claude can read, understand, and reason about. When debugging fails, Claude
   can read the adapter source code and explain what went wrong.

2. **Fixed timeout (60 seconds)**: MCP operations have a 60-second timeout. Long-running
   operations (e.g., searching large mailboxes, paginating through thousands of calendar
   events) fail silently.

3. **No dynamic tool selection**: MCP tools have fixed resources and operations. The system
   cannot dynamically select different operations based on context — for example, an MCP
   email tool must have its resource and operation predetermined.

4. **User must build their own**: For MCP to work, users need to be technical enough to
   set up and configure their own MCP server. WOS skills ship as part of the plugin and
   "just work" after authentication.

5. **No code-level introspection**: Claude cannot read MCP server source code to understand
   edge cases, debug failures, or suggest improvements. With native skills, the entire
   integration is visible.

6. **Ecosystem maturity**: Many widely used applications have not released MCP server
   offerings. The ecosystem is young and fragmented.

### 5.3 What WOS Should Adopt from MCP Server Design

Despite not using MCP, several patterns from MCP servers are worth adopting:

- **Per-service module organization** (from google_workspace_mcp): Keep Google Calendar,
  Google Docs, and Microsoft Graph in separate modules under `wos/`.
- **Tool tiers / capability filtering** (from google_workspace_mcp and google-calendar-mcp):
  Let users control which capabilities are active.
- **Read-only mode as a first-class concept** (from google_workspace_mcp): Make read-only
  the default; write operations require explicit opt-in.
- **Multi-account support via explicit account parameter** (from microsoft-mcp): Do not
  assume a single account. Design the adapter interface to accept account identifiers.
- **Disabled capability visibility** (from google-calendar-mcp): When a capability is
  restricted, tell the user it exists but is disabled, rather than hiding it.

---

## 6. Actionable Recommendations for WOS

### What WOS Should Adopt

1. **Protocol-based adapter interfaces** (PEP 544) for cross-platform abstraction, with
   platform-specific capabilities exposed separately.
2. **Read-only by default**: OAuth scopes should request read-only access. Write operations
   should be a separate, explicit authorization step.
3. **Human-in-the-loop for writes**: Surface write actions as suggestions with explicit
   user confirmation. Never execute writes silently.
4. **Per-service modules**: `wos/google_calendar.py`, `wos/google_docs.py`,
   `wos/ms_graph.py` — not a monolithic adapter.
5. **Structured error messages** with recovery actions, not raw API errors.
6. **`tenacity`-based retry** with exponential backoff and jitter for rate limiting.
7. **Incremental OAuth scopes**: Request Calendar read-only when the user first uses
   calendar features, not all Google scopes at plugin install time.
8. **OS keychain for token storage** via the `keyring` library.
9. **Capability discovery**: Each adapter exposes a `capabilities` set so the skill layer
   knows what is available without try/except.

### What WOS Should Avoid

1. **Lowest-common-denominator abstraction** that hides platform strengths.
2. **All-or-nothing scope requests** that trigger "unverified app" warnings.
3. **Plaintext token storage** in config files.
4. **Logging token values** at any log level.
5. **Treating recurring events as simple repeats** without handling exceptions.
6. **Confusing delegated vs application permissions** for Microsoft Graph.
7. **Building an MCP server** when native skills give Claude full code visibility.
8. **Using the implicit OAuth flow** (deprecated by RFC 9700).
9. **Hiding disabled capabilities** — always tell users what exists but is restricted.
10. **Hand-rolling retry logic** instead of using battle-tested libraries.
