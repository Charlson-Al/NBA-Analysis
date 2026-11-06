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
from ingestion.store import (IngestionError, REPO, decode, digest, encode,
                             import_snapshot, private_root, validate, verify)
from ingestion.public_guard import allowed

FIXTURES = REPO / 'tests/fixtures/synthetic'


class IngestionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.root = self.base / 'private'
        self.source = self.base / 'input.json'
        self.raw = (FIXTURES / 'observations-input.json').read_bytes()
        self.source.write_bytes(self.raw)
        self.meta = json.loads((FIXTURES / 'metadata-input.json').read_text())

    def save(self, metadata=None, inventory=None):
        return import_snapshot(self.source, self.meta if metadata is None else metadata,
                               root=self.root, inventory=inventory)

    def edit(self, change):
        value = decode(self.raw)
        change(value)
        self.source.write_bytes(encode(value))

    def inventory(self):
        inv = dict(synthetic=True, independent_reference='urn:synthetic:independent-schedule',
                   season='synthetic-season', season_type='synthetic', through='2026-01-01',
                   games=[dict(game_id='SYN_GAME_1', game_date='2026-01-01', team_ids=['SYN_A', 'SYN_B'])])
        path = self.base / 'schedule.json'
        path.write_bytes(encode(inv))
        self.meta['cutoff']['inventory_sha256'] = digest(path.read_bytes())
        return path

    def test_preservation_and_deterministic_replay(self):
        path = self.save()
        self.assertEqual((path / 'original.json').read_bytes(), self.raw)
        self.assertEqual(self.source.read_bytes(), self.raw)
        first = verify(self.meta['snapshot_id'], root=self.root)
        self.assertEqual(first, verify(self.meta['snapshot_id'], root=self.root))
        self.assertEqual(first, (path / 'observations.json').read_bytes())
        self.assertIsNone(decode(first)[1]['value'])
        self.assertEqual(decode(first)[1]['value_status'], 'missing')
        manifest = decode((path / 'manifest.json').read_bytes())
        self.assertEqual(manifest['artifacts']['original.json']['sha256'], digest(self.raw))
        for key in ('method', 'source_reference', 'parameters', 'collected_at', 'provider_updated_at'):
            self.assertEqual(manifest['acquisition'][key], self.meta['acquisition'][key])
        self.assertNotEqual(manifest['acquisition']['imported_at'], self.meta['acquisition']['imported_at'])
        self.assertEqual(manifest['metrics'], self.meta['metrics'])
        self.assertEqual(decode((path / 'validation.json').read_bytes())['cutoff_verification_status'], 'unverified')
        self.assertEqual(path.stat().st_mode & 0o777, 0o500)
        self.assertEqual((path / 'original.json').stat().st_mode & 0o777, 0o400)

    def test_reimport_cannot_overwrite(self):
        path = self.save()
        before = {p.name: p.read_bytes() for p in path.iterdir()}
        with self.assertRaises(IngestionError):
            self.save()
        self.assertEqual(before, {p.name: p.read_bytes() for p in path.iterdir()})

    def test_duplicate_records(self):
        def duplicate(v):
            row = dict(v['observations'][0], source_row=3)
            v['observations'].append(row)
        self.edit(duplicate)
        with self.assertRaises(IngestionError): self.save()

    def test_invalid_units_and_denominators(self):
        for field in ('unit', 'denominator', 'metric_id'):
            with self.subTest(field=field):
                self.edit(lambda v: v['observations'][0].update({field: 'incompatible'}))
                with self.assertRaises(IngestionError): self.save()

    def test_missing_statuses_are_not_zero(self):
        for status in ('missing', 'unavailable', 'not_applicable'):
            with self.subTest(status=status):
                meta = copy.deepcopy(self.meta)
                meta['snapshot_id'] += '-' + status
                self.edit(lambda v: v['observations'][1].update(value_status=status))
                path = self.save(meta)
                row = decode(verify(meta['snapshot_id'], root=self.root))[1]
                self.assertIsNone(row['value'])
                self.assertEqual(row['value_status'], status)

    def test_status_schema_contradictions(self):
        for change in ({'value_status': 'present'}, {'value': 0}, {'reason': None}):
            with self.subTest(change=change):
                self.edit(lambda v: v['observations'][1].update(change))
                with self.assertRaises(IngestionError): self.save()

    def test_schema_and_timestamps(self):
        for change in ({'schema_version': '2.0'}, {'synthetic': False}, {'rights': 'licensed'},
                       {'data_category': 'forecast'}, {'extra': 1}):
            meta = {**self.meta, **change}
            with self.subTest(change=change), self.assertRaises(IngestionError): self.save(meta)
        self.meta['acquisition']['collected_at'] = 'yesterday'
        with self.assertRaises(IngestionError): self.save()

    def test_invalid_json_and_nonfinite(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}', b'not json'):
            with self.subTest(raw=raw), self.assertRaises(IngestionError): decode(raw)

    def test_unsupported_cutoff_claim(self):
        self.meta['cutoff']['verification_status'] = 'verified'
        with self.assertRaises(IngestionError): self.save()

    def test_independent_inventory_verified_coverage(self):
        inv = self.inventory()
        self.meta['cutoff']['verification_status'] = 'verified'
        path = self.save(inventory=inv)
        report = decode((path / 'validation.json').read_bytes())
        self.assertEqual(report['cutoff_verification_status'], 'verified')
        self.assertEqual(report['latest_game_by_team'], {'SYN_A': '2026-01-01', 'SYN_B': '2026-01-01'})

    def test_inventory_missing_game_or_wrong_scope(self):
        for field, value in [('games', []), ('season', 'wrong'), ('through', '2026-01-02')]:
            inv = self.inventory()
            obj = decode(inv.read_bytes()); obj[field] = value; inv.write_bytes(encode(obj))
            self.meta['cutoff']['inventory_sha256'] = digest(inv.read_bytes())
            with self.subTest(field=field), self.assertRaises(IngestionError): self.save(inventory=inv)

    def test_inventory_tampering(self):
        inv = self.inventory()
        inv.write_bytes(b'{}')
        with self.assertRaises(IngestionError): self.save(inventory=inv)

    def test_cutoff_and_team_coverage(self):
        self.meta['scope']['expected_team_ids'].append('SYN_C')
        with self.assertRaises(IngestionError): self.save()
        self.meta['scope']['expected_team_ids'].pop()
        self.meta['cutoff']['requested_through'] = '2025-12-31'
        with self.assertRaises(IngestionError): self.save()

    def test_partial_metric_coverage(self):
        metric = dict(self.meta['metrics'][0], id='another_metric')
        self.meta['metrics'].append(metric)
        with self.assertRaises(IngestionError): self.save()

    def test_source_row_provenance(self):
        self.edit(lambda v: v['observations'][0].update(source_row=99))
        with self.assertRaises(IngestionError): self.save()

    def test_original_tamper_detected(self):
        path = self.save() / 'original.json'
        path.chmod(0o600); path.write_bytes(b'{}')
        with self.assertRaises(IngestionError): verify(self.meta['snapshot_id'], root=self.root)

    def test_derived_and_report_tamper_detected(self):
        for name in ('observations.json', 'validation.json', 'manifest.json'):
            meta = dict(self.meta, snapshot_id='tamper-' + name.replace('.', '-'))
            path = self.save(meta) / name
            path.chmod(0o600); path.write_bytes(b'{}')
            with self.subTest(name=name), self.assertRaises(IngestionError): verify(meta['snapshot_id'], root=self.root)

    def test_no_unconfigured_unsafe_or_git_roots(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(IngestionError): private_root()
        for root in (REPO, REPO / 'private', REPO.parent, Path('relative')):
            with self.subTest(root=root), self.assertRaises(IngestionError): private_root(root)
        other = self.base / 'other'; other.mkdir(mode=0o700); (other / '.git').write_text('gitdir: external')
        with self.assertRaises(IngestionError): private_root(other / 'data')
        unsafe = self.base / 'unsafe'; unsafe.mkdir(mode=0o700); unsafe.chmod(0o755)
        with self.assertRaises(IngestionError): private_root(unsafe)

    def test_full_thirty_team_coverage(self):
        rows, teams = [], []
        template = decode(self.raw)['observations'][0]
        for game in range(15):
            for side in range(2):
                team = 'SYN_' + str(game * 2 + side)
                teams.append(team)
                rows.append(dict(template, team_id=team, game_id='SYN_GAME_' + str(game), source_row=len(rows) + 1))
        self.source.write_bytes(encode({'synthetic': True, 'observations': rows}))
        self.meta['scope']['expected_team_ids'] = teams
        self.save()
        self.assertEqual(len(decode(verify(self.meta['snapshot_id'], root=self.root))), 30)

    def test_failed_import_leaves_no_snapshot(self):
        self.edit(lambda v: v['observations'][0].update(unit='bad'))
        with self.assertRaises(IngestionError): self.save()
        self.assertEqual(list(self.root.iterdir()), [])

    def test_snapshot_artifact_symlink_rejected(self):
        path = self.save()
        path.chmod(0o700)
        (path / 'original.json').unlink()
        (path / 'original.json').symlink_to(self.source)
        with self.assertRaises(IngestionError): verify(self.meta['snapshot_id'], root=self.root)

    def test_symlinks_and_path_traversal(self):
        real = self.base / 'real'; real.mkdir(mode=0o700)
        link = self.base / 'link'; link.symlink_to(real)
        with self.assertRaises(IngestionError): private_root(link)
        self.meta['snapshot_id'] = '../escape'
        with self.assertRaises(IngestionError): self.save()
        self.meta['snapshot_id'] = 'synthetic-demo-1'
        self.source.unlink(); self.source.symlink_to(FIXTURES / 'observations-input.json')
        with self.assertRaises(IngestionError): self.save()

    def test_cli_offline_import_and_verify(self):
        env = dict(os.environ, PYTHONPATH=str(REPO / 'src'), NBA_PRIVATE_DATA_ROOT=str(self.root), PYTHONDONTWRITEBYTECODE='1')
        prefix = [sys.executable, '-m', 'ingestion']
        for args in (['import', '--source', str(self.source), '--metadata', str(FIXTURES / 'metadata-input.json')], ['verify', self.meta['snapshot_id']]):
            proc = subprocess.run(prefix + args, env=env, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertNotIn(str(self.root), proc.stdout + proc.stderr)

    def test_api_response_file_uses_same_pipeline(self):
        self.meta['acquisition']['method'] = 'api_response_file'
        self.save()
        self.assertTrue(verify(self.meta['snapshot_id'], root=self.root))

    def test_zero_is_present_and_does_not_mean_missing(self):
        self.edit(lambda v: v['observations'][0].update(value=0))
        self.save()
        row = decode(verify(self.meta['snapshot_id'], root=self.root))[0]
        self.assertEqual(row['value'], 0)
        self.assertEqual(row['value_status'], 'present')

    def test_conflicting_game_dates_rejected(self):
        self.edit(lambda v: v['observations'][1].update(game_date='2025-12-31'))
        with self.assertRaises(IngestionError): self.save()

    def test_source_change_does_not_modify_snapshot(self):
        path = self.save()
        self.source.write_bytes(b'changed after import')
        self.assertEqual((path / 'original.json').read_bytes(), self.raw)
        self.assertTrue(verify(self.meta['snapshot_id'], root=self.root))

    def test_public_guard(self):
        for path, blob in [('data/source/new.csv', b'x'), ('docs/manifest.json', b'{}'),
                           ('snapshots/a/original.json', b'{}'), ('docs/research.txt', b'/home/research/private'),
                           ('tests/fixtures/synthetic/real.json', b'{"synthetic":false}')]:
            with self.subTest(path=path): self.assertFalse(allowed(path, blob))
        self.assertTrue(allowed('tests/fixtures/synthetic/demo.json', b'{"synthetic":true}'))
        self.assertTrue(allowed('src/ingestion/store.py', b'print("synthetic")'))

    def test_schemas_are_valid_draft_2020_12(self):
        from jsonschema import Draft202012Validator
        for path in (REPO / 'manifests/schemas').glob('*.json'):
            Draft202012Validator.check_schema(json.loads(path.read_text()))


if __name__ == '__main__':
    unittest.main()
