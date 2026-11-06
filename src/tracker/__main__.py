"""Private offline execution records. Payloads and filesystem paths stay out of CLI logs."""
import argparse
import os
import sys
import uuid

from ingestion.store import IngestionError, decode, private_root, read_file
from pathlib import Path
from .journal import append, create, load, at_event
from .review import render, review
from .coverage import seed_coverage


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', help='Explicit owner-only external storage, or NBA_PRIVATE_DATA_ROOT')
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('init', 'append'):
        command = commands.add_parser(name)
        command.add_argument('session')
        command.add_argument('--record', required=True, help='JSON tracker input record')
    seed = commands.add_parser('seed-coverage', help='Create unreviewed eight-market rows for the declared roster')
    seed.add_argument('session')
    for name in ('check', 'report'):
        command = commands.add_parser(name)
        command.add_argument('session')
        command.add_argument('--at', help='Read-only report/check at an original event ID')
    args = parser.parse_args(argv)
    try:
        if args.command == 'seed-coverage':
            count = seed_coverage(args.session, root=args.root)
            print(f'Unreviewed coverage rows appended: {count}. No analytical assessments assigned.')
            return 0
        if args.command in ('init', 'append'):
            record = decode(read_file(Path(args.record)))
            operation = create if args.command == 'init' else append
            event = operation(args.session, record, root=args.root)
            print(f'Tracker event appended: {event["event_id"]}.')
            warnings, _, _ = review(load(args.session, root=args.root))
            print(f'Mechanical warnings: {len(warnings)}. Original record retained for review.')
            return 2 if warnings else 0
        events = load(args.session, root=args.root)
        if args.at:
            events = at_event(events, args.at)
        warnings, _, _ = review(events)
        if args.command == 'report':
            # Unique report outside the journal; no user payload rendered to stdout.
            reports = private_root(private_root(args.root) / 'tracker-reports')
            output = reports / (uuid.uuid4().hex + '.md')
            try:
                with output.open('xb') as stream:
                    os.chmod(output, 0o600)
                    stream.write(render(events).encode())
                    stream.flush()
                    os.fsync(stream.fileno())
                output.chmod(0o400)
            except Exception:
                output.unlink(missing_ok=True)
                raise
            print('Checklist saved in private tracker-reports directory.')
        print(f'Mechanical warnings: {len(warnings)}. Human review remains required.')
        return 2 if warnings else 0
    except (IngestionError, OSError, ValueError, TypeError, KeyError, RecursionError):
        print('Rejected: invalid records, integrity, schema or private storage. Inspect privately.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
