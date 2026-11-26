#!/usr/bin/env python3
"""Security guard for the published spec.

The spec at main is read directly by GitBook (refreshed every six hours), by the
"Download OpenAPI spec" link and by the Scalar API client. Whatever lands on main
reaches readers without another review, so this script fails the build when a
change could send a reader's API key somewhere else or let a reader fire a bulk
send from the docs.

Checks:
  1. The only server is https://restapi.netmera.com, with no path or operation overrides.
  2. Authentication is the X-netmera-api-key header, applied globally, and no operation
     overrides or removes it.
  3. Endpoints that delete data in bulk hide the Test it panel (x-hideTryItPanel: true).
     Endpoints that can send to many users either hide it, or open the description with a
     danger hint that starts "**Requests sent from Test it are real.**" and use a default (first) example that
     does not set `sendToAll: true`. Any endpoint whose request body has a `sendToAll` field
     is treated as a bulk send automatically.
  4. No request proxy extension, no active HTML (script, iframe, event handlers,
     javascript: links) and no plain-http links.
  5. No file tracked in the repository contains a credential (API keys, tokens, private
     keys, JWTs), a real-looking email address, a Turkish mobile number other than the
     placeholder 905000000000, or a link to a host outside the allowlist. The repository is
     public, so anything committed is readable by anyone, including in its history.

Usage:
    python3 scripts/guard_spec.py netmera-rest-api.yaml

Exit codes: 0 pass, 1 a check failed, 2 the file could not be read.
"""

import os
import re
import subprocess
import sys

import yaml

SERVER_URL = "https://restapi.netmera.com"
SCHEME_NAME = "REST-API-key"
SCHEME = {"type": "apiKey", "in": "header", "name": "X-netmera-api-key"}
METHODS = ("get", "post", "put", "patch", "delete")

# Endpoints that delete in bulk. Test it stays hidden on these; remove an entry only with a
# reason in the commit message.
MUST_HIDE_TRY_IT = {
    "deleteUsers",             # list of users
    "deleteUsersPermanently",  # list of users, irreversible
    "deleteProfileAttributes", # attribute removed from every user
    "changeSegmentStatus",     # can delete a segment
}

# Endpoints that can send to many users. Test it may stay open only with the warning hint
# and a default example that does not send to everyone.
BULK_SEND = {
    "sendBulkNotification",  # audience or sendToAll push
    "sendNotification",      # transactional, accepts an array of sends
    "updateLiveActivity",    # every device holding the activity
    "sendEmailAndSms",       # target supports sendToAll
    "sendBulkEmail",         # audience or sendToAll email
}
WARNING_MARK = '{% hint style="danger" %}\n**Requests sent from Test it are real.**'


def first_example(spec, content):
    for media in content.values():
        media = resolve(spec, media)
        examples = media.get("examples") or {}
        if examples:
            return resolve(spec, next(iter(examples.values()))).get("value")
        if "example" in media:
            return media["example"]
    return None


def sends_to_all(value):
    if isinstance(value, dict):
        return value.get("sendToAll") is True or any(sends_to_all(v) for v in value.values())
    if isinstance(value, list):
        return any(sends_to_all(v) for v in value)
    return False


FORBIDDEN_TEXT = [
    (r"<\s*script", "a <script> tag"),
    (r"<\s*iframe", "an <iframe> tag"),
    (r"<\s*(object|embed)\b", "an <object>/<embed> tag"),
    (r"\son[a-z]+\s*=\s*[\"']", "an inline event handler"),
    (r"javascript\s*:", "a javascript: link"),
    (r"http://(?!www\.w3\.org/)", "a plain-http link"),
    (r"x-enable-proxy", "the GitBook request proxy extension"),
]


# Repository-wide data checks (check 5).
SECRET_PATTERNS = [
    (r"AKIA[0-9A-Z]{16}", "an AWS access key"),
    (r"AIza[0-9A-Za-z_\-]{35}", "a Google API key"),
    (r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}", "a GitHub token"),
    (r"xox[abprs]-[A-Za-z0-9-]{10,}", "a Slack token"),
    (r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{5,}", "a JWT"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "a private key"),
    (r"[A-Za-z0-9_\-]{11,}:APA91b[A-Za-z0-9_\-]{20,}", "an FCM device token"),
    (r"(?i)(?:x-netmera-api-key|x-nm-app-key|authorization|bearer|api[_-]?key|secret|password)"
     r"[\"']?\s*[:=]\s*[\"']?(?!YOUR_|your_|<|\$|\{)[A-Za-z0-9+/=_\-.]{24,}", "a credential value"),
]
EMAIL_RE = r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"
EMAIL_DOMAINS_ANY = ("example.com", "example.org", "example.net", "users.noreply.github.com")
EMAIL_NETMERA_LOCAL = {"example", "example1", "example2", "example3", "info"}
PHONE_RE = r"(?<![\d.])(?:\+?90)?5\d{9}(?!\d)"
PHONE_ALLOWED = {"905000000000", "+905000000000", "5000000000"}
HOST_ALLOWED = {
    "restapi.netmera.com", "user.netmera.com", "netmera.com", "www.netmera.com",
    "www.w3.org", "raw.githubusercontent.com", "github.com", "www.google.com", "www.youtube.com",
}
HOST_SUFFIX_ALLOWED = (".example.com", ".example.org", ".example.net")
HOST_EXACT_ALLOWED_SUFFIXLESS = {"example.com", "example.org", "example.net"}


def tracked_files():
    try:
        out = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True).stdout
        return [f for f in out.splitlines() if f]
    except (OSError, subprocess.CalledProcessError):
        return []


def scan_repository(files):
    errors = []
    for path in files:
        if not os.path.isfile(path):
            continue
        try:
            text = open(path, encoding="utf-8").read()
        except (UnicodeDecodeError, OSError):
            continue
        def where(pos):
            return f"{path}:{text.count(chr(10), 0, pos) + 1}"
        for pattern, what in SECRET_PATTERNS:
            for m in re.finditer(pattern, text):
                errors.append(f"{where(m.start())}: looks like {what}; never commit credentials")
        for m in re.finditer(EMAIL_RE, text):
            local, _, domain = m.group(0).rpartition("@")
            domain = domain.lower()
            if domain in EMAIL_DOMAINS_ANY or any(domain.endswith("." + d) for d in EMAIL_DOMAINS_ANY):
                continue
            if domain == "netmera.com" and local.lower() in EMAIL_NETMERA_LOCAL:
                continue
            errors.append(f"{where(m.start())}: email address {m.group(0)} is not a placeholder; "
                          "use an example.com address")
        for m in re.finditer(PHONE_RE, text):
            if m.group(0) not in PHONE_ALLOWED:
                errors.append(f"{where(m.start())}: phone number {m.group(0)} looks real; use 905000000000")
        for m in re.finditer(r"https?://([A-Za-z0-9.\-]+)", text):
            host = m.group(1).lower().rstrip(".")
            if host in HOST_ALLOWED or host in HOST_EXACT_ALLOWED_SUFFIXLESS or host.endswith(HOST_SUFFIX_ALLOWED):
                continue
            errors.append(f"{where(m.start())}: link to {host} is not on the host allowlist in guard_spec.py")
    return errors


def resolve(spec, node, seen=None):
    seen = seen or set()
    while isinstance(node, dict) and "$ref" in node:
        ref = node["$ref"]
        if ref in seen:
            return {}
        seen.add(ref)
        node = spec
        for part in ref.lstrip("#/").split("/"):
            node = node.get(part, {})
    return node


def has_send_to_all(spec, node, seen=None):
    seen = seen if seen is not None else set()
    if isinstance(node, dict):
        if "$ref" in node:
            if node["$ref"] in seen:
                return False
            seen.add(node["$ref"])
            return has_send_to_all(spec, resolve(spec, node), seen)
        if "sendToAll" in (node.get("properties") or {}):
            return True
        return any(has_send_to_all(spec, v, seen) for v in node.values())
    if isinstance(node, list):
        return any(has_send_to_all(spec, v, seen) for v in node)
    return False


def main():
    if len(sys.argv) != 2:
        print("::error::usage: guard_spec.py SPEC.yaml")
        sys.exit(2)
    try:
        text = open(sys.argv[1], encoding="utf-8").read()
        spec = yaml.safe_load(text)
    except (OSError, yaml.YAMLError) as exc:
        print(f"::error::cannot read {sys.argv[1]}: {exc}")
        sys.exit(2)

    errors = []

    servers = spec.get("servers") or []
    if [s.get("url") for s in servers] != [SERVER_URL]:
        errors.append(f"servers must be exactly [{SERVER_URL}], found {[s.get('url') for s in servers]}")

    schemes = (spec.get("components") or {}).get("securitySchemes") or {}
    if list(schemes) != [SCHEME_NAME] or any(schemes[SCHEME_NAME].get(k) != v for k, v in SCHEME.items()):
        errors.append(f"securitySchemes must contain only {SCHEME_NAME}: {SCHEME}")
    if spec.get("security") != [{SCHEME_NAME: []}]:
        errors.append(f"global security must be [{{{SCHEME_NAME}: []}}]")

    seen_ops = set()
    for path, item in (spec.get("paths") or {}).items():
        if "servers" in item:
            errors.append(f"{path} overrides servers")
        for method, op in item.items():
            if method not in METHODS:
                continue
            op_id = op.get("operationId") or f"{method.upper()} {path}"
            seen_ops.add(op_id)
            if "servers" in op:
                errors.append(f"{op_id} overrides servers")
            if "security" in op:
                errors.append(f"{op_id} overrides security; authentication must stay global")
            body = (op.get("requestBody") or {}).get("content") or {}
            hidden = op.get("x-hideTryItPanel") is True
            if op_id in MUST_HIDE_TRY_IT and not hidden:
                errors.append(f"{op_id} deletes in bulk; set x-hideTryItPanel: true")
            elif (op_id in BULK_SEND or has_send_to_all(spec, body)) and not hidden:
                if WARNING_MARK not in (op.get("description") or ""):
                    errors.append(f"{op_id} can send to many users and shows Test it; add the "
                                  "'Requests sent from Test it are real.' danger hint after the first paragraph "
                                  "or set x-hideTryItPanel: true")
                if sends_to_all(first_example(spec, body)):
                    errors.append(f"{op_id} shows Test it with a default example that sets sendToAll: true; "
                                  "make the first example target a test tag")

    for op_id in sorted((MUST_HIDE_TRY_IT | BULK_SEND) - seen_ops):
        errors.append(f"{op_id} is listed in the guard but no longer exists; update the list")

    for pattern, what in FORBIDDEN_TEXT:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            line = text.count("\n", 0, m.start()) + 1
            errors.append(f"line {line}: {what} is not allowed in the spec")

    errors.extend(scan_repository(tracked_files()))

    for e in errors:
        print(f"::error::{e}")
    if errors:
        print(f"\nsecurity guard: {len(errors)} problem(s)")
        sys.exit(1)
    print("security guard: servers, authentication, Test it settings and repository data are safe")


if __name__ == "__main__":
    main()
