---
name: OAuth Token Management Patterns for CLI Tools
description: Research on secure OAuth token storage, lifecycle, and management patterns for CLI tools and plugins, with a recommended approach for WOS.
type: research
sources:
  - https://cli.github.com/manual/gh_auth_login
  - https://kollitsch.dev/blog/2023/saving-github-access-token-in-local-encrypted-storage-via-gh-cli/
  - https://github.com/cli/cli/issues/10108
  - https://github.com/cli/cli/discussions/7109
  - https://docs.google.com/sdk/docs/authorizing
  - https://cloud.google.com/sdk/docs/authorizing
  - https://docs.google.com/docs/authentication/application-default-credentials
  - https://learn.microsoft.com/en-us/cli/azure/msal-based-azure-cli
  - https://learn.microsoft.com/en-us/entra/identity-platform/msal-acquire-cache-tokens
  - https://learn.microsoft.com/en-us/entra/identity-platform/refresh-tokens
  - https://learn.microsoft.com/en-us/entra/identity-platform/configurable-token-lifetimes
  - https://learn.microsoft.com/en-us/entra/identity-platform/scopes-oidc
  - https://learn.microsoft.com/en-us/entra/msal/python/
  - https://learn.microsoft.com/en-us/entra/msal/python/getting-started/acquiring-tokens
  - https://github.com/Azure-Samples/ms-identity-python-devicecodeflow
  - https://pypi.org/project/keyring/
  - https://pypi.org/project/msal/
  - https://pypi.org/project/Authlib/
  - https://pypi.org/project/google-auth-oauthlib/
  - https://developers.google.com/identity/protocols/oauth2
  - https://developers.google.com/identity/protocols/oauth2/scopes
  - https://developers.google.com/identity/protocols/oauth2/web-server
  - https://developers.google.com/identity/protocols/oauth2/resources/best-practices
  - https://developers.google.com/workspace/calendar/api/auth
  - https://developers.google.com/workspace/gmail/api/auth/scopes
  - https://graphpermissions.merill.net/permission/Calendars.Read
  - https://graphpermissions.merill.net/permission/Mail.Read
  - https://googleapis.github.io/google-api-python-client/docs/oauth-installed.html
  - https://google-auth-oauthlib.readthedocs.io/en/latest/reference/google_auth_oauthlib.flow.html
  - https://msal-python.readthedocs.io/
  - https://docs.authlib.org/en/latest/client/oauth2.html
  - https://requests-oauthlib.readthedocs.io/
  - https://datatracker.ietf.org/doc/html/draft-ietf-oauth-security-topics
  - https://cheatsheetseries.owasp.org/cheatsheets/OAuth2_Cheat_Sheet.html
  - https://auth0.com/docs/secure/tokens/token-best-practices
  - https://cloud.google.com/architecture/bps-for-mitigating-gcloud-oauth-tokens
related:
  - docs/plans/2026-02-22-simplification-design.md
---

# OAuth Token Management Patterns for CLI Tools

This document surveys how established CLI tools handle OAuth token storage,
lifecycle, and security, then recommends an approach for WOS -- a Claude Code
plugin that will authenticate with Google and Microsoft APIs using read-only
scopes.

---

## 1. Token Storage Patterns

### 1.1 What established CLI tools do

#### `gh` CLI (GitHub)

The GitHub CLI implements a **three-tier storage strategy**:

1. **System keyring (default since ~v2.40):** Uses the OS-native credential
   store -- macOS Keychain, Windows Credential Manager, or Linux Secret
   Service (via D-Bus). This became the default after initially being opt-in
   via `--secure-storage`.
2. **Encrypted file fallback:** If no keyring is detected, `gh` falls back to
   writing the token to a plain-text config file at
   `~/.config/gh/hosts.yml`. This silent fallback has been controversial
   (see [cli/cli#10108](https://github.com/cli/cli/issues/10108)), with
   proposals to make the failure explicit rather than silent.
3. **Environment variable:** `GITHUB_TOKEN` or `GH_TOKEN` can override stored
   credentials entirely, which is the standard pattern for CI/headless
   environments.

Key takeaway: `gh` started with file-based storage, migrated to keyring as
default, and learned that **silent fallback to insecure storage is a UX and
security problem**.

#### `gcloud` CLI (Google Cloud)

Google's CLI stores credentials as **plain JSON files** on disk:

- User credentials: `~/.config/gcloud/credentials.db` (SQLite) and
  `~/.config/gcloud/application_default_credentials.json`
- The `application_default_credentials.json` file contains `client_id`,
  `client_secret`, and `refresh_token` in plain text
- File permissions are set to owner-only (0600) on Unix systems

Google explicitly warns: "Any user with access to your file system can use
those credentials." They rely on filesystem permissions rather than encryption,
accepting this trade-off for simplicity and headless compatibility.

#### `az` CLI (Azure)

Azure CLI uses **MSAL's token cache**:

- Token cache location: `~/.azure/msal_token_cache.bin` (or `.json`)
- **On Windows:** encrypted via DPAPI (Data Protection API), bound to the
  Windows user account
- **On macOS and Linux:** stored as plaintext files
- Stores both access tokens and refresh tokens
- The older `accessTokens.json` format has been deprecated in favor of the
  MSAL cache

### 1.2 Storage options comparison

| Approach | Security | Cross-platform | Headless/CI | Complexity |
|----------|----------|----------------|-------------|------------|
| OS keyring (`keyring` pkg) | High (OS-managed encryption) | macOS, Windows, Linux w/ Secret Service | Poor (requires D-Bus or GUI) | Medium |
| Encrypted file (app-managed) | Medium (key management is your problem) | Excellent | Good | High |
| Plain JSON + 0600 perms | Low-Medium (filesystem ACL only) | Excellent | Excellent | Low |
| Environment variable | Varies (depends on env security) | Excellent | Excellent | Low |

### 1.3 The `keyring` Python package

The `keyring` package provides a unified API across OS credential stores:

- **macOS:** Keychain
- **Windows:** Windows Credential Locker (formerly Credential Manager)
- **Linux:** GNOME Keyring / KDE Wallet via Secret Service D-Bus API

```python
import keyring

# Store a token
keyring.set_password("wos-google", "user@example.com", refresh_token)

# Retrieve a token
token = keyring.get_password("wos-google", "user@example.com")

# Delete a token
keyring.delete_password("wos-google", "user@example.com")
```

**Limitations:**

- On Linux, requires a running D-Bus session with a secret service provider
  (GNOME Keyring, KDE Wallet). Headless servers typically lack this.
- Falls back to an insecure plaintext backend or raises `NoKeyringError` if
  no backend is available.
- In CI/container environments, the keyring is generally unavailable.
- Some Linux environments prompt for a keyring unlock password, which breaks
  non-interactive flows.

---

## 2. Minimal Scoping

### 2.1 Google: read-only scopes

Google uses URL-based scope identifiers. For WOS's read-only needs:

| API | Read-only scope | What it grants |
|-----|----------------|----------------|
| Calendar | `https://www.googleapis.com/auth/calendar.readonly` | Read calendar events |
| Calendar (events only) | `https://www.googleapis.com/auth/calendar.events.readonly` | Read events without settings |
| Gmail | `https://www.googleapis.com/auth/gmail.readonly` | Read emails and settings |
| Gmail (metadata only) | `https://www.googleapis.com/auth/gmail.metadata` | Read message metadata (no body) |

Google classifies scopes into three tiers:

1. **Non-sensitive:** No verification required (e.g., `openid`, `profile`)
2. **Sensitive:** Requires app verification (e.g., `calendar.readonly`)
3. **Restricted:** Requires security assessment (e.g., full `gmail` access)

The `calendar.readonly` scope is *sensitive* (requires verification but not a
full security audit). The `gmail.readonly` scope is also sensitive. WOS should
request the narrowest scope needed.

### 2.2 Microsoft: read-only scopes

Microsoft uses dot-separated permission names for Graph API:

| API | Read-only scope | What it grants |
|-----|----------------|----------------|
| Calendar | `Calendars.Read` | Read user's calendar events |
| Mail | `Mail.Read` | Read user's email messages |
| User profile | `User.Read` | Read basic profile (usually always included) |

Microsoft also supports `.Shared` variants (e.g., `Calendars.Read.Shared`) for
accessing shared mailboxes/calendars.

### 2.3 Scope validation at token acquisition

**Can we refuse over-privileged tokens?**

Both Google and Microsoft return the granted scopes in the token response:

```json
{
  "access_token": "...",
  "scope": "https://www.googleapis.com/auth/calendar.readonly",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

WOS can (and should) validate the response:

```python
def validate_scopes(granted_scopes: set[str], required_scopes: set[str]) -> None:
    """Refuse tokens with unexpected extra scopes."""
    extra = granted_scopes - required_scopes - ALLOWED_BASELINE_SCOPES
    if extra:
        raise ValueError(
            f"Token carries unexpected scopes: {extra}. "
            "Revoke and re-authorize with minimal permissions."
        )
```

**What happens if a user grants broader scopes?** The OAuth consent screen
shows exactly what was requested. Users cannot grant *more* than requested in
the standard flow -- the authorization server only issues the scopes that were
requested. However, if the same client ID has previously been authorized with
broader scopes, some providers may return a union of previously granted scopes.
Google's `include_granted_scopes=true` parameter enables this "incremental
authorization" behavior explicitly.

**Recommendation:** Always request scopes explicitly, never use
`include_granted_scopes=true`, and validate the returned scope set matches
expectations.

---

## 3. Token Lifecycle

### 3.1 Access token expiry

| Provider | Default access token lifetime | Configurable? |
|----------|------------------------------|---------------|
| Google | 3,600 seconds (1 hour) | Service accounts can extend to 12 hours |
| Microsoft | 60-90 minutes (avg 75 min); 2 hours for Teams/M365 clients | Configurable up to ~24 hours via tenant policy |

### 3.2 Refresh token behavior

#### Google refresh tokens

- **Lifetime:** Do not expire by default. Valid until the user explicitly
  revokes access.
- **Expiration conditions:**
  - User revokes access via Google Account settings
  - Token unused for 6 months
  - User changes password (if token carries Gmail scopes)
  - Per-user/per-client token limit exceeded (older tokens invalidated)
  - App is in "Testing" publishing status: **7-day expiry** (important
    during development)
- **Rotation:** Google does not rotate refresh tokens on each use -- the same
  refresh token remains valid.

#### Microsoft refresh tokens

- **Lifetime:** 90 days (rolling window) for desktop/mobile apps; 24 hours
  for SPAs.
- **Rolling behavior:** Each time the refresh token is used, a new one is
  issued. The new token's lifetime equals the *remaining* lifetime of the
  original, not a fresh 90 days.
- **Inactivity expiration:** Tokens expire if unused for the configured
  inactivity period (varies by tenant policy).
- **Rotation:** Microsoft issues a new refresh token with each access token
  refresh, and the old one is invalidated.

#### Key difference

Google keeps the same refresh token forever (until revoked); Microsoft rotates
refresh tokens on each use and they have a finite lifetime. WOS must persist
the *new* refresh token after every Microsoft token refresh.

### 3.3 Transparent refresh

Both Google and Microsoft libraries handle token refresh automatically:

**Google (`google-auth-oauthlib`):**

```python
from google.oauth2.credentials import Credentials

creds = Credentials(
    token=access_token,
    refresh_token=refresh_token,
    client_id=client_id,
    client_secret=client_secret,
    token_uri="https://oauth2.googleapis.com/token",
)

if creds.expired and creds.refresh_token:
    creds.refresh(google.auth.transport.requests.Request())
    # creds.token now has a fresh access token
```

**Microsoft (`msal`):**

```python
import msal

app = msal.PublicClientApplication(client_id, authority=authority)
accounts = app.get_accounts()
if accounts:
    result = app.acquire_token_silent(scopes, account=accounts[0])
    # MSAL checks the cache, refreshes if expired, returns fresh token
    # result["access_token"] is ready to use
```

MSAL's `acquire_token_silent()` handles the full cache lookup + refresh cycle
internally. Google's library requires an explicit `refresh()` call but the
pattern is straightforward.

### 3.4 Revocation

#### Google

POST to `https://oauth2.googleapis.com/revoke` with the token in the body:

```python
import requests

requests.post(
    "https://oauth2.googleapis.com/revoke",
    params={"token": refresh_token},
    headers={"Content-Type": "application/x-www-form-urlencoded"},
)
```

Revoking the refresh token also invalidates all associated access tokens.

#### Microsoft

MSAL provides `remove_account()` which clears tokens from the local cache.
For server-side revocation, the Microsoft identity platform supports the
standard logout endpoint:

```
https://login.microsoftonline.com/common/oauth2/v2.0/logout
```

However, Microsoft does not currently support the OAuth 2.0 token revocation
endpoint (RFC 7009) for revoking individual tokens programmatically. The
`remove_account()` method is the recommended approach for desktop/CLI apps.

**Recommendation:** WOS should implement a `/wos:logout` or disconnect flow
that (1) revokes the Google token via their revocation endpoint, (2) clears
the Microsoft account from the MSAL cache, and (3) removes all locally stored
tokens.

---

## 4. OAuth Flow for CLI Applications

### 4.1 Flow options

| Flow | How it works | Best for |
|------|-------------|----------|
| Authorization Code + PKCE | Opens browser, redirect to localhost | Desktop/CLI with browser access |
| Device Code | Display code, user visits URL on any device | Headless, SSH, or no-browser environments |

Both Google and Microsoft support both flows. The **Authorization Code + PKCE**
flow is preferred when a browser is available because it completes in a single
action. The **Device Code** flow is the fallback for environments without a
local browser.

### 4.2 Google: InstalledAppFlow

```python
from google_auth_oauthlib.flow import InstalledAppFlow

flow = InstalledAppFlow.from_client_config(
    client_config,  # dict, not a file path (avoids shipping secrets)
    scopes=["https://www.googleapis.com/auth/calendar.readonly"],
)

# Option A: Open browser, run local server to catch redirect
creds = flow.run_local_server(port=0)

# Option B: Console-based (user copies URL, pastes code back)
creds = flow.run_console()
```

### 4.3 Microsoft: Device Code Flow via MSAL

```python
import msal

app = msal.PublicClientApplication(
    client_id,
    authority="https://login.microsoftonline.com/common",
)

flow = app.initiate_device_flow(scopes=["Calendars.Read", "Mail.Read"])
print(flow["message"])  # "To sign in, visit https://microsoft.com/devicelogin ..."

result = app.acquire_token_by_device_flow(flow)
# result["access_token"] is ready to use
```

---

## 5. Prior Art and Libraries

### 5.1 Provider-specific libraries

| Library | Provider | Key feature | PyPI |
|---------|----------|-------------|------|
| `google-auth` + `google-auth-oauthlib` | Google | Full OAuth flow, credential objects, auto-refresh | `google-auth-oauthlib` |
| `msal` | Microsoft | Device code flow, silent token acquisition, built-in cache | `msal` |

**Can they share a common pattern?** Not really at the library level -- Google
uses `Credentials` objects with explicit `refresh()`, while MSAL uses
`PublicClientApplication` with `acquire_token_silent()`. However, WOS can
create a thin **adapter layer** that presents a uniform interface:

```python
class TokenProvider(Protocol):
    """Common interface for both providers."""
    def get_access_token(self) -> str: ...
    def revoke(self) -> None: ...
    def is_authenticated(self) -> bool: ...
```

Each provider implements this protocol using its native library. The skill
layer only interacts with the protocol, never with provider-specific code.

### 5.2 Generic OAuth libraries

| Library | Notes |
|---------|-------|
| `oauthlib` + `requests-oauthlib` | Generic OAuth 1/2 implementation. Powerful but low-level -- you manage token persistence, refresh, and caching yourself. |
| `authlib` | Higher-level alternative. Supports OAuth 1/2, OIDC, JWS/JWE. Auto-refresh support. Version 1.6.x, Python 3.9+. |

**Recommendation:** Use the provider-specific libraries (`google-auth-oauthlib`
and `msal`). They handle provider-specific quirks (Google's consent screen
behavior, Microsoft's token rotation) that generic libraries miss. The
additional dependency cost is justified by significantly reduced implementation
complexity and better maintenance alignment with provider API changes.

### 5.3 The `keyring` package

| Feature | Status |
|---------|--------|
| macOS Keychain | Supported natively |
| Windows Credential Locker | Supported natively |
| Linux Secret Service (GNOME/KDE) | Supported via D-Bus |
| Headless Linux / CI | No reliable backend |
| Simple API (get/set/delete) | Yes |
| Multiple credentials per service | Yes (via `username` parameter) |
| Nested/structured data | No (string values only; must serialize) |

For storing refresh tokens, `keyring` is well-suited: the values are simple
strings, the API is minimal, and the security is OS-managed.

---

## 6. Security Considerations

### 6.1 Token file permissions (if file-based)

If tokens must be stored on disk (as a fallback or for headless environments):

```python
import os
import stat

def write_token_file(path: str, content: str) -> None:
    """Write token file with owner-only permissions."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, content.encode())
    finally:
        os.close(fd)
```

The file should be created with `0600` permissions from the start (not
created then chmod'd, which leaves a race window). This is the same approach
used by `gcloud`, SSH (`~/.ssh/`), and GPG.

On Windows, use the user's `%APPDATA%` directory which is ACL-protected by
default, or use DPAPI via `keyring`.

### 6.2 Preventing token leakage

**In logs and error messages:**

- Never log access tokens, refresh tokens, or authorization codes
- Redact tokens in error messages: show at most the first 4 characters
- Use `repr()` overrides on credential objects to prevent accidental logging

```python
class TokenData:
    """Token container that redacts itself in string representations."""
    def __init__(self, access_token: str, refresh_token: str):
        self._access_token = access_token
        self._refresh_token = refresh_token

    def __repr__(self) -> str:
        return "TokenData(access_token='****', refresh_token='****')"

    def __str__(self) -> str:
        return self.__repr__()
```

**In URLs and headers:**

- Never pass tokens as URL query parameters (they appear in server logs,
  browser history, and proxy logs). Use `Authorization: Bearer` headers.
- Both Google and Microsoft APIs use the `Authorization` header approach.

**In version control:**

- Add token storage paths to `.gitignore`
- Never embed client secrets in source code. Use a registered "Desktop app"
  OAuth client type, which uses PKCE instead of a client secret.

### 6.3 What NOT to do (common mistakes)

1. **Storing tokens in environment variables persistently** (e.g., in
   `.bashrc`). Environment variables are inherited by child processes and
   may be visible via `/proc` on Linux.
2. **Logging full HTTP responses** during debugging. Token refresh responses
   contain new access tokens.
3. **Using `include_granted_scopes=true`** with Google, which can silently
   accumulate scopes from prior authorizations.
4. **Skipping PKCE** for public clients. Both Google and Microsoft require
   PKCE for native/desktop apps. The `InstalledAppFlow` and MSAL
   `PublicClientApplication` handle this automatically.
5. **Hardcoding client secrets** in source code. For desktop/CLI apps, use
   the "Desktop application" client type which does not require a client
   secret (relies on PKCE instead).
6. **Silent fallback to insecure storage** without warning the user (the
   lesson `gh` learned).
7. **Not persisting rotated refresh tokens** from Microsoft. If you discard
   the new refresh token returned during a refresh, the old one becomes
   invalid and the user must re-authenticate.

---

## 7. Recommended Approach for WOS

### 7.1 Storage strategy: keyring-primary, file-fallback

```
Attempt 1: OS keyring via `keyring` package
  |
  +--> Success: tokens stored in macOS Keychain / Windows Credential Locker
  |
  +--> Failure: warn user explicitly, offer file-based fallback
         |
         +--> User accepts: JSON file at ~/.config/wos/tokens.json
         |    with 0600 permissions, containing encrypted or plain tokens
         |
         +--> User declines: no token stored, must re-auth each session
```

Unlike `gh`'s silent fallback, WOS should **always inform the user** when
falling back to file-based storage.

### 7.2 Token storage layout

```
~/.config/wos/
  tokens.json       # fallback file (0600 perms)
```

Or in keyring:

```
Service: "wos-google"    Username: "user@gmail.com"     Value: {refresh_token JSON}
Service: "wos-microsoft" Username: "user@outlook.com"   Value: {serialized MSAL cache}
```

MSAL has its own cache serialization format. Rather than extracting individual
tokens, store the serialized MSAL cache blob in the keyring (or file).

### 7.3 Provider abstraction

```python
from __future__ import annotations

from typing import Protocol, Optional


class TokenProvider(Protocol):
    """Uniform interface for Google and Microsoft auth."""

    @property
    def provider_name(self) -> str: ...

    def is_authenticated(self) -> bool: ...

    def authenticate(self) -> None:
        """Run interactive OAuth flow (browser or device code)."""
        ...

    def get_access_token(self) -> str:
        """Return a valid access token, refreshing if needed."""
        ...

    def revoke(self) -> None:
        """Revoke tokens and clear local storage."""
        ...

    def get_user_email(self) -> Optional[str]:
        """Return the authenticated user's email, if known."""
        ...
```

Two implementations: `GoogleTokenProvider` and `MicrosoftTokenProvider`, each
using their native library (`google-auth-oauthlib` and `msal` respectively).

### 7.4 Scopes to request

**Google:**
- `https://www.googleapis.com/auth/calendar.readonly`
- `https://www.googleapis.com/auth/gmail.readonly` (or `.metadata` if body
  access is not needed)

**Microsoft:**
- `User.Read`
- `Calendars.Read`
- `Mail.Read`

Validate granted scopes after token acquisition. Refuse and warn if unexpected
scopes are present.

### 7.5 Dependencies to add

```toml
# In pyproject.toml [project.optional-dependencies]
integrations = [
    "google-auth>=2.0",
    "google-auth-oauthlib>=1.0",
    "msal>=1.20",
    "keyring>=24.0",
]
```

These should be **optional dependencies** (`pip install wos[integrations]`)
since the base WOS plugin does not require OAuth. This keeps the core
dependency footprint small.

### 7.6 Summary of key decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Primary storage | OS keyring via `keyring` | Best security for interactive terminal use |
| Fallback storage | JSON file, 0600 perms, explicit user consent | Headless compatibility without silent insecurity |
| OAuth libraries | `google-auth-oauthlib` + `msal` (provider-native) | Handle provider quirks; well-maintained |
| OAuth flow | Auth Code + PKCE (primary), Device Code (fallback) | Browser-based is seamless; device code for SSH |
| Scope strategy | Request minimal read-only; validate on acquisition | Principle of least privilege |
| Token refresh | Transparent via provider libraries | Both libraries handle refresh internally |
| Microsoft token rotation | Persist new refresh token after every refresh | Required by Microsoft's rotation policy |
| Dependency model | Optional extras (`wos[integrations]`) | Keep core plugin lightweight |
| Revocation | Google endpoint + MSAL `remove_account()` + local cleanup | Complete cleanup on disconnect |
| Logging safety | Custom `__repr__` on token objects; never log raw tokens | Prevent accidental leakage |
