// Copyright (c) 2023. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
// -----------
//
// This assembly file tests the fli.d instruction
// for the following ISA configurations:
// * RV32ID_Zfa
// * RV64ID_Zfa

#include "model_test.h"
#include "arch_test.h"

RVTEST_ISA("RV32ID_Zfa,RV64ID_Zfa")

.section .text.init
.globl rvtest_entry_point
rvtest_entry_point:

RVMODEL_BOOT

RVTEST_CODE_BEGIN

#ifdef TEST_CASE_1

RVTEST_CASE(0,"//check ISA:=regex(.*I.*D.*.Zfa.*);def TEST_CASE_1=True;",fli.d_b1)

// Registers with a special purpose
#define SIG_BASEREG x1
#define FCSR_REG x2
#define DATA_BASEREG x3

// Initialize the FPU
RVTEST_FP_ENABLE()
// Prepare the DATA_BASEREG register
RVTEST_VALBASEUPD(DATA_BASEREG, dataset_tc1)
// Prepare the SIG_BASEREG register
RVTEST_SIGBASE(SIG_BASEREG, signature_tc1)

// FLI.D loads a pre-defined constant into a FP register.
// FLI.D has the following inputs and outputs:
// - input rs1: 5-bit immediate holding the constants ID
// - output fld: FP register

// TEST_CASE_FLI_D executes a FLI.D insn and stores the result in the sig
// 1) the FCSR_OLD value will be store into FCSR using FCSR_REG
// 2) fli.d is executed using FLD as dest register and FLI_CONST as constant
// 3) The constents of FLD and FCSR are stored in the signature
#define TEST_CASE_FLI_D(fld, fli_const, fcsr_old, fcsr_reg) \
    li fcsr_reg, fcsr_old ;\
    csrw fcsr, fcsr_reg   ;\
    fli.d fld, fli_const  ;\
    csrr fcsr_reg, fcsr   ;\
    RVTEST_SIGUPD_F(SIG_BASEREG, fld, fcsr_reg) ;\

// Below we have one instruction test per constant

inst_0:
TEST_CASE_FLI_D(f16, -0x1p+0, 0, FCSR_REG)

inst_1:
TEST_CASE_FLI_D(f17, min, 0, FCSR_REG)

inst_2:
TEST_CASE_FLI_D(f18, 0x1p-16, 0, FCSR_REG)

inst_3:
TEST_CASE_FLI_D(f19, 0x1p-15, 0, FCSR_REG)

inst_4:
TEST_CASE_FLI_D(f20, 0x1p-8, 0, FCSR_REG)

inst_5:
TEST_CASE_FLI_D(f21, 0x1p-7, 0, FCSR_REG)

inst_6:
TEST_CASE_FLI_D(f22, 0x1p-4, 0, FCSR_REG)

inst_7:
TEST_CASE_FLI_D(f23, 0x1p-3, 0, FCSR_REG)

inst_8:
TEST_CASE_FLI_D(f24, 0x1p-2, 0, FCSR_REG)

inst_9:
TEST_CASE_FLI_D(f25, 0x1.4p-2, 0, FCSR_REG)

inst_10:
TEST_CASE_FLI_D(f26, 0x1.8p-2, 0, FCSR_REG)

inst_11:
TEST_CASE_FLI_D(f27, 0x1.cp-2, 0, FCSR_REG)

inst_12:
TEST_CASE_FLI_D(f28, 0x1p-1, 0, FCSR_REG)

inst_13:
TEST_CASE_FLI_D(f29, 0x1.4p-1, 0, FCSR_REG)

inst_14:
TEST_CASE_FLI_D(f30, 0x1.8p-1, 0, FCSR_REG)

inst_15:
TEST_CASE_FLI_D(f31, 0x1.cp-1, 0, FCSR_REG)

inst_16:
TEST_CASE_FLI_D(f0, 0x1p0, 0, FCSR_REG)

inst_17:
TEST_CASE_FLI_D(f1, 0x1.4p+0, 0, FCSR_REG)

inst_18:
TEST_CASE_FLI_D(f2, 0x1.8p+0, 0, FCSR_REG)

inst_19:
TEST_CASE_FLI_D(f3, 0x1.cp+0, 0, FCSR_REG)

inst_20:
TEST_CASE_FLI_D(f4, 0x1p+1, 0, FCSR_REG)

inst_21:
TEST_CASE_FLI_D(f5, 0x1.4p+1, 0, FCSR_REG)

inst_22:
TEST_CASE_FLI_D(f6, 0x1.8p+1, 0, FCSR_REG)

inst_23:
TEST_CASE_FLI_D(f7, 0x1p+2, 0, FCSR_REG)

inst_24:
TEST_CASE_FLI_D(f8, 0x1p+3, 0, FCSR_REG)

inst_25:
TEST_CASE_FLI_D(f9, 0x1p+4, 0, FCSR_REG)

inst_26:
TEST_CASE_FLI_D(f10, 0x1p+7, 0, FCSR_REG)

inst_27:
TEST_CASE_FLI_D(f11, 0x1p+8, 0, FCSR_REG)

inst_28:
TEST_CASE_FLI_D(f12, 0x1p+15, 0, FCSR_REG)

inst_29:
TEST_CASE_FLI_D(f13, 0x1p+16, 0, FCSR_REG)

inst_30:
TEST_CASE_FLI_D(f14, inf, 0, FCSR_REG)

inst_31:
TEST_CASE_FLI_D(f15, nan, 0, FCSR_REG)

#endif // TEST_CASE_1

RVTEST_CODE_END

RVMODEL_HALT

RVTEST_DATA_BEGIN
.word 0xbabecafe // trapreg_sv
.word 0xabecafeb // tramptbl_sv
.word 0xbecafeba // mtvec_save
.word 0xecafebab // mscratch_save
dataset_tc1:
/* empty */
RVTEST_DATA_END

RVMODEL_DATA_BEGIN
rvtest_sig_begin:
sig_begin_canary:
CANARY;

signature_tc1:
// We have 32 test cases and store for each test case:
// - 32-bit FP register (fld)
// - 32-bit FCSR content after the instruction
    .fill 64*((SIGALIGN)/4),4,0xdeadbeef

#ifdef rvtest_mtrap_routine

tsig_begin_canary:
CANARY;
tsig_begin_canary:
CANARY;
mtrap_sigptr:
    .fill 64*(XLEN/32),4,0xdeadbeef
tsig_end_canary:
CANARY;
tsig_end_canary:
CANARY;

#endif // rvtest_mtrap_routine

#ifdef rvtest_gpr_save

gpr_save:
    .fill 32*XLEN/32,4,0xdeadbeef

#endif // rvtest_gpr_save

sig_end_canary:
CANARY;
rvtest_sig_end:
RVMODEL_DATA_END
