# Small V2.2 research assistant

This implementation is one editable private JSON note, deterministic calculations
and structural checks, and exclusive pregame snapshots. It replaces the PR's
journal, UUID dependencies, per-market review flags and per-requirement forms.
The governing November 3 source and methodology are unchanged. Use the repository
skill `.agents/skills/nba-v22-research/SKILL.md` and complete original framework.

## Start and run

Use Python 3.12 with the existing pinned `requirements.txt`. No new dependencies:

```sh
python -m venv .venv
# Activate the environment for your operating system.
python -m pip install -r requirements.txt
export PYTHONPATH=src
export NBA_PRIVATE_DATA_ROOT='<absolute-owner-only-directory-outside-every-git-checkout>'
python -m tracker new slate-note
# Or create an invented working example:
python -m tracker example synthetic-demo
python -m tracker check synthetic-demo.json
python -m tracker report synthetic-demo.json
python -m tracker freeze synthetic-demo.json before-tip
python -m tracker snapshot synthetic-demo before-tip
```

Global `--root` before the command can replace the environment variable. `new`
creates a blank owner-only note, expected authority references and current dated
refinement list; it assigns no scores, grades, ranks or selections. `example`
copies only the invented repository fixture. Names are relative to the private
root. Edit this one note directly or ask Codex to organize/transcribe authorized
supplied inputs. No provider fetching/integration is included.

`check` prints counts only: exit 0 means no detected structural omissions, 2 means
findings, 1 means invalid schema/private storage or integrity failure. Exit 0 is
not analytical verification. Explicit `report`/`snapshot` commands print private
research Markdown; keep output private, including redirected files and terminal
logs. They do not publish or write source data into the repository.

## The note follows a research session

- **Shared matchup:** three notes per game (environment, personnel, rotation),
  linked to the same source records. Explain credible roster coverage once.
- **Original inputs:** projection rows have provider, player, original minutes,
  per-game/per-minute basis, supplied values and source label. One DC row holds
  all available markets; the checker derives missing eight-market coverage.
  DARKO combined normalization uses individual components first. Missing standard
  lines affect market evaluation, never completion of model screening.
- **Source:** a short label, reference, observed/reviewed times, cutoff, sample,
  units/denominator, declared kind/subject/channel, status and exact scope. Unknown
  times/context stay null. No status means “verified basketball truth.” Optional
  `file` is a relative private artifact path with expected SHA-256; changed bytes
  are flagged, not silently substituted.
- **Candidate:** four existing analyst scores/rationales with source labels,
  original exact line, direction, outlook/failure, grade/rank when recorded,
  research disposition and review time. Add disagreement or sensitivity notes
  only where material. No normalized result is editable: one canonical arithmetic
  result drives both report and eligibility checks.
- **Shared risks:** record affected players once; the checker applies them to
  their candidates. Carried risks are allowed, not a new automatic grade cap.
- **Comparison:** name the analyst-chosen boundary candidate/alternative and one
  substantive rationale. Their model, threshold and factor records supply the
  context; do not repeat eight comparison forms. Human judgment still determines
  whether the exclusion is strongest and why the boundary is defensible.
- **Final review:** one time/source/rationale record for actual personnel and
  market rechecks; one explicit decision and separate placement status. There
  are no “met” or blanket “N/A” switches to bypass missing records.

The strict storage schema is `manifests/schemas/tracker.schema.json`; the working
example is `tests/fixtures/synthetic/research-note.json`. Ordinary JSON editing
is the whole input interface; this is intentionally not a management platform.

## What the report establishes

Five stage summaries, original model comparisons, shared risks, candidate
assessments, comparison rationale and all 17 §III lock items are generated.
States are **missing**, **conflicting**, **recorded**, or **analyst review required**.
“Recorded” means present, not scientifically or analytically verified. There is
no supported-completion boolean and never a software-certified completed lock.
An incomplete finalized declaration is preserved but labeled an unsupported
claim. A structurally populated note still requires substantive analyst review.

Authority checks pin the November 3 source/manifest, existing approval record and
recorded dated refinements. Applicability is inspected at actual research,
assessment, lock and decision checkpoints. A later approval is not backdated.
Evidence observed/reviewed after the decision is retrospective, not pregame
support. The final recheck must link within-session observations of personnel
and markets before the decision; this is a checkpoint check, not a universal
age/expiry rule. Unknown timestamps do not establish freshness.

Known mismatched subject/channel evidence and forecast-only opportunity support
are exposed. False claims with convincing fabricated labels cannot be detected
as truth by software; the report never authenticates them. The original rubric
and §5D eligibility limits are checked only against analyst-entered values, never
assigned automatically. All other A-range conditions remain human judgments.
Source definitions, sample quality, scheme, ownership, materiality, strongest
lane/alternative, payout value and confidence always require basketball judgment.

The final consistency corrections preserve contradictory declarations rather than
rewrite them: Research/Pass cannot contain finalized selections, selected
candidates cannot be excluded/Pass or lack a grade, and duplicate selections are
reported without deduplication. Candidate `research` disposition is the working
assessment; membership in a slate `finalized_selection` decision supplies final
analytical selection status. Placement remains separate.

Market availability and final market rechecks require a recorded, observed,
pregame market source for the candidate, with observation/review times before
the relevant checkpoint. The final observation must also be within the research
session and reviewed by final review. Forecasts and other references can retain
exact-line diagnostic calculations but cannot establish an available market.
No universal line-expiry threshold is introduced.

Before DARKO normalization, source `unit` and `denominator` are checked against
the input basis. Common per-game/per-minute spellings are recognized; conflicting
basis declarations and possession/play rates prevent the calculation. Missing or
unrecognized source bases require analyst review and leave comparison unresolved.
There is no inferred rate conversion or change to original model values. This
small dimensional check is not a comprehensive parser of provider definitions.

## Freeze and later reassessment

`freeze` never finalizes a selection. It saves an exclusive owner-read snapshot:
exact original note bytes, original report/findings, governing source and approval
references, and optional attached private source bytes. Raw source capture is
optional because access/retention rights vary; without it, only the supplied
original typed inputs are preserved, not proof of a provider payload. Missing or
changed declared attachments prevent a misleading preservation claim.

The manifest contains sizes/digests and the checker fingerprint. Existing labels
cannot be overwritten. Ordinary reports include frozen finding summaries, so a
later grade or forecast change cannot hide an original eligibility violation.
`snapshot` verifies and prints the stored original report without recomputing
history using current inputs/code. Do not delete frozen records to improve history.

Keep `postgame` separate; it does not enter pregame checking. Sources marked
postgame cannot support pregame assessments. Do not freeze a mixed postgame note;
use the existing pregame snapshot for later review. Historical-audit mode labels
recovered notes as retrospective, not contemporaneously collected evidence.
The prior experimental event journals are left untouched outside Git; no automatic
conversion or silent historical migration is performed.

## Manual fields and duplication

`entry_metrics(note)` exposes the count rather than claiming zero manual work.
A fully assessed candidate has 14 judgment slots: four scores, four distinct
rationales, direction, outlook, failure, grade, rank and research disposition.
Unknown/unassigned values remain null; they are not forced just to fill a form.
Source labels, IDs, original model/line values and review times can be transcribed
by Codex from supplied evidence; the analyst checks them rather than maintaining
UUIDs or calculation results.

There are three shared matchup notes per game; four judgment slots per shared
risk (description, affected players, disposition, rationale); three per boundary
comparison (pair plus rationale); and seven session-level slots (roster scope,
correlation, lock rationale, decision status/selection/reason, placement status).
Conditional disagreement/sensitivity notes add one each. These count information
that must be supplied/reviewed, not necessarily hand-typed or non-null fields.
Each source has eight core metadata fields; numerical statistical evidence adds
four context fields (cutoff, sample, unit, denominator), nullable when unknown.
Categorical personnel/market references do not require invented statistical units.
Unknown relevant metadata is exposed, not guessed. Codex may populate supported metadata from supplied artifacts.

The two-candidate invented example has 45 judgment slots, six unique source
records, one shared matchup record, no duplicated source definitions and no
manual coverage flags, event IDs, or separate requirement declarations. Repeated
source labels are references, not copies of source evidence. This is not a timed
usability benchmark. The redundant 247 requirement declarations from the former
six-candidate design are gone; the actual basketball work remains necessary.

## Validation and limits

Permanent tests named M1–M6 cover the prior material defects: unsupported locks,
irrelevant evidence, checkpoint approvals/timing, input changes, immutable original
findings, exact-line precision and screening/market/lifecycle separation. Other
synthetic tests cover decision contradictions/duplicates, observed market scope
and timing, source-basis compatibility, schema, normalization/components, risk continuity, placement,
private storage, corruption, interrupted writes, postgame separation and CLI use.
Run the complete suite and unchanged V1.2 reconciliation:

```sh
python -m unittest discover -s tests -v
python src/audit.py
python -m pip check
```

Validation after the final three corrections: 79 tests passed, with no skips. The unchanged V1.2
audit reconciled 1,290/1,290 values with zero errors/mismatches and the existing
150 evidence warnings; it remains not game-day-ready. Pinned dependencies install
successfully in the separate Python environment and `pip check` passes.

The frozen November 5 acceptance detects the conflicting framework, unsupported
opportunity claims, unresolved shared rotation, incomplete exact-market
comparison, and missing final-lock review. All six retained Pass decisions, zero
finalized selections, and all 18 original acceptance records remain unchanged.

The frozen November 5 acceptance is a private, read-only reconstruction from
previously recovered pregame transcript/file-change evidence. Its limitations
are explicit: no full 312-row import or lost raw source replay, no new source
fetching, no postgame outcomes. Original grades, Pass dispositions and zero
finalized selections stay unchanged. Private notes/reports/snapshots are not
committed; only synthetic fixtures and the redacted acceptance account belong here.

This is trusted single-owner local storage, not WORM, encrypted storage,
crash-atomic storage or a durability/backups service. SHA-256 detects changes
against recorded digests, not coordinated same-owner rewrites. Snapshots are
read-only against accidents, not an independent integrity trust anchor. Rights
for source acquisition, private retention/use and backups must be established
separately before real-data use. The local publication guard is secondary and
bypassable; manual publication review remains necessary. No live automation,
subagents, database, dashboard, scheduling or provider integrations are added.
