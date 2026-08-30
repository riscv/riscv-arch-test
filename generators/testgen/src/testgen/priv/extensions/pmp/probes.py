##################################
# priv/extensions/pmp/probes.py
#
# PMP access probes used by privileged test generators.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate PMP access probes and register their testcases."""

from collections.abc import Callable

from testgen.data.state import TestData

_OFFSETS = ("address", "address-4", "address+4", "address+g-4", "address+g")
_AMOS = ("amoadd", "amoand", "amoor", "amoxor", "amomax", "amomaxu", "amomin", "amominu", "amoswap")
_RET_ENCODING = {32: "0x00008067", 64: "0x0000806700008067"}


def _probe_labels(test_data: TestData, case: str, coverpoint: str, names: tuple[str, ...]) -> list[str]:
    """Register probe testcases and return their assembly labels."""
    assert test_data.test_chunk is not None
    labels = []
    for number, name in enumerate(names, start=1):
        test_data.add_testcase(f"{case}_{number}_{name}", coverpoint, test_data.testsuite)
        labels.append(test_data.current_testcase_label)
    test_data.test_chunk.sigupd_count += len(labels)
    return labels


def _memory_probe(instruction: str, data_reg: str, address_reg: str, label: str) -> str:
    return "\n".join(
        [
            f"{label}:",
            f"{instruction} {data_reg}, 0({address_reg})",
            "nop",
            f"RVTEST_SIGUPD(x2, x5, x4, a4, {label}, {label}_str)",
        ]
    )


def _execute_probe(address_reg: str, resume: int, label: str) -> str:
    return "\n".join(
        [
            f"LA(ra, {resume}f)",
            f"{label}:",
            f"jalr x0, 0({address_reg})",
            "nop",
            f"{resume}:",
            "nop",
            f"RVTEST_SIGUPD(x2, x5, x4, a4, {label}, {label}_str)",
        ]
    )


def gen_rwx(test_data: TestData, case: str, coverpoint: str, region: str = "TEST_FOR_EXECUTION") -> list[str]:
    labels = _probe_labels(test_data, case, coverpoint, ("jalr", "sw", "lw"))
    return [
        "",
        "RVTEST_FENCEI",
        f"LA(a4, {region})",
        _execute_probe("a4", 1, labels[0]),
        f"LA(a5, {region})",
        f"LI(a4, {_RET_ENCODING[test_data.xlen]})",
        _memory_probe("sw", "a4", "a5", labels[1]),
        _memory_probe("lw", "a4", "a5", labels[2]),
    ]


def gen_rwx_mprv(test_data: TestData, case: str, coverpoint: str, bits: str) -> list[str]:
    labels = _probe_labels(test_data, case, coverpoint, ("jalr", "sw", "lw"))

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
        _execute_probe("a4", 1, labels[0]),
        "LA(a5, TEST_FOR_EXECUTION)",
        f"LI(a4, {_RET_ENCODING[test_data.xlen]})",
        arm(bits),
        _memory_probe("sw", "a4", "a5", labels[1]),
        arm(bits),
        _memory_probe("lw", "a4", "a5", labels[2]),
        arm("0"),
    ]


def gen_lw(test_data: TestData, case: str, coverpoint: str, region: str) -> list[str]:
    label = _probe_labels(test_data, case, coverpoint, ("lw",))[0]
    return ["", f"LA(a5, {region})", _memory_probe("lw", "a4", "a5", label)]


def gen_lw_bounds(test_data: TestData, case: str, coverpoint: str, region: str, beyond: str) -> list[str]:
    labels = _probe_labels(test_data, case, coverpoint, ("lw_address", "lw_address-4", "lw_beyond"))
    return [
        "",
        f"LA(a5, {region})",
        _memory_probe("lw", "a4", "a5", labels[0]),
        "addi a5, a5, -4",
        _memory_probe("lw", "a4", "a5", labels[1]),
        f"LI(t0, ({beyond}) + 4)",
        "add a5, a5, t0",
        _memory_probe("lw", "a4", "a5", labels[2]),
    ]


def gen_rwx_all(test_data: TestData, case: str, coverpoint: str, region: str = "TEST_FOR_EXECUTION") -> list[str]:
    instructions = (
        ("sb", "sh", "sw", "sd", "lb", "lbu", "lh", "lhu", "lw", "lwu", "ld")
        if test_data.xlen == 64
        else ("sb", "sh", "sw", "lb", "lbu", "lh", "lhu", "lw")
    )
    names = (*instructions, "jalr")
    labels = _probe_labels(test_data, case, coverpoint, names)
    lines = [
        "",
        "// Execute probe",
        "RVTEST_FENCEI",
        f"LA(a4, {region})",
        _execute_probe("a4", 1, labels[-1]),
        "",
        "// Load and store probes",
        f"LA(a5, {region})",
        f"LI(a4, {_RET_ENCODING[test_data.xlen]})",
    ]
    lines.extend(_memory_probe(instruction, "a4", "a5", label) for instruction, label in zip(instructions, labels))
    return lines


def gen_rwx_na4(test_data: TestData, case: str, coverpoint: str, region: str = "TEST_FOR_EXECUTION") -> list[str]:
    names = tuple(f"jalr_{offset}" for offset in _OFFSETS[:3]) + tuple(
        f"{op}_{offset}" for offset in _OFFSETS[:3] for op in ("sw", "lw")
    )
    labels = _probe_labels(test_data, case, coverpoint, names)
    lines = ["", "RVTEST_FENCEI", f"LA(a4, {region})", _execute_probe("a4", 1, labels[0])]
    for adjustment, resume, label in zip((-4, 8), (2, 3), labels[1:3], strict=True):
        lines.extend([f"addi a4, a4, {adjustment}", _execute_probe("a4", resume, label)])
    lines.extend([f"LA(a5, {region})", f"LI(a4, {_RET_ENCODING[test_data.xlen]})"])
    for adjustment, instruction, label in zip((0, 0, -4, 0, 8, 0), ("sw", "lw") * 3, labels[3:], strict=True):
        if adjustment:
            lines.append(f"addi a5, a5, {adjustment}")
        lines.append(_memory_probe(instruction, "a4", "a5", label))
    return lines


def gen_rwx_legal(test_data: TestData, case: str, coverpoint: str, region: str = "TEST_FOR_EXECUTION") -> list[str]:
    names = tuple(f"{op}_{offset}" for op in ("jalr", "sw", "lw") for offset in _OFFSETS)
    labels = _probe_labels(test_data, case, coverpoint, names)
    lines = [
        "",
        "RVTEST_FENCEI",
        "LI(t0, PMP_TOR_REGION_BYTES - 8)",
        "",
        "// Execute probes",
        f"LA(a4, {region})",
    ]
    for resume, (adjustment, label) in enumerate(
        zip(
            (None, "addi a4, a4, -4", "addi a4, a4, 8", "add a4, a4, t0", "addi a4, a4, 4"),
            labels[:5],
            strict=True,
        ),
        1,
    ):
        if adjustment:
            lines.append(adjustment)
        lines.append(_execute_probe("a4", resume, label))
    for instruction, group in (("sw", labels[5:10]), ("lw", labels[10:15])):
        operation = "Store" if instruction == "sw" else "Load"
        lines.extend(["", f"// {operation} probes", f"LA(a5, {region})"])
        if instruction == "sw":
            lines.append(f"LI(a4, {_RET_ENCODING[test_data.xlen]})")
        for adjustment, label in zip(
            (None, "addi a5, a5, -4", "addi a5, a5, 8", "add a5, a5, t0", "addi a5, a5, 4"),
            group,
            strict=True,
        ):
            if adjustment:
                lines.append(adjustment)
            lines.append(_memory_probe(instruction, "a4", "a5", label))
    return lines


def gen_rwx_napot(test_data: TestData, case: str, coverpoint: str, region: str = "TEST_FOR_EXECUTION") -> list[str]:
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
    if test_data.xlen == 64:
        names += ("sd_address", "ld_address", "lwu_address")
    labels = _probe_labels(test_data, case, coverpoint, names)
    lines = [
        "",
        "RVTEST_FENCEI",
        "LI(t0, PMP_NAPOT_REGION_BYTES - 8)",
        "",
        "// Execute probes",
        f"LA(a4, {region})",
    ]
    for resume, (adjustment, label) in enumerate(
        zip(
            (None, "addi a4, a4, -4", "addi a4, a4, 8", "add a4, a4, t0", "addi a4, a4, 4"),
            labels[16:21],
            strict=True,
        ),
        1,
    ):
        if adjustment:
            lines.append(adjustment)
        lines.append(_execute_probe("a4", resume, label))
    lines.extend(["", "// Store probes", f"LA(a5, {region})", f"LI(a4, {_RET_ENCODING[test_data.xlen]})"])
    for instruction, label in zip(("sb", "sh", "sw"), labels[:3], strict=True):
        lines.append(_memory_probe(instruction, "a4", "a5", label))
    for adjustment, label in zip(
        ("addi a5, a5, -4", "addi a5, a5, 8", "add a5, a5, t0", "addi a5, a5, 4"),
        labels[3:7],
        strict=True,
    ):
        lines.extend([adjustment, _memory_probe("sw", "a4", "a5", label)])
    lines.extend(["", "// Load probes", f"LA(a5, {region})"])
    for instruction, label in zip(("lb", "lbu", "lh", "lhu", "lw"), labels[7:12], strict=True):
        lines.append(_memory_probe(instruction, "a4", "a5", label))
    for adjustment, label in zip(
        ("addi a5, a5, -4", "addi a5, a5, 8", "add a5, a5, t0", "addi a5, a5, 4"),
        labels[12:16],
        strict=True,
    ):
        lines.extend([adjustment, _memory_probe("lw", "a4", "a5", label)])
    if test_data.xlen == 64:
        lines.extend(
            [
                f"LA(a5, {region})",
                _memory_probe("sd", "a4", "a5", labels[21]),
                _memory_probe("ld", "a4", "a5", labels[22]),
                _memory_probe("lwu", "a4", "a5", labels[23]),
            ]
        )
    return lines


def gen_rwx_tor_bot(test_data: TestData, case: str, coverpoint: str, region: str = "TEST_FOR_EXECUTION") -> list[str]:
    names = tuple(f"{op}_{where}" for op in ("sw", "lw", "jalr") for where in ("bot-4", "bot", "top-4", "top"))
    labels = _probe_labels(test_data, case, coverpoint, names)
    lines = [
        "",
        "RVTEST_FENCEI",
        "LI(t0, PMP_TOR_REGION_BYTES - 8)",
        "",
        "// Store probes",
        f"LA(a5, {region})",
        f"LI(a4, {_RET_ENCODING[test_data.xlen]})",
    ]
    adjustments = (
        "addi a5, a5, -4",
        "addi a5, a5, 4",
        "add a5, a5, t0\naddi a5, a5, 4",
        "addi a5, a5, 4",
    )
    for instruction, group in (("sw", labels[:4]), ("lw", labels[4:8])):
        if instruction == "lw":
            lines.extend(["", "// Load probes", f"LA(a5, {region})"])
        for adjustment, label in zip(adjustments, group, strict=True):
            lines.extend([adjustment, _memory_probe(instruction, "a4", "a5", label)])
    lines.extend(["", "// Execute probes", f"LA(a4, {region})"])
    for resume, (adjustment, label) in enumerate(zip(adjustments, labels[8:], strict=True), 1):
        lines.extend([adjustment.replace("a5", "a4"), _execute_probe("a4", resume, label)])
    return lines


def gen_rwx_tor_zero(test_data: TestData, case: str, coverpoint: str, region: str = "TEST_FOR_EXECUTION") -> list[str]:
    names = tuple(f"{op}_{where}" for op in ("sw", "lw", "jalr") for where in ("top", "top-4"))
    labels = _probe_labels(test_data, case, coverpoint, names)
    return [
        "",
        "// Store probes",
        f"LA(a5, {region})",
        f"LI(a4, {_RET_ENCODING[test_data.xlen]})",
        _memory_probe("sw", "a4", "a5", labels[0]),
        "addi a5, a5, -4",
        _memory_probe("sw", "a4", "a5", labels[1]),
        "LI(a4, 0x00008067)",
        "LI(a5, 0)",
        "LA(ra, 7f)",
        "sw a4, 0(a5)",
        "nop",
        "7:",
        "nop",
        "",
        "// Load probes",
        f"LA(a5, {region})",
        _memory_probe("lw", "a4", "a5", labels[2]),
        "addi a5, a5, -4",
        _memory_probe("lw", "a4", "a5", labels[3]),
        "LI(a5, 0)",
        "LA(ra, 8f)",
        "lw a4, 0(a5)",
        "nop",
        "8:",
        "nop",
        "",
        "// Execute probes",
        "RVTEST_FENCEI",
        f"LA(a4, {region})",
        _execute_probe("a4", 1, labels[4]),
        "addi a4, a4, -4",
        _execute_probe("a4", 2, labels[5]),
        "LI(a5, 0)",
        "LA(ra, 9f)",
        "jalr x0, 0(a5)",
        "nop",
        "9:",
        "nop",
    ]


def gen_float(test_data: TestData, case: str, coverpoint: str, region: str = "TEST_FOR_EXECUTION") -> list[str]:
    instructions = ("fsh", "fsw", "fsd", "flh", "flw", "fld")
    labels = _probe_labels(test_data, case, coverpoint, instructions)
    return [
        "",
        f"LA(a5, {region})",
        *(_memory_probe(op, "f14", "a5", label) for op, label in zip(instructions, labels, strict=True)),
    ]


def gen_amo(test_data: TestData, case: str, coverpoint: str, region: str = "TEST_FOR_EXECUTION") -> list[str]:
    operations = tuple((amo, width) for amo in _AMOS for width in (("w", "d") if test_data.xlen == 64 else ("w",)))
    labels = _probe_labels(test_data, case, coverpoint, tuple(f"{amo}_{width}" for amo, width in operations))
    lines = ["", f"LI(a6, {_RET_ENCODING[test_data.xlen]})", f"LA(a5, {region})"]
    for (operation, width), label in zip(operations, labels, strict=True):
        lines.append(
            "\n".join(
                [
                    f"{label}:",
                    f"{operation}.{width} a4, a6, (a5)",
                    "nop",
                    f"RVTEST_SIGUPD(x2, x5, x4, a4, {label}, {label}_str)",
                ]
            )
        )
    return lines


def gen_lrsc(
    test_data: TestData, case: str, coverpoint: str, region: str = "TEST_FOR_EXECUTION", *, retry: bool = False
) -> list[str]:
    widths = ("w", "d") if test_data.xlen == 64 else ("w",)
    labels = _probe_labels(
        test_data, case, coverpoint, tuple(f"{op}_{width}" for width in widths for op in ("lr", "sc"))
    )
    lines = ["", f"LA(a5, {region})"]
    for offset, width in enumerate(widths):
        lr_label, sc_label = labels[2 * offset : 2 * offset + 2]
        if retry:
            tag = f"{case}_{width}"
            lines.append(
                "\n".join(
                    [
                        "LI(t2, 100)",
                        f"{tag}_retry:",
                        f"{lr_label}:",
                        f"lr.{width} a3, (a5)",
                        f"{sc_label}:",
                        f"sc.{width} a2, a3, (a5)",
                        f"beqz a2, {tag}_success",
                        "addi t2, t2, -1",
                        f"bnez t2, {tag}_retry",
                        f"{tag}_success:",
                        f"RVTEST_SIGUPD(x2, x5, x4, a3, {lr_label}, {lr_label}_str)",
                        f"RVTEST_SIGUPD(x2, x5, x4, a2, {sc_label}, {sc_label}_str)",
                    ]
                )
            )
        else:
            lines.append(
                "\n".join(
                    [
                        f"{lr_label}:",
                        f"lr.{width} a2, (a5)",
                        "nop",
                        f"RVTEST_SIGUPD(x2, x5, x4, a2, {lr_label}, {lr_label}_str)",
                        f"{sc_label}:",
                        f"sc.{width} a2, a2, (a5)",
                        "nop",
                        f"RVTEST_SIGUPD(x2, x5, x4, a2, {sc_label}, {sc_label}_str)",
                    ]
                )
            )
    return lines


def gen_lrsc_success(test_data: TestData, case: str, coverpoint: str, region: str = "TEST_FOR_EXECUTION") -> list[str]:
    return gen_lrsc(test_data, case, coverpoint, region, retry=True)


def gen_compressed_execute(test_data: TestData, case: str, coverpoint: str, region: str) -> list[str]:
    label = _probe_labels(test_data, case, coverpoint, ("c.jalr",))[0]
    return [
        "",
        f"LA(x15, {region})",
        f"{label}:",
        "c.jalr x15",
        "nop",
        f"RVTEST_SIGUPD(x2, x5, x4, a4, {label}, {label}_str)",
    ]


def gen_cbo(test_data: TestData, case: str, coverpoint: str, region: str = "TEST_FOR_EXECUTION") -> list[str]:
    instructions = ("cbo.zero", "cbo.clean", "cbo.flush", "cbo.inval")
    labels = _probe_labels(test_data, case, coverpoint, instructions)
    lines = ["", f"LA(a4, {region})"]
    for instruction, label in zip(instructions, labels, strict=True):
        lines.extend(
            [
                f"{label}:",
                f"{instruction} (a4)",
                "nop",
                f"RVTEST_SIGUPD(x2, x5, x4, a4, {label}, {label}_str)",
            ]
        )
    return lines


def gen_prefetch(test_data: TestData, case: str, coverpoint: str, region: str = "TEST_FOR_EXECUTION") -> list[str]:
    instructions = ("prefetch.i", "prefetch.r", "prefetch.w")
    labels = _probe_labels(test_data, case, coverpoint, instructions)
    lines = ["", f"LA(t0, {region})"]
    for instruction, label in zip(instructions, labels, strict=True):
        lines.extend(
            [
                f"{label}:",
                f"{instruction} 0(t0)",
                "nop",
                f"RVTEST_SIGUPD(x2, x5, x4, a4, {label}, {label}_str)",
            ]
        )
    return lines


def _compressed_memory_probe(instruction: str, data_reg: str, label: str) -> str:
    return "\n".join(
        [
            f"{label}:",
            f"{instruction} {data_reg}, 0(x8)",
            "c.nop",
            "c.nop",
            f"RVTEST_SIGUPD(x2, x5, x4, a4, {label}, {label}_str)",
        ]
    )


def _compressed_sp_probes(store: str, load: str, data_reg: str) -> str:
    return "\n".join(
        [
            "mv t0, sp",
            "addi sp, x8, 0",
            f"{store} {data_reg}, 0(sp)",
            "c.nop",
            "c.nop",
            f"{load} {data_reg}, 0(sp)",
            "c.nop",
            "c.nop",
            "mv sp, t0",
        ]
    )


def gen_zca(test_data: TestData, case: str, coverpoint: str, region: str = "TEST_FOR_EXECUTION") -> list[str]:
    instructions = ("c.sw", "c.lw", "c.jalr") + (("c.sd", "c.ld") if test_data.xlen == 64 else ())
    labels = _probe_labels(test_data, case, coverpoint, instructions)
    execute_label = labels[2]
    lines = [
        "",
        "RVTEST_FENCEI",
        f"LA(x15, {region})",
        "LA(ra, 1f)",
        f"{execute_label}:",
        "c.jalr x15",
        "c.nop",
        "c.nop",
        "1:",
        "c.nop",
        "c.nop",
        f"RVTEST_SIGUPD(x2, x5, x4, a4, {execute_label}, {execute_label}_str)",
        "LI(x15, 0x00010001)",
        f"LA(x8, {region})",
        _compressed_memory_probe("c.sw", "x15", labels[0]),
        _compressed_memory_probe("c.lw", "x15", labels[1]),
        _compressed_sp_probes("c.swsp", "c.lwsp", "x15"),
    ]
    if test_data.xlen == 64:
        lines.extend(
            [
                "LI(x15, 0x0001000100010001)",
                _compressed_memory_probe("c.sd", "x15", labels[3]),
                _compressed_memory_probe("c.ld", "x15", labels[4]),
                _compressed_sp_probes("c.sdsp", "c.ldsp", "x15"),
            ]
        )
    return lines


def gen_zcb(test_data: TestData, case: str, coverpoint: str, region: str = "TEST_FOR_EXECUTION") -> list[str]:
    instructions = ("c.sb", "c.lbu", "c.sh", "c.lhu", "c.sh", "c.lh")
    labels = _probe_labels(test_data, case, coverpoint, instructions)
    lines = ["", "LI(x15, NOP)", f"LA(x8, {region})"]
    lines.extend(_compressed_memory_probe(op, "x15", label) for op, label in zip(instructions, labels, strict=True))
    return lines


def gen_zcd(test_data: TestData, case: str, coverpoint: str, region: str = "TEST_FOR_EXECUTION") -> list[str]:
    labels = _probe_labels(test_data, case, coverpoint, ("c.fsd", "c.fld"))
    return [
        "",
        "li x15, 0x3f800000",
        "fmv.w.x f8, x15",
        f"LA(x8, {region})",
        _compressed_memory_probe("c.fsd", "f8", labels[0]),
        _compressed_memory_probe("c.fld", "f8", labels[1]),
        _compressed_sp_probes("c.fsdsp", "c.fldsp", "f8"),
    ]


def gen_zcf(test_data: TestData, case: str, coverpoint: str, region: str = "TEST_FOR_EXECUTION") -> list[str]:
    labels = _probe_labels(test_data, case, coverpoint, ("c.fsw", "c.flw"))
    return [
        "",
        "li x15, 0x3f800000",
        "fmv.w.x f8, x15",
        f"LA(x8, {region})",
        _compressed_memory_probe("c.fsw", "f8", labels[0]),
        _compressed_memory_probe("c.flw", "f8", labels[1]),
        _compressed_sp_probes("c.fswsp", "c.flwsp", "f8"),
    ]


ProbeGenerator = Callable[[TestData, str, str, str], list[str]]
