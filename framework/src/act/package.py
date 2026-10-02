##################################
# package.py
#
# SPDX-License-Identifier: Apache-2.0
#
# Build a certification kit: pre-assembled test objects plus the model shim
# the customer links their private RVMODEL macros into.
##################################

"""Build a certification kit for one config.

Each test is assembled into an object with the Sail golden signature baked in,
shipped with a shim the customer compiles against their private rvmodel_macros.h.
Objects are built with RVMODEL_SHIM_EXTERN and no DUT include dir, so any leftover
dependency on rvmodel_macros.h fails the build instead of leaking DUT code.

Not a tamper guard: the customer runs the ELFs and owns rvmodel_halt_pass. The
hashes prove which binaries were certified, not what ran.
"""

from __future__ import annotations

import hashlib
import importlib.resources
import json
import os
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
from act.build_types import BuildTask, PythonAction, SubprocessAction
from act.certificate_tests import certificate_exists
from act.config import Config
from act.parse_test_constraints import TestMetadata, TestYamlHeaderError, generate_test_dict
from act.select_tests import prepare_configs_and_select_tests
from act.sig_modify import process_signature_file

# Symbols the shim must define; keep in sync with data/rvmodel_shim.S.
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
    "rvmodel_clr_vsw_int_h",
    "rvmodel_clr_vtimer_int_h",
    "rvmodel_clr_vext_int_h",
)

# CSR_SEDELEG/CSR_SIDELEG are .set to undefined symbols in rvtest_trap_handler.h
# (pre-existing bug; linker resolves them to 0). _end is defined by act_link.ld, so
# it is undefined in an object by construction. Not the shim's job, so don't flag.
_KNOWN_UNRESOLVED: frozenset[str] = frozenset({"CSR_SEDELEG", "CSR_SIDELEG", "_end"})

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


@dataclass
class KitTest:
    """One certified test object in the kit."""

    name: str  # e.g. "priv/InterruptsSm/InterruptsSm-00"
    obj: Path  # absolute path to the built object
    march: str
    mabi: str
    xlen: int
    flen: str
    results: Path | None = None  # golden signature file, for the provenance digest


def _mabi(xlen: int, e_ext: bool) -> str:
    """Match build_plan.py's ABI selection."""
    return f"{'i' if xlen == 32 else ''}lp{xlen}{'e' if e_ext else ''}"


def _kit_compiler_cmd(
    config: Config, xlen: int, tests_dir: Path, udb_header_dir: Path, empty_include: Path
) -> list[str]:
    """Compiler prefix for certified objects, with an empty dir in place of the
    DUT include dir so a stray rvmodel_macros.h reference fails the build."""
    from act.toolchain import Toolchain

    cmd = list(Toolchain(config.compiler_exe, config.compiler_type).compile_prefix(xlen))
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
    """Fail if a certified object references anything the shim does not provide,
    so a bad object stops the kit here instead of at the customer."""
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
    kit_stamp: KitStamp,
) -> tuple[list[BuildTask], list[KitTest]]:
    """One certified object per test, plus the kit inventory.

    Per test: test.S -> sig.elf -> sig (ref model) -> results, then compile the
    DUT-free object with the results baked in. The signature steps match the
    normal build so the baked-in signature is identical.
    """
    # Reuse build_plan's command helpers so the compile flags stay in sync (they
    # drifted once already when the main build added -DTEST_FILE and platform defines).
    from act.build_plan import _ref_model_sig_cmd, _sail_platform_defines
    from act.toolchain import Toolchain

    config_wkdir = workdir / config.name
    build_dir = config_wkdir / "package_build"
    # build()'s cache keys outputs under cache_root, so build here and copy into the kit.
    obj_root = config_wkdir / "kit_objects"
    empty_include = config_wkdir / "_kit_no_dut_include"
    empty_include.mkdir(parents=True, exist_ok=True)

    # One stamp header for the whole kit, force-included into every object. Written
    # eagerly rather than as a build task: it is an input to every compile, and a new
    # kit id must rebuild every object rather than reuse a cached one.
    build_dir.mkdir(parents=True, exist_ok=True)
    stamp_h = build_dir / "kit_stamp.h"
    stamp_h.write_text(kit_stamp.header_text())

    toolchain = Toolchain(config.compiler_exe, config.compiler_type)
    env_dir = tests_dir / "env"
    sig_cmd_prefix = [
        *toolchain.compile_prefix(xlen),
        f"-I{config.dut_include_dir.absolute()}",
        f"-T{config.linker_script.absolute()}",
        "-O0",
        "-g",
        "-mcmodel=medany",
        "-nostdlib",
        f"-I{env_dir}",
        f"-I{config_wkdir.absolute()}",
    ]
    kit_cmd_prefix = _kit_compiler_cmd(config, xlen, tests_dir, config_wkdir, empty_include)

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
        # sail_macros.h wants the CLINT / interrupt-generator addresses via -D.
        signature_compile_flags = _sail_platform_defines(sail_json)

    tasks: list[BuildTask] = []
    inventory: list[KitTest] = []

    for name_str, meta in sorted(selected.items()):
        name = Path(name_str)
        # C tests pull in C-runtime sources; kit support for them is unvalidated, so skip.
        if meta.is_c_test:
            rprint(f"[yellow]Skipping C test (not supported in kits yet):[/] {name}", file=sys.stderr)
            continue

        march = meta.march.replace("${XLEN}", str(xlen))
        march_flags = list(toolchain.march_flags(xlen, meta.march, assembly=True, e_ext=meta.e_ext))
        mabi = _mabi(xlen, meta.e_ext)
        flen = meta.flen
        test_file_define = f'-DTEST_FILE="{name.name}"'

        results = build_dir / name.with_suffix(".results")
        obj = obj_root / name.with_suffix(".o")

        obj_deps: tuple[Path, ...] = ()
        sig_flag = "-DRVTEST_NOSIG"
        if meta.needs_signature:
            sig_elf = build_dir / name.with_suffix(".sig.elf")
            sig = build_dir / name.with_suffix(".sig")
            sig_trace = build_dir / name.with_suffix(".sig.trace")
            sig_log = build_dir / name.with_suffix(".sig.log")

            # sig.elf: built with the DUT include dir; sail_macros.h drives it
            # (RVTEST_SELFCHECK is off here).
            tasks.append(
                BuildTask(
                    outputs=(sig_elf,),
                    extra_inputs=(meta.test_path, *sig_inputs),
                    action=SubprocessAction(
                        cmd=[
                            *sig_cmd_prefix,
                            "-o",
                            str(sig_elf),
                            *march_flags,
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
                        cmd=_ref_model_sig_cmd(config, sig_elf, sig, sig_trace, xlen, debug, False),
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
            # Bake a digest of the golden signature block into the object so the
            # DUT log can state which signatures the run was checked against.
            digest_h = build_dir / name.with_suffix(".sigdigest.h")
            tasks.append(
                BuildTask(
                    outputs=(digest_h,),
                    deps=(results,),
                    action=PythonAction(fn=write_sigdigest_header, args=(results, digest_h)),
                    intermediate=True,
                )
            )
            obj_deps = (results, digest_h)
            sig_flag = f'-DSIGNATURE_FILE="{results}"'

        # 4. the certified object: signature baked in, no DUT include dir
        tasks.append(
            BuildTask(
                outputs=(obj,),
                deps=obj_deps,
                extra_inputs=(meta.test_path, stamp_h, *kit_inputs),
                action=SubprocessAction(
                    cmd=[
                        *kit_cmd_prefix,
                        "-c",
                        "-o",
                        str(obj),
                        *march_flags,
                        f"-mabi={mabi}",
                        "-DRVTEST_SELFCHECK",
                        "-DRVMODEL_SHIM_EXTERN",
                        sig_flag,
                        "-include",
                        str(stamp_h),
                        *(
                            ["-include", str(build_dir / name.with_suffix(".sigdigest.h"))]
                            if meta.needs_signature
                            else []
                        ),
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

        inventory.append(
            KitTest(
                name=str(name.with_suffix("")),
                obj=obj,
                march=march,
                mabi=mabi,
                xlen=xlen,
                flen=flen,
                results=results if meta.needs_signature else None,
            )
        )

    return tasks, inventory


def write_sigdigest_header(results: Path, out: Path) -> None:
    """Emit `#define RVCP_SIG_DIGEST` holding the sha256 of the golden signatures."""
    digest = hashlib.sha256(results.read_bytes()).hexdigest()
    out.write_text(f'#define RVCP_SIG_DIGEST "{digest}"\n')


def signature_digest(results: Path) -> str:
    return hashlib.sha256(results.read_bytes()).hexdigest()


def _check_and_stamp(obj: Path, objdump_exe: Path | None, stamp: Path) -> None:
    check_object_is_clean(obj, objdump_exe)
    stamp.touch()


_BUILD_SCRIPT = """#!/bin/bash
# build_kit.sh -- build the certification-test ELFs.
#
# You supply rvmodel_macros.h; nothing in it leaves your machine. This script
# builds it into librvmodel.a and links that against the certified test archives
# in lib/, which already contain the expected results.
#
# Usage:  ./build_kit.sh <dir-containing-rvmodel_macros.h> [outdir]
set -euo pipefail

DUT_INCLUDE="${1:?usage: ./build_kit.sh <dir-with-rvmodel_macros.h> [outdir]}"
OUTDIR="${2:-elfs}"
KIT="$(cd "$(dirname "$0")" && pwd)"

CC="${CC:-%(compiler)s}"
AR="${AR:-%(ar)s}"
MARCH="%(march)s"
MABI="%(mabi)s"
XLEN=%(xlen)d

[ -f "$DUT_INCLUDE/rvmodel_macros.h" ] || {
  echo "error: no rvmodel_macros.h in $DUT_INCLUDE" >&2; exit 1; }

mkdir -p "$OUTDIR" "$OUTDIR/.work"

echo "==> Verifying kit integrity"
( cd "$KIT" && sha256sum -c checksums.sha256 --quiet ) && echo "    all objects and archives match the manifest"

echo "==> Building your model library (librvmodel.a) from your private macros"
"$CC" -I"$DUT_INCLUDE" -I"$KIT/include" -O0 -g -mcmodel=medany -nostdlib \
      -march="$MARCH" -mabi="$MABI" -DXLEN=$XLEN -DTEST_FLEN=64 \
      -DRVTEST_SELFCHECK -c -o "$OUTDIR/.work/rvmodel_shim.o" "$KIT/rvmodel_shim.S"
"$AR" rcs "$OUTDIR/librvmodel.a" "$OUTDIR/.work/rvmodel_shim.o"
echo "    $OUTDIR/librvmodel.a"

echo "==> Linking certified tests against your model library"
fail=0; n=0
while IFS=$'\t' read -r name obj march mabi; do
  out="$OUTDIR/$(basename "$name").elf"
  if "$CC" -T"$KIT/act_link.ld" -nostdlib -mcmodel=medany \
        -march="$march" -mabi="$mabi" -Wl,--no-relax -Wl,--no-warn-rwx-segments \
        -o "$out" "$KIT/$obj" -L"$OUTDIR" -Wl,--whole-archive -lrvmodel -Wl,--no-whole-archive; then
    n=$((n+1))
  else
    echo "  FAILED: $name" >&2; fail=$((fail+1))
  fi
done < <(python3 -c "
import json,sys
m=json.load(open('$KIT/manifest.json'))
for t in m['tests']:
    print('\t'.join([t['name'],t['object'],t['march'],t['mabi']]))
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
built in, plus a shim source file that adapts them to your device.

## Build

    ./build_kit.sh /path/to/dir/containing/rvmodel_macros.h

This produces `elfs/`. Run those ELFs on your DUT and return the logs.

## Start with the Hello tests

If this kit includes the `Hello` suite, run those ELFs first. There are seven, they
finish in well under a second, and each one checks a single layer of what your
environment has to provide -- in order: boot and I/O, the signature mechanism, trap
entry and return, privilege transitions, the software and external interrupt macros,
the timer device addresses, and the access-fault address. The file that fails names
the layer to fix. Working through them before launching the full suite turns a
multi-hour run into a few seconds of feedback.

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

  Every object also carries this kit's id, and each test prints it on the pass
  path:

      RVCP-KIT: id=%(kit_id)s built=%(generated)s

  A log without that line, or with a different id, did not come from this kit, and
  the returned results will be rejected.

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
    kit_dir: Path, config: Config, xlen: int, tests: list[KitTest], tests_dir: Path, workdir: Path, stamp: KitStamp
) -> None:
    """Copy the static kit inputs and write the manifest, README and build script."""
    inc = kit_dir / "include"
    inc.mkdir(parents=True, exist_ok=True)

    # Env headers the shim needs. Only .h: a non-test .S under tests/ would be
    # picked up by generate_test_dict()'s rglob("*.S").
    for h in sorted((tests_dir / "env").iterdir()):
        if h.suffix == ".h":
            shutil.copy2(h, inc / h.name)

    # UDB- and config-derived headers
    cfg_wkdir = workdir / config.name
    for gen in ("rvtest_config.h", "dut_environment.h"):
        src = cfg_wkdir / gen
        if src.exists():
            shutil.copy2(src, inc / gen)

    # Framework-owned kit assets. These live in the act package, not tests/, so
    # the test scanner never sees the shim.
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
        sig_digest = signature_digest(t.results) if t.results and t.results.exists() else None
        sig_values = (
            len([ln for ln in t.results.read_text().splitlines() if ln.strip()])
            if t.results and t.results.exists()
            else 0
        )
        entries.append(
            {
                "name": t.name,
                "object": str(rel),
                "suite": str(Path(t.name).parent),
                "march": t.march,
                "mabi": t.mabi,
                "xlen": t.xlen,
                "flen": t.flen,
                "sha256": _sha256(dest),
                "signature_sha256": sig_digest,
                "signature_values": sig_values,
            }
        )
    # Bundle the certified objects into one static archive per suite. This is what
    # the customer receives and links against.
    lib_dir = kit_dir / "lib"
    lib_dir.mkdir(parents=True, exist_ok=True)
    ar = Path(str(config.compiler_exe).replace("-gcc", "-ar"))
    if not ar.exists():
        ar = Path("ar")
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
            {
                "archive": f"lib/{libname}",
                "suite": suite,
                "members": len(members),
                "sha256": _sha256(libpath),
            }
        )

    manifest = {
        "kit_version": 2,
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
        "linker_script": "act_link.ld",
        "shim_source": "rvmodel_shim.S",
        "shim_symbols": list(SHIM_SYMBOLS),
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

    marches = {t.march for t in tests}
    (kit_dir / "build_kit.sh").write_text(
        _BUILD_SCRIPT
        % {
            "compiler": Path(str(config.compiler_exe)).name,
            "ar": Path(str(config.compiler_exe)).name.replace("-gcc", "-ar"),
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
            "kit_id": manifest["kit_id"],
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
        [config_file], certificate, full_tests, workdir, jobs=jobs, verbose=verbose
    )
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

    stamp = KitStamp(
        kit_id=kit_id or secrets.token_hex(16),
        built=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        certificate=certificate,
    )
    tasks, inventory = _gen_kit_tasks(config, xlen, selected, test_dir, workdir, kit_dir, debug=False, kit_stamp=stamp)
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

    _write_kit_files(kit_dir, config, xlen, built, test_dir, workdir, stamp)

    rprint(f"[bold green]Kit complete:[/] {len(built)} certified objects in {kit_dir}")
    rprint(f"  manifest: {kit_dir / 'manifest.json'}")
    rprint("  customer builds with: ./build_kit.sh <dir-with-rvmodel_macros.h>")


def main() -> None:
    package_app()


if __name__ == "__main__":
    main()
