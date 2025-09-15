import os
from pathlib import Path
from typing import Iterable


def _parse_line(line: str):
    s = line.strip()
    if not s or s.startswith('#'):
        return None, None
    if s.startswith('export '):
        s = s[len('export '):]
    if '=' not in s:
        return None, None
    key, val = s.split('=', 1)
    key = key.strip()
    val = val.strip()
    # Strip quotes if wrapped
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        val = val[1:-1]
    return key, val


def load_dotenv_if_present(extra_paths: Iterable[Path] | None = None):
    """
    Load key=value pairs from .env files, without overriding existing os.environ.
    Search order (first found wins per key):
      - CWD/.env
      - repo_root/.env (two levels up from this file)
      - /opt/app/.env
      - any extra_paths provided
    """
    tried = []
    paths = [Path.cwd() / '.env', Path(__file__).resolve().parents[1] / '.env', Path('/opt/app/.env')]
    if extra_paths:
        paths.extend(list(extra_paths))
    for p in paths:
        try:
            if not p or not p.exists():
                continue
            tried.append(str(p))
            for line in p.read_text().splitlines():
                k, v = _parse_line(line)
                if not k:
                    continue
                if k not in os.environ:
                    os.environ[k] = v
        except Exception:
            # Silent on purpose; this is best-effort
            continue
    return tried

