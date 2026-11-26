"""Add endpoint cards to every tag description. Usage: python3 scripts/tag_cards.py netmera-rest-api.yaml"""
import re
import sys

import yaml

p = sys.argv[1]
text = open(p, encoding="utf-8").read()
spec = yaml.safe_load(text)
BASE = "https://user.netmera.com/netmera-developer-guide/api-documentation/api-reference/"


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline(s):
    s = esc(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    return s


def first_sentence(desc):
    para = desc.strip().split("\n\n")[0].replace("\n", " ")
    m = re.match(r"(.+?\.)(\s|$)", para)
    return (m.group(1) if m else para).strip()


tags = {t["name"]: t for t in spec["tags"]}
tag_path = {}
for t in spec["tags"]:
    parent = t.get("x-parent")
    tag_path[t["name"]] = (slug(tags[parent]["x-page-title"]) + "/" if parent else "") + slug(t["x-page-title"])

ops = {}
for path, item in spec["paths"].items():
    for method, op in item.items():
        if method in ("get", "post"):
            ops.setdefault(op["tags"][0], []).append((method.upper(), op))

# Goal-oriented card text for the two messaging groups.
GOALS = {
    "sendBulkNotification": "Send one message to an audience: tags, segments, profile attributes, a location or everyone.",
    "createNotificationDefinition": "Create a reusable transactional message once; use its key for every personal send.",
    "sendNotification": "Send a personal message, such as an OTP or an order update, to one or more users.",
    "updateLiveActivity": "Start, update or end an iOS Live Activity for a group.",
    "sendEmailAndSms": "Send an email or an SMS to one user, with the content in the request or from a template.",
    "sendEmailWithAttachment": "Send a panel email to one user with files attached.",
    "sendBulkEmail": "Send a panel email template to an audience, filling its placeholders at send time.",
}

HEAD = ('<table data-view="cards"><thead><tr><th></th><th></th>'
        '<th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody>')


def card(title, body, url):
    return (f'<tr><td><strong>{esc(title)}</strong></td><td>{body}</td>'
            f'<td><a href="{url}">{esc(title)}</a></td></tr>')


def lead(desc):
    """Keep the group's first paragraph only (drop older goal bullet lists)."""
    return desc.strip().split("\n\n")[0].strip()


new_desc = {}
for t in spec["tags"]:
    name = t["name"]
    rows = []
    children = [c for c in spec["tags"] if c.get("x-parent") == name]
    for c in children:
        rows.append(card(c["x-page-title"], inline(lead(c["description"])), BASE + tag_path[c["name"]]))
    for method, op in ops.get(name, []):
        body = f"<code>{method}</code> " + inline(GOALS.get(op["operationId"]) or first_sentence(op["description"]))
        rows.append(card(op["summary"], body, BASE + tag_path[name] + "/" + slug(op["summary"])))
    new_desc[name] = lead(t["description"]) + "\n\n" + HEAD + "".join(rows) + "</tbody></table>\n"

# Rewrite the tags block in place, keeping its other keys and order.
head, rest = text.split("\ntags:\n", 1)
tags_block, after = rest.split("\npaths:\n", 1)
out = []
for name, title, icon, parent in [(t["name"], t["x-page-title"], t["x-page-icon"], t.get("x-parent")) for t in spec["tags"]]:
    out.append(f"  - name: {name}")
    if parent:
        out.append(f"    x-parent: {parent}")
    out.append(f"    x-page-title: {title}")
    out.append(f"    x-page-icon: {icon}")
    out.append("    description: |")
    out += ["      " + line if line else "" for line in new_desc[name].rstrip("\n").split("\n")]
text = head + "\ntags:\n" + "\n".join(out) + "\n\npaths:\n" + after
open(p, "w", encoding="utf-8").write(text)
check = yaml.safe_load(text)
assert [t["name"] for t in check["tags"]] == [t["name"] for t in spec["tags"]]
assert {k: v for k, v in check.items() if k != "tags"} == {k: v for k, v in spec.items() if k != "tags"}
print("cards per tag:", {t["name"]: t["description"].count("<tr><td>") for t in check["tags"]})
