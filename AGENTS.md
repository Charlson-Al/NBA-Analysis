# NBA Analysis Hub — Codex governing instructions (proof of concept)

## Authority
- The user's current, explicitly approved NBA analytical framework and later approved refinements govern all work. Do not invent a framework version, approval, score, grade, projection or odds.
- This file is an implementation guardrail, **not** a replacement for the complete approved framework. Do not assert that a framework rule is fully specified until the complete framework has been provided and versioned.
- Preserve original historical pregame assumptions and selections; never revise them after outcomes are known.

## Evidence discipline
- Source snapshot != verified game cutoff. Track collection time, source's last game, denominators, and quality independently.
- Do not combine points per 100 classified plays with adjusted ratings per 100 possessions.
- Do not promote team-level potential assists or rebound chances into player opportunity ownership.
- Do not treat unvalidated October shot-zone profiles as live November data.
- Distinguish verified inputs, external projections, independent inference, missing evidence, and blocked statuses.
- Validate injuries, rotations and ownership separately before game-day use.
- Never invent unavailable intervals from Drop Coverage or alter external forecasts without an explicitly approved method.
- Exclude PropSims, PBP Stats, and BoxScore Lab CSV from player-prop research unless explicitly authorized.

## Engineering rules
- Raw data in `data/source` is immutable; new snapshots must have unique filenames and provenance metadata.
- Never silently fill, smooth, interpolate, or overwrite missing measurements.
- Every change to data transformation rules requires an automated test and diffable review.
- Keep tests green; show failures instead of force-passing them.
- Never scrape authenticated, blocked or restricted sources without permission and compliant access.
- Do not schedule unattended updates or commit secrets/API keys.

## Current scope
- V1.2 is an incomplete **snapshot** captured 2026-11-03; source cutoffs, current shot zones and personnel are unresolved.
- Phase 1 checks CSV/document fidelity only. No live data fetching, grades or prop recommendations yet.
