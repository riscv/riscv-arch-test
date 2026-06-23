##################################
# _corner_helpers.py
#
# Shared corner value helpers for vector edge coverpoints.
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.random import random_int
from testgen.data.state import TestData

CORNER_NAMES = [
    "zero",
    "one",
    "two",
    "ones",
    "onesm1",
    "min",
    "minm1",
    "max",
    "maxm1",
    "walkeven",
    "walkodd",
    "random",
]


def _corner_value(corner: str, sew: int) -> int:
    if corner == "zero":
        return 0
    if corner == "one":
        return 1
    if corner == "two":
        return 2
    if corner == "ones":
        return (1 << sew) - 1
    if corner == "onesm1":
        return (1 << sew) - 2
    if corner == "min":
        return 1 << (sew - 1)
    if corner == "minm1":
        return (1 << (sew - 1)) + 1
    if corner == "max":
        return (1 << (sew - 1)) - 1
    if corner == "maxm1":
        return (1 << (sew - 1)) - 2
    if corner == "walkeven":
        return sum(1 << i for i in range(sew) if i % 2 == 0)
    if corner == "walkodd":
        return sum(1 << i for i in range(sew) if i % 2 == 1)
    if corner == "random":
        return random_int(sew)
    raise ValueError(f"Unknown corner: {corner}")


def make_corner_label(corner: str, sew: int, test_data: TestData, suffix: str = "") -> str:
    if corner == "random":
        label = f"vs_corner_random_emul1_{test_data.test_count}{suffix}"
    else:
        label = f"vs_corner_{corner}_emul1"
    test_data.register_vector_data(label, sew, elements=[_corner_value(corner, sew)])
    return label
