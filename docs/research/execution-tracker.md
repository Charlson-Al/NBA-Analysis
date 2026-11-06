# V2.2 research execution tracker

A small offline CLI and repository-scoped skill support the existing five stages
and final lock. They do not implement basketball judgment or a new methodology.
Read `.agents/skills/nba-v22-research/SKILL.md` and the complete November 3 source.

## Private storage and installation

Use the existing Python 3.12 environment and pinned `requirements.txt`:

```sh
python -m venv .venv
# Activate the virtual environment for your operating system.
python -m pip install -r requirements.txt
python -m pip check
export NBA_PRIVATE_DATA_ROOT='<absolute-owner-only-directory-outside-every-git-checkout>'
export PYTHONPATH=src
```

There is no storage default. The tracker reuses ingestion's strict JSON decoding,
Draft 2020-12 validation, mandatory date/time checkers, root ownership/permission
and symlink safeguards, canonical encoding and SHA-256. It does not relax the
synthetic-only statistical ingestion pipeline. It records operator-supplied
private research metadata; it does not fetch NBA or proprietary source data.
Source access, retention and intended use must be authorized separately.

## Practical workflow

```sh
python -m tracker init SESSION_ID --record PRIVATE_SESSION_INPUT_JSON
python -m tracker seed-coverage SESSION_ID
python -m tracker append SESSION_ID --record PRIVATE_EVENT_INPUT_JSON
python -m tracker check SESSION_ID
python -m tracker report SESSION_ID
python -m tracker report SESSION_ID --at ORIGINAL_DECISION_EVENT_ID
```

Global `--root` can replace the environment variable and precedes the command.
Keep input JSON outside Git as well. `report` writes a uniquely named, owner-read
Markdown file in the private root's `tracker-reports` directory. CLI output
contains event IDs/counts, never research payloads or private paths. Reports are
private: source references and analytical notes may themselves be sensitive.

Exit codes: 0 = operation/check completed without findings (or coverage seeded);
2 = record retained/report generated with compliance findings; 1 = invalid input,
unsafe storage or journal/schema integrity failure. Exit 2 is not a failed write,
a basketball Pass, or automatic exclusion. `init` and `append` verify intake and
record consistency immediately and retain conflicting declarations for audit.

Each command appends at most one analytical input record. Seed coverage only
creates unreviewed bookkeeping rows, is idempotent, and assigns no scores,
projections, grades, ranks, directions or selection decisions. A partially
interrupted seed can be rerun. It never marks markets reviewed automatically.

A source edit does not alter an earlier model input. Append revised inputs and
explicitly reassess affected candidates. Do not silently reuse an assessment
whose pinned dependencies changed. A shared rotation issue is recorded once and
linked in both directions to affected candidates. A carried risk is allowed by
V2.2; its existence is not an automatic eligibility violation.

## Record envelope and types

All input records have:

```json
{"kind":"evidence","entity_id":"evidence-example","basis":[],"data":{}}
```

The empty data above is explanatory, not valid evidence. See the strict schema
`manifests/schemas/tracker.schema.json` and fully invented example
`tests/fixtures/synthetic/tracker-inputs.json` for required fields.

`entity_id` is a stable safe identifier. Reuse it to append a revision of the same
kind; earlier bytes remain intact. `basis` lists the exact prior event IDs the
assessment actually used, not every previous journal event. Pin direct inputs,
including source/model/calculation/market/evidence/shared-risk versions. Avoid
circular conceptual dependencies: a rotation uncertainty should depend on its
source evidence, not on the candidate assessment that will consume it.

The session declaration is immutable. Start a new linked-by-notes research
session/checkpoint if its research scope/time or applicable approvals change.
This keeps intraday and historical applicability explicit rather than silently
changing which rules governed earlier records.

| Kind | Required content |
|---|---|
| session | Research date/checkpoint timestamp, prospective/retrospective mode, actual rules-used checksum, approval/refinement references, credible roster and inclusion rationale |
| source | Reference, collection/publication times, statistical cutoff, sample, units, denominator, filters, optional private artifact digest and limitations |
| evidence | Claim, observed/forecast/derived/inference type, verified/incomplete/unavailable/conflicting status, sources, review time and exact verification scope |
| coverage | Player-market, Higher/Lower review, market search status, independent opportunities, advancement/investigation reasons and disposition |
| model | Original DC/DARKO statistic, minutes, per-game/per-minute basis, units, source and accessible uncertainty |
| calculation | Original model IDs, normalized result, optional display value, normalized component IDs for combined markets |
| market | Exact threshold, provider, period, tier, observed time, availability, source, payout and settlement |
| uncertainty | Shared issue, affected candidates, evidence, open/resolved/carried/disqualifying status and rationale |
| candidate | Analyst direction, original grade/rank when actually recorded, four nullable scores with distinct evidence, model/market/calculation links, opportunities, outlook and risks |
| comparison | Distinct candidate IDs; availability, models, rubric, opportunities, minutes/risks, value, user constraints, coverage, outcome and rationale |
| requirement | Existing catalog code, slate/candidate scope, met/partial/not_met/not_applicable, evidence, review time and rationale |
| decision | Research candidate/finalized selection/Pass/explicitly confirmed wager, exact candidate versions, decision time, placement evidence and historical reference |

Null means unknown, never zero. Decision time may be null for incomplete history;
recovery time must not replace it. Source timestamps, cutoffs, analytical review
and decision time have separate meanings. A source refresh time is not a market
observation time. Keep dated source changes as new records.

The journal adds a UUID event ID, actual append timestamp, sequence and previous
record hash. It creates read-only canonical JSON files exclusively and uses an
exclusive writer lock. Decisions pin versions; `--at` renders the original event
prefix even after later reassessments. Later revisions never rewrite the older
forecast, grade or decision. Preserve any literal original source artifacts
separately in authorized private storage: typed model numbers and their source
references do not prove the original payload was retained.

## Authority and compliance

The validator pins the November 3 source bytes, the existing approval decision
record and the new record of already-approved clarifications. It checks recorded
approval references and effective timestamps. This proves consistency with the
reviewed references, not external authentication of a conversation or a legal
license. Unknown intraday applicability is reported rather than assumed.
The source methodology, historical files and original framework manifest are
not modified.

The catalog maps §§1A–5I, all 17 §III lock items, archive/postgame requirements,
source discipline, historical safeguards, the five-slate protocol and standard
output back to V2.2. Completion is an analyst declaration. Reports show the
status, evidence IDs (linked to the evidence register), mechanical reasons a
completion claim is unsupported, and unresolved concerns.

- **Hard violation:** Recorded framework/approval conflict, ineligible ranked or
  selected market, incompatible normalization, arithmetic mismatch, or a grade
  outside an existing explicit eligibility limit. Original declarations remain.
- **Incomplete evidence:** Missing inputs, unsupported verified claims, open
  rubric fields, incomplete comparisons/lock checks or unpinned assessments.
- **Warning:** Stale dependencies, carried/shared risks, timing discrepancies,
  or placement without a separately recorded analytical selection.
- **Analyst judgment:** Evidence quality/independence, materiality, minutes
  plausibility, substantive comparison strength, final scores, grades and ranks.

No new grade restriction is introduced. The validator checks the existing §5D
bands against operator-recorded scores/grades. An A-range eligibility check does
not certify all seven A-range conditions. Those remain explicit checklist and
analyst judgments. Missing factors remain unscored. Model agreement never
supplies opportunity evidence. Model disagreement never automatically excludes
an opportunity or causes a software-selected Pass.

Arithmetic checks use the approved per-game/per-minute normalization, once,
with compatible units. Combined markets require normalized component records at
the same DC minutes. A numerical tolerance of 1e-9 is only a computation check,
not an analytical materiality threshold. Store full calculation precision;
`display_value` is separate. Exact-line classification does not round model
values. Integer win/tie/loss counts do not establish provider settlement,
probabilities, payout value or a selection.

## Synthetic quickstart without repetitive JSON editing

After configuring the private root and Python path, the Python API can load the
invented fixture and pin each original dependency version:

```python
from ingestion.store import REPO, decode
from tracker.journal import create, append

records = decode((REPO / 'tests/fixtures/synthetic/tracker-inputs.json').read_bytes())['records']
events = []
for record in records:
    record['basis'] = [event['event_id'] for event in events]
    operation = create if not events else append
    events.append(operation('synthetic-demo', record))
```

Then run `python -m tracker report synthetic-demo`. In real use, pin direct
inputs only. The invented candidate deliberately has incomplete research and
must produce findings. No real evidence belongs in the fixture namespace.

## Validation and read-only Slate 3 acceptance

Run `python -m unittest discover -s tests -v`, `python src/audit.py`, and
`python -m pip check`. Synthetic tests cover authority/provenance, intraday
refinement applicability, eight-market bookkeeping, supported opportunities
across model splits, normalization/components, exact ties/direction, existing
grade limits, incomplete evidence/comparisons, stale/shared risks, separate
placement status, append-only history, checkpoint replay, corruption, symlinks,
write failures and private CLI reports.

The November 5 acceptance uses private retrospective metadata annotations from
the frozen pregame transcript and pregame file-change records recovered in the
completed workflow audit. It does not use postgame outcomes. It is not an import
of every row of the 312-row ledger or a byte-for-byte replay of lost raw sources.
Generic missing-input findings can reflect this deliberately limited import;
they must not be represented as proof that every original candidate lacked
opportunity evidence.

Confirmed acceptance findings: conflicting historical framework reference;
Ighodaro's unverified passing opportunities and Green's weak three-point channel;
unresolved shared Phoenix center rotation; incomplete finalist/exclusion
comparison; incomplete personnel, synchronized board/payout and final recheck
lock items. Retrospective candidate annotations retain all six final Pass
statuses, zero finalized selections and unknown exact decision time. Journal
hashes are unchanged by review. Original historical files are not touched.
Private acceptance journals/reports are not committed. Public evidence is this
redacted account of the test and the synthetic automated regressions.

## Limits and publication boundary

This is a trusted single-owner local-filesystem tool, not WORM, encrypted,
crash-atomic or independently anchored storage. File permissions and hash chains
do not prevent a coordinated owner rewrite or undetectable removal of the
journal tail without an external trusted checkpoint. Interrupted writes can
leave an incomplete event or lock requiring private inspection; do not blindly
remove a live writer lock. Successful ordinary write failures are cleaned up.
The existing managed workspace is not evidence of durable storage/backups.

Schemas validate structure, not source authenticity, licensing or basketball
truth. Free-text “substantive” comparisons require human review. The report is a
mechanical consistency view of recorded latest inputs; use `--at` for historical
checkpoints. Missing explicit dependency links limit stale-change detection.

Only code, schemas, guidance, approved-rule references and invented fixtures
belong in public Git. The public guard narrowly permits this skill file and
rejects tracker-report/research-record directories regardless of case. It is
still a local, bypassable secondary defense, not a secret or proprietary-content
classifier. No new scraping, databases, dashboards, schedules, specialized
subagents or automated final decisions are implemented.

Validation for this draft: 74 automated tests passed with zero failures or skips,
including all existing ingestion/audit tests. `pip check` passed. The V1.2 audit
retained 1,290/1,290 numeric matches, zero errors/mismatches and the 150 existing
evidence warnings. Game-day readiness remains false. The private Slate 3
acceptance recovered the expected pregame gaps and left its 18 annotated journal
events unchanged. No independent CI result is claimed.
