##################################
# dut_environment.py
#
# SPDX-License-Identifier: Apache-2.0
#
# Generate dut_environment.h from the `dut_environment` block of a UDB config.
##################################

"""Turn the config's dut_environment block into a C header.

These are DUT-specific values (device addresses, interrupt timing, and whether
the DUT has a standard M-mode) that test objects bake into their code, as opposed
to the DUT code behind the RVMODEL_* macros, which only the driver library sees.
They come from the config, not rvmodel_macros.h, because the reference model
needs the same values to produce a matching signature, and because test objects
are built without rvmodel_macros.h.

UDB accepts an unknown top-level block but udb-gen won't emit it, so we do it here.
"""

from __future__ import annotations

from pathlib import Path

from ruamel.yaml import YAML

# Integer-valued entries: emitted as #define <name> <value>.
# Anything not listed here is rejected, so a typo in a config fails loudly
# instead of silently leaving a constant undefined.
_INT_KEYS: tuple[str, ...] = (
    "RVMODEL_ACCESS_FAULT_ADDRESS",
    "RVMODEL_MSIP_ADDRESS",
    "RVMODEL_MTIME_ADDRESS",
    "RVMODEL_MTIMECMP_ADDRESS",
    "RVMODEL_INTERRUPT_LATENCY",
    "RVMODEL_TIMER_INT_SOON_DELAY",
    "RVMODEL_MAX_CYCLES_PER_TIMER_TICK",
)

# Every config needs these; check_defines.h would stop each test on its own otherwise.
_REQUIRED_KEYS: tuple[str, ...] = ("RVMODEL_INTERRUPT_LATENCY", "RVMODEL_TIMER_INT_SOON_DELAY")

# Boolean flags: emitted as a bare #define of the mapped name when true, omitted when false.
_FLAG_KEYS: dict[str, str] = {
    "STANDARD_SM_SUPPORTED": "STANDARD_SM_SUPPORTED",
    # The DUT's driver provides RVMODEL_INVISIBLE_TRAP_HANDLER (see rvtest_driver.h).
    "INVISIBLE_TRAP_HANDLER": "RVTEST_DUT_INVISIBLE_TRAP_HANDLER",
}

_GUARD = "_ACT_DUT_ENVIRONMENT_H"


def read_dut_environment(udb_config_file: Path) -> dict[str, object]:
    """Return the ``dut_environment`` block, or {} when the config has none."""
    yaml = YAML(typ="safe", pure=True)
    config = yaml.load(udb_config_file.read_text())
    block = (config or {}).get("dut_environment") or {}
    if not isinstance(block, dict):
        raise TypeError(f"dut_environment must be a mapping in {udb_config_file}, got {type(block).__name__}")
    unknown = sorted(set(block) - set(_INT_KEYS) - set(_FLAG_KEYS))
    if unknown:
        known = ", ".join((*_INT_KEYS, *_FLAG_KEYS))
        raise ValueError(f"Unknown dut_environment key(s) in {udb_config_file}: {unknown}. Known keys: {known}")
    return block


def _int_lines(name: str, value: object) -> list[str]:
    """Emit one integer constant plus an agreement check. Test objects never see
    rvmodel_macros.h, so the config is the only source there; the driver build
    sees both and #errors if they disagree, catching a stale value left in the
    DUT's header."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"dut_environment.{name} must be an integer, got {value!r}")
    cfg_name = f"ACT_CFG_{name}"
    return [
        f"#define {cfg_name} {value:#x}",
        f"#ifdef {name}",
        f"  #if ({name}) != ({cfg_name})",
        f'    #error "{name} in rvmodel_macros.h disagrees with dut_environment in the UDB config"',
        "  #endif",
        "#else",
        f"  #define {name} {cfg_name}",
        "#endif",
        "",
    ]


def generate_dut_environment_header(udb_config_file: Path, output_file: Path) -> None:
    """Write dut_environment.h for one config."""
    block = read_dut_environment(udb_config_file)
    missing = [key for key in _REQUIRED_KEYS if key not in block]
    if missing:
        raise ValueError(
            f"{udb_config_file} has no {', '.join(missing)} in its dut_environment block. Test objects "
            "are built without rvmodel_macros.h, so device addresses and timings belong in the config."
        )

    lines = [
        "// Auto-generated from the UDB config's dut_environment block by act (do not edit)",
        "// SPDX-License-Identifier: Apache-2.0",
        "",
        f"#ifndef {_GUARD}",
        f"#define {_GUARD}",
        "",
    ]

    for name in _INT_KEYS:
        if name in block:
            lines += _int_lines(name, block[name])

    for key, name in _FLAG_KEYS.items():
        if block.get(key):
            lines += [f"#ifndef {name}", f"  #define {name}", "#endif", ""]

    lines += [f"#endif // {_GUARD}", ""]
    output_file.write_text("\n".join(lines))
