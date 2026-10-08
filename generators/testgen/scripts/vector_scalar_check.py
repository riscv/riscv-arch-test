##################################
# vector_scalar_check.py
#
# Scalar self-checking variants of the vector tests from the standalone generator (e.g. Vf32-scalarcheck).
# Outside the instruction under test, these tests only use vset{i}vl{i} and unmasked unit-stride
# vle<eew>.v/vse<eew>.v with EEW = SEW. Each function returns (line, comment) pairs that replace setup code
# that would use other vector instructions. See tests/env/rvtest_vector_scalar_check.h.
# SPDX-License-Identifier: Apache-2.0
##################################

import math
import re
from collections.abc import Callable, Sequence

SUFFIX = "-scalarcheck"

# Set while generating a scalar self-checking suite
enabled = False


def set_enabled(value: bool) -> None:
  global enabled
  enabled = value


def select_suites(extensions, include_set, exclude_set, testplans, scalar):
  """
  With --vector-check scalar, replace the Vf suites with their scalar self-checking variants. Variants named in
  include_set are generated in either mode.
  """
  if scalar:
    extensions = [re.sub(r"^(Vf\d+)$", rf"\1{SUFFIX}", e) for e in extensions]
  return extensions + sorted(
    e for e in include_set
    if e.endswith(SUFFIX) and e.removesuffix(SUFFIX) in testplans
    and e.startswith("Vf") and e not in exclude_set and e not in extensions
  )


def mixed_width_load_applies(load_unique_vtype, register_value, nf_prefill, register_sew, sew, register_val_pointer) -> bool:
  """A preload whose EEW differs from SEW needs vtype switched to SEW = EEW, since vle<eew>.v needs EEW = SEW."""
  return (enabled and not load_unique_vtype and register_value is None and nf_prefill == 1
          and register_sew != sew and register_val_pointer != "vs_corner_zero_emul8")


def mixed_width_vtype_lines(register_sew, sew, saved_reg, new_reg, field_reg):
  """Switch vtype to SEW = register_sew and LMUL scaled by the same factor, keeping vl and vta/vma."""
  width_shift = int(math.log2(register_sew)) - int(math.log2(sew))
  return [
    (f"csrr x{saved_reg}, vtype", f"# load at EEW={register_sew}: scale vsew and vlmul by {2**width_shift}"),
    (f"andi x{field_reg}, x{saved_reg}, 7", ""),
    (f"addi x{field_reg}, x{field_reg}, {width_shift}", ""),
    (f"andi x{field_reg}, x{field_reg}, 7", "# new vlmul"),
    (f"andi x{new_reg}, x{saved_reg}, 0xF8", "# vma, vta, vsew"),
    (f"addi x{new_reg}, x{new_reg}, {width_shift << 3}", "# new vsew"),
    (f"or x{new_reg}, x{new_reg}, x{field_reg}", ""),
    (f"vsetvl x0, x0, x{new_reg}", "# same SEW/LMUL ratio, so vl is unchanged"),
  ]


def restore_vtype_lines(saved_reg):
  return [(f"vsetvl x0, x0, x{saved_reg}", "# restore vtype")]


def mask_lines(maskval, sew, lmulflag, temp_reg, used: Sequence[int], pick: Callable[[Sequence[int]], int]):
  """Load v0 for prepMaskV without vmv.v.i, vid.v, vmsltu.vx, or vlm.v. Leaves x{temp_reg} = VLMAX."""
  lines = [(f"vsetvli x{temp_reg}, x0, e{sew}, m{lmulflag}, ta, ma", f"# x{temp_reg} = VLMAX")]
  if maskval in ("zeroes", "ones", "vlmaxm1_ones", "vlmaxd2p1_ones"):
    lines.append((f"LA(x{temp_reg}, rvtest_vsc_zeros)", ""))
    lines.append((f"vle{sew}.v v0, (x{temp_reg})", "# Set mask register group to 0"))
  if maskval in ("ones", "vlmaxm1_ones", "vlmaxd2p1_ones"):
    t1 = pick([*used, temp_reg])
    t2 = pick([*used, temp_reg, t1])
    t3 = pick([*used, temp_reg, t1, t2])
    lines.append((f"vsetvli x{temp_reg}, x0, e{sew}, m{lmulflag}, ta, ma", f"# x{temp_reg} = VLMAX"))
    if maskval == "vlmaxm1_ones":
      lines.append((f"addi x{temp_reg}, x{temp_reg}, -1", f"# x{temp_reg} = VLMAX - 1"))
    elif maskval == "vlmaxd2p1_ones":
      lines.append((f"srli x{temp_reg}, x{temp_reg}, 1", f"# x{temp_reg} = VLMAX / 2"))
      lines.append((f"addi x{temp_reg}, x{temp_reg}, 1", f"# x{temp_reg} = VLMAX / 2 + 1"))
    lines.append((f"RVTEST_VSC_LOWER_BITS_MASK(x{temp_reg}, x{t1}, x{t2}, x{t3})", f"# v0[i] = (i < x{temp_reg}) ? 1 : 0"))
  elif maskval != "zeroes":
    # vlm.v at this vtype loads ceil(VLMAX/8) bytes and leaves the rest of v0 undisturbed
    lines.append((f"addi x{temp_reg}, x{temp_reg}, 7", ""))
    lines.append((f"srli x{temp_reg}, x{temp_reg}, 3", f"# x{temp_reg} = ceil(VLMAX/8)"))
    lines.append((f"vsetvli x0, x{temp_reg}, e8, m1, tu, mu", ""))
    lines.append((f"la x{temp_reg}, {maskval}", ""))
    lines.append((f"vle8.v v0, (x{temp_reg})", "# Load mask value into v0"))
  lines.append((f"vsetvli x{temp_reg}, x0, e{sew}, m{lmulflag}, ta, ma", f"# x{temp_reg} = VLMAX"))
  return lines


def zero_v0_lines(sew, addr_reg):
  return [
    (f"LA(x{addr_reg}, rvtest_vsc_zeros)", ""),
    (f"vle{sew}.v v0, (x{addr_reg})", "# set v0 register to 0 in base suit where vm is fixed to 0"),
  ]


def zero_regs_lines(registers, addr_reg):
  """Zero each register at the current vl (SEW=8) by loading a zero buffer."""
  return [f"LA(x{addr_reg}, rvtest_vsc_zeros)"] + [f"vle8.v v{register}, (x{addr_reg})" for register in registers]


def fill_0xd_lines(registers, sew, addr_reg):
  """Fill each register with 0xD at the current vl by loading a constant buffer."""
  lines = [(f"LA(x{addr_reg}, rvtest_vsc_splat_d_e{sew})", "")]
  for register in registers:
    lines.append((f"vle{sew}.v v{register}, (x{addr_reg})",
                  f"# Initialize v{register} to 0xD for deterministic undisturbed/tail elements in base suite"))
  return lines
