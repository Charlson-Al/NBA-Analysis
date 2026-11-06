"""Simplicity-first regressions, including the six PR #2 review defects."""
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
from tracker.calculations import exact_line, normalize
from tracker.review import check, effective, render
from tracker.storage import assess, freeze, read_note, report, snapshot

FIXTURE = REPO / 'tests/fixtures/synthetic/research-note.json'


class TrackerTests(unittest.TestCase):
    def setUp(self):
        self.note = decode(FIXTURE.read_bytes())
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve() / 'private'
        self.root.mkdir(mode=0o700)
        self.path = self.root / 'session.json'
        self.save()

    def save(self):
        self.path.write_bytes(encode(self.note)); self.path.chmod(0o600)

    def codes(self):
        return {i['code'] for i in check(self.note)['issues']}

    def finalized(self):
        self.note['decision'].update(status='finalized_selection',at='2026-11-07T12:06:00Z',selected=['A-AST'],reason='Invented analyst declaration only')

    def test_M1_unsupported_lock_and_blanket_na_cannot_pass(self):
        self.finalized()
        self.note['comparisons'] = []
        self.note['lock_review'] = dict(at=None,sources=[],note=None)
        self.note['candidates'][0]['validation']['opportunities']['sources'] = []
        r=check(self.note)
        self.assertEqual(r['lock_status'],'unsupported claim')
        self.assertTrue({'EVIDENCE','BOUNDARY_COMPARISON','FINAL_RECHECK'}<=self.codes())
        self.note['lock_review']['status']='not_applicable'
        with self.assertRaises(IngestionError): check(self.note)

    def test_M1_irrelevant_evidence_and_field_population_never_certifies(self):
        self.note['sources']['S4']['subjects']=['SYN_B']
        self.assertIn('IRRELEVANT_EVIDENCE',self.codes())
        self.note['sources']['S4']['subjects']=['SYN_A','SYN_B']
        self.note['sources']['S4']['kind']='forecast'
        self.assertIn('OWNERSHIP',self.codes())
        clean=decode(FIXTURE.read_bytes());r=check(clean)
        self.assertEqual(r['issues'],[])
        self.assertEqual(r['lock_status'],'analyst review required')
        self.assertNotIn('completion_supported',r)
        self.assertIn('No automated analytical verification',render(clean))

    def test_M2_actual_decision_checkpoint_controls_refinements(self):
        self.note.update(research_at='2026-11-05T17:00:00Z')
        self.note['authority']['refinements']=[]
        self.finalized()
        self.note['candidates'][0]['line']['tier']='goblin'
        self.assertTrue({'AUTHORITY','MARKET_ELIGIBILITY'}<=self.codes())
        self.assertEqual(effective('2026-11-05T17:00:00Z'),[])
        self.assertEqual(effective('2026-11-05T18:10:00Z'),['standard-only'])
        self.assertEqual(len(effective('2026-11-06T14:09:00Z')),4)

    def test_M2_postdecision_evidence_and_stale_market_recheck(self):
        self.finalized()
        self.note['sources']['S4']['reviewed_at']='2026-11-08T12:00:00Z'
        self.note['sources']['S6']['observed_at']='2026-10-01T00:00:00Z'
        self.assertTrue({'LATE_EVIDENCE','STALE_ASSESSMENT','FINAL_RECHECK'}<=self.codes())
        self.assertEqual(check(self.note)['lock_status'],'unsupported claim')

    def test_M3_single_note_has_no_unrelated_event_binding_bypass(self):
        self.note['candidates'][0]['validation']['opportunities']['sources']=['missing']
        self.assertIn('SOURCE_LINK',self.codes())
        self.note['basis']=['arbitrary-valid-event']
        with self.assertRaises(IngestionError):check(self.note)

    def test_M3_source_bytes_and_later_inputs_invalidate_current_assessment(self):
        source=self.root/'source.bin';source.write_bytes(b'original invented inputs');source.chmod(0o600)
        self.note['sources']['S2'].update(file='source.bin',sha256=digest(source.read_bytes()))
        self.save();self.assertNotIn('SOURCE_FILE',{i['code'] for i in assess(self.root,'session.json')[1]['issues']})
        source.write_bytes(b'changed')
        self.assertIn('SOURCE_FILE',{i['code'] for i in assess(self.root,'session.json')[1]['issues']})
        with self.assertRaises(IngestionError):freeze(self.root,'session.json','bad-originals')
        self.note['sources']['S2']['reviewed_at']='2026-11-07T12:04:30Z'
        self.assertIn('STALE_ASSESSMENT',self.codes())

    def test_M4_frozen_grade_findings_survive_later_reassessment(self):
        self.note['projections'][1]['values']['AST']=4.5
        self.note['candidates'][0]['grade']='A'
        self.finalized();self.save()
        self.assertIn('GRADE_ELIGIBILITY',self.codes())
        freeze(self.root,'session.json','original')
        old_manifest,old_report=snapshot(self.root,self.note['id'],'original')
        original_bytes=self.path.read_bytes()
        self.note['candidates'][0]['grade']='C';self.note['candidates'][0]['validation']={k:dict(score=1,note=v['note'],sources=v['sources']) for k,v in self.note['candidates'][0]['validation'].items()}
        self.save()
        self.assertNotIn('GRADE_ELIGIBILITY',self.codes())
        new_manifest,new_report=snapshot(self.root,self.note['id'],'original')
        self.assertEqual(old_manifest,new_manifest);self.assertEqual(old_report,new_report)
        self.assertEqual((self.root/'pregame-snapshots'/self.note['id']/'original'/'note.json').read_bytes(),original_bytes)
        self.assertIn('GRADE_ELIGIBILITY',report(self.root,'session.json').split('## Frozen history')[1])

    def test_M5_one_canonical_normalization_at_exact_line(self):
        d=self.note['projections'][1]
        value=normalize(d,32,'AST')
        self.assertEqual(str(value),'8')
        self.assertEqual(exact_line(9,value,8,'Higher')['relationship'],'Unresolved')
        self.note['candidates'][0]['normalized']=8.0000000005
        with self.assertRaises(IngestionError):check(self.note)
        self.assertEqual(exact_line(8,8,7,'Higher')['wins'],'8+')
        self.assertEqual(exact_line(8,8,10,'Lower')['wins'],'9 or fewer')

    def test_M6_screening_is_independent_of_market_availability_and_postgame(self):
        self.note['candidates']=[];self.note['comparisons']=[]
        r=check(self.note)
        self.assertEqual(r['stages']['2'],'recorded')
        self.assertEqual(len(r['coverage']['SYN_A']),8)
        self.assertEqual(len(r['stages']),5)
        self.assertNotIn('V-A',render(self.note))
        self.assertNotIn('requirements',self.note)

    def test_normalization_components_basis_and_input_preservation(self):
        original=copy.deepcopy(self.note)
        d=self.note['projections'][1]
        self.assertEqual(normalize(d,32,'PRA'),36)
        d['basis']='per_minute';d['values']['AST']=.25;d['minutes']=None
        self.assertEqual(normalize(d,32,'AST'),8)
        d['basis']='per_game'
        with self.assertRaises(ValueError):normalize(d,32,'AST')
        with self.assertRaises(ValueError):normalize(original['projections'][1],None,'AST')
        raw=encode(original);check(original);self.assertEqual(raw,encode(original))

    def test_model_disagreement_stays_in_research_and_grade_limits_unchanged(self):
        self.note['projections'][1]['values']['AST']=4.5
        self.note['candidates'][0]['grade']='B'
        self.assertIn('DISAGREEMENT',self.codes())
        self.assertNotIn('GRADE_LIMIT',self.codes())
        self.note['candidates'][0]['grade']='A'
        self.assertTrue({'GRADE_LIMIT','GRADE_ELIGIBILITY'}<=self.codes())
        self.assertEqual(self.note['candidates'][0]['grade'],'A')
        self.assertEqual(self.note['candidates'][0]['disposition'],'research')

    def test_shared_risk_applies_without_duplicate_candidate_links(self):
        self.note['risks'][0].update(kind='rotation',status='open')
        self.assertTrue({'SHARED_RISK','SENSITIVITY'}<=self.codes())
        self.note['risks'][0]['status']='carried'
        self.assertNotIn('SHARED_RISK',self.codes())
        self.finalized();self.note['risks'][0]['status']='disqualifying'
        self.assertIn('RISK_DECISION',self.codes())

    def test_postgame_separate_and_cannot_support_pregame(self):
        before=check(self.note)
        self.note['postgame']={'actuals':'Invented outcome only'}
        self.assertEqual(before,check(self.note))
        self.note['sources']['POST']={**self.note['sources']['S4'],'phase':'postgame'}
        self.note['candidates'][0]['validation']['opportunities']['sources']=['POST']
        self.assertIn('POSTGAME_SUPPORT',self.codes())
        self.save()
        with self.assertRaises(IngestionError):freeze(self.root,'session.json','mixed')

    def test_snapshots_exclusive_tamper_detection_and_raw_source_copy(self):
        source=self.root/'source.bin';source.write_bytes(b'original synthetic data');source.chmod(0o600)
        self.note['sources']['S2'].update(file='source.bin',sha256=digest(source.read_bytes()));self.save()
        path=freeze(self.root,'session.json','pregame')
        self.assertEqual((path/'source-S2.bin').read_bytes(),source.read_bytes())
        with self.assertRaises(IngestionError):freeze(self.root,'session.json','pregame')
        self.assertEqual(path.stat().st_mode&0o777,0o500)
        f=path/'note.json';self.assertEqual(f.stat().st_mode&0o777,0o400)
        f.chmod(0o600);f.write_bytes(b'{}')
        with self.assertRaises(IngestionError):snapshot(self.root,self.note['id'],'pregame')

    def test_private_roots_symlinks_and_interrupted_writes(self):
        with self.assertRaises(IngestionError):read_note(REPO,'README.md')
        self.path.unlink();self.path.symlink_to(FIXTURE)
        with self.assertRaises(IngestionError):read_note(self.root,'session.json')
        self.path.unlink();self.save()
        with patch('tracker.storage.os.fsync',side_effect=OSError('injected')):
            with self.assertRaises(OSError):freeze(self.root,'session.json','interrupted')
        self.assertFalse((self.root/'pregame-snapshots'/self.note['id']/'interrupted').exists())
        freeze(self.root,'session.json','interrupted')

    def test_strict_schema_no_scoring_or_unavailable_validators(self):
        from jsonschema import FormatChecker
        with patch.object(FormatChecker,'checkers',{}):
            with self.assertRaises(IngestionError):check(self.note)
        for field,value in [('research_at','yesterday'),('new_factor',1)]:
            n=copy.deepcopy(self.note);n[field]=value
            with self.assertRaises(IngestionError):check(n)
        n=copy.deepcopy(self.note);n['projections'][1]['values']['DPM']=3
        with self.assertRaises(IngestionError):check(n)
        n=copy.deepcopy(self.note);n['candidates'][0]['validation']['role']['score']=3
        with self.assertRaises(IngestionError):check(n)

    def test_cli_example_report_and_freeze(self):
        env=dict(os.environ,PYTHONPATH=str(REPO/'src'),NBA_PRIVATE_DATA_ROOT=str(self.root))
        def run(*args):return subprocess.run([sys.executable,'-m','tracker',*args],env=env,capture_output=True,text=True)
        self.assertEqual(run('example','demo').returncode,0)
        self.assertEqual(run('check','demo.json').returncode,0)
        result=run('report','demo.json');self.assertEqual(result.returncode,0)
        self.assertIn('analyst review required',result.stdout)
        self.assertEqual(run('freeze','demo.json','before-tip').returncode,0)
        self.assertIn('V2.2 research checklist',run('snapshot','demo','before-tip').stdout)
        self.assertEqual(run('freeze','demo.json','before-tip').returncode,1)
        self.assertEqual(run('new','blank').returncode,0)
        self.assertEqual(run('check','blank.json').returncode,2)
        self.assertNotIn(str(self.root),run('check','missing.json').stderr)

    def test_duplicate_models_do_not_choose_a_forecast(self):
        other=copy.deepcopy(self.note['projections'][0]);other['values']['AST']=100
        self.note['projections'].append(other)
        result=check(self.note)
        self.assertIn('DUPLICATE_MODEL',{i['code'] for i in result['issues']})
        self.assertNotIn('A-AST',result['calculations'])
        self.assertEqual(self.note['projections'][0]['values']['AST'],8)

    def test_placeholders_and_forecast_only_opportunities_do_not_satisfy_lock(self):
        self.finalized()
        self.note['comparisons'][0]['reason']='N/A'
        self.note['lock_review']['note']='not applicable'
        self.note['sources']['S4']['kind']='forecast'
        self.assertTrue({'COMPARISON','FINAL_RECHECK','INDEPENDENT_OPPORTUNITIES'}<=self.codes())
        self.assertEqual(check(self.note)['lock_status'],'unsupported claim')

    def test_source_context_and_placement_remain_separate(self):
        self.note['sources']['S4']['cutoff']='2026-11-08'
        self.assertIn('FUTURE_CUTOFF',self.codes())
        self.note['placement']['status']='confirmed'
        self.assertIn('EVIDENCE',self.codes())
        self.assertEqual(self.note['decision']['status'],'research')
        self.note['sources']['S4']['cutoff']=None
        self.assertIn('SOURCE_CONTEXT',self.codes())

    def test_entry_metrics_have_no_administrative_duplicates(self):
        from tracker.review import entry_metrics
        m=entry_metrics(self.note)
        self.assertEqual(m['manual_judgment_slots'],45)
        self.assertEqual(m['requirement_declarations'],0)
        self.assertEqual(m['manual_coverage_flags'],0)
        self.assertEqual(m['event_ids'],0)
        self.assertEqual(m['duplicate_source_definitions'],0)
        self.assertEqual(m['shared_matchup_definitions'],1)

    def test_original_zero_minutes_and_negative_values_are_not_overwritten(self):
        self.note['projections'][1]['minutes']=0
        self.note['projections'][0]['values']['AST']=-.1
        raw=encode(self.note)
        self.assertTrue({'NORMALIZATION','ORIGINAL_INPUT'}<=self.codes())
        self.assertEqual(raw,encode(self.note))

    def test_lowercase_rfc3339_and_cutoff_offsets(self):
        self.note['research_at']='2026-11-07t12:00:00z'
        self.note['sources']['S4']['cutoff']='2026-11-08T00:00:00+14:00'
        self.assertNotIn('FUTURE_CUTOFF',self.codes())
        self.note['sources']['S4']['cutoff']='2026-11-08t12:00:00z'
        self.assertIn('FUTURE_CUTOFF',self.codes())

    def test_authority_conflicts_and_unapproved_refinements_are_detected(self):
        self.note['authority'].update(rules_used_sha256='historical-conflict',approval_reference='assistant-proposal',refinements=['not-approved'])
        self.assertIn('AUTHORITY',self.codes())
        self.assertEqual(self.note['authority']['rules_used_sha256'],'historical-conflict')
        with patch('tracker.review.FRAMEWORK_SHA','0'*64):
            self.assertTrue(any('Pinned authority bytes' in i['reason'] for i in check(self.note)['issues']))

    def test_later_placement_confirmation_does_not_rewrite_analysis(self):
        self.finalized()
        self.note['sources']['RECEIPT']=dict(ref='urn:synthetic:receipt',observed_at='2026-11-08T12:00:00Z',reviewed_at='2026-11-08T12:01:00Z',kind='observed',subjects=[self.note['id']],supports=['placement'],status='recorded',scope='Invented explicit entry confirmation only; not pregame evidence',phase='postgame')
        self.note['placement']=dict(status='confirmed',sources=['RECEIPT'])
        r=check(self.note)
        self.assertFalse(any(i['stage']=='placement' for i in r['issues']))
        self.assertNotIn('LATE_EVIDENCE',self.codes())
        self.assertEqual(self.note['decision']['status'],'finalized_selection')
        self.save()
        with self.assertRaises(IngestionError):freeze(self.root,'session.json','postgame-confirmation')

    def test_decision_consistency_valid_research_pass_and_finalized(self):
        for status in ('research', 'pass', 'finalized_selection'):
            with self.subTest(status=status):
                self.note['decision']['status'] = status
                if status == 'finalized_selection':
                    self.finalized()
                before = encode(self.note)
                result = check(self.note)
                self.assertFalse(any(i['code'] in ('DECISION_STATUS', 'DUPLICATE_SELECTION') for i in result['issues']))
                self.assertEqual(before, encode(self.note))
                self.assertEqual(result['lock_status'], 'analyst review required')

    def test_decision_contradictions_preserve_original_declarations(self):
        original = copy.deepcopy(self.note)
        cases = [('slate', 'research'), ('slate', 'pass'), ('disposition', 'excluded'),
                 ('disposition', 'pass'), ('direction', 'Pass'), ('grade', 'Pass'), ('grade', None)]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                self.note = copy.deepcopy(original)
                self.finalized()
                if field == 'slate':
                    self.note['decision']['status'] = value
                else:
                    self.note['candidates'][0][field] = value
                before = encode(self.note)
                result = check(self.note)
                self.assertIn('DECISION_STATUS', {i['code'] for i in result['issues']})
                if field != 'slate':
                    self.assertEqual(result['lock_status'], 'unsupported claim')
                self.assertEqual(before, encode(self.note))

    def test_duplicate_selections_are_reported_without_deduplication(self):
        self.finalized()
        self.note['decision']['selected'].append('A-AST')
        before = encode(self.note)
        self.assertIn('DUPLICATE_SELECTION', self.codes())
        self.assertEqual(check(self.note)['lock_status'], 'unsupported claim')
        self.assertEqual(before, encode(self.note))

    def test_frozen_status_conflict_survives_working_correction(self):
        self.finalized()
        self.note['candidates'][0]['disposition'] = 'excluded'
        self.save()
        path = freeze(self.root, 'session.json', 'original-status')
        original = {p.name: p.read_bytes() for p in path.iterdir()}
        manifest, output = snapshot(self.root, self.note['id'], 'original-status')
        self.assertIn('DECISION_STATUS', output)
        self.note['candidates'][0]['disposition'] = 'research'
        self.save()
        self.assertNotIn('DECISION_STATUS', self.codes())
        self.assertEqual((manifest, output), snapshot(self.root, self.note['id'], 'original-status'))
        self.assertEqual(original, {p.name: p.read_bytes() for p in path.iterdir()})
        self.assertIn('DECISION_STATUS', report(self.root, 'session.json').split('## Frozen history')[1])

    def test_observed_market_and_current_recheck_are_accepted(self):
        self.finalized()
        self.assertEqual(check(self.note)['issues'], [])
        # An older reference can be observed, but final review needs a fresh observation.
        self.note['sources']['OLD'] = {**self.note['sources']['S6'],
            'observed_at': '2026-11-06T12:00:00Z', 'reviewed_at': '2026-11-06T12:01:00Z'}
        self.note['candidates'][0]['line']['source'] = 'OLD'
        self.assertNotIn('MARKET_OBSERVATION', self.codes())
        self.assertNotIn('FINAL_RECHECK', self.codes())
        self.assertEqual(check(self.note)['lock_status'], 'analyst review required')

    def test_forecast_inference_and_annotations_do_not_prove_market_availability(self):
        self.finalized()
        for kind in ('forecast', 'inference', 'historical_annotation'):
            with self.subTest(kind=kind):
                self.note['sources']['S6']['kind'] = kind
                before = encode(self.note)
                result = check(self.note)
                self.assertTrue({'MARKET_OBSERVATION', 'FINAL_RECHECK'} <= {i['code'] for i in result['issues']})
                self.assertEqual(result['lock_status'], 'unsupported claim')
                self.assertEqual(len(result['coverage']['SYN_A']), 8)
                self.assertIn('A-AST', result['calculations'])  # Reference-line arithmetic is retained.
                self.assertEqual(before, encode(self.note))

    def test_market_scope_status_and_observation_timing_are_required(self):
        self.finalized()
        original = copy.deepcopy(self.note)
        cases = [('supports', ['model']), ('subjects', ['unrelated-player']),
                 ('phase', 'postgame'), ('status', 'missing'), ('observed_at', None),
                 ('reviewed_at', None), ('observed_at', '2026-11-07T12:07:00Z'),
                 ('reviewed_at', '2026-11-07T12:07:00Z')]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                self.note = copy.deepcopy(original)
                self.note['sources']['S6'][field] = value
                result = check(self.note)
                self.assertIn('MARKET_OBSERVATION', {i['code'] for i in result['issues']})
                self.assertEqual(result['lock_status'], 'unsupported claim')
        # Correctly observed line does not let a different invalid recheck source pass.
        for changes in ({'kind': 'forecast'}, {'supports': ['model']}, {'subjects': ['other']},
                        {'observed_at': '2026-10-01T12:00:00Z'},
                        {'observed_at': '2026-11-07T12:05:30Z', 'reviewed_at': '2026-11-07T12:05:30Z'}):
            with self.subTest(recheck=changes):
                self.note = copy.deepcopy(original)
                self.note['sources']['FINAL'] = {**self.note['sources']['S6'], **changes}
                self.note['lock_review']['sources'] = ['S1', 'FINAL']
                result = check(self.note)
                self.assertNotIn('MARKET_OBSERVATION', {i['code'] for i in result['issues']})
                self.assertIn('FINAL_RECHECK', {i['code'] for i in result['issues']})
                self.assertEqual(result['lock_status'], 'unsupported claim')

    def test_normalization_compatible_source_basis_preserves_canonical_results(self):
        original = copy.deepcopy(self.note)
        for basis, denominator, unit in (('per_game', 'per_game', 'count'),
                ('per_game', 'PER-GAME', 'counts per game'),
                ('per_minute', 'per_minute', 'count'), ('per_minute', 'per minute', 'count/minute')):
            with self.subTest(basis=basis, denominator=denominator, unit=unit):
                self.note = copy.deepcopy(original)
                for d in self.note['projections']:
                    if d['provider'] == 'DARKO':
                        d['basis'] = basis
                        if basis == 'per_minute':
                            d['values'] = {k: v / 24 for k, v in d['values'].items()}
                            d['minutes'] = None
                self.note['sources']['S3'].update(denominator=denominator, unit=unit)
                before = encode(self.note)
                result = check(self.note)
                self.assertNotIn('NORMALIZATION_UNITS', {i['code'] for i in result['issues']})
                self.assertEqual(result['calculations']['A-AST']['DARKO_normalized'], '8' if basis == 'per_game' else '8.00')
                self.assertEqual(result['calculations']['A-AST']['relationship'], 'Agree Higher')
                self.assertEqual(before, encode(self.note))

    def test_normalization_source_unit_conflicts_block_comparison(self):
        self.finalized()
        original = copy.deepcopy(self.note)
        cases = [('per_game', 'per_minute', 'count'), ('per_minute', 'per_game', 'count'),
                 ('per_game', 'per_100_possessions', 'count'), ('per_minute', 'per_100_possessions', 'count'),
                 ('per_minute', 'per minute', 'counts / 100 possessions'),
                 ('per_game', 'per game', 'points per minute')]
        for basis, denominator, unit in cases:
            with self.subTest(basis=basis, denominator=denominator, unit=unit):
                self.note = copy.deepcopy(original)
                self.note['projections'][1]['basis'] = basis
                self.note['sources']['S3'].update(denominator=denominator, unit=unit)
                before = encode(self.note)
                result = check(self.note)
                self.assertTrue(any(i['code'] == 'NORMALIZATION_UNITS' and i['state'] == 'conflicting' for i in result['issues']))
                self.assertNotIn('A-AST', result['calculations'])
                self.assertEqual(result['lock_status'], 'unsupported claim')
                self.assertEqual(before, encode(self.note))

    def test_unknown_source_basis_does_not_infer_a_conversion(self):
        original = copy.deepcopy(self.note)
        for denominator in (None, 'provider-specific rate', 'per 36 minutes'):
            with self.subTest(denominator=denominator):
                self.note = copy.deepcopy(original)
                self.note['sources']['S3']['denominator'] = denominator
                result = check(self.note)
                self.assertTrue(any(i['code'] == 'NORMALIZATION_UNITS' and i['state'] == 'analyst_review_required' for i in result['issues']))
                self.assertNotIn('A-AST', result['calculations'])
                self.assertEqual(self.note['projections'][1]['values']['AST'], 6)
