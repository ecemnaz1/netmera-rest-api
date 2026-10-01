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

## Scenario files

GitBook opens an OpenAPI block with the first request example of the operation and
cannot choose another one. Each scenario of `sendBulkNotification`, `sendNotification`
and `createNotificationDefinition` has its own guide page, so `scenarios/` holds one
small spec per request example: the full operation with only that example kept. Each
file is registered in GitBook as its own spec (slug `scn-<operation>-<example>`, in
lowercase) and bound to one page.

The files are derived from `netmera-rest-api.yaml`. Never edit them by hand. After any
change to the main spec, run `python3 scripts/split_scenarios.py` and commit the result;
CI fails when the files are stale. If an example has a `description`, the script places
it at the top of the operation description, because a block does not show example
descriptions.

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
because operations document only their success responses. Neither is a defect to fix.

## Conventions

**The Developer Guide is authoritative for requests; the live API is authoritative
for responses.** Request fields, parameter descriptions and payload examples come
from the guide. Response bodies come from calling the endpoint and recording what
came back.

**Nothing is invented.** No enum asserts a list is complete unless the guide says
so. No response schema is written for an endpoint whose response has not been seen.
No field is marked required unless something says it is.

**Operations document success responses only.** Error responses are not listed on
operations. The full Netmera error code table lives once, in `info.description`, which
GitBook publishes as the Error Responses page. Endpoint-specific failures that were
observed are recorded under *Observed endpoint errors* below so the knowledge is kept
without being published on operation pages.

**`x-netmera-verified: <date>`** marks a response confirmed against the live API.
It is invisible to readers and exists so a regeneration from the guide cannot
silently replace confirmed behaviour with a guess. `scripts/check_verified.py`
fails the build if a marker disappears.

## Known divergences from the Developer Guide

These are defects in the source documentation, recorded here so they are not
"fixed" back into the spec by mistake:

- `smsIysMessageType` is required for SMS sends on `sendEmailAndSms`, but the guide
  documents it as an ordinary optional field.
- Error code 2004 is returned by the API but is absent from the guide's error table.
- Unmatched routes return an RFC 9457 problem detail rather than the Netmera
  `{code, error}` envelope, so two error shapes exist.
- `getCategoryPreferences` is documented in the guide with a JSON body on a `GET`;
  it is modelled here with query parameters.
- The guide marks `target` as required for bulk notifications, but its carousel and slider
  examples omit it. The guide marks `title`, `message` and `platforms` as required for
  notification definitions, but its slider example has no top-level `title` or `platforms`.
  The spec therefore does not mark these fields required at the top level; it keeps what the
  guide says in the operation pages instead.
- `sendEmailAndSms` has no field the guide marks as required, so the request schema has
  no `required` list. `smsIysMessageType` is documented above as conditionally required.

## Observed endpoint errors

These were removed from the operation pages on purpose and are kept here for reference:

| Operation | Failure | Response |
| --- | --- | --- |
| `sendNotification` | A field sent with the wrong type (verified live) | `{"code": 2004, "error": "Field 'notificationKey' should be a text"}` |
| `sendEmailAndSms` | SMS send without `smsIysMessageType` (verified live) | `{"code": 2004, "error": "Please add smsIysMessageType parameter into request!"}` |
| `removeEmail`, `removeMsisdn`, `removeWhatsApp` | `extId` missing or `null`; no user is changed | `text/plain`: `Please provide an external id.` |
| `registerUsers` | Every entry is invalid, or no registration was sent | not captured |
| `targetingCount` | Invalid targeting query | not captured |
| `targetingCountBatch` | `groupBy` missing or contains neither `profile` nor `installation` | not captured |
| `sendPushApproval` | No message with the given `messageId` (error code 5003, from the guide's error table) | not captured |

`scripts/check_verified.py` lists the two verified entries as intentionally retired, so the
guard does not fail on them.

## Still unverified

Responses for `sendBulkNotification`, `sendPushApproval`, `sendEmailWithAttachment`,
`sendBulkEmail`, `deleteProfileAttributes` and `deleteProfileAttributeValue` have not been
captured. The Developer Guide shows the bulk response only as `NotificationKey: 1000`, so
its body is left undocumented.
They carry no response schema rather than a guessed one.

## Open questions for Netmera engineering

These cannot be answered from the guide or the spec and are left undocumented rather than
guessed: rate limits, request size and timeout limits, field length limits, what the REST
API key is authorized to do, which endpoints return 404, differences between test and
production environments, side effects of removing a channel on segment membership and
message category permissions, and the responses of the five operations listed above plus
`registerUsers`, `deleteUsers`, `addTesters` and `addPromotionCodes`.
