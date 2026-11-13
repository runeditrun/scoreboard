#!/usr/bin/env python3
"""Count d: updates applied through the platform with no fleet hands.

For every installation named in config.json, counts the click..Live windows in its platform event
log with no person and no repair-shaped event after the click (the same rule as the update proof).
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
import score

cfg = score.config()
session = score.viewer_session(cfg)
if not session:
    score.count('d', 'NOT-MEASURED', f"event logs need secret {cfg['stage']['viewer_session_secret']}", 'stage:/api/installations/:id/events')
targets = {t['installation_id']: t['business_id'] for t in cfg['steps'].values() if t.get('installation_id')}
clean, read = 0, []
for inst, business in targets.items():
    record, error = score.platform_installation(cfg, inst, session)
    log = None
    if record is not None:
        log, error = score.events(cfg, inst, session)
    if log is None:
        score.count('d', 'NOT-MEASURED', f'installation {inst}: {error}', f'installation:{inst}/events')
    clean += sum(1 for w in score.update_windows(cfg, log, record.get('owner_id')) if w['live'] and not w['hands'])
    read.append(inst[:8])
score.count('d', str(clean), f"hands-free updates across {len(read)} installation(s): {','.join(read)}", 'stage:/api/installations/:id/events')
