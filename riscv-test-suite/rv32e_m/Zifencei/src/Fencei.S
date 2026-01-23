// -----------
// Copyright (c) 2020. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
// -----------
//
// This assembly file tests the fence.i instruction of the RISC-V Zifencei extension.
// 

#include "model_test.h"
#include "arch_test.h"

# Test Virtual Machine (TVM) used by program.
RVTEST_ISA("RV32E_Zifencei")

# Test code region
.section .text.init
.globl rvtest_entry_point
rvtest_entry_point:
RVMODEL_BOOT
RVTEST_CODE_BEGIN
RVMODEL_IO_ASSERT_GPR_EQ(x15, x0, 0x00000000)
RVMODEL_IO_WRITE_STR(x15, "# Test Begin\n")

#ifdef TEST_CASE_1
  RVTEST_CASE(1,"// check ISA:=regex(.*E.*); check ISA:=regex(.*Zifencei.*);def RVTEST_E = True; def TEST_CASE_1=True", fencei)

    # ---------------------------------------------------------------------------------------------
    RVMODEL_IO_WRITE_STR(x15, "# Test part A - test fence\n");

    # Addresses for test data and results
    LA(     x6,test_A_data)
    LA(     x7,test_A_res)

    # Register initialization
    LI(     x3,0)

    # Load testdata
    lw      x1, 0(x6)
    lw      x2, 4(x6)

    # Test
    LA(     x10,instr_A_src)
    LA(     x11,instr_A_dst)
    lw      x5, 0(x10)
    sw      x5, 0(x11)
    fence.i
instr_A_dst:
    lui     x2, 0

    # Store results
    sw      x1, 0(x7)
    sw      x2, 4(x7)
    sw      x3, 8(x7)
    sw      x5, 12(x7)

    //
    // Assert
    //
    RVMODEL_IO_ASSERT_GPR_EQ(x7, x2,  0x00000012)
    RVMODEL_IO_ASSERT_GPR_EQ(x7, x3,  0x00000042)
    RVMODEL_IO_ASSERT_GPR_EQ(x7, x5, 0x001101B3)

    RVMODEL_IO_WRITE_STR(x15, "# Test part A1  - Complete\n");

    RVMODEL_IO_WRITE_STR(x15, "# Test End\n")

#endif

 # ---------------------------------------------------------------------------------------------
    # HALT
    RVMODEL_HALT

RVTEST_CODE_END

RVTEST_DATA_BEGIN
# Input data section.
    .data
    .align 4

instr_A_src:
    add     x3, x2, x1

test_A_data:
    .word 0x30
    .word 0x12
RVTEST_DATA_END


# Output data section.
RVMODEL_DATA_BEGIN
rvtest_sig_begin:
sig_begin_canary:
CANARY;
test_A_res:
    .fill 4, 4, 0xdeadbeef

#ifdef rvtest_mtrap_routine
mtrap_sigptr:
  .fill 4, 4, 0xdeadbeef
#endif

#ifdef rvtest_gpr_save
gpr_save:
    .fill 32*(XLEN/32), 4, 0xdeadbeef
#endif

sig_end_canary:
CANARY;
rvtest_sig_end:
RVMODEL_DATA_END
