"""Boundary regressions using synthetic inputs and isolated repositories/storage."""
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_ingestion as fixtures
from ingestion import store
from ingestion.public_guard import allowed


class BoundaryTests(unittest.TestCase):
    setUp = fixtures.IngestionTests.setUp
    save = fixtures.IngestionTests.save
    edit = fixtures.IngestionTests.edit
    inventory = fixtures.IngestionTests.inventory

    def test_partial_write_cleanup_and_retry(self):
        original_open = Path.open
        class BrokenWriter:
            def __init__(self, file): self.file = file
            def __enter__(self): return self
            def __exit__(self, *args): self.file.close()
            def write(self, data):
                self.file.write(data[:5])
                raise OSError('injected partial write')
        def open_file(path, mode='r', *args, **kwargs):
            file = original_open(path, mode, *args, **kwargs)
            return BrokenWriter(file) if mode == 'xb' else file
        with patch.object(Path, 'open', open_file):
            with self.assertRaises(OSError): self.save()
        self.assertEqual(list(self.root.iterdir()), [])
        self.save()
        self.assertTrue(store.verify(self.meta['snapshot_id'], root=self.root))

    def test_required_format_checkers_fail_closed(self):
        from jsonschema import FormatChecker
        for missing in ('date', 'date-time'):
            checkers = dict(FormatChecker.checkers)
            checkers.pop(missing)
            with self.subTest(missing=missing), patch.object(FormatChecker, 'checkers', checkers):
                with self.assertRaisesRegex(store.IngestionError, 'validators unavailable'):
                    self.save()
        self.assertEqual(list(self.root.iterdir()), [])

    def test_invalid_rfc3339_timestamps(self):
        for field in ('collected_at', 'provider_updated_at'):
            for value in ('yesterday', '2026-01-01T12:00:00', '2026-02-30T00:00:00Z'):
                self.meta['acquisition'][field] = value
                with self.subTest(field=field, value=value), self.assertRaises(store.IngestionError):
                    self.save()
            self.meta['acquisition'][field] = None

    def test_blank_missing_reasons(self):
        for status in ('missing', 'unavailable', 'not_applicable'):
            for reason in ('', ' ', '\t\n'):
                self.edit(lambda v: v['observations'][1].update(value_status=status, reason=reason))
                with self.subTest(status=status, reason=reason), self.assertRaises(store.IngestionError):
                    self.save()

    def test_write_fsync_and_verification_failure_cleanup_and_retry(self):
        for target in ('ingestion.store.os.fsync', 'ingestion.store.verify', 'pathlib.Path.chmod'):
            with self.subTest(target=target):
                with patch(target, side_effect=[OSError('injected'), None]):
                    with self.assertRaises(OSError):
                        self.save()
                self.assertEqual(list(self.root.iterdir()), [])
                path = self.save()
                self.assertTrue(store.verify(self.meta['snapshot_id'], root=self.root))
                path.chmod(0o700)
                import shutil
                shutil.rmtree(path)

    def test_process_interruption_preserves_incomplete_snapshot_and_blocks_retry(self):
        with patch('ingestion.store.os.fsync', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.save()
        path = self.root / self.meta['snapshot_id']
        before = {p.name: p.read_bytes() for p in path.iterdir()}
        self.assertEqual(set(before), {'original.json'})
        with self.assertRaises(store.IngestionError):
            store.verify(self.meta['snapshot_id'], root=self.root)
        with self.assertRaisesRegex(store.IngestionError, 'already exists'):
            self.save()
        self.assertEqual(before, {p.name: p.read_bytes() for p in path.iterdir()})

    def test_separate_acquisitions_replay_identically(self):
        from datetime import datetime, timezone
        with patch('ingestion.store.datetime') as clock:
            clock.now.return_value = datetime(2026, 1, 2, tzinfo=timezone.utc)
            first = self.save()
            self.meta['snapshot_id'] = 'second-acquisition'
            clock.now.return_value = datetime(2026, 1, 3, tzinfo=timezone.utc)
            second = self.save()
        self.assertEqual((first / 'original.json').read_bytes(), (second / 'original.json').read_bytes())
        self.assertEqual(store.verify(first.name, root=self.root), store.verify(second.name, root=self.root))
        a, b = [store.decode((p / 'manifest.json').read_bytes()) for p in (first, second)]
        self.assertNotEqual(a['acquisition']['imported_at'], b['acquisition']['imported_at'])
        self.assertNotEqual((first / 'validation.json').read_bytes(), (second / 'validation.json').read_bytes())
        a.pop('snapshot_id'); b.pop('snapshot_id')
        a['acquisition'].pop('imported_at'); b['acquisition'].pop('imported_at')
        self.assertEqual(a, b)
        outputs = []
        for seed, snapshot in (('1', first), ('99', second)):
            env = dict(os.environ, PYTHONHASHSEED=seed, PYTHONPATH=str(store.REPO / 'src'))
            code = 'import sys; from ingestion.store import verify; sys.stdout.buffer.write(verify(sys.argv[1], root=sys.argv[2]))'
            outputs.append(subprocess.check_output([sys.executable, '-c', code, snapshot.name, str(self.root)], env=env))
        self.assertEqual(outputs[0], outputs[1])

    def test_inventory_tampering_after_storage(self):
        path = self.save(inventory=self.inventory()) / 'inventory.json'
        path.chmod(0o600)
        path.write_bytes(b'{}')
        with self.assertRaises(store.IngestionError):
            store.verify(self.meta['snapshot_id'], root=self.root)

    def test_missing_unexpected_and_size_mismatch(self):
        path = self.save()
        path.chmod(0o700)
        extra = path / 'unexpected'
        extra.write_bytes(b'x')
        with self.assertRaises(store.IngestionError): store.verify(path.name, root=self.root)
        extra.unlink()
        manifest_path = path / 'manifest.json'
        manifest = store.decode(manifest_path.read_bytes())
        manifest['artifacts']['original.json']['size_bytes'] += 1
        manifest_path.chmod(0o600); manifest_path.write_bytes(store.encode(manifest))
        with self.assertRaisesRegex(store.IngestionError, 'checksum or size'): store.verify(path.name, root=self.root)
        (path / 'validation.json').unlink()
        with self.assertRaises(store.IngestionError): store.verify(path.name, root=self.root)

    def test_snapshot_directory_symlink(self):
        path = self.save()
        (self.root / 'alias').symlink_to(path, target_is_directory=True)
        with self.assertRaises(store.IngestionError): store.verify('alias', root=self.root)

    def test_guard_case_variants(self):
        for name in ('docs/export.CSV', 'docs/export.CsV', 'docs/MANIFEST.JSON',
                     'docs/SnapShots/a.txt', 'docs/Private-Data/a.txt', 'docs/Derived/a.txt',
                     'docs/Acquisition-Events/a.txt', 'docs/a.PdF', 'docs/a.JsOn'):
            with self.subTest(name=name): self.assertFalse(allowed(name, b'{}'))

    def test_actual_staged_index_guard(self):
        repo = self.base / 'git-test'; repo.mkdir()
        def git(*args):
            return subprocess.run(['git', *args], cwd=repo, check=True, capture_output=True)
        git('init', '-q')
        guard = Path(store.REPO / 'src/ingestion/public_guard.py')
        def check(expected):
            result = subprocess.run([sys.executable, str(guard)], cwd=repo, capture_output=True, text=True)
            self.assertEqual(result.returncode, expected, result.stderr)
            self.assertNotIn('SECRET_SENTINEL', result.stdout + result.stderr)
        good = repo / 'tests/fixtures/synthetic/demo.json'
        good.parent.mkdir(parents=True)
        good.write_bytes(b'{"synthetic":true}')
        git('add', '.'); check(0)
        # Index is authoritative even when the working file is changed afterwards.
        good.write_bytes(b'{"synthetic":false}')
        check(0)
        git('add', '.'); check(1)
        good.write_bytes(b'{"synthetic":true}'); git('add', '.')
        for name, data in [('docs/export.CsV', b'SECRET_SENTINEL'),
                           ('docs/Private-Data/note.txt', b'SECRET_SENTINEL'),
                           ('docs/restricted.json', b'{"rights":"restricted"}'),
                           ('tests/fixtures/synthetic/private.json', b'{"synthetic":false}')]:
            file = repo / name; file.parent.mkdir(parents=True, exist_ok=True); file.write_bytes(data)
            git('add', '.'); check(1)
            git('rm', '--cached', name); file.unlink()
        link = repo / 'docs/link.txt'; link.symlink_to('target')
        git('add', '.'); check(1)
