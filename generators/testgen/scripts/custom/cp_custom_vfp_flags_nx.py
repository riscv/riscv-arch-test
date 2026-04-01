# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_vfp_flags_nx

For instructions that can raise NX but not NV/DZ/OF/UF (int→float conversions).
"""

from coverpoint_registry import register
from ._vfp_flags_common import should_skip, gen_spacer, gen_nx


@register("cp_custom_vfp_flags_nx")
def make(test, sew):
    if should_skip(test, sew):
        return

    gen_spacer(test, sew)
    gen_nx(test, sew)
