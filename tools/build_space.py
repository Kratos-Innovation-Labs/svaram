#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
"""Build the Hugging Face demo Space folder from a tagged release of this repository.

    python3 tools/build_space.py --ref v0.1.0 --out /tmp/svaram-space

The Space is a copy of the code at that git ref, never edited by hand: GitHub stays the source of
truth. It holds the services, the language packs, the model fetcher and pins, the locked
requirements, and space/ (the Gradio page, start script and Dockerfile). No model is copied.
"""
from __future__ import annotations

import argparse
import io
import os
import shutil
import subprocess
import sys
import tarfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: What the Space needs from the repository, as paths in the git tree.
KEEP = ["core", "lang", "api", "translate", "voices", "space/app.py", "space/start.sh",
        "tools/fetch_models.py", "tools/slim_checkpoint.py", "deploy/models.yaml", "deploy/requirements",
        "LICENSE", "NOTICE", "CREDITS.md"]
#: Space files that Hugging Face expects at the top of the Space repository.
TOP = {"space/README.md": "README.md", "space/Dockerfile": "Dockerfile"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ref", default="HEAD", help="git tag or commit to build from (default HEAD)")
    ap.add_argument("--out", required=True, help="folder to write; replaced if it exists")
    a = ap.parse_args()

    tar = subprocess.run(["git", "-C", ROOT, "archive", "--format=tar", a.ref],
                         capture_output=True, check=False)
    if tar.returncode != 0:
        sys.exit(f"git archive {a.ref} failed: {tar.stderr.decode().strip()}")
    commit = subprocess.run(["git", "-C", ROOT, "rev-parse", "--short", f"{a.ref}^{{commit}}"],
                            capture_output=True, text=True, check=True).stdout.strip()

    if os.path.isdir(a.out):
        shutil.rmtree(a.out)
    os.makedirs(a.out)
    n = 0
    with tarfile.open(fileobj=io.BytesIO(tar.stdout)) as tf:
        for m in tf.getmembers():
            if not m.isfile():
                continue
            name = m.name
            dest = TOP.get(name)
            if dest is None and any(name == k or name.startswith(k + "/") for k in KEEP):
                dest = name
            if dest is None or "/__pycache__/" in name:
                continue
            path = os.path.join(a.out, dest)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(tf.extractfile(m).read())
            os.chmod(path, 0o755 if m.mode & 0o111 else 0o644)
            n += 1
    for need in ("README.md", "Dockerfile", "space/app.py", "space/start.sh", "deploy/models.yaml"):
        if not os.path.isfile(os.path.join(a.out, need)):
            sys.exit(f"{need} is missing at {a.ref}")
    with open(os.path.join(a.out, "SOURCE"), "w", encoding="utf-8") as f:
        f.write(f"Built from https://github.com/Kratos-Innovation-Labs/svaram at {a.ref} ({commit}) "
                f"by tools/build_space.py. Do not edit here; change the repository and rebuild.\n")
    print(f"{n} files from {a.ref} ({commit}) -> {a.out}")


if __name__ == "__main__":
    main()
