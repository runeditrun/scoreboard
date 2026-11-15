#!/usr/bin/env python3
"""A change goes live the first time: the newest ordinary change requested on the named installation
reached the live product with no retry, and how long it took from request to Live.

PASS needs:
  public   the product answers /health ok;
  platform (viewer-only session) the installation is under the named Business with an acceptable
           owner; its newest ordinary change (not an update, not itself a retry) made at or after
           `since` is published, its release has a verified receipt, and neither the change's events
           nor a later change show a retry (Try again, Check again, Build again, a fix round, a checks
           rerun, or Ask for it again).
The line states request-to-Live minutes and, when recorded, publish-click-to-Live minutes.
"""
import json, os, sys
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
import score

# What the stage's change event log writes when a step had to happen again (read from real change histories):
# a second preview.build_requested (Try again), a second publish.requested (Build again), a fix round (the
# page handback), an explicit recheck/rebuild/checks rerun; and the failures an owner sees before a retry.
AGAIN_KINDS = ('preview.build_requested', 'publish.requested')
RETRY_KINDS = ('fix.requested', 'preview.deploy.rechecked', 'release.rebuild_requested', 'change.checks_rerun_requested')
FAILURE_KINDS = ('preview.deploy.failed', 'release.unreleased', 'fix.failed', 'preview.auto.failed')


def when(text):
    return datetime.fromisoformat(str(text).replace('Z', '+00:00').replace(' ', 'T'))


def minutes(a, b):
    return f'{(when(b) - when(a)).total_seconds() / 60:.1f}'


cfg = score.config()
t = cfg['steps']['CHANGE']
inst = t.get('installation_id')
if not inst:
    score.step('CHANGE', 'NOT-MEASURED', 'no installation is named for the change proof in config.json', 'config.json')
origin = cfg['stage']['platform_origin']

health, error = score.get_json(t['app_url'].rstrip('/') + '/health')
if health is None or (health.get('ok') is not True and health.get('status') != 'ok'):
    score.step('CHANGE', 'FAIL', f"product /health is not ok ({error or 'not ok'})", t['app_url'] + '/health')

session = score.viewer_session(cfg)
if not session:
    score.step('CHANGE', 'NOT-MEASURED', f"the change record needs secret {cfg['stage']['viewer_session_secret']}", f'installation:{inst}')
record, error = score.platform_installation(cfg, inst, session)
if record is None:
    score.step('CHANGE', 'NOT-MEASURED', error, f'installation:{inst}')
if record.get('business_id') != t['business_id']:
    score.step('CHANGE', 'FAIL', f"installation is not under Business {t['business_id']}", f'installation:{inst}')
owner_problem = score.owner_verdict(cfg, record)
if owner_problem:
    score.step('CHANGE', 'FAIL', owner_problem, f'installation:{inst}')

body, error = score.get_json(f'{origin}/api/installations/{inst}/changes', session)
if body is None:
    score.step('CHANGE', 'NOT-MEASURED', f'change list read failed ({error})', f'installation:{inst}/changes')
changes = body.get('changes') or []
since = t.get('since') or '1970-01-01T00:00:00Z'
ordinary = [c for c in changes if not c.get('update') and not c.get('retryOf') and when(c['created_at']) >= when(since)]
if not ordinary:
    score.step('CHANGE', 'FAIL', f'no ordinary change requested since {since} ({len(changes)} changes in all)', f'installation:{inst}/changes')
change = max(ordinary, key=lambda c: when(c['created_at']))
cid, requested = change['id'], change['created_at']
evidence = f'installation:{inst}/changes/{cid}'

events, after = [], 0
for _ in range(20):
    page, error = score.get_json(f'{origin}/api/changes/{cid}/events?after={after}', session)
    if page is None:
        score.step('CHANGE', 'NOT-MEASURED', f'change event read failed ({error})', evidence)
    batch = page.get('events') or []
    events += batch
    if len(batch) < 200:
        break
    after = page.get('cursor', after)
kinds = [e.get('kind', '') for e in events]
retries = [k for k in kinds if k in RETRY_KINDS + FAILURE_KINDS]
retries += [f'{k} (again)' for k in AGAIN_KINDS for _ in range(max(0, kinds.count(k) - 1))]
retries += [f"ask again {c['id']}" for c in changes if c.get('retryOf') == cid]

linkage = change.get('releaseLinkage') or {}
if linkage.get('state') != 'published':
    state = change.get('status')
    why = f"; retries so far: {', '.join(retries[:4])}" if retries else ''
    score.step('CHANGE', 'FAIL', f'change requested at {requested} is not live (change {state}, release {linkage.get("state")}){why}', evidence)

releases, error = score.get_json(f'{origin}/api/delivery/installations/{inst}/releases', session)
if releases is None:
    score.step('CHANGE', 'NOT-MEASURED', f'release read failed ({error})', evidence)
release = next((r for r in releases.get('releases') or [] if r.get('id') == linkage.get('releaseId')), None)
receipt = (release or {}).get('receipt') or (release or {}).get('receipt_json') or {}
if isinstance(receipt, str):
    try:
        receipt = json.loads(receipt)
    except ValueError:
        receipt = {}
live = receipt.get('verifiedAt') if isinstance(receipt, dict) else None
if not live:
    score.step('CHANGE', 'NOT-MEASURED', f"release {linkage.get('releaseId')} states no verified time", evidence)

clicks = [e.get('createdAt') for e in events if e.get('kind') == 'publish.requested' and e.get('createdAt')]
publish = f', publish click to Live {minutes(clicks[0], live)} min' if clicks else ''
timing = f'requested {requested}, Live {live}: {minutes(requested, live)} min{publish}'
if retries:
    score.step('CHANGE', 'FAIL', f"{timing}, but not first time ({len(retries)} retry or failure events): {', '.join(retries[:4])}", evidence)
score.step('CHANGE', 'PASS', f'{timing}, no retry', evidence)
