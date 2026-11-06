import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ingestion.store import IngestionError, REPO, decode, digest, encode, validate
from tracker.catalog import CATALOG, FRAMEWORK_SHA, LOCK, MARKETS, REFINEMENTS
from tracker.journal import append, create, load
from tracker.review import framework_check, render, review

FIXTURE = REPO / 'tests/fixtures/synthetic/tracker-inputs.json'


class TrackerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve() / 'private'
        self.records = decode(FIXTURE.read_bytes())['records']
        self.events = []
        for r in self.records:
            self.add(r)

    def add(self, record):
        record = copy.deepcopy(record)
        if not record['basis']:
            latest = {e['record']['entity_id']: e for e in self.events}
            record['basis'] = [e['event_id'] for key, e in latest.items() if key != record['entity_id']]
        event = (create if not self.events else append)('synthetic', record, root=self.root)
        self.events.append(event)
        return event

    def codes(self):
        return {w[0] for w in review(load('synthetic', root=self.root))[0]}

    def record(self, kind):
        return copy.deepcopy(next(r for r in self.records if r['kind'] == kind))

    def test_framework_and_complete_catalog(self):
        self.assertTrue(framework_check())
        self.assertEqual(len(LOCK), 17)
        self.assertTrue({'1A','1E','2A','2F','3C','4E','5I','IV-B','V-F','VIII','IX'} <= CATALOG.keys())
        self.assertNotIn('FRAMEWORK_CONFLICT', self.codes())
        self.assertNotIn('NORMALIZATION_MISMATCH', self.codes())

    def test_framework_conflict_and_refinement_effective_dates(self):
        session = self.record('session')
        session['data'].update(research_date='2026-11-05',research_at='2026-11-05T18:24:10Z',mode='retrospective',rules_used_sha256='conflicting-historical-source')
        events = copy.deepcopy(self.events)
        events[0]['record'] = session
        codes = {w[0] for w in review(events)[0]}
        self.assertIn('FRAMEWORK_CONFLICT', codes)
        self.assertIn('REFINEMENT_NOT_APPLICABLE', codes)
        with patch('tracker.review.FRAMEWORK_SHA', '0' * 64):
            self.assertFalse(framework_check())

    def test_schema_rejects_bad_dates_unknown_fields_and_bad_scores(self):
        for field, value in [('reviewed_at','yesterday'),('unknown',1)]:
            record = self.record('candidate'); record['data'][field] = value
            with self.assertRaises(IngestionError): self.add(record)
        record = self.record('candidate'); record['data']['rubric']['role'] = 3
        with self.assertRaises(IngestionError): self.add(record)
        raw = b'{"a":1,"a":2}'
        with self.assertRaises(IngestionError): decode(raw)

    def test_originals_and_decision_versions_survive_reassessment(self):
        before = {p.name:p.read_bytes() for p in (self.root/'synthetic').iterdir()}
        decision = dict(kind='decision',entity_id='decision-one',basis=[self.events[-1]['event_id']],data=dict(status='pass',candidate_ids=['candidate-a'],rationale='Insufficient research',confirmation_evidence_ids=[],decision_at='2026-11-07T12:03:00Z',historical_reference=None))
        self.add(decision)
        changed = self.record('candidate'); changed['data']['outlook'] = 'Later independent reassessment'
        self.add(changed)
        events = load('synthetic',root=self.root)
        self.assertEqual(events[-2]['record']['data']['status'], 'pass')
        self.assertEqual(events[-2]['record']['basis'], [events[7]['event_id']])
        self.assertEqual(events[7]['record']['data']['outlook'], 'Invented example only')
        for name, raw in before.items(): self.assertEqual((self.root/'synthetic'/name).read_bytes(),raw)
        self.assertNotIn('DECISION_BASIS',self.codes())

    def test_hash_chain_and_incomplete_event_rejected(self):
        path=self.root/'synthetic'/'00000002.json'
        path.chmod(0o600); event=decode(path.read_bytes()); event['record']['data']['sample']='changed'
        path.write_bytes(encode(event))
        with self.assertRaises(IngestionError):load('synthetic',root=self.root)
        path.write_bytes(b'{')
        with self.assertRaises(IngestionError):load('synthetic',root=self.root)

    def test_permissions_symlinks_lock_and_existing_session(self):
        path=self.root/'synthetic'
        self.assertEqual((path/'00000001.json').stat().st_mode & 0o777,0o400)
        with self.assertRaises(IngestionError):create('synthetic',self.records[0],root=self.root)
        (path/'.lock').write_bytes(b'')
        with self.assertRaises(IngestionError):self.add(self.record('source'))
        (path/'.lock').unlink()
        file=path/'00000002.json'; file.unlink(); file.symlink_to(FIXTURE)
        with self.assertRaises(IngestionError):load('synthetic',root=self.root)
        with self.assertRaises(IngestionError):create('../escape',self.records[0],root=self.root)

    def test_failed_append_cleanup_and_retry(self):
        before=load('synthetic',root=self.root)
        with patch('tracker.journal.os.fsync',side_effect=OSError('injected')):
            with self.assertRaises(OSError):self.add(self.record('source'))
        self.assertEqual(before,load('synthetic',root=self.root))
        self.add(self.record('source'))
        self.assertEqual(len(before)+1,len(load('synthetic',root=self.root)))

    def test_missing_checkers_fail_closed(self):
        from jsonschema import FormatChecker
        with patch.object(FormatChecker,'checkers',{}):
            with self.assertRaises(IngestionError):load('synthetic',root=self.root)

    def test_coverage_keeps_independent_disagreement_candidates(self):
        for market in MARKETS:
            self.add(dict(kind='coverage',entity_id='coverage-'+market,basis=[],data=dict(player='SYN_A',market=market,higher_reviewed=True,lower_reviewed=True,market_status='not_recovered',opportunity_evidence_ids=['evidence-a'],advance_reasons=['independent_opportunity'],disagreement_investigation='Investigate near-line disagreement; do not automatically reject',disposition='investigate',rationale='Synthetic independently supported channel')))
        self.assertNotIn('COVERAGE',self.codes())
        self.assertIn('MARKET_COVERAGE',self.codes())
        self.assertEqual(len([e for e in load('synthetic',root=self.root) if e['record']['kind']=='coverage']),8)

    def test_normalization_per_minute_invalid_and_incompatible(self):
        record=self.record('calculation'); record['data']['result']=8.1
        self.add(record);self.assertIn('NORMALIZATION_MISMATCH',self.codes())
        self.add(self.record('calculation'))
        darko=copy.deepcopy(self.records[4]);darko['data'].update(value=0.25,basis='per_minute',minutes=None)
        self.add(darko);self.assertNotIn('NORMALIZATION_MISMATCH',self.codes())
        darko['data']['unit']='different';self.add(darko)
        self.assertIn('CALCULATION',self.codes())

    def test_combined_normalizes_components_and_rejects_cycle(self):
        for suffix,market in [('p','PTS'),('r','REB')]:
            for base in (self.records[3],self.records[4]):
                record=copy.deepcopy(base);record['entity_id'] += suffix;record['data']['market']=market;record['data']['unit']=market;self.add(record)
            calc=self.record('calculation');calc['entity_id']+=suffix;calc['data'].update(dc_id='dc-a'+suffix,darko_id='darko-a'+suffix);self.add(calc)
        dc=self.record('model');dc['entity_id']='dc-pr';dc['data'].update(market='PR',unit='PR',value=16);self.add(dc)
        calc=self.record('calculation');calc['entity_id']='calc-pr';calc['data'].update(dc_id='dc-pr',darko_id=None,component_ids=['calc-ap','calc-ar'],result=16);self.add(calc)
        self.assertNotIn('CALCULATION',self.codes())
        calc['data']['component_ids']=['calc-pr','calc-ar'];self.add(calc)
        self.assertIn('CALCULATION',self.codes())

    def test_unsupported_verified_source_metadata_and_missing_links(self):
        evidence=self.record('evidence');evidence['data'].update(source_ids=[],verification_scope=None);self.add(evidence)
        source=self.record('source');source['data']['cutoff']=None;self.add(source)
        self.assertTrue({'UNSUPPORTED_VERIFIED','UNSUPPORTED_EVIDENCE','SOURCE_METADATA'} <= self.codes())
        candidate=self.record('candidate');candidate['data'].update(dc_id='missing',opportunity_evidence_ids=[]);self.add(candidate)
        self.assertTrue({'MISSING_LINK','OPPORTUNITY_GAP'}<=self.codes())

    def test_shared_risk_continuity_and_staleness(self):
        risk=dict(kind='uncertainty',entity_id='rotation',basis=[],data=dict(issue='Invented shared rotation',candidate_ids=['candidate-a'],evidence_ids=[],status='open',rationale='Requires review'))
        self.add(risk);self.assertIn('RISK_CONTINUITY',self.codes())
        candidate=self.record('candidate');candidate['data']['uncertainty_ids']=['rotation'];self.add(candidate)
        self.assertNotIn('RISK_CONTINUITY',self.codes())
        risk['data']['status']='carried';self.add(risk)
        self.assertTrue({'STALE_ASSESSMENT','OPEN_RISK'}<=self.codes())

    def test_comparison_incomplete_and_finalization_does_not_imply_placement(self):
        c=self.record('candidate');c['entity_id']='candidate-b';self.add(c)
        comparison=dict(kind='comparison',entity_id='challenge',basis=[],data=dict(finalist_id='candidate-a',exclusion_id='candidate-b',fields={k:None for k in ('availability','models','rubric','opportunities','minutes_risks','market_value','user_constraints','coverage')},outcome='investigate',rationale='Not completed',reviewed_at=None))
        self.add(comparison);self.assertIn('COMPARISON_INCOMPLETE',self.codes())
        decision=dict(kind='decision',entity_id='selection',basis=[],data=dict(status='finalized_selection',candidate_ids=['candidate-a'],rationale='Analyst input, not system decision',confirmation_evidence_ids=[],decision_at='2026-11-07T12:03:00Z',historical_reference=None))
        self.add(decision);self.assertIn('LOCK_INCOMPLETE',self.codes())
        self.assertNotIn('confirmed_wager',render(load('synthetic',root=self.root)))
        decision['entity_id']='placement';decision['data']['status']='confirmed_wager';self.add(decision)
        self.assertIn('MISSING_EVIDENCE',self.codes())

    def test_grade_is_preserved_not_assigned(self):
        c=self.record('candidate');c['data']['grade']='A';c['data']['rubric']={k:1 for k in c['data']['rubric']};self.add(c)
        self.assertIn('GRADE_ELIGIBILITY',self.codes())
        self.assertEqual(load('synthetic',root=self.root)[-1]['record']['data']['grade'],'A')

    def test_deterministic_report_incomplete_is_not_met(self):
        events=load('synthetic',root=self.root)
        self.assertEqual(render(events),render(events))
        self.assertIn('L17: Material personnel',render(events))
        self.assertIn('unassessed',render(events))
        self.assertIn('RUBRIC_OPEN',render(events))
        self.assertIn('Original grade',render(events))

    def test_cli_private_report_and_safe_error(self):
        env=dict(os.environ,PYTHONPATH=str(REPO/'src'),NBA_PRIVATE_DATA_ROOT=str(self.root))
        result=subprocess.run([sys.executable,'-m','tracker','report','synthetic'],env=env,capture_output=True,text=True)
        self.assertEqual(result.returncode,2,result.stderr)
        self.assertNotIn(str(self.root),result.stdout+result.stderr)
        reports=list((self.root/'tracker-reports').glob('*.md'));self.assertEqual(len(reports),1)
        self.assertIn('# V2.2',reports[0].read_text())
        bad=subprocess.run([sys.executable,'-m','tracker','check','missing'],env=env,capture_output=True,text=True)
        self.assertEqual(bad.returncode,1);self.assertNotIn(str(self.root),bad.stderr)

    def test_compliance_separates_eligibility_evidence_and_judgment(self):
        from tracker.review import compliance
        c=self.record('candidate');c['data']['grade']='A';c['data']['rubric']={k:1 for k in c['data']['rubric']};self.add(c)
        other=self.record('candidate');other['entity_id']='incomplete-candidate';self.add(other)
        report=compliance(load('synthetic',root=self.root))
        self.assertTrue(any(f['code']=='GRADE_ELIGIBILITY' and f['severity']=='hard_violation' for f in report['findings']))
        self.assertTrue(any(f['code']=='RUBRIC_OPEN' and f['severity']=='incomplete_evidence' for f in report['findings']))
        self.assertTrue(all('Analyst' in row['judgment'] for row in report['requirements']))
        r=dict(kind='requirement',entity_id='false-completion',basis=[],data=dict(scope='slate',code='3A-opportunities',status='met',evidence_ids=[],rationale='Unsupported assertion for test',reviewed_at='2026-11-07T12:03:00Z'))
        self.add(r)
        row=next(r for r in compliance(load('synthetic',root=self.root))['requirements'] if r['scope']=='slate' and r['code']=='3A-opportunities')
        self.assertFalse(row['completion_supported'])
        self.assertIn('Completion claim has no evidence links',row['concerns'])

    def test_exact_threshold_neutral_disagreement_and_direction(self):
        c=self.record('candidate');c['data'].update(grade='A',rubric={k:2 for k in c['data']['rubric']});self.add(c)
        self.assertNotIn('GRADE_ELIGIBILITY',self.codes())
        market=self.record('market');market['data']['line']=8;self.add(market)
        self.assertIn('GRADE_ELIGIBILITY',self.codes())
        market['data']['line']=9;self.add(market)
        self.assertIn('GRADE_ELIGIBILITY',self.codes())  # Agree Lower does not support an A Higher.
        market['data']['line']=7;self.add(market)
        darko=copy.deepcopy(self.records[4]);darko['data']['value']=4.5;self.add(darko)
        calc=self.record('calculation');calc['data']['result']=6;self.add(calc)
        self.assertIn('DISAGREEMENT_CEILING',self.codes())
        c['data'].update(grade='B+',rubric={k:1 for k in c['data']['rubric']});self.add(c)
        self.assertIn('GRADE_ELIGIBILITY',self.codes())

    def test_intake_approval_provenance_and_intraday_refinements(self):
        from tracker.review import compliance
        events=copy.deepcopy(self.events)
        d=events[0]['record']['data']
        d.update(approval_reference='unapproved-suggestion',research_date='2026-11-05',research_at='2026-11-05T17:00:00Z',refinement_ids=['standard-only'],refinement_approvals={'standard-only':'not-an-approval'})
        codes={f['code'] for f in compliance(events)['findings']}
        self.assertTrue({'APPROVAL_PROVENANCE','REFINEMENT_PROVENANCE','REFINEMENT_NOT_APPLICABLE'}<=codes)
        d['research_at']=None
        self.assertIn('APPLICABILITY_TIME',{f['code'] for f in compliance(events)['findings']})

    def test_historical_checkpoint_does_not_use_later_assessment(self):
        from tracker.journal import at_event
        before=load('synthetic',root=self.root)
        original_id=before[-1]['event_id']
        c=self.record('candidate');c['data']['grade']='A';c['data']['rubric']={k:1 for k in c['data']['rubric']};self.add(c)
        frozen=at_event(load('synthetic',root=self.root),original_id)
        self.assertEqual(frozen,before)
        self.assertNotIn('GRADE_ELIGIBILITY',{w[0] for w in review(frozen)[0]})
        with self.assertRaises(IngestionError):at_event(before,'missing')

    def test_reference_market_only_hard_violation_if_ranked_or_selected(self):
        market=self.record('market');market['data']['tier']='goblin';self.add(market)
        self.assertIn('REFERENCE_MARKET',self.codes())
        self.assertNotIn('MARKET_INELIGIBLE',self.codes())
        c=self.record('candidate');c['data']['rank']=1;self.add(c)
        self.assertIn('MARKET_INELIGIBLE',self.codes())

    def test_coverage_seed_is_idempotent_and_does_not_decide(self):
        from tracker.coverage import seed_coverage
        self.assertEqual(seed_coverage('synthetic',root=self.root),8)
        before=load('synthetic',root=self.root)
        self.assertEqual(seed_coverage('synthetic',root=self.root),0)
        self.assertEqual(before,load('synthetic',root=self.root))
        for e in before:
            if e['record']['kind']=='coverage':
                d=e['record']['data']
                self.assertEqual(d['disposition'],'not_started')
                self.assertFalse(d['higher_reviewed']);self.assertFalse(d['lower_reviewed'])
        self.assertIn('DIRECTION_COVERAGE',self.codes())

    def test_documented_carried_risk_does_not_create_new_eligibility_rule(self):
        from tracker.review import compliance
        risk=dict(kind='uncertainty',entity_id='rotation',basis=[self.events[2]['event_id']],data=dict(issue='Invented uncertainty',candidate_ids=['candidate-a'],evidence_ids=['evidence-a'],status='carried',rationale='Analyst explicitly carries risk, not disqualifying'))
        self.add(risk)
        c=self.record('candidate');c['data']['uncertainty_ids']=['rotation'];self.add(c)
        self.add(dict(kind='requirement',entity_id='continuity',basis=[],data=dict(scope='slate',code='4C',status='met',evidence_ids=['evidence-a'],rationale='All linked concerns carried explicitly',reviewed_at='2026-11-07T12:03:00Z')))
        row=next(r for r in compliance(load('synthetic',root=self.root))['requirements'] if r['scope']=='slate' and r['code']=='4C')
        self.assertTrue(row['completion_supported'],row['concerns'])
        self.assertIn('OPEN_RISK',self.codes())

    def test_exact_line_report_has_win_tie_counts_without_probabilities(self):
        from tracker.review import compare_at_line, compliance
        self.assertEqual(compare_at_line(4.8,4.2,4,'Higher')['wins'],'5 or more')
        self.assertEqual(compare_at_line(8.7,9.2,10,'Lower')['wins'],'9 or fewer')
        self.assertEqual(compare_at_line(6,7,6,'Higher')['relationship'],'Unresolved')
        row=compliance(load('synthetic',root=self.root))['exact_lines'][0]
        self.assertEqual(row['relationship'],'Agree Higher')
        self.assertEqual(row['ties'],'7')
        self.assertIn('provider settlement',render(load('synthetic',root=self.root)))

    def test_verified_claim_with_dangling_source_is_unsupported(self):
        e=self.record('evidence');e['data']['source_ids']=['missing-source'];self.add(e)
        self.assertIn('UNSUPPORTED_VERIFIED',self.codes())
        self.assertIn('UNSUPPORTED_EVIDENCE',self.codes())

    def test_public_guard_allows_only_named_skill_and_blocks_reports(self):
        from ingestion.public_guard import allowed
        self.assertTrue(allowed('.agents/skills/nba-v22-research/SKILL.md',b'Synthetic workflow guidance'))
        self.assertFalse(allowed('.agents/skills/other/SKILL.md',b'x'))
        self.assertFalse(allowed('docs/Tracker-Reports/checklist.md',b'x'))
        self.assertFalse(allowed('docs/Research-Records/note.txt',b'x'))

    def test_missing_grade_inputs_are_incomplete_not_a_new_hard_ceiling(self):
        from tracker.review import compliance
        c=self.record('candidate');c['data'].update(grade='A',dc_id=None,calculation_id=None)
        self.add(c)
        findings=[f for f in compliance(load('synthetic',root=self.root))['findings'] if f['entity']=='candidate-a']
        self.assertTrue(any(f['code']=='GRADE_SUPPORT_INCOMPLETE' and f['severity']=='incomplete_evidence' for f in findings))
        self.assertFalse(any(f['code']=='GRADE_ELIGIBILITY' for f in findings))

    def test_all_evidence_statuses_are_visible_and_preserved(self):
        from tracker.review import compliance
        for status in ('incomplete','unavailable','conflicting'):
            e=self.record('evidence');e['data']['status']=status;self.add(e)
            result=compliance(load('synthetic',root=self.root))
            self.assertTrue(any(f['code']=='EVIDENCE_'+status.upper() for f in result['findings']))
            self.assertEqual(result['latest']['evidence-a']['record']['data']['status'],status)

    def test_dpm_cannot_be_normalized_as_boxscore_production(self):
        for base in (self.records[3],self.records[4]):
            record=copy.deepcopy(base);record['data']['unit']='DPM';self.add(record)
        self.assertIn('CALCULATION',self.codes())
