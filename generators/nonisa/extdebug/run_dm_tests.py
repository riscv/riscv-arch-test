#!/usr/bin/env python3
##################################
# run_dm_tests.py
#
# Run External Debug tests on ACT DUT configurations through their EDALs.
# Each test file runs on a freshly started DUT.  A test that needs an EDAL
# level the DUT lacks (e.g. DMI access on a DUT with no Debug Module) reports
# SKIP.  Run from the ACT root with uv:
#
#   uv run generators/nonisa/extdebug/run_dm_tests.py                          # DM.py on spike-rv64-max
#   uv run generators/nonisa/extdebug/run_dm_tests.py -c spike -c cvw-rv64gc   # every Spike config, and cvw-rv64gc
#   uv run generators/nonisa/extdebug/run_dm_tests.py -c config/spike/spike-rv32-max DM.py
#
# A config name selects every config/**/run_cmd.txt with that directory name in its path,
# like the Makefile run targets.  cvw configs need $WALLY set to a cvw tree with the
# Debug Module and testbench/common/jtag_rbb.sv.
#
# David Harris (David_Harris@hmc.edu) with Claude, 8 November 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from __future__ import annotations

import argparse
import runpy
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import DM_helpers
import EDAL
from DM_helpers import DMError

DEFAULT_TESTS = [HERE / "DM.py"]


def run_test(config: EDAL.DutConfig, test: Path, dut_args: str) -> str:
    """Run one test file on a freshly started DUT.  Print and return its result."""
    start = time.monotonic()
    DM_helpers.dm_reset()
    try:
        with EDAL.open_edal(config, args=dut_args) as e:
            EDAL.set_active(e)
            try:
                runpy.run_path(str(test), run_name="__main__")
            finally:
                EDAL.set_active(None)
        result, detail = "PASS", ""
    except DMError as err:  # a test may still raise DMError to stop at a fatal error
        DM_helpers.dm_errors.append(err)
        result, detail = "FAIL", ""
    except EDAL.EDALUnsupported as err:
        result, detail = "SKIP", str(err)
    except EDAL.EDALError as err:
        result, detail = "ERROR", f"EDAL: {err}"
    except Exception:  # noqa: BLE001 - report any other failure as ERROR and go on to the next test
        result, detail = "ERROR", traceback.format_exc().rstrip()
    errors = [str(err) for err in DM_helpers.dm_errors]
    if errors and result == "PASS":
        result = "FAIL"
    print(f"{result:<5} {config.name:<20} {test.name:<24} {time.monotonic() - start:6.1f} s", flush=True)
    if errors:
        print(f"      {len(errors)} error{'s' if len(errors) != 1 else ''}:", flush=True)
        for err in errors:
            print("        " + err, flush=True)
    if detail:
        print("      " + detail.replace("\n", "\n      "), flush=True)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tests", nargs="*", type=Path, default=DEFAULT_TESTS, help="test files (default: DM.py)")
    parser.add_argument(
        "-c",
        "--config",
        action="append",
        help="ACT config name or directory; repeat for several (default: spike-rv64-max)",
    )
    parser.add_argument("--dut-args", default="", help="extra simulator arguments, e.g. '--dm-progsize=0' for Spike")
    args = parser.parse_args()

    try:
        configs = [c for selector in (args.config or ["spike-rv64-max"]) for c in EDAL.find_configs(selector)]
    except EDAL.EDALError as err:
        print(f"error: {err}", file=sys.stderr)
        return 2

    results: dict[str, int] = {}
    for config in configs:
        for test in args.tests:
            result = run_test(config, test.resolve(), args.dut_args)
            results[result] = results.get(result, 0) + 1
    print(", ".join(f"{n} {result}" for result, n in sorted(results.items())))
    return 0 if set(results) <= {"PASS", "SKIP"} else 1


if __name__ == "__main__":
    sys.exit(main())
