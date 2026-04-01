# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_vfp_flags_inactive_not_set

Verifies that inactive elements do not set FP flags (vfrsqrt7.v only).
"""

from coverpoint_registry import register
from ._vfp_flags_common import should_skip, gen_spacer, gen_inactive


@register("cp_custom_vfp_flags_inactive_not_set")
def make(test, sew):
    if should_skip(test, sew):
        return

    gen_spacer(test, sew)
    gen_inactive(test, sew)
