"""Offline private research notes. Commands never finalize analytical selections."""
import argparse
from datetime import datetime, timezone
import sys

from ingestion.store import IngestionError, REPO, decode, encode, private_root, snapshot_path
from .catalog import APPROVAL_REFERENCE, FRAMEWORK_SHA
from .review import effective
from .storage import assess, freeze, report, snapshot, write_exclusive


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', help='Owner-only external root or NBA_PRIVATE_DATA_ROOT')
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('new','example'):
        p = commands.add_parser(name)
        p.add_argument('session')
    for name in ('check','report','freeze'):
        p = commands.add_parser(name)
        p.add_argument('note', help='Relative JSON note filename in private root')
        if name == 'freeze':
            p.add_argument('label', help='Human-readable exclusive snapshot label')
    p = commands.add_parser('snapshot')
    p.add_argument('session'); p.add_argument('label')
    args = parser.parse_args(argv)
    try:
        root = private_root(args.root)
        if args.command in ('new','example'):
            note = decode((REPO / 'tests/fixtures/synthetic/research-note.json').read_bytes())
            note['id'] = args.session
            if args.command == 'new':
                now = datetime.now(timezone.utc).isoformat()
                note.update(synthetic=False,mode='prospective',research_at=now,
                            authority=dict(rules_used_sha256=FRAMEWORK_SHA,approval_reference=APPROVAL_REFERENCE,refinements=effective(now)),
                            players=[],roster_note=None,sources={},matchups={},projections=[],candidates=[],risks=[],comparisons=[],correlation=None,
                            lock_review=dict(at=None,sources=[],note=None),
                            decision=dict(status='research',at=None,selected=[],reason=None),placement=dict(status='unconfirmed',sources=[]))
            path = snapshot_path(root, args.session).with_suffix('.json')
            write_exclusive(path, encode(note), mode=0o600)
            print('Editable private note created. No analytical decisions assigned.')
            return 0
        if args.command == 'freeze':
            freeze(root, args.note, args.label)
            print('Exclusive pregame snapshot saved, including original findings. No selection finalized by software.')
            return 0
        if args.command == 'snapshot':
            _, output = snapshot(root, args.session, args.label)
        elif args.command == 'report':
            output = report(root, args.note)
        else:
            _, result = assess(root, args.note)
            print(f'Structural findings: {len(result["issues"])}. Analytical review is always required.')
            return 2 if result['issues'] else 0
        # Explicit report command renders private research; user must keep its output private.
        print(output)
        return 0
    except (IngestionError, OSError, ValueError, TypeError, KeyError, RecursionError):
        print('Rejected: invalid note, unsafe private storage or snapshot integrity. Inspect privately.',file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
