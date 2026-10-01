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

**The live Developer Guide is authoritative.** Request fields, parameter descriptions,
payload examples and response samples come from the guide. Behaviour observed against
the live API is not added unless the guide documents it; see "The live Developer Guide is
the source" below.

**Nothing is invented.** No enum asserts a list is complete unless the guide says
so. No response schema is written for an endpoint whose response has not been seen.
No field is marked required unless something says it is.

**Operations document success responses only.** Error responses are not listed on
operations. The Netmera error code table lives once, in `info.description`.

**`x-netmera-verified: <date>`** marks a response confirmed against the live API.
It is invisible to readers and exists so a regeneration from the guide cannot
silently replace confirmed behaviour with a guess. `scripts/check_verified.py`
fails the build if a marker disappears.

## The live Developer Guide is the source

The spec carries only what the live Developer Guide documents. Anything else is left out,
even when it was observed against the API, so the reference never says more than the
guide. The one exception is the "Returns no response body" wording on write operations,
which was confirmed against the live API and kept on purpose.

These were removed for that reason and must not be added back unless the guide adds them:

- The `sendPushApproval` and `deleteProfileAttributeValue` operations.
- The "Response bodies" section, the RFC 9457 error shape and error code 2004.
- The `{}` body of `sendNotification`, the `notificationKey` body of `sendEmailAndSms`,
  the `smsIysMessageType` / `smsIysRecipientType` requirement notes, and the note on
  characters allowed in category names.
- `required` on `sendEmailWithAttachment`, `addEmail`, `addMsisdn` and the `getPushStats`
  response.
- Descriptions inferred from examples (`schedule.localTimezone`, `speed`, `languages`,
  `_nm_badge_count`, an array `tag` on `tagUsers` / `untagUsers`, WhatsApp addressing),
  the plain-string `message` and extra root fields on bulk and definition requests, and
  the `offset` parameter of `getPushResult`.
- All error responses on operations.

The guide's carousel and slider examples put message fields at the root level, so Redocly
reports them as not matching the schema. The examples are kept verbatim from the guide.

The guide marks `target` as required for bulk notifications and `title`, `message` and
`platforms` for notification definitions, but its own carousel and slider examples omit
them, so these fields are not marked required at the top level.

## Still unverified

Responses for `sendBulkNotification`, `sendEmailWithAttachment`, `sendBulkEmail` and
`deleteProfileAttributes` have not been captured. The Developer Guide shows the bulk response only as `NotificationKey: 1000`, so
its body is left undocumented.
They carry no response schema rather than a guessed one.

## Open questions for Netmera engineering

These cannot be answered from the guide or the spec and are left undocumented rather than
guessed: rate limits, request size and timeout limits, field length limits, what the REST
API key is authorized to do, which endpoints return 404, differences between test and
production environments, side effects of removing a channel on segment membership and
message category permissions, and the responses of the five operations listed above plus
`registerUsers`, `deleteUsers`, `addTesters` and `addPromotionCodes`.
