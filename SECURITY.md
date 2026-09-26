# Security policy

## Supported scope

Security fixes target the current default-branch code. The project is a single-user service bound to `127.0.0.1`, with local files and browser storage. It is not designed for shared public hosting, untrusted network users, exam proctoring, or operating-system lockdown. Do not expose the service through port forwarding or a public proxy without designing and reviewing authentication and authorization first.

## Reporting a vulnerability

If the repository's **Security → Report a vulnerability** feature is enabled, use it for a private report. This document does not promise that the host has enabled that feature. Otherwise, open a minimal issue asking the repository maintainer for a private reporting channel; omit exploit details, private URLs, credentials, materials, answers, and recordings until a private channel is available. Do not invent a contact address or send personal data to an unverified address.

Include the affected revision, operating system/browser, a minimal synthetic reproduction, the expected boundary, and observed impact. Do not attach another user's data or test against other people's deployments. No response-time guarantee or bug-bounty program is offered.

## Sensitive local data

`storage/` includes answers and voice recordings; browser IndexedDB may contain pending uploads. `data/`, `generated/`, and `scripts/verified_*.json` may contain copyrighted material and private source evidence. Keep these files out of Git and public issue attachments. A JSON session export can contain answers and personal text, even when audio bytes are downloaded separately.

The selected `examples/ets-practice-test-1/` package is the explicit resource exception, documented in its [source notice](examples/ets-practice-test-1/NOTICE.md). It contains reference keys and sources for local study, but no personal responses or recordings. Renaming its public files does not make the rest of `data/` or `generated/` safe to publish.

Back up the complete storage safely before upgrades. Wait for recording uploads to finish before clearing browser data. If a credential was accidentally published, revoke it through its provider; deleting the file from a later commit does not revoke the credential or remove history.

## Application boundaries to preserve

The server must reject stale answers, unauthorized asset paths, and strict-session bypasses. Reference answers, transcripts, review evidence, historical scores, and another session's media must not leak into an active strict exam. Imported resources require bounded local paths and validated structure; code and HTML supplied as content must not be executed. Tests using synthetic fixtures should exercise these boundaries without modifying real user records.

The historical [strict-mode review](docs/STRICT_MODE_SECURITY_REVIEW.md) describes a specific revision's findings and fixes; it is not a certification of the current deployment.
