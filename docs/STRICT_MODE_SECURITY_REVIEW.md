# Strict-mode API isolation review

English | [简体中文](STRICT_MODE_SECURITY_REVIEW.zh-CN.md)

Review date: 2026-09-01. The review used isolated FastAPI TestClient fixtures and temporary storage, without calling the running 4173 service or changing private sources or user records. The reviewer reported findings; the backend owner implemented fixes. This historical report is not a fresh certification of later code.

## Confirmed findings and retested fixes

| Severity | Before | Isolated reproduction | After |
| --- | --- | --- | --- |
| P1 | History was an answer oracle | While strict remained active, a second single-question practice submitted B/A and completed; session-list correct/total revealed the key even with feedback blocked | Other scores are hidden and parallel practice start/resume is blocked |
| P2 | Another practice bypassed one-time audio | A timed-practice asset URL still returned original audio while strict was active | Other session questions, events, and ordinary media routes share the lock |
| P1 | Necessary academic passage image was filtered | Some paper reading tasks then used a registered `passage` image as their only material, but active projection allowed only `stem` | At that revision, projection and asset authorization both allowed registered passage images |

The passage-image finding predates the later all-structured migration: current active presentation rejects legacy full-question images and uses structured text with necessary visuals. The historical fix must not be treated as a request to re-enable old images.

A score of 0/1 or 1/1 can reveal a key without any `answer` field. Blocking only review/feedback, or only new session creation, is insufficient; pre-created sessions and historical scores also need coverage.

## Other results at the reviewed revision

- Active strict sessions returned 403 for validation, question-bank, and original-library routes.
- Cross-session review, export, review assets, and recording playback used the global strict gate.
- Generated audit/bank/exam files, direct material paths, and storage paths were not static public endpoints.
- Catalog/exam/rules metadata did not include fixture answer, explanation, or transcript markers.
- Active questions used field allowlists; source keys and full reference material were review-only. Source warnings were generalized in active responses.
- Assets remained authorized by current question and playback phase, not merely by asset ID.

## Regression

```sh
.venv/bin/python -m pytest tests/security/test_strict_isolation.py -q
```

Before the fixes, four of five checks failed. After adding pre-created-session question/event coverage, all six passed. Scope included score probing, parallel creation, old audio URLs, old-session questions/events, source/direct paths, and the then-current passage authorization.

This is application API/session isolation, not proctoring or an OS sandbox. It cannot prevent opening owned source files, browsing public sites, or using content saved before practice. It is not ETS certification.

## Historical integrity metadata

The gate also gained exam-level `verificationInputs`: hashes of six private curation files and referenced derived resources, covering 1,370 assets at that revision. Normalized semantic hashes of all eighteen archives' `sections` were unchanged. No questions, keys, timing, or media links were modified. Later manifest/asset counts are recorded separately in [DATA_QA.md](DATA_QA.md).
