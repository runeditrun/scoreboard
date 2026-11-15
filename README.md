# RER scoreboard

A scoreboard the fleet's own sessions do not write. One short script per ladder step asserts the
outcome from outside, through public doors and one read-only credential, and four dated counts sit
beside them. Each run prints PASS, FAIL or NOT-MEASURED per step and writes `out/latest.json`.

The ladder is section 8 of the platform plan of record (12 Nov 2026). Steps 1-3, the update proof
(P2) and the change proof (CHANGE) have scripts. Rungs 4-8 (production carries 1-3, company 1's Business shows its products, its
data is in, cutovers pressed, a second company repeats it) have none yet.

## Rules every script keeps

- Outcomes only, from public or read-only doors. Nothing writes to any service, mints a token or
  changes DNS. HTTP redirects are never followed, so a credential never travels to another host.
- No mock or fallback results. A script that cannot read its source prints NOT-MEASURED with the
  reason, never an old or assumed value. A public check that fails is FAIL even without a credential.
- One line each, exit code 0 PASS, 1 FAIL, 2 NOT-MEASURED:
  `STEP <n> PASS|FAIL|NOT-MEASURED <reason> <evidence-url-or-id> <utc>`
  `COUNT <id> <value|NOT-MEASURED> <note> <source> <utc>`
- Targets (Business, installation, address, expected version) are in `config.json`. Fleet-held
  stand-in owner addresses are named there in `identities.standin_owner_addresses`, accepted only for
  the stage steps; any other owner matching `fleet_identity_patterns` fails.

## Steps

| Step | Asserts | Does not assert |
|---|---|---|
| 1 | The product answers `/health` ok on its platform address and states the expected version (`buildVersion`, or `deployment.sourceSha` equal to the pinned commit); it serves a platform release receipt (`/__rer/release`). With the credential: the installation is under the named Business, its claimed owner is a named stand-in or not a fleet identity, the platform records a verified current release, and that release is the one the address serves. | First human owner sign-in, applied migrations, owner-recovery binding, payment. |
| 2 | Every company address named in `steps.2.company_addresses` is not a platform default host (`*.rer.run`), answers `/health` ok over verified TLS, and serves the same release receipt as the installation's platform address (so a hand-built copy on the name cannot pass). With the credential: Business and owner as step 1. No named address is FAIL. | That no other company can claim the name, that Remove works, held-out checks H1-H13, Lamp's stored address and Pre-launch state. The platform's domain list is owner-only, so attachment itself is not read. |
| 3 | FAIL while step 1 fails (there is nothing to import into). Otherwise NOT-MEASURED: the import result lives inside HappyToHelp behind owner sign-in and has no read-only door. | Row counts, attachments, resume without repeats. |
| P2 | The product's `/health` states a version at or above `minimum_version` (the release that puts the version on health). With the credential: Business and owner as step 1, and the platform event log holds an update click by the installation owner followed by a Live event with no person and no repair-shaped event in between (`event_log` patterns in `config.json`). A repaired update is FAIL with the repair named. | The content of the edit; anything outside the platform event log. |
| CHANGE | A change goes live the first time. The product answers `/health` ok. With the credential: the installation is under the named Business with an acceptable owner, and its newest ordinary change since `steps.CHANGE.since` is published with a verified release receipt, with no retry or failure event in its history (a second preview build or publish request, a fix round, a recheck or rebuild, a checks rerun, a failed preview or unreleased build) and no Ask-for-it-again change. The line gives request-to-Live minutes and publish-click-to-Live minutes. | How the change was asked for (browser, rer or an agent tool), the content of the edit. |

Platform main (`86030a5`, 14 Nov) writes only `update.available` to the installation event log for
updates. P2 cannot pass until the platform records the click and Live there; the `event_log` patterns
must then match the names it writes.

## Counts

| Count | Value | Source |
|---|---|---|
| a | Days since anyone outside the owner used a product | None exists: no read-only door reports use by identities outside the owner and the fleet. NOT-MEASURED until one does. |
| b | Ladder steps passing, out of the scripted steps | This run's step lines. |
| c | Company 1 conversations handled in a seed | `counts/company.local.json` (git-ignored) maps company 1 to its Business and seed installation. NOT-MEASURED while it has none, and while HappyToHelp has no read-only count door. The repository never names the company. |
| d | Updates applied through the platform with no fleet hands | The event logs of every installation in `config.json`, by the P2 rule. Needs the credential. |

`calendar.json` holds the dated calendar from the 13 Nov retrospective (row 12), with what yields.

## Credential

| Secret | What it must be | Used by |
|---|---|---|
| `RER_STAGE_VIEWER_SESSION` | The `__Host-rer_session` cookie value of a stage platform user (`billing-qualification.runeditrun.com`) that holds only the viewer role on the installations in `config.json`. Platform sessions last 7 days, so it needs renewing weekly; the platform has no durable read-only token today (its smoke session cannot read installation detail). The scripts refuse it if an owner-only door answers. | Steps 1, 2, P2 (platform-record half) and count d. |

No credential is needed for the public checks. None is printed or logged; the workflow references the
secret by name only.

## Run locally

```sh
./run.sh                                   # all steps and counts; writes out/latest.json and out/<utc>.json
python3 steps/step-p2.py; echo $?          # one step
RER_STAGE_VIEWER_SESSION=... ./run.sh      # with the read-only credential, from your secret store
cp counts/company.example.json counts/company.local.json   # then fill in company 1
```

Python 3.9+ standard library only.

## Schedule

`.github/workflows/scoreboard.yml` runs hourly and on push to main, with `contents: read` only and no
pull-request or manual triggers. Each run uploads `out/` as an artifact and writes the table to the
job summary. Turning the workflow off is the off switch; the page then reads "not measured".
