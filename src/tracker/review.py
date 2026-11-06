"""Five stage structural checks, never basketball certification or automatic decisions."""
from datetime import datetime
from html import escape

from ingestion.store import REPO, decode, digest, encode, validate
from .calculations import exact_line, normalize
from .catalog import (APPROVAL_PATH, APPROVAL_REFERENCE, APPROVAL_SHA, FRAMEWORK_PATH,
                      FRAMEWORK_SHA, LOCK, MARKETS, COMPONENTS, REFINEMENT_PATH, REFINEMENT_SHA,
                      REFINEMENT_TIMES, STAGES)


def present(value):
    return isinstance(value, str) and bool(value.strip()) and value.strip().lower() not in {'n/a','na','none','unknown','not applicable','not researched','not assessed'}


def when(value):
    return datetime.fromisoformat(value.upper()) if value else None


def effective(at):
    return sorted(key for key, start in REFINEMENT_TIMES.items() if when(start) <= when(at))


def authority_issues(note):
    files = ((FRAMEWORK_PATH, FRAMEWORK_SHA), (APPROVAL_PATH, APPROVAL_SHA),
             (REFINEMENT_PATH, REFINEMENT_SHA))
    errors = []
    for path, expected in files:
        if digest((REPO / path).read_bytes()) != expected:
            errors.append('Pinned authority bytes differ: ' + path)
    manifest = decode((REPO / 'manifests/framework-sources.json').read_bytes())
    if not any(s['path'] == FRAMEWORK_PATH and s['sha256'] == FRAMEWORK_SHA and s['status'] == 'governing' for s in manifest['sources']):
        errors.append('Governing manifest identity differs')
    if note['authority']['rules_used_sha256'] != FRAMEWORK_SHA:
        errors.append('Historical/working framework reference conflicts with November 3; original declaration preserved')
    if note['authority']['approval_reference'] != APPROVAL_REFERENCE:
        errors.append('Explicit approval reference differs')
    checkpoints = [note['research_at'], note['decision']['at'], note['lock_review']['at']]
    checkpoints += [c['reviewed_at'] for c in note['candidates']]
    last = max(when(at) for at in checkpoints if at)
    required = set(effective(last.isoformat()))
    declared = set(note['authority']['refinements'])
    if required != declared:
        errors.append('Applicable dated refinements need review at actual checkpoints: ' + ', '.join(sorted(required ^ declared)))
    return errors


def check(note, additional=()):
    validate('tracker', note)
    issues = list(additional)
    def issue(stage, state, code, subject, reason):
        item = dict(stage=stage, state=state, code=code, subject=subject, reason=reason)
        if item not in issues:
            issues.append(item)
    for reason in authority_issues(note):
        issue('authority', 'conflicting', 'AUTHORITY', note['id'], reason)
    decision = note['decision']
    checkpoint = decision['at'] or note['lock_review']['at'] or max(
        [note['research_at']] + [c['reviewed_at'] for c in note['candidates'] if c['reviewed_at']], key=when)
    cutoff = when(checkpoint)
    if cutoff < when(note['research_at']):
        issue('authority', 'conflicting', 'CHECKPOINT_ORDER', note['id'], 'Decision precedes research checkpoint')
    players = {p['id']: p for p in note['players']}
    candidates = {c['id']: c for c in note['candidates']}
    sources = note['sources']
    for rows, field, label in ((note['players'], 'id', 'player'), (note['candidates'], 'id', 'candidate'), (note['risks'], 'id', 'risk')):
        if len({r[field] for r in rows}) != len(rows):
            issue('1', 'conflicting', 'DUPLICATE_ID', label, 'Identifiers must be unique')
    if not present(note['roster_note']):
        issue('1', 'analyst_review_required', 'ROSTER_SCOPE', 'slate', 'Explain credible rotation coverage once, including any exclusions')
    if not players:
        issue('1', 'missing', 'ROSTER', 'slate', 'Credible rotation roster and inclusion rationale missing')

    def evidence(ids, support, subject, stage, owner, independent=False, pregame=True):
        if not ids:
            issue(stage, 'missing', 'EVIDENCE', owner, (support or 'Risk resolution') + ' evidence references missing')
            return []
        used = []
        for key in ids:
            source = sources.get(key)
            if not source:
                issue(stage, 'missing', 'SOURCE_LINK', owner, 'Unknown source: ' + key)
                continue
            used.append(source)
            scoped = subject in source['subjects'] or (support in ('environment','personnel','rotation','matchup',None) and players.get(subject, {}).get('game') in source['subjects'])
            if (support is not None and support not in source['supports']) or not scoped:
                issue(stage, 'conflicting', 'IRRELEVANT_EVIDENCE', owner, key + ' lacks declared subject/channel scope')
            if independent and source['kind'] in ('forecast', 'inference'):
                issue(stage, 'analyst_review_required', 'OWNERSHIP', owner, key + ' is not independent observed opportunity evidence')
            if pregame and source.get('phase', 'pregame') == 'postgame':
                issue(stage, 'conflicting', 'POSTGAME_SUPPORT', owner, key + ' cannot support an original pregame decision')
            if source['status'] != 'recorded':
                issue(stage, source['status'], 'EVIDENCE_STATUS', owner, key + ': ' + source['status'])
            for field in ('observed_at', 'reviewed_at'):
                at = when(source[field])
                if at is None:
                    issue(stage, 'missing', 'SOURCE_TIME', owner, key + ': ' + field + ' unknown')
                elif pregame and at > cutoff:
                    issue(stage, 'conflicting', 'LATE_EVIDENCE', owner, key + ': ' + field + ' after decision/checkpoint; retrospective only')
            if pregame and source.get('cutoff'):
                try:
                    parsed = datetime.fromisoformat(source['cutoff'].upper())
                    if (parsed > cutoff if parsed.utcoffset() is not None else parsed.date() > cutoff.date()):
                        issue(stage, 'conflicting', 'FUTURE_CUTOFF', owner, key + ': statistical cutoff follows decision')
                except ValueError:
                    pass  # Non-ISO descriptions remain analyst-reviewed, not silently normalized.
            if source['observed_at'] and source['reviewed_at'] and when(source['observed_at']) > when(source['reviewed_at']):
                issue(stage, 'conflicting', 'SOURCE_ORDER', owner, key + ': observation follows review')
        return used

    for key, source in sources.items():
        if source.get('phase') == 'postgame':
            continue  # Kept in the working note; never counted as pregame support.
        for field in ('cutoff', 'sample', 'unit', 'denominator') if set(source['supports']) & {'model','opportunities','sustainability'} else ():
            if not source.get(field) or not source[field].strip():
                issue('sources', 'analyst_review_required', 'SOURCE_CONTEXT', key, field + ' not established; no inferred value')
    for game in sorted({p['game'] for p in players.values()}):
        matchup = note['matchups'].get(game)
        for section in ('environment', 'personnel', 'rotation'):
            claim = matchup[section] if matchup else None
            if not claim or not present(claim['note']):
                issue('1', 'missing', 'MATCHUP', game, section + ' research missing')
            evidence(claim['sources'] if claim else [], section, game, '1', game)

    models, screening = {}, {}
    for projection in note['projections']:
        key = projection['player'], projection['provider']
        if key in models:
            issue('2', 'conflicting', 'DUPLICATE_MODEL', projection['player'], 'Ambiguous original model rows')
            models[key] = None
            continue
        models[key] = projection
        if projection['minutes'] is not None and projection['minutes'] < 0 or any(value < 0 for value in projection['values'].values()):
            issue('2', 'conflicting', 'ORIGINAL_INPUT', projection['player'], 'Negative original count/minutes retained unchanged; inspect supplied source')
        if projection['player'] not in players:
            issue('2', 'conflicting', 'MODEL_PLAYER', projection['player'], 'Projection outside declared roster')
        evidence([projection['source']], 'model', projection['player'], '2', projection['player'])
        if projection['provider'] == 'DC':
            screening[projection['player']] = sorted(projection['values'])
            if projection['basis'] != 'per_game' or projection['minutes'] is None:
                issue('2', 'conflicting', 'DC_INPUT', projection['player'], 'Original DC per-game values and minutes required')
    for player in players:
        missing = sorted(set(MARKETS) - set(screening.get(player, [])))
        if missing:
            issue('2', 'missing', 'SCREEN_COVERAGE', player, 'Missing supplied DC screening inputs: ' + ', '.join(missing))

    if not candidates:
        for stage in ('3','4','5'):
            issue(stage, 'analyst_review_required', 'NO_CANDIDATES', 'slate', 'No serious candidate assessments recorded; no implied validation or forced selection count')
    boundary = set(decision['selected']) | {c['id'] for c in candidates.values() if c['rank'] is not None}
    comparison_members = {c[key] for c in note['comparisons'] for key in ('candidate','alternative')}
    lines, used_by_candidate = {}, {}
    for c in candidates.values():
        owner, player = c['id'], c['player']
        if player not in players:
            issue('1', 'conflicting', 'CANDIDATE_PLAYER', owner, 'Candidate outside declared roster')
        reviewed = when(c['reviewed_at'])
        if reviewed is None:
            issue('3', 'missing', 'ASSESSMENT_TIME', owner, 'Analyst review time unknown')
        elif reviewed > cutoff:
            issue('3', 'conflicting', 'LATE_ASSESSMENT', owner, 'Assessment follows decision; original decision cannot use it')
        used = []
        for factor, support in (('role', 'rotation'), ('opportunities', 'opportunities'), ('matchup', 'matchup'), ('sustainability', 'sustainability')):
            f = c['validation'][factor]
            if f['score'] is None or not present(f['note']):
                issue('3', 'missing', 'VALIDATION', owner, factor + ': analyst score/rationale incomplete')
            used += evidence(f['sources'], support, player, '3', owner, independent=factor == 'opportunities')
        opportunity_sources = [sources[key] for key in c['validation']['opportunities']['sources'] if key in sources]
        if not any(s['kind'] == 'observed' and s['status'] == 'recorded' and player in s['subjects'] and 'opportunities' in s['supports'] and s.get('phase','pregame') == 'pregame' for s in opportunity_sources):
            issue('3', 'missing', 'INDEPENDENT_OPPORTUNITIES', owner, 'No scoped independent observed opportunity source; original score retained, not certified')
        for field in ('outlook', 'failure'):
            if not present(c[field]):
                issue('4', 'missing', 'OUTLOOK', owner, field + ' missing')
        dc, darko, market = models.get((player, 'DC')), models.get((player, 'DARKO')), c['line']
        relationship = 'Unresolved'
        if dc and darko and c['market'] in dc['values']:
            try:
                benchmark = normalize(darko, dc['minutes'], c['market'])
                if market:
                    lines[owner] = exact_line(dc['values'][c['market']], benchmark, market['value'], c['direction'])
                    lines[owner].update(DC_minutes=dc['minutes'], DARKO_minutes=darko['minutes'], DARKO_basis=darko['basis'], DARKO_original={key:darko['values'][key] for key in COMPONENTS.get(c['market'],(c['market'],))})
                    relationship = lines[owner]['relationship']
            except ValueError as exc:
                issue('2', 'missing', 'NORMALIZATION', owner, str(exc))
            for model in (dc, darko):
                used += evidence([model['source']], 'model', player, '2', owner)
        else:
            issue('2', 'missing', 'MODEL_COMPARISON', owner, 'Original compatible model inputs incomplete')
        if relationship == 'Disagree' and not present(c.get('disagreement')):
            issue('3', 'analyst_review_required', 'DISAGREEMENT', owner, 'Investigate split; independent opportunity remains in research')
        if market is None:
            issue('5', 'missing', 'MARKET', owner, 'No selectable threshold recorded; this does not invalidate model screening')
        else:
            used += evidence([market['source']], 'market', player, '5', owner)
            if 'standard-only' in effective(checkpoint) and (market['provider'], market['tier'], market['period']) != ('PrizePicks', 'standard', 'full_game'):
                state = 'conflicting' if owner in boundary or owner in comparison_members else 'analyst_review_required'
                issue('5', state, 'MARKET_ELIGIBILITY', owner, 'Observed reference line is not eligible for current selection/ranking')
        if reviewed and any(when(s['reviewed_at']) and when(s['reviewed_at']) > reviewed for s in used):
            issue('3', 'analyst_review_required', 'STALE_ASSESSMENT', owner, 'Input reviewed after candidate assessment; analyst recheck required')
        used_by_candidate[owner] = used
        scores = [f['score'] for f in c['validation'].values()]
        grade = c['grade']
        if grade and grade.startswith('A') and (relationship != 'Agree ' + c['direction'] or any(v is None for v in scores)):
            issue('5', 'conflicting' if relationship != 'Unresolved' else 'analyst_review_required', 'GRADE_ELIGIBILITY', owner, 'Recorded A grade lacks existing agreement/rubric eligibility; original grade unchanged')
        if grade and all(v is not None for v in scores):
            total = sum(scores)
            ceiling = 'A' if total >= 7 else 'B' if total >= 5 else 'C' if total >= 3 else 'D'
            if relationship == 'Disagree':
                ceiling = 'B+' if total >= 7 else 'B' if total >= 5 else 'C'
            order = ['Pass','D','C-','C','C+','B-','B','B+','A-','A','A+']
            maximum = 'A+' if ceiling == 'A' else 'B+' if ceiling == 'B' and relationship != 'Disagree' else 'C+' if ceiling == 'C' else ceiling
            if grade in order and order.index(grade) > order.index(maximum):
                issue('5', 'conflicting', 'GRADE_LIMIT', owner, 'Existing V2.2 eligibility band exceeded; no automatic regrading')
    for risk in note['risks']:
        affected = [c for c in candidates.values() if c['player'] in risk['players']]
        for player in risk['players']:
            if player not in players:
                issue('1', 'conflicting', 'RISK_PLAYER', risk['id'], 'Unknown affected player')
        if risk['status'] == 'disqualifying' and any(c['id'] in decision['selected'] for c in affected):
            issue('lock', 'conflicting', 'RISK_DECISION', risk['id'], 'Analyst-disqualifying risk contradicts finalized selection')
        if risk['status'] in ('open', 'disqualifying'):
            for c in affected:
                issue('1', 'analyst_review_required', 'SHARED_RISK', c['id'], risk['id'] + ': ' + risk['note'])
                if 'minutes-sensitivity' in effective(checkpoint) and risk.get('kind') == 'rotation' and not present(c.get('sensitivity')):
                    issue('3', 'analyst_review_required', 'SENSITIVITY', c['id'], 'Document credible minutes/role sensitivity where material; do not replace forecasts')
        if not present(risk['rationale']):
            issue('4', 'missing', 'RISK_CONTINUITY', risk['id'], 'Resolve, carry or disqualify with analyst rationale')
        if risk['status'] == 'resolved':
            for player in risk['players']:
                channel = 'rotation' if risk.get('kind') == 'rotation' else 'opportunities' if risk.get('kind') == 'opportunity' else None
                evidence(risk['sources'], channel, player, '1', risk['id'])

    compared = set()
    for comparison in note['comparisons']:
        a, b = candidates.get(comparison['candidate']), candidates.get(comparison['alternative'])
        if not a or not b or a['id'] == b['id'] or not present(comparison['reason']):
            issue('5', 'missing', 'COMPARISON', comparison['candidate'], 'Distinct recorded candidates and substantive analyst rationale required')
            continue
        compared.add(a['id'])
        if not a['line'] or not b['line']:
            issue('5', 'missing', 'COMPARISON_MARKETS', a['id'], 'Actual eligible thresholds needed on both sides')
    if boundary and not (boundary & compared):
        issue('5', 'missing', 'BOUNDARY_COMPARISON', 'slate', 'No recorded weakest-finalist/strongest-exclusion challenge; do not certify slate ranking')
    if boundary and not present(note['correlation']):
        issue('5', 'missing', 'CORRELATION', 'slate', 'Shared scripts/competition assessment missing')
    for candidate in decision['selected']:
        if candidate not in candidates:
            issue('lock', 'conflicting', 'DECISION_LINK', candidate, 'Selected candidate not in note')
        elif candidates[candidate]['disposition'] == 'pass' or candidates[candidate]['direction'] == 'Pass' or candidates[candidate]['grade'] in (None, 'Pass'):
            issue('lock', 'conflicting', 'DECISION_STATUS', candidate, 'Selection contradicts original assessment')
    if decision['status'] == 'finalized_selection' and (not decision['selected'] or not decision['at'] or not present(decision['reason'])):
        issue('lock', 'missing', 'FINALIZED_CLAIM', 'slate', 'Finalized declaration lacks candidates/time/rationale')
    lock = note['lock_review']
    if lock['at'] is None and decision['status'] != 'finalized_selection':
        issue('lock', 'analyst_review_required', 'LOCK_NOT_RECORDED', 'slate', 'No final-lock review recorded; research/Pass is preserved, not a completed lock')
    if decision['status'] == 'finalized_selection' or lock['at']:
        if not lock['at'] or not present(lock['note']):
            issue('lock', 'missing', 'FINAL_RECHECK', 'slate', 'Explicit final review time and rationale missing')
        for selected in decision['selected']:
            c = candidates.get(selected)
            if not c:
                continue
            for support, subject in (('market', c['player']), ('personnel', players.get(c['player'], {}).get('game', c['player']))):
                matching = [key for key in lock['sources'] if key in sources and support in sources[key]['supports'] and subject in sources[key]['subjects']]
                checked = evidence(matching, support, subject, 'lock', selected)
                if not any(s['observed_at'] and when(note['research_at']) <= when(s['observed_at']) <= when(lock['at'] or checkpoint) for s in checked):
                    issue('lock', 'missing', 'FINAL_RECHECK', selected, 'No within-session ' + support + ' observation linked to final review')
            if lock['at'] and any(s['reviewed_at'] and when(s['reviewed_at']) > when(lock['at']) for s in used_by_candidate.get(selected, [])):
                issue('lock', 'analyst_review_required', 'STALE_LOCK', selected, 'Inputs changed after final recheck')
        if lock['at'] and when(lock['at']) > cutoff:
            issue('lock', 'conflicting', 'LOCK_TIME', 'slate', 'Lock review follows decision')
    if note['placement']['status'] == 'confirmed':
        receipts = evidence(note['placement']['sources'], 'placement', note['id'], 'placement', 'slate', pregame=False)
        if not any(s['kind'] == 'observed' and s['status'] == 'recorded' for s in receipts):
            issue('placement', 'missing', 'PLACEMENT_EVIDENCE', 'slate', 'Explicit observed confirmation required; research status is not placement proof')
    states = {}
    for stage in STAGES:
        found = [i['state'] for i in issues if i['stage'] in (stage, 'authority', 'sources')]
        states[stage] = next((state for state in ('conflicting','missing','analyst_review_required') if state in found), 'recorded')
    lock_state = 'unsupported claim' if decision['status'] == 'finalized_selection' and any(i['state'] in ('missing','conflicting') and i['stage'] != 'placement' for i in issues) else 'analyst review required'
    return {'stages': states, 'issues': issues, 'calculations': lines,
            'coverage': screening, 'lock_status': lock_state,
            'checkpoints': {'research': effective(note['research_at']), 'decision': effective(checkpoint)},
            'judgment': 'Recorded means documented only. No automated analytical verification or completed-lock certification.'}


def text(value):
    result = escape(str(value)).replace('|', r'\|').replace('\n', ' ')
    for symbol in ('[',']','*','`'):
        result = result.replace(symbol, '\\' + symbol)
    return result


def render(note, result=None):
    r = result or check(note)
    lines = ['# V2.2 research checklist', '', r['judgment'], '',
             '| Stage | Record status |', '|---|---|']
    lines += [f'| {key}: {text(label)} | {r["stages"][key]} |' for key,label in STAGES.items()]
    lines += ['', '## Screening and original-input comparison', '',
              'Coverage comes from supplied DC values, not market availability. Both directions remain for analyst screening.', '',
              '| Player | Supplied DC markets |', '|---|---|']
    lines += [f'| {text(p)} | {", ".join(markets)} |' for p,markets in r['coverage'].items()]
    lines += ['', '| Candidate | Original DC @ minutes | Original DARKO / basis / minutes | Normalized DARKO | Line | Relationship | Wins | Ties |', '|---|---|---|---|---|---|---|---|']
    lines += ['| ' + ' | '.join(text(v) for v in (key,row['DC'] + ' @ ' + str(row['DC_minutes']),str(row['DARKO_original']) + ' / ' + row['DARKO_basis'] + ' / ' + str(row['DARKO_minutes']),row['DARKO_normalized'],row['line'],row['relationship'],row['wins'],row['ties'])) + ' |' for key,row in r['calculations'].items()]
    lines += ['', '## Analyst candidate assessments (unchanged inputs)', '', '| Candidate | Direction | Role / Opportunities / Matchup / Sustainability | Original grade | Rank | Research status |', '|---|---|---|---|---|---|']
    for c in note['candidates']:
        factors = ' / '.join(str(c['validation'][key]['score']) if c['validation'][key]['score'] is not None else 'unscored' for key in ('role','opportunities','matchup','sustainability'))
        lines.append('| ' + ' | '.join(text(v) for v in (c['id'],c['direction'],factors,c['grade'] or 'unrecorded',c['rank'] or 'unrecorded',c['disposition'])) + ' |')
    lines.append('')
    for c in note['candidates']:
        lines.append(f'- {text(c["id"])} outlook: {text(c["outlook"])}; failure: {text(c["failure"])}.')
    lines += ['', '## Shared unresolved risks', '']
    lines += [f'- {text(risk["id"])} [{text(risk["status"])}; {text(", ".join(risk["players"]))}]: {text(risk["note"])}; disposition: {text(risk["rationale"])}.' for risk in note['risks']] or ['No shared risks recorded; this does not prove none exist.']
    lines += ['', 'Provider settlement is separate from arithmetic. Original model inputs remain in the note/snapshot.', '',
              '## Final-lock review', '', 'Declared research status: ' + note['decision']['status'],
              'Mechanical lock assessment: **' + r['lock_status'] + '**. This never finalizes a selection.', '',
              '| Existing V2.2 lock item | Review |', '|---|---|']
    stage_for = [1,1,2,2,2,2,2,3,3,3,4,5,5,5,5,5,1]
    for (code,label), stage in zip(LOCK.items(),stage_for):
        states = [i['state'] for i in r['issues'] if i['stage'] in (str(stage),'lock','authority','sources')]
        state = next((s for s in ('conflicting','missing','analyst_review_required') if s in states), 'analyst_review_required')
        lines.append(f'| {code}: {text(label)} | {state} |')
    lines += ['', '## Material omissions and conflicts', '']
    lines += [f'- {i["state"]}: {i["code"]} [{text(i["subject"])}] — {text(i["reason"])}' for i in r['issues']] or ['No structural omissions found; substantive evidence review is still required.']
    lines += ['', '## Shared research and sources', '']
    for game, matchup in note['matchups'].items():
        lines.append(f'- {text(game)}: ' + '; '.join(f'{section}: {text(claim["note"])} ({text(", ".join(claim["sources"]))})' for section,claim in matchup.items()))
    for key,s in note['sources'].items():
        lines.append(f'- {text(key)}: {text(s["ref"])}; scope: {text(s["scope"])}; observed {text(s["observed_at"])}; cutoff {text(s.get("cutoff"))}; {text(s["status"])}.')
    lines += ['', '## Comparison rationale', '']
    lines += [f'- {text(c["candidate"])} vs {text(c["alternative"])}: {text(c["reason"])}' for c in note['comparisons']] or ['No boundary comparison recorded.']
    lines += ['', 'Effective refinements: research ' + ', '.join(r['checkpoints']['research']) + '; decision/checkpoint ' + ', '.join(r['checkpoints']['decision']),
              'Postgame notes are excluded from this pregame assessment. Frozen reports remain separate and unchanged.', '']
    return '\n'.join(lines)


def entry_metrics(note):
    """Transparent field-slot estimate, not a timed benchmark or analytical rule."""
    games, candidates, risks, comparisons = map(len, (note['matchups'],note['candidates'],note['risks'],note['comparisons']))
    conditional = sum(bool(c.get(key)) for c in note['candidates'] for key in ('disagreement','sensitivity'))
    source_rows = [encode(source) for source in note['sources'].values()]
    return {'manual_judgment_slots':7 + 3*games + 14*candidates + 4*risks + 3*comparisons + conditional,
            'breakdown':{'session':7,'matchup_notes':3*games,'candidate_judgments':14*candidates,
                         'risk_judgments':4*risks,'comparison_judgments':3*comparisons,'conditional_notes':conditional},
            'source_metadata_core_fields_per_source':8,'statistical_context_fields_if_applicable':4,'source_definitions':len(source_rows),
            'shared_matchup_definitions':games,'duplicate_source_definitions':len(source_rows)-len(set(source_rows)),
            'duplicate_matchup_definitions':0,'requirement_declarations':0,'manual_coverage_flags':0,'event_ids':0}
