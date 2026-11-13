#!/usr/bin/env python3
"""Step 2: that company attaches its own addresses to a product the platform hosts.

PASS needs, for every address named in config.json steps.2.company_addresses:
  public   the address is not a platform default host, answers /health ok over verified TLS, and
           serves the same platform release receipt (/__rer/release) as the installation's own
           platform address (so a hand-built copy on the same name cannot pass);
  platform (viewer-only session) the installation is under the named Business with an acceptable owner.
No named address is FAIL: the rung has no proof to read.
"""
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
import score

cfg = score.config()
t = cfg['steps']['2']
inst = t['installation_id']
addresses = t.get('company_addresses') or []

if not addresses:
    score.step('2', 'FAIL', f'no company address is named for installation {inst}; the platform default host is not company-address proof', f'installation:{inst}')
expected, error = score.release_identity(t['app_url'])
if not expected:
    score.step('2', 'FAIL', f'installation platform address serves no release receipt ({error})', t['app_url'] + '/__rer/release')
for address in addresses:
    origin = address if address.startswith('https://') else 'https://' + address
    host = origin.split('/')[2]
    if re.search(cfg['platform_default_host_pattern'], host):
        score.step('2', 'FAIL', f'{host} is a platform default host, not a company address', origin)
    failure, _ = score.product_health(origin)
    if failure and 'states no version' not in failure:  # version is step 1's and P2's assertion
        score.step('2', 'FAIL', f'{host}: {failure}', origin + '/health')
    digest, error = score.release_identity(origin)
    if digest != expected:
        score.step('2', 'FAIL', f'{host} does not serve the installation release ({error or digest})', origin + '/__rer/release')

session = score.viewer_session(cfg)
if not session:
    score.step('2', 'NOT-MEASURED', f"{len(addresses)} address(es) serve the installation; Business and owner need secret {cfg['stage']['viewer_session_secret']}", f'release:{expected}')
record, error = score.platform_installation(cfg, inst, session)
if record is None:
    score.step('2', 'NOT-MEASURED', error, f'installation:{inst}')
if record.get('business_id') != t['business_id']:
    score.step('2', 'FAIL', f"installation is not under Business {t['business_id']}", f'installation:{inst}')
owner_problem = score.owner_verdict(cfg, record)
if owner_problem:
    score.step('2', 'FAIL', owner_problem, f'installation:{inst}')
score.step('2', 'PASS', f"{len(addresses)} company address(es) serve release {expected[:12]} of the named installation", f'installation:{inst}')
