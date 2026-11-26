# Security policy

This repository holds the public OpenAPI description of the Netmera REST API. It contains
no code that runs in production, no credentials and no customer data, and it must stay that
way: the repository is public and its whole history is readable by anyone.

## Reporting a vulnerability

Report privately through GitHub: open the **Security** tab of this repository and choose
**Report a vulnerability**. Do not open a public issue or pull request for a security problem.

This covers problems in this repository, such as a credential or personal data in a file or
in the history, or a spec change that would send readers' API keys to another host. Problems
in the Netmera API or Panel themselves can be reported the same way; they are forwarded to the
Netmera team.

## If a credential or personal data was committed

1. Revoke or rotate the credential first (for a REST API key: Netmera Panel > Developers > API).
   Removing it from the repository does not make it safe again.
2. Remove it from the file in a pull request.
3. Ask the repository owner to purge it from the history and to contact GitHub Support to clear
   cached views, because forks and pull request refs keep old commits.

## Safeguards in this repository

- `main` accepts changes only through pull requests that pass CI.
- CI runs `scripts/guard_spec.py`, which fails on credentials, real-looking email addresses or
  phone numbers, links to unknown hosts, a changed server or authentication scheme, and Test it
  settings that would let a reader send to many users or delete in bulk without a warning.
- GitHub secret scanning and push protection are on.

These safeguards protect the documentation only. The API itself is protected on the Netmera
side by API key validation, the per-application IP allowlist and request quotas.
