#!/usr/bin/env python3
"""Count c: company 1 conversations handled in a seed.

Company 1 is named only in counts/company.local.json (git-ignored; see company.example.json).
Nothing printed here names the company. A conversation counts only when it was handled in a seed
installation the platform installed for company 1's own Business.
"""
import json, os, sys
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, '..', 'lib'))
import score

path = os.path.join(here, 'company.local.json')
if not os.path.exists(path):
    score.count('c', 'NOT-MEASURED', 'company 1 mapping file is absent on this runner', 'counts/company.local.json')
company = json.load(open(path)).get('company_1') or {}
seed = company.get('happytohelp_installation_id')
if not seed:
    score.count('c', 'NOT-MEASURED', 'company 1 has no seed installation named in its mapping', 'counts/company.local.json')
score.count('c', 'NOT-MEASURED', 'HappyToHelp has no read-only conversation-count door', f'installation:{seed}')
