"""Offline CLI; emits no payloads or private filesystem paths."""
import argparse
import sys

from .store import IngestionError, decode, import_snapshot, read_file, verify
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    imp = commands.add_parser('import')
    imp.add_argument('--source', required=True)
    imp.add_argument('--metadata', required=True)
    imp.add_argument('--inventory')
    check = commands.add_parser('verify')
    check.add_argument('snapshot_id')
    args = parser.parse_args()
    try:
        if args.command == 'import':
            import_snapshot(args.source, decode(read_file(Path(args.metadata))), inventory=args.inventory)
        else:
            verify(args.snapshot_id)
    except (IngestionError, OSError, TypeError, KeyError):
        # Do not expose source rows, local paths or exception payloads in public logs.
        print('Rejected: input, integrity, schema, or private-storage validation failed.', file=sys.stderr)
        return 1
    print('Offline synthetic snapshot validation passed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
