##################################
# priv/extensions/sv/assembly.py
#
# Shared Sv data-section fragments.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shared Sv assembly fragments."""

DATA_REGION = """\
.p2align 12
rvtest_data_1:
nop
addi a4, a2, 4
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
  addi a4, a2, 4
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
  addi a4, a2, 4
  jr ra
  nop
  .word 0xbeefcaf1          // Random word
  .word 0xbeefcaf2          // Random word
  jr ra
  .skip (2 << 12) - (7*4)
  nop
  addi a4, a2, 4
  jr ra
  nop
  .word 0xbeefcaf3          // Random word
  .word 0xbeefcaf4          // Random word
  jr ra
  .skip (13 << 12) - (7*4)
  nop
  addi a4, a2, 4
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
  addi a4, a2, 4
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
  addi a4, a2, REGWIDTH
  jr ra
  nop
  .word 0xbeefcaf1          // Random word
  .word 0xbeefcaf2          // Random word
  .skip ((1 << 10) - 7)*4
  .word 0xbeefcaf3          // Random word

.p2align 12
rvtest_data_1_l0_x:
  nop
  addi a4, a2, REGWIDTH
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
  addi a4, a2, REGWIDTH
  jr ra
  nop
  .word 0xbeefcaf1          // Random word
  .word 0xbeefcaf2          // Random word
  .skip ((1 << 10) - 7)*4
  jr ra
""".strip("\n")
