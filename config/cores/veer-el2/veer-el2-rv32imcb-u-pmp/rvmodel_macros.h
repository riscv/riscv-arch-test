# rvmodel_macros.h
# RVMODEL macro definitions for the CHIPS Alliance VeeR EL2 core
# Written against Cores-VeeR-EL2 commit 925f3a34bdadc8f28b12a70cfb73e043b0f5ef3d
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0

#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

#define RVMODEL_DATA_SECTION

#define STANDARD_SM_SUPPORTED

# The testbench console/termination mailbox.
#   https://github.com/chipsalliance/Cores-VeeR-EL2/blob/925f3a34/testbench/tb_top.sv#L100
.EQU VEER_MAILBOX, 0xd0580000

# The PIC and the external interrupt source that the testbench drives for the tests.
# Source 1 is only ever pulsed by the testbench, so source 3 is used.
.EQU VEER_PIC_MEIPL, 0xf00c0000
.EQU VEER_PIC_MEIE, 0xf00c2000
.EQU VEER_EXT_INT_SRC, 3

##### STARTUP #####

# Program the region attributes in mrac (0x7C0) as VeeR's hello_world does, so that the
# mailbox region is side-effect and console stores are not merged in the store buffer.
#   https://github.com/chipsalliance/Cores-VeeR-EL2/blob/925f3a34/testbench/asm/hello_world.s#L41
# Give the external interrupt source priority 15 and enable it in the PIC. The gateway
# resets to level-triggered, active-high, and the threshold (meipt) resets to 0.
#   https://github.com/chipsalliance/Cores-VeeR-EL2/blob/925f3a34/docs/source/interrupts.md#L139-L149
#define RVMODEL_BOOT \
  li t0, 0x5f555555                            ;\
  csrw 0x7c0, t0                               ;\
  li t0, VEER_PIC_MEIPL + 4 * VEER_EXT_INT_SRC ;\
  li t1, 15                                    ;\
  sw t1, 0(t0)                                 ;\
  li t0, VEER_PIC_MEIE + 4 * VEER_EXT_INT_SRC  ;\
  li t1, 1                                     ;\
  sw t1, 0(t0)                                 ;

##### TERMINATION #####

# A byte store of 0xFF to the mailbox ends the simulation with TEST_PASSED.
#   https://github.com/chipsalliance/Cores-VeeR-EL2/blob/925f3a34/testbench/tb_top.sv#L1005
#define RVMODEL_HALT_PASS  \
  li t0, VEER_MAILBOX     ;\
  li t1, 0xff             ;\
  sb t1, 0(t0)            ;\
  self_loop_pass:         ;\
    j self_loop_pass      ;

# A byte store of 0x01 ends the simulation with TEST_FAILED.
#   https://github.com/chipsalliance/Cores-VeeR-EL2/blob/925f3a34/testbench/tb_top.sv#L997
#define RVMODEL_HALT_FAIL \
  li t0, VEER_MAILBOX     ;\
  li t1, 0x1              ;\
  sb t1, 0(t0)            ;\
  self_loop_fail:         ;\
    j self_loop_fail      ;

##### IO #####

# Byte stores of 0x06..0x7E to the mailbox are echoed to the console.
#   https://github.com/chipsalliance/Cores-VeeR-EL2/blob/925f3a34/testbench/tb_top.sv#L771
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

# Not defined: the tests fetch, load and store at one address, and no EL2 address faults on
# all three. Fetches fault only in the ICCM region (0xE) outside the ICCM, loads and stores
# only in the DCCM/PIC region (0xF) outside the DCCM and PIC, and the testbench backs every
# other address with memory.
#   https://github.com/chipsalliance/Cores-VeeR-EL2/blob/925f3a34/docs/source/memory-map.md#L265-L335

##### Interrupt Latency #####

#define RVMODEL_INTERRUPT_LATENCY 10

##### Machine Timer #####

# EL2 has no mtime or mtimecmp; the SoC must provide them and the testbench does not.
#define RVMODEL_TIMER_INT_SOON_DELAY 100

##### Machine Interrupts #####

# A word store of 0x81 | (N << 8) to the mailbox raises external interrupt source N, and 0x90
# lowers every interrupt line. 0x80, which lowers one source, also pulses NMI, so it is not
# used. The testbench only pulses the soft and timer lines for one cycle, so MSI is not tested.
#   https://github.com/chipsalliance/Cores-VeeR-EL2/blob/925f3a34/testbench/tb_top.sv#L825-L898
#define RVMODEL_SET_MEXT_INT(_R1, _R2)          \
  li _R1, 0x81 | (VEER_EXT_INT_SRC << 8)       ;\
  li _R2, VEER_MAILBOX                         ;\
  sw _R1, 0(_R2)                               ;

#define RVMODEL_CLR_MEXT_INT(_R1, _R2)          \
  li _R1, 0x90                                 ;\
  li _R2, VEER_MAILBOX                         ;\
  sw _R1, 0(_R2)                               ;

#endif // _RVMODEL_MACROS_H
