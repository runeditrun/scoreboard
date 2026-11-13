#!/usr/bin/env python3
"""Step 3: that company imports legacy history through the product.

The import's result (rows equal the package, resume without repeats) is recorded inside HappyToHelp
and is readable only after an owner signs in; there is no read-only door for it. So this step can
only FAIL (step 1 has no Live HappyToHelp installation to import into) or be NOT-MEASURED.
"""
import os, subprocess, sys
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, '..', 'lib'))
import score

cfg = score.config()
inst = cfg['steps'][cfg['steps']['3']['uses_step']]['installation_id']
prior = subprocess.run([sys.executable, os.path.join(here, 'step-1.py')], capture_output=True, text=True, timeout=300)
if prior.returncode == 1:
    reason = prior.stdout.split(' FAIL ', 1)[-1].rsplit(' ', 2)[0] if ' FAIL ' in prior.stdout else 'step 1 fails'
    score.step('3', 'FAIL', f'no Live HappyToHelp to import into (step 1: {reason})', f'installation:{inst}')
score.step('3', 'NOT-MEASURED', 'import completion is readable only inside the product after owner sign-in; no read-only door exists', f'installation:{inst}')
