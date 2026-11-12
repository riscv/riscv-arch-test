// rvmodel_macros.h
// RVMODEL macro definitions for the NEORV32 processor in .github/scripts/neorv32-act-tb.sv,
// stnolting/neorv32 v1.13.7 (b1f307244928161a3fca1a010af11d5a736b5339).
// Copyright (c) 2026, Harvey Mudd College
// SPDX-License-Identifier: Apache-2.0

#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

#define RVMODEL_DATA_SECTION

#define STANDARD_SM_SUPPORTED

// Testbench registers on the external bus, in the uncached region that starts at CACHE_UC_BASE
// (0xF0000000), so stores reach the testbench in program order.
.EQU NEORV32_TB_CONSOLE, 0xF0000000
.EQU NEORV32_TB_EXIT,    0xF0000004
.EQU NEORV32_TB_MEI,     0xF0000008

##### TERMINATION #####

// A store to the exit register ends the simulation; 0 means pass.
#define RVMODEL_HALT_PASS        \
  li t0, NEORV32_TB_EXIT        ;\
  sw x0, 0(t0)                  ;\
  self_loop_pass:               ;\
    j self_loop_pass            ;

#define RVMODEL_HALT_FAIL        \
  li t0, NEORV32_TB_EXIT        ;\
  li t1, 1                      ;\
  sw t1, 0(t0)                  ;\
  self_loop_fail:               ;\
    j self_loop_fail            ;

##### IO #####

#define RVMODEL_IO_WRITE_STR(_R1, _R2, _R3, _STR_PTR) \
1:                           ;                        \
  lbu  _R1, 0(_STR_PTR)      ; /* Load byte */        \
  beqz _R1, 3f               ; /* Exit if null */     \
2:                           ;                        \
  li   _R2, NEORV32_TB_CONSOLE ;                      \
  sb   _R1, 0(_R2)           ;                        \
  addi _STR_PTR, _STR_PTR, 1 ; /* Next char */        \
  j 1b                       ; /* Loop */             \
3:

##### Access faults #####

// The testbench answers every external-bus address outside RAM and its three registers with a
// bus error. This one is uncached, so the instruction cache does not turn a fetch from it into a
// block refill, and the fault is reported at the exact address.
//   https://github.com/stnolting/neorv32/blob/b1f307244928161a3fca1a010af11d5a736b5339/docs/datasheet/soc_icache.adoc#L76-L84
#define RVMODEL_ACCESS_FAULT_ADDRESS 0xF0001000

##### Interrupt Latency #####

#define RVMODEL_INTERRUPT_LATENCY 10

##### Machine Timer #####

// The CLINT MTIMER increments once per clock cycle.
//   https://github.com/stnolting/neorv32/blob/b1f307244928161a3fca1a010af11d5a736b5339/docs/datasheet/soc_clint.adoc#L42-L77
#define RVMODEL_MTIME_ADDRESS     0xFFF4BFF8
#define RVMODEL_MTIMECMP_ADDRESS  0xFFF44000
// From U-mode, RVTEST_SET_MTIME_INT_SOON_U makes several T-SBI calls, each taking a few thousand
// cycles on this multi-cycle core, and the interrupt must not fire before the last one returns.
#define RVMODEL_TIMER_INT_SOON_DELAY 20000

##### Machine Interrupts #####

// CLINT MSWI register for hart 0.
#define RVMODEL_MSIP_ADDRESS      0xFFF40000

// The testbench drives irq_mei_i from bit 0 of its MEI register.
#define RVMODEL_SET_MEXT_INT(_R1, _R2)                                        \
    li _R1, NEORV32_TB_MEI             ;                                      \
    li _R2, 1                          ;                                      \
    sw _R2, 0(_R1)

#define RVMODEL_CLR_MEXT_INT(_R1, _R2)                                        \
    li _R1, NEORV32_TB_MEI             ;                                      \
    sw zero, 0(_R1)

#endif // _RVMODEL_MACROS_H
