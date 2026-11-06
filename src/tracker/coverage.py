"""Create unreviewed bookkeeping rows, never research conclusions."""
from ingestion.store import digest, encode
from .catalog import MARKETS
from .journal import append, load


def seed_coverage(session_id, *, root=None):
    events = load(session_id, root=root)
    latest = {e['record']['entity_id']: e['record'] for e in events}
    session = events[0]['record']['data']
    existing = {(r['data']['player'], r['data']['market']) for r in latest.values() if r['kind'] == 'coverage'}
    count = 0
    for player in session['players']:
        for market in MARKETS:
            if (player['id'], market) in existing:
                continue
            key = 'coverage-' + digest(encode([player['id'], market]))[:24]
            append(session_id, {'kind':'coverage','entity_id':key,'basis':[events[0]['event_id']],
                               'data':{'player':player['id'],'market':market,
                                       'higher_reviewed':False,'lower_reviewed':False,
                                       'market_status':'not_searched','opportunity_evidence_ids':[],
                                       'advance_reasons':[],'disagreement_investigation':None,
                                       'disposition':'not_started','rationale':'Unreviewed bookkeeping row; analyst action required'}},root=root)
            count += 1
    return count
