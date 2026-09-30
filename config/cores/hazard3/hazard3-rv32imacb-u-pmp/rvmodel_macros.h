// rvmodel_macros.h
// RVMODEL macro definitions for Hazard3 in its Verilator testbench,
// Wren6991/Hazard3 commit ba0c83c657a21f2e9946cf02cbc6c8d3d9a7dab6.
// Copyright (c) 2026, Harvey Mudd College
// SPDX-License-Identifier: Apache-2.0

#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

#define RVMODEL_DATA_SECTION

#define STANDARD_SM_SUPPORTED

// Testbench IO registers:
// https://github.com/Wren6991/Hazard3/blob/ba0c83c657a21f2e9946cf02cbc6c8d3d9a7dab6/test/sim/tb_common/include/tb_constants.h#L15-L32
.EQU H3_IO_BASE,        0xc0000000
.EQU H3_IO_PRINT_CHAR,  0x000
.EQU H3_IO_EXIT,        0x008
.EQU H3_IO_SET_SOFTIRQ, 0x010
.EQU H3_IO_CLR_SOFTIRQ, 0x014
.EQU H3_IO_GLOBMON_EN,  0x018
.EQU H3_IO_SET_IRQ,     0x020
.EQU H3_IO_CLR_IRQ,     0x030

##### STARTUP #####

// mcountinhibit.CY and IR reset to 1. The testbench's global exclusive monitor is off at
// reset, and until it is enabled every exclusive store reports success.
#define RVMODEL_BOOT \
  csrw mcountinhibit, zero                ;\
  li   t0, H3_IO_BASE                     ;\
  li   t1, 1                              ;\
  sw   t1, H3_IO_GLOBMON_EN(t0)           ;

// The testbench returns a bus error for every address outside RAM and the IO window.
#define RVMODEL_ACCESS_FAULT_ADDRESS 0x90000000

##### TERMINATION #####

// With --cpuret, the word written to IO_EXIT is the testbench's exit status.
#define RVMODEL_HALT_PASS  \
  li t0, H3_IO_BASE       ;\
  sw x0, H3_IO_EXIT(t0)   ;\
  self_loop_pass:         ;\
    j self_loop_pass      ;

#define RVMODEL_HALT_FAIL \
  li t0, H3_IO_BASE       ;\
  li t1, 1                ;\
  sw t1, H3_IO_EXIT(t0)   ;\
  self_loop_fail:         ;\
    j self_loop_fail      ;

##### IO #####

#define RVMODEL_IO_WRITE_STR(_R1, _R2, _R3, _STR_PTR) \
1:                           ;                        \
  lbu  _R1, 0(_STR_PTR)      ; /* Load byte */        \
  beqz _R1, 3f               ; /* Exit if null */     \
2:                           ;                        \
  li   _R2, H3_IO_BASE       ;                        \
  sb   _R1, H3_IO_PRINT_CHAR(_R2) ;                   \
  addi _STR_PTR, _STR_PTR, 1 ; /* Next char */        \
  j 1b                       ; /* Loop */             \
3:

##### Interrupt Latency #####

#define RVMODEL_INTERRUPT_LATENCY 10

##### Machine Timer #####

// The testbench's mtime advances once per cycle.
#define RVMODEL_MAX_CYCLES_PER_TIMER_TICK 1

// From U-mode, RVTEST_SET_MTIME_INT_SOON_U makes several T-SBI calls of about 900 cycles
// each, and the interrupt must not fire before the last one returns.
#define RVMODEL_TIMER_INT_SOON_DELAY 5000

#define RVMODEL_MTIME_ADDRESS     0xc0000100
#define RVMODEL_MTIMECMP_ADDRESS  0xc0000108

##### Machine Interrupts #####

// With Xh3irq off, the core ORs its irq inputs into mip.MEIP.
#define RVMODEL_SET_MEXT_INT(_R1, _R2)                                        \
    li _R1, H3_IO_BASE                 ;                                      \
    li _R2, 1                          ;                                      \
    sw _R2, H3_IO_SET_IRQ(_R1)

#define RVMODEL_CLR_MEXT_INT(_R1, _R2)                                        \
    li _R1, H3_IO_BASE                 ;                                      \
    li _R2, 1                          ;                                      \
    sw _R2, H3_IO_CLR_IRQ(_R1)

#define RVMODEL_SET_MSW_INT(_R1, _R2)                                         \
    li _R1, H3_IO_BASE                 ;                                      \
    li _R2, 1                          ;                                      \
    sw _R2, H3_IO_SET_SOFTIRQ(_R1)

#define RVMODEL_CLR_MSW_INT(_R1, _R2)                                         \
    li _R1, H3_IO_BASE                 ;                                      \
    li _R2, 1                          ;                                      \
    sw _R2, H3_IO_CLR_SOFTIRQ(_R1)

#endif // _RVMODEL_MACROS_H
