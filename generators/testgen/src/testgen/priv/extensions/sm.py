##################################
# priv/extensions/sm.py
#
# Sm privileged extension test generator.
# jcarlin@hmc.edu Jan 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Sm privileged extension test generator."""

from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator


@add_priv_test_generator("Sm")
def make_sm(test_data: TestData) -> list[str]:
    """Generate tests for Sm privileged extension."""
    return ["// SM privileged test placeholder"]
