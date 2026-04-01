# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_vfp_flags_set

Universal flag-set check: every flag-setting FP instruction can raise NV
(sNaN input). DZ/NX/OF/UF are covered by per-instruction specific columns.
"""

from coverpoint_registry import register
from ._vfp_flags_common import should_skip, gen_spacer, gen_nv


@register("cp_custom_vfp_flags_set")
def make(test, sew):
    if should_skip(test, sew):
        return

    gen_spacer(test, sew)
    gen_nv(test, sew)
