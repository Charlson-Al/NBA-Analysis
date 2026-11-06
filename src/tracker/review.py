"""Mechanical omissions/consistency checks only. Evidence quality requires a human."""
from datetime import datetime
from decimal import Decimal
from math import floor, ceil

from ingestion.store import REPO, digest, decode
from .catalog import (CATALOG, COMPONENTS, FRAMEWORK_PATH, FRAMEWORK_SHA,
                      LOCK, MARKETS, REFINEMENTS, REFINEMENT_PATH, REFINEMENT_SHA, STAGES,
                      APPROVAL_PATH, APPROVAL_REFERENCE, APPROVAL_SHA,
                      REFINEMENT_APPROVALS, REFINEMENT_TIMES)


def framework_check():
    manifest = decode((REPO / 'manifests/framework-sources.json').read_bytes())
    source = next((s for s in manifest['sources'] if s['path'] == FRAMEWORK_PATH), None)
    return bool(manifest['governing_revision_date'] == '2026-11-03' and source and source['status'] == 'governing' and source['sha256'] == FRAMEWORK_SHA and digest((REPO / FRAMEWORK_PATH).read_bytes()) == FRAMEWORK_SHA)


def review(events):
    latest = {e['record']['entity_id']: e for e in events}
    by_event = {e['event_id']: e for e in events}
    warnings = []
    def warn(code, entity, detail):
        warnings.append((code, entity, detail))
    def records(kind):
        return [(key, e['record']['data']) for key, e in latest.items() if e['record']['kind'] == kind]
    def get(key, kind, owner):
        e = latest.get(key)
        if not e or e['record']['kind'] != kind:
            warn('MISSING_LINK', owner, f'Missing {kind} reference')
            return None
        return e['record']['data']
    def verified_claim(e):
        return bool(e and e['status'] == 'verified' and e['verification_scope'] and e['verification_scope'].strip() and e['reviewed_at'] and e['source_ids'] and all(key in latest and latest[key]['record']['kind'] == 'source' for key in e['source_ids']))
    def supported(ids, owner):
        if not ids:
            warn('MISSING_EVIDENCE', owner, 'No evidence links')
            return False
        ok = True
        for key in ids:
            e = get(key, 'evidence', owner)
            if not verified_claim(e):
                warn('UNSUPPORTED_EVIDENCE', owner, 'Evidence is incomplete, unavailable, conflicting or lacks verification support')
                ok = False
        return ok
    if not framework_check():
        warn('FRAMEWORK_BYTES', 'session', 'Governing November 3 source checksum differs')
    if digest((REPO / REFINEMENT_PATH).read_bytes()) != REFINEMENT_SHA:
        warn('REFINEMENT_BYTES', 'session', 'Recorded approved refinement reference differs')
    sessions = records('session')
    if len(sessions) != 1:
        raise ValueError('Exactly one session required')
    session_id, session = sessions[0]
    if digest((REPO / APPROVAL_PATH).read_bytes()) != APPROVAL_SHA or session['approval_reference'] != APPROVAL_REFERENCE:
        warn('APPROVAL_PROVENANCE', session_id, 'Approval reference or pinned decision record differs; review explicit provenance')
    if session['rules_used_sha256'] != FRAMEWORK_SHA:
        warn('FRAMEWORK_CONFLICT', session_id, 'Recorded rules differ from governing November 3 V2.2; preserve historical rules used')
    if session['research_at'] is None:
        applicable = {key for key, (start, _) in REFINEMENTS.items() if start < session['research_date']}
        warn('APPLICABILITY_TIME', session_id, 'Research checkpoint time missing; same-day approval applicability unresolved')
    else:
        research_at = datetime.fromisoformat(session['research_at'])
        applicable = {key for key, start in REFINEMENT_TIMES.items() if datetime.fromisoformat(start) <= research_at}
        if research_at.date().isoformat() != session['research_date']:
            warn('RESEARCH_TIME', session_id, 'Date and timestamp differ; confirm slate timezone convention')
    for key in session['refinement_ids']:
        if session['refinement_approvals'].get(key) != REFINEMENT_APPROVALS.get(key) or key not in REFINEMENTS:
            warn('REFINEMENT_PROVENANCE', session_id, 'Refinement lacks the recorded explicit approval reference: ' + key)

    for key in applicable - set(session['refinement_ids']):
        warn('REFINEMENT_MISSING', session_id, key)
    for key in set(session['refinement_ids']) - applicable:
        if session['research_at'] is None and key in REFINEMENTS and REFINEMENTS[key][0] == session['research_date']:
            warn('REFINEMENT_TIME_UNRESOLVED', session_id, key)
        else:
            warn('REFINEMENT_NOT_APPLICABLE', session_id, key)
    players = {p['id'] for p in session['players']}
    if len(players) != len(session['players']):
        warn('DUPLICATE_PLAYER', session_id, 'Roster contains duplicate identifiers')
    if not players:
        warn('COVERAGE', session_id, 'Credible rotation roster has not been established')
    for key, event in latest.items():
        record, data = event['record'], event['record']['data']
        if record['kind'] in ('candidate', 'comparison', 'requirement', 'calculation') and not record['basis']:
            warn('NO_BASIS', key, 'Assessment has no pinned input event versions')
        for basis_id in record['basis']:
            prior = by_event[basis_id]
            if record['kind'] in ('candidate', 'comparison', 'requirement', 'calculation') and latest[prior['record']['entity_id']]['event_id'] != basis_id:
                warn('STALE_ASSESSMENT', key, 'A pinned dependency has a newer version; analyst review needed')
    for key, source in records('source'):
        for field in ('collected_at', 'cutoff', 'sample', 'unit', 'denominator'):
            if source[field] is None or not str(source[field]).strip():
                warn('SOURCE_METADATA', key, f'Missing {field}; do not infer it')
        if source['published_at'] and source['collected_at'] and datetime.fromisoformat(source['published_at']) > datetime.fromisoformat(source['collected_at']):
            warn('SOURCE_TIME', key, 'Publication follows collection; explain snapshot timing')
    for key, evidence in records('evidence'):
        for source_id in evidence['source_ids']:
            get(source_id, 'source', key)
        if evidence['status'] == 'verified' and not verified_claim(evidence):
            warn('UNSUPPORTED_VERIFIED', key, 'Verified claim lacks sources, review time or verification scope')
        if evidence['status'] != 'verified':
            warn('EVIDENCE_' + evidence['status'].upper(), key, 'Evidence explicitly records ' + evidence['status'] + '; scope and limitation require review')
        if evidence['status'] != 'verified' and not evidence['limitation']:
            warn('MISSING_LIMITATION', key, 'Unresolved evidence needs an explanation')
    coverage = {}
    for key, row in records('coverage'):
        pair = row['player'], row['market']
        if pair in coverage:
            warn('DUPLICATE_COVERAGE', key, 'Multiple entities describe one player-market pair')
        coverage[pair] = row
        if row['player'] not in players:
            warn('UNKNOWN_PLAYER', key, 'Player absent from declared roster')
        if row['opportunity_evidence_ids'] and not row['advance_reasons']:
            warn('OPPORTUNITY_QUEUE', key, 'Independent opportunity evidence present; analyst research priority not documented')
        if not row['higher_reviewed'] or not row['lower_reviewed']:
            warn('DIRECTION_COVERAGE', key, 'Higher/Lower review incomplete')
        if row['market_status'] != 'verified':
            warn('MARKET_COVERAGE', key, 'Market not searched, not recovered, unavailable or uncertain; not proof of absence')
        for evidence_id in row['opportunity_evidence_ids']:
            get(evidence_id, 'evidence', key)
        if row['disposition'] == 'excluded' and not row['disagreement_investigation']:
            warn('EXCLUSION_REVIEW', key, 'Exclusion has no disagreement investigation; do not exclude solely on a split')
    for player in sorted(players):
        missing = [market for market in MARKETS if (player, market) not in coverage]
        if missing:
            warn('COVERAGE', player, 'Missing market rows: ' + ', '.join(missing))
    for key, model in records('model'):
        get(model['source_id'], 'source', key)
        if model['player'] not in players:
            warn('UNKNOWN_PLAYER', key, 'Model player absent from roster')
        if model['provider'] == 'DC' and (model['basis'] != 'per_game' or model['minutes'] is None):
            warn('MODEL_INPUT', key, 'DC requires original per-game forecast and minutes')
        if model['provider'] == 'DARKO' and model['basis'] == 'per_game' and model['minutes'] is None:
            warn('MODEL_INPUT', key, 'DARKO per-game normalization requires original minutes')
    calculations = {}
    def calculated(key, visiting=None):
        if key in calculations:
            return calculations[key]
        visiting = set() if visiting is None else visiting
        if key in visiting:
            warn('CALCULATION', key, 'Cyclic component references')
            return None
        visiting = visiting | {key}
        c = get(key, 'calculation', key)
        if not c:
            return None
        dc = get(c['dc_id'], 'model', key)
        if not dc or dc['minutes'] is None:
            warn('NORMALIZATION_INPUT_MISSING', key, 'DC input or original minutes missing')
            return None
        if dc['provider'] != 'DC' or dc['basis'] != 'per_game' or dc['unit'] != dc['market']:
            warn('CALCULATION', key, 'Invalid DC normalization input')
            return None
        if dc['market'] in COMPONENTS:
            expected_components = COMPONENTS[dc['market']]
            children = [get(child, 'calculation', key) for child in c['component_ids']]
            models = [get(child['dc_id'], 'model', key) if child else None for child in children]
            if c['darko_id'] is not None or len(models) != len(expected_components) or any(m is None for m in models) or sorted(m['market'] for m in models) != sorted(expected_components) or any(m['player'] != dc['player'] or m['minutes'] != dc['minutes'] for m in models):
                warn('CALCULATION', key, 'Combined markets require compatible normalized individual components')
                return None
            values = [calculated(child, visiting) for child in c['component_ids']]
            if any(v is None for v in values):
                warn('NORMALIZATION_COMPONENT_MISSING', key, 'A component calculation is incomplete or invalid')
                return None
            result = sum(values, Decimal(0))
        else:
            darko = get(c['darko_id'], 'model', key)
            if not darko or (darko['basis'] == 'per_game' and darko['minutes'] is None):
                warn('NORMALIZATION_INPUT_MISSING', key, 'DARKO input or original per-game minutes missing')
                return None
            if c['component_ids'] or darko['unit'] != darko['market'] or darko['provider'] != 'DARKO' or any(dc[f] != darko[f] for f in ('player', 'market', 'unit')) or (darko['basis'] == 'per_game' and darko['minutes'] is None):
                warn('CALCULATION', key, 'Incompatible model units, player, statistic or minutes')
                return None
            result = Decimal(str(darko['value'])) * Decimal(str(dc['minutes']))
            if darko['basis'] == 'per_game':
                result /= Decimal(str(darko['minutes']))
        if abs(result - Decimal(str(c['result']))) > Decimal('0.000000001'):
            warn('NORMALIZATION_MISMATCH', key, 'Recorded result differs from approved arithmetic; inputs unchanged')
            return None
        calculations[key] = result
        return result
    for key, _ in records('calculation'):
        calculated(key)
    candidates = dict(records('candidate'))
    for key, candidate in candidates.items():
        dc = get(candidate['dc_id'], 'model', key)
        market = get(candidate['market_id'], 'market', key)
        calc = get(candidate['calculation_id'], 'calculation', key)
        for item in (dc, market):
            if item and (item['player'] != candidate['player'] or item['market'] != candidate['market']):
                warn('CANDIDATE_INPUT', key, 'Input does not match candidate player/market')
        if calc and calc['dc_id'] != candidate['dc_id']:
            warn('CANDIDATE_INPUT', key, 'Calculation uses a different DC snapshot')
        if candidate['rank'] is not None and market and 'standard-only' in applicable and (market['provider'] != 'PrizePicks' or market['period'] != 'full_game' or market['tier'] != 'standard'):
            warn('MARKET_INELIGIBLE', key, 'Ranked candidate uses a market outside approved eligibility')
        benchmark = calculated(candidate['calculation_id']) if calc else None
        relationship = 'Unresolved'
        if dc and market and benchmark is not None and calc and calc['dc_id'] == candidate['dc_id']:
            relationship = compare_at_line(dc['value'], benchmark, market['line'], candidate['direction'])['relationship']
        scores = list(candidate['rubric'].values())
        grade = candidate['grade']
        if grade and grade.startswith('A'):
            if any(v is None for v in scores) or (relationship == 'Unresolved' and (dc is None or calc is None or market is None or benchmark is None)):
                warn('GRADE_SUPPORT_INCOMPLETE', key, 'Recorded A-range grade lacks complete agreement/rubric inputs; analyst review, no auto-regrade')
            if (all(v is not None for v in scores) and sum(scores) < 7) or (dc and market and benchmark is not None and relationship != 'Agree ' + candidate['direction']):
                warn('GRADE_ELIGIBILITY', key, 'Recorded A-range grade conflicts with existing directional agreement or 7-of-8 requirement')
        if grade and relationship == 'Disagree' and grade.startswith('A'):
            warn('DISAGREEMENT_CEILING', key, 'Existing V2.2 B+ maximum; original grade retained')
        if grade and relationship == 'Disagree' and all(v is not None for v in scores) and sum(scores) <= 6 and grade == 'B+':
            warn('GRADE_ELIGIBILITY', key, 'Existing disagreement eligibility band requires analyst review; original grade retained')
        if grade and grade != 'Pass' and all(v is not None for v in scores):
            total = sum(scores)
            if relationship.startswith('Agree') and ((total < 7 and grade.startswith('A')) or (total < 5 and grade.startswith('B')) or (total < 3 and grade.startswith('C'))):
                warn('GRADE_ELIGIBILITY', key, 'Recorded grade exceeds existing agreement/rubric eligibility band')
            if relationship == 'Disagree' and total <= 4 and grade.startswith('B'):
                warn('GRADE_ELIGIBILITY', key, 'Recorded grade exceeds existing disagreement/rubric eligibility band')
        if candidate['rank'] is not None and not any(key in (c['finalist_id'], c['exclusion_id']) for _, c in records('comparison')):
            warn('COMPARISON_MISSING', key, 'Rank has no documented candidate challenge; comparison coverage requires analyst review')
        for opportunity_id in candidate['opportunity_evidence_ids']:
            evidence = get(opportunity_id, 'evidence', key)
            if evidence and evidence['kind'] == 'external_forecast':
                warn('OPPORTUNITY_FORECAST', key, 'External forecast alone does not establish independent opportunity ownership')
        for ref in [candidate['dc_id'], candidate['calculation_id'], candidate['market_id'], *candidate['uncertainty_ids'], *candidate['opportunity_evidence_ids']]:
            if ref in latest and latest[ref]['event_id'] not in latest[key]['record']['basis']:
                warn('UNPINNED_INPUT', key, 'Candidate does not pin a referenced input version')
        if not candidate['outlook'] or not candidate['principal_risk'] or candidate['reviewed_at'] is None:
            warn('CANDIDATE_INCOMPLETE', key, 'Outlook, principal risk or review time missing')
        if not candidate['opportunity_evidence_ids']:
            warn('OPPORTUNITY_GAP', key, 'Player-specific opportunity evidence missing')
        else:
            supported(candidate['opportunity_evidence_ids'], key)
        for factor, score in candidate['rubric'].items():
            if score is None:
                warn('RUBRIC_OPEN', key, factor + ' is unscored; do not present a complete total')
            elif not supported(candidate['rubric_evidence'][factor], key):
                warn('RUBRIC_SUPPORT', key, factor + ' score needs analyst evidence review')
        if candidate['rubric']['opportunities'] == 2 and not candidate['opportunity_evidence_ids']:
            warn('FULL_OPPORTUNITY_SUPPORT', key, 'Full opportunity credit lacks channel evidence')
        for uncertainty_id in candidate['uncertainty_ids']:
            uncertainty = get(uncertainty_id, 'uncertainty', key)
            if uncertainty and key not in uncertainty['candidate_ids']:
                warn('RISK_LINK', key, 'Shared uncertainty does not link back to candidate')
    for key, market in records('market'):
        get(market['source_id'], 'source', key)
        if market['availability'] != 'verified' or market['observed_at'] is None or not market['settlement'] or not market['payout']:
            warn('MARKET_INCOMPLETE', key, 'Availability, observation time, settlement or payout incomplete')
        if 'standard-only' in applicable and (market['provider'] != 'PrizePicks' or market['period'] != 'full_game' or market['tier'] != 'standard'):
            warn('REFERENCE_MARKET', key, 'Reference market is outside standard-only selection scope')
    for key, uncertainty in records('uncertainty'):
        if uncertainty['status'] != 'resolved':
            warn('OPEN_RISK', key, 'Shared uncertainty remains ' + uncertainty['status'])
        elif not supported(uncertainty['evidence_ids'], key):
            warn('RISK_RESOLUTION', key, 'Resolution requires supporting evidence')
        for candidate_id in uncertainty['candidate_ids']:
            c = get(candidate_id, 'candidate', key)
            if c and key not in c['uncertainty_ids']:
                warn('RISK_CONTINUITY', candidate_id, 'Affected candidate omitted shared uncertainty')
    for key, comparison in records('comparison'):
        a = get(comparison['finalist_id'], 'candidate', key)
        b = get(comparison['exclusion_id'], 'candidate', key)
        if comparison['finalist_id'] == comparison['exclusion_id'] or any(not v or not v.strip() for v in comparison['fields'].values()) or comparison['reviewed_at'] is None:
            warn('COMPARISON_INCOMPLETE', key, 'Distinct candidates and every substantive comparison field required')
        if a and b:
            required = {latest[comparison[f]]['event_id'] for f in ('finalist_id', 'exclusion_id')}
            if not required <= set(latest[key]['record']['basis']):
                warn('COMPARISON_BASIS', key, 'Pin both candidate assessment versions')
    requirements = {}
    for key, requirement in records('requirement'):
        pair = requirement['scope'], requirement['code']
        if requirement['code'] not in CATALOG:
            warn('UNKNOWN_REQUIREMENT', key, 'Not an existing catalog requirement')
        if requirement['scope'] != 'slate' and requirement['scope'] not in candidates:
            warn('REQUIREMENT_SCOPE', key, 'Unknown candidate scope')
        if pair in requirements:
            warn('DUPLICATE_REQUIREMENT', key, 'Duplicate scope/requirement assessment')
        requirements[pair] = requirement
        if requirement['status'] == 'met' and not supported(requirement['evidence_ids'], key):
            warn('REQUIREMENT_SUPPORT', key, 'Met claim lacks evidence support')
        if requirement['reviewed_at'] is None:
            warn('REQUIREMENT_TIME', key, 'Assessment review time missing')
    # Report requirement coverage for the slate and every assessed candidate separately.
    for scope in ['slate', *sorted(candidates)]:
        codes = CATALOG if scope == 'slate' else STAGES
        missing = [code for code in codes if (scope, code) not in requirements]
        if missing:
            warn('CHECKLIST_INCOMPLETE', scope, 'Unassessed requirements: ' + ', '.join(missing))
    for key, decision in records('decision'):
        decision_event = latest[key]
        pinned_candidates = {by_event[eid]['record']['entity_id']: by_event[eid] for eid in decision_event['record']['basis'] if by_event[eid]['record']['kind'] == 'candidate'}
        prior_records = {e['record']['entity_id']: e for e in events if e['sequence'] <= decision_event['sequence']}
        prior_requirements = {(e['record']['data']['scope'], e['record']['data']['code']): e['record']['data'] for e in prior_records.values() if e['record']['kind'] == 'requirement'}
        if decision['decision_at'] is None:
            warn('DECISION_TIME', key, 'Original decision time unknown; do not substitute recovery time')
        for candidate_id in decision['candidate_ids']:
            get(candidate_id, 'candidate', key)
        if decision['status'] in ('finalized_selection', 'confirmed_wager') and not decision['candidate_ids']:
            warn('DECISION_STATUS', key, 'Finalized/placed status without candidates')
        if decision['status'] == 'confirmed_wager':
            supported(decision['confirmation_evidence_ids'], key)
            prior_final = any(e['record']['kind'] == 'decision' and e['sequence'] < latest[key]['sequence'] and e['record']['data']['status'] == 'finalized_selection' and set(decision['candidate_ids']) <= set(e['record']['data']['candidate_ids']) for e in events)
            if not prior_final:
                warn('PLACEMENT_WITHOUT_SELECTION', key, 'Placement has no separate finalized analytical record; do not infer selection status')
        if decision['status'] == 'finalized_selection':
            for code in LOCK:
                r = prior_requirements.get(('slate', code))
                if not r or r['status'] not in ('met', 'not_applicable'):
                    warn('LOCK_INCOMPLETE', key, code)
            for candidate_id in decision['candidate_ids']:
                pinned = pinned_candidates.get(candidate_id)
                c = pinned['record']['data'] if pinned else None
                market_event = next((by_event[eid] for eid in pinned['record']['basis'] if by_event[eid]['record']['entity_id'] == c['market_id'] and by_event[eid]['record']['kind'] == 'market'), None) if pinned else None
                m = market_event['record']['data'] if market_event else None
                if m and 'standard-only' in applicable and (m['provider'] != 'PrizePicks' or m['period'] != 'full_game' or m['tier'] != 'standard'):
                    warn('MARKET_INELIGIBLE', key, 'Finalized selection uses an ineligible market')
                if c and (c['disposition'] == 'pass' or c['direction'] == 'Pass' or c['grade'] in (None, 'Pass')):
                    warn('DECISION_STATUS', key, 'Finalized selection conflicts with candidate assessment')
        if not set(decision['candidate_ids']) <= set(pinned_candidates):
            warn('DECISION_BASIS', key, 'Decision must pin original candidate versions')
    return sorted(set(warnings)), latest, requirements


# Categories describe structural compliance, never automatic basketball decisions.
HARD = {'FRAMEWORK_BYTES', 'FRAMEWORK_CONFLICT', 'APPROVAL_PROVENANCE',
        'REFINEMENT_BYTES', 'REFINEMENT_PROVENANCE', 'REFINEMENT_NOT_APPLICABLE',
        'MARKET_INELIGIBLE', 'GRADE_ELIGIBILITY', 'DISAGREEMENT_CEILING',
        'NORMALIZATION_MISMATCH', 'CALCULATION', 'CANDIDATE_INPUT', 'DECISION_STATUS'}
INCOMPLETE = {'MISSING_LINK', 'MISSING_EVIDENCE', 'UNSUPPORTED_EVIDENCE',
              'UNSUPPORTED_VERIFIED', 'SOURCE_METADATA', 'REFINEMENT_MISSING',
              'APPLICABILITY_TIME', 'REFINEMENT_TIME_UNRESOLVED', 'COVERAGE', 'DIRECTION_COVERAGE', 'MARKET_COVERAGE',
              'CANDIDATE_INCOMPLETE', 'OPPORTUNITY_GAP', 'RUBRIC_OPEN', 'RUBRIC_SUPPORT',
              'FULL_OPPORTUNITY_SUPPORT', 'MARKET_INCOMPLETE', 'COMPARISON_INCOMPLETE',
              'COMPARISON_MISSING', 'CHECKLIST_INCOMPLETE', 'LOCK_INCOMPLETE',
              'REQUIREMENT_SUPPORT', 'REQUIREMENT_TIME', 'NO_BASIS', 'UNPINNED_INPUT',
              'COMPARISON_BASIS', 'DECISION_BASIS', 'DECISION_TIME', 'OPPORTUNITY_FORECAST','GRADE_SUPPORT_INCOMPLETE','NORMALIZATION_INPUT_MISSING','NORMALIZATION_COMPONENT_MISSING','EVIDENCE_INCOMPLETE','EVIDENCE_UNAVAILABLE','EVIDENCE_CONFLICTING'}
CHECK_CODES = {
    'coverage': {'COVERAGE','DIRECTION_COVERAGE','MARKET_COVERAGE','EXCLUSION_REVIEW'},
    'models': {'NORMALIZATION_COMPONENT_MISSING','NORMALIZATION_INPUT_MISSING','MODEL_INPUT','NORMALIZATION_MISMATCH','CALCULATION','CANDIDATE_INPUT','MISSING_LINK'},
    'evidence': {'UNSUPPORTED_VERIFIED','UNSUPPORTED_EVIDENCE','MISSING_EVIDENCE','SOURCE_METADATA'},
    'opportunities': {'OPPORTUNITY_GAP','FULL_OPPORTUNITY_SUPPORT','OPPORTUNITY_FORECAST'},
    'rubric': {'RUBRIC_OPEN','RUBRIC_SUPPORT'},
    'risks': {'RISK_CONTINUITY','RISK_LINK','RISK_RESOLUTION','STALE_ASSESSMENT','UNPINNED_INPUT'},
    'market': {'MARKET_INCOMPLETE','MARKET_INELIGIBLE'},
    'comparison': {'COMPARISON_INCOMPLETE','COMPARISON_MISSING','COMPARISON_BASIS'},
    'grade': {'GRADE_SUPPORT_INCOMPLETE','GRADE_ELIGIBILITY','DISAGREEMENT_CEILING'},
}
REQUIREMENT_GROUPS = {
    '2A': ('coverage',), 'L03': ('coverage',),
    '2B': ('models',), '2C': ('models',), '2D': ('models','market'), '2F': ('models',),
    'L04': ('models',), 'L05': ('models',), 'L06': ('models',), 'L07': ('models','market'),
    '3A-opportunities': ('opportunities','evidence'), 'L09': ('opportunities','evidence'),
    '3C': ('rubric','evidence'), 'L08': ('rubric','evidence'),
    '4C': ('risks',), 'L11': ('risks',), '1C': ('risks',), '1D': ('risks',), 'L02': ('risks',),
    '5A': ('market',), 'L13': ('market',), '5G': ('comparison',), 'L14': ('comparison',),
    '5D': ('grade','rubric'), 'L16': ('grade','rubric'), 'VI': ('evidence',),
}


def compliance(events):
    warnings, latest, assessments = review(events)
    findings = [{'severity': 'hard_violation' if code in HARD else 'incomplete_evidence' if code in INCOMPLETE else 'warning',
                 'code': code, 'entity': entity, 'reason': reason} for code, entity, reason in warnings]
    rows = []
    scopes = ['slate'] + sorted(k for k,e in latest.items() if e['record']['kind'] == 'candidate')
    for scope in scopes:
        for code, description in CATALOG.items():
            if scope != 'slate' and code not in STAGES:
                continue
            assessment = assessments.get((scope,code))
            reasons = []
            if not assessment:
                reasons.append('No analyst assessment recorded')
            else:
                if assessment['status'] not in ('met','not_applicable'):
                    reasons.append('Analyst records ' + assessment['status'])
                if assessment['reviewed_at'] is None:
                    reasons.append('Review time missing')
                if assessment['status'] == 'met' and not assessment['evidence_ids']:
                    reasons.append('Completion claim has no evidence links')
                for evidence_id in assessment['evidence_ids']:
                    e = latest.get(evidence_id)
                    if not e or e['record']['kind'] != 'evidence' or e['record']['data']['status'] != 'verified':
                        reasons.append('Evidence link missing or not verified: ' + evidence_id)
                own = [key for key,e in latest.items() if e['record']['kind']=='requirement' and e['record']['data'] is assessment]
                reasons.extend(f['reason'] for f in findings if f['entity'] in own)
            relevant_codes = set().union(*(CHECK_CODES[g] for g in REQUIREMENT_GROUPS.get(code,())))
            related = [f for f in findings if f['code'] in relevant_codes and (scope == 'slate' or f['entity'] == scope)]
            reasons.extend(f['code'] + ': ' + f['reason'] for f in related)
            rows.append({'scope':scope,'code':code,'description':description,
                         'analyst_status':assessment['status'] if assessment else 'unassessed',
                         'evidence_ids':assessment['evidence_ids'] if assessment else [],
                         'rationale':assessment['rationale'] if assessment else None,
                         'completion_supported':not reasons,
                         'concerns':sorted(set(reasons)),
                         'judgment':'Analyst evidence quality, materiality and basketball judgment remain required'})
    exact_lines = []
    invalid = {f['entity'] for f in findings if f['code'] in {'NORMALIZATION_MISMATCH','NORMALIZATION_INPUT_MISSING','NORMALIZATION_COMPONENT_MISSING','CALCULATION','CANDIDATE_INPUT'}}
    for key, event in latest.items():
        if event['record']['kind'] != 'candidate':
            continue
        c = event['record']['data']
        def linked(ref, kind):
            e = latest.get(ref)
            return e['record']['data'] if e and e['record']['kind'] == kind else None
        dc, calc, market = linked(c['dc_id'],'model'), linked(c['calculation_id'],'calculation'), linked(c['market_id'],'market')
        if dc and calc and market and key not in invalid and c['calculation_id'] not in invalid:
            exact_lines.append({'candidate':key,'DC':dc['value'],'DARKO_normalized':calc['result'],'line':market['line'],**compare_at_line(dc['value'],calc['result'],market['line'],c['direction'])})
    return {'findings':findings,'requirements':rows,'latest':latest,'exact_lines':exact_lines}


def compare_at_line(dc, darko, line, direction):
    a,b,l = (Decimal(str(v)) for v in (dc,darko,line))
    relationship = 'Unresolved' if a == l or b == l else ('Agree Higher' if a > l else 'Agree Lower') if (a > l) == (b > l) else 'Disagree'
    if direction == 'Higher':
        winning_count = str(floor(l) + 1) + ' or more'
        losing_count = str(ceil(l) - 1) + ' or fewer'
    elif direction == 'Lower':
        winning_count = str(ceil(l) - 1) + ' or fewer'
        losing_count = str(floor(l) + 1) + ' or more'
    else:
        winning_count = losing_count = 'No selected direction'
    return {'relationship':relationship,'wins':winning_count,'ties':str(l) if l == l.to_integral_value() else 'No integer tie','loses':losing_count}



def cell(value):
    return str(value).replace('|',r'\|').replace('\n',' ').replace('\r',' ')


def render(events):
    report = compliance(events)
    latest = report['latest']
    findings = report['findings']
    lines = ['# V2.2 execution and compliance checklist', '',
             'Mechanical review only. Statuses are analyst declarations, not automated basketball verification.',
             'Source identity: ' + ('matches pinned November 3 bytes.' if framework_check() else 'MISMATCH.'),
             'Approval/refinement provenance checked against pinned records; not independent authentication.', '',
             f'Journal events: {len(events)}. Checkpoint event: {events[-1]["event_id"]}.',
             'Original event records remain unchanged. --at reports can reproduce an earlier checkpoint.', '',
             '| Governing requirement | Analyst status | Evidence links | Completion support / concerns |',
             '|---|---|---|---|']
    for row in report['requirements']:
        if row['scope'] != 'slate':
            continue
        support = '; '.join(row['concerns']) if row['concerns'] else 'Recorded; human judgment still required'
        lines.append('| ' + ' | '.join(cell(v) for v in (row['code'] + ': ' + row['description'],row['analyst_status'],', '.join('[' + eid + '](#evidence-' + eid + ')' for eid in row['evidence_ids']) or 'none',support)) + ' |')
    lines += ['', '## Candidate assessments (original decisions preserved)', '',
              '| Candidate | Direction | Original grade | Rank | Research status | Unassessed stage requirements |',
              '|---|---|---|---|---|---|']
    for key,event in latest.items():
        if event['record']['kind']=='candidate':
            c=event['record']['data']
            count=sum(row['scope']==key and row['analyst_status']=='unassessed' for row in report['requirements'])
            lines.append('| ' + ' | '.join(cell(v) for v in (key,c['direction'],c['grade'] or 'unrecorded',c['rank'] or 'unrecorded',c['disposition'],count)) + ' |')
    lines += ['', '## Exact-line arithmetic (not a probability or selection)', '', '| Candidate | DC | DARKO normalized | Line | Relationship | Wins | Ties | Loses |', '|---|---|---|---|---|---|---|---|']
    for row in report['exact_lines']:
        lines.append('| ' + ' | '.join(cell(row[k]) for k in ('candidate','DC','DARKO_normalized','line','relationship','wins','ties','loses')) + ' |')
    lines += ['', 'Tie counts are arithmetic; provider settlement must be separately verified. Invalid/missing inputs are omitted.', '']
    lines += ['', '## Evidence register (verification scope is limited)', '']
    for key,event in latest.items():
        if event['record']['kind']=='evidence':
            e=event['record']['data']
            lines += [f'<a id="evidence-{key}"></a>', f'- {key}: {cell(e["status"])}; scope: {cell(e["verification_scope"] or "unrecorded")}; sources: {cell(", ".join(e["source_ids"]) or "none")}; concerns: {cell(e["limitation"] or "none recorded")}.']
    lines += ['', '| Source ID | Reference | Collected | Statistical cutoff | Unit / denominator |', '|---|---|---|---|---|']
    for key,event in latest.items():
        if event['record']['kind']=='source':
            s=event['record']['data']
            lines.append('| ' + ' | '.join(cell(v if v is not None else 'unknown') for v in (key,s['reference'],s['collected_at'],s['cutoff'],str(s['unit']) + ' / ' + str(s['denominator']))) + ' |')
    for category in ('hard_violation','incomplete_evidence','warning'):
        group=[f for f in findings if f['severity']==category]
        lines += ['', '## ' + category.replace('_',' ').title() + f' ({len(group)})', '']
        lines += [f'- {f["code"]} [{f["entity"]}]: {f["reason"]}' for f in group] or ['None recorded.']
    lines += ['', '## Decision history', '']
    for event in events:
        record=event['record']
        if record['kind']=='decision':
            d=record['data']
            lines.append(f'- {d["decision_at"]}: {d["status"]}; pinned versions: {len(record["basis"])}; original event {event["event_id"]}.')
    lines += ['', 'Private output: do not commit source data, private provenance, reports or placement evidence to public Git.', '']
    return '\n'.join(lines)
