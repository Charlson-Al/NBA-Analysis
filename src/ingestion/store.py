"""Immutable, offline, synthetic-only snapshots in an external private directory.

The same JSON envelope accepts an authorized response file or manual export.
This pilot deliberately rejects real research data and forecasts.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
from datetime import datetime, timezone

from jsonschema import Draft202012Validator, FormatChecker

REPO = Path(__file__).resolve().parents[2]
SCHEMAS = REPO / 'manifests/schemas'
PARSER = 'synthetic-json-1'
FILES = {'original.json', 'observations.json', 'inventory.json', 'manifest.json', 'validation.json'}


class IngestionError(ValueError):
    """Rejected input or unsafe storage; callers should not publish payloads."""


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def decode(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise IngestionError('Duplicate JSON object key')
            result[key] = value
        return result
    try:
        value = json.loads(data, object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(IngestionError('Nonfinite number')))
        # Also rejects numeric overflow such as 1e999.
        encode(value)
        return value
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise IngestionError('Invalid JSON input') from exc


def validate(name, value):
    schema = json.loads((SCHEMAS / f'{name}.schema.json').read_text())
    checker = FormatChecker()
    if not {'date', 'date-time'} <= checker.checkers.keys():
        raise IngestionError('Required date/time validators unavailable; install pinned dependencies')
    errors = list(Draft202012Validator(schema, format_checker=checker).iter_errors(value))
    if errors:
        raise IngestionError(f'{name} schema validation failed')


def private_root(configured=None):
    value = configured if configured is not None else os.environ.get('NBA_PRIVATE_DATA_ROOT')
    if not value:
        raise IngestionError('NBA_PRIVATE_DATA_ROOT must be explicitly configured')
    path = Path(value).expanduser()
    if not path.is_absolute() or path != path.resolve():
        raise IngestionError('Private root must be absolute and contain no symlink components')
    repo = REPO.resolve()
    if path == repo or repo in path.parents or path in repo.parents:
        raise IngestionError('Private root must be outside and not contain the checkout')
    for parent in (path, *path.parents):
        marker = parent / '.git'
        # Managed workers mount empty .git placeholders outside project checkouts.
        # Actual metadata, gitdir files and symlinks are all rejected.
        if marker.is_symlink() or marker.is_file() or (marker.is_dir() and any(marker.iterdir())):
            raise IngestionError('Private root must not be inside any Git checkout')
        if (parent / 'HEAD').is_file() and (parent / 'objects').is_dir():
            raise IngestionError('Private root must not be inside a bare Git repository')
    if not path.exists():
        path.mkdir(mode=0o700, parents=True)
    if not path.is_dir() or path.stat().st_uid != os.getuid() or path.stat().st_mode & 0o077:
        raise IngestionError('Private root must be an owner-only directory owned by this user')
    return path


def snapshot_path(root, snapshot_id):
    import re
    if not isinstance(snapshot_id, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', snapshot_id):
        raise IngestionError('Invalid snapshot identifier')
    return root / snapshot_id


def read_file(path):
    if path.is_symlink() or not path.is_file():
        raise IngestionError('Snapshot artifacts must be regular files, not symlinks')
    return path.read_bytes()


def normalize(raw, manifest, inventory):
    data = decode(raw)
    if not isinstance(data, dict) or set(data) != {'synthetic', 'observations'} or data['synthetic'] is not True:
        raise IngestionError('Only explicitly synthetic observation envelopes are supported')
    rows = data['observations']
    if not isinstance(rows, list) or not rows:
        raise IngestionError('Observations must be a nonempty list')
    metrics = {m['id']: m for m in manifest['metrics']}
    if len(metrics) != len(manifest['metrics']):
        raise IngestionError('Duplicate metric definitions')
    seen, games, teams, latest = set(), {}, set(), {}
    for index, row in enumerate(rows, 1):
        validate('observation', row)
        if row['source_row'] != index:
            raise IngestionError('Source row must identify its original array position')
        key = row['team_id'], row['game_id'], row['metric_id']
        if key in seen:
            raise IngestionError('Duplicate observation')
        seen.add(key)
        metric = metrics.get(row['metric_id'])
        if metric is None or any(row[k] != metric[k] for k in ('unit', 'denominator')):
            raise IngestionError('Unknown metric or incompatible units/denominator')
        game = games.setdefault(row['game_id'], {'game_id': row['game_id'], 'game_date': row['game_date'], 'team_ids': set()})
        if game['game_date'] != row['game_date']:
            raise IngestionError('Conflicting dates for the same game')
        game['team_ids'].add(row['team_id'])
        teams.add(row['team_id'])
        latest[row['team_id']] = max(latest.get(row['team_id'], ''), row['game_date'])
        cutoff = manifest['cutoff']['requested_through']
        if cutoff and row['game_date'] > cutoff:
            raise IngestionError('Observation exceeds requested cutoff')
    if teams != set(manifest['scope']['expected_team_ids']):
        raise IngestionError('Team coverage does not match declared scope')
    if any(len(g['team_ids']) != 2 for g in games.values()):
        raise IngestionError('Pilot requires exactly two teams per completed game')
    # Require each declared metric for both teams; unavailable values must be explicit rows.
    expected = {(t, gid, metric) for gid, g in games.items() for t in g['team_ids'] for metric in metrics}
    if seen != expected:
        raise IngestionError('Incomplete team/game/metric coverage')
    included = [{**g, 'team_ids': sorted(g['team_ids'])} for _, g in sorted(games.items())]
    if inventory is not None:
        if not isinstance(inventory, dict) or set(inventory) != {'synthetic', 'independent_reference', 'season', 'season_type', 'through', 'games'}:
            raise IngestionError('Invalid independent inventory')
        if inventory['synthetic'] is not True or not isinstance(inventory['independent_reference'], str) or not inventory['independent_reference'].strip():
            raise IngestionError('Inventory needs synthetic independent provenance')
        if any(inventory[k] != manifest['scope'][k] for k in ('season', 'season_type')) or inventory['through'] != manifest['cutoff']['requested_through']:
            raise IngestionError('Inventory scope/cutoff mismatch')
        if inventory['games'] != included:
            raise IngestionError('Inventory differs from actual game coverage')
    verified = manifest['cutoff']['verification_status'] == 'verified'
    if verified and (inventory is None or not manifest['cutoff']['requested_through']):
        raise IngestionError('Verified cutoff requires independent inventory and explicit cutoff')
    ordered = sorted(rows, key=lambda r: (r['game_id'], r['team_id'], r['metric_id']))
    return ordered, included, sorted(teams), latest


def report_for(manifest, raw, inventory_bytes):
    inventory = decode(inventory_bytes)
    rows, games, teams, latest = normalize(raw, manifest, inventory)
    report = {'schema_version': '1.0', 'snapshot_id': manifest['snapshot_id'], 'parser_version': PARSER,
              'manifest_sha256': digest(encode(manifest)), 'status': 'passed', 'row_count': len(rows),
              'team_ids': teams, 'included_games': games, 'latest_game_by_team': latest,
              'cutoff_verification_status': manifest['cutoff']['verification_status'],
              'checks': ['schema', 'definitions', 'duplicates', 'team_metric_coverage', 'cutoff_claim', 'source_row_provenance']}
    validate('validation', report)
    return encode(rows), encode(report)


def import_snapshot(source, metadata, *, root=None, inventory=None):
    """Store original bytes and reproducible outputs; metadata supplies no artifact hashes.

    inventory is a separate synthetic inventory JSON file, not inferred from observations.
    A passed validation is not a declaration of real-world source authenticity.
    """
    root = private_root(root)
    raw = read_file(Path(source))
    inv = read_file(Path(inventory)) if inventory is not None else encode(None)
    manifest = decode(encode(metadata))
    if not isinstance(manifest, dict) or not isinstance(manifest.get('acquisition'), dict):
        raise IngestionError('Metadata must contain acquisition details')
    manifest['acquisition']['imported_at'] = datetime.now(timezone.utc).isoformat()
    manifest['original_filename'] = Path(source).name
    if any(k in manifest for k in ('artifacts', 'parser_version')):
        raise IngestionError('Artifact integrity fields are generated by the importer')
    manifest['parser_version'] = PARSER
    # Preliminary schema validation before any semantic access or destination write.
    placeholder = {'sha256': '0' * 64, 'size_bytes': 0}
    manifest['artifacts'] = {k: dict(placeholder) for k in ('original.json', 'observations.json', 'inventory.json')}
    validate('snapshot', manifest)
    inventory_hash = digest(inv) if inventory is not None else None
    if manifest['cutoff']['inventory_sha256'] != inventory_hash:
        raise IngestionError('Independent inventory checksum mismatch')
    observations, _ = report_for(manifest, raw, inv)
    artifacts = {'original.json': raw, 'observations.json': observations, 'inventory.json': inv}
    manifest['artifacts'] = {name: {'sha256': digest(data), 'size_bytes': len(data)} for name, data in artifacts.items()}
    validate('snapshot', manifest)
    _, report = report_for(manifest, raw, inv)
    artifacts.update({'manifest.json': encode(manifest), 'validation.json': report})
    destination = snapshot_path(root, manifest['snapshot_id'])
    # mkdir is exclusive: simultaneous imports cannot replace the same snapshot ID.
    try:
        destination.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise IngestionError('Snapshot already exists; overwrite is forbidden') from exc
    try:
        for name, data in artifacts.items():
            with (destination / name).open('xb') as f:
                os.chmod(destination / name, 0o600)
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
        verify(manifest['snapshot_id'], root=root)
        for path in destination.iterdir():
            path.chmod(0o400)
        destination.chmod(0o500)
    except Exception:
        destination.chmod(0o700)
        shutil.rmtree(destination)
        raise
    return destination


def verify(snapshot_id, *, root=None):
    """Revalidate checksums, original-row provenance, coverage and deterministic replay."""
    root = private_root(root)
    path = snapshot_path(root, snapshot_id)
    if path.is_symlink() or not path.is_dir() or {p.name for p in path.iterdir()} != FILES:
        raise IngestionError('Missing, unexpected or unsafe snapshot artifacts')
    manifest_bytes = read_file(path / 'manifest.json')
    manifest = decode(manifest_bytes)
    validate('snapshot', manifest)
    if manifest['snapshot_id'] != snapshot_id or manifest_bytes != encode(manifest):
        raise IngestionError('Manifest identity or encoding mismatch')
    data = {}
    for name, expected in manifest['artifacts'].items():
        data[name] = read_file(path / name)
        if digest(data[name]) != expected['sha256'] or len(data[name]) != expected['size_bytes']:
            raise IngestionError('Artifact checksum or size mismatch')
    inv_hash = digest(data['inventory.json']) if decode(data['inventory.json']) is not None else None
    if inv_hash != manifest['cutoff']['inventory_sha256']:
        raise IngestionError('Inventory integrity mismatch')
    observations, report = report_for(manifest, data['original.json'], data['inventory.json'])
    if observations != data['observations.json'] or report != read_file(path / 'validation.json'):
        raise IngestionError('Replay differs from stored observations or validation record')
    return observations
