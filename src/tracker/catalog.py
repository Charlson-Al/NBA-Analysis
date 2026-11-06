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
    '1': 'Environment/personnel: V2.2 §§1A–1E (both teams, definitions, roles and rotations)',
    '2': 'Screen/models: §§2A–2F (eight markets, original inputs, normalization and disagreements)',
    '3': 'Independent validation: §§3A–3C (four analyst factors; ownership, quality and sustainability)',
    '4': 'Outlook: §§4A–4E (supported direction, uncertainty and failure scenarios)',
    '5': 'Ranking/market: §§5A–5I (eligible lines, value, original grade, alternatives and correlation)',
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
CATALOG = {**STAGES, **LOCK}
