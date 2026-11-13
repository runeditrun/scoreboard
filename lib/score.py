"""Shared helpers for the step and count scripts: read-only GETs and the one-line result format.

Nothing here writes to any service. A credential is read from the environment by name, sent only
as a cookie to the configured platform origin, never followed across a redirect, and never printed.
"""
import json, os, re, sys, urllib.error, urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXIT = {'PASS': 0, 'FAIL': 1, 'NOT-MEASURED': 2}
SESSION_COOKIE = '__Host-rer_session'


def utc():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def config():
    with open(os.path.join(ROOT, 'config.json')) as f:
        return json.load(f)


def step(ident, status, reason, evidence):
    """Print `STEP <n> <status> <reason> <evidence> <utc>` and exit 0/1/2."""
    print(f"STEP {ident} {status} {' '.join(str(reason).split())} {str(evidence).replace(' ', '') or '-'} {utc()}")
    sys.exit(EXIT[status])


def count(ident, value, note, source):
    """Print `COUNT <id> <value> <note> <source> <utc>`; exit 0 when measured, 2 when not."""
    print(f"COUNT {ident} {value} {' '.join(str(note).split())} {str(source).replace(' ', '') or '-'} {utc()}")
    sys.exit(2 if value == 'NOT-MEASURED' else 0)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None  # a redirect is reported as its status; a cookie never travels to another host


_OPENER = urllib.request.build_opener(_NoRedirect)


def get(url, session=None, timeout=20):
    """GET url. Returns (status, text, error); status 0 means no HTTP answer."""
    headers = {'User-Agent': 'rer-scoreboard/1 (read-only)', 'Accept': 'application/json'}
    if session:
        headers['Cookie'] = f'{SESSION_COOKIE}={session}'
    try:
        with _OPENER.open(urllib.request.Request(url, headers=headers), timeout=timeout) as r:
            return r.status, r.read(2_000_000).decode('utf-8', 'replace'), None
    except urllib.error.HTTPError as e:
        return e.code, '', f'http {e.code}'
    except Exception as e:  # DNS, TLS, timeout: no answer at all
        return 0, '', f'{type(e).__name__} {getattr(e, "reason", "")}'.strip()[:120]


def get_json(url, session=None):
    status, text, error = get(url, session)
    if status != 200:
        return None, error or f'http {status}'
    try:
        return json.loads(text), None
    except ValueError:
        return None, 'answer is not JSON'


def product_health(app_url, expected_version=None, expected_commit=None, minimum_version=None):
    """Public door: the product answers /health with ok and states the expected version.
    Returns (failure_reason or None, health_body)."""
    body, error = get_json(app_url.rstrip('/') + '/health')
    if body is None:
        return f'product does not answer /health ({error})', None
    if body.get('ok') is not True and body.get('status') != 'ok':
        return 'product /health is not ok', body
    version = body.get('buildVersion') or body.get('version')
    commit = (body.get('deployment') or {}).get('sourceSha')
    if not version and not commit:
        return 'product /health states no version (buildVersion and deployment.sourceSha are empty)', body
    if expected_version and version != expected_version and commit != expected_commit:
        return f'product /health states version {version or commit}, expected {expected_version}', body
    if minimum_version and not (version and _ver(version) >= _ver(minimum_version)):
        return f'product /health states version {version or commit}, expected {minimum_version} or later', body
    return None, body


def _ver(text):
    return tuple(int(p) for p in re.findall(r'\d+', text)[:3])


def release_identity(origin):
    """The managed deploy's own release receipt, served by the platform's delivery wrapper."""
    body, error = get_json(origin.rstrip('/') + '/__rer/release')
    return (body.get('releaseDigest'), None) if body and body.get('releaseDigest') else (None, error or 'no releaseDigest')


def viewer_session(cfg):
    return os.environ.get(cfg['stage']['viewer_session_secret']) or None


def platform_installation(cfg, installation_id, session):
    """Read the installation record with a viewer-only session. Returns (record, error)."""
    origin = cfg['stage']['platform_origin']
    status, _, _ = get(f'{origin}/api/installations/{installation_id}/members', session)
    if status == 200:  # owner-only door answered: this credential can act, so it is not read-only
        return None, f"{cfg['stage']['viewer_session_secret']} holds the owner role; the scoreboard takes a viewer-only session"
    body, error = get_json(f'{origin}/api/installations/{installation_id}', session)
    if body is None or not isinstance(body.get('installation'), dict):
        return None, f'platform installation read failed ({error or "no installation"})'
    return body['installation'], None


def owner_verdict(cfg, record):
    """None when the installation's claimed owner is acceptable, else the failure reason."""
    email = (((record.get('state') or {}).get('ownerClaim') or {}).get('email') or '').lower()
    if not email:
        return 'platform records no claimed owner'
    if email in [a.lower() for a in cfg['identities']['standin_owner_addresses']]:
        return None
    if any(re.search(p, email) for p in cfg['identities']['fleet_identity_patterns']):
        return 'installation owner is a fleet identity not named as a stand-in'
    return None


def events(cfg, installation_id, session, pages=50):
    """Every installation event in order, or (None, error)."""
    origin, after, out = cfg['stage']['platform_origin'], 0, []
    for _ in range(pages):
        body, error = get_json(f'{origin}/api/installations/{installation_id}/events?after={after}', session)
        if body is None:
            return None, f'event log read failed ({error})'
        batch = body.get('events') or []
        out += batch
        if len(batch) < 100:
            return out, None
        after = body.get('cursor', after)
    return None, 'event log longer than the read cap'


def update_windows(cfg, log, owner_id):
    """Split the log into click..Live windows. Each: {click, live|None, hands:[(type, actor)]}.
    A hand is any event after the click with a person as actor, or a repair-shaped type."""
    rules = cfg['event_log']
    click, live, repair = (re.compile(rules[k]) for k in ('click_type', 'live_type', 'repair_type'))
    windows, current = [], None
    for e in log:
        kind, actor = e.get('type', ''), e.get('actor_id')
        if current is None:
            if click.search(kind) and actor:
                current = {'click': e, 'live': None, 'hands': [] if actor == owner_id else [(kind, 'click-by-non-owner')]}
            continue
        if actor or repair.search(kind):
            current['hands'].append((kind, actor or 'platform'))
        if live.search(kind):
            current['live'] = e
            windows.append(current)
            current = None
    if current:
        windows.append(current)
    return windows
