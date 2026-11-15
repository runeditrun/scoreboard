#!/usr/bin/env python3
"""Step 1: a stand-in company installs HappyToHelp through its Business on the stage.

PASS needs all of, from outside:
  public   the product answers /health ok on its platform address, states the expected version,
           and serves a platform release receipt (/__rer/release);
  platform (viewer-only session) the installation sits under the named Business, its claimed owner
           is not an unnamed fleet identity, and the release it serves is the one the platform records.
A failed public check is FAIL without any credential; a missing credential is NOT-MEASURED.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
import score

cfg = score.config()
t = cfg['steps']['1']
inst = t['installation_id']

failure, health = score.product_health(t['app_url'], t.get('expected_version'), t.get('expected_commit'))
if failure:
    score.step('1', 'FAIL', failure, t['app_url'] + '/health')
digest, error = score.release_identity(t['app_url'])
if not digest:
    score.step('1', 'FAIL', f'no platform release receipt on the product address ({error})', t['app_url'] + '/__rer/release')

session = score.viewer_session(cfg)
if not session:
    score.step('1', 'NOT-MEASURED', f"public checks pass; Business, owner and release need secret {cfg['stage']['viewer_session_secret']}", f'release:{digest}')
record, error = score.platform_installation(cfg, inst, session)
if record is None:
    score.step('1', 'NOT-MEASURED', error, f'installation:{inst}')

if record.get('business_id') != t['business_id']:
    score.step('1', 'FAIL', f"installation is not under Business {t['business_id']}", f'installation:{inst}')
owner_problem = score.owner_verdict(cfg, record)
if owner_problem:
    score.step('1', 'FAIL', owner_problem, f'installation:{inst}')
current = (record.get('state') or {}).get('currentRelease') or {}
if not current.get('verifiedAt'):
    score.step('1', 'FAIL', 'platform records no verified release (not Live)', f'installation:{inst}')
if current.get('id') != digest:
    score.step('1', 'FAIL', 'product serves a release the platform does not record as current', f'installation:{inst}')
version = health.get('buildVersion') or (health.get('release') or {}).get('version') or (health.get('deployment') or {}).get('sourceSha')
score.step('1', 'PASS', f"{t['product']} {version} Live under the named Business, verified {current['verifiedAt']}", f'installation:{inst}')
