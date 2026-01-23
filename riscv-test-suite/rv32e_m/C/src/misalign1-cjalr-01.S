// -----------
// Copyright (c) 2020. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
// -----------
//
// This assembly file tests the misaligned c.jalr instruction of the RISC-V C extension.
//
#include "model_test.h"
#include "arch_test.h"
RVTEST_ISA("RV32EC")

.section .text.init
.globl rvtest_entry_point
rvtest_entry_point:
RVMODEL_BOOT
RVTEST_CODE_BEGIN

#ifdef TEST_CASE_1

RVTEST_CASE(0,"//check ISA:=regex(.*32.*);check ISA:=regex(.*E.*C.*);def RVTEST_E = True;def TEST_CASE_1=True;",misalign1-cjalr)

RVTEST_SIGBASE( x10,signature_x10_1)

// ea_align == 1,
// opcode: jalr; op1:x6; align:1
// TEST_CJALR_OP(x11, x6, x10, 0)
5:					;
    LA(x6, 3f+1)				;
					;
2:  c.jalr x6				;
    xori x1,x1, 0x2			;
    j 4f				;
					;
3:  xori x1,x1, 0x3			;
					;
4: LA(x11, 5b)			;
   andi x11,x11,~(3)		;
    sub x1,x1,x11			;
    RVTEST_SIGUPD(x10,x1,0)

#endif


RVTEST_CODE_END
RVMODEL_HALT

RVTEST_DATA_BEGIN
.align 4

rvtest_data:
.word 0xbabecafe
.word 0xbabecafe
.word 0xbabecafe
.word 0xbabecafe
RVTEST_DATA_END


RVMODEL_DATA_BEGIN
rvtest_sig_begin:
sig_begin_canary:
CANARY;


signature_x10_1:
    .fill 0*(XLEN/32),4,0xdeadbeef


signature_x1_1:
    .fill 1*(XLEN/32),4,0xdeadbeef

#ifdef rvtest_mtrap_routine

tsig_begin_canary:
CANARY;
mtrap_sigptr:
    .fill 64*(XLEN/32),4,0xdeadbeef
tsig_end_canary:
CANARY;

#endif

#ifdef rvtest_gpr_save

gpr_save:
    .fill 32*(XLEN/32),4,0xdeadbeef

#endif

sig_end_canary:
CANARY;
rvtest_sig_end:
RVMODEL_DATA_END
