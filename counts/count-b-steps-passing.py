#!/usr/bin/env python3
"""Count b: ladder steps passing, out of the steps that have a script.

Usage: count-b-steps-passing.py STEP_LINES_FILE   (the lines this run's step scripts printed)
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
import score

if len(sys.argv) < 2 or not os.path.exists(sys.argv[1]):
    score.count('b', 'NOT-MEASURED', 'no step results from this run', 'steps/')
lines = [l.split() for l in open(sys.argv[1]) if l.startswith('STEP ')]
passing = [l[1] for l in lines if l[2] == 'PASS']
score.count('b', f'{len(passing)}/{len(lines)}', 'ladder steps passing: ' + (','.join(passing) or 'none'), 'steps/')
