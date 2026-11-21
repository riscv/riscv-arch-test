// rvmodel_macros.h
// RVMODEL macro definitions for Shakti E-class in its base-sim SoC under Verilator,
// shaktiproject/cores/e-class commit e8a0dfd2d1c4907c74fb58432e379016871fdd3a.
// Copyright (c) 2026, Harvey Mudd College
// SPDX-License-Identifier: Apache-2.0

#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

#define RVMODEL_DATA_SECTION

#define STANDARD_SM_SUPPORTED

// base-sim memory map:
// https://gitlab.com/shaktiproject/cores/e-class/-/blob/e8a0dfd2d1c4907c74fb58432e379016871fdd3a/base-sim/Soc.defines#L22-L33
// UART registers (devices/uart/uart.defines at devices 5.0.2): TX data at 0x4, status at 0xC
// with bit 0 = transmission done and bit 1 = transmit FIFO not full.
.EQU SHAKTI_UART_BASE,   0x11300
.EQU SHAKTI_UART_TX,     0x4
.EQU SHAKTI_UART_STATUS, 0xc
// A write to offset 0xC of the signature-dump device ends the simulation (base-sim/sign_dump.bsv).
.EQU SHAKTI_END_SIM,     0x2000c
// CLINT (devices/clint/clint.defines): msip at +0, mtimecmp at +0x4000, mtime at +0xBFF8.
.EQU SHAKTI_CLINT_BASE,  0x2000000

##### STARTUP #####

// mtimecmp resets to 0 while mtime counts up from 0, so mip.MTIP is set from reset. Park
// mtimecmp at its maximum until a test arms it.
#define RVMODEL_BOOT \
  li   t0, SHAKTI_CLINT_BASE + 0x4000    ;\
  li   t1, -1                            ;\
  sw   t1, 4(t0)                         ;\
  sw   t1, 0(t0)                         ;

// The fabric sends every address outside the memory map to an error slave, which answers with
// a bus error.
#define RVMODEL_ACCESS_FAULT_ADDRESS 0x90000000

##### TERMINATION #####

// The testbench has no exit status. Wait until the UART has sent the last character and the
// testbench's receiving UART has had time to take it (one character is about 800 cycles), then
// end the simulation. run-shakti.sh passes the test only if the RVCP-SUMMARY line says PASSED.
#define SHAKTI_END_SIMULATION         \
  li   t0, SHAKTI_UART_BASE          ;\
1:                                   ;\
  lbu  t1, SHAKTI_UART_STATUS(t0)    ;\
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
  lbu  _R3, SHAKTI_UART_STATUS(_R2) ; /* Wait for FIFO space */    \
  andi _R3, _R3, 2                ;                                \
  beqz _R3, 2b                    ;                                \
  sb   _R1, SHAKTI_UART_TX(_R2)   ;                                \
  addi _STR_PTR, _STR_PTR, 1      ; /* Next char */                \
  j 1b                            ; /* Loop */                     \
3:

##### Interrupt Latency #####

#define RVMODEL_INTERRUPT_LATENCY 20

##### Machine Timer #####

// mtime counts once every 16 cycles. From U-mode, RVTEST_SET_MTIME_INT_SOON_U makes several
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

#endif // _RVMODEL_MACROS_H
