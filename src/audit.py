"""Read-only provenance and fidelity audit for NBA Analysis Hub V1.2.

Never replaces missing source values, estimates cutoffs, or corrects data automatically.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from datetime import date
from pathlib import Path

from docx import Document

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / 'data/source/NBA_Team_Stats_2026-27_Download.csv'
DOCX_PATH = ROOT / 'data/source/NBA_Team_Profiles_2026-27_V1.2.docx'
REPORT_PATH = ROOT / 'reports/audit.json'

# Maps each DOCX team section's numeric tables to the corresponding CSV fields.
MAP = [
    [ # table 1: adjusted ratings
        ('adjusted_off_rating',1,0), ('adjusted_def_rating',1,1),
        ('adjusted_net_rating',1,2), ('pace',1,3), ('strength_of_schedule',1,4),
    ],
    [ # table 2: Four Factors
        ('off_efg_pct',1,1), ('def_allowed_efg_pct',1,2),
        ('off_tov_pct',2,1), ('def_forced_tov_pct',2,2),
        ('off_oreb_pct',3,1), ('def_opponent_oreb_pct',3,2),
        ('off_ftr',4,1), ('def_allowed_ftr',4,2),
    ],
    [ # table 3: six play contexts, offense and defense
        ('off_transition_frequency_pct',1,1), ('off_transition_eff_pts_per_100_plays',1,2),
        ('def_opp_transition_frequency_pct',1,3), ('def_opp_transition_eff_pts_per_100_plays',1,4),
        ('early_off_freq_pct',2,1), ('early_off_eff_per100plays',2,2),
        ('def_early_freq_pct',2,3), ('def_early_eff_per100plays',2,4),
        ('off_halfcourt_frequency_pct',3,1), ('off_halfcourt_eff_pts_per_100_plays',3,2),
        ('def_opp_halfcourt_frequency_pct',3,3), ('def_opp_halfcourt_eff_pts_per_100_plays',3,4),
        ('midclock_freq_pct',4,1), ('midclock_eff_per100plays',4,2),
        ('def_midclock_freq_pct',4,3), ('def_midclock_eff_per100plays',4,4),
        ('lateclock_freq_pct',5,1), ('lateclock_eff_per100plays',5,2),
        ('def_lateclock_freq_pct',5,3), ('def_lateclock_eff_per100plays',5,4),
        ('putback_freq_pct',6,1), ('putback_eff_per100plays',6,2),
        ('def_putback_freq_pct',6,3), ('def_putback_eff_per100plays',6,4),
    ],
    [ # table 4: opportunity tracking
        ('potential_assists_per_game',1,0), ('assist_conversion_pct',1,1),
        ('secondary_assists_per_game',1,2), ('rebound_chances_per_game',1,3),
        ('def_rebound_chances_per_game',1,4), ('rebound_conversion_pct',1,5),
    ],
]

EXPECTED = {'ATL','BKN','BOS','CHA','CHI','CLE','DAL','DEN','DET','GSW','HOU','IND','LAC','LAL','MEM',
            'MIA','MIL','MIN','NOP','NYK','OKC','ORL','PHI','PHX','POR','SAC','SAS','TOR','UTA','WAS'}


def parse_number(s: str) -> float:
    """Only strip literal display suffixes, never reinterpret denominators."""
    s = s.strip().replace(',', '')
    if s.endswith(' forced'):
        s = s[:-7]
    if s.endswith(' allowed'):
        s = s[:-8]
    return float(s.rstrip('%'))


def inspect(csv_path: Path = CSV_PATH, docx_path: Path = DOCX_PATH) -> dict:
    with csv_path.open(newline='', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    result = {'source_csv':csv_path.name,'source_docx':docx_path.name,'teams':len(rows),
              'columns':len(rows[0]) if rows else 0, 'checks':0,'matched':0,'mismatches':[],
              'errors':[], 'warnings':[], 'blocked_for_game_day': True}
    teams = [r['team'] for r in rows]
    if len(rows) != 30 or set(teams) != EXPECTED or len(set(teams)) != len(teams):
        result['errors'].append({'type':'coverage','teams':teams})
    if not rows:
        return result
    for row in rows:
        team = row['team']
        for flag in ('new_metrics_exact_game_cutoff_verified','def_context_exact_cutoff_verified'):
            if row.get(flag, '').lower() != 'true':
                result['warnings'].append({'team':team,'field':flag,'reason':'exact cutoff unverified'})
        if row.get('cutoff_verified','').lower() not in ('true','verified'):
            result['warnings'].append({'team':team,'field':'cutoff_verified','reason':'source-specific cutoff unverified'})
        if row.get('shot_zone_status','').strip():
            result['warnings'].append({'team':team,'field':'shot_zone_status','reason':row['shot_zone_status']})
        if row.get('personnel_status','').strip():
            result['warnings'].append({'team':team,'field':'personnel_status','reason':row['personnel_status']})
        for key, val in row.items():
            if key.endswith('_pct') and val:
                try:
                    n=float(val)
                    if not (0 <= n <= 100):
                        result['errors'].append({'team':team,'field':key,'reason':'percentage outside 0..100','value':val})
                except ValueError:
                    result['errors'].append({'team':team,'field':key,'reason':'not numeric','value':val})
        # Ratings may have rounding differences, so only warn rather than rewrite.
        try:
            implied=float(row['adjusted_off_rating'])-float(row['adjusted_def_rating'])
            if abs(implied - float(row['adjusted_net_rating'])) > 0.16:
                result['warnings'].append({'team':team,'field':'adjusted_net_rating',
                                           'reason':'difference exceeds expected one-decimal rounding tolerance'})
        except (ValueError, KeyError):
            result['errors'].append({'team':team,'reason':'missing adjusted rating'})
    document = Document(docx_path)
    tables = document.tables
    if len(tables) != 151:
        result['errors'].append({'type':'docx_layout','reason':f'Expected 151 tables (overview + 5 per team), found {len(tables)}'})
        return result
    for i, row in enumerate(rows):
        # We verify 43 numeric fields/team represented in the first 4 team tables.
        for t_index, specs in enumerate(MAP):
            table = tables[1 + i*5 + t_index]
            for field, r, c in specs:
                result['checks'] += 1
                observed = table.cell(r,c).text.strip()
                expected = row[field].strip()
                try:
                    a, b = parse_number(observed), float(expected)
                    identical = math.isclose(a,b,rel_tol=0,abs_tol=0.000001)
                except ValueError:
                    identical = False
                if identical:
                    result['matched'] += 1
                else:
                    result['mismatches'].append({'team':row['team'],'field':field,
                                                 'csv':expected,'docx':observed})
    result['checked_fields_per_team'] = sum(map(len,MAP))
    result['pass_numeric_reconciliation'] = result['checks'] == result['matched'] and not result['errors']
    result['warning_counts'] = dict(Counter(w['field'] for w in result['warnings']))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description='Audit V1.2 CSV against source DOCX. Read-only.')
    parser.add_argument('--csv',type=Path,default=CSV_PATH)
    parser.add_argument('--docx',type=Path,default=DOCX_PATH)
    parser.add_argument('--output',type=Path,default=REPORT_PATH)
    args = parser.parse_args()
    report = inspect(args.csv,args.docx)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(f"Teams: {report['teams']} | columns: {report['columns']} | numeric matches: {report['matched']}/{report['checks']}")
    print(f"Errors: {len(report['errors'])} | mismatches: {len(report['mismatches'])} | warnings: {len(report['warnings'])}")
    print(f"Game-day-ready: {not report['blocked_for_game_day']}")
    print(f"Report: {args.output}")
    if not report.get('pass_numeric_reconciliation'):
        raise SystemExit(1)


if __name__=='__main__':
    main()
