"""Find API keys, tokens and passwords before they can become public.

JC's rule (2026-11-28): never leave an API key public. This scanner is used two ways:
  * scripts/check_public.py calls find_secrets() on every file before any commit
    to this PUBLIC repository, so an automated job can never publish a key here;
  * the daily Claude check runs it over every clone:
        python3 scripts/secret_scan.py <repo dir> [<repo dir> ...]
    Exit code 0 = clean, 1 = possible key found. The secret itself is never printed.

Keys that have no recognisable shape (FRED, Tiingo) are caught by value: when a
workflow passes the real secret in an environment variable listed in SECRET_ENV,
any file containing that exact value is flagged.
"""
import os
import pathlib
import re
import subprocess
import sys

PATTERNS = [
    ("AWS access key", r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    ("GitHub token", r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}"),
    ("GitHub fine-grained token", r"\bgithub_pat_[A-Za-z0-9_]{50,}"),
    ("Anthropic or OpenAI key", r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_-]{32,}"),
    ("Google API key", r"\bAIza[0-9A-Za-z_-]{35}"),
    ("Google OAuth client secret", r"\bGOCSPX-[A-Za-z0-9_-]{20,}"),
    ("Google service-account key", r'"private_key_id"\s*:\s*"[0-9a-f]{20,}"'),
    ("Slack token", r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    ("Stripe live key", r"\b(?:sk|rk)_live_[A-Za-z0-9]{20,}"),
    ("Private key", r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY"),
    ("Amazon LWA refresh token", r"Atzr\|[A-Za-z0-9_\-]{20,}"),
    ("Amazon LWA client secret", r"\bamzn1\.oa2-cs\.v1\.[A-Za-z0-9]{20,}"),
    ("JWT / Supabase key", r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    ("Telegram bot token", r"\b\d{8,10}:AA[A-Za-z0-9_-]{30,}"),
]
COMPILED = [(name, re.compile(rx)) for name, rx in PATTERNS]

# key = "long literal value" in code or config.
ASSIGNMENT = re.compile(
    r"""(?i)\b(?:api[_-]?key|apikey|secret|client[_-]?secret|access[_-]?token|refresh[_-]?token"""
    r"""|auth[_-]?token|token|password|passwd)\b["']?\s*[:=]\s*["']([^"'\s]{16,})["']""")
# Values that are clearly not real secrets.
HARMLESS = re.compile(r"(?i)fixture|example|placeholder|dummy|sample|changeme|your[_-]|<|\$\{|env\(|xxxx|\*\*\*\*|test")

SECRET_ENV = ("FRED_API_KEY", "TIINGO_TOKEN", "SEC_UA")
ENV_FILE = re.compile(r"(^|/)\.env(\.[^/]*)?$")
ENV_OK = re.compile(r"(^|/)\.env\.(example|sample|template)$")
MAX_BYTES = 50 * 1024 * 1024


def _known_values():
    vals = []
    for name in SECRET_ENV:
        v = (os.environ.get(name) or "").strip()
        if len(v) >= 8:
            vals.append((name, v))
    return vals


def find_secrets(text, known=None):
    """Return a list of (line_number, kind) for every possible secret in text."""
    known = _known_values() if known is None else known
    hits = []
    for no, line in enumerate(text.splitlines(), 1):
        for name, rx in COMPILED:
            if rx.search(line):
                hits.append((no, name))
        m = ASSIGNMENT.search(line)
        if m and not HARMLESS.search(m.group(1)):
            hits.append((no, "hard-coded secret value"))
        for env_name, value in known:
            if value in line:
                hits.append((no, f"real value of {env_name}"))
    return hits


def check_path(rel):
    """Problems that come from the file name alone (a committed .env file)."""
    if ENV_FILE.search(rel) and not ENV_OK.search(rel):
        return ["committed .env file (keep it in .gitignore)"]
    return []


def _files(root):
    root = pathlib.Path(root)
    try:
        out = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], capture_output=True, check=True)
        names = [n for n in out.stdout.decode("utf-8", "replace").split("\0") if n]
        return [(n, root / n) for n in names]
    except (OSError, subprocess.CalledProcessError):
        return [(p.relative_to(root).as_posix(), p) for p in root.rglob("*")
                if p.is_file() and ".git" not in p.parts]


def scan_repo(root):
    found = []
    known = _known_values()
    for rel, path in _files(root):
        for msg in check_path(rel):
            found.append(f"{rel}: {msg}")
        try:
            if not path.is_file() or path.stat().st_size > MAX_BYTES:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for no, kind in find_secrets(text, known):
            found.append(f"{rel}:{no}: possible {kind}")
    return found


if __name__ == "__main__":
    roots = sys.argv[1:] or ["."]
    bad = 0
    for r in roots:
        problems = scan_repo(r)
        bad += len(problems)
        for p in problems:
            print(f"LEAK {pathlib.Path(r).name}/{p}")
        print(f"{pathlib.Path(r).resolve().name}: {'clean' if not problems else f'{len(problems)} possible key(s)'}")
    sys.exit(1 if bad else 0)
