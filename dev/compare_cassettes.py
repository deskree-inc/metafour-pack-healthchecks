"""Compare two cassette directories by what a replay serves: each interaction's request line and
the response's status and JSON body. Response headers (the date, the server) are not compared.

    python3 dev/compare_cassettes.py COMMITTED RECORDED

Exit 1, with one line per difference, when the live instance answered differently from the
committed cassettes.
"""

import json
import sys
from pathlib import Path


def served(path: Path) -> list:
    out = []
    for item in json.loads(path.read_text())["interactions"]:
        response = item["response"]
        try:
            body = json.loads(response.get("body") or "null")
        except ValueError:
            body = response.get("body")
        out.append((item["request"]["method"], item["request"]["url"], response["status"], body))
    return out


def main(committed: Path, recorded: Path) -> int:
    problems = []
    names = sorted({p.relative_to(committed) for p in committed.rglob("*.json")}
                   | {p.relative_to(recorded) for p in recorded.rglob("*.json")})
    for name in names:
        a, b = committed / name, recorded / name
        if not (a.exists() and b.exists()):
            problems.append(f"{name}: only in {'the recording' if b.exists() else 'the commit'}")
        elif served(a) != served(b):
            problems.append(f"{name}: the live instance answered differently")
    for line in problems:
        print(line)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]), Path(sys.argv[2])))
