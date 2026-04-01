# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_vfp_flags_nv_nx_of

For instructions that can raise NV, NX, and OF but not DZ/UF
(vfadd.vv, vfadd.vf).
"""

from coverpoint_registry import register
from ._vfp_flags_common import should_skip, gen_spacer, gen_nv, gen_nx, gen_of


@register("cp_custom_vfp_flags_nv_nx_of")
def make(test, sew):
    if should_skip(test, sew):
        return

    gen_spacer(test, sew)
    gen_nv(test, sew)
    gen_nx(test, sew)
    gen_of(test, sew)
