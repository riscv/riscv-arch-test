##################################
# package.py
#
# SPDX-License-Identifier: Apache-2.0
#
# Build a certification kit: pre-assembled test objects plus the model shim
# the customer links their private RVMODEL macros into.
##################################

"""Emit a certification kit for one config.

The kit exists so a certification applicant never has to hand over their
``rvmodel_macros.h``. We assemble every test into a relocatable object with the
Sail-derived golden signature already baked in, and ship a shim template the
customer assembles against their own private macros. They link the two and run
the resulting ELFs themselves.

What makes this sound rather than merely convenient:

* The certified objects contain no DUT implementation code. They are assembled
  with ``RVMODEL_SHIM_EXTERN`` and with **no DUT include directory at all**, so a
  stray dependency on ``rvmodel_macros.h`` fails the build instead of silently
  baking a private implementation into a certified artifact.
* The signature is inside the object (``#include SIGNATURE_FILE`` lands in
  ``.data``), so it cannot be swapped for a friendlier one.
* ``act_link.ld`` keeps every customer-supplied section after ``.data``, so the
  shim's size cannot shift a signature-visible address.

What this does NOT do: stop a customer fabricating a log. They own
``rvmodel_halt_pass`` and run the ELFs on their own machine. The manifest hashes
prove which test binaries were certified, not what was executed.
"""

from __future__ import annotations

import hashlib
import importlib.resources
import json
import os
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
from act.build_types import BuildTask, PythonAction, SubprocessAction
from act.config import Config
from act.parse_test_constraints import TestMetadata, TestYamlHeaderError, generate_test_dict
from act.select_tests import prepare_configs_and_select_tests
from act.sig_modify import process_signature_file

# Symbols the customer's shim must define. Kept here so the kit README and the
# post-build check agree with each other and with data/rvmodel_shim.S.
SHIM_SYMBOLS: tuple[str, ...] = (
    "rvmodel_dut_boot",
    "rvmodel_dut_io_init",
    "rvmodel_io_write_str",
    "rvmodel_halt_pass",
    "rvmodel_halt_fail",
    "rvtest_set_msw_int",
    "rvtest_clr_msw_int",
    "rvtest_set_mext_int",
    "rvtest_clr_mext_int",
    "rvtest_set_ssw_int",
    "rvtest_clr_ssw_int",
    "rvtest_set_sext_int",
    "rvtest_clr_sext_int",
    "rvmodel_clr_msw_int_h",
    "rvmodel_clr_mext_int_h",
    "rvmodel_clr_ssw_int_h",
    "rvmodel_clr_sext_int_h",
)

# Undefined symbols that are expected in a certified object but are NOT the
# shim's responsibility. CSR_SEDELEG/CSR_SIDELEG are referenced by a .set in
# rvtest_trap_handler.h and defined nowhere; the linker resolves them to 0. That
# is a pre-existing framework bug, tracked separately -- listed here so the kit's
# own consistency check does not mistake it for a missing shim symbol.
_KNOWN_UNRESOLVED: frozenset[str] = frozenset({"CSR_SEDELEG", "CSR_SIDELEG"})

package_app = typer.Typer(context_settings={"help_option_names": ["-h", "--help"]})


@dataclass
class KitTest:
    """One certified test object in the kit."""

    name: str  # e.g. "priv/InterruptsSm/InterruptsSm-00"
    obj: Path  # absolute path to the built object
    march: str
    mabi: str
    xlen: int
    flen: str


def _mabi(xlen: int, e_ext: bool) -> str:
    """Match build_plan.py's ABI selection."""
    return f"{'i' if xlen == 32 else ''}lp{xlen}{'e' if e_ext else ''}"


def _kit_compiler_cmd(config: Config, tests_dir: Path, udb_header_dir: Path, empty_include: Path) -> list[str]:
    """Compiler prefix for certified objects.

    Deliberately substitutes an empty directory for the DUT include dir. If a
    test or env header still reaches for rvmodel_macros.h, the build fails here
    rather than shipping DUT code inside a certified object.
    """
    from act.config import CompilerType

    cmd = [str(config.compiler_exe)]
    if config.compiler_type == CompilerType.CLANG:
        cmd.append("-fuse-ld=lld")
    cmd.extend(
        [
            f"-I{empty_include}",
            "-O0",
            "-g",
            "-mcmodel=medany",
            "-nostdlib",
            f"-I{tests_dir}/env",
            f"-I{udb_header_dir.absolute()}",
        ]
    )
    return cmd


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _tool_version(exe: str | Path, *args: str) -> str:
    try:
        r = subprocess.run([str(exe), *args], capture_output=True, text=True, timeout=10, check=False)
        return (r.stdout or r.stderr).strip().splitlines()[0] if (r.stdout or r.stderr) else "unknown"
    except (OSError, subprocess.SubprocessError, IndexError):
        return "unknown"


def check_object_is_clean(obj: Path, objdump_exe: Path | None) -> None:
    """Fail if a certified object references anything the shim does not provide.

    Runs as a build action so a bad object stops the kit rather than being
    discovered by the customer.
    """
    if objdump_exe is None:
        return
    nm = Path(str(objdump_exe).replace("objdump", "nm"))
    if not nm.exists():
        return
    out = subprocess.run([str(nm), "-u", str(obj)], capture_output=True, text=True, check=False).stdout
    undefined = {line.split()[-1] for line in out.splitlines() if line.strip()}
    unexpected = undefined - set(SHIM_SYMBOLS) - _KNOWN_UNRESOLVED
    if unexpected:
        raise RuntimeError(
            f"{obj.name} references symbols no shim provides: {sorted(unexpected)}. "
            "Either the shim is missing an entry point or DUT code leaked into a certified object."
        )


def _gen_kit_tasks(
    config: Config,
    xlen: int,
    selected: dict[str, TestMetadata],
    tests_dir: Path,
    workdir: Path,
    kit_dir: Path,
    debug: bool,
) -> tuple[list[BuildTask], list[KitTest]]:
    """Tasks producing one certified object per test, plus the kit inventory.

    Pipeline per test (first three steps mirror the normal ACT build exactly, so
    the golden signature is the same one the normal flow would produce):
        test.S -> test.sig.elf -> test.sig (reference model) -> test.results
        test.S + test.results -> <kit>/objects/<name>.o     (certified, DUT-free)
    """
    # Reuse the normal build's command construction so the signature ELF and the
    # certified object stay in lock-step with build_plan.py. Duplicating those
    # flag lists is exactly what broke when the main build added -DTEST_FILE and
    # the Sail platform defines.
    from act.build_plan import _compiler_cmd, _ref_model_sig_cmd, _sail_platform_defines

    config_wkdir = workdir / config.name
    build_dir = config_wkdir / "package_build"
    # Objects are built inside the workdir (build()'s cache keys every output
    # relative to cache_root) and published into the kit afterwards.
    obj_root = config_wkdir / "kit_objects"
    empty_include = config_wkdir / "_kit_no_dut_include"
    empty_include.mkdir(parents=True, exist_ok=True)

    sig_cmd_prefix = _compiler_cmd(config, xlen, tests_dir, config_wkdir)
    kit_cmd_prefix = _kit_compiler_cmd(config, tests_dir, config_wkdir, empty_include)

    env_headers = tuple(sorted(p.absolute() for p in (tests_dir / "env").iterdir() if p.is_file()))
    dut_headers = tuple(sorted(p.absolute() for p in config.dut_include_dir.iterdir() if p.suffix == ".h"))
    udb_headers = tuple(sorted(p.absolute() for p in config_wkdir.iterdir() if p.suffix == ".h"))
    sig_inputs = (*env_headers, *dut_headers, *udb_headers, config.linker_script.absolute())
    kit_inputs = (*env_headers, *udb_headers)

    ref_inputs: tuple[Path, ...] = ()
    signature_compile_flags: tuple[str, ...] = ()
    sail_json = config.dut_include_dir / "sail.json"
    if sail_json.exists():
        ref_inputs = (sail_json.absolute(),)
        # sail_macros.h now expects the CLINT / interrupt-generator base addresses
        # on the command line (Sail reference build only).
        signature_compile_flags = _sail_platform_defines(sail_json)

    tasks: list[BuildTask] = []
    inventory: list[KitTest] = []

    for name_str, meta in sorted(selected.items()):
        name = Path(name_str)
        # C tests link framework C-runtime sources into the object; a certified
        # C-test object plus a linked shim is an unvalidated corner, so skip them
        # explicitly rather than emit something untested.
        if meta.is_c_test:
            rprint(f"[yellow]Skipping C test (not supported in kits yet):[/] {name}", file=sys.stderr)
            continue

        march = meta.march.replace("${XLEN}", str(xlen))
        mabi = _mabi(xlen, meta.e_ext)
        flen = meta.flen
        test_file_define = f'-DTEST_FILE="{name.name}"'

        results = build_dir / name.with_suffix(".results")
        obj = obj_root / name.with_suffix(".o")

        # Signature chain (only for tests that need one), identical to the normal
        # build so the baked-in golden signature is the same one ACT would use.
        obj_deps: tuple[Path, ...] = ()
        sig_flag = "-DRVTEST_NOSIG"
        if meta.needs_signature:
            sig_elf = build_dir / name.with_suffix(".sig.elf")
            sig = build_dir / name.with_suffix(".sig")
            sig_trace = build_dir / name.with_suffix(".sig.trace")
            sig_log = build_dir / name.with_suffix(".sig.log")

            # 1. signature ELF (DUT include dir present; sail_macros.h overrides
            #    the model macros because RVTEST_SELFCHECK is not defined here)
            tasks.append(
                BuildTask(
                    outputs=(sig_elf,),
                    extra_inputs=(meta.test_path, *sig_inputs),
                    action=SubprocessAction(
                        cmd=[
                            *sig_cmd_prefix,
                            "-o",
                            str(sig_elf),
                            f"-march={march}",
                            f"-mabi={mabi}",
                            "-DSIGNATURE",
                            *signature_compile_flags,
                            f"-DTEST_FLEN={flen}",
                            test_file_define,
                            str(meta.test_path),
                        ]
                    ),
                    intermediate=True,
                )
            )

            # 2. golden signature from the reference model
            tasks.append(
                BuildTask(
                    outputs=(sig,),
                    deps=(sig_elf,),
                    extra_inputs=ref_inputs,
                    action=SubprocessAction(
                        cmd=_ref_model_sig_cmd(config, sig_elf, sig, sig_trace, xlen, debug),
                        stdout_file=sig_log,
                    ),
                    intermediate=True,
                )
            )

            # 3. .results (assembler-friendly form of the signature)
            tasks.append(
                BuildTask(
                    outputs=(results,),
                    deps=(sig,),
                    action=PythonAction(fn=process_signature_file, args=(sig, xlen)),
                    intermediate=True,
                )
            )
            obj_deps = (results,)
            sig_flag = f'-DSIGNATURE_FILE="{results}"'

        # 4. the certified object: signature baked in, no DUT include dir
        tasks.append(
            BuildTask(
                outputs=(obj,),
                deps=obj_deps,
                extra_inputs=(meta.test_path, *kit_inputs),
                action=SubprocessAction(
                    cmd=[
                        *kit_cmd_prefix,
                        "-c",
                        "-o",
                        str(obj),
                        f"-march={march}",
                        f"-mabi={mabi}",
                        "-DRVTEST_SELFCHECK",
                        "-DRVMODEL_SHIM_EXTERN",
                        sig_flag,
                        f"-DXLEN={xlen}",
                        f"-DTEST_FLEN={flen}",
                        test_file_define,
                        str(meta.test_path),
                    ]
                ),
                label=f"kit object {name}",
            )
        )

        # 5. refuse to ship an object that needs anything the shim does not define
        stamp = build_dir / name.with_suffix(".checked")
        tasks.append(
            BuildTask(
                outputs=(stamp,),
                deps=(obj,),
                action=PythonAction(fn=_check_and_stamp, args=(obj, config.objdump_exe, stamp)),
            )
        )

        inventory.append(KitTest(name=str(name.with_suffix("")), obj=obj, march=march, mabi=mabi, xlen=xlen, flen=flen))

    return tasks, inventory


def _check_and_stamp(obj: Path, objdump_exe: Path | None, stamp: Path) -> None:
    check_object_is_clean(obj, objdump_exe)
    stamp.touch()


_BUILD_SCRIPT = """#!/bin/bash
# build_kit.sh -- build the certification-test ELFs.
#
# You supply rvmodel_macros.h; nothing in it leaves your machine. This script
# assembles it into the model shim and links that with the pre-certified test
# objects shipped in objects/.
#
# Usage:  ./build_kit.sh <path-to-dir-containing-rvmodel_macros.h> [outdir]
set -euo pipefail

DUT_INCLUDE="${1:?usage: ./build_kit.sh <dir-with-rvmodel_macros.h> [outdir]}"
OUTDIR="${2:-elfs}"
KIT="$(cd "$(dirname "$0")" && pwd)"

CC="${CC:-%(compiler)s}"
MARCH="%(march)s"
MABI="%(mabi)s"
XLEN=%(xlen)d

[ -f "$DUT_INCLUDE/rvmodel_macros.h" ] || {
  echo "error: no rvmodel_macros.h in $DUT_INCLUDE" >&2; exit 1; }

mkdir -p "$OUTDIR"

echo "Assembling model shim from your rvmodel_macros.h ..."
"$CC" -I"$DUT_INCLUDE" -I"$KIT/include" -O0 -g -mcmodel=medany -nostdlib \\
      -march="$MARCH" -mabi="$MABI" -DXLEN=$XLEN -DTEST_FLEN=64 \\
      -DRVTEST_SELFCHECK -c -o "$OUTDIR/rvmodel_shim.o" "$KIT/rvmodel_shim.S"

echo "Linking $(grep -c '"object"' "$KIT/manifest.json") test objects ..."
fail=0
while IFS=$'\\t' read -r name obj march mabi; do
  out="$OUTDIR/$(basename "$name").elf"
  mkdir -p "$(dirname "$out")"
  if ! "$CC" -T"$KIT/act_link.ld" -nostdlib -mcmodel=medany \\
        -march="$march" -mabi="$mabi" -Wl,--no-relax -Wl,--no-warn-rwx-segments \\
        -o "$out" "$KIT/$obj" "$OUTDIR/rvmodel_shim.o"; then
    echo "  FAILED: $name" >&2; fail=$((fail+1))
  fi
done < <(python3 -c "
import json,sys
m=json.load(open('$KIT/manifest.json'))
for t in m['tests']:
    print('\\t'.join([t['name'],t['object'],t['march'],t['mabi']]))
")

echo
if [ $fail -eq 0 ]; then echo \"All ELFs built into $OUTDIR/\"; else echo \"$fail link failure(s)\" >&2; exit 1; fi
"""


_README = """# ACT Certification Kit -- %(config)s

Generated %(generated)s by ACT %(act_version)s.

Your `rvmodel_macros.h` never leaves your machine. This kit contains test objects
that were assembled by the certification authority with expected results already
built in, plus a shim source file that adapts them to your device.

## Build

    ./build_kit.sh /path/to/dir/containing/rvmodel_macros.h

This produces `elfs/`. Run those ELFs on your DUT and return the logs.

## What you must provide

`rvmodel_macros.h` defining the usual RVMODEL_* macros. The shim
(`rvmodel_shim.S`) turns them into these %(nsym)d symbols:

%(symbols)s

## Rules that must not be broken

* **Use the supplied `act_link.ld` unchanged.** The expected results were
  computed against exactly this memory layout. Changing an address invalidates
  every test in the kit.
* **Do not rebuild the objects in `objects/`.** They are the certified artifacts;
  `manifest.json` records a SHA-256 for each one. Verify with:

      sha256sum -c checksums.sha256

* **Do not edit `include/`.** Those headers must match the ones used to produce
  the expected results.
* Your macro implementations may be any size. Everything you supply is linked
  after `.data`, so it cannot disturb a result-visible address.

## Device values

The device addresses and interrupt timings in `include/dut_environment.h` came
from your submitted config, and the reference model was configured with the same
values. If they do not match your hardware, the config is wrong -- fix the config
and request a new kit rather than editing the header.
"""


def _write_kit_files(
    kit_dir: Path, config: Config, xlen: int, tests: list[KitTest], tests_dir: Path, workdir: Path
) -> None:
    """Copy the static kit inputs and write the manifest, README and build script."""
    inc = kit_dir / "include"
    inc.mkdir(parents=True, exist_ok=True)

    # Env headers. The customer compiles the shim, so it needs the same headers
    # the certified objects were built against. Only headers: tests/ must contain
    # no non-test .S file, because generate_test_dict() rglobs "*.S" over it.
    for h in sorted((tests_dir / "env").iterdir()):
        if h.suffix == ".h":
            shutil.copy2(h, inc / h.name)

    # UDB- and config-derived headers
    cfg_wkdir = workdir / config.name
    for gen in ("rvtest_config.h", "dut_environment.h"):
        src = cfg_wkdir / gen
        if src.exists():
            shutil.copy2(src, inc / gen)

    # Framework-owned kit assets (linker script and the model shim template).
    # These live in the act package rather than tests/ precisely so the test
    # scanner never sees the shim.
    act_res = importlib.resources.files("act")
    shutil.copy2(Path(str(act_res / "data" / "act_link.ld")), kit_dir / "act_link.ld")
    shutil.copy2(Path(str(act_res / "data" / "rvmodel_shim.S")), kit_dir / "rvmodel_shim.S")

    # Publish the built objects into the kit, then hash what actually shipped
    # (not the workdir copy) so the manifest describes the delivered bytes.
    entries = []
    for t in sorted(tests, key=lambda x: x.name):
        rel = Path("objects") / f"{t.name}.o"
        dest = kit_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(t.obj, dest)
        entries.append(
            {
                "name": t.name,
                "object": str(rel),
                "march": t.march,
                "mabi": t.mabi,
                "xlen": t.xlen,
                "flen": t.flen,
                "sha256": _sha256(dest),
            }
        )
    manifest = {
        "kit_version": 1,
        "config": config.name,
        "xlen": xlen,
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "act_version": _act_version(),
        "toolchain": {
            "compiler": _tool_version(config.compiler_exe, "--version"),
            "reference_model": f"{config.ref_model_type.value} {_tool_version(config.ref_model_exe, '--version')}",
        },
        "linker_script": "act_link.ld",
        "shim_source": "rvmodel_shim.S",
        "shim_symbols": list(SHIM_SYMBOLS),
        "test_count": len(entries),
        "tests": entries,
    }
    (kit_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    # Standalone checksum file so the customer can verify without parsing JSON
    (kit_dir / "checksums.sha256").write_text("".join(f"{e['sha256']}  {e['object']}\n" for e in entries))

    marches = {t.march for t in tests}
    (kit_dir / "build_kit.sh").write_text(
        _BUILD_SCRIPT
        % {
            "compiler": Path(str(config.compiler_exe)).name,
            "march": min(marches) if marches else f"rv{xlen}i",
            "mabi": _mabi(xlen, False),
            "xlen": xlen,
        }
    )
    (kit_dir / "build_kit.sh").chmod(0o755)

    (kit_dir / "README.md").write_text(
        _README
        % {
            "config": config.name,
            "generated": manifest["generated"],
            "act_version": manifest["act_version"],
            "nsym": len(SHIM_SYMBOLS),
            "symbols": "\n".join(f"  - `{s}`" for s in SHIM_SYMBOLS),
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
    jobs: Annotated[int, typer.Option("--jobs", "-j", help="Parallel jobs (0 = CPU count)")] = 0,
    *,
    keep_going: Annotated[bool, typer.Option("--keep-going", "-k", help="Continue after failures")] = False,
    verbose: Annotated[bool, typer.Option(help="Print each command")] = False,
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

    prepared = prepare_configs_and_select_tests([config_file], full_tests, workdir, jobs=jobs, verbose=verbose)
    config, params, selected = prepared[0]
    xlen = params["MXLEN"]
    if not isinstance(xlen, int):
        raise TypeError(f"MXLEN must be an integer, got {xlen!r}")

    if not selected:
        rprint("[bold red]No tests selected for this config.[/]", file=sys.stderr)
        raise typer.Exit(1)

    # A kit is only meaningful when the config carries the DUT values, because a
    # certified object is built with no access to rvmodel_macros.h.
    if not (workdir / config.name / "dut_environment.h").exists():
        rprint("[bold red]Config has no dut_environment block.[/] A kit cannot be built without it.", file=sys.stderr)
        raise typer.Exit(1)

    kit_dir.mkdir(parents=True, exist_ok=True)
    rprint(f"Building kit for [cyan]{config.name}[/] ({len(selected)} tests, RV{xlen}) -> {kit_dir}")

    tasks, inventory = _gen_kit_tasks(config, xlen, selected, test_dir, workdir, kit_dir, debug=False)
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

    built = [t for t in inventory if t.obj.exists()]
    if len(built) != len(inventory):
        rprint(
            f"[yellow]Warning:[/] {len(inventory) - len(built)} object(s) missing; kit will be incomplete.",
            file=sys.stderr,
        )

    _write_kit_files(kit_dir, config, xlen, built, test_dir, workdir)

    rprint(f"[bold green]Kit complete:[/] {len(built)} certified objects in {kit_dir}")
    rprint(f"  manifest: {kit_dir / 'manifest.json'}")
    rprint("  customer builds with: ./build_kit.sh <dir-with-rvmodel_macros.h>")


def main() -> None:
    package_app()


if __name__ == "__main__":
    main()
