# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_vfp_flags_nv_dz

For instructions that can raise NV and DZ but not NX/OF/UF (vfrec7.v).
"""

from coverpoint_registry import register
from ._vfp_flags_common import should_skip, gen_spacer, gen_nv, gen_dz


@register("cp_custom_vfp_flags_nv_dz")
def make(test, sew):
    if should_skip(test, sew):
        return

    gen_spacer(test, sew)
    gen_nv(test, sew)
    gen_dz(test, sew)
