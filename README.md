# Netmera REST API — OpenAPI specification

`netmera-rest-api.yaml` is the source of truth for the API Reference section of the
Netmera Developer Guide. GitBook reads it from the raw URL of this repository and
regenerates the reference whenever it changes.

## How an update reaches the docs

1. Edit `netmera-rest-api.yaml` on a branch and open a pull request.
2. CI parses the file, lints it with Redocly, and checks that no live-verified
   response was dropped.
3. Merge to `main`. GitBook reads the raw URL on its own schedule and picks the
   change up within a few hours. To publish immediately, open the OpenAPI panel in
   GitBook and click **Check for updates**.

Never upload the file to GitBook by hand. The published spec is bound to this URL,
and a manual upload would be overwritten by the next push.

## Setup

No secrets or repository variables are needed. CI only validates the spec; it does not
talk to GitBook.

GitBook is pointed at the raw URL of this file on `main`:

```
https://raw.githubusercontent.com/ecemnaz1/netmera-rest-api/main/netmera-rest-api.yaml
```

Two things about that URL matter. It must contain `main`, not a commit SHA — a
SHA-pinned URL never refreshes. And the repository must stay public, because GitBook
cannot read a source that sits behind a login.

## What CI checks

| Step | Purpose |
| --- | --- |
| Parse | The file is valid YAML. |
| Redocly lint | The file is a valid OpenAPI document. |
| Guard | No `x-netmera-verified` marker was dropped since the base branch. |

The lint step is expected to report warnings and still pass. `info-license` is expected
because the source documentation states no license. `operation-4xx-response` is expected
because error responses are documented only where the specific failure is known, never
added generically. Neither is a defect to fix.

## Conventions

**The Developer Guide is authoritative for requests; the live API is authoritative
for responses.** Request fields, parameter descriptions and payload examples come
from the guide. Response bodies come from calling the endpoint and recording what
came back.

**Nothing is invented.** No enum asserts a list is complete unless the guide says
so. No response schema is written for an endpoint whose response has not been seen.
No field is marked required unless something says it is.

**Errors are documented where they are known, not generically.** Operations do not
carry a boilerplate set of 400/401/403/500 responses. An error appears on an
operation when that specific failure has been observed or is documented for that
endpoint. The full Netmera error code table lives once, in `info.description`.

**`x-netmera-verified: <date>`** marks a response confirmed against the live API.
It is invisible to readers and exists so a regeneration from the guide cannot
silently replace confirmed behaviour with a guess. `scripts/check_verified.py`
fails the build if a marker disappears.

## Known divergences from the Developer Guide

These are defects in the source documentation, recorded here so they are not
"fixed" back into the spec by mistake:

- `sendNotification` requires `notificationKey` as a **string**, while
  `createNotificationDefinition` returns it as an **integer**. Sending an integer
  fails with error code 2004.
- `smsIysMessageType` is required for SMS sends on `sendEmailAndSms`, but the guide
  documents it as an ordinary optional field.
- Error code 2004 is returned by the API but is absent from the guide's error table.
- Unmatched routes return an RFC 9457 problem detail rather than the Netmera
  `{code, error}` envelope, so two error shapes exist.
- `getCategoryPreferences` is documented in the guide with a JSON body on a `GET`;
  it is modelled here with query parameters.

## Still unverified

Responses for `sendPushApproval`, `sendEmailWithAttachment`, `sendBulkEmail`,
`deleteProfileAttributes` and `deleteProfileAttributeValue` have not been captured.
They carry no response schema rather than a guessed one.
