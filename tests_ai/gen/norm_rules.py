#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""List the normative rules (norm: tags) in ISA-manual AsciiDoc sources.

Every norm: tag is a normative rule (riscv-isa-manual #3422). A tag is either inline,
[#norm:name]#text# or [#norm:name]+text+, or a paragraph anchor, [[norm:name]] on its own
line followed by the paragraph.

Usage:
  norm_rules.py [--rev REV] [--manual DIR] [--grep REGEX] FILE...
    FILE   path inside the manual, e.g. src/priv/sstc.adoc
    --rev  git revision to read (default upstream/main); use "WORKTREE" for files on disk
    --grep keep only rules whose name or text matches REGEX (case-insensitive)
Prints one block per rule: name, file:line, and text with AsciiDoc markup lightly cleaned.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

INLINE = re.compile(r"\[#(norm:[A-Za-z0-9_.:\-]+)\]([#+])")
PARA = re.compile(r"^\[\[(norm:[A-Za-z0-9_.:\-]+)\]\]\s*$|^\[#(norm:[A-Za-z0-9_.:\-]+)\]\s*$")


def read(manual: Path, rev: str, path: str) -> str:
    if rev == "WORKTREE":
        return (manual / path).read_text()
    return subprocess.run(
        ["git", "-C", str(manual), "show", f"{rev}:{path}"], check=True, capture_output=True, text=True
    ).stdout


def clean(text: str) -> str:
    text = re.sub(r"(?:csr|insn|ext|qty|param)::\[([^\]]*)\]", r"\1", text)
    text = re.sub(
        r"(csr|insn|ext):([A-Za-z0-9_.]+)\[([^\]]*)\]",
        lambda m: m.group(2) + (f"[{m.group(3)}]" if m.group(3) else ""),
        text,
    )
    text = re.sub(r"qty:(\d+)\[([a-z]+)\]", r"\1 \2", text)
    text = re.sub(r"\[#norm:[^\]]+\][#+]", "", text)
    return " ".join(text.split())


def rules(src: str, path: str) -> list[tuple[str, int, str]]:
    out = []
    lines = src.splitlines()
    flat = "\n".join(lines)
    for m in INLINE.finditer(flat):
        delim = m.group(2)
        start = m.end()
        end = flat.find(delim, start)
        line = flat.count("\n", 0, m.start()) + 1
        out.append((m.group(1)[5:], line, clean(flat[start:end])))
    for i, ln in enumerate(lines):
        m = PARA.match(ln)
        if not m:
            continue
        body = []
        for nxt in lines[i + 1 :]:
            if not nxt.strip():
                break
            body.append(nxt)
        out.append(((m.group(1) or m.group(2))[5:], i + 1, clean(" ".join(body))))
    return sorted(out, key=lambda r: r[1])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--rev", default="upstream/main")
    ap.add_argument("--manual", default=str(Path.home() / "repos/riscv-isa-manual"))
    ap.add_argument("--grep")
    a = ap.parse_args()
    pat = re.compile(a.grep, re.IGNORECASE) if a.grep else None
    for f in a.files:
        for name, line, text in rules(read(Path(a.manual), a.rev, f), f):
            if pat and not (pat.search(name) or pat.search(text)):
                continue
            print(f"{name}  ({f}:{line})\n    {text}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
