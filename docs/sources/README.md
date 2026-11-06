# Source definitions and validation scope

The governing source responsibilities are in [V2.2 §VI](../framework/source/nba-player-props-v2.2-2026-11-03.txt). DC supplies game-specific forecasts/minutes/uncertainty; DARKO supplies sustainable statistical benchmarks, with DPM for impact context only. Official NBA supplies personnel/logs; Hoops Junkie opportunity tracking; Databallr environment/access/resistance; Hashtag Basketball/RotoWire rotations; team profiles historical context; KEEL historical/postgame verification. PropSims, PBP Stats and BoxScore Lab CSV remain excluded.

Preserve source dates, sample sizes, statistical denominators, filters, personnel context and model freshness. Distinguish observed rates, model outputs, independently verified data, inference and missing evidence. Do not treat overlapping samples as independent confirmation. Permitted alternative sources do not authorize scraping restricted or authenticated sources.

Framework source bytes, original names and SHA-256 values are recorded in [the manifest](../../manifests/framework-sources.json). The original CSV and V1.2 DOCX remain unchanged under data/source. V1.2 identifies a team-statistical reference snapshot, not the governing analytical framework.

The existing audit compares 43 numeric fields × 30 teams (1,290 comparisons), checks team coverage and percentage ranges, and tests tampering detection. It does not validate V2.2 execution or historical approval. Eighteen other CSV columns, archival shot-zone tables, narrative conclusions, source authenticity, exact last-game cutoffs and game-day personnel remain outside numeric reconciliation. A passing audit does not make this data game-day-ready.

Future dataset manifests should record immutable snapshot path/checksum, provider/URL, collection time, source update time, last included game, season/window, units/denominator, filters, verification evidence and limitations. These fields are proposed documentation requirements; no ingestion or transformation code is added.
