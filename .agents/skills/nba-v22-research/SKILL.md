---
name: nba-v22-research
description: Research the requested NBA scope under November 3 V2.2, produce justified preliminary scores, grades and rankings, and maintain private evidence and snapshots without automatically finalizing selections or wagers.
---

# NBA V2.2 research assistant

Use for authorized NBA-Analysis research, checklist reviews and historical audits.
Read root AGENTS.md and the complete governing reference:
`docs/framework/source/nba-player-props-v2.2-2026-11-03.txt`.
This skill is navigation, not a replacement methodology or new framework version.

## Research responsibility

The user's November 6 research execution adjustment authorizes Codex to research,
assign evidence-supported preliminary rubric scores and confidence grades, and
rank candidates. This supersedes the earlier operator-only scoring restriction
for future research; it does not change V2.2 or backdate any assessment.
Codex makes the basketball assessment; the deterministic checker validates its
arithmetic, eligibility and record consistency. Neither a populated note nor a
clean check certifies the assessment. Preliminary conclusions remain open to
analyst challenge and never finalize analytical selections or confirm wagers.

## Intake and private note

- Verify the November 3 source/manifest and explicit approval in
  `docs/governance/decisions.md`. Read the existing dated approvals in
  `docs/governance/v22-execution-refinements.md`. Apply them at the actual research
  and decision checkpoints. Preserve conflicting historical references as facts
  about what was used; never silently replace them.
- Follow `docs/research/execution-tracker.md`. Work in one editable private JSON
  note outside Git. Codex maintains it from the research conversation and authorized
  sources, including its explained preliminary judgments. Do not require separate
  analyst JSON entry or repeated transcription. Never invent unknown timestamps,
  cutoffs, source values, roles or unsupported scores.
- Reuse short source labels and one matchup record per game. Shared risks list
  affected players once. No event IDs, manual dependency graph or requirement
  forms. Retain original DC/DARKO inputs and any authorized raw local artifacts.
- Do not scrape sources, use excluded providers, introduce integrations, agents,
  scheduling, dashboards or databases, or place wagers. Source access/storage/use
  rights remain separate from a working URL or a valid checklist.

## Normal five-stage session

Establish the requested game/date scope first; a one-game request remains one
game. Screen the complete requested scope before deep-diving likely candidates.
Reuse still-current evidence across players; revisit affected conclusions when
material facts change, without restarting unrelated research.

### Execution order and efficiency

- Load and verify the governing rules once at session intake. Reuse that context;
  reassess applicable approvals when checkpoints or instructions change.
- Collect shared game/personnel data, original models, opportunity tracking and
  market observations before repeated candidate reasoning. Batch supported reads
  and fetch independent providers concurrently. Reuse already available authorized
  observations with their original times, cutoffs and scope; never relabel them fresh.
- Mark a failed/inaccessible source unavailable with its reason. Do not repeatedly
  search or retry it without a material access change or explicit update request.
  Expose a critical gap; do not silently substitute weaker evidence.
- Assess each team's environment once. Screen broadly, then focus validation where
  it could change inclusion, grade or rank. Reuse a player's opportunity evidence
  across component/combined markets without awarding duplicate credit.
- Batch deterministic calculations. Keep working research together, then generate
  the private note and concise board once, with one compliance pass at the
  preliminary-board boundary. Recheck only affected findings after material changes.
  Do not repeatedly rewrite notes, render transcripts, or freeze working drafts.
- When measuring performance, record source/tool calls, failures, duplicate reads,
  stage elapsed times and input/scope identity in a private one-off experiment.
  Separate tool/provider time from agent orchestration/reasoning and user waits;
  label unmeasured time unknown. Cached replay is not completed research. Claim
  end-to-end improvement only for comparable completed runs with equivalent scope.

1. **Environment/personnel (§§1A–1E).** Independently evaluate both teams: pace,
   possessions, efficiency/Four Factors, shot/opportunity channels, resistance,
   personnel, recent rotations, closing roles and material scheduling/scripts.
   Distinguish tendencies from vulnerabilities. Preserve definitions, dates,
   samples, units and denominators. Record credible rotation scope once.
2. **Screen/models (§§2A–2F).** Preserve supplied original DC forecasts/minutes
   and accessible uncertainty. Screen credible players across PTS, REB, AST, 3PM,
   PR, PA, RA, PRA in both directions. Derive coverage from provided projection
   inputs, not from availability of selectable markets. Preserve original DARKO
   counts/rates/minutes; DPM is not a box-score rate. Normalize compatible
   components once to DC minutes. Compare the same exact threshold. Keep both
   model signals and independently supported opportunities in research; investigate
   disagreement without averaging or changing either official forecast.
3. **Independent validation (§§3A–3C).** Codex evaluates and assigns justified
   preliminary 0–2 scores with distinct basketball-specific rationales and source
   links for role, opportunities, matchup and sustainability. Independently
   verify player-specific chances, volume, quality and ownership, including combined
   components. Assess defensive access/resistance and conversion sustainability
   without duplicate credit. When material evidence is insufficient, leave the
   factor null and explain what is missing; do not default to zero or neutral.
   The checker cannot establish the truth of a populated source claim.
4. **Outlook (§§4A–4E).** Codex records supported direction/neighborhood and
   failure scenarios, not a third projection model. Shared rotation uncertainty
   applies to all affected candidates automatically. Resolve, carry or disqualify
   material risks with rationale. Review credible minutes sensitivity when material;
   diagnostics never replace original forecasts. Where credible alternative
   minutes erase the cushion or flip direction, hold from final selection until
   the role is resolved or the case is robust, as already approved.
5. **Market/ranking (§§5A–5I).** Verify actual eligible full-game standard
   PrizePicks thresholds after the approved restriction. Consider meaningful value,
   variability, settlement/payout and integer winning/tie counts. Codex compares
   lanes and makes preliminary assessments. Preserve §5D eligibility exactly:
   A-range needs agreement and at least 7/8 plus all other conditions; genuine
   disagreement has B+ maximum. Calculate the existing rubric total only when all
   four factors are scored. Assign the strongest defensible preliminary grade and
   rank using the full framework, exact threshold, variability and remaining risks.
   A band is eligibility, not an automatic award of its highest grade. Leave a
   grade/rank unresolved when evidence cannot justify it. Record a substantive
   weakest-proposed-inclusion/strongest-credible-exclusion challenge with rationale;
   the report supplies the existing model/line/rubric context. Consider correlation,
   teammate competition and shared scripts without automatic penalties.

## Completed research output

- Produce a comprehensive ranked **preliminary research board** for every
  defensible candidate in the requested scope, with the strongest supported lane
  per player. Do not cap output at two or three props or force any count.
- Show rank, player/team/opponent, eligible market/direction, observed standard
  full-game PrizePicks threshold and observation time, original DC forecast/minutes,
  original DARKO values/minutes/basis and compatible normalized benchmark, model
  relationship, four factor scores/total, preliminary V2.2 grade, independent
  basketball rationale, principal failure risk and unresolved limitations.
- Summarize both-team environments and shared risks once. Show strongest credible
  excluded alternatives with original evidence and reasons. Keep unresolved or
  unavailable cases separate; disagreement alone is not a reason for exclusion.
- Keep `decision.status=research` and `decision.selected=[]` for a preliminary
  board, even when candidates have grades and ranks. Use existing fields, source
  links and comparison records; no additional approval forms or tracking layer.
  If material research remains incomplete, label the output a checkpoint and
  identify its gaps rather than claim the completed board or final lock.

## Final review and preservation

- Run `tracker check` and `tracker report`; examine five stage summaries and all
  17 existing §III lock items. Missing/conflicting records cannot establish a
  completed lock. “Recorded” means documented, not analytically verified. Even a
  structurally clean note requires analyst review, not software certification.
- Link the actual personnel/market recheck observations and review time before
  the decision. Preserve open risks and re-evaluate changed inputs. There is no
  invented universal market-age threshold.
- Keep research, finalized analytical selections, and explicit placement evidence
  separate. Enter only the analyst/user's actual decision; the tool never chooses.
- Freeze final decisions only after the user explicitly triggers final lock and
  the actual decision is recorded; a preliminary board never triggers it. Use a
  pregame-only note under a new readable label. Snapshots preserve exact
  note bytes, original findings, governing references and attached original source
  bytes. Never overwrite a snapshot or historical grade. Later working-note edits
  do not erase the frozen findings shown by ordinary reports.
- Keep postgame evidence in its separate section/phase. Apply §§IV–V against the
  original snapshot: minutes, roles, volume, quality, conversion, matchup, scripts,
  combined components and exclusions. Review wins and losses equally. Do not infer
  missing chances from box scores or backfill pregame evidence using outcomes.
- Preserve the five-slate protocol and current historical warning dispositions.
  Reuse still-current findings; update affected conclusions only. No methodological
  revisions or historical regrading are authorized by this skill.
