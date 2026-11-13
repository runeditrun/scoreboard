#!/usr/bin/env python3
"""Update proof (P2): one update taken by a click on the installed product, with no fleet action
between the click and Live, shown by the platform's event log.

PASS needs:
  public   the product's /health states a version at or above the configured minimum (the release
           that carries the version on health);
  platform (viewer-only session) the installation is under the named Business with an acceptable
           owner, and its event log holds a click by the installation owner followed by a Live event
           with no person and no repair-shaped event in between (config.json event_log patterns).
An update an agent repaired is FAIL with the repair named.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
import score

cfg = score.config()
t = cfg['steps']['P2']
inst = t['installation_id']

failure, health = score.product_health(t['app_url'], minimum_version=t.get('minimum_version'))
if failure:
    score.step('P2', 'FAIL', failure, t['app_url'] + '/health')

session = score.viewer_session(cfg)
if not session:
    score.step('P2', 'NOT-MEASURED', f"health states {health.get('buildVersion')}; the event log needs secret {cfg['stage']['viewer_session_secret']}", f'installation:{inst}')
record, error = score.platform_installation(cfg, inst, session)
if record is None:
    score.step('P2', 'NOT-MEASURED', error, f'installation:{inst}')
if record.get('business_id') != t['business_id']:
    score.step('P2', 'FAIL', f"installation is not under Business {t['business_id']}", f'installation:{inst}')
owner_problem = score.owner_verdict(cfg, record)
if owner_problem:
    score.step('P2', 'FAIL', owner_problem, f'installation:{inst}')
log, error = score.events(cfg, inst, session)
if log is None:
    score.step('P2', 'NOT-MEASURED', error, f'installation:{inst}')

windows = score.update_windows(cfg, log, record.get('owner_id'))
clean = [w for w in windows if w['live'] and not w['hands']]
if clean:
    w = clean[-1]
    score.step('P2', 'PASS', f"click {w['click']['type']} at {w['click']['created_at']} to {w['live']['type']} at {w['live']['created_at']}, no fleet actor", f"installation:{inst}/events/{w['click']['sequence']}-{w['live']['sequence']}")
if not windows:
    score.step('P2', 'FAIL', f'event log ({len(log)} events) holds no update click by the owner', f'installation:{inst}/events')
w = windows[-1]
if not w['live']:
    score.step('P2', 'FAIL', f"update clicked at {w['click']['created_at']} has not reached Live", f"installation:{inst}/events/{w['click']['sequence']}")
named = ', '.join(f'{kind} by {actor}' for kind, actor in w['hands'][:3])
score.step('P2', 'FAIL', f'fleet or repair action between click and Live: {named}', f"installation:{inst}/events/{w['click']['sequence']}-{w['live']['sequence']}")
