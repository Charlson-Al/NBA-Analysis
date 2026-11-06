"""Exclusive, hash-linked local records. Trusted owner; not WORM or durable hosting."""
from contextlib import contextmanager
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import uuid

from ingestion.store import (IngestionError, decode, digest, encode, private_root,
                             read_file, snapshot_path, validate)


def directory(session_id, root=None):
    path = snapshot_path(private_root(root), session_id)
    if path.is_symlink() or not path.is_dir():
        raise IngestionError('Missing or unsafe tracker session')
    return private_root(path)


@contextmanager
def locked(path):
    marker = path / '.lock'
    try:
        fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise IngestionError('Session locked; inspect interrupted writer privately') from exc
    try:
        os.close(fd)
        yield
    finally:
        marker.unlink()


def load(session_id, *, root=None):
    path = directory(session_id, root)
    files = sorted(p for p in path.iterdir() if p.name != '.lock')
    events, previous, identities = [], None, set()
    for sequence, file in enumerate(files, 1):
        if file.name != f'{sequence:08}.json':
            raise IngestionError('Incomplete or unexpected tracker files')
        raw = read_file(file)
        event = decode(raw)
        if not isinstance(event, dict) or set(event) != {'sequence', 'previous_sha256', 'event_id', 'created_at', 'record'}:
            raise IngestionError('Invalid journal envelope')
        if raw != encode(event) or event['sequence'] != sequence or event['previous_sha256'] != previous:
            raise IngestionError('Journal integrity mismatch')
        if not isinstance(event['event_id'], str) or event['event_id'] in identities:
            raise IngestionError('Duplicate or invalid event identity')
        identities.add(event['event_id'])
        try:
            when = datetime.fromisoformat(event['created_at'])
            if when.utcoffset() is None:
                raise ValueError('No timezone')
        except (ValueError, TypeError) as exc:
            raise IngestionError('Invalid journal time') from exc
        validate('tracker', event['record'])
        if not set(event['record']['basis']) <= {e['event_id'] for e in events}:
            raise IngestionError('Basis must refer to earlier events')
        if sequence == 1 and event['record']['kind'] != 'session':
            raise IngestionError('Session declaration must be first')
        if sequence > 1 and event['record']['kind'] == 'session':
            raise IngestionError('Session declaration cannot be replaced')
        prior = [e for e in events if e['record']['entity_id'] == event['record']['entity_id']]
        if prior and prior[-1]['record']['kind'] != event['record']['kind']:
            raise IngestionError('Entity type cannot change')
        events.append(event)
        previous = digest(raw)
    if not events:
        raise IngestionError('Empty journal')
    return events


def append(session_id, record, *, root=None):
    validate('tracker', record)
    path = directory(session_id, root)
    with locked(path):
        events = load(session_id, root=root) if any(path.glob('*.json')) else []
        if not events and record['kind'] != 'session':
            raise IngestionError('Session declaration required')
        if events and record['kind'] == 'session':
            raise IngestionError('Session declaration is immutable')
        if not set(record['basis']) <= {e['event_id'] for e in events}:
            raise IngestionError('Unknown basis event')
        if any(e['record']['entity_id'] == record['entity_id'] and e['record']['kind'] != record['kind'] for e in events):
            raise IngestionError('Entity type cannot change')
        # Detect interrupted/unexpected files before creating another event.
        if not events and {p.name for p in path.iterdir()} != {'.lock'}:
            raise IngestionError('Unexpected session files')
        event = {'sequence': len(events) + 1,
                 'previous_sha256': digest(encode(events[-1])) if events else None,
                 'event_id': uuid.uuid4().hex,
                 'created_at': datetime.now(timezone.utc).isoformat(), 'record': record}
        destination = path / f'{event["sequence"]:08}.json'
        try:
            with destination.open('xb') as stream:
                os.chmod(destination, 0o600)
                stream.write(encode(event))
                stream.flush()
                os.fsync(stream.fileno())
            destination.chmod(0o400)
        except Exception:
            if destination.exists():
                destination.unlink()
            raise
        return event


def create(session_id, record, *, root=None):
    validate('tracker', record)
    if record['kind'] != 'session':
        raise IngestionError('Expected session declaration')
    path = snapshot_path(private_root(root), session_id)
    try:
        path.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise IngestionError('Session already exists') from exc
    try:
        return append(session_id, record, root=root)
    except Exception:
        shutil.rmtree(path)
        raise


def at_event(events, event_id):
    """Read-only view at a recorded checkpoint, including its original dependencies."""
    for index, event in enumerate(events):
        if event['event_id'] == event_id:
            return events[:index + 1]
    raise IngestionError('Unknown checkpoint event')
