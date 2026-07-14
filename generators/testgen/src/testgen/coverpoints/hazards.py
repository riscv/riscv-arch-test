##################################
# hazards.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Hazard coverpoint generators (cp_gpr_hazard, cp_fpr_hazard)."""

from __future__ import annotations

from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_instruction
from testgen.formatters.params import generate_random_params
from testgen.formatters.registry import get_instr_type_config


def _hazard_class(coverpoint: str) -> str:
    """Return the requested hazard class suffix: r, w, or rw."""
    parts = coverpoint.split("_")
    if len(parts) > 3 and parts[-1] in {"r", "w", "rw"}:
        return parts[-1]
    return "rw"


def _int_sources(instr_type: str) -> list[str]:
    if instr_type == "S":
        # rs1 (address base) now covered via _make_store_base_hazard using the
        # formatter's own address-setup arithmetic as the RAW producer.
        return ["rs1", "rs2"]
    if instr_type == "JR":
        # JALR rs1 is a jump target — a RAW hazard on rs1 would corrupt control flow.
        # RAW generation for JALR is excluded entirely. No dedicated pattern exists.
        return []
    required = get_instr_type_config(instr_type).required_params or set()
    return [field for field in ("rs1", "rs2", "rs3") if field in required]


def _float_sources(instr_type: str) -> list[str]:
    required = get_instr_type_config(instr_type).required_params or set()
    return [field for field in ("fs1", "fs2", "fs3") if field in required]


def _has_int_dest(instr_type: str) -> bool:
    required = get_instr_type_config(instr_type).required_params or set()
    return "rd" in required


def _has_float_dest(instr_type: str) -> bool:
    required = get_instr_type_config(instr_type).required_params or set()
    return "fd" in required


def _get_param(params: InstructionParams, field: str) -> int:
    value = getattr(params, field)
    assert value is not None
    return value


def _with_hazard_comment(line: str, comment: str) -> str:
    instr = line.split("#", 1)[0].rstrip()
    return f"{instr} {comment}"


def _generate_with_fixed_int_source(test_data: TestData, instr_type: str, field: str, reg: int) -> InstructionParams:
    exclude_regs = [0] if _has_int_dest(instr_type) else []
    if field == "rs1":
        return generate_random_params(test_data, instr_type, rs1=reg, exclude_regs=exclude_regs)
    if field == "rs2":
        return generate_random_params(test_data, instr_type, rs2=reg, exclude_regs=exclude_regs)
    if field == "rs3":
        return generate_random_params(test_data, instr_type, rs3=reg, exclude_regs=exclude_regs)
    raise ValueError(f"Unknown integer source field: {field}")


def _generate_with_fixed_float_source(test_data: TestData, instr_type: str, field: str, reg: int) -> InstructionParams:
    if field == "fs1":
        return generate_random_params(test_data, instr_type, fs1=reg)
    if field == "fs2":
        return generate_random_params(test_data, instr_type, fs2=reg)
    if field == "fs3":
        return generate_random_params(test_data, instr_type, fs3=reg)
    raise ValueError(f"Unknown floating-point source field: {field}")


def _make_gpr_stressor(test_data: TestData, forbidden: set[int] | None = None) -> str:
    forbidden = (forbidden or set()) | {0}
    available_regs = sorted(test_data.int_regs.reg_list - forbidden)
    if len(available_regs) < 3:
        return "addi x0, x0, 0"
    rd, rs1, rs2 = available_regs[:3]
    return f"add x{rd}, x{rs1}, x{rs2}"


def _make_load_base_hazard(
    instr_name: str,
    instr_type: str,
    coverpoint: str,
    test_data: TestData,
    case_idx: int | str,
    filler: str = "",
    filler_name: str = "",
) -> list[str]:
    """Generate a RAW hazard where a load consumes a valid freshly written base register."""
    base_reg = test_data.int_regs.get_register(exclude_regs=[0])
    consumer = generate_random_params(test_data, instr_type, rs1=base_reg, exclude_regs=[0, base_reg])
    bin_name = case_idx if isinstance(case_idx, str) else f"raw_rs1_{case_idx}"
    label_line = test_data.add_testcase(bin_name, coverpoint)
    setup, test, check = format_instruction(instr_name, instr_type, test_data, consumer)
    if filler_name == "stressor":
        forbidden = {base_reg} | set(consumer.used_int_regs)
        filler = _make_gpr_stressor(test_data, forbidden)
    mid = [f"  {filler} # depth=1 filler: {filler_name}"] if filler else []
    setup_lines = setup.splitlines()
    setup_lines[-1] = _with_hazard_comment(setup_lines[-1], f"# RAW producer: writes x{base_reg} with load base")
    test = _with_hazard_comment(test, "# RAW consumer: reads rs1 load base - tests bypass forwarding")
    lines = [f"\n# Testcase {coverpoint} {bin_name}", "\n".join(setup_lines), *mid, label_line, test]
    if check:
        lines.append(check)
    test_data.int_regs.return_registers(consumer.used_int_regs + [base_reg])
    return [line for line in lines if line]


def _make_store_base_hazard(
    instr_name: str,
    instr_type: str,
    coverpoint: str,
    test_data: TestData,
    case_idx: int | str,
    filler: str = "",
    filler_name: str = "",
) -> list[str]:
    """Generate a RAW hazard where a store consumes a freshly written base/address register."""
    base_reg = test_data.int_regs.get_register(exclude_regs=[0])
    consumer = generate_random_params(test_data, instr_type, rs1=base_reg, exclude_regs=[0, base_reg])
    bin_name = case_idx if isinstance(case_idx, str) else f"raw_rs1_{case_idx}"
    label_line = test_data.add_testcase(bin_name, coverpoint)
    setup, test, check = format_instruction(instr_name, instr_type, test_data, consumer)
    if filler_name == "stressor":
        forbidden = {base_reg} | set(consumer.used_int_regs)
        filler = _make_gpr_stressor(test_data, forbidden)
    mid = [f"  {filler} # depth=1 filler: {filler_name}"] if filler else []
    setup_lines = setup.splitlines()
    setup_lines[-1] = _with_hazard_comment(setup_lines[-1], f"# RAW producer: writes x{base_reg} with store base")
    test = _with_hazard_comment(test, "# RAW consumer: reads rs1 store base - tests bypass forwarding")
    lines = [f"\n# Testcase {coverpoint} {bin_name}", "\n".join(setup_lines), *mid, label_line, test]
    if check:
        lines.append(check)
    test_data.int_regs.return_registers(consumer.used_int_regs)
    return [line for line in lines if line]


def _make_gpr_hazard(
    instr_name: str,
    instr_type: str,
    coverpoint: str,
    test_data: TestData,
    haz_type: str,
    field: str | None,
    case_idx: int | str,
    filler: str = "",
    filler_name: str = "",
) -> list[str]:
    """Generate one adjacent GPR producer/consumer hazard testcase."""
    if haz_type == "raw" and instr_type == "L" and field == "rs1":
        return _make_load_base_hazard(instr_name, instr_type, coverpoint, test_data, case_idx, filler, filler_name)
    if haz_type == "raw" and instr_type == "S" and field == "rs1":
        return _make_store_base_hazard(instr_name, instr_type, coverpoint, test_data, case_idx, filler, filler_name)

    producer = generate_random_params(test_data, "R", exclude_regs=[0, 1, 2, 4, 5, 7, 8, 12, 13])
    assert producer.rd is not None and producer.rs1 is not None and producer.rs2 is not None

    if haz_type == "raw":
        assert field is not None
        consumer = _generate_with_fixed_int_source(test_data, instr_type, field, producer.rd)

        # Address-based consumers need the producer to preserve the computed base
        # register that their formatter establishes during setup.
        if field == "rs1" and instr_type in {"L", "S", "JR"}:
            test_data.int_regs.return_registers([producer.rs1, producer.rs2])
            available = sorted(test_data.int_regs.reg_list - {0, producer.rd})
            producer.rs1 = available[0] if available else producer.rd
            producer.rs2 = available[1] if len(available) > 1 else producer.rd
    elif haz_type == "waw":
        consumer = generate_random_params(test_data, instr_type, rd=producer.rd)
    else:
        raise ValueError(f"Unknown hazard type: {haz_type}")

    bin_name = (
        case_idx if isinstance(case_idx, str) else (haz_type if field is None else f"{haz_type}_{field}_{case_idx}")
    )
    label_line = test_data.add_testcase(bin_name, coverpoint)
    assert test_data.test_chunk is not None
    sigupd_count = test_data.test_chunk.sigupd_count
    setup1, test1, check1 = format_instruction("add", "R", test_data, producer)
    if check1:
        test_data.test_chunk.sigupd_count = sigupd_count
        check1 = ""
    setup2, test2, check2 = format_instruction(instr_name, instr_type, test_data, consumer)
    if filler_name == "stressor":
        forbidden = {producer.rd} | set(consumer.used_int_regs)
        filler = _make_gpr_stressor(test_data, forbidden)
    mid = [f"  {filler} # depth=1 filler: {filler_name}"] if filler else []
    if haz_type == "raw":
        test1 = _with_hazard_comment(test1, f"# RAW producer: writes x{producer.rd}")
        test2 = _with_hazard_comment(test2, f"# RAW consumer: reads {field} - tests bypass forwarding")
    elif haz_type == "waw":
        test1 = _with_hazard_comment(test1, f"# WAW producer: writes x{producer.rd} (must NOT win)")
        test2 = _with_hazard_comment(test2, f"# WAW consumer: writes x{consumer.rd} (must win - last write)")
    lines = [f"\n# Testcase {coverpoint} {bin_name}", setup1, setup2, test1, *mid, label_line, test2]
    if haz_type == "waw":
        lines.append(check2)
    else:
        if check2:
            lines.append(check2)

    test_data.int_regs.return_registers(producer.used_int_regs)
    test_data.int_regs.return_registers(consumer.used_int_regs)
    test_data.float_regs.return_registers(consumer.used_float_regs)
    return [line for line in lines if line]


def _make_fpr_stressor(test_data: TestData) -> str:
    """Independent FP-register-consuming filler for depth=1 FPR hazard tests."""
    available_regs = sorted(test_data.float_regs.reg_list)
    if len(available_regs) < 3:
        return "fadd.s f0, f0, f0"
    fd, fs1, fs2 = available_regs[:3]
    return f"fadd.s f{fd}, f{fs1}, f{fs2}"


def _make_fpr_hazard(
    instr_name: str,
    instr_type: str,
    coverpoint: str,
    test_data: TestData,
    haz_type: str,
    field: str | None,
    case_idx: int | str,
    filler: str = "",
    filler_name: str = "",
) -> list[str]:
    """Generate one adjacent FPR producer/consumer hazard testcase."""
    producer = generate_random_params(test_data, "FR", fp_load_type="single")
    assert producer.fd is not None and producer.fs1 is not None and producer.fs2 is not None

    if haz_type == "raw":
        assert field is not None
        consumer = _generate_with_fixed_float_source(test_data, instr_type, field, producer.fd)
    elif haz_type == "waw":
        consumer = generate_random_params(test_data, instr_type, fd=producer.fd)
    elif haz_type == "war":
        assert field is not None
        consumer = generate_random_params(test_data, instr_type, fd=_get_param(producer, field))
    else:
        raise ValueError(f"Unknown hazard type: {haz_type}")

    bin_name = haz_type if field is None else f"{haz_type}_{field}_{case_idx}"
    label_line = test_data.add_testcase(bin_name, coverpoint)
    setup1, test1, check1 = format_instruction("fadd.s", "FR", test_data, producer)
    setup2, test2, check2 = format_instruction(instr_name, instr_type, test_data, consumer)

    if filler_name == "stressor":
        filler = _make_fpr_stressor(test_data)
    mid = [f"  {filler} # depth=1 filler: {filler_name}"] if filler else []
    lines = [f"\n# Testcase {coverpoint} {bin_name}", setup1, setup2, test1, *mid, label_line, test2]
    if haz_type == "waw":
        lines.append(check2)
    else:
        if check1:
            lines.append(check1)
        if check2:
            lines.append(check2)

    test_data.float_regs.return_registers(producer.used_float_regs)
    test_data.float_regs.return_registers(consumer.used_float_regs)
    test_data.int_regs.return_registers(consumer.used_int_regs)
    return [line for line in lines if line]


@add_coverpoint_generator("cp_gpr_hazard", "cp_fpr_hazard")
def make_cp_hazard(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate RAW and WAW register hazard tests."""
    tc = test_data.begin_test_chunk()
    haz_class = _hazard_class(coverpoint)
    test_lines: list[str] = []
    if coverpoint.startswith("cp_fpr_hazard"):
        source_fields = _float_sources(instr_type)
        has_dest = _has_float_dest(instr_type)
        make_hazard = _make_fpr_hazard
    else:
        source_fields = _int_sources(instr_type)
        has_dest = _has_int_dest(instr_type)
        make_hazard = _make_gpr_hazard
    FILLERS = {
        "nop": "addi x0, x0, 0",
        "stressor": "stressor",
    }
    if "r" in haz_class:
        # Depth=0: producer immediately followed by consumer (no filler)
        for field in source_fields:
            if instr_type == "JR" and field == "rs1":
                continue  # jalr rs1 is a jump target - RAW hazard corrupts control flow
            bin_name = f"raw_{field}_depth0"
            test_lines.extend(make_hazard(instr_name, instr_type, coverpoint, test_data, "raw", field, bin_name))
        # Depth=1: producer, filler, consumer
        for field in source_fields:
            if instr_type == "JR" and field == "rs1":
                continue  # jalr rs1 is a jump target - RAW hazard corrupts control flow
            for filler_name, filler in FILLERS.items():
                bin_name = f"raw_{field}_{filler_name}"
                test_lines.extend(
                    _make_gpr_hazard(
                        instr_name, instr_type, coverpoint, test_data, "raw", field, bin_name, filler, filler_name
                    )
                    if make_hazard is _make_gpr_hazard
                    else make_hazard(instr_name, instr_type, coverpoint, test_data, "raw", field, bin_name, filler, filler_name)
                )
    if "w" in haz_class and has_dest:
        test_lines.extend(make_hazard(instr_name, instr_type, coverpoint, test_data, "waw", None, "waw"))

    tc.code = "\n".join(test_lines)
    return [test_data.end_test_chunk()]
