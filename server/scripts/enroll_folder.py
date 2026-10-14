"""Bulk-enroll students from a folder of photos.

Usage: python scripts/enroll_folder.py path/to/folder [--api http://localhost:8000]
Each file is named CODE__Full Name.jpg (double underscore). Group can be added as CODE__Name__Group.jpg.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib import request, error
import json
import mimetypes
import uuid


def post_json(url: str, body: dict) -> tuple[int, dict]:
    data = json.dumps(body).encode()
    req = request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def post_file(url: str, path: Path) -> tuple[int, dict]:
    boundary = uuid.uuid4().hex
    ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{path.name}\"\r\n"
        f"Content-Type: {ctype}\r\n\r\n"
    ).encode() + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    req = request.Request(url, data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}, method="POST")
    try:
        with request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--api", default="http://localhost:8000")
    args = ap.parse_args()
    folder = Path(args.folder)
    with request.urlopen(f"{args.api}/students") as r:
        existing = {s["code"]: s for s in json.loads(r.read())}
    ok = 0
    for path in sorted(folder.iterdir()):
        if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            continue
        parts = path.stem.split("__")
        if len(parts) < 2:
            print(f"skip {path.name}: expected CODE__Name[__Group]")
            continue
        code, name = parts[0], parts[1]
        group = parts[2] if len(parts) > 2 else ""
        student = existing.get(code)
        if student is None:
            status, student = post_json(f"{args.api}/students", {"code": code, "name": name, "group": group})
            if status != 201:
                print(f"fail {path.name}: {student}")
                continue
            existing[code] = student
        status, res = post_file(f"{args.api}/students/{student['id']}/enroll", path)
        if status == 200:
            ok += 1
            print(f"enrolled {name} ({res['templates']} templates)")
        else:
            print(f"fail {path.name}: {res.get('detail', res)}")
    print(f"done: {ok} enrolled")
    return 0


if __name__ == "__main__":
    sys.exit(main())
