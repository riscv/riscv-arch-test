// rvmodel_macros.h
// RVMODEL macro definitions for Shakti C-class in its test_soc SoC under Verilator,
// shaktiproject/cores/c-class commit f52775317b0e6c16272f5c42d3dd7d52282f0e65.
// Copyright (c) 2026, Harvey Mudd College
// SPDX-License-Identifier: Apache-2.0

#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

#define RVMODEL_DATA_SECTION

#define STANDARD_SM_SUPPORTED

// test_soc memory map:
// https://gitlab.com/shaktiproject/cores/c-class/-/blob/f52775317b0e6c16272f5c42d3dd7d52282f0e65/test_soc/c64_c32/Soc.defines
// UART registers (devices/uart_v2/uart.defines at devices 9.0.8): TX data at 0x4, and a 16-bit
// status register at 0xC with bit 0 = transmitter empty and bit 1 = transmitter full. A byte
// load from the status register never completes, so it is read with lhu.
.EQU SHAKTI_UART_BASE,   0x11300
.EQU SHAKTI_UART_TX,     0x4
.EQU SHAKTI_UART_STATUS, 0xc
// A write to offset 0xC of the signature-dump device ends the simulation
// (test_soc/c64_c32/sign_dump.bsv). So does committing `j .` or `c.j .` (test_soc/c64_c32/TbSoc.bsv).
.EQU SHAKTI_END_SIM,     0x2000c
// CLINT (devices/clint/clint.defines): msip at +0, mtimecmp at +0x4000, mtime at +0xBFF8.
.EQU SHAKTI_CLINT_BASE,  0x2000000

// The fabric sends every address outside the memory map to an error slave, which answers with
// a bus error.
#define RVMODEL_ACCESS_FAULT_ADDRESS 0x40000000

##### TERMINATION #####

// The testbench has no exit status. Wait until the UART has sent the last character and the
// testbench's receiving UART has had time to take it (one character is about 800 cycles), then
// end the simulation. run-shakti.sh passes the test only if the RVCP-SUMMARY line says PASSED.
#define SHAKTI_END_SIMULATION         \
  li   t0, SHAKTI_UART_BASE          ;\
1:                                   ;\
  lhu  t1, SHAKTI_UART_STATUS(t0)    ;\
  andi t1, t1, 1                     ;\
  beqz t1, 1b                        ;\
  li   t1, 2000                      ;\
2:                                   ;\
  addi t1, t1, -1                    ;\
  bnez t1, 2b                        ;\
  li   t0, SHAKTI_END_SIM            ;\
  sw   x0, 0(t0)                     ;\
3:                                   ;\
  j 3b                               ;

#define RVMODEL_HALT_PASS SHAKTI_END_SIMULATION

#define RVMODEL_HALT_FAIL SHAKTI_END_SIMULATION

##### IO #####

#define RVMODEL_IO_WRITE_STR(_R1, _R2, _R3, _STR_PTR)              \
  li   _R2, SHAKTI_UART_BASE      ;                                \
1:                                ;                                \
  lbu  _R1, 0(_STR_PTR)           ; /* Load byte */                \
  beqz _R1, 3f                    ; /* Exit if null */             \
2:                                ;                                \
  lhu  _R3, SHAKTI_UART_STATUS(_R2) ; /* Wait while TX is full */ \
  andi _R3, _R3, 2                ;                                \
  bnez _R3, 2b                    ;                                \
  sb   _R1, SHAKTI_UART_TX(_R2)   ;                                \
  addi _STR_PTR, _STR_PTR, 1      ; /* Next char */                \
  j 1b                            ; /* Loop */                     \
3:

##### Interrupt Latency #####

#define RVMODEL_INTERRUPT_LATENCY 20

##### Machine Timer #####

// mtime counts once every 2 cycles. From U-mode, RVTEST_SET_MTIME_INT_SOON_U makes several
// T-SBI calls, and the interrupt must not fire before the last one returns.
#define RVMODEL_TIMER_INT_SOON_DELAY 1000

#define RVMODEL_MTIME_ADDRESS     0x0200bff8
#define RVMODEL_MTIMECMP_ADDRESS  0x02004000

##### Machine Interrupts #####

#define RVMODEL_MSIP_ADDRESS      0x02000000

// The installer adds byte registers to the signature-dump device and connects them to
// the core's external interrupt inputs. Each register independently sets or clears one input.
#define SHAKTI_SET_EXT_INT(_R1, _R2, _ADDRESS) \
  LI(_R1, _ADDRESS);                         \
  LI(_R2, 1);                                \
  sb _R2, 0(_R1);
#define SHAKTI_CLR_EXT_INT(_R1, _R2, _ADDRESS) \
  LI(_R1, _ADDRESS);                         \
  sb zero, 0(_R1);
#define RVMODEL_SET_MEXT_INT(_R1, _R2) SHAKTI_SET_EXT_INT(_R1, _R2, 0x20004)
#define RVMODEL_CLR_MEXT_INT(_R1, _R2) SHAKTI_CLR_EXT_INT(_R1, _R2, 0x20004)
#define RVMODEL_SET_SEXT_INT(_R1, _R2) SHAKTI_SET_EXT_INT(_R1, _R2, 0x20005)
#define RVMODEL_CLR_SEXT_INT(_R1, _R2) SHAKTI_CLR_EXT_INT(_R1, _R2, 0x20005)

#endif // _RVMODEL_MACROS_H
