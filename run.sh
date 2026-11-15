#!/usr/bin/env bash
# Run every step and count, print their lines, and write out/latest.json plus a dated copy.
# Exit 0 when the scoreboard was written (FAIL and NOT-MEASURED are results, not run errors).
set -u
cd "$(dirname "$0")"
mkdir -p out
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
utc() { date -u +%Y-%m-%dT%H:%M:%SZ; }
run_one() { # kind id script [args]: a script that crashes or prints no line is NOT-MEASURED, never skipped
  local kind=$1 id=$2 script=$3; shift 3
  local line
  line=$(python3 "$script" "$@" 2>"$work/err" | grep -E "^$kind $id " | tail -1)
  if [ -z "$line" ]; then
    local why
    why=$(tail -1 "$work/err" | tr -cd '[:alnum:] ._:-' | cut -c1-100)
    if [ "$kind" = STEP ]; then line="STEP $id NOT-MEASURED script error: ${why:-no output} $script $(utc)"
    else line="COUNT $id NOT-MEASURED script error: ${why:-no output} $script $(utc)"; fi
  fi
  echo "$line"
}
run_utc=$(utc)
for id in 1 2 3 p2 change; do
  run_one STEP "$(echo $id | tr a-z A-Z)" "steps/step-$id.py"
done | tee "$work/steps.txt"
{
  run_one COUNT a counts/count-a-outside-use.py
  run_one COUNT b counts/count-b-steps-passing.py "$work/steps.txt"
  run_one COUNT c counts/count-c-company1-conversations.py
  run_one COUNT d counts/count-d-hands-free-updates.py
} | tee "$work/counts.txt"
python3 - "$run_utc" "$work/steps.txt" "$work/counts.txt" <<'PY'
import json, subprocess, sys
run_utc, steps_file, counts_file = sys.argv[1:4]
def parse(line):
    t = line.split()
    return t[0], t[1], t[2], ' '.join(t[3:-2]), t[-2], t[-1]
steps = []
for line in open(steps_file):
    if line.startswith('STEP '):
        _, ident, status, reason, evidence, at = parse(line)
        steps.append({'step': ident, 'status': status, 'reason': reason, 'evidence': evidence, 'utc': at})
counts = []
names = {'a': 'days since anyone outside the owner used a product', 'b': 'ladder steps passing',
         'c': 'company 1 conversations handled in a seed', 'd': 'updates applied through the platform with no fleet hands'}
for line in open(counts_file):
    if line.startswith('COUNT '):
        _, ident, value, note, source, at = parse(line)
        counts.append({'count': ident, 'name': names.get(ident, ident), 'value': value, 'note': note, 'source': source, 'utc': at})
rev = subprocess.run(['git', 'rev-parse', '--verify', '-q', 'HEAD'], capture_output=True, text=True)
commit = rev.stdout.strip() if rev.returncode == 0 else None
calendar = json.load(open('calendar.json'))
doc = {'run_utc': run_utc, 'config_commit': commit, 'steps': steps, 'counts': counts,
       'calendar': calendar['dates'], 'calendar_yields': calendar['yields']}
text = json.dumps(doc, indent=2) + '\n'
open('out/latest.json', 'w').write(text)
open(f"out/{run_utc.replace(':', '')}.json", 'w').write(text)
print(f'wrote out/latest.json and out/{run_utc.replace(":", "")}.json')
PY
