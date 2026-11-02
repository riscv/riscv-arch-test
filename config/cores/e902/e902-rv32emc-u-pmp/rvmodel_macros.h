# rvmodel_macros.h
# RVMODEL macro definitions for the XuanTie OpenE902 in its smart_run SoC testbench
# Written against T-head-Semi/opene902 commit 991836411b405ac6a0a8d7668f2f5de6fa2a5b8c
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0

#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

#define RVMODEL_DATA_SECTION

#define STANDARD_SM_SUPPORTED

# The testbench prints the low byte of every store to E902_CONSOLE, and ends the
# simulation when the stored word is 0xFFF (pass) or 0xEEE (fail).
#   https://github.com/T-head-Semi/opene902/blob/991836411b405ac6a0a8d7668f2f5de6fa2a5b8c/smart_run/logical/tb/tb.v#L183-L227
.EQU E902_CONSOLE,   0x6000FFF8
.EQU E902_HALT_PASS, 0xFFF
.EQU E902_HALT_FAIL, 0xEEE

# Top 4 KB of the instruction-bus SRAM, outside the linked image (see link.ld).
.EQU E902_TRAP_VECTOR, 0x0007F000

##### STARTUP #####

# mtvec resets to 0, the start of the test image, and always reads back MODE = 3, so the
# trap prolog's write never verifies and the prolog copies its trampoline to the mtvec
# target instead.  Point mtvec at a 64-byte aligned block outside the image first.
#   https://github.com/T-head-Semi/opene902/blob/991836411b405ac6a0a8d7668f2f5de6fa2a5b8c/E902_RTL_FACTORY/gen_rtl/cp0/rtl/cr_cp0_oreg.v#L490-L506
#define RVMODEL_BOOT              \
  li   t0, E902_TRAP_VECTOR      ;\
  csrw mtvec, t0                 ;

##### INVISIBLE TRAPS #####

# E902 does not implement mcounteren (0x306), mhpmevent3-31 (0x323-0x33F),
# mhpmcounter3-31 (0xB03-0xB1F) or mhpmcounter3h-31h (0xB83-0xB9F).  The privileged
# specification requires them, read-only zero at the least, but the CSR decoder sends
# them to its illegal-instruction default, and rvtest_setup.h writes them on every boot.
#   https://github.com/T-head-Semi/opene902/blob/991836411b405ac6a0a8d7668f2f5de6fa2a5b8c/E902_RTL_FACTORY/gen_rtl/cp0/rtl/cr_cp0_iui.v#L539-L590
# This handler emulates an M-mode CSR instruction on any of them as read-only zero: rd
# gets 0 and the write is dropped.  From U-mode they stay illegal, as the specification
# requires.
#define RVMODEL_INVISIBLE_TRAP_HANDLER(_PC_REG, _INSTRUCTION_REG, _ACTION_REG, _DEST_REG, _VALUE_REG) \
  andi _VALUE_REG, _INSTRUCTION_REG, 0x7f   /* SYSTEM opcode */                 ;\
  li   _DEST_REG, 0x73                                                          ;\
  bne  _VALUE_REG, _DEST_REG, 1f                                                ;\
  srli _VALUE_REG, _INSTRUCTION_REG, 12     /* funct3[1:0] != 0: a CSR access */ ;\
  andi _VALUE_REG, _VALUE_REG, 3                                                ;\
  beqz _VALUE_REG, 1f                                                           ;\
  csrr _VALUE_REG, mstatus                  /* trapped from M-mode? */          ;\
  li   _DEST_REG, MSTATUS_MPP                                                   ;\
  and  _VALUE_REG, _VALUE_REG, _DEST_REG                                        ;\
  bne  _VALUE_REG, _DEST_REG, 1f                                                ;\
  srli _VALUE_REG, _INSTRUCTION_REG, 20     /* CSR number */                    ;\
  li   _DEST_REG, 0x306                     /* mcounteren */                    ;\
  beq  _VALUE_REG, _DEST_REG, 2f                                                ;\
  addi _DEST_REG, _VALUE_REG, -0x323        /* mhpmevent3-31 */                 ;\
  sltiu _DEST_REG, _DEST_REG, 29                                                ;\
  bnez _DEST_REG, 2f                                                            ;\
  li   _DEST_REG, 0xB03                     /* mhpmcounter3-31 */               ;\
  sub  _DEST_REG, _VALUE_REG, _DEST_REG                                         ;\
  sltiu _DEST_REG, _DEST_REG, 29                                                ;\
  bnez _DEST_REG, 2f                                                            ;\
  li   _DEST_REG, 0xB83                     /* mhpmcounter3h-31h */             ;\
  sub  _DEST_REG, _VALUE_REG, _DEST_REG                                         ;\
  sltiu _DEST_REG, _DEST_REG, 29                                                ;\
  beqz _DEST_REG, 1f                                                            ;\
2:                                                                              ;\
  li   _VALUE_REG, 0                                                            ;\
  srli _DEST_REG, _INSTRUCTION_REG, 7       /* rd */                            ;\
  andi _DEST_REG, _DEST_REG, 0x1f                                               ;\
  li   _ACTION_REG, 2                                                           ;\
1:

##### TERMINATION #####

#define RVMODEL_HALT_PASS  \
  li t0, E902_CONSOLE     ;\
  li t1, E902_HALT_PASS   ;\
  sw t1, 0(t0)            ;\
  self_loop_pass:         ;\
    j self_loop_pass      ;

#define RVMODEL_HALT_FAIL \
  li t0, E902_CONSOLE     ;\
  li t1, E902_HALT_FAIL   ;\
  sw t1, 0(t0)            ;\
  self_loop_fail:         ;\
    j self_loop_fail      ;

##### IO #####

#define RVMODEL_IO_WRITE_STR(_R1, _R2, _R3, _STR_PTR) \
1:                           ;                        \
  lbu  _R1, 0(_STR_PTR)      ; /* Load byte */        \
  beqz _R1, 3f               ; /* Exit if null */     \
2:                           ;                        \
  li   _R2, E902_CONSOLE     ;                        \
  sb   _R1, 0(_R2)           ;                        \
  addi _STR_PTR, _STR_PTR, 1 ; /* Next char */        \
  j 1b                       ; /* Loop */             \
3:

##### Access faults #####

# The system bus sends every address outside 0x2000_0000-0x207F_FFFF, 0x4000_0000-0x4FFF_FFFF
# and 0x6000_0000-0x600F_FFFF to an error slave that answers every transfer with ERROR.
# 0x3000_0000 is above the instruction-bus window (0x0000_0000-0x1FFF_FFFF) and outside
# every sail.json memory region.
#   https://github.com/T-head-Semi/opene902/blob/991836411b405ac6a0a8d7668f2f5de6fa2a5b8c/smart_run/logical/ahb/ahb.v#L277-L286
#   https://github.com/T-head-Semi/opene902/blob/991836411b405ac6a0a8d7668f2f5de6fa2a5b8c/smart_run/logical/common/err_gen.v#L77
#define RVMODEL_ACCESS_FAULT_ADDRESS 0x30000000

##### Interrupt Latency #####

#define RVMODEL_INTERRUPT_LATENCY 10

##### Machine Timer #####

# RVMODEL_MTIME_ADDRESS and RVMODEL_MTIMECMP_ADDRESS are undefined.  The CLINT timer
# interrupt reaches the core only through the CLIC, and in CLIC mode mie and mip read 0,
# so the standard timer-interrupt tests cannot run.
#define RVMODEL_TIMER_INT_SOON_DELAY 100

#endif // _RVMODEL_MACROS_H
