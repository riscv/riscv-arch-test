##################################
# priv/extensions/InterruptsH.py
#
# InterruptsH privileged test generator: hstatus.VGEIN switching and the VS-level interrupt aliases.
# David_Harris@hmc.edu 8 November 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""InterruptsH test generator.

The tests boot to HS-mode and set hideleg = 0x444 and hie = hgeie = 0, so no VS-level interrupt is ever pending and
enabled where it could be taken.  Boot leaves menvcfg.STCE = henvcfg.STCE = 0, so hip.VSTIP comes from hvip alone.

cp_vgein_switch*: guest external interrupt 3 is pending and the other guest files are idle.  Each csrrw, csrrs or
csrrc of hstatus moves VGEIN between 0, an idle file and file 3, and hip.VSEIP must follow hgeip[VGEIN] after every
write.

cp_vs_int_alias*: each single-bit set or clear of VSSIP, VSTIP or VSEIP in vsip or vsie (VS-mode), hvip, hip or hie
(HS-mode), and mip or mie (M-mode, through T-SBI), followed by reads of every alias.
"""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

_CG = "InterruptsH_cg"
_PENDING = 3  # the pending guest external interrupt
_SGEI_GATE = "defined(RVTEST_SGEI_INTR_IMPL) && UDB_NUM_EXTERNAL_GUEST_INTERRUPTS >= 3"
_GEILEN7_GATE = "UDB_NUM_EXTERNAL_GUEST_INTERRUPTS >= 7"


def _setup(reg: int) -> list[str]:
    return [
        f"LI(x{reg}, MIP_VS_MASK)",
        f"csrw hideleg, x{reg}",
        "csrw hie, zero",
        "csrw hvip, zero",
        "csrw hgeie, zero",
    ]


def _teardown() -> list[str]:
    return ["csrw hvip, zero", "csrw hie, zero", "csrw hideleg, zero"]


# (form, coverpoint, old VGEIN, new VGEIN, operand, gate): csrrw writes hstatus with VGEIN = new; csrrs and csrrc
# set or clear the operand's VGEIN bits
_VGEIN_CASES = (
    ("csrrw", "cp_vgein_switch_csrrw", 3, 0, 0, None),
    ("csrrw", "cp_vgein_switch_csrrw", 3, 1, 1, None),
    ("csrrw", "cp_vgein_switch_csrrw", 0, 3, 3, None),
    ("csrrw", "cp_vgein_switch_csrrw", 1, 3, 3, None),
    ("csrrs", "cp_vgein_switch_csrrs", 0, 3, 3, None),
    ("csrrs", "cp_vgein_switch_csrrs", 1, 3, 2, None),
    ("csrrs", "cp_vgein_switch_csrrs", 3, 7, 4, _GEILEN7_GATE),
    ("csrrc", "cp_vgein_switch_csrrc", 3, 0, 3, None),
    ("csrrc", "cp_vgein_switch_csrrc", 3, 1, 2, None),
    ("csrrc", "cp_vgein_switch_csrrc", 7, 3, 4, _GEILEN7_GATE),
)


def _set_vgein(value: int, base: int, tmp: int) -> list[str]:
    """x{base} = hstatus with VGEIN = value."""
    return [
        f"csrr x{base}, hstatus",
        f"LI(x{tmp}, HSTATUS_VGEIN)",
        f"not x{tmp}, x{tmp}",
        f"and x{base}, x{base}, x{tmp}",
        *([f"LI(x{tmp}, {value} << 12)", f"or x{base}, x{base}, x{tmp}"] if value else []),
    ]


def _vgein_tests(test_data: TestData) -> list[str]:
    base, tmp, rd, save = test_data.int_regs.get_registers(4)
    lines = [
        comment_banner(
            "cp_vgein_switch_csrrw, cp_vgein_switch_csrrs, cp_vgein_switch_csrrc",
            f"Guest external interrupt {_PENDING} is pending and the other guest files are idle.  Move hstatus.VGEIN\n"
            "between 0, an idle file and the pending file with csrrw, csrrs and csrrc, and read hip after each write:\n"
            "hip.VSEIP = hgeip[VGEIN], and 0 when VGEIN = 0",
        ),
        f"#if {_SGEI_GATE}",
        f"csrr x{save}, hstatus",
        *_setup(tmp),
        f"RVTEST_SET_GUEST_EXT_INT_S({_PENDING})",
    ]
    for form, coverpoint, old, new, operand, gate in _VGEIN_CASES:
        name = f"{form}_{old}_to_{new}"
        body = [*_set_vgein(old, base, tmp), f"csrw hstatus, x{base}"]
        if form == "csrrw":
            body.extend(_set_vgein(new, base, tmp))
        else:
            body.append(f"LI(x{base}, {operand} << 12)")
        body.extend(
            [
                test_data.add_testcase(name, coverpoint, _CG),
                f"{form} x0, hstatus, x{base}",
                f"csrr x{rd}, hip",
                f"LI(x{tmp}, MIP_VSEIP | MIP_SGEIP)",
                f"and x{rd}, x{rd}, x{tmp}",
                write_sigupd(rd, test_data),
            ]
        )
        lines.extend(body if gate is None else [f"#if {gate}", *body, f"#endif // {gate}"])
    lines.extend(
        [
            f"csrw hstatus, x{save}",
            f"RVTEST_CLR_GUEST_EXT_INT_S({_PENDING})",
            *_teardown(),
            f"#endif // {_SGEI_GATE}",
        ]
    )
    test_data.int_regs.return_registers([base, tmp, rd, save])
    return lines


# VS-level bits as hvip, hip, hie, mip and mie hold them; vsip and vsie hold them one bit lower
_VS_BITS = {"vssi": "MIP_VSSIP", "vsti": "MIP_VSTIP", "vsei": "MIP_VSEIP"}


def _read_aliases(test_data: TestData, rd: int, mask_reg: int, name: str, coverpoint: str) -> list[str]:
    """In HS-mode, record every copy of the VS-level interrupt bits."""
    lines = [f"LI(x{mask_reg}, MIP_VS_MASK)"]
    for csr in ("hvip", "hip", "hie"):
        lines.extend(
            [
                test_data.add_testcase(f"{name}_{csr}", coverpoint, _CG),
                f"csrr x{rd}, {csr}",
                f"and x{rd}, x{rd}, x{mask_reg}",
                write_sigupd(rd, test_data),
            ]
        )
    for csr in ("CSR_MIP", "CSR_MIE"):
        lines.extend(
            [
                test_data.add_testcase(f"{name}_{csr[4:].lower()}", coverpoint, _CG),
                f"RVTEST_TSBI_CSR_READ({csr})",
                f"and x{rd}, a0, x{mask_reg}",
                write_sigupd(rd, test_data),
            ]
        )
    lines.append(f"srli x{mask_reg}, x{mask_reg}, 1")
    for csr in ("vsip", "vsie"):
        lines.extend(
            [
                test_data.add_testcase(f"{name}_{csr}", coverpoint, _CG),
                f"csrr x{rd}, {csr}",
                f"and x{rd}, x{rd}, x{mask_reg}",
                write_sigupd(rd, test_data),
            ]
        )
    return lines


def _alias_tests(test_data: TestData) -> list[str]:
    rd, mask_reg, bit_reg = test_data.int_regs.get_registers(3)
    lines = [
        comment_banner(
            "cp_vs_int_alias_vs, cp_vs_int_alias_hs, cp_vs_int_alias_m",
            "Set and clear each of VSSIP, VSTIP and VSEIP alone in vsip and vsie from VS-mode (as sip and sie,\n"
            "one bit lower), in hvip, hip and hie from HS-mode, and in mip and mie from M-mode.  Before a clear, HS-mode\n"
            "sets the bit in hvip or hie.  Read hvip, hip, hie, mip, mie, vsip and vsie after each write",
        ),
        *_setup(rd),
    ]
    # (mode, CSR the instruction names, family): the family's canonical HS-mode CSR sets the bit before a clear
    targets = (
        ("VS", "sip", "hvip"),
        ("VS", "sie", "hie"),
        ("HS", "hvip", "hvip"),
        ("HS", "hip", "hvip"),
        ("HS", "hie", "hie"),
        ("M", "mip", "hvip"),
        ("M", "mie", "hie"),
    )
    for mode, csr, family in targets:
        coverpoint = f"cp_vs_int_alias_{mode.lower()}"
        for bit, mask in _VS_BITS.items():
            operand = f"({mask} >> 1)" if mode == "VS" else mask
            for op in ("csrs", "csrc"):
                name = f"{mode.lower()}_{csr}_{op}_{bit}"
                lines.extend(["", f"# {op} {bit} in {csr} from {mode}-mode", "csrw hvip, zero", "csrw hie, zero"])
                if op == "csrc":
                    lines.extend([f"LI(x{bit_reg}, {mask})", f"csrs {family}, x{bit_reg}"])
                if mode == "M":
                    tsbi = "SET" if op == "csrs" else "CLEAR"
                    lines.extend(
                        [
                            test_data.add_testcase(name, coverpoint, _CG),
                            f"RVTEST_TSBI_CSR_{tsbi}(CSR_{csr.upper()}, {mask})",
                        ]
                    )
                else:
                    lines.extend(
                        [
                            f"LI(x{bit_reg}, {operand})",
                            *(["RVTEST_TSBI_GOTO_VSMODE"] if mode == "VS" else []),
                            test_data.add_testcase(name, coverpoint, _CG),
                            f"{op} {csr}, x{bit_reg}",
                            *(["RVTEST_TSBI_GOTO_SMODE"] if mode == "VS" else []),
                        ]
                    )
                lines.extend(_read_aliases(test_data, rd, mask_reg, name, coverpoint))
    lines.extend(_teardown())
    test_data.int_regs.return_registers([rd, mask_reg, bit_reg])
    return lines


@add_priv_test_generator("InterruptsH", required_extensions=["H"], extra_defines=["#define BOOT_TO_SMODE"])
def make_interruptsh(test_data: TestData) -> list[TestChunk]:
    """Generate the InterruptsH tests: VGEIN switching and the VS-level interrupt aliases."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk("vgein")
    tc.code.extend(_vgein_tests(test_data))
    test_chunks.append(test_data.end_test_chunk())
    tc = test_data.begin_test_chunk("alias")
    tc.code.extend(_alias_tests(test_data))
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
