##################################
# priv/extensions/pmp/probes.py
#
# PMP access probes used by privileged test generators.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate PMP access probes and register their testcases."""

from collections.abc import Callable
from typing import Literal

from testgen.asm.helpers import write_sigupd
from testgen.data.state import TestData

_OFFSETS = ("address", "address-4", "address+4", "address+g-4", "address+g")
_AMOS = ("amoadd", "amoand", "amoor", "amoxor", "amomax", "amomaxu", "amomin", "amominu", "amoswap")

#: The covergroup cross a probe's testcase belongs to: a name, or a function of the probe's instruction.
Cross = str | Callable[[str], str]


def cross_by_access(
    *, load: str, store: str, execute: str = "", lw: str | None = None, sw: str | None = None
) -> Callable[[str], str]:
    """Name the cross for a load, store or jalr probe. ``lw`` and ``sw`` name the crosses for those two
    instructions when the covergroup samples them apart from the other widths."""

    def name(instruction: str) -> str:
        if instruction.endswith("jalr"):
            return execute
        if instruction == "lw" and lw:
            return lw
        if instruction == "sw" and sw:
            return sw
        return store if instruction.removeprefix("c.").startswith(("s", "fs")) else load

    return name


def _testcase(test_data: TestData, name: str, coverpoint: Cross, instruction: str) -> str:
    cross = coverpoint if isinstance(coverpoint, str) else coverpoint(instruction)
    return test_data.add_testcase(name, cross, f"{test_data.testsuite}_cg")


def gen_rwx(test_data: TestData, case: str, coverpoint: Cross, region: str = "TEST_FOR_EXECUTION") -> list[str]:
    return [
        "",
        "RVTEST_FENCEI",
        f"LA(a4, {region})",
        "LA(ra, 1f)",
        _testcase(test_data, f"{case}_1_jalr", coverpoint, "jalr"),
        "jalr x0, 0(a4)",
        "1:",
        write_sigupd(14, test_data),
        f"LA(a5, {region})",
        "LI(a4, RVTEST_PMP_RET_ENCODING)",
        _testcase(test_data, f"{case}_2_sw", coverpoint, "sw"),
        "sw a4, 0(a5)",
        write_sigupd(14, test_data),
        _testcase(test_data, f"{case}_3_lw", coverpoint, "lw"),
        "lw a4, 0(a5)",
        write_sigupd(14, test_data),
    ]


def gen_rwx_mprv(test_data: TestData, case: str, coverpoint: Cross, bits: str) -> list[str]:
    def arm(value: str) -> str:
        return "\n".join(
            [
                "LI(t0, (1 << 17) | (3 << 11))",
                "csrc mstatus, t0",
                f"LI(t0, {value})",
                "csrs mstatus, t0",
            ]
        )

    return [
        "",
        "RVTEST_FENCEI",
        "LA(a4, TEST_FOR_EXECUTION)",
        arm(bits),
        "LA(ra, 1f)",
        _testcase(test_data, f"{case}_1_jalr", coverpoint, "jalr"),
        "jalr x0, 0(a4)",
        "1:",
        write_sigupd(14, test_data),
        "LA(a5, TEST_FOR_EXECUTION)",
        "LI(a4, RVTEST_PMP_RET_ENCODING)",
        arm(bits),
        _testcase(test_data, f"{case}_2_sw", coverpoint, "sw"),
        "sw a4, 0(a5)",
        write_sigupd(14, test_data),
        arm(bits),
        _testcase(test_data, f"{case}_3_lw", coverpoint, "lw"),
        "lw a4, 0(a5)",
        write_sigupd(14, test_data),
        arm("0"),
    ]


def gen_lw_bounds(test_data: TestData, case: str, coverpoint: Cross, region: str, beyond: str) -> list[str]:
    return [
        "",
        f"LA(a5, {region})",
        _testcase(test_data, f"{case}_1_lw_address", coverpoint, "lw"),
        "lw a4, 0(a5)",
        write_sigupd(14, test_data),
        "addi a5, a5, -4",
        _testcase(test_data, f"{case}_2_lw_address-4", coverpoint, "lw"),
        "lw a4, 0(a5)",
        write_sigupd(14, test_data),
        f"LI(t0, ({beyond}) + 4)",
        "add a5, a5, t0",
        _testcase(test_data, f"{case}_3_lw_beyond", coverpoint, "lw"),
        "lw a4, 0(a5)",
        write_sigupd(14, test_data),
    ]


def gen_rwx_all(test_data: TestData, case: str, coverpoint: Cross, region: str = "TEST_FOR_EXECUTION") -> list[str]:
    instructions = ("sb", "sh", "sw", "sd", "lb", "lbu", "lh", "lhu", "lw", "lwu", "ld")
    lines = [
        "",
        "// Execute probe",
        "RVTEST_FENCEI",
        f"LA(a4, {region})",
        "LA(ra, 1f)",
        _testcase(test_data, f"{case}_12_jalr", coverpoint, "jalr"),
        "jalr x0, 0(a4)",
        "1:",
        write_sigupd(14, test_data),
        "",
        "// Load and store probes",
        f"LA(a5, {region})",
        "LI(a4, RVTEST_PMP_RET_ENCODING)",
    ]
    for number, instruction in enumerate(instructions, start=1):
        rv64_only = instruction in ("sd", "lwu", "ld")
        if rv64_only:
            lines.append("#if __riscv_xlen == 64")
        lines.extend(
            [
                _testcase(test_data, f"{case}_{number}_{instruction}", coverpoint, instruction),
                f"{instruction} a4, 0(a5)",
                write_sigupd(14, test_data),
            ]
        )
        if rv64_only:
            lines.append("#endif")
    return lines


def gen_rwx_na4(test_data: TestData, case: str, coverpoint: Cross, region: str = "TEST_FOR_EXECUTION") -> list[str]:
    lines = [
        "",
        "RVTEST_FENCEI",
        f"LA(a4, {region})",
        "LA(ra, 1f)",
        _testcase(test_data, f"{case}_1_jalr_{_OFFSETS[0]}", coverpoint, "jalr"),
        "jalr x0, 0(a4)",
        "1:",
        write_sigupd(14, test_data),
    ]
    for number, (adjustment, offset) in enumerate(zip((-4, 8), _OFFSETS[1:3], strict=True), start=2):
        lines.extend(
            [
                f"addi a4, a4, {adjustment}",
                f"LA(ra, {number}f)",
                _testcase(test_data, f"{case}_{number}_jalr_{offset}", coverpoint, "jalr"),
                "jalr x0, 0(a4)",
                f"{number}:",
                write_sigupd(14, test_data),
            ]
        )
    lines.extend([f"LA(a5, {region})", "LI(a4, RVTEST_PMP_RET_ENCODING)"])
    probes = zip((0, 0, -4, 0, 8, 0), ("sw", "lw") * 3, (offset for offset in _OFFSETS[:3] for _ in range(2)))
    for number, (adjustment, instruction, offset) in enumerate(probes, start=4):
        if adjustment:
            lines.append(f"addi a5, a5, {adjustment}")
        lines.extend(
            [
                _testcase(test_data, f"{case}_{number}_{instruction}_{offset}", coverpoint, instruction),
                f"{instruction} a4, 0(a5)",
                write_sigupd(14, test_data),
            ]
        )
    return lines


def gen_rwx_legal(test_data: TestData, case: str, coverpoint: Cross, region: str = "TEST_FOR_EXECUTION") -> list[str]:
    lines = [
        "",
        "RVTEST_FENCEI",
        "LI(t0, PMP_TOR_REGION_BYTES - 8)",
        "",
        "// Execute probes",
        f"LA(a4, {region})",
    ]
    execute_adjustments = (None, "addi a4, a4, -4", "addi a4, a4, 8", "add a4, a4, t0", "addi a4, a4, 4")
    for number, (adjustment, offset) in enumerate(zip(execute_adjustments, _OFFSETS, strict=True), start=1):
        if adjustment:
            lines.append(adjustment)
        lines.extend(
            [
                f"LA(ra, {number}f)",
                _testcase(test_data, f"{case}_{number}_jalr_{offset}", coverpoint, "jalr"),
                "jalr x0, 0(a4)",
                f"{number}:",
                write_sigupd(14, test_data),
            ]
        )
    data_adjustments = (None, "addi a5, a5, -4", "addi a5, a5, 8", "add a5, a5, t0", "addi a5, a5, 4")
    for instruction, first in (("sw", 6), ("lw", 11)):
        operation = "Store" if instruction == "sw" else "Load"
        lines.extend(["", f"// {operation} probes", f"LA(a5, {region})"])
        if instruction == "sw":
            lines.append("LI(a4, RVTEST_PMP_RET_ENCODING)")
        for number, (adjustment, offset) in enumerate(zip(data_adjustments, _OFFSETS, strict=True), start=first):
            if adjustment:
                lines.append(adjustment)
            lines.extend(
                [
                    _testcase(test_data, f"{case}_{number}_{instruction}_{offset}", coverpoint, instruction),
                    f"{instruction} a4, 0(a5)",
                    write_sigupd(14, test_data),
                ]
            )
    return lines


def gen_rwx_napot(test_data: TestData, case: str, coverpoint: Cross, region: str = "TEST_FOR_EXECUTION") -> list[str]:
    names = (
        "sb_address",
        "sh_address",
        *(f"sw_{offset}" for offset in _OFFSETS),
        "lb_address",
        "lbu_address",
        "lh_address",
        "lhu_address",
        *(f"lw_{offset}" for offset in _OFFSETS),
        *(f"jalr_{offset}" for offset in _OFFSETS),
    )
    names += ("sd_address", "ld_address", "lwu_address")
    lines = [
        "",
        "RVTEST_FENCEI",
        "LI(t0, PMP_NAPOT_REGION_BYTES - 8)",
        "",
        "// Execute probes",
        f"LA(a4, {region})",
    ]
    for resume, (adjustment, name) in enumerate(
        zip(
            (None, "addi a4, a4, -4", "addi a4, a4, 8", "add a4, a4, t0", "addi a4, a4, 4"),
            names[16:21],
            strict=True,
        ),
        1,
    ):
        if adjustment:
            lines.append(adjustment)
        lines.extend(
            [
                f"LA(ra, {resume}f)",
                _testcase(test_data, f"{case}_{resume + 16}_{name}", coverpoint, name.split("_")[0]),
                "jalr x0, 0(a4)",
                f"{resume}:",
                write_sigupd(14, test_data),
            ]
        )
    lines.extend(["", "// Store probes", f"LA(a5, {region})", "LI(a4, RVTEST_PMP_RET_ENCODING)"])
    for number, (instruction, name) in enumerate(zip(("sb", "sh", "sw"), names[:3], strict=True), start=1):
        lines.extend(
            [
                _testcase(test_data, f"{case}_{number}_{name}", coverpoint, name.split("_")[0]),
                f"{instruction} a4, 0(a5)",
                write_sigupd(14, test_data),
            ]
        )
    for number, (adjustment, name) in enumerate(
        zip(
            ("addi a5, a5, -4", "addi a5, a5, 8", "add a5, a5, t0", "addi a5, a5, 4"),
            names[3:7],
            strict=True,
        ),
        start=4,
    ):
        lines.extend(
            [
                adjustment,
                _testcase(test_data, f"{case}_{number}_{name}", coverpoint, name.split("_")[0]),
                "sw a4, 0(a5)",
                write_sigupd(14, test_data),
            ]
        )
    lines.extend(["", "// Load probes", f"LA(a5, {region})"])
    for number, (instruction, name) in enumerate(
        zip(("lb", "lbu", "lh", "lhu", "lw"), names[7:12], strict=True), start=8
    ):
        lines.extend(
            [
                _testcase(test_data, f"{case}_{number}_{name}", coverpoint, name.split("_")[0]),
                f"{instruction} a4, 0(a5)",
                write_sigupd(14, test_data),
            ]
        )
    for number, (adjustment, name) in enumerate(
        zip(
            ("addi a5, a5, -4", "addi a5, a5, 8", "add a5, a5, t0", "addi a5, a5, 4"),
            names[12:16],
            strict=True,
        ),
        start=13,
    ):
        lines.extend(
            [
                adjustment,
                _testcase(test_data, f"{case}_{number}_{name}", coverpoint, name.split("_")[0]),
                "lw a4, 0(a5)",
                write_sigupd(14, test_data),
            ]
        )
    lines.extend(
        [
            "#if __riscv_xlen == 64",
            f"LA(a5, {region})",
            _testcase(test_data, f"{case}_22_{names[21]}", coverpoint, "sd"),
            "sd a4, 0(a5)",
            write_sigupd(14, test_data),
            _testcase(test_data, f"{case}_23_{names[22]}", coverpoint, "ld"),
            "ld a4, 0(a5)",
            write_sigupd(14, test_data),
            _testcase(test_data, f"{case}_24_{names[23]}", coverpoint, "lwu"),
            "lwu a4, 0(a5)",
            write_sigupd(14, test_data),
            "#endif",
        ]
    )
    return lines


def gen_rwx_tor_bot(test_data: TestData, case: str, coverpoint: Cross, region: str = "TEST_FOR_EXECUTION") -> list[str]:
    locations = ("bot-4", "bot", "top-4", "top")
    lines = [
        "",
        "RVTEST_FENCEI",
        "LI(t0, PMP_TOR_REGION_BYTES - 8)",
        "",
        "// Store probes",
        f"LA(a5, {region})",
        "LI(a4, RVTEST_PMP_RET_ENCODING)",
    ]
    adjustments = (
        "addi a5, a5, -4",
        "addi a5, a5, 4",
        "add a5, a5, t0\naddi a5, a5, 4",
        "addi a5, a5, 4",
    )
    for instruction, first in (("sw", 1), ("lw", 5)):
        if instruction == "lw":
            lines.extend(["", "// Load probes", f"LA(a5, {region})"])
        for number, (adjustment, location) in enumerate(zip(adjustments, locations, strict=True), start=first):
            lines.extend(
                [
                    adjustment,
                    _testcase(test_data, f"{case}_{number}_{instruction}_{location}", coverpoint, instruction),
                    f"{instruction} a4, 0(a5)",
                    write_sigupd(14, test_data),
                ]
            )
    lines.extend(["", "// Execute probes", f"LA(a4, {region})"])
    for resume, (adjustment, location) in enumerate(zip(adjustments, locations, strict=True), 1):
        lines.extend(
            [
                adjustment.replace("a5", "a4"),
                f"LA(ra, {resume}f)",
                _testcase(test_data, f"{case}_{resume + 8}_jalr_{location}", coverpoint, "jalr"),
                "jalr x0, 0(a4)",
                f"{resume}:",
                write_sigupd(14, test_data),
            ]
        )
    return lines


def gen_rwx_tor_zero(
    test_data: TestData, case: str, coverpoint: Cross, region: str = "TEST_FOR_EXECUTION"
) -> list[str]:
    return [
        "",
        "// Store probes",
        f"LA(a5, {region})",
        "LI(a4, RVTEST_PMP_RET_ENCODING)",
        _testcase(test_data, f"{case}_1_sw_top", coverpoint, "sw"),
        "sw a4, 0(a5)",
        write_sigupd(14, test_data),
        "addi a5, a5, -4",
        _testcase(test_data, f"{case}_2_sw_top-4", coverpoint, "sw"),
        "sw a4, 0(a5)",
        write_sigupd(14, test_data),
        "LI(a5, 0)",
        _testcase(test_data, f"{case}_3_sw_zero", coverpoint, "sw"),
        "sw a4, 0(a5)",
        write_sigupd(14, test_data),
        "",
        "// Load probes",
        f"LA(a5, {region})",
        _testcase(test_data, f"{case}_4_lw_top", coverpoint, "lw"),
        "lw a4, 0(a5)",
        write_sigupd(14, test_data),
        "addi a5, a5, -4",
        _testcase(test_data, f"{case}_5_lw_top-4", coverpoint, "lw"),
        "lw a4, 0(a5)",
        write_sigupd(14, test_data),
        "LI(a5, 0)",
        _testcase(test_data, f"{case}_6_lw_zero", coverpoint, "lw"),
        "lw a4, 0(a5)",
        write_sigupd(14, test_data),
        "",
        "// Execute probes",
        "RVTEST_FENCEI",
        f"LA(a4, {region})",
        "LA(ra, 1f)",
        _testcase(test_data, f"{case}_7_jalr_top", coverpoint, "jalr"),
        "jalr x0, 0(a4)",
        "1:",
        write_sigupd(14, test_data),
        "addi a4, a4, -4",
        "LA(ra, 2f)",
        _testcase(test_data, f"{case}_8_jalr_top-4", coverpoint, "jalr"),
        "jalr x0, 0(a4)",
        "2:",
        write_sigupd(14, test_data),
        "LI(a5, 0)",
        "LA(ra, 3f)",
        _testcase(test_data, f"{case}_9_jalr_zero", coverpoint, "jalr"),
        "jalr x0, 0(a5)",
        "3:",
        write_sigupd(14, test_data),
    ]


def gen_float(test_data: TestData, case: str, coverpoint: Cross, region: str = "TEST_FOR_EXECUTION") -> list[str]:
    instructions = (
        ("fsh", "#ifdef ZFHMIN_SUPPORTED"),
        ("fsw", None),
        ("fsd", "#ifdef D_SUPPORTED"),
        ("flh", "#ifdef ZFHMIN_SUPPORTED"),
        ("flw", None),
        ("fld", "#ifdef D_SUPPORTED"),
    )
    lines = ["", f"LA(a5, {region})"]
    for number, (instruction, guard) in enumerate(instructions, start=1):
        if guard:
            lines.append(guard)
        lines.extend(
            [
                _testcase(test_data, f"{case}_{number}_{instruction}", coverpoint, instruction),
                f"{instruction} f14, 0(a5)",
                write_sigupd(14, test_data, "float"),
            ]
        )
        if guard:
            lines.append("#endif")
    return lines


def gen_amo(test_data: TestData, case: str, coverpoint: Cross, region: str = "TEST_FOR_EXECUTION") -> list[str]:
    operations = tuple((amo, width) for amo in _AMOS for width in ("w", "d"))
    lines = ["", "LI(a6, RVTEST_PMP_RET_ENCODING)", f"LA(a5, {region})"]
    for number, (operation, width) in enumerate(operations, start=1):
        if width == "d":
            lines.append("#if __riscv_xlen == 64")
        lines.append(
            "\n".join(
                [
                    _testcase(test_data, f"{case}_{number}_{operation}_{width}", coverpoint, f"{operation}.{width}"),
                    f"{operation}.{width} a4, a6, (a5)",
                    write_sigupd(14, test_data),
                ]
            )
        )
        if width == "d":
            lines.append("#endif")
    return lines


def gen_lrsc(
    test_data: TestData, case: str, coverpoint: Cross, region: str = "TEST_FOR_EXECUTION", *, retry: bool = False
) -> list[str]:
    widths = ("w", "d")
    lines = ["", f"LA(a5, {region})"]
    for offset, width in enumerate(widths):
        lr_testcase = f"{case}_{2 * offset + 1}_lr_{width}"
        sc_testcase = f"{case}_{2 * offset + 2}_sc_{width}"
        if width == "d":
            lines.append("#if __riscv_xlen == 64")
        if retry:
            tag = f"{case}_{width}"
            lines.extend(
                [
                    "LI(t2, 100)",
                    f"{tag}_retry:",
                    _testcase(test_data, lr_testcase, coverpoint, f"lr.{width}"),
                    f"lr.{width} a3, (a5)",
                ]
            )
            lr_sigupd = write_sigupd(13, test_data)
            lines.extend(
                [
                    _testcase(test_data, sc_testcase, coverpoint, f"sc.{width}"),
                    f"sc.{width} a2, a3, (a5)",
                    f"beqz a2, {tag}_success",
                    "addi t2, t2, -1",
                    f"bnez t2, {tag}_retry",
                    f"{tag}_success:",
                    lr_sigupd,
                    write_sigupd(12, test_data),
                ]
            )
        else:
            lines.append(
                "\n".join(
                    [
                        _testcase(test_data, lr_testcase, coverpoint, f"lr.{width}"),
                        f"lr.{width} a2, (a5)",
                        write_sigupd(12, test_data),
                        _testcase(test_data, sc_testcase, coverpoint, f"sc.{width}"),
                        f"sc.{width} a2, a2, (a5)",
                        write_sigupd(12, test_data),
                    ]
                )
            )
        if width == "d":
            lines.append("#endif")
    return lines


def gen_lrsc_success(
    test_data: TestData, case: str, coverpoint: Cross, region: str = "TEST_FOR_EXECUTION"
) -> list[str]:
    return gen_lrsc(test_data, case, coverpoint, region, retry=True)


def gen_compressed_execute(test_data: TestData, case: str, coverpoint: Cross, region: str) -> list[str]:
    return [
        "",
        f"LA(x15, {region})",
        _testcase(test_data, f"{case}_1_c.jalr", coverpoint, "c.jalr"),
        "c.jalr x15",
        write_sigupd(1, test_data),
    ]


def gen_cbo(test_data: TestData, case: str, coverpoint: Cross, region: str = "TEST_FOR_EXECUTION") -> list[str]:
    instructions = ("cbo.zero", "cbo.clean", "cbo.flush", "cbo.inval")
    lines = ["", f"LA(a4, {region})"]
    for number, instruction in enumerate(instructions, start=1):
        lines.extend(
            [
                _testcase(test_data, f"{case}_{number}_{instruction}", coverpoint, instruction),
                f"{instruction} (a4)",
                write_sigupd(14, test_data),
            ]
        )
    return lines


def gen_prefetch(test_data: TestData, case: str, coverpoint: Cross, region: str = "TEST_FOR_EXECUTION") -> list[str]:
    instructions = ("prefetch.i", "prefetch.r", "prefetch.w")
    lines = ["", f"LA(t0, {region})"]
    for number, instruction in enumerate(instructions, start=1):
        lines.extend(
            [
                _testcase(test_data, f"{case}_{number}_{instruction}", coverpoint, instruction),
                f"{instruction} 0(t0)",
                write_sigupd(14, test_data),
            ]
        )
    return lines


def _compressed_sp_probes(
    test_data: TestData,
    case: str,
    coverpoint: Cross,
    first: int,
    store: str,
    load: str,
    data_reg: str,
    check_reg: int,
    sig_type: Literal["int", "float"] = "int",
) -> str:
    lines = [
        "mv t0, sp",
        "addi sp, x8, 0",
        _testcase(test_data, f"{case}_{first}_{store}", coverpoint, store),
        f"{store} {data_reg}, 0(sp)",
        "mv sp, t0",
        write_sigupd(check_reg, test_data, sig_type),
        "mv t0, sp",
        "addi sp, x8, 0",
        _testcase(test_data, f"{case}_{first + 1}_{load}", coverpoint, load),
        f"{load} {data_reg}, 0(sp)",
        "mv sp, t0",
        write_sigupd(check_reg, test_data, sig_type),
    ]
    return "\n".join(lines)


def gen_zca(test_data: TestData, case: str, coverpoint: Cross, region: str = "TEST_FOR_EXECUTION") -> list[str]:
    lines = [
        "",
        "RVTEST_FENCEI",
        f"LA(x15, {region})",
        "LA(ra, 1f)",
        _testcase(test_data, f"{case}_3_c.jalr", coverpoint, "c.jalr"),
        "c.jalr x15",
        "1:",
        write_sigupd(1, test_data),
        "LI(x15, 0x00010001)",
        f"LA(x8, {region})",
        _testcase(test_data, f"{case}_1_c.sw", coverpoint, "c.sw"),
        "c.sw x15, 0(x8)",
        write_sigupd(15, test_data),
        _testcase(test_data, f"{case}_2_c.lw", coverpoint, "c.lw"),
        "c.lw x15, 0(x8)",
        write_sigupd(15, test_data),
        _compressed_sp_probes(test_data, case, coverpoint, 6, "c.swsp", "c.lwsp", "x15", 15),
        "#if __riscv_xlen == 64",
        "LI(x15, 0x0001000100010001)",
        _testcase(test_data, f"{case}_4_c.sd", coverpoint, "c.sd"),
        "c.sd x15, 0(x8)",
        write_sigupd(15, test_data),
        _testcase(test_data, f"{case}_5_c.ld", coverpoint, "c.ld"),
        "c.ld x15, 0(x8)",
        write_sigupd(15, test_data),
        _compressed_sp_probes(test_data, case, coverpoint, 8, "c.sdsp", "c.ldsp", "x15", 15),
        "#endif",
    ]
    return lines


def gen_zcb(test_data: TestData, case: str, coverpoint: Cross, region: str = "TEST_FOR_EXECUTION") -> list[str]:
    instructions = ("c.sb", "c.lbu", "c.sh", "c.lhu", "c.sh", "c.lh")
    lines = ["", "LI(x15, NOP)", f"LA(x8, {region})"]
    for number, instruction in enumerate(instructions, start=1):
        lines.extend(
            [
                _testcase(test_data, f"{case}_{number}_{instruction}", coverpoint, instruction),
                f"{instruction} x15, 0(x8)",
                write_sigupd(15, test_data),
            ]
        )
    return lines


def _gen_compressed_float(test_data: TestData, case: str, coverpoint: Cross, region: str, width: str) -> list[str]:
    store = f"c.fs{width}"
    load = f"c.fl{width}"
    return [
        "",
        "li x15, 0x3f800000",
        "fmv.w.x f8, x15",
        f"LA(x8, {region})",
        _testcase(test_data, f"{case}_1_{store}", coverpoint, store),
        f"{store} f8, 0(x8)",
        write_sigupd(8, test_data, "float"),
        _testcase(test_data, f"{case}_2_{load}", coverpoint, load),
        f"{load} f8, 0(x8)",
        write_sigupd(8, test_data, "float"),
        _compressed_sp_probes(test_data, case, coverpoint, 3, f"{store}sp", f"{load}sp", "f8", 8, "float"),
    ]


def gen_zcd(test_data: TestData, case: str, coverpoint: Cross, region: str = "TEST_FOR_EXECUTION") -> list[str]:
    return _gen_compressed_float(test_data, case, coverpoint, region, "d")


def gen_zcf(test_data: TestData, case: str, coverpoint: Cross, region: str = "TEST_FOR_EXECUTION") -> list[str]:
    return _gen_compressed_float(test_data, case, coverpoint, region, "w")


ProbeGenerator = Callable[[TestData, str, Cross, str], list[str]]
