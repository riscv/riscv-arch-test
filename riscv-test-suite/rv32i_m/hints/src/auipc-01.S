/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 3, 2025
Description: This test verifies the auipc instruction as a hint whatever the value in the imm field, 
              rd should be zero and there should be no architectural change.
              */
#include "model_test.h"
#include "arch_test.h"
RVTEST_ISA("RV32I_Zicsr")

.section .text.init
.globl rvtest_entry_point
rvtest_entry_point:
RVMODEL_BOOT
RVTEST_CODE_BEGIN

#ifdef TEST_CASE_1

RVTEST_CASE(0,"//check ISA:=regex(.*32.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;",auipc)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: auipc ; dest:x0; immval:0x0
TEST_AUIPC(auipc,x0, 0x0, 0x0, x3, 0, x12)

inst_1:
// opcode: auipc ; dest:x0; immval:0xe
TEST_AUIPC(auipc,x0, 0xe000, 0xe, x3, 4, x12)

inst_2:
// opcode: auipc ; dest:x0 immval:0xfffff
TEST_AUIPC(auipc,x0, -0x1000, 0xfffff, x3, 8, x12)

inst_3:
// opcode: auipc ; dest:x0; immval:0x3
TEST_AUIPC(auipc,x0, 0x3000, 0x3, x3, 12, x12)

inst_4:
// opcode: auipc ; dest:x0; immval:0x55555
TEST_AUIPC(auipc,x0, 0x55555000, 0x55555, x3, 16, x12)

inst_5:
// opcode: auipc ; dest:x0 immval:0xaaaaa
TEST_AUIPC(auipc,x0, -0x55556000, 0xaaaaa, x3, 20, x12)

inst_6:
// opcode: auipc ; dest:x0; immval:0x5
TEST_AUIPC(auipc,x0, 0x5000, 0x5, x3, 24, x12)

inst_7:
// opcode: auipc ; dest:x0; immval:0x33333
TEST_AUIPC(auipc,x0, 0x33333000, 0x33333, x3, 28, x12)

inst_8:
// opcode: auipc ; dest:x0 immval:0x66666
TEST_AUIPC(auipc,x0, 0x66666000, 0x66666, x3, 32, x12)

inst_9:
// opcode: auipc ; dest:x0; immval:0x2d4
TEST_AUIPC(auipc,x0, 0x2d4000, 0x2d4, x3, 36, x12)

inst_10:
// opcode: auipc ; dest:x0; immval:0x3ff
TEST_AUIPC(auipc,x0, 0x3ff000, 0x3ff, x3, 40, x12)

inst_11:
// opcode: auipc ; dest:x0; immval:0x2
TEST_AUIPC(auipc,x0, 0x2000, 0x2, x3, 44, x12)

inst_12:
// opcode: auipc ; dest:x0 immval:0x55554
TEST_AUIPC(auipc,x0, 0x55554000, 0x55554, x3, 48, x12)

inst_13:
// opcode: auipc ; dest:x0 immval:0xaaaa9
TEST_AUIPC(auipc,x0, -0x55557000, 0xaaaa9, x3, 52, x12)

inst_14:
// opcode: auipc ; dest:x0; immval:0x4
TEST_AUIPC(auipc,x0, 0x4000, 0x4, x3, 56, x12)

inst_15:
// opcode: auipc ; dest:x0; immval:0x33332
TEST_AUIPC(auipc,x0, 0x33332000, 0x33332, x3, 60, x12)

inst_16:
// opcode: auipc ; dest:x0; immval:0x66665
TEST_AUIPC(auipc,x0, 0x66665000, 0x66665, x3, 64, x12)

inst_17:
// opcode: auipc ; dest:x0 immval:0x2d3
TEST_AUIPC(auipc,x0, 0x2d3000, 0x2d3, x3, 68, x12)

inst_18:
// opcode: auipc ; dest:x0; immval:0x3fe
TEST_AUIPC(auipc,x0, 0x3fe000, 0x3fe, x3, 72, x12)

inst_19:
// opcode: auipc ; dest:x0 immval:0x55556
TEST_AUIPC(auipc,x0, 0x55556000, 0x55556, x3, 76, x12)

inst_20:
// opcode: auipc ; dest:x0; immval:0xaaaab
TEST_AUIPC(auipc,x0, -0x55555000, 0xaaaab, x3, 80, x12)

RVTEST_SIGBASE( x30,signature_x30_1)
TEST_STORE_GPRS_AND_STATUS(x30)

#endif


RVTEST_CODE_END
RVMODEL_HALT
RVTEST_DATA_BEGIN

RVTEST_DATA_END


RVMODEL_DATA_BEGIN
rvtest_sig_begin:
sig_begin_canary:
CANARY;


signature_x31_1:
    .fill 32*(XLEN/32),4,0xdeadbeef

signature_x3_0:
    .fill 0*(XLEN/32),4,0xdeadbeef


signature_x3_1:
    .fill 32*(XLEN/32),4,0xdeadbeef



signature_x30_1:
    .fill 32*(XLEN/32),4,0xdeadbeef
    
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
