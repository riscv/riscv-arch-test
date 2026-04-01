# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_vfp_flags_nv_nx

For FP arithmetic that can raise NV and NX but not DZ/OF/UF
(FMA, sub, conversion, sqrt, reduction, etc.).
"""

from coverpoint_registry import register
from ._vfp_flags_common import should_skip, gen_spacer, gen_nv, gen_nx


@register("cp_custom_vfp_flags_nv_nx")
def make(test, sew):
    if should_skip(test, sew):
        return

    gen_spacer(test, sew)
    gen_nv(test, sew)
    gen_nx(test, sew)
