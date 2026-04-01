# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_vfp_flags_nv_nx_of_uf

For instructions that can raise NV, NX, OF, and UF but not DZ
(vfmul.vv, vfmul.vf).
"""

from coverpoint_registry import register
from ._vfp_flags_common import should_skip, gen_spacer, gen_nv, gen_nx, gen_of, gen_uf


@register("cp_custom_vfp_flags_nv_nx_of_uf")
def make(test, sew):
    if should_skip(test, sew):
        return

    gen_spacer(test, sew)
    gen_nv(test, sew)
    gen_nx(test, sew)
    gen_of(test, sew)
    gen_uf(test, sew)
