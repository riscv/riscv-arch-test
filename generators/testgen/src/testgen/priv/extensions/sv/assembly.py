##################################
# priv/extensions/sv/assembly.py
#
# Shared Sv data-section fragments.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shared Sv assembly fragments.

The routines in these regions are executed by the tests, so the registers they use are filled in from the
chunk's SvRegs by generate.data_region: ``{value}`` is the running store value and ``{result}`` receives
the routine's result. They return with ``jr ra``; see SvRegs for why the return address stays in x1.
"""

DATA_REGION = """\
.p2align 12
rvtest_data_1:
nop
addi {result}, {value}, 4
jr ra
nop
.word 0xbeefcaf1
.word 0xbeefcaf2
nop
jr ra"""

DATA_REGION_ALIGNED = r"""
.p2align 12
.p2align (UDB_PMP_GRANULARITY)
rvtest_data_1:
  nop
  addi {result}, {value}, 4
  jr ra
  nop
  .word 0xbeefcaf1          // Random word
  .word 0xbeefcaf2          // Random word
  nop
  jr ra

.p2align (UDB_PMP_GRANULARITY)
""".strip("\n")

NAPOT_DATA = r"""
.p2align 16
rvtest_data_1:
  nop
  addi {result}, {value}, 4
  jr ra
  nop
  .word 0xbeefcaf1          // Random word
  .word 0xbeefcaf2          // Random word
  jr ra
  .skip (2 << 12) - (7*4)
  nop
  addi {result}, {value}, 4
  jr ra
  nop
  .word 0xbeefcaf3          // Random word
  .word 0xbeefcaf4          // Random word
  jr ra
  .skip (13 << 12) - (7*4)
  nop
  addi {result}, {value}, 4
  jr ra
  nop
  .word 0xbeefcaf3          // Random word
  .word 0xbeefcaf4          // Random word
  jr ra
""".strip("\n")

NAPOT_RESERVED_DATA = r"""
.p2align 16
rvtest_data_1:
  nop
  addi {result}, {value}, 4
  jr ra
  nop
  .word 0xbeefcaf1          // Random word
  .word 0xbeefcaf2          // Random word
  .skip (1 << 16) - (7*4)
  jr ra
""".strip("\n")

VA_ONES_DATA = r"""
.p2align 12
rvtest_data_1_l0_rw:
  nop
  addi {result}, {value}, REGWIDTH
  jr ra
  nop
  .word 0xbeefcaf1          // Random word
  .word 0xbeefcaf2          // Random word
  .skip ((1 << 10) - 7)*4
  .word 0xbeefcaf3          // Random word

.p2align 12
rvtest_data_1_l0_x:
  nop
  addi {result}, {value}, REGWIDTH
  jr ra
  nop
  .word 0xbeefcaf1          // Random word
  .word 0xbeefcaf2          // Random word
  .skip ((1 << 10) - 7)*4
  jr ra
""".strip("\n")

VA_ZEROS_DATA = r"""
.p2align 12
rvtest_data_1_l0_rw:
  .word 0xbeefcaf1          // Random word
  .word 0xbeefcaf2          // Random word
  .skip ((1 << 10) - 3)*4
  .word 0xbeefcaf3          // Random word

.p2align 12
rvtest_data_1_l0_x:
  nop
  addi {result}, {value}, REGWIDTH
  jr ra
  nop
  .word 0xbeefcaf1          // Random word
  .word 0xbeefcaf2          // Random word
  .skip ((1 << 10) - 7)*4
  jr ra
""".strip("\n")
