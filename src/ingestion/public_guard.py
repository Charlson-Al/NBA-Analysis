"""Review staged paths/blobs before a public commit. No network or data output."""
from pathlib import PurePosixPath
import json
import re
import subprocess


def allowed(path, blob):
    """Conservative boundary for newly staged ingestion work; not a rights detector."""
    p = PurePosixPath(path)
    if any(x in p.parts for x in ('snapshots', 'derived', 'private-data', 'acquisition-events')):
        return False
    if p.name in ('original.json', 'observations.json', 'inventory.json', 'manifest.json', 'validation.json'):
        return False
    if p.suffix in ('.csv', '.docx', '.pdf', '.png', '.jpg', '.parquet', '.zip'):
        return False
    if not (path.startswith(('src/', 'tests/', 'docs/', 'manifests/schemas/')) or path in ('.gitignore', 'requirements.txt', 'README.md', '.githooks/pre-commit')):
        return False
    try:
        text = blob.decode('utf-8')
    except UnicodeError:
        return False
    if p.suffix != '.py' and re.search(r'(?:/workspace/|/home/|/Users/|/tmp/|[A-Za-z]:\\Users\\)', text):
        return False
    if p.suffix == '.json':
        try:
            value = json.loads(text)
        except ValueError:
            return False
        if path.startswith('manifests/schemas/'):
            return isinstance(value, dict) and value.get('$schema') == 'https://json-schema.org/draft/2020-12/schema'
        if path.startswith('tests/fixtures/synthetic/'):
            return isinstance(value, dict) and value.get('synthetic') is True
        return False
    return True


def main():
    files = subprocess.check_output(['git', 'diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z']).decode().split('\0')
    failures = []
    for name in filter(None, files):
        blob = subprocess.check_output(['git', 'show', f':{name}'])
        if not allowed(name, blob):
            failures.append(name)
    if failures:
        print('Public commit guard rejected staged content; review paths and rights privately.')
        return 1
    print('Public commit guard passed; manual rights review remains required.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
