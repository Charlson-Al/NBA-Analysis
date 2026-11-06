"""Private editable notes and exclusive immutable pregame snapshots, not an event store."""
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import shutil

from ingestion.store import (IngestionError, REPO, decode, digest, encode, private_root,
                             read_file, snapshot_path, validate)
from .catalog import FRAMEWORK_PATH, REFINEMENT_PATH, APPROVAL_PATH
from .review import check, render


def private_file(root, name):
    path = Path(root) / name
    if not path.is_absolute() or path != path.resolve() or Path(root) not in path.parents:
        raise IngestionError('File must be inside configured private root without symlinks')
    if not path.is_file() or path.is_symlink():
        raise IngestionError('Missing or unsafe private file')
    if path.stat().st_uid != os.getuid() or path.stat().st_mode & 0o077:
        raise IngestionError('Private files must be owner-only')
    return path


def read_note(root, name):
    root = private_root(root)
    raw = read_file(private_file(root, name))
    note = decode(raw)
    validate('tracker', note)
    return raw, note


def attachments(root, note):
    data, issues = {}, []
    for key, source in note['sources'].items():
        if source.get('phase') == 'postgame' or not source.get('file'):
            continue
        try:
            raw = read_file(private_file(root, source['file']))
            if not source.get('sha256') or digest(raw) != source['sha256']:
                raise IngestionError('Source bytes differ from note reference')
            data['source-' + key + '.bin'] = raw
        except (OSError, IngestionError):
            issues.append(dict(stage='sources',state='conflicting',code='SOURCE_FILE',subject=key,
                               reason='Private source missing, unsafe or differs from recorded digest; original reference unchanged'))
    return data, issues


def assess(root, name):
    _, note = read_note(root, name)
    _, source_issues = attachments(root, note)
    return note, check(note, additional=source_issues)


def write_exclusive(path, raw, mode=0o400):
    with path.open('xb') as stream:
        os.chmod(path, 0o600)
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(mode)


def freeze(root, name, label):
    root = private_root(root)
    raw, note = read_note(root, name)
    if note.get('postgame') or any(source.get('phase') == 'postgame' for source in note['sources'].values()):
        raise IngestionError('Freeze a pregame-only note; postgame review belongs after an existing snapshot')
    captured, source_issues = attachments(root, note)
    if source_issues:
        raise IngestionError('Cannot claim original attachment preservation with changed/missing bytes')
    result = check(note)
    files = {'note.json':raw, 'report.md':render(note, result).encode(),
             'framework.txt':(REPO / FRAMEWORK_PATH).read_bytes(),
             'refinements.md':(REPO / REFINEMENT_PATH).read_bytes(),
             'approval.md':(REPO / APPROVAL_PATH).read_bytes(), **captured}
    parent = private_root(private_root(root / 'pregame-snapshots') / note['id'])
    destination = snapshot_path(parent, label)
    try:
        destination.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise IngestionError('Pregame snapshot exists; overwrite forbidden') from exc
    manifest = {'format':'pregame-snapshot-1','session':note['id'],'label':label,
                'created_at':datetime.now(timezone.utc).isoformat(),'mode':note['mode'],
                'files':{key:{'sha256':digest(value),'size':len(value)} for key,value in files.items()},
                'engine_sha256':digest(encode({name:digest((Path(__file__).parent / name).read_bytes()) for name in ('review.py','calculations.py','catalog.py','storage.py')})),
                'findings':result['issues'], 'decision':note['decision'], 'lock_status':result['lock_status']}
    try:
        for key,value in files.items():
            write_exclusive(destination / key, value)
        write_exclusive(destination / 'manifest.json', encode(manifest))
        destination.chmod(0o500)
    except Exception:
        destination.chmod(0o700)
        shutil.rmtree(destination)
        raise
    return destination


def snapshot(root, session, label):
    parent = snapshot_path(private_root(root), 'pregame-snapshots')
    path = snapshot_path(snapshot_path(parent, session), label)
    if path != path.resolve() or path.is_symlink() or not path.is_dir():
        raise IngestionError('Unsafe snapshot')
    raw = read_file(path / 'manifest.json')
    m = decode(raw)
    keys = {'format','session','label','created_at','mode','files','engine_sha256','findings','decision','lock_status'}
    if not isinstance(m, dict) or set(m) != keys or not isinstance(m['files'], dict):
        raise IngestionError('Invalid snapshot manifest')
    if raw != encode(m) or m['format'] != 'pregame-snapshot-1' or m['session'] != session or m['label'] != label:
        raise IngestionError('Snapshot identity/encoding mismatch')
    required = {'note.json','report.md','framework.txt','refinements.md','approval.md'}
    names = set(m['files'])
    if not required <= names or any(key not in required and not re.fullmatch(r'source-[A-Za-z0-9_-]+\.bin', key) for key in names):
        raise IngestionError('Unexpected snapshot file mapping')
    if {p.name for p in path.iterdir()} != names | {'manifest.json'}:
        raise IngestionError('Missing/unexpected snapshot files')
    for key, expected in m['files'].items():
        if not isinstance(expected, dict) or set(expected) != {'sha256','size'} or not isinstance(expected['sha256'], str) or not re.fullmatch('[a-f0-9]{64}', expected['sha256']) or type(expected['size']) is not int or expected['size'] < 0:
            raise IngestionError('Invalid snapshot checksum mapping')
        value = read_file(path / key)
        if digest(value) != expected['sha256'] or len(value) != expected['size']:
            raise IngestionError('Snapshot checksum/size mismatch')
    frozen_note = decode(read_file(path / 'note.json'))
    if not isinstance(frozen_note, dict) or frozen_note.get('id') != session or frozen_note['decision'] != m['decision']:
        raise IngestionError('Snapshot decision differs from original note')
    return m, read_file(path / 'report.md').decode()


def report(root, name):
    root = private_root(root)
    note, result = assess(root, name)
    output = render(note, result)
    parent = root / 'pregame-snapshots' / note['id']
    if parent.exists():
        if parent != parent.resolve() or not parent.is_dir():
            raise IngestionError('Unsafe snapshot history')
        output += '\n## Frozen history (original findings, not current reassessments)\n\n'
        for child in sorted(parent.iterdir()):
            m, _ = snapshot(root, note['id'], child.name)
            codes = ', '.join(sorted({f['code'] for f in m['findings']})) or 'No original structural omissions'
            output += f'- {child.name}: original {m["decision"]["status"]}; {m["lock_status"]}; {codes}.\n'
    return output
