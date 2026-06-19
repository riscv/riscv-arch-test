##################################
# formatters/params.py
#
# Random parameter generation for vector instructions.
# rwolk@hmc.edu June 2026
# Taken From vector_testgen_common: James Kaden Cassidy kacassidy@hmc.edu 25 Jun 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from __future__ import annotations

import math
import random
from typing import Any, Literal

from testgen.data.params import InstructionParams
from testgen.data.state import TestData

# TODO: REFACTOR THESE LATER
#       It should be part of the formatter and instruction type in general!
#       The source of truth for what attributes an instruction has should not be
#       these lists!

type_vxm = [
    # Unit-stride loads
    "vle8.v",
    "vle16.v",
    "vle32.v",
    "vle64.v",
    "vlseg2e8.v",
    "vlseg2e16.v",
    "vlseg2e32.v",
    "vlseg2e64.v",
    "vlseg3e8.v",
    "vlseg3e16.v",
    "vlseg3e32.v",
    "vlseg3e64.v",
    "vlseg4e8.v",
    "vlseg4e16.v",
    "vlseg4e32.v",
    "vlseg4e64.v",
    "vlseg5e8.v",
    "vlseg5e16.v",
    "vlseg5e32.v",
    "vlseg5e64.v",
    "vlseg6e8.v",
    "vlseg6e16.v",
    "vlseg6e32.v",
    "vlseg6e64.v",
    "vlseg7e8.v",
    "vlseg7e16.v",
    "vlseg7e32.v",
    "vlseg7e64.v",
    "vlseg8e8.v",
    "vlseg8e16.v",
    "vlseg8e32.v",
    "vlseg8e64.v",
    # Fault-only-first loads
    "vle8ff.v",
    "vle16ff.v",
    "vle32ff.v",
    "vle64ff.v",
    "vlseg2e8ff.v",
    "vlseg2e16ff.v",
    "vlseg2e32ff.v",
    "vlseg2e64ff.v",
    "vlseg3e8ff.v",
    "vlseg3e16ff.v",
    "vlseg3e32ff.v",
    "vlseg3e64ff.v",
    "vlseg4e8ff.v",
    "vlseg4e16ff.v",
    "vlseg4e32ff.v",
    "vlseg4e64ff.v",
    "vlseg5e8ff.v",
    "vlseg5e16ff.v",
    "vlseg5e32ff.v",
    "vlseg5e64ff.v",
    "vlseg6e8ff.v",
    "vlseg6e16ff.v",
    "vlseg6e32ff.v",
    "vlseg6e64ff.v",
    "vlseg7e8ff.v",
    "vlseg7e16ff.v",
    "vlseg7e32ff.v",
    "vlseg7e64ff.v",
    "vlseg8e8ff.v",
    "vlseg8e16ff.v",
    "vlseg8e32ff.v",
    "vlseg8e64ff.v",
]

type_vxxm = [
    # Strided loads
    "vlse8.v",
    "vlse16.v",
    "vlse32.v",
    "vlse64.v",
    "vlsseg2e8.v",
    "vlsseg2e16.v",
    "vlsseg2e32.v",
    "vlsseg2e64.v",
    "vlsseg3e8.v",
    "vlsseg3e16.v",
    "vlsseg3e32.v",
    "vlsseg3e64.v",
    "vlsseg4e8.v",
    "vlsseg4e16.v",
    "vlsseg4e32.v",
    "vlsseg4e64.v",
    "vlsseg5e8.v",
    "vlsseg5e16.v",
    "vlsseg5e32.v",
    "vlsseg5e64.v",
    "vlsseg6e8.v",
    "vlsseg6e16.v",
    "vlsseg6e32.v",
    "vlsseg6e64.v",
    "vlsseg7e8.v",
    "vlsseg7e16.v",
    "vlsseg7e32.v",
    "vlsseg7e64.v",
    "vlsseg8e8.v",
    "vlsseg8e16.v",
    "vlsseg8e32.v",
    "vlsseg8e64.v",
]

type_vxvm = [
    # Indexed unordered loads
    "vluxei8.v",
    "vluxei16.v",
    "vluxei32.v",
    "vluxei64.v",
    "vluxseg2ei8.v",
    "vluxseg2ei16.v",
    "vluxseg2ei32.v",
    "vluxseg2ei64.v",
    "vluxseg3ei8.v",
    "vluxseg3ei16.v",
    "vluxseg3ei32.v",
    "vluxseg3ei64.v",
    "vluxseg4ei8.v",
    "vluxseg4ei16.v",
    "vluxseg4ei32.v",
    "vluxseg4ei64.v",
    "vluxseg5ei8.v",
    "vluxseg5ei16.v",
    "vluxseg5ei32.v",
    "vluxseg5ei64.v",
    "vluxseg6ei8.v",
    "vluxseg6ei16.v",
    "vluxseg6ei32.v",
    "vluxseg6ei64.v",
    "vluxseg7ei8.v",
    "vluxseg7ei16.v",
    "vluxseg7ei32.v",
    "vluxseg7ei64.v",
    "vluxseg8ei8.v",
    "vluxseg8ei16.v",
    "vluxseg8ei32.v",
    "vluxseg8ei64.v",
    # Indexed ordered Loads
    "vloxei8.v",
    "vloxei16.v",
    "vloxei32.v",
    "vloxei64.v",
    "vloxseg2ei8.v",
    "vloxseg2ei16.v",
    "vloxseg2ei32.v",
    "vloxseg2ei64.v",
    "vloxseg3ei8.v",
    "vloxseg3ei16.v",
    "vloxseg3ei32.v",
    "vloxseg3ei64.v",
    "vloxseg4ei8.v",
    "vloxseg4ei16.v",
    "vloxseg4ei32.v",
    "vloxseg4ei64.v",
    "vloxseg5ei8.v",
    "vloxseg5ei16.v",
    "vloxseg5ei32.v",
    "vloxseg5ei64.v",
    "vloxseg6ei8.v",
    "vloxseg6ei16.v",
    "vloxseg6ei32.v",
    "vloxseg6ei64.v",
    "vloxseg7ei8.v",
    "vloxseg7ei16.v",
    "vloxseg7ei32.v",
    "vloxseg7ei64.v",
    "vloxseg8ei8.v",
    "vloxseg8ei16.v",
    "vloxseg8ei32.v",
    "vloxseg8ei64.v",
]

type_vsxm = [
    # Unit-stride Stores
    "vse8.v",
    "vse16.v",
    "vse32.v",
    "vse64.v",
    "vsseg2e8.v",
    "vsseg2e16.v",
    "vsseg2e32.v",
    "vsseg2e64.v",
    "vsseg3e8.v",
    "vsseg3e16.v",
    "vsseg3e32.v",
    "vsseg3e64.v",
    "vsseg4e8.v",
    "vsseg4e16.v",
    "vsseg4e32.v",
    "vsseg4e64.v",
    "vsseg5e8.v",
    "vsseg5e16.v",
    "vsseg5e32.v",
    "vsseg5e64.v",
    "vsseg6e8.v",
    "vsseg6e16.v",
    "vsseg6e32.v",
    "vsseg6e64.v",
    "vsseg7e8.v",
    "vsseg7e16.v",
    "vsseg7e32.v",
    "vsseg7e64.v",
    "vsseg8e8.v",
    "vsseg8e16.v",
    "vsseg8e32.v",
    "vsseg8e64.v",
]

type_vsxxm = [
    # Strided Stores
    "vsse8.v",
    "vsse16.v",
    "vsse32.v",
    "vsse64.v",
    "vssseg2e8.v",
    "vssseg2e16.v",
    "vssseg2e32.v",
    "vssseg2e64.v",
    "vssseg3e8.v",
    "vssseg3e16.v",
    "vssseg3e32.v",
    "vssseg3e64.v",
    "vssseg4e8.v",
    "vssseg4e16.v",
    "vssseg4e32.v",
    "vssseg4e64.v",
    "vssseg5e8.v",
    "vssseg5e16.v",
    "vssseg5e32.v",
    "vssseg5e64.v",
    "vssseg6e8.v",
    "vssseg6e16.v",
    "vssseg6e32.v",
    "vssseg6e64.v",
    "vssseg7e8.v",
    "vssseg7e16.v",
    "vssseg7e32.v",
    "vssseg7e64.v",
    "vssseg8e8.v",
    "vssseg8e16.v",
    "vssseg8e32.v",
    "vssseg8e64.v",
]

type_vsxvm = [
    # Indexed unordered Stores
    "vsuxei8.v",
    "vsuxei16.v",
    "vsuxei32.v",
    "vsuxei64.v",
    "vsuxseg2ei8.v",
    "vsuxseg2ei16.v",
    "vsuxseg2ei32.v",
    "vsuxseg2ei64.v",
    "vsuxseg3ei8.v",
    "vsuxseg3ei16.v",
    "vsuxseg3ei32.v",
    "vsuxseg3ei64.v",
    "vsuxseg4ei8.v",
    "vsuxseg4ei16.v",
    "vsuxseg4ei32.v",
    "vsuxseg4ei64.v",
    "vsuxseg5ei8.v",
    "vsuxseg5ei16.v",
    "vsuxseg5ei32.v",
    "vsuxseg5ei64.v",
    "vsuxseg6ei8.v",
    "vsuxseg6ei16.v",
    "vsuxseg6ei32.v",
    "vsuxseg6ei64.v",
    "vsuxseg7ei8.v",
    "vsuxseg7ei16.v",
    "vsuxseg7ei32.v",
    "vsuxseg7ei64.v",
    "vsuxseg8ei8.v",
    "vsuxseg8ei16.v",
    "vsuxseg8ei32.v",
    "vsuxseg8ei64.v",
    # Indexed ordered Stores
    "vsoxei8.v",
    "vsoxei16.v",
    "vsoxei32.v",
    "vsoxei64.v",
    "vsoxseg2ei8.v",
    "vsoxseg2ei16.v",
    "vsoxseg2ei32.v",
    "vsoxseg2ei64.v",
    "vsoxseg3ei8.v",
    "vsoxseg3ei16.v",
    "vsoxseg3ei32.v",
    "vsoxseg3ei64.v",
    "vsoxseg4ei8.v",
    "vsoxseg4ei16.v",
    "vsoxseg4ei32.v",
    "vsoxseg4ei64.v",
    "vsoxseg5ei8.v",
    "vsoxseg5ei16.v",
    "vsoxseg5ei32.v",
    "vsoxseg5ei64.v",
    "vsoxseg6ei8.v",
    "vsoxseg6ei16.v",
    "vsoxseg6ei32.v",
    "vsoxseg6ei64.v",
    "vsoxseg7ei8.v",
    "vsoxseg7ei16.v",
    "vsoxseg7ei32.v",
    "vsoxseg7ei64.v",
    "vsoxseg8ei8.v",
    "vsoxseg8ei16.v",
    "vsoxseg8ei32.v",
    "vsoxseg8ei64.v",
]

type_vx = [
    # Whole Register Loads
    "vl1re8.v",
    "vl2re8.v",
    "vl4re8.v",
    "vl8re8.v",
    "vl1re16.v",
    "vl2re16.v",
    "vl4re16.v",
    "vl8re16.v",
    "vl1re32.v",
    "vl2re32.v",
    "vl4re32.v",
    "vl8re32.v",
    "vl1re64.v",
    "vl2re64.v",
    "vl4re64.v",
    "vl8re64.v",
    # Mask Load
    "vlm.v",
]

type_vsx = [
    # Whole Register Stores
    "vs1r.v",
    "vs2r.v",
    "vs4r.v",
    "vs8r.v",
    # Mask Store
    "vsm.v",
]

################################## vector bit manipulation and crypto ##################################

vvvm_b_type = ["vandn.vv", "vrol.vv", "vror.vv", "vwsll.vv", "vclmul.vv", "vclmulh.vv"]
vvxm_b_type = ["vandn.vx", "vrol.vx", "vror.vx", "vwsll.vx", "vclmul.vx", "vclmulh.vx"]
vvim_b_type = ["vror.vi", "vwsll.vi"]
vvm_b_type = ["vbrev.v", "vbrev8.v", "vrev8.v", "vclz.v", "vctz.v", "vcpop.v"]
bwvvins = ["vwsll.vv", "vwsll.vx", "vwsll.vi"]
bimm_31 = ["vwsll.vi", "vror.vi"]

################################## vector floating point instruction ##################################

vvvm_f_type = [
    "vfadd.vv",
    "vfwadd.vv",
    "vfwadd.wv",
    "vfsub.vv",
    "vfwsub.vv",
    "vfwsub.wv",
    "vfmul.vv",
    "vfwmul.vv",
    "vfdiv.vv",
    "vfmin.vv",
    "vfmax.vv",
    "vfsgnj.vv",
    "vfsgnjn.vv",
    "vfsgnjx.vv",
    "vfredosum.vs",
    "vfwredosum.vs",
    "vfredusum.vs",
    "vfwredusum.vs",
    "vfredmax.vs",
    "vfredmin.vs",
    "vmfeq.vv",
    "vmfne.vv",
    "vmflt.vv",
    "vmfle.vv",
]
vvfmtype = [
    "vfadd.vf",
    "vfwadd.vf",
    "vfwadd.wf",
    "vfsub.vf",
    "vfwsub.vf",
    "vfwsub.wf",
    "vfrsub.vf",
    "vfmul.vf",
    "vfwmul.vf",
    "vfdiv.vf",
    "vfrdiv.vf",
    "vfmin.vf",
    "vfmax.vf",
    "vfsgnj.vf",
    "vfsgnjn.vf",
    "vfsgnjx.vf",
    "vmfeq.vf",
    "vmfne.vf",
    "vmflt.vf",
    "vmfle.vf",
    "vmfgt.vf",
    "vmfge.vf",
    "vfslide1up.vf",
    "vfslide1down.vf",
]
vvfvtype = ["vfmerge.vfm"]
vvvmr_f_type = [
    "vfmacc.vv",
    "vfnmacc.vv",
    "vfmsac.vv",
    "vfnmsac.vv",
    "vfmadd.vv",
    "vfnmadd.vv",
    "vfmsub.vv",
    "vfnmsub.vv",
    "vfwmacc.vv",
    "vfwnmacc.vv",
    "vfwmsac.vv",
    "vfwnmsac.vv",
    "vfwmaccbf16.vv",
]
vfvmtype = [
    "vfmacc.vf",
    "vfnmacc.vf",
    "vfmsac.vf",
    "vfnmsac.vf",
    "vfmadd.vf",
    "vfnmadd.vf",
    "vfmsub.vf",
    "vfnmsub.vf",
    "vfwmacc.vf",
    "vfwnmacc.vf",
    "vfwmsac.vf",
    "vfwnmsac.vf",
    "vfwmaccbf16.vf",
]
vvm_f_type = [
    "vfsqrt.v",
    "vfrsqrt7.v",
    "vfrec7.v",
    "vfcvt.xu.f.v",
    "vfwcvt.xu.f.v",
    "vfncvt.xu.f.w",
    "vfcvt.x.f.v",
    "vfwcvt.x.f.v",
    "vfncvt.x.f.w",
    "vfcvt.rtz.xu.f.v",
    "vfwcvt.rtz.xu.f.v",
    "vfncvt.rtz.xu.f.w",
    "vfcvt.rtz.x.f.v",
    "vfwcvt.rtz.x.f.v",
    "vfncvt.rtz.x.f.w",
    "vfcvt.f.xu.v",
    "vfwcvt.f.xu.v",
    "vfncvt.f.xu.w",
    "vfcvt.f.x.v",
    "vfwcvt.f.x.v",
    "vfncvt.f.x.w",
    "vfwcvt.f.f.v",
    "vfncvt.f.f.w",
    "vfncvt.rod.f.f.w",
    "vfclass.v",
    "vfwcvtbf16.f.f.v",
    "vfncvtbf16.f.f.w",
]
vftype = ["vfmv.v.f", "vfmv.s.f"]
fvtype = ["vfmv.f.s"]

vfloattypes = vvvm_f_type + vvfmtype + vvvmr_f_type + vfvmtype + vvm_f_type + vftype + fvtype + vvfvtype
vf_permutation_ins = ["vfmv.f.s", "vfmv.s.f", "vfslide1up.vf", "vfslide1down.vf"]

bf16_instructions = ["vfwmaccbf16.vv", "vfwmaccbf16.vf", "vfncvtbf16.f.f.w", "vfwcvtbf16.f.f.v"]

##################################    vector integer instruction     ##################################

vvvmtype = (
    [
        "vadd.vv",
        "vwadd.vv",
        "vwaddu.vv",
        "vsub.vv",
        "vwsub.vv",
        "vwsubu.vv",
        "vwadd.wv",
        "vwsub.wv",
        "vwaddu.wv",
        "vwsubu.wv",
        "vand.vv",
        "vor.vv",
        "vxor.vv",
        "vsll.vv",
        "vsrl.vv",
        "vsra.vv",
        "vnsra.wv",
        "vnsrl.wv",
        "vmseq.vv",
        "vmsne.vv",
        "vmslt.vv",
        "vmsltu.vv",
        "vmsle.vv",
        "vmsleu.vv",
        "vmin.vv",
        "vminu.vv",
        "vmax.vv",
        "vmaxu.vv",
        "vmul.vv",
        "vmulh.vv",
        "vmulhu.vv",
        "vmulhsu.vv",
        "vwmul.vv",
        "vwmulu.vv",
        "vwmulsu.vv",
        "vdiv.vv",
        "vdivu.vv",
        "vrem.vv",
        "vremu.vv",
        "vsadd.vv",
        "vsaddu.vv",
        "vssub.vv",
        "vssubu.vv",
        "vaadd.vv",
        "vaaddu.vv",
        "vasub.vv",
        "vasubu.vv",
        "vsmul.vv",
        "vssrl.vv",
        "vssra.vv",
        "vnclip.wv",
        "vnclipu.wv",
        "vredsum.vs",
        "vwredsum.vs",
        "vwredsumu.vs",
        "vredmax.vs",
        "vredmaxu.vs",
        "vredmin.vs",
        "vredminu.vs",
        "vredand.vs",
        "vredor.vs",
        "vredxor.vs",
        "vrgather.vv",
        "vrgatherei16.vv",
    ]
    + vvvm_f_type
    + vvvm_b_type
)

vvxmtype = [
    "vadd.vx",
    "vwadd.vx",
    "vwaddu.vx",
    "vsub.vx",
    "vwsub.vx",
    "vwsubu.vx",
    "vrsub.vx",
    "vwadd.wx",
    "vwsub.wx",
    "vwaddu.wx",
    "vwsubu.wx",
    "vmadc.vx",
    "vmsbc.vx",
    "vand.vx",
    "vor.vx",
    "vxor.vx",
    "vsll.vx",
    "vsrl.vx",
    "vsra.vx",
    "vnsra.wx",
    "vnsrl.wx",
    "vmseq.vx",
    "vmsne.vx",
    "vmslt.vx",
    "vmsltu.vx",
    "vmsle.vx",
    "vmsleu.vx",
    "vmsgt.vx",
    "vmsgtu.vx",
    "vmin.vx",
    "vminu.vx",
    "vmax.vx",
    "vmaxu.vx",
    "vmul.vx",
    "vmulh.vx",
    "vmulhu.vx",
    "vmulhsu.vx",
    "vwmul.vx",
    "vwmulu.vx",
    "vwmulsu.vx",
    "vdiv.vx",
    "vdivu.vx",
    "vrem.vx",
    "vremu.vx",
    "vsadd.vx",
    "vsaddu.vx",
    "vssub.vx",
    "vssubu.vx",
    "vaadd.vx",
    "vaaddu.vx",
    "vasub.vx",
    "vasubu.vx",
    "vsmul.vx",
    "vssrl.vx",
    "vssra.vx",
    "vnclip.wx",
    "vnclipu.wx",
    "vslideup.vx",
    "vslidedown.vx",
    "vslide1up.vx",
    "vslide1down.vx",
    "vrgather.vx",
] + vvxm_b_type

vvimtype = [
    "vadd.vi",
    "vrsub.vi",
    "vmadc.vi",
    "vand.vi",
    "vor.vi",
    "vxor.vi",
    "vsll.vi",
    "vsrl.vi",
    "vsra.vi",
    "vnsra.wi",
    "vnsrl.wi",
    "vmseq.vi",
    "vmsne.vi",
    "vmsle.vi",
    "vmsleu.vi",
    "vmsgt.vi",
    "vmsgtu.vi",
    "vsadd.vi",
    "vsaddu.vi",
    "vssrl.vi",
    "vssra.vi",
    "vnclip.wi",
    "vnclipu.wi",
    "vslideup.vi",
    "vslidedown.vi",
    "vrgather.vi",
] + vvim_b_type

xvmtype = ["vcpop.m", "vfirst.m"]

vvvmrtype = ["vmacc.vv", "vnmsac.vv", "vmadd.vv", "vnmsub.vv", "vwmacc.vv", "vwmaccu.vv", "vwmaccsu.vv"] + vvvmr_f_type
vvmtype = (
    [
        "vmsbf.m",
        "viota.m",
        "vmsif.m",
        "vmsof.m",
        "vzext.vf2",
        "vzext.vf4",
        "vzext.vf8",
        "vsext.vf2",
        "vsext.vf4",
        "vsext.vf8",
    ]
    + vvm_f_type
    + vvm_b_type
)
vxvmtype = ["vmacc.vx", "vnmsac.vx", "vmadd.vx", "vnmsub.vx", "vwmacc.vx", "vwmaccu.vx", "vwmaccsu.vx", "vwmaccus.vx"]
vvrtype = ["vmv.v.v"]
vxtype = ["vmv.s.x", "vmv.v.x"]
vitype = ["vmv.v.i"]
xvtype = ["vmv.x.s"]
vvvxtype = ["vmv1r.v", "vmv2r.v", "vmv4r.v", "vmv8r.v"]
vmtype = ["vid.v"]
vvivtype = ["vadc.vim", "vmerge.vim", "vmadc.vim"]
vvvvtype = ["vadc.vvm", "vsbc.vvm", "vmerge.vvm", "vmadc.vvm", "vmsbc.vvm"]
vvxvtype = ["vadc.vxm", "vsbc.vxm", "vmerge.vxm", "vmadc.vxm", "vmsbc.vxm"]
vvvtype = [
    "vmadc.vv",
    "vmsbc.vv",
    "vmand.mm",
    "vmnand.mm",
    "vmandn.mm",
    "vmxor.mm",
    "vmor.mm",
    "vmnor.mm",
    "vmorn.mm",
    "vmxnor.mm",
    "vcompress.vm",
]
imm_31 = [
    "vnclip.wi",
    "vnclipu.wi",
    "vnsra.wi",
    "vnsrl.wi",
    "vrgather.vi",
    "vslidedown.vi",
    "vslideup.vi",
    "vsll.vi",
    "vsra.vi",
    "vsrl.vi",
    "vssra.vi",
    "vssrl.vi",
] + bimm_31

##################################    vector crypto instructions     ##################################
crypto_vv = [
    "vgmul.vv",
    "vaesef.vv",
    "vaesef.vs",
    "vaesem.vv",
    "vaesem.vs",
    "vaesdf.vv",
    "vaesdf.vs",
    "vaesdm.vv",
    "vaesdm.vs",
    "vaesz.vs",
    "vsm4r.vv",
    "vsm4r.vs",
]
crypto_vvv = ["vghsh.vv", "vsha2ms.vv", "vsha2ch.vv", "vsha2cl.vv", "vsm3me.vv"]
crypto_vvi = ["vaeskf1.vi", "vaeskf2.vi", "vsm4k.vi", "vsm3c.vi"]
crypto_imm_31 = ["vsm3c.vi", "vaeskf1.vi", "vaeskf2.vi", "vsm4k.vi"]

vvvtype += crypto_vvv
vvtype = crypto_vv
vvimtype += crypto_vvi
imm_31 += crypto_imm_31

crypto_ins = crypto_vv + crypto_vvv + crypto_vvi
crypto_egs8 = ["vsm3me.vv", "vsm3c.vi"]

crypto_no_vd_vs2 = ["vaesef.vs", "vaesem.vs", "vaesdf.vs", "vaesdm.vs", "vaesz.vs", "vsm4r.vs", "vsm3me.vv", "vsm3c.vi"]
crypto_no_vd_vs2_vs1 = ["vsha2ms.vv", "vsha2ch.vv", "vsha2cl.vv"]

crypto_aes_subbytes_ins = [
    "vaesef.vv",
    "vaesef.vs",
    "vaesem.vv",
    "vaesem.vs",
    "vaesdf.vv",
    "vaesdf.vs",
    "vaesdm.vv",
    "vaesdm.vs",
    "vaeskf1.vi",
    "vaeskf2.vi",
]
crypto_sm_subbytes_ins = ["vsm4k.vi", "vsm4r.vv", "vsm4r.vs"]

vs1ins = vvvmtype + vvrtype + vvvvtype + vvvtype + vvvmrtype

##################################     vector instruction groups     ##################################

# vector instruction groups by EEW (prefix + suffix)
# normal
fvvins = [
    "vfadd.vv",
    "vfsub.vv",
    "vfmul.vv",
    "vfdiv.vv",
    "vfmin.vv",
    "vfmax.vv",
    "vfmacc.vv",
    "vfnmacc.vv",
    "vfmsac.vv",
    "vfnmsac.vv",
    "vfmadd.vv",
    "vfnmadd.vv",
    "vfmsub.vv",
    "vfnmsub.vv",
    "vfsgnj.vv",
    "vfsgnjn.vv",
    "vfsgnjx.vv",
]
fvfins = [
    "vfadd.vf",
    "vfsub.vf",
    "vfrsub.vf",
    "vfmul.vf",
    "vfdiv.vf",
    "vfrdiv.vf",
    "vfmin.vf",
    "vfmax.vf",
    "vfmacc.vf",
    "vfnmacc.vf",
    "vfmsac.vf",
    "vfnmsac.vf",
    "vfmadd.vf",
    "vfnmadd.vf",
    "vfmsub.vf",
    "vfnmsub.vf",
    "vfsgnj.vf",
    "vfsgnjn.vf",
    "vfsgnjx.vf",
]
vvins = [
    "vadd.vv",
    "vsub.vv",
    "vand.vv",
    "vor.vv",
    "vxor.vv",
    "vsll.vv",
    "vsrl.vv",
    "vsra.vv",
    "vmin.vv",
    "vminu.vv",
    "vmax.vv",
    "vmaxu.vv",
    "vmul.vv",
    "vmulh.vv",
    "vmulhu.vv",
    "vmulhsu.vv",
    "vdiv.vv",
    "vdivu.vv",
    "vrem.vv",
    "vremu.vv",
    "vsadd.vv",
    "vsaddu.vv",
    "vssub.vv",
    "vssubu.vv",
    "vaadd.vv",
    "vaaddu.vv",
    "vasub.vv",
    "vasubu.vv",
    "vsmul.vv",
    "vssrl.vv",
    "vssra.vv",
] + fvvins
vxins = [
    "vadd.vx",
    "vsub.vx",
    "vrsub.vx",
    "vand.vx",
    "vor.vx",
    "vxor.vx",
    "vsll.vx",
    "vsrl.vx",
    "vsra.vx",
    "vmin.vx",
    "vminu.vx",
    "vmax.vx",
    "vmaxu.vx",
    "vmul.vx",
    "vmulh.vx",
    "vmulhu.vx",
    "vmulhsu.vx",
    "vdiv.vx",
    "vdivu.vx",
    "vrem.vx",
    "vremu.vx",
    "vsadd.vx",
    "vsaddu.vx",
    "vssub.vx",
    "vssubu.vx",
    "vaadd.vx",
    "vaaddu.vx",
    "vasub.vx",
    "vasubu.vx",
    "vsmul.vx",
    "vssrl.vx",
    "vssra.vx",
]
viins = [
    "vadd.vi",
    "vrsub.vi",
    "vand.vi",
    "vor.vi",
    "vxor.vi",
    "vsll.vi",
    "vsrl.vi",
    "vsra.vi",
    "vsadd.vi",
    "vsaddu.vi",
    "vssrl.vi",
    "vssra.vi",
]
# narrowing
wvins = ["vnsrl.wv", "vnsra.wv", "vnclip.wv", "vnclipu.wv"]
wxins = ["vnsrl.wx", "vnsra.wx", "vnclip.wx", "vnclipu.wx"]
wiins = ["vnsrl.wi", "vnsra.wi", "vnclip.wi", "vnclipu.wi"]
fcvt_w_ins = [
    "vfncvt.xu.f.w",
    "vfncvt.x.f.w",
    "vfncvt.rtz.xu.f.w",
    "vfncvt.rtz.x.f.w",
    "vfncvt.f.xu.w",
    "vfncvt.f.x.w",
    "vfncvt.f.f.w",
    "vfncvt.rod.f.f.w",
    "vfncvtbf16.f.f.w",
]
narrowins = wvins + wxins + wiins + fcvt_w_ins
# widening
fwvvins = [
    "vfwadd.vv",
    "vfwsub.vv",
    "vfwmul.vv",
    "vfwmacc.vv",
    "vfwnmacc.vv",
    "vfwmsac.vv",
    "vfwnmsac.vv",
    "vfwmaccbf16.vv",
]
fwvfins = [
    "vfwadd.vf",
    "vfwsub.vf",
    "vfwmul.vf",
    "vfwmacc.vf",
    "vfwnmacc.vf",
    "vfwmsac.vf",
    "vfwnmsac.vf",
    "vfwmaccbf16.vf",
]
fwwvins = ["vfwadd.wv", "vfwsub.wv"]
fwwfins = ["vfwadd.wf", "vfwsub.wf"]
wvvins = (
    [
        "vwadd.vv",
        "vwaddu.vv",
        "vwsub.vv",
        "vwsubu.vv",
        "vwmul.vv",
        "vwmulu.vv",
        "vwmulsu.vv",
        "vwmacc.vv",
        "vwmaccu.vv",
        "vwmaccsu.vv",
    ]
    + fwvvins
    + bwvvins
)
wvxins = [
    "vwadd.vx",
    "vwaddu.vx",
    "vwsub.vx",
    "vwsubu.vx",
    "vwmul.vx",
    "vwmulu.vx",
    "vwmulsu.vx",
    "vwmacc.vx",
    "vwmaccu.vx",
    "vwmaccsu.vx",
    "vwmaccus.vx",
]
wwvins = ["vwadd.wv", "vwaddu.wv", "vwsub.wv", "vwsubu.wv"] + fwwvins
wwxins = ["vwadd.wx", "vwaddu.wx", "vwsub.wx", "vwsubu.wx"]
fwcvt_ins = [
    "vfwcvt.xu.f.v",
    "vfwcvt.x.f.v",
    "vfwcvt.rtz.xu.f.v",
    "vfwcvt.rtz.x.f.v",
    "vfwcvt.f.xu.v",
    "vfwcvt.f.x.v",
    "vfwcvt.f.f.v",
    "vfwcvtbf16.f.f.v",
]
vs2_widen_ins = narrowins + wwvins + wwxins + fwwfins
# masking
vvmins = ["vadc.vvm", "vsbc.vvm", "vmerge.vvm"]
vxmins = ["vadc.vxm", "vsbc.vxm", "vmerge.vxm"]
vimins = ["vadc.vim", "vmerge.vim"]
fvfmins = ["vfmerge.vfm"]
fmvvins = ["vmfeq.vv", "vmfne.vv", "vmflt.vv", "vmfle.vv"]  # can be masked
fmvfins = ["vmfeq.vf", "vmfne.vf", "vmflt.vf", "vmfle.vf", "vmfgt.vf", "vmfge.vf"]  # can be masked
vm_nomask_ins = ["vmadc.vv", "vmsbc.vv", "vmadc.vx", "vmsbc.vx", "vmadc.vi"]
mvvins = ["vmseq.vv", "vmsne.vv", "vmslt.vv", "vmsltu.vv", "vmsle.vv", "vmsleu.vv"]
mvxins = ["vmseq.vx", "vmsne.vx", "vmslt.vx", "vmsltu.vx", "vmsle.vx", "vmsleu.vx", "vmsgt.vx", "vmsgtu.vx"]
mviins = ["vmseq.vi", "vmsne.vi", "vmsle.vi", "vmsleu.vi", "vmsgt.vi", "vmsgtu.vi"]
mvvmins = ["vmadc.vvm", "vmsbc.vvm"]
mvxmins = ["vmadc.vxm", "vmsbc.vxm"]
mvimins = ["vmadc.vim"]
mmins = ["vmand.mm", "vmnand.mm", "vmandn.mm", "vmxor.mm", "vmor.mm", "vmnor.mm", "vmorn.mm", "vmxnor.mm"]
maskins = vm_nomask_ins + mvvins + mvxins + mviins + mvvmins + mvxmins + mvimins + fmvvins + fmvfins
v_mins = vvmins + vxmins + vimins + fvfmins
mv_ins = vm_nomask_ins + mvvins + mvxins + mviins
mv_mins = mvvmins + mvxmins + mvimins
# extending
vextins = ["vzext.vf2", "vzext.vf4", "vzext.vf8", "vsext.vf2", "vsext.vf4", "vsext.vf8"]
# widening reduction
fwvsins = ["vfwredosum.vs", "vfwredusum.vs"]
wvsins = ["vwredsum.vs", "vwredsumu.vs"] + fwvsins
# slide/gather/compress
vfslideupins = ["vfslide1up.vf"]
vslideupins = ["vslideup.vx", "vslideup.vi", "vslide1up.vx"] + vfslideupins
vfslidedownins = ["vfslide1down.vf"]
vslidedownins = ["vslidedown.vx", "vslidedown.vi", "vslide1down.vx"] + vfslidedownins
vrgatherins = ["vrgather.vv", "vrgather.vx", "vrgather.vi", "vrgatherei16.vv"]
vcompressins = ["vcompress.vm"]
vupgatherins = vslideupins + vrgatherins
# mask logical
vmlogicalins = ["vmsbf.m", "vmsif.m", "vmsof.m"]
viotains = ["viota.m"]
vfredins = ["vfredosum.vs", "vfwredosum.vs", "vfredusum.vs", "vfwredusum.vs", "vfredmax.vs", "vfredmin.vs"]
vredins = [
    "vredsum.vs",
    "vwredsumu.vs",
    "vwredsum.vs",
    "vredmaxu.vs",
    "vredmax.vs",
    "vredminu.vs",
    "vredmin.vs",
    "vredand.vs",
    "vredor.vs",
    "vredxor.vs",
] + vfredins
mask_ls_ins = ["vlm.v", "vsm.v"]
maskprodins = mmins + vmlogicalins + maskins + mask_ls_ins
maskopins = mmins + vmlogicalins + viotains  # instructions that take mask operands

ls_not_maskable = [
    "vl1re8.v",
    "vl2re8.v",
    "vl4re8.v",
    "vl8re8.v",
    "vl1re16.v",
    "vl2re16.v",
    "vl4re16.v",
    "vl8re16.v",
    "vl1re32.v",
    "vl2re32.v",
    "vl4re32.v",
    "vl8re32.v",
    "vl1re64.v",
    "vl2re64.v",
    "vl4re64.v",
    "vl8re64.v",
    "vs1r.v",
    "vs2r.v",
    "vs4r.v",
    "vs8r.v",
    "vsm.v",
    "vlm.v",
]

vmvins = vvrtype + vxtype + vitype + xvtype + vftype + fvtype + vvvxtype + vcompressins
vd_widen_ins = wvvins + wvxins + wwvins + wwxins + wvsins + fwvfins + fwwfins + fwcvt_ins
# Widening multiply-accumulate instructions: vd is both destination (EEW=2*SEW) AND a source
# operand (the accumulator, also read at EEW=2*SEW). Because vs1/vs2 are read at EEW=SEW, any
# overlap between vd and vs1/vs2 would cause the same vector register to be read at two different
# EEWs, which is reserved per V spec section 5.2 (norm:eew_emul). The standard widening
# "lowest-numbered-part" overlap exception does NOT apply here, because vd is also read (not
# just written). Therefore vd must have NO overlap with vs1/vs2 for these instructions.
widening_mac_ins = [
    "vwmacc.vv",
    "vwmaccu.vv",
    "vwmaccsu.vv",
    "vwmacc.vx",
    "vwmaccu.vx",
    "vwmaccsu.vx",
    "vwmaccus.vx",
    "vfwmacc.vv",
    "vfwnmacc.vv",
    "vfwmsac.vv",
    "vfwnmsac.vv",
    "vfwmacc.vf",
    "vfwnmacc.vf",
    "vfwmsac.vf",
    "vfwnmsac.vf",
    "vfwmaccbf16.vv",
    "vfwmaccbf16.vf",
]
not_maskable = vm_nomask_ins + mmins + vmvins + ls_not_maskable + crypto_ins

# "vl1re8.v", "vl1re16.v", "vl1re32.v", "vl1re64.v"
# "vs1r.v",

whole_register_move = ["vmv1r.v", "vmv2r.v", "vmv4r.v", "vmv8r.v"]
whole_register_stores = ["vs1r.v", "vs2r.v", "vs4r.v", "vs8r.v"]

# Instructions that require vstart=0; non-zero vstart is reserved and traps
# illegal-instruction. cp_vstart sets vstart != 0, so these always trap.
vstart_zero_required = [
    # scalar-move instructions
    "vmv.x.s",
    "vmv.s.x",
    "vfmv.f.s",
    "vfmv.s.f",
    # integer reductions
    "vredsum.vs",
    "vredand.vs",
    "vredor.vs",
    "vredxor.vs",
    "vredminu.vs",
    "vredmin.vs",
    "vredmaxu.vs",
    "vredmax.vs",
    "vwredsumu.vs",
    "vwredsum.vs",
    # FP reductions
    "vfredosum.vs",
    "vfredusum.vs",
    "vfredmax.vs",
    "vfredmin.vs",
    "vfwredosum.vs",
    "vfwredusum.vs",
    # mask population/find-first
    "vcpop.m",
    "vfirst.m",
    # mask set-before/including/only-first
    "vmsbf.m",
    "vmsif.m",
    "vmsof.m",
    # iota / id
    "viota.m",
    "vid.v",
    # compress
    "vcompress.vm",
]

strided_loads = [
    "vlse8.v",
    "vlse16.v",
    "vlse32.v",
    "vlse64.v",
    "vlsseg2e8.v",
    "vlsseg2e16.v",
    "vlsseg2e32.v",
    "vlsseg2e64.v",
    "vlsseg3e8.v",
    "vlsseg3e16.v",
    "vlsseg3e32.v",
    "vlsseg3e64.v",
    "vlsseg4e8.v",
    "vlsseg4e16.v",
    "vlsseg4e32.v",
    "vlsseg4e64.v",
    "vlsseg5e8.v",
    "vlsseg5e16.v",
    "vlsseg5e32.v",
    "vlsseg5e64.v",
    "vlsseg6e8.v",
    "vlsseg6e16.v",
    "vlsseg6e32.v",
    "vlsseg6e64.v",
    "vlsseg7e8.v",
    "vlsseg7e16.v",
    "vlsseg7e32.v",
    "vlsseg7e64.v",
    "vlsseg8e8.v",
    "vlsseg8e16.v",
    "vlsseg8e32.v",
    "vlsseg8e64.v",
]

strided_stores = [
    "vsse8.v",
    "vsse16.v",
    "vsse32.v",
    "vsse64.v",
    "vssseg2e8.v",
    "vssseg2e16.v",
    "vssseg2e32.v",
    "vssseg2e64.v",
    "vssseg3e8.v",
    "vssseg3e16.v",
    "vssseg3e32.v",
    "vssseg3e64.v",
    "vssseg4e8.v",
    "vssseg4e16.v",
    "vssseg4e32.v",
    "vssseg4e64.v",
    "vssseg5e8.v",
    "vssseg5e16.v",
    "vssseg5e32.v",
    "vssseg5e64.v",
    "vssseg6e8.v",
    "vssseg6e16.v",
    "vssseg6e32.v",
    "vssseg6e64.v",
    "vssseg7e8.v",
    "vssseg7e16.v",
    "vssseg7e32.v",
    "vssseg7e64.v",
    "vssseg8e8.v",
    "vssseg8e16.v",
    "vssseg8e32.v",
    "vssseg8e64.v",
]

# ─── Segment length 2 ──────────────────────────────────────────────

seg2_loads = [
    "vloxseg2ei8.v",
    "vlseg2e8.v",
    "vlseg2e8ff.v",
    "vlsseg2e8.v",
    "vluxseg2ei8.v",
    "vloxseg2ei16.v",
    "vlseg2e16.v",
    "vlseg2e16ff.v",
    "vlsseg2e16.v",
    "vluxseg2ei16.v",
    "vloxseg2ei32.v",
    "vlseg2e32.v",
    "vlseg2e32ff.v",
    "vlsseg2e32.v",
    "vluxseg2ei32.v",
    "vloxseg2ei64.v",
    "vlseg2e64.v",
    "vlseg2e64ff.v",
    "vlsseg2e64.v",
    "vluxseg2ei64.v",
    "vl2re8.v",
    "vl2re16.v",
    "vl2re32.v",
    "vl2re64.v",
]

seg2_stores = [
    "vsoxseg2ei8.v",
    "vsseg2e8.v",
    "vssseg2e8.v",
    "vsuxseg2ei8.v",
    "vsoxseg2ei16.v",
    "vsseg2e16.v",
    "vssseg2e16.v",
    "vsuxseg2ei16.v",
    "vsoxseg2ei32.v",
    "vsseg2e32.v",
    "vssseg2e32.v",
    "vsuxseg2ei32.v",
    "vsoxseg2ei64.v",
    "vsseg2e64.v",
    "vssseg2e64.v",
    "vsuxseg2ei64.v",
    "vs2r.v",
]

seg2 = seg2_stores + seg2_loads

# ─── Segment length 3 ──────────────────────────────────────────────

seg3_loads = [
    "vloxseg3ei8.v",
    "vlseg3e8.v",
    "vlseg3e8ff.v",
    "vlsseg3e8.v",
    "vluxseg3ei8.v",
    "vloxseg3ei16.v",
    "vlseg3e16.v",
    "vlseg3e16ff.v",
    "vlsseg3e16.v",
    "vluxseg3ei16.v",
    "vloxseg3ei32.v",
    "vlseg3e32.v",
    "vlseg3e32ff.v",
    "vlsseg3e32.v",
    "vluxseg3ei32.v",
    "vloxseg3ei64.v",
    "vlseg3e64.v",
    "vlseg3e64ff.v",
    "vlsseg3e64.v",
    "vluxseg3ei64.v",
]

seg3_stores = [
    "vsoxseg3ei8.v",
    "vsseg3e8.v",
    "vssseg3e8.v",
    "vsuxseg3ei8.v",
    "vsoxseg3ei16.v",
    "vsseg3e16.v",
    "vssseg3e16.v",
    "vsuxseg3ei16.v",
    "vsoxseg3ei32.v",
    "vsseg3e32.v",
    "vssseg3e32.v",
    "vsuxseg3ei32.v",
    "vsoxseg3ei64.v",
    "vsseg3e64.v",
    "vssseg3e64.v",
    "vsuxseg3ei64.v",
]

seg3 = seg3_stores + seg3_loads

# ─── Segment length 4 ──────────────────────────────────────────────

seg4_loads = [
    "vloxseg4ei8.v",
    "vlseg4e8.v",
    "vlseg4e8ff.v",
    "vlsseg4e8.v",
    "vluxseg4ei8.v",
    "vloxseg4ei16.v",
    "vlseg4e16.v",
    "vlseg4e16ff.v",
    "vlsseg4e16.v",
    "vluxseg4ei16.v",
    "vloxseg4ei32.v",
    "vlseg4e32.v",
    "vlseg4e32ff.v",
    "vlsseg4e32.v",
    "vluxseg4ei32.v",
    "vloxseg4ei64.v",
    "vlseg4e64.v",
    "vlseg4e64ff.v",
    "vlsseg4e64.v",
    "vluxseg4ei64.v",
    "vl4re8.v",
    "vl4re16.v",
    "vl4re32.v",
    "vl4re64.v",
]

seg4_stores = [
    "vsoxseg4ei8.v",
    "vsseg4e8.v",
    "vssseg4e8.v",
    "vsuxseg4ei8.v",
    "vsoxseg4ei16.v",
    "vsseg4e16.v",
    "vssseg4e16.v",
    "vsuxseg4ei16.v",
    "vsoxseg4ei32.v",
    "vsseg4e32.v",
    "vssseg4e32.v",
    "vsuxseg4ei32.v",
    "vsoxseg4ei64.v",
    "vsseg4e64.v",
    "vssseg4e64.v",
    "vsuxseg4ei64.v",
    "vs4r.v",
]

seg4 = seg4_stores + seg4_loads

# ─── Segment length 5 ──────────────────────────────────────────────
seg5_loads = [
    "vloxseg5ei8.v",
    "vlseg5e8.v",
    "vlseg5e8ff.v",
    "vlsseg5e8.v",
    "vluxseg5ei8.v",
    "vloxseg5ei16.v",
    "vlseg5e16.v",
    "vlseg5e16ff.v",
    "vlsseg5e16.v",
    "vluxseg5ei16.v",
    "vloxseg5ei32.v",
    "vlseg5e32.v",
    "vlseg5e32ff.v",
    "vlsseg5e32.v",
    "vluxseg5ei32.v",
    "vloxseg5ei64.v",
    "vlseg5e64.v",
    "vlseg5e64ff.v",
    "vlsseg5e64.v",
    "vluxseg5ei64.v",
]

seg5_stores = [
    "vsoxseg5ei8.v",
    "vsseg5e8.v",
    "vssseg5e8.v",
    "vsuxseg5ei8.v",
    "vsoxseg5ei16.v",
    "vsseg5e16.v",
    "vssseg5e16.v",
    "vsuxseg5ei16.v",
    "vsoxseg5ei32.v",
    "vsseg5e32.v",
    "vssseg5e32.v",
    "vsuxseg5ei32.v",
    "vsoxseg5ei64.v",
    "vsseg5e64.v",
    "vssseg5e64.v",
    "vsuxseg5ei64.v",
]

seg5 = seg5_stores + seg5_loads

# ─── Segment length 6 ──────────────────────────────────────────────
seg6_loads = [
    "vloxseg6ei8.v",
    "vlseg6e8.v",
    "vlseg6e8ff.v",
    "vlsseg6e8.v",
    "vluxseg6ei8.v",
    "vloxseg6ei16.v",
    "vlseg6e16.v",
    "vlseg6e16ff.v",
    "vlsseg6e16.v",
    "vluxseg6ei16.v",
    "vloxseg6ei32.v",
    "vlseg6e32.v",
    "vlseg6e32ff.v",
    "vlsseg6e32.v",
    "vluxseg6ei32.v",
    "vloxseg6ei64.v",
    "vlseg6e64.v",
    "vlseg6e64ff.v",
    "vlsseg6e64.v",
    "vluxseg6ei64.v",
]

seg6_stores = [
    "vsoxseg6ei8.v",
    "vsseg6e8.v",
    "vssseg6e8.v",
    "vsuxseg6ei8.v",
    "vsoxseg6ei16.v",
    "vsseg6e16.v",
    "vssseg6e16.v",
    "vsuxseg6ei16.v",
    "vsoxseg6ei32.v",
    "vsseg6e32.v",
    "vssseg6e32.v",
    "vsuxseg6ei32.v",
    "vsoxseg6ei64.v",
    "vsseg6e64.v",
    "vssseg6e64.v",
    "vsuxseg6ei64.v",
]

seg6 = seg6_stores + seg6_loads

# ─── Segment length 7 ──────────────────────────────────────────────
seg7_loads = [
    "vloxseg7ei8.v",
    "vlseg7e8.v",
    "vlseg7e8ff.v",
    "vlsseg7e8.v",
    "vluxseg7ei8.v",
    "vloxseg7ei16.v",
    "vlseg7e16.v",
    "vlseg7e16ff.v",
    "vlsseg7e16.v",
    "vluxseg7ei16.v",
    "vloxseg7ei32.v",
    "vlseg7e32.v",
    "vlseg7e32ff.v",
    "vlsseg7e32.v",
    "vluxseg7ei32.v",
    "vloxseg7ei64.v",
    "vlseg7e64.v",
    "vlseg7e64ff.v",
    "vlsseg7e64.v",
    "vluxseg7ei64.v",
]

seg7_stores = [
    "vsoxseg7ei8.v",
    "vsseg7e8.v",
    "vssseg7e8.v",
    "vsuxseg7ei8.v",
    "vsoxseg7ei16.v",
    "vsseg7e16.v",
    "vssseg7e16.v",
    "vsuxseg7ei16.v",
    "vsoxseg7ei32.v",
    "vsseg7e32.v",
    "vssseg7e32.v",
    "vsuxseg7ei32.v",
    "vsoxseg7ei64.v",
    "vsseg7e64.v",
    "vssseg7e64.v",
    "vsuxseg7ei64.v",
]

seg7 = seg7_stores + seg7_loads

# ─── Segment length 8 ──────────────────────────────────────────────
seg8_loads = [
    "vloxseg8ei8.v",
    "vlseg8e8.v",
    "vlseg8e8ff.v",
    "vlsseg8e8.v",
    "vluxseg8ei8.v",
    "vloxseg8ei16.v",
    "vlseg8e16.v",
    "vlseg8e16ff.v",
    "vlsseg8e16.v",
    "vluxseg8ei16.v",
    "vloxseg8ei32.v",
    "vlseg8e32.v",
    "vlseg8e32ff.v",
    "vlsseg8e32.v",
    "vluxseg8ei32.v",
    "vloxseg8ei64.v",
    "vlseg8e64.v",
    "vlseg8e64ff.v",
    "vlsseg8e64.v",
    "vluxseg8ei64.v",
    "vl8re8.v",
    "vl8re16.v",
    "vl8re32.v",
    "vl8re64.v",
]

seg8_stores = [
    "vsoxseg8ei8.v",
    "vsseg8e8.v",
    "vssseg8e8.v",
    "vsuxseg8ei8.v",
    "vsoxseg8ei16.v",
    "vsseg8e16.v",
    "vssseg8e16.v",
    "vsuxseg8ei16.v",
    "vsoxseg8ei32.v",
    "vsseg8e32.v",
    "vssseg8e32.v",
    "vsuxseg8ei32.v",
    "vsoxseg8ei64.v",
    "vsseg8e64.v",
    "vssseg8e64.v",
    "vsuxseg8ei64.v",
    "vs8r.v",
]

seg8 = seg8_stores + seg8_loads

whole_register_ls = [
    "vl1re8.v",
    "vl2re8.v",
    "vl4re8.v",
    "vl8re8.v",
    "vl1re16.v",
    "vl2re16.v",
    "vl4re16.v",
    "vl8re16.v",
    "vl1re32.v",
    "vl2re32.v",
    "vl4re32.v",
    "vl8re32.v",
    "vl1re64.v",
    "vl2re64.v",
    "vl4re64.v",
    "vl8re64.v",
    "vs1r.v",
    "vs2r.v",
    "vs4r.v",
    "vs8r.v",
]

eew8_ins = [
    "vle8.v",
    "vlseg2e8.v",
    "vlseg3e8.v",
    "vlseg4e8.v",
    "vlseg5e8.v",
    "vlseg6e8.v",
    "vlseg7e8.v",
    "vlseg8e8.v",
    "vle8ff.v",
    "vlseg2e8ff.v",
    "vlseg3e8ff.v",
    "vlseg4e8ff.v",
    "vlseg5e8ff.v",
    "vlseg6e8ff.v",
    "vlseg7e8ff.v",
    "vlseg8e8ff.v",
    "vlse8.v",
    "vlsseg2e8.v",
    "vlsseg3e8.v",
    "vlsseg4e8.v",
    "vlsseg5e8.v",
    "vlsseg6e8.v",
    "vlsseg7e8.v",
    "vlsseg8e8.v",
    "vluxei8.v",
    "vluxseg2ei8.v",
    "vluxseg3ei8.v",
    "vluxseg4ei8.v",
    "vluxseg5ei8.v",
    "vluxseg6ei8.v",
    "vluxseg7ei8.v",
    "vluxseg8ei8.v",
    "vloxei8.v",
    "vloxseg2ei8.v",
    "vloxseg3ei8.v",
    "vloxseg4ei8.v",
    "vloxseg5ei8.v",
    "vloxseg6ei8.v",
    "vloxseg7ei8.v",
    "vloxseg8ei8.v",
    "vse8.v",
    "vsseg2e8.v",
    "vsseg3e8.v",
    "vsseg4e8.v",
    "vsseg5e8.v",
    "vsseg6e8.v",
    "vsseg7e8.v",
    "vsseg8e8.v",
    "vsse8.v",
    "vssseg2e8.v",
    "vssseg3e8.v",
    "vssseg4e8.v",
    "vssseg5e8.v",
    "vssseg6e8.v",
    "vssseg7e8.v",
    "vssseg8e8.v",
    "vsuxei8.v",
    "vsuxseg2ei8.v",
    "vsuxseg3ei8.v",
    "vsuxseg4ei8.v",
    "vsuxseg5ei8.v",
    "vsuxseg6ei8.v",
    "vsuxseg7ei8.v",
    "vsuxseg8ei8.v",
    "vsoxei8.v",
    "vsoxseg2ei8.v",
    "vsoxseg3ei8.v",
    "vsoxseg4ei8.v",
    "vsoxseg5ei8.v",
    "vsoxseg6ei8.v",
    "vsoxseg7ei8.v",
    "vsoxseg8ei8.v",
    "vl1re8.v",
    "vl2re8.v",
    "vl4re8.v",
    "vl8re8.v",
    "vs8r.v",
]

eew16_ins = [
    "vle16.v",
    "vlseg2e16.v",
    "vlseg3e16.v",
    "vlseg4e16.v",
    "vlseg5e16.v",
    "vlseg6e16.v",
    "vlseg7e16.v",
    "vlseg8e16.v",
    "vle16ff.v",
    "vlseg2e16ff.v",
    "vlseg3e16ff.v",
    "vlseg4e16ff.v",
    "vlseg5e16ff.v",
    "vlseg6e16ff.v",
    "vlseg7e16ff.v",
    "vlseg8e16ff.v",
    "vlse16.v",
    "vlsseg2e16.v",
    "vlsseg3e16.v",
    "vlsseg4e16.v",
    "vlsseg5e16.v",
    "vlsseg6e16.v",
    "vlsseg7e16.v",
    "vlsseg8e16.v",
    "vluxei16.v",
    "vluxseg2ei16.v",
    "vluxseg3ei16.v",
    "vluxseg4ei16.v",
    "vluxseg5ei16.v",
    "vluxseg6ei16.v",
    "vluxseg7ei16.v",
    "vluxseg8ei16.v",
    "vloxei16.v",
    "vloxseg2ei16.v",
    "vloxseg3ei16.v",
    "vloxseg4ei16.v",
    "vloxseg5ei16.v",
    "vloxseg6ei16.v",
    "vloxseg7ei16.v",
    "vloxseg8ei16.v",
    "vse16.v",
    "vsseg2e16.v",
    "vsseg3e16.v",
    "vsseg4e16.v",
    "vsseg5e16.v",
    "vsseg6e16.v",
    "vsseg7e16.v",
    "vsseg8e16.v",
    "vsse16.v",
    "vssseg2e16.v",
    "vssseg3e16.v",
    "vssseg4e16.v",
    "vssseg5e16.v",
    "vssseg6e16.v",
    "vssseg7e16.v",
    "vssseg8e16.v",
    "vsuxei16.v",
    "vsuxseg2ei16.v",
    "vsuxseg3ei16.v",
    "vsuxseg4ei16.v",
    "vsuxseg5ei16.v",
    "vsuxseg6ei16.v",
    "vsuxseg7ei16.v",
    "vsuxseg8ei16.v",
    "vsoxei16.v",
    "vsoxseg2ei16.v",
    "vsoxseg3ei16.v",
    "vsoxseg4ei16.v",
    "vsoxseg5ei16.v",
    "vsoxseg6ei16.v",
    "vsoxseg7ei16.v",
    "vsoxseg8ei16.v",
    "vl1re16.v",
    "vl2re16.v",
    "vl4re16.v",
    "vl8re16.v",
]

eew32_ins = [
    "vle32.v",
    "vlseg2e32.v",
    "vlseg3e32.v",
    "vlseg4e32.v",
    "vlseg5e32.v",
    "vlseg6e32.v",
    "vlseg7e32.v",
    "vlseg8e32.v",
    "vle32ff.v",
    "vlseg2e32ff.v",
    "vlseg3e32ff.v",
    "vlseg4e32ff.v",
    "vlseg5e32ff.v",
    "vlseg6e32ff.v",
    "vlseg7e32ff.v",
    "vlseg8e32ff.v",
    "vlse32.v",
    "vlsseg2e32.v",
    "vlsseg3e32.v",
    "vlsseg4e32.v",
    "vlsseg5e32.v",
    "vlsseg6e32.v",
    "vlsseg7e32.v",
    "vlsseg8e32.v",
    "vluxei32.v",
    "vluxseg2ei32.v",
    "vluxseg3ei32.v",
    "vluxseg4ei32.v",
    "vluxseg5ei32.v",
    "vluxseg6ei32.v",
    "vluxseg7ei32.v",
    "vluxseg8ei32.v",
    "vloxei32.v",
    "vloxseg2ei32.v",
    "vloxseg3ei32.v",
    "vloxseg4ei32.v",
    "vloxseg5ei32.v",
    "vloxseg6ei32.v",
    "vloxseg7ei32.v",
    "vloxseg8ei32.v",
    "vse32.v",
    "vsseg2e32.v",
    "vsseg3e32.v",
    "vsseg4e32.v",
    "vsseg5e32.v",
    "vsseg6e32.v",
    "vsseg7e32.v",
    "vsseg8e32.v",
    "vsse32.v",
    "vssseg2e32.v",
    "vssseg3e32.v",
    "vssseg4e32.v",
    "vssseg5e32.v",
    "vssseg6e32.v",
    "vssseg7e32.v",
    "vssseg8e32.v",
    "vsuxei32.v",
    "vsuxseg2ei32.v",
    "vsuxseg3ei32.v",
    "vsuxseg4ei32.v",
    "vsuxseg5ei32.v",
    "vsuxseg6ei32.v",
    "vsuxseg7ei32.v",
    "vsuxseg8ei32.v",
    "vsoxei32.v",
    "vsoxseg2ei32.v",
    "vsoxseg3ei32.v",
    "vsoxseg4ei32.v",
    "vsoxseg5ei32.v",
    "vsoxseg6ei32.v",
    "vsoxseg7ei32.v",
    "vsoxseg8ei32.v",
    "vl1re32.v",
    "vl2re32.v",
    "vl4re32.v",
    "vl8re32.v",
]

eew64_ins = [
    "vle64.v",
    "vlseg2e64.v",
    "vlseg3e64.v",
    "vlseg4e64.v",
    "vlseg5e64.v",
    "vlseg6e64.v",
    "vlseg7e64.v",
    "vlseg8e64.v",
    "vle64ff.v",
    "vlseg2e64ff.v",
    "vlseg3e64ff.v",
    "vlseg4e64ff.v",
    "vlseg5e64ff.v",
    "vlseg6e64ff.v",
    "vlseg7e64ff.v",
    "vlseg8e64ff.v",
    "vlse64.v",
    "vlsseg2e64.v",
    "vlsseg3e64.v",
    "vlsseg4e64.v",
    "vlsseg5e64.v",
    "vlsseg6e64.v",
    "vlsseg7e64.v",
    "vlsseg8e64.v",
    "vluxei64.v",
    "vluxseg2ei64.v",
    "vluxseg3ei64.v",
    "vluxseg4ei64.v",
    "vluxseg5ei64.v",
    "vluxseg6ei64.v",
    "vluxseg7ei64.v",
    "vluxseg8ei64.v",
    "vloxei64.v",
    "vloxseg2ei64.v",
    "vloxseg3ei64.v",
    "vloxseg4ei64.v",
    "vloxseg5ei64.v",
    "vloxseg6ei64.v",
    "vloxseg7ei64.v",
    "vloxseg8ei64.v",
    "vse64.v",
    "vsseg2e64.v",
    "vsseg3e64.v",
    "vsseg4e64.v",
    "vsseg5e64.v",
    "vsseg6e64.v",
    "vsseg7e64.v",
    "vsseg8e64.v",
    "vsse64.v",
    "vssseg2e64.v",
    "vssseg3e64.v",
    "vssseg4e64.v",
    "vssseg5e64.v",
    "vssseg6e64.v",
    "vssseg7e64.v",
    "vssseg8e64.v",
    "vsuxei64.v",
    "vsuxseg2ei64.v",
    "vsuxseg3ei64.v",
    "vsuxseg4ei64.v",
    "vsuxseg5ei64.v",
    "vsuxseg6ei64.v",
    "vsuxseg7ei64.v",
    "vsuxseg8ei64.v",
    "vsoxei64.v",
    "vsoxseg2ei64.v",
    "vsoxseg3ei64.v",
    "vsoxseg4ei64.v",
    "vsoxseg5ei64.v",
    "vsoxseg6ei64.v",
    "vsoxseg7ei64.v",
    "vsoxseg8ei64.v",
    "vl1re64.v",
    "vl2re64.v",
    "vl4re64.v",
    "vl8re64.v",
]

ls_no_eew_ins = ["vs1r.v", "vs2r.v", "vs4r.v", "vs8r.v", "vsm.v", "vlm.v"]

segment_stores = seg2_stores + seg3_stores + seg4_stores + seg5_stores + seg6_stores + seg7_stores + seg8_stores
segment_loads = seg2_loads + seg3_loads + seg4_loads + seg5_loads + seg6_loads + seg7_loads + seg8_loads

indexed_stores = [
    # Indexed unordered Stores
    "vsuxei8.v",
    "vsuxei16.v",
    "vsuxei32.v",
    "vsuxei64.v",
    "vsuxseg2ei8.v",
    "vsuxseg2ei16.v",
    "vsuxseg2ei32.v",
    "vsuxseg2ei64.v",
    "vsuxseg3ei8.v",
    "vsuxseg3ei16.v",
    "vsuxseg3ei32.v",
    "vsuxseg3ei64.v",
    "vsuxseg4ei8.v",
    "vsuxseg4ei16.v",
    "vsuxseg4ei32.v",
    "vsuxseg4ei64.v",
    "vsuxseg5ei8.v",
    "vsuxseg5ei16.v",
    "vsuxseg5ei32.v",
    "vsuxseg5ei64.v",
    "vsuxseg6ei8.v",
    "vsuxseg6ei16.v",
    "vsuxseg6ei32.v",
    "vsuxseg6ei64.v",
    "vsuxseg7ei8.v",
    "vsuxseg7ei16.v",
    "vsuxseg7ei32.v",
    "vsuxseg7ei64.v",
    "vsuxseg8ei8.v",
    "vsuxseg8ei16.v",
    "vsuxseg8ei32.v",
    "vsuxseg8ei64.v",
    # Indexed ordered Stores
    "vsoxei8.v",
    "vsoxei16.v",
    "vsoxei32.v",
    "vsoxei64.v",
    "vsoxseg2ei8.v",
    "vsoxseg2ei16.v",
    "vsoxseg2ei32.v",
    "vsoxseg2ei64.v",
    "vsoxseg3ei8.v",
    "vsoxseg3ei16.v",
    "vsoxseg3ei32.v",
    "vsoxseg3ei64.v",
    "vsoxseg4ei8.v",
    "vsoxseg4ei16.v",
    "vsoxseg4ei32.v",
    "vsoxseg4ei64.v",
    "vsoxseg5ei8.v",
    "vsoxseg5ei16.v",
    "vsoxseg5ei32.v",
    "vsoxseg5ei64.v",
    "vsoxseg6ei8.v",
    "vsoxseg6ei16.v",
    "vsoxseg6ei32.v",
    "vsoxseg6ei64.v",
    "vsoxseg7ei8.v",
    "vsoxseg7ei16.v",
    "vsoxseg7ei32.v",
    "vsoxseg7ei64.v",
    "vsoxseg8ei8.v",
    "vsoxseg8ei16.v",
    "vsoxseg8ei32.v",
    "vsoxseg8ei64.v",
]

indexed_loads = [
    # Indexed unordered loads
    "vluxei8.v",
    "vluxei16.v",
    "vluxei32.v",
    "vluxei64.v",
    "vluxseg2ei8.v",
    "vluxseg2ei16.v",
    "vluxseg2ei32.v",
    "vluxseg2ei64.v",
    "vluxseg3ei8.v",
    "vluxseg3ei16.v",
    "vluxseg3ei32.v",
    "vluxseg3ei64.v",
    "vluxseg4ei8.v",
    "vluxseg4ei16.v",
    "vluxseg4ei32.v",
    "vluxseg4ei64.v",
    "vluxseg5ei8.v",
    "vluxseg5ei16.v",
    "vluxseg5ei32.v",
    "vluxseg5ei64.v",
    "vluxseg6ei8.v",
    "vluxseg6ei16.v",
    "vluxseg6ei32.v",
    "vluxseg6ei64.v",
    "vluxseg7ei8.v",
    "vluxseg7ei16.v",
    "vluxseg7ei32.v",
    "vluxseg7ei64.v",
    "vluxseg8ei8.v",
    "vluxseg8ei16.v",
    "vluxseg8ei32.v",
    "vluxseg8ei64.v",
    # Indexed ordered Loads
    "vloxei8.v",
    "vloxei16.v",
    "vloxei32.v",
    "vloxei64.v",
    "vloxseg2ei8.v",
    "vloxseg2ei16.v",
    "vloxseg2ei32.v",
    "vloxseg2ei64.v",
    "vloxseg3ei8.v",
    "vloxseg3ei16.v",
    "vloxseg3ei32.v",
    "vloxseg3ei64.v",
    "vloxseg4ei8.v",
    "vloxseg4ei16.v",
    "vloxseg4ei32.v",
    "vloxseg4ei64.v",
    "vloxseg5ei8.v",
    "vloxseg5ei16.v",
    "vloxseg5ei32.v",
    "vloxseg5ei64.v",
    "vloxseg6ei8.v",
    "vloxseg6ei16.v",
    "vloxseg6ei32.v",
    "vloxseg6ei64.v",
    "vloxseg7ei8.v",
    "vloxseg7ei16.v",
    "vloxseg7ei32.v",
    "vloxseg7ei64.v",
    "vloxseg8ei8.v",
    "vloxseg8ei16.v",
    "vloxseg8ei32.v",
    "vloxseg8ei64.v",
]

indexed_ls_ins = indexed_loads + indexed_stores

vector_loads = [
    "vl1re16.v",
    "vl1re32.v",
    "vl1re64.v",
    "vl1re8.v",
    "vl2re16.v",
    "vl2re32.v",
    "vl2re64.v",
    "vl2re8.v",
    "vl4re16.v",
    "vl4re32.v",
    "vl4re64.v",
    "vl4re8.v",
    "vl8re16.v",
    "vl8re32.v",
    "vl8re64.v",
    "vl8re8.v",
    "vle16.v",
    "vle16ff.v",
    "vle32.v",
    "vle32ff.v",
    "vle64.v",
    "vle64ff.v",
    "vle8.v",
    "vle8ff.v",
    "vloxei16.v",
    "vloxei32.v",
    "vloxei64.v",
    "vloxei8.v",
    "vloxseg2ei16.v",
    "vloxseg2ei32.v",
    "vloxseg2ei64.v",
    "vloxseg2ei8.v",
    "vloxseg3ei16.v",
    "vloxseg3ei32.v",
    "vloxseg3ei64.v",
    "vloxseg3ei8.v",
    "vloxseg4ei16.v",
    "vloxseg4ei32.v",
    "vloxseg4ei64.v",
    "vloxseg4ei8.v",
    "vloxseg5ei16.v",
    "vloxseg5ei32.v",
    "vloxseg5ei64.v",
    "vloxseg5ei8.v",
    "vloxseg6ei16.v",
    "vloxseg6ei32.v",
    "vloxseg6ei64.v",
    "vloxseg6ei8.v",
    "vloxseg7ei16.v",
    "vloxseg7ei32.v",
    "vloxseg7ei64.v",
    "vloxseg7ei8.v",
    "vloxseg8ei16.v",
    "vloxseg8ei32.v",
    "vloxseg8ei64.v",
    "vloxseg8ei8.v",
    "vlse16.v",
    "vlse32.v",
    "vlse64.v",
    "vlse8.v",
    "vlseg2e16.v",
    "vlseg2e16ff.v",
    "vlseg2e32.v",
    "vlseg2e32ff.v",
    "vlseg2e64.v",
    "vlseg2e64ff.v",
    "vlseg2e8.v",
    "vlseg2e8ff.v",
    "vlseg3e16.v",
    "vlseg3e16ff.v",
    "vlseg3e32.v",
    "vlseg3e32ff.v",
    "vlseg3e64.v",
    "vlseg3e64ff.v",
    "vlseg3e8.v",
    "vlseg3e8ff.v",
    "vlseg4e16.v",
    "vlseg4e16ff.v",
    "vlseg4e32.v",
    "vlseg4e32ff.v",
    "vlseg4e64.v",
    "vlseg4e64ff.v",
    "vlseg4e8.v",
    "vlseg4e8ff.v",
    "vlseg5e16.v",
    "vlseg5e16ff.v",
    "vlseg5e32.v",
    "vlseg5e32ff.v",
    "vlseg5e64.v",
    "vlseg5e64ff.v",
    "vlseg5e8.v",
    "vlseg5e8ff.v",
    "vlseg6e16.v",
    "vlseg6e16ff.v",
    "vlseg6e32.v",
    "vlseg6e32ff.v",
    "vlseg6e64.v",
    "vlseg6e64ff.v",
    "vlseg6e8.v",
    "vlseg6e8ff.v",
    "vlseg7e16.v",
    "vlseg7e16ff.v",
    "vlseg7e32.v",
    "vlseg7e32ff.v",
    "vlseg7e64.v",
    "vlseg7e64ff.v",
    "vlseg7e8.v",
    "vlseg7e8ff.v",
    "vlseg8e16.v",
    "vlseg8e16ff.v",
    "vlseg8e32.v",
    "vlseg8e32ff.v",
    "vlseg8e64.v",
    "vlseg8e64ff.v",
    "vlseg8e8.v",
    "vlseg8e8ff.v",
    "vlsseg2e16.v",
    "vlsseg2e32.v",
    "vlsseg2e64.v",
    "vlsseg2e8.v",
    "vlsseg3e16.v",
    "vlsseg3e32.v",
    "vlsseg3e64.v",
    "vlsseg3e8.v",
    "vlsseg4e16.v",
    "vlsseg4e32.v",
    "vlsseg4e64.v",
    "vlsseg4e8.v",
    "vlsseg5e16.v",
    "vlsseg5e32.v",
    "vlsseg5e64.v",
    "vlsseg5e8.v",
    "vlsseg6e16.v",
    "vlsseg6e32.v",
    "vlsseg6e64.v",
    "vlsseg6e8.v",
    "vlsseg7e16.v",
    "vlsseg7e32.v",
    "vlsseg7e64.v",
    "vlsseg7e8.v",
    "vlsseg8e16.v",
    "vlsseg8e32.v",
    "vlsseg8e64.v",
    "vlsseg8e8.v",
    "vluxei16.v",
    "vluxei32.v",
    "vluxei64.v",
    "vluxei8.v",
    "vluxseg2ei16.v",
    "vluxseg2ei32.v",
    "vluxseg2ei64.v",
    "vluxseg2ei8.v",
    "vluxseg3ei16.v",
    "vluxseg3ei32.v",
    "vluxseg3ei64.v",
    "vluxseg3ei8.v",
    "vluxseg4ei16.v",
    "vluxseg4ei32.v",
    "vluxseg4ei64.v",
    "vluxseg4ei8.v",
    "vluxseg5ei16.v",
    "vluxseg5ei32.v",
    "vluxseg5ei64.v",
    "vluxseg5ei8.v",
    "vluxseg6ei16.v",
    "vluxseg6ei32.v",
    "vluxseg6ei64.v",
    "vluxseg6ei8.v",
    "vluxseg7ei16.v",
    "vluxseg7ei32.v",
    "vluxseg7ei64.v",
    "vluxseg7ei8.v",
    "vluxseg8ei16.v",
    "vluxseg8ei32.v",
    "vluxseg8ei64.v",
    "vluxseg8ei8.v",
] + [
    # Unit-stride loads
    "vle8.v",
    "vle16.v",
    "vle32.v",
    "vle64.v",
    # Fault-only-first loads
    "vle8ff.v",
    "vle16ff.v",
    "vle32ff.v",
    "vle64ff.v",
    # Strided loads
    "vlse8.v",
    "vlse16.v",
    "vlse32.v",
    "vlse64.v",
    # Indexed unordered loads
    "vluxei8.v",
    "vluxei16.v",
    "vluxei32.v",
    "vluxei64.v",
    # Indexed ordered Loads
    "vloxei8.v",
    "vloxei16.v",
    "vloxei32.v",
    "vloxei64.v",
    # Whole Register Loads
    "vl1re8.v",
    "vl2re8.v",
    "vl4re8.v",
    "vl8re8.v",
    "vl1re16.v",
    "vl2re16.v",
    "vl4re16.v",
    "vl8re16.v",
    "vl1re32.v",
    "vl2re32.v",
    "vl4re32.v",
    "vl8re32.v",
    "vl1re64.v",
    "vl2re64.v",
    "vl4re64.v",
    "vl8re64.v",
    # Mask Load
    "vlm.v",
]

vector_stores = [
    "vs1r.v",
    "vs2r.v",
    "vs4r.v",
    "vs8r.v",
    "vse16.v",
    "vse32.v",
    "vse64.v",
    "vse8.v",
    "vsoxei16.v",
    "vsoxei32.v",
    "vsoxei64.v",
    "vsoxei8.v",
    "vsoxseg2ei16.v",
    "vsoxseg2ei32.v",
    "vsoxseg2ei64.v",
    "vsoxseg2ei8.v",
    "vsoxseg3ei16.v",
    "vsoxseg3ei32.v",
    "vsoxseg3ei64.v",
    "vsoxseg3ei8.v",
    "vsoxseg4ei16.v",
    "vsoxseg4ei32.v",
    "vsoxseg4ei64.v",
    "vsoxseg4ei8.v",
    "vsoxseg5ei16.v",
    "vsoxseg5ei32.v",
    "vsoxseg5ei64.v",
    "vsoxseg5ei8.v",
    "vsoxseg6ei16.v",
    "vsoxseg6ei32.v",
    "vsoxseg6ei64.v",
    "vsoxseg6ei8.v",
    "vsoxseg7ei16.v",
    "vsoxseg7ei32.v",
    "vsoxseg7ei64.v",
    "vsoxseg7ei8.v",
    "vsoxseg8ei16.v",
    "vsoxseg8ei32.v",
    "vsoxseg8ei64.v",
    "vsoxseg8ei8.v",
    "vsse16.v",
    "vsse32.v",
    "vsse64.v",
    "vsse8.v",
    "vsseg2e16.v",
    "vsseg2e32.v",
    "vsseg2e64.v",
    "vsseg2e8.v",
    "vsseg3e16.v",
    "vsseg3e32.v",
    "vsseg3e64.v",
    "vsseg3e8.v",
    "vsseg4e16.v",
    "vsseg4e32.v",
    "vsseg4e64.v",
    "vsseg4e8.v",
    "vsseg5e16.v",
    "vsseg5e32.v",
    "vsseg5e64.v",
    "vsseg5e8.v",
    "vsseg6e16.v",
    "vsseg6e32.v",
    "vsseg6e64.v",
    "vsseg6e8.v",
    "vsseg7e16.v",
    "vsseg7e32.v",
    "vsseg7e64.v",
    "vsseg7e8.v",
    "vsseg8e16.v",
    "vsseg8e32.v",
    "vsseg8e64.v",
    "vsseg8e8.v",
    "vssseg2e16.v",
    "vssseg2e32.v",
    "vssseg2e64.v",
    "vssseg2e8.v",
    "vssseg3e16.v",
    "vssseg3e32.v",
    "vssseg3e64.v",
    "vssseg3e8.v",
    "vssseg4e16.v",
    "vssseg4e32.v",
    "vssseg4e64.v",
    "vssseg4e8.v",
    "vssseg5e16.v",
    "vssseg5e32.v",
    "vssseg5e64.v",
    "vssseg5e8.v",
    "vssseg6e16.v",
    "vssseg6e32.v",
    "vssseg6e64.v",
    "vssseg6e8.v",
    "vssseg7e16.v",
    "vssseg7e32.v",
    "vssseg7e64.v",
    "vssseg7e8.v",
    "vssseg8e16.v",
    "vssseg8e32.v",
    "vssseg8e64.v",
    "vssseg8e8.v",
    "vsuxei16.v",
    "vsuxei32.v",
    "vsuxei64.v",
    "vsuxei8.v",
    "vsuxseg2ei16.v",
    "vsuxseg2ei32.v",
    "vsuxseg2ei64.v",
    "vsuxseg2ei8.v",
    "vsuxseg3ei16.v",
    "vsuxseg3ei32.v",
    "vsuxseg3ei64.v",
    "vsuxseg3ei8.v",
    "vsuxseg4ei16.v",
    "vsuxseg4ei32.v",
    "vsuxseg4ei64.v",
    "vsuxseg4ei8.v",
    "vsuxseg5ei16.v",
    "vsuxseg5ei32.v",
    "vsuxseg5ei64.v",
    "vsuxseg5ei8.v",
    "vsuxseg6ei16.v",
    "vsuxseg6ei32.v",
    "vsuxseg6ei64.v",
    "vsuxseg6ei8.v",
    "vsuxseg7ei16.v",
    "vsuxseg7ei32.v",
    "vsuxseg7ei64.v",
    "vsuxseg7ei8.v",
    "vsuxseg8ei16.v",
    "vsuxseg8ei32.v",
    "vsuxseg8ei64.v",
    "vsuxseg8ei8.v",
] + [
    # Unit-stride Stores
    "vse8.v",
    "vse16.v",
    "vse32.v",
    "vse64.v",
    # Strided Stores
    "vsse8.v",
    "vsse16.v",
    "vsse32.v",
    "vsse64.v",
    # Indexed unordered Stores
    "vsuxei8.v",
    "vsuxei16.v",
    "vsuxei32.v",
    "vsuxei64.v",
    # Indexed ordered Stores
    "vsoxei8.v",
    "vsoxei16.v",
    "vsoxei32.v",
    "vsoxei64.v",
    # Whole Register Stores
    "vs1r.v",
    "vs2r.v",
    "vs4r.v",
    "vs8r.v",
    # Mask Store
    "vsm.v",
]

vector_ls_ins = vector_stores + vector_loads

seg_vv_load = [
    # Indexed unordered loads
    "vluxseg2ei8.v",
    "vluxseg2ei16.v",
    "vluxseg2ei32.v",
    "vluxseg2ei64.v",
    "vluxseg3ei8.v",
    "vluxseg3ei16.v",
    "vluxseg3ei32.v",
    "vluxseg3ei64.v",
    "vluxseg4ei8.v",
    "vluxseg4ei16.v",
    "vluxseg4ei32.v",
    "vluxseg4ei64.v",
    "vluxseg5ei8.v",
    "vluxseg5ei16.v",
    "vluxseg5ei32.v",
    "vluxseg5ei64.v",
    "vluxseg6ei8.v",
    "vluxseg6ei16.v",
    "vluxseg6ei32.v",
    "vluxseg6ei64.v",
    "vluxseg7ei8.v",
    "vluxseg7ei16.v",
    "vluxseg7ei32.v",
    "vluxseg7ei64.v",
    "vluxseg8ei8.v",
    "vluxseg8ei16.v",
    "vluxseg8ei32.v",
    "vluxseg8ei64.v",
    # Indexed ordered Loads
    "vloxseg2ei8.v",
    "vloxseg2ei16.v",
    "vloxseg2ei32.v",
    "vloxseg2ei64.v",
    "vloxseg3ei8.v",
    "vloxseg3ei16.v",
    "vloxseg3ei32.v",
    "vloxseg3ei64.v",
    "vloxseg4ei8.v",
    "vloxseg4ei16.v",
    "vloxseg4ei32.v",
    "vloxseg4ei64.v",
    "vloxseg5ei8.v",
    "vloxseg5ei16.v",
    "vloxseg5ei32.v",
    "vloxseg5ei64.v",
    "vloxseg6ei8.v",
    "vloxseg6ei16.v",
    "vloxseg6ei32.v",
    "vloxseg6ei64.v",
    "vloxseg7ei8.v",
    "vloxseg7ei16.v",
    "vloxseg7ei32.v",
    "vloxseg7ei64.v",
    "vloxseg8ei8.v",
    "vloxseg8ei16.v",
    "vloxseg8ei32.v",
    "vloxseg8ei64.v",
]


def vector_instruction_defaults(instruction: str) -> dict[str, Any]:
    vector_register_data = {}

    if instruction in wvsins:
        vector_register_data["vs1_size_multiplier"] = 2
        vector_register_data["vd_size_multiplier"] = 2
    if instruction in vs2_widen_ins:
        vector_register_data["vs2_size_multiplier"] = 2
    if instruction in vd_widen_ins:
        vector_register_data["vd_size_multiplier"] = 2

    if instruction in mmins or instruction in vmlogicalins:  # instructions operate with EEW = 1
        vector_register_data["vs1_reg_type"] = "mask"
        vector_register_data["vs2_reg_type"] = "mask"
        vector_register_data["vd_reg_type"] = "mask"
    if instruction in viotains:
        vector_register_data["vs2_reg_type"] = "mask"
    if instruction in maskins:  # instructions operate with vd EEW = 1
        vector_register_data["vd_reg_type"] = "mask"
    if instruction in vredins:
        vector_register_data["vd_reg_type"] = "scalar"
        vector_register_data["vs1_reg_type"] = "scalar"
    if instruction == "vmv.x.s":
        vector_register_data["vs2_reg_type"] = "scalar"
    if instruction == "vmv.s.x":
        vector_register_data["vd_reg_type"] = "scalar"

    return vector_register_data


def _add_overlap(l1: list[list[str]] | None, l2: list[list[str]] | None) -> list[list[str]]:
    no_overlap = []
    if l1 is not None:
        no_overlap += l1
    if l2 is not None:
        no_overlap += l2
    return no_overlap


def _get_instruction_EEW(instruction: str) -> int | None:
    if instruction in eew8_ins:
        return 8
    elif instruction in eew16_ins:
        return 16
    elif instruction in eew32_ins:
        return 32
    elif instruction in eew64_ins:
        return 64
    else:
        return None


def _get_instruction_segments(instruction: str) -> int:
    if instruction in seg2:
        return 2
    elif instruction in seg3:
        return 3
    elif instruction in seg4:
        return 4
    elif instruction in seg5:
        return 5
    elif instruction in seg6:
        return 6
    elif instruction in seg7:
        return 7
    elif instruction in seg8:
        return 8
    else:
        return 1


def vector_instruction_overlap_constraints(instruction: str, sew: int, masked: bool = False) -> list[list[str]] | None:
    no_overlap = None

    # Widening MACs must be checked before the generic widening branches: vd is read+written at
    # EEW=2*SEW (accumulator). For .vv forms, both vs1 and vs2 are EEW=SEW vector sources, so
    # overlap with either would read the same vector register at two different EEWs (reserved per
    # V spec §5.2). For .vx/.vf forms, the second source is scalar, so only constrain vd vs vs2.
    if instruction in widening_mac_ins:
        no_overlap = [["vd", "vs2"], ["vd", "vs1"]] if instruction.endswith(".vv") else [["vd", "vs2"]]
    elif instruction in wvvins:
        no_overlap = [["vd_bottom", "vs2"], ["vd_bottom", "vs1"]]
    elif instruction in vupgatherins:
        no_overlap = [["vd", "vs2"], ["vd", "vs1"]]
    elif instruction in vmlogicalins or instruction in viotains:
        no_overlap = [["vd", "vs2"]]
    elif instruction in wvxins or instruction in fwvfins:
        no_overlap = [["vd_bottom", "vs2"]]
    elif instruction in mv_ins or instruction in fmvvins:
        no_overlap = [["vd", "vs2"], ["vd", "vs1"]]  # mv_ins can never be masked
    elif instruction in fmvfins:
        no_overlap = [["vd", "vs2"]]  # fmvfins can be masked
    elif instruction in vextins:
        no_overlap = [["vd_bottom", "vs2"]]
    elif instruction in narrowins:
        no_overlap = [["vd", "vs2_top"], ["vs2", "vs1"]]
    elif instruction in wvsins:
        no_overlap = [["vs2", "vs1"]]  # no "_bottom" in vd because its a reduction instruction
    elif instruction in wwvins:
        no_overlap = [["vd_bottom", "vs1"], ["vs1", "vs2"]]
    elif instruction in fwcvt_ins:
        no_overlap = [["vd_bottom", "vs2"]]
    elif instruction in v_mins:
        no_overlap = [["v0", "vs2"], ["v0", "vs1"], ["v0", "vd"]]
    elif instruction in mv_mins:
        no_overlap = [["vd", "vs2"], ["v0", "vs2"], ["vd", "vs1"], ["v0", "vs1"]]
    elif instruction in vcompressins:
        no_overlap = [["vd", "vs2", "vs1"]]
    elif instruction in seg_vv_load or instruction in crypto_no_vd_vs2:
        no_overlap = [["vd", "vs2"]]
    elif instruction in crypto_no_vd_vs2_vs1:
        no_overlap = [["vd", "vs1"], ["vd", "vs2"]]

    if instruction in vector_ls_ins:
        no_overlap = _add_overlap(no_overlap, [["rs1", "rs2"]])

    # vrgatherei16.vv: vs1 holds 16-bit indices while vs2 holds SEW-bit data, so their EMUL groups
    # differ when SEW != 16 and the registers cannot safely overlap.
    if instruction == "vrgatherei16.vv" and not isinstance(sew, str) and sew != 16:
        no_overlap = _add_overlap(no_overlap, [["vs1", "vs2"]])

    ls_indexed_vs2_eew = _get_instruction_EEW(instruction)

    if ls_indexed_vs2_eew is not None and not isinstance(sew, str):  # noqa: SIM102
        # Indexed L/S: data EEW (= SEW) vs index EEW (= instruction EEW) may differ.
        # V-spec §5.2 register-overlap rules between dest and source register groups:
        #   (a) EEW_dest == EEW_src                -> any overlap legal
        #   (b) EEW_dest <  EEW_src                -> overlap only at LOWEST part of source group
        #   (c) EEW_dest >  EEW_src, EMUL_src >= 1 -> overlap only at HIGHEST part of dest group
        # For non-segment indexed loads (dest=vd, src=vs2) we forbid the *illegal*
        # overlap region:
        #   K > SEW: vd must not overlap the TOP of vs2 group (only bottom legal -> rule b).
        #   K < SEW: vs2 must not overlap the BOTTOM of vd group (only top legal -> rule c).
        # Indexed segment loads keep the full no-overlap rule applied above
        # (norm:vector_ls_seg_indexed_vreg_rsv).
        # For indexed stores (any nf) both vs3 and vs2 are sources; vs3 == vs2 is only
        # legal when EEW_idx == SEW (a single source register cannot be read at two EEWs).
        if ls_indexed_vs2_eew != sew:
            if instruction in indexed_stores:
                no_overlap = _add_overlap(no_overlap, [["vs3", "vs2"]])
            elif instruction in indexed_loads and instruction not in segment_loads:
                if ls_indexed_vs2_eew > sew:
                    no_overlap = _add_overlap(no_overlap, [["vd", "vs2_top"]])
                else:  # ls_indexed_vs2_eew < sew
                    no_overlap = _add_overlap(no_overlap, [["vd_bottom", "vs2"]])

    if instruction in segment_loads:
        # Indexed segment loads explicitly reserve any vd/vs2 overlap (V-spec
        # norm:vector_ls_seg_indexed_vreg_rsv); non-indexed segment loads keep the
        # same conservative rule.
        no_overlap = _add_overlap(no_overlap, [["vd", "vs2"]])

    # Masked indexed LS: vs2 (index, EEW = index EEW) cannot equal v0 (mask,
    # EEW = 1) — spec forbids reading the same register at two different EEWs
    # in a single instruction (v-spec norm:vreg_source_eew_rsv).
    if masked and instruction in indexed_ls_ins:
        no_overlap = _add_overlap(no_overlap, [["v0", "vs2"]])

    return no_overlap


def randomizeRegister(
    instruction: str,
    eew: int | None,
    register_argument_name: str,
    reg_count: int,
    register_preset_data: dict[str, dict[str, Any]],
    xlen: int,
    flen: int,
    lmul: int = 1,
) -> dict[str, Any]:

    register_data = register_preset_data[register_argument_name].copy()
    register_type = register_argument_name[0]

    register = register_data["reg"]

    if register is None:  # if the register is a vector register
        if register_type == "v":
            # scalar and mask holding registers only take up 1 register no matter the lmul
            emul = int(register_data["size_multiplier"] * lmul)  # need to avoid 1.0
            segments = register_data["segments"]
            if register_data["reg_type"] == "scalar" or register_data["reg_type"] == "mask" or emul < 1:
                emul = 1
            # Align to lmul even for scalar/mask registers so that scaffolding
            # loads/stores (which execute at the current vtype LMUL) don't trap
            # on misaligned register numbers.
            alignment = max(emul, int(lmul)) if int(lmul) >= 1 else emul
            register = alignment * random.randint(
                0, int(reg_count / alignment) - (segments)
            )  # only register numbers of multiples of alignment are allowed, segments must not go past reg 31
        else:  # normal instructions
            if register_type == "r":  # noqa: SIM108
                register = random.randint(1, reg_count - 1)  # 1 to maxreg, inclusive
            else:  # "f" registers
                register = random.randint(0, reg_count - 1)  # 0 to maxreg, inclusive
    elif register_type == "v":
        # Preset vector register: verify the requested base register leaves room
        # for the full segment group (NF * EMUL_field). Callers (e.g. make_vs3_vs2)
        # iterate over v in range(32) and rely on ValueError to skip illegal vs.
        emul_check = int(register_data["size_multiplier"] * lmul)
        if register_data["reg_type"] == "scalar" or register_data["reg_type"] == "mask" or emul_check < 1:
            emul_check = 1
        if register + emul_check * register_data["segments"] > reg_count:
            raise ValueError(
                f"preset {register_argument_name}=v{register} with NF={register_data['segments']} "
                f"EMUL_field={emul_check} overflows past v{reg_count - 1} for {instruction}"
            )
        if emul_check > 1 and register % emul_check != 0:
            raise ValueError(
                f"preset {register_argument_name}=v{register} not aligned to EMUL={emul_check} for {instruction}"
            )

    register_data["reg"] = register

    if register_type == "r":
        if register_data["val"] is None:
            if (
                instruction in vector_ls_ins and register_argument_name == "rs2" and instruction not in ls_no_eew_ins
            ):  # loads and stores stride
                assert eew is not None, 'eew should be set when "instruction not in ls_no_eew_ins"'
                register_data["val"] = random.randint(-2, 2 + 1) * int(eew / 8)
            else:
                register_data["val"] = random.randint(0, (2**xlen) - 1)
        if (
            register_data["val_pointer"] is None and instruction in vector_ls_ins and register_argument_name == "rs1"
        ):  # needs to point to an address
            register_data["val_pointer"] = "vector_ls_random_base"
    elif register_type == "f":
        if register_data["val"] is None:
            register_data["val"] = random.randint(0, (2**flen) - 1)

    return register_data


def generate_random_vector_params(
    test_data: TestData,
    instruction: str,
    instr_type: str,
    lmul: int,
    additional_no_overlap: list[list[str]] | None = None,
    masked: bool = False,
    suite: Literal["length", "base"] = "base",
    **fixed_params: Any,  # noqa: ANN401
) -> InstructionParams:
    test_count = test_data.test_count

    sew = test_data.config.sew
    assert sew is not None, "SEW must be set for Vector Instructions"

    fixed_params.update(vector_instruction_defaults(instr_type))
    no_overlap = vector_instruction_overlap_constraints(instr_type, sew, masked)
    no_overlap = _add_overlap(no_overlap, additional_no_overlap)

    scalar_register_preset_data: dict[str, dict[str, Any]] = {
        "rd": {"reg": None, "val": None, "val_pointer": None},
        "rs1": {"reg": None, "val": None, "val_pointer": None},
        "rs2": {"reg": None, "val": None, "val_pointer": None},
    }

    floating_point_register_preset_data = {
        "fd": {"reg": None, "val": None, "val_pointer": None},
        "fs1": {"reg": None, "val": None, "val_pointer": None},
    }

    vector_register_preset_data = {
        "vs3": {"reg": None, "val": None, "val_pointer": None, "size_multiplier": 1, "reg_type": None, "segments": 1},
        "vd": {"reg": None, "val": None, "val_pointer": None, "size_multiplier": 1, "reg_type": None, "segments": 1},
        "vs1": {"reg": None, "val": None, "val_pointer": None, "size_multiplier": 1, "reg_type": None, "segments": 1},
        "vs2": {"reg": None, "val": None, "val_pointer": None, "size_multiplier": 1, "reg_type": None, "segments": 1},
    }

    immediate_preset_data = None

    vector_additional_arguments = ["v0"]

    ####################################################################################
    # set all incoming data to
    # designate reserved scalar, floating point and vector registers
    ####################################################################################

    scalar_register_data = scalar_register_preset_data.copy()
    floating_point_register_data = floating_point_register_preset_data.copy()
    vector_register_data = vector_register_preset_data.copy()

    for variable, value in fixed_params.items():
        found = False

        # Get index of first underscore
        idx = variable.find("_")

        # Split into two parts
        if idx == -1:
            data_name = variable
            data_type = "reg"
        else:
            data_name = variable[:idx]
            data_type = variable[idx + 1 :]

        # load vector register data
        if data_name in vector_register_preset_data:
            vector_register_preset_data[data_name][data_type] = value
            found = True

        # load scalar register data
        if data_name in scalar_register_preset_data:
            scalar_register_data[data_name][data_type] = value
            found = True

        # load floating point register data
        if data_name in floating_point_register_preset_data:
            floating_point_register_data[data_name][data_type] = value
            found = True

        if data_name == "imm":
            immediate_preset_data = value
            found = True
        elif data_name in vector_additional_arguments:
            found = True

        if not found:
            raise TypeError(f"Unexpected keyword argument: '{variable}'")

    if instruction in whole_register_ls:
        lmul = max(
            1, _get_instruction_segments(instruction)
        )  # whole register load stores ignore lmul and instead use nfields as emul
    else:
        segments = _get_instruction_segments(instruction)
        vector_register_preset_data["vs3"]["segments"] = segments
        vector_register_preset_data["vs2"]["segments"] = segments
        vector_register_preset_data["vs1"]["segments"] = segments
        vector_register_preset_data["vd"]["segments"] = segments

    eew = None
    if instruction in eew64_ins:
        eew = 64
    elif instruction in eew32_ins:
        eew = 32
    elif instruction in eew16_ins:
        eew = 16
    elif instruction in eew8_ins:
        eew = 8

    if eew is not None:  # if emul is greater than 1 use it for the size multiplier
        if instruction in whole_register_ls:
            pass
        elif instruction in indexed_loads or instruction in indexed_stores:
            vector_register_preset_data["vs2"]["size_multiplier"] = eew / sew
        elif instruction in vector_loads:
            vector_register_preset_data["vd"]["size_multiplier"] = eew / sew
        elif instruction in vector_stores:
            vector_register_preset_data["vs3"]["size_multiplier"] = eew / sew

    # For indexed LS, the index register group (vs2) is NOT segmented —
    # only the data register group uses nf.  Override the general assignment.
    if instruction in indexed_ls_ins:
        vector_register_preset_data["vs2"]["segments"] = 1

    if instruction in vextins:  # swapped lmul and emul of vext instr for the convenience of register managing
        fraction_sew = 1 / int(instruction[-1])
        vector_register_preset_data["vs2"]["size_multiplier"] = fraction_sew

    ####################################################################################

    register_overlap = True

    vreg_count = test_data.vec_regs.reg_count
    xreg_count = test_data.int_regs.reg_count
    freg_count = test_data.float_regs.reg_count

    xlen = test_data.config.xlen
    flen = test_data.config.flen

    if no_overlap == []:
        register_overlap = False

        vector_register_data["vs3"] = randomizeRegister(
            instruction, eew, "vs3", vreg_count, vector_register_preset_data, xlen, flen, lmul
        )
        vector_register_data["vd"] = randomizeRegister(
            instruction, eew, "vd", vreg_count, vector_register_preset_data, xlen, flen, lmul
        )
        vector_register_data["vs1"] = randomizeRegister(
            instruction, eew, "vs1", vreg_count, vector_register_preset_data, xlen, flen, lmul
        )
        vector_register_data["vs2"] = randomizeRegister(
            instruction, eew, "vs2", vreg_count, vector_register_preset_data, xlen, flen, lmul
        )

        scalar_register_data["rd"] = randomizeRegister(
            instruction,
            eew,
            "rd",
            xreg_count,
            scalar_register_preset_data,
            xlen,
            flen,
        )
        scalar_register_data["rs1"] = randomizeRegister(
            instruction, eew, "rs1", xreg_count, scalar_register_preset_data, xlen, flen
        )
        scalar_register_data["rs2"] = randomizeRegister(
            instruction, eew, "rs2", xreg_count, scalar_register_preset_data, xlen, flen
        )

        floating_point_register_data["fd"] = randomizeRegister(
            instruction, eew, "fd", freg_count, floating_point_register_preset_data, xlen, flen
        )
        floating_point_register_data["fs1"] = randomizeRegister(
            instruction, eew, "fs1", freg_count, floating_point_register_preset_data, xlen, flen
        )

    ####################################################################################
    # check and resolve and register overlap
    ####################################################################################

    randomization_count = 0

    while register_overlap:
        vector_register_data["vs3"] = randomizeRegister(
            instruction, eew, "vs3", vreg_count, vector_register_preset_data, xlen, flen, lmul
        )
        vector_register_data["vd"] = randomizeRegister(
            instruction, eew, "vd", vreg_count, vector_register_preset_data, xlen, flen, lmul
        )
        vector_register_data["vs1"] = randomizeRegister(
            instruction, eew, "vs1", vreg_count, vector_register_preset_data, xlen, flen, lmul
        )
        vector_register_data["vs2"] = randomizeRegister(
            instruction, eew, "vs2", vreg_count, vector_register_preset_data, xlen, flen, lmul
        )

        scalar_register_data["rd"] = randomizeRegister(
            instruction, eew, "rd", xreg_count, scalar_register_preset_data, xlen, flen
        )
        scalar_register_data["rs1"] = randomizeRegister(
            instruction, eew, "rs1", xreg_count, scalar_register_preset_data, xlen, flen
        )
        scalar_register_data["rs2"] = randomizeRegister(
            instruction, eew, "rs2", xreg_count, scalar_register_preset_data, xlen, flen
        )

        floating_point_register_data["fd"] = randomizeRegister(
            instruction, eew, "fd", freg_count, floating_point_register_preset_data, xlen, flen
        )
        floating_point_register_data["fs1"] = randomizeRegister(
            instruction, eew, "fs1", freg_count, floating_point_register_preset_data, xlen, flen
        )

        register_overlap = False
        for no_overlap_set in no_overlap:
            register_type = no_overlap_set[0][0]  # grab either "v" "r" or "f" to get the register type
            registers_occupied = []

            for register in no_overlap_set:
                if not register_type == register[0]:
                    raise TypeError(f"Register type mismatch from {register_type}: '{register}'")
                elif register_type == "r":
                    registers_occupied.append(
                        scalar_register_data[register]["reg"]
                    )  # add register value to list to check for overlap
                elif register_type == "f":
                    registers_occupied.append(
                        floating_point_register_data[register]["reg"]
                    )  # add register to reserved list to prevent overlap
                elif register_type == "v":
                    if register == "v0":
                        registers_occupied.append(0)
                    else:
                        top_no_overlap = False
                        if register[-4:] == "_top":  # if specifying no overlap with the top of a register
                            top_no_overlap = True  # save for reserved section below
                            register = register[:-4]  # remove "_top" from register name

                        bottom_no_overlap = False
                        if register[-7:] == "_bottom":  # if specifying no overlap with the bottom of a register
                            bottom_no_overlap = True  # save for reserved section below
                            register = register[:-7]  # remove "_bottom" from register name

                        start_no_overlap = False
                        if (
                            register[-6:] == "_start"
                        ):  # if specifying no overlap with the initial register of a group (single register v)
                            start_no_overlap = True  # save for reserved section below
                            register = register[:-6]  # remove "_start" from register name

                        smallest_emul = int(
                            lmul * min(register["size_multiplier"] for register in vector_register_preset_data.values())
                        )
                        emul = (
                            math.ceil(vector_register_preset_data[register]["size_multiplier"] * lmul)
                            * vector_register_preset_data[register]["segments"]
                        )  # segment instructions take up consecutive registers even when lmul < 1

                        if (
                            start_no_overlap
                            or vector_register_preset_data[register]["reg_type"] == "scalar"
                            or vector_register_preset_data[register]["reg_type"] == "mask"
                            or emul < 1
                        ):
                            start_no_register_overlap = 0
                            end_register_no_overlap = 1
                        else:
                            start_no_register_overlap = smallest_emul if top_no_overlap and smallest_emul >= 1 else 0
                            end_register_no_overlap = (
                                emul - smallest_emul if bottom_no_overlap and smallest_emul >= 1 else emul
                            )  # need to include nfields (there is no bottom or top overlap allowed)
                        for i in range(start_no_register_overlap, end_register_no_overlap):
                            registers_occupied.append(
                                vector_register_data[register]["reg"] + i
                            )  # add register to reserved list to prevent overlap

            if len(registers_occupied) != len(set(registers_occupied)):  # checks for duplicates
                register_overlap = True

        max_randomization_count = 1000
        if randomization_count >= max_randomization_count:
            raise ValueError(
                f'No Overlap constraint "{no_overlap}" cannot be met for instruction "{instruction}" with sew "{sew}" and lmul "{lmul}" after {max_randomization_count} attempts'
            )
        randomization_count = randomization_count + 1

    ####################################################################################
    if test_count is not None and suite is not None:
        if vector_register_data["vs3"]["val_pointer"] is None:
            vector_register_data["vs3"]["val_pointer"] = f"vs3_random_{suite}_{test_count:03d}"
        if vector_register_data["vd"]["val_pointer"] is None:
            vector_register_data["vd"]["val_pointer"] = f"vd_random_{suite}_{test_count:03d}"
        if vector_register_data["vs1"]["val_pointer"] is None:
            vector_register_data["vs1"]["val_pointer"] = f"vs1_random_{suite}_{test_count:03d}"
        if vector_register_data["vs2"]["val_pointer"] is None:
            vector_register_data["vs2"]["val_pointer"] = f"vs2_random_{suite}_{test_count:03d}"

        if scalar_register_data["rs1"]["val_pointer"] is None:
            scalar_register_data["rs1"]["val_pointer"] = f"vd_load_random_{suite}_{test_count:03d}"

    # TODO : implement floating point data address

    # immediate handling
    if immediate_preset_data is None:
        immval = random.randint(0, 31) if instruction in imm_31 else random.randint(-16, 15)
    else:
        immval = immediate_preset_data

    # Turn it into instruction params
    params = InstructionParams()

    # Vector Registers
    params.vs1 = vector_register_data["vs1"]["reg"]
    params.vs1_val = vector_register_data["vs1"]["val"]
    params.vs1_val_pointer = vector_register_data["vs1"]["val_pointer"]
    params.vs1_size_multiplier = vector_register_data["vs1"]["size_multiplier"]
    params.vs1_segments = vector_register_data["vs1"]["segments"]
    params.vs1_type = vector_register_data["vs1"]["reg_type"]
    params.vs2 = vector_register_data["vs2"]["reg"]
    params.vs2_val = vector_register_data["vs2"]["val"]
    params.vs2_val_pointer = vector_register_data["vs2"]["val_pointer"]
    params.vs2_size_multiplier = vector_register_data["vs2"]["size_multiplier"]
    params.vs2_segments = vector_register_data["vs2"]["segments"]
    params.vs2_type = vector_register_data["vs2"]["reg_type"]
    params.vs3 = vector_register_data["vs3"]["reg"]
    params.vs3_val = vector_register_data["vs3"]["val"]
    params.vs3_val_pointer = vector_register_data["vs3"]["val_pointer"]
    params.vs3_size_multiplier = vector_register_data["vs3"]["size_multiplier"]
    params.vs3_segments = vector_register_data["vs3"]["segments"]
    params.vs3_type = vector_register_data["vs3"]["reg_type"]
    params.vd = vector_register_data["vd"]["reg"]
    params.vd_val = vector_register_data["vd"]["val"]
    params.vd_val_pointer = vector_register_data["vd"]["val_pointer"]
    params.vd_size_multiplier = vector_register_data["vd"]["size_multiplier"]
    params.vd_segments = vector_register_data["vd"]["segments"]
    params.vd_type = vector_register_data["vd"]["reg_type"]

    # Scalar Registers
    params.rd = scalar_register_data["rd"]["reg"]
    params.rdval = scalar_register_data["rd"]["val"]
    params.rs1 = scalar_register_data["rs1"]["reg"]
    params.rs1val = scalar_register_data["rs1"]["val"]
    params.rs1val_pointer = scalar_register_data["rs1"]["val_pointer"]
    params.rs2 = scalar_register_data["rs2"]["reg"]
    params.rs2val = scalar_register_data["rs2"]["val"]

    # Float Registers
    params.fd = floating_point_register_data["fd"]["reg"]
    params.fdval = floating_point_register_data["fd"]["val"]
    params.fs1 = floating_point_register_data["fs1"]["reg"]
    params.fs1val = floating_point_register_data["fs1"]["val"]

    # Immediate
    params.immval = immval

    params.temp_reg = test_data.int_regs.get_register()
    params.sew = sew
    params.lmul = lmul

    return params
