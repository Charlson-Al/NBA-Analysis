# Offline synthetic ingestion foundation

This pilot adds storage/validation only. It does not fetch NBA data, implement projections, normalize forecasts, score candidates or change V2.2. Only explicitly synthetic observed-statistics JSON envelopes are supported; do not import real research data. A synthetic marker is an operator assertion, not a detector of proprietary content.

## Run

Install `requirements.txt` in the development virtual environment. Run from the repository root with that environment activated:

```sh
# Set to an absolute, owner-only directory OUTSIDE every real Git checkout.
# The placeholder must be replaced; it is not a storage default.
export NBA_PRIVATE_DATA_ROOT='<absolute-private-directory>'
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m ingestion import \
  --source tests/fixtures/synthetic/observations-input.json \
  --metadata tests/fixtures/synthetic/metadata-input.json
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m ingestion verify synthetic-demo-1
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v
```

There is no default storage root. Relative paths, symlink components, checkout descendants/ancestors, other Git metadata and permissive directories are rejected. Empty managed-worker `.git` placeholder directories contain no checkout metadata and are not treated as repositories. The directory is created owner-only if absent. Existing permissive directories are rejected rather than silently changing their permissions. Source/inventory symlinks are rejected.

The input envelope is JSON with `synthetic: true` and an `observations` array. Each observation declares schema version, team/game/date, metric ID, exact unit/denominator, value/status, verification status, reason and original one-based array position. The two fixture teams and numbers are invented. Both `manual_upload` and `api_response_file` acquisition labels use this same envelope; arbitrary provider response schemas, CSV, PDFs and screenshots are not yet supported.

## Contract

- Three Draft 2020-12 schemas live in `manifests/schemas`: snapshot, observation and validation, each schema version 1.0. This is a storage schema version, not a framework version.
- The manifest preserves provider, source reference, supplied collection/provider-update timestamps, filters, source-specific metric definitions and acquisition method. The importer generates the actual UTC import timestamp. Unknown source times remain null. Never put credentials, signed URLs or personal account identifiers in metadata.
- Each snapshot is a new exclusive directory containing original.json (unchanged bytes), inventory.json, observations.json, manifest.json and validation.json. The importer records the supplied source file's basename as original_filename; it is not used as a storage path. No filenames are interpolated from untrusted source metadata.
- The manifest records SHA-256 and size for originals, inventory and deterministic observations. The validation report references the manifest checksum. Verification checks these links and reproduces observations and the entire report from the original plus pinned manifest. JSON duplicate keys, nonfinite numbers, schema violations, duplicate records, unknown metrics, incompatible units/denominators, conflicting game dates and incomplete declared team/game/metric coverage fail.
- `present` requires a numeric value. `missing`, `unavailable` and `not_applicable` require null plus a nonempty reason. Verification status is separate; parsing does not upgrade an observation's evidence quality.
- A cutoff remains unverified unless explicitly claimed verified AND supported by a separate inventory. Supply it with `--inventory`; its SHA-256 must match `cutoff.inventory_sha256`. It must declare synthetic provenance, independent_reference, matching season/type/through and the exact sorted included games with two team IDs each. All declared metrics must be present (possibly null/status-marked) for both teams of every game. No observation can exceed the requested date. The report preserves included games and latest date per team.
- Inventory independence/completeness is an asserted provenance requirement; the software verifies equality and scope, not the truth of an independently collected schedule. This synthetic proof does not certify real game coverage. Future real-source support needs independent authoritative inventory evidence and final-game status checks.
- Replay writes nothing and returns identical canonical observation bytes for an unchanged snapshot. Re-importing an existing ID fails without replacing it. Different IDs are separate acquisitions even if original bytes are identical. The same original/definitions/parser produce the same observations; generated import timestamps can make manifests differ across acquisitions.
- Successful artifacts are read-only (owner read), and their directory is owner read/execute. Partial write failures are cleaned up; process interruption may leave an incomplete directory that verification rejects and re-import will not overwrite. Verify before use. No active pointer or research-ready promotion is implemented.

## Public repository boundary

Keep all generated snapshots, manifests, inventories, reports and replay results outside Git. The repository contains only schemas, code, synthetic fixture inputs and documentation. Existing V1.2/source/framework files are untouched, and their redistribution rights remain a separate review.

`.gitignore` is a secondary defense. A conservative staged-file guard rejects data/binary extensions, generated artifact paths/names, JSON outside schemas or explicitly synthetic fixtures, and private absolute paths in documentation/JSON. Python code requires manual review for private paths and embedded data. Run:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m ingestion.public_guard
# Enable the supplied hook after checking for existing local hook configuration:
git config --local core.hooksPath .githooks
```

The guard examines staged blobs and prints no payloads. It is intentionally conservative: later legitimate changes to existing data or non-schema manifests need a separate review, not a broad relaxation. Hooks are local and bypassable; add required CI review before relying on this as an organization-wide control. No automatic upload/push is performed.

## Security and remaining prerequisites

Read-only permissions prevent accidental writes, not modifications by the same OS owner or administrators. SHA-256 detects corruption against recorded hashes; a coordinated rewrite of originals and all metadata is not detectable without an external trusted digest/signature. This is a trusted single-user local-filesystem pilot, not hostile concurrent-writer, WORM, encrypted or crash-atomic storage. Do not use shared/untrusted parent directories for real data. CLI failures suppress payloads/paths; library exceptions and operator logs still require private handling.

Cloud filesystem presence is not proof of durability. Before real data: establish persistent access-controlled storage/backups and retention rights, confirm publication policy, add source-specific parsers and coverage evidence, and separately authorize/test NBA access under applicable terms. Research-grade readiness and provenance authenticity are not inferred from a passing synthetic validation.
