##################################
# priv/extensions/sv/modes.py
#
# Privilege-mode transitions for Sv tests under T-SBI.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Privilege-mode transitions shared by the Sv suites.

The test driver runs from the boot identity map of the test image. begin_sv_test
registers the virtual alias of the code region (va_rvtest_code_begin, which carries
PTE.U for U-mode tests) with SAVE_AREA_SETUP, so the T-SBI GOTO macros move a U-mode
excursion into the alias and back without the test computing any addresses.
"""

BOOT_SMODE = "#define BOOT_TO_SMODE"
BOOT_MMODE = "#define BOOT_TO_MMODE"

_GOTO = {
    "Mmode": "RVTEST_TSBI_GOTO_MMODE",
    "Smode": "RVTEST_TSBI_GOTO_SMODE",
    "Umode": "RVTEST_TSBI_GOTO_UMODE",
}


def enter_mode(mode: str, driver_mode: str) -> list[str]:
    """Switch from the driver mode to the mode under test."""
    return [] if mode == driver_mode else [_GOTO[mode]]


def leave_mode(mode: str, driver_mode: str) -> list[str]:
    """Return to the driver mode after enter_mode."""
    return [] if mode == driver_mode else [_GOTO[driver_mode]]
