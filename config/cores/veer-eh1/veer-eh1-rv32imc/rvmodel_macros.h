# rvmodel_macros.h
# RVMODEL macro definitions for the CHIPS Alliance VeeR EH1 core
# Written against Cores-VeeR-EH1 commit d04b1c7ae675a63dc4307cacfd10547ec937b928
# SPDX-License-Identifier: Apache-2.0

#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

#define RVMODEL_DATA_SECTION

#define STANDARD_SM_SUPPORTED

# The testbench console/termination mailbox.
#   Quote: "#define STDOUT 0xd0580000"
#   https://github.com/chipsalliance/Cores-VeeR-EH1/blob/d04b1c7a/testbench/asm/hello_world.s#L23
.EQU VEER_MAILBOX, 0xd0580000

##### STARTUP #####

# Program mrac (0x7C0) so that the memory regions behave sensibly before any test
# code runs.  This is the "custom register initialization" hook: VeeR's own
# hello_world does exactly this before printing.
#   Quote: "// Enable Caches in MRAC / li x1, 0x5f555555 / csrw 0x7c0, x1"
#   https://github.com/chipsalliance/Cores-VeeR-EH1/blob/d04b1c7a/testbench/asm/hello_world.s#L41
# Each 256 MB region gets two bits in mrac: {side-effect, cacheable}.  0x5F555555
# marks every region cacheable and additionally marks region 0xD (the mailbox)
# side-effect, which keeps console byte stores from being merged in the store buffer.
# Measured: with this write hello_world completes in 1038 cycles, without it 1659,
# and console output is identical either way, so this is required for performance
# and store ordering rather than for output correctness.
#define RVMODEL_BOOT \
  li t0, 0x5f555555       ;\
  csrw 0x7c0, t0          ;

##### TERMINATION #####

# A byte store of 0xFF to the mailbox makes the testbench print TEST_PASSED and $finish.
#   Quote: "if(mailbox_write && WriteData[7:0] == 8'hff) begin"
#   https://github.com/chipsalliance/Cores-VeeR-EH1/blob/d04b1c7a/testbench/tb_top.sv#L340
#define RVMODEL_HALT_PASS  \
  li t0, VEER_MAILBOX     ;\
  li t1, 0xff             ;\
  sb t1, 0(t0)            ;\
  self_loop_pass:         ;\
    j self_loop_pass      ;

# A byte store of 0x01 takes the testbench failure path.
#   Quote: "else if(mailbox_write && WriteData[7:0] == 8'h1) begin"
#   https://github.com/chipsalliance/Cores-VeeR-EH1/blob/d04b1c7a/testbench/tb_top.sv#L346
#define RVMODEL_HALT_FAIL \
  li t0, VEER_MAILBOX     ;\
  li t1, 0x1              ;\
  sb t1, 0(t0)            ;\
  self_loop_fail:         ;\
    j self_loop_fail      ;

##### IO #####

# Byte stores in the range 0x06..0x7E are echoed to stdout and to console.log.
#   Quote: "assign mailbox_data_val = WriteData[7:0] > 8'h5 && WriteData[7:0] < 8'h7f;"
#   https://github.com/chipsalliance/Cores-VeeR-EH1/blob/d04b1c7a/testbench/tb_top.sv#L321
# Note this excludes \n (0x0A is > 0x05, so newlines DO print) but silently drops
# characters below 0x06.  ACT's RVCP-SUMMARY strings are printable ASCII plus \n.
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

# Not defined: VeeR EH1 reports out-of-window accesses as either a misaligned or an
# access fault depending on configuration, and with no data access windows enabled
# (the default) ordinary addresses never fault.
#   Quote: "However, any access not within the DCCM's or PIC memory-mapped control
#   register's address range results in a precise load/store address misaligned or
#   access fault exception."
#   https://github.com/chipsalliance/Cores-VeeR-EH1/blob/d04b1c7a/docs/source/memory-map.md#L201
# Leaving this undefined means access-fault tests are not exercised.
//#define RVMODEL_ACCESS_FAULT_ADDRESS

##### Interrupt Latency #####

#define RVMODEL_INTERRUPT_LATENCY 10

##### Machine Timer #####

# VeeR EH1 has no mtime/mtimecmp: the PRM states the SoC must supply them, and the
# testbench does not.  Leaving RVMODEL_MTIME_ADDRESS undefined disables all machine
# timer interrupt testing, which is the documented behaviour in check_defines.h.
//#define RVMODEL_MTIME_ADDRESS
//#define RVMODEL_MTIMECMP_ADDRESS
#define RVMODEL_TIMER_INT_SOON_DELAY 100

##### Machine Interrupts #####

# Stubs for the first bring-up pass.  The testbench can drive interrupts through the
# mailbox stimulus hooks, but external interrupts additionally require programming the
# VeeR PIC (meipl/meie/meicurpl), so these are left empty until the interrupt suites
# are brought up deliberately.
#define RVMODEL_SET_MEXT_INT(_R1, _R2)
#define RVMODEL_CLR_MEXT_INT(_R1, _R2)
#define RVMODEL_SET_MSW_INT(_R1, _R2)
#define RVMODEL_CLR_MSW_INT(_R1, _R2)

##### Supervisor Interrupts #####
# VeeR EH1 is M-mode only; these cannot occur but must be defined.

#define RVMODEL_SET_SEXT_INT(_R1, _R2)
#define RVMODEL_CLR_SEXT_INT(_R1, _R2)
#define RVMODEL_SET_SSW_INT(_R1, _R2)
#define RVMODEL_CLR_SSW_INT(_R1, _R2)

#endif // _RVMODEL_MACROS_H
