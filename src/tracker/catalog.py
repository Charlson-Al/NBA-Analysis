"""Navigation to existing V2.2 requirements, not a scoring implementation."""
FRAMEWORK_SHA = '7eea2f0bd83bcba4f930ca96764e971a077f3d5aad37f70f72216be16849395a'
FRAMEWORK_PATH = 'docs/framework/source/nba-player-props-v2.2-2026-11-03.txt'
REFINEMENT_PATH = 'docs/governance/v22-execution-refinements.md'
REFINEMENT_SHA = '4d26e13094dcfc325e6ff27d4bfd8ee42e2b9ade47a6e30e24cafe6773cad41a'
APPROVAL_PATH = 'docs/governance/decisions.md'
APPROVAL_REFERENCE = 'docs/governance/decisions.md#decision-2026-11-06-baseline'
APPROVAL_SHA = 'ea7983b61d3c267dff11266abb85de14772fe709dd1e57a05025ca14b8a681b7'
REFINEMENT_APPROVALS = {
    'standard-only': '01a1ace7-09e3-7282-9824-6ed138226f54',
    'opportunity-handoff': '01a1b130-b6ef-7971-b378-d6dce44c8b0e',
    'minutes-sensitivity': '01a1b130-b6ef-7971-b378-d6dce44c8b0e',
    'whole-number-outcomes': '01a1b130-b6ef-7971-b378-d6dce44c8b0e',
}
REFINEMENT_TIMES = {'standard-only': '2026-11-05T18:09:45+00:00',
                    **{key: '2026-11-06T14:08:42+00:00' for key in REFINEMENT_APPROVALS if key != 'standard-only'}}
REFINEMENTS = {
    'standard-only': ('2026-11-05', 'Standard full-game PrizePicks eligibility'),
    'opportunity-handoff': ('2026-11-06', 'Investigate independently supported opportunities despite model splits'),
    'minutes-sensitivity': ('2026-11-06', 'Review credible minutes sensitivity before ranking'),
    'whole-number-outcomes': ('2026-11-06', 'Record winning, tying and losing outcomes'),
}
MARKETS = ('PTS', 'REB', 'AST', '3PM', 'PR', 'PA', 'RA', 'PRA')
COMPONENTS = {'PR': ('PTS', 'REB'), 'PA': ('PTS', 'AST'), 'RA': ('REB', 'AST'), 'PRA': ('PTS', 'REB', 'AST')}
STAGES = {
    '1A': 'Both offenses/defenses: pace, possessions, transition, adjusted efficiency, Four Factors, shot profiles, schedule; compatible samples/units',
    '1B': 'Tendencies versus vulnerabilities: access, resistance and player ownership',
    '1C': 'Active personnel, injuries, starters, restrictions, bench/closing roles, competition and effects',
    '1D': 'Recent/personnel-specific minutes and substitutions; preserve DC baseline; no double injury adjustment',
    '1E': 'Carry role, environment, minutes credibility, resistance and unresolved concerns',
    '2A': 'Credible rotation players, eight markets, Higher/Lower; preserve DC and available uncertainty',
    '2B': 'DARKO statistical sustainability inputs; DPM is not a box-score projection',
    '2C': 'Compatible normalization once to DC minutes; original inputs and components retained',
    '2D': 'Exact-threshold model relationship; neutral is not agreement',
    '2E': 'Investigate role, chances, competition, quality, conversion, timing and nonlinear minutes; no automatic averaging',
    '2F': 'Complete model comparison record or explicitly unresolved',
    '3A-role': 'Analyst minutes/role factor, distinct supporting evidence',
    '3A-opportunities': 'Player-specific volume, quality and ownership; each combined component; no unsupported full credit',
    '3A-matchup': 'Incremental opponent access/resistance to established channel',
    '3A-sustainability': 'Volume, quality and conversion regression; distinct conclusions, no double counting',
    '3B': 'Investigate disagreement and preserve conflict; existing B+ maximum applies',
    '3C': 'Four-factor evidence record with unresolved concerns; incomplete is not a complete total',
    '4A': 'Supported statistical neighborhood; no fabricated third model or range',
    '4B': 'Analyst-supported Higher, Lower or Pass',
    '4C': 'Every material risk resolved, carried or disqualifying',
    '4D': 'Minutes, volume, quality, conversion, matchup, competition and script failure paths',
    '4E': 'Outlook, evidence, uncertainty and principal failure scenario preserved',
    '5A': 'Actual eligible line, provider, period, tier, settlement, payout and availability',
    '5B': 'Both models compared at exact current threshold; recompute on change',
    '5C': 'Meaningful margin relative to variability and risks; no universal margin or invented probabilities',
    '5D': 'Analyst grade follows existing eligibility bands and all A-range requirements; no automatic grade',
    '5E': 'Strongest credible market per player, including independent opportunities',
    '5F': 'Overall slate ranking and comparison coverage; no forced selections',
    '5G': 'Substantive weakest-finalist versus strongest-eligible-exclusion comparison',
    '5H': 'Teammate competition, shared scripts, compatible correlation and concentrated downside',
    '5I': 'Exact market, models, rubric, advantage, original grade, risk, comparison and selection status',
}
LOCK = dict(zip((f'L{i:02}' for i in range(1,18)), (
    'Both teams and material offensive/defensive conditions evaluated',
    'Current injuries, rotations and expected starters checked',
    'Every credible player screened across eight markets',
    'Original DC projections and minutes preserved',
    'Compatible DARKO normalized to DC minutes',
    'Original and normalized DARKO distinguished',
    'Model relationship assessed at selected exact threshold',
    'Distinct evidence for each rubric factor',
    'Full opportunities credit has player-specific statistical support',
    'Volume, quality and conversion evaluated separately',
    'Material risks carried through all five stages',
    'Market advantage assessed relative to variability',
    'Available lines, tiers and payouts checked',
    'Weakest finalist challenged against strongest exclusion',
    'Correlation and shared scripts considered',
    'Original grade reflects evidence and uncertainty',
    'Material personnel and market developments rechecked',
)))
ARCHIVE = {
    'IV-A': 'Cumulative stage evidence and documented reasons for changed conclusions',
    'IV-B': 'Frozen original pregame models, markets, grades, evidence, exclusions and selection/placement status',
    'IV-C': 'Reuse current verified findings; revisit only material changes',
    'V-A': 'Postgame minutes, role, volume, quality, conversion, matchup, script, market and confidence; combined components',
    'V-B': 'Classify mechanisms without inferring unavailable chances or double-counting losses',
    'V-C': 'Review winners and favorable conversion using the same standards',
    'V-D': 'Predictable mistake versus variance, unusual event or unresolved',
    'V-E': 'Review exclusions using original evidence and actual availability',
    'V-F': 'Calibration by original grades/evidence; no small-sample probabilities or reactive grading changes',
    'VI': 'Source responsibilities, exclusions, dates, sample sizes, units, filters, freshness and independence',
    'VII': 'Ownership, risk continuity, confidence, binding comparison, process/outcome separation and provenance',
    'VIII': 'Five-slate protocol: archive, opportunities/risks, verified outcomes, mechanisms and exclusions',
    'IX': 'Standard final output fields and strongest-exclusion rationale',
}
CATALOG = {**STAGES, **LOCK, **ARCHIVE}
