#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
"""Slim a Coqui TTS training checkpoint to what speech needs: its config and model weights.

    slim_checkpoint.py SRC DST [--want SHA256]

The Indic-TTS release checkpoints also carry the optimizer state and training counters (about
three times the size). Speech uses only "config" and "model", so this keeps those two, saves
them to DST, and proves every weight tensor in DST equals the one in SRC.

If --want is given (the SHA-256 of the same file on svaram.live), the two possible key orders are
tried and the one that reproduces that file exactly is kept. Prints "exact" when DST matches
--want, otherwise "same-weights". Run with the indictts environment's Python (it needs torch).
"""
import hashlib
import os
import sys
import tempfile

import torch


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    args = sys.argv[1:]
    want = None
    if "--want" in args:
        i = args.index("--want")
        want = args[i + 1].lower()
        del args[i:i + 2]
    src, dst = args
    c = torch.load(src, map_location="cpu", weights_only=False)
    if "model" not in c or "config" not in c:
        sys.exit(f"{src}: no config and model in this checkpoint")
    result = "same-weights"
    # torch.save names the archive after the file, so save under DST's own name in a temp folder
    with tempfile.TemporaryDirectory(dir=os.path.dirname(os.path.abspath(dst))) as tmp:
        cand = os.path.join(tmp, os.path.basename(dst))
        chosen = None
        for order in (("config", "model"), ("model", "config")):
            torch.save({k: c[k] for k in order}, cand)
            if want and sha256(cand) == want:
                chosen, result = order, "exact"
                break
            if chosen is None:
                chosen = order
        if result != "exact":
            torch.save({k: c[k] for k in chosen}, cand)
        os.replace(cand, dst)
    d = torch.load(dst, map_location="cpu", weights_only=False)
    a, b = c["model"], d["model"]
    if set(a) != set(b) or not all(torch.equal(a[k], b[k]) for k in a):
        os.remove(dst)
        sys.exit(f"{dst}: weights differ from {src}; file removed")
    print(result)


if __name__ == "__main__":
    main()
