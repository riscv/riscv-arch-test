# rvmodel_macros.h
# RVMODEL macro definitions for the CHIPS Alliance VeeR EH2 core
# Written against Cores-VeeR-EH2 commit a7203d02d4774c9b8aa08b4827ec300d2c80a388
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0

#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

#define RVMODEL_DATA_SECTION

#define STANDARD_SM_SUPPORTED

# The testbench console/termination mailbox.
#   Quote: "#define STDOUT 0xd0580000"
#   https://github.com/chipsalliance/Cores-VeeR-EH2/blob/a7203d02/testbench/asm/hello_world.s#L23
.EQU VEER_MAILBOX, 0xd0580000

##### STARTUP #####

# Program mrac (0x7C0) as VeeR's own hello_world does.
#   Quote: "// Enable Caches in MRAC / li x1, 0x5f555555 / csrw 0x7c0, x1"
#   https://github.com/chipsalliance/Cores-VeeR-EH2/blob/a7203d02/testbench/asm/hello_world.s#L73-L75
# Each 256 MB region gets two bits in mrac: {side-effect, cacheable}. 0x5F555555 makes
# every region cacheable except 0xC and 0xD (the mailbox), whose value 11 the hardware
# maps to 10: side-effect and not cacheable. This keeps console byte stores from being
# merged in the store buffer.
#   https://github.com/chipsalliance/Cores-VeeR-EH2/blob/a7203d02/docs/source/memory-map.md#L681-L684
#define RVMODEL_BOOT \
  li t0, 0x5f555555       ;\
  csrw 0x7c0, t0          ;

##### TERMINATION #####

# A byte store of 0xFF to the mailbox makes the testbench print TEST_PASSED and $finish.
#   Quote: "if(mailbox_write && WriteData[7:0] == 8'hFF) begin"
#   https://github.com/chipsalliance/Cores-VeeR-EH2/blob/a7203d02/testbench/tb_top.sv#L372
#define RVMODEL_HALT_PASS  \
  li t0, VEER_MAILBOX     ;\
  li t1, 0xff             ;\
  sb t1, 0(t0)            ;\
  self_loop_pass:         ;\
    j self_loop_pass      ;

# A byte store of 0x01 takes the testbench failure path.
#   Quote: "else if(mailbox_write && WriteData[7:0] == 8'h01) begin"
#   https://github.com/chipsalliance/Cores-VeeR-EH2/blob/a7203d02/testbench/tb_top.sv#L380
#define RVMODEL_HALT_FAIL \
  li t0, VEER_MAILBOX     ;\
  li t1, 0x1              ;\
  sb t1, 0(t0)            ;\
  self_loop_fail:         ;\
    j self_loop_fail      ;

##### IO #####

# Byte stores in the range 0x06..0x7E are echoed to stdout and to console.log. ACT's
# RVCP-SUMMARY strings are printable ASCII plus \n (0x0A).
#   Quote: "assign mailbox_data_val = WriteData[7:0] > 8'h5 && WriteData[7:0] < 8'h7f;"
#   https://github.com/chipsalliance/Cores-VeeR-EH2/blob/a7203d02/testbench/tb_top.sv#L336
#define RVMODEL_IO_WRITE_STR(_R1, _R2, _R3, _STR_PTR) \
1:                           ;                        \
  lbu  _R1, 0(_STR_PTR)      ; /* Load byte */        \
  beqz _R1, 3f               ; /* Exit if null */     \
2:                           ;                        \
  li   _R2, VEER_MAILBOX     ;                        \
  sb   _R1, 0(_R2)           ;                        \
  addi _STR_PTR, _STR_PTR, 1 ; /* Next char */        \
  j 1b                       ; /* Loop */             \
3:

##### Access faults #####

# With no access windows requested, veer.config enables four instruction and four data
# access windows that leave region 0x9 as a hole (RV_EXTERNAL_MEM_HOLE = 0x90000000).
# Fetches, loads and stores there raise access faults.
#   Quote: "# Create the memory map hole for random testing"
#   https://github.com/chipsalliance/Cores-VeeR-EH2/blob/a7203d02/configs/veer.config#L1944-L1999
#   https://github.com/chipsalliance/Cores-VeeR-EH2/blob/a7203d02/docs/source/memory-map.md#L182-L190
#define RVMODEL_ACCESS_FAULT_ADDRESS 0x90000000

##### Interrupt Latency #####

#define RVMODEL_INTERRUPT_LATENCY 10

##### Machine Timer #####

# VeeR EH2 has no mtime/mtimecmp and the testbench supplies none, so RVMODEL_MTIME_ADDRESS
# and RVMODEL_MTIMECMP_ADDRESS are not defined.
#define RVMODEL_TIMER_INT_SOON_DELAY 100

##### Machine Interrupts #####

# The testbench ties the external, timer and software interrupt inputs to 0, so no
# RVMODEL_SET/CLR_*_INT macros are defined (UDB MEI/MSI/MTI_INTR_IMPL are false).

#endif // _RVMODEL_MACROS_H
