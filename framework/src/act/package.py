##################################
# package.py
#
# SPDX-License-Identifier: Apache-2.0
#
# Build a certification kit: the certified test objects for one config, plus the
# driver source the DUT owner assembles against their private rvmodel_macros.h.
##################################

"""Build a certification kit for one config.

A kit is the output of the normal build stopped at the certified objects: each
test assembled without rvmodel_macros.h, with the reference model's expected
signature baked in. It ships with the driver source (rvmodel_driver.S), the env
headers, the config's linker script and a build script. The DUT owner assembles
the driver against their rvmodel_macros.h and links it with the objects; their
macros never leave their machine.

Every object also carries a random kit id, so a returned log can be tied to the
objects that were shipped (see act-verify-logs).

Not a tamper guard: the DUT owner runs the ELFs and owns rvmodel_halt_pass. The
hashes prove which binaries were certified, not what ran.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

import typer
from rich import print as rprint

from act.build import build
from act.build_plan import TestOutputs, generate_build_plan
from act.certificate_tests import certificate_exists
from act.config import Config, CoverageSimulator
from act.parse_test_constraints import TestYamlHeaderError, generate_test_dict
from act.select_tests import prepare_configs_and_select_tests

package_app = typer.Typer(context_settings={"help_option_names": ["-h", "--help"]})


@dataclass(frozen=True)
class KitStamp:
    """Identity of one kit build, baked into every certified object.

    ``kit_id`` is random, so it cannot be derived from the test sources: a log that
    carries it can only have come from objects we shipped. ``built`` says which
    shipment. Both are printed by every test and checked by act-verify-logs.
    """

    kit_id: str
    built: str
    certificate: str | None = None

    def header_text(self) -> str:
        return f'#define RVCP_KIT_ID "{self.kit_id}"\n#define RVCP_KIT_BUILT "{self.built}"\n'


def driver_symbols(tests_dir: Path) -> list[str]:
    """Symbols the driver defines for the test objects, from rvtest_driver.h."""
    text = (tests_dir / "env" / "rvtest_driver.h").read_text()
    return sorted(set(re.findall(r"^\s*\.global\s+(\w+)", text, flags=re.MULTILINE)))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def signature_digest(results: Path) -> str:
    return _sha256(results)


def _tool_version(exe: str | Path, *args: str) -> str:
    try:
        r = subprocess.run([str(exe), *args], capture_output=True, text=True, timeout=10, check=False)
        return (r.stdout or r.stderr).strip().splitlines()[0] if (r.stdout or r.stderr) else "unknown"
    except (OSError, subprocess.SubprocessError, IndexError):
        return "unknown"


_BUILD_SCRIPT = """#!/bin/bash
# build_kit.sh -- build the certification-test ELFs.
#
# You supply rvmodel_macros.h; nothing in it leaves your machine. This script
# assembles the driver (rvmodel_driver.S) against it into librvmodel.a, then links
# that with each certified test object in objects/, which already contain the
# expected results.
#
# Usage:  ./build_kit.sh <dir-containing-rvmodel_macros.h> [outdir]
set -euo pipefail

DUT_INCLUDE="${1:?usage: ./build_kit.sh <dir-with-rvmodel_macros.h> [outdir]}"
OUTDIR="${2:-elfs}"
KIT="$(cd "$(dirname "$0")" && pwd)"

CC="${CC:-%(compiler)s}"
AR="${AR:-%(ar)s}"
XLEN=%(xlen)d

[ -f "$DUT_INCLUDE/rvmodel_macros.h" ] || {
  echo "error: no rvmodel_macros.h in $DUT_INCLUDE" >&2; exit 1; }

mkdir -p "$OUTDIR" "$OUTDIR/.work"

echo "==> Verifying kit integrity"
( cd "$KIT" && sha256sum -c checksums.sha256 --quiet ) && echo "    all objects and archives match the manifest"

# One driver per ABI the kit's tests use (lp64/ilp32, or the E-extension ABIs).
build_driver() {
  local mabi="$1" base="rv${XLEN}i"
  case "$mabi" in *e) base="rv${XLEN}e" ;; esac
  mkdir -p "$OUTDIR/.work/$mabi"
  "$CC" -c -I"$DUT_INCLUDE" -I"$KIT/include" -O0 -g -mcmodel=medany -nostdlib \\
        -march="${base}_zicsr_zifencei" -mabi="$mabi" -DXLEN=$XLEN -DTEST_FLEN=32 \\
        -DRVTEST_SELFCHECK -o "$OUTDIR/.work/$mabi/rvmodel_driver.o" "$KIT/rvmodel_driver.S"
  rm -f "$OUTDIR/.work/$mabi/librvmodel.a"
  "$AR" rcs "$OUTDIR/.work/$mabi/librvmodel.a" "$OUTDIR/.work/$mabi/rvmodel_driver.o"
}

echo "==> Building your driver library (librvmodel.a) from your private macros"
for mabi in %(mabis)s; do
  build_driver "$mabi"
  echo "    $OUTDIR/.work/$mabi/librvmodel.a"
done

echo "==> Linking certified tests against your driver"
fail=0; n=0
while IFS=$'\\t' read -r name obj mabi; do
  out="$OUTDIR/$(basename "$name").elf"
  base="rv${XLEN}i"; case "$mabi" in *e) base="rv${XLEN}e" ;; esac
  if "$CC" -T"$KIT/link.ld" -nostdlib -mcmodel=medany -march="$base" -mabi="$mabi" \\
        -Wl,--no-warn-rwx-segments -o "$out" "$KIT/$obj" \\
        -L"$OUTDIR/.work/$mabi" -Wl,--whole-archive -lrvmodel -Wl,--no-whole-archive; then
    n=$((n+1))
  else
    echo "  FAILED: $name" >&2; fail=$((fail+1))
  fi
done < <(python3 -c "
import json
m=json.load(open('$KIT/manifest.json'))
for t in m['tests']:
    print('\\t'.join([t['name'],t['object'],t['mabi']]))
")

echo
if [ $fail -eq 0 ]; then
  echo "Built $n ELFs into $OUTDIR/"
  echo "Run them on your DUT and return the logs."
else
  echo "$fail link failure(s)" >&2; exit 1
fi
"""


_README = """# ACT Certification Kit -- %(config)s

Generated %(generated)s by ACT %(act_version)s. Kit id `%(kit_id)s`.

Your `rvmodel_macros.h` never leaves your machine. This kit contains test objects
that were assembled by the certification authority with expected results already
built in, plus the driver source that adapts them to your device.

## Build

    ./build_kit.sh /path/to/dir/containing/rvmodel_macros.h

This assembles `rvmodel_driver.S` against your macros into `librvmodel.a`, links
it with every object, and writes the ELFs to `elfs/`. Run those ELFs on your DUT
and return the logs.

## Start with the Hello tests

If this kit includes the `Hello` suite, run those ELFs first. There are seven, they
finish in well under a second, and each one checks a single layer of what your
environment has to provide -- in order: boot and I/O, the signature mechanism, trap
entry and return, privilege transitions, the software and external interrupt macros,
the timer device addresses, and the access-fault address. The file that fails names
the layer to fix. Working through them before launching the full suite turns a
multi-hour run into a few seconds of feedback.

## What you must provide

`rvmodel_macros.h` defining the RVMODEL_* driver macros: `RVMODEL_DATA_SECTION`,
`RVMODEL_HALT_PASS`, `RVMODEL_HALT_FAIL`, `RVMODEL_IO_WRITE_STR`, and, when your
DUT needs them, `RVMODEL_BOOT`, `RVMODEL_IO_INIT` and the interrupt set/clear
macros. The driver turns them into these %(nsym)d symbols:

%(symbols)s

## Rules that must not be broken

* **Use the supplied `link.ld` unchanged.** The expected results were computed
  against exactly this memory layout. Changing an address invalidates every test
  in the kit.
* **Do not rebuild the objects in `objects/`.** They are the certified artifacts;
  `manifest.json` records a SHA-256 for each one. Verify with:

      sha256sum -c checksums.sha256

  Every object also carries this kit's id, and each test prints it on the pass
  path:

      RVCP-KIT: id=%(kit_id)s built=%(generated)s

  A log without that line, or with a different id, did not come from this kit, and
  the returned results will be rejected.

* **Do not edit `include/` or `rvmodel_driver.S`.** They must match the ones used to
  produce the expected results.
* Your macro implementations may be any size. The driver is linked after `.data`,
  so it cannot disturb a result-visible address.

## Device values

The device addresses and interrupt timings in `include/dut_environment.h` came
from the `dut_environment` block of your submitted config, and the reference model
was configured with the same values. If they do not match your hardware, the
config is wrong -- fix the config and request a new kit rather than editing the
header. A value left in your `rvmodel_macros.h` must agree with the config, or the
driver will not assemble.
"""


def _find_archiver(config: Config) -> Path:
    """The archiver that matches the config's compiler (gcc -> ar, clang -> llvm-ar)."""
    compiler = Path(str(config.compiler_exe))
    for name in (compiler.name.replace("-gcc", "-ar").replace("clang", "llvm-ar"), "llvm-ar", "ar"):
        candidate = compiler.with_name(name)
        if candidate.exists():
            return candidate
        found = shutil.which(name)
        if found:
            return Path(found)
    raise FileNotFoundError(f"No archiver found next to {compiler}")


def _write_kit_files(
    kit_dir: Path,
    config: Config,
    xlen: int,
    tests: list[TestOutputs],
    tests_dir: Path,
    header_dir: Path,
    stamp: KitStamp,
) -> None:
    """Copy the static kit inputs and write the manifest, README and build script."""
    inc = kit_dir / "include"
    inc.mkdir(parents=True, exist_ok=True)

    # Env headers the driver needs. Only .h: a non-test .S under tests/ would be
    # picked up by generate_test_dict()'s rglob("*.S").
    for h in sorted((tests_dir / "env").iterdir()):
        if h.suffix == ".h":
            shutil.copy2(h, inc / h.name)

    # UDB- and config-derived headers
    for gen in ("rvtest_config.h", "dut_environment.h"):
        src = header_dir / gen
        if src.exists():
            shutil.copy2(src, inc / gen)

    # The driver source, and the linker script the expected results were computed with
    shutil.copy2(tests_dir / "env" / "rvmodel_driver.S", kit_dir / "rvmodel_driver.S")
    shutil.copy2(config.linker_script, kit_dir / "link.ld")

    # Publish the built objects into the kit, then hash what actually shipped
    # (not the workdir copy) so the manifest describes the delivered bytes.
    entries = []
    for t in sorted(tests, key=lambda x: str(x.name)):
        rel = Path("objects") / f"{t.name}.o"
        dest = kit_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(t.obj, dest)
        has_results = t.results is not None and t.results.exists()
        entries.append(
            {
                "name": str(t.name),
                "object": str(rel),
                "suite": str(Path(t.name).parent),
                "march": t.march,
                "mabi": t.mabi,
                "xlen": xlen,
                "flen": t.flen,
                "sha256": _sha256(dest),
                "signature_sha256": signature_digest(t.results) if has_results and t.results else None,
                "signature_values": (
                    len([ln for ln in t.results.read_text().splitlines() if ln.strip()])
                    if has_results and t.results
                    else 0
                ),
            }
        )

    # Bundle the certified objects into one static archive per suite, for anyone
    # who would rather link archives than individual objects.
    lib_dir = kit_dir / "lib"
    lib_dir.mkdir(parents=True, exist_ok=True)
    ar = _find_archiver(config)
    archives = []
    by_suite: dict[str, list[dict]] = {}
    for e in entries:
        by_suite.setdefault(e["suite"], []).append(e)
    for suite, members in sorted(by_suite.items()):
        libname = "libact-" + suite.replace("/", "-") + ".a"
        libpath = lib_dir / libname
        libpath.unlink(missing_ok=True)
        subprocess.run(
            [str(ar), "rcs", str(libpath), *[str(kit_dir / m["object"]) for m in members]],
            check=True,
            capture_output=True,
        )
        for m in members:
            m["archive"] = f"lib/{libname}"
        archives.append(
            {"archive": f"lib/{libname}", "suite": suite, "members": len(members), "sha256": _sha256(libpath)}
        )

    symbols = driver_symbols(tests_dir)
    manifest = {
        "kit_version": 3,
        "config": config.name,
        "xlen": xlen,
        "kit_id": stamp.kit_id,
        "certificate": stamp.certificate,
        "generated": stamp.built,
        "act_version": _act_version(),
        "toolchain": {
            "compiler": _tool_version(config.compiler_exe, "--version"),
            "reference_model": f"{config.ref_model_type.value} {_tool_version(config.ref_model_exe, '--version')}",
        },
        "linker_script": "link.ld",
        "driver_source": "rvmodel_driver.S",
        "driver_symbols": symbols,
        "test_count": len(entries),
        "archive_count": len(archives),
        "archives": archives,
        "tests": entries,
    }
    (kit_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    # Standalone checksum file so the customer can verify without parsing JSON
    (kit_dir / "checksums.sha256").write_text(
        "".join(f"{a['sha256']}  {a['archive']}\n" for a in archives)
        + "".join(f"{e['sha256']}  {e['object']}\n" for e in entries)
    )
    # Sign the manifest itself: one digest that covers every object, archive and
    # signature digest in the kit.
    manifest_digest = _sha256(kit_dir / "manifest.json")
    (kit_dir / "MANIFEST.sha256").write_text(f"{manifest_digest}  manifest.json\n")

    compiler_name = Path(str(config.compiler_exe)).name
    (kit_dir / "build_kit.sh").write_text(
        _BUILD_SCRIPT
        % {
            "compiler": compiler_name,
            "ar": ar.name,
            "xlen": xlen,
            "mabis": " ".join(sorted({t.mabi for t in tests})),
        }
    )
    (kit_dir / "build_kit.sh").chmod(0o755)

    (kit_dir / "README.md").write_text(
        _README
        % {
            "config": config.name,
            "generated": manifest["generated"],
            "kit_id": manifest["kit_id"],
            "act_version": manifest["act_version"],
            "nsym": len(symbols),
            "symbols": "\n".join(f"  - `{s}`" for s in symbols),
        }
    )


def _act_version() -> str:
    try:
        from importlib.metadata import version

        return version("act")
    except Exception:  # noqa: BLE001
        return "unknown"


@package_app.command()
def make_kit(
    config_file: Annotated[
        Path, typer.Argument(exists=True, file_okay=True, dir_okay=False, help="ACT test config file")
    ],
    output: Annotated[Path, typer.Option("--output", "-o", file_okay=False, help="Kit output directory")],
    test_dir: Annotated[
        Path, typer.Option("--test-dir", "-t", exists=True, file_okay=False, help="Tests directory")
    ] = Path("tests"),
    workdir: Annotated[Path | None, typer.Option("--workdir", "-w", file_okay=False, show_default="./work")] = None,
    extensions: Annotated[str, typer.Option("--extensions", "-e", help="Comma-separated suites")] = "all",
    exclude: Annotated[str, typer.Option("--exclude", "-x", help="Comma-separated suites to exclude")] = "",
    certificate: Annotated[
        str | None,
        typer.Option(help="Only include tests for the specified certificate"),
    ] = None,
    jobs: Annotated[int, typer.Option("--jobs", "-j", help="Parallel jobs (0 = CPU count)")] = 0,
    kit_id: Annotated[
        str,
        typer.Option(
            "--kit-id",
            help="Kit identity stamped into every object (default: a fresh random id). "
            "Pass the id of an earlier kit only to rebuild that exact shipment.",
        ),
    ] = "",
    *,
    keep_going: Annotated[bool, typer.Option("--keep-going", "-k", help="Continue after failures")] = False,
    verbose: Annotated[bool, typer.Option(help="Print each command")] = False,
    enable_experimental_extensions: Annotated[
        bool, typer.Option(help="Enable tests for experimental extensions")
    ] = False,
) -> None:
    """Build a certification kit the customer links their private macros into."""
    if workdir is None:
        workdir = Path.cwd() / "work"
    if jobs <= 0:
        jobs = os.cpu_count() or 1
    test_dir, workdir, kit_dir = test_dir.absolute(), workdir.absolute(), output.absolute()

    try:
        full_tests = generate_test_dict(test_dir, extensions, exclude)
    except TestYamlHeaderError as e:
        e.print()
        raise typer.Exit(1) from None

    if certificate and not certificate_exists(certificate):
        raise typer.BadParameter(f"Unknown certificate '{certificate}'.", param_hint="--certificate")

    prepared = prepare_configs_and_select_tests(
        [config_file],
        certificate,
        full_tests,
        workdir,
        jobs=jobs,
        verbose=verbose,
        enable_experimental_extensions=enable_experimental_extensions,
    )
    config, params, selected = prepared[0]
    xlen = params["MXLEN"]
    if not isinstance(xlen, int):
        raise TypeError(f"MXLEN must be an integer, got {xlen!r}")

    if not selected:
        rprint("[bold red]No tests selected for this config.[/]", file=sys.stderr)
        raise typer.Exit(1)

    kit_dir.mkdir(parents=True, exist_ok=True)
    rprint(f"Building kit for [cyan]{config.name}[/] ({len(selected)} tests, RV{xlen}) -> {kit_dir}")

    stamp = KitStamp(
        kit_id=kit_id or secrets.token_hex(16),
        built=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        certificate=certificate,
    )
    # Kit objects get their own build area, so a kit build never reuses objects
    # stamped for another kit, nor disturbs the unstamped ones from `make`.
    header_dir = workdir / config.name
    out_dir = header_dir / "kit"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp_h = out_dir / "kit_stamp.h"
    stamp_h.write_text(stamp.header_text())

    tasks, outputs = generate_build_plan(
        config,
        xlen,
        selected,
        test_dir,
        Path("coverpoints").absolute(),
        workdir,
        False,
        CoverageSimulator.QUESTA,
        enable_experimental_extensions=enable_experimental_extensions,
        rvmodel_dir=None,
        out_dir=out_dir,
        kit_stamp=stamp_h,
    )
    result = build(
        tasks,
        jobs=jobs,
        cache_root=workdir,
        keep_going=keep_going,
        verbose=verbose,
        phase_label="Assembling kit objects",
    )

    if result.errors:
        rprint(f"\n[bold red]Kit build failed:[/] {result.failed} task(s)", file=sys.stderr)
        for e in result.errors[:10]:
            rprint(f"  - {e.task_name}", file=sys.stderr)
        raise typer.Exit(1)

    built = [t for t in outputs if t.obj.exists()]
    if len(built) != len(outputs):
        rprint(
            f"[yellow]Warning:[/] {len(outputs) - len(built)} object(s) missing; kit will be incomplete.",
            file=sys.stderr,
        )

    _write_kit_files(kit_dir, config, xlen, built, test_dir, header_dir, stamp)

    rprint(f"[bold green]Kit complete:[/] {len(built)} certified objects in {kit_dir}")
    rprint(f"  manifest: {kit_dir / 'manifest.json'}")
    rprint("  customer builds with: ./build_kit.sh <dir-with-rvmodel_macros.h>")


def main() -> None:
    package_app()


if __name__ == "__main__":
    main()
