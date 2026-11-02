// rvmodel_macros.h
// RVMODEL macro definitions for NaxRiscv (naxriscv.Gen64 --withRvc --withFloat --withDouble) in
// NaxRiscv's own Verilator simulator, src/test/cpp/naxriscv, at SpinalHDL/NaxRiscv commit
// 9f452d50560d02fb391bc8039f5453c54e0911af.
// Copyright (c) 2026, Harvey Mudd College
// SPDX-License-Identifier: Apache-2.0

#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

#define RVMODEL_DATA_SECTION

#define STANDARD_SM_SUPPORTED

// Simulator peripherals (src/test/cpp/naxriscv/src/main.cpp#L210-L240):
//   https://github.com/SpinalHDL/NaxRiscv/blob/9f452d50560d02fb391bc8039f5453c54e0911af/src/test/cpp/naxriscv/src/main.cpp#L210-L240
.EQU NAX_PUTC,           0x10000000
.EQU NAX_MEXT_INT,       0x10000010
.EQU NAX_SEXT_INT,       0x10000018
.EQU NAX_FAILURE,        0x10000080
.EQU NAX_CLINT_BASE,     0x10010000

##### STARTUP #####

// The simulator's mtimecmp resets to 0, so mip.MTIP would be set from the first cycle.
// Start with mtimecmp at its maximum, as a CLINT driver would.
#define RVMODEL_BOOT \
  li   t0, NAX_CLINT_BASE + 0x4000        ;\
  li   t1, -1                             ;\
  sd   t1, 0(t0)                          ;

// No peripheral is mapped at 0x1F00_0000, in the I/O region (address bits 31:28 = 1): the
// simulator answers loads and stores there with a bus error, and the region is not executable
// (fetchRange excludes it). The simulator's MM_FAULT_ADDRESS, 0x1230, is outside both memory and
// I/O, but the core reports every access there as a page fault (see ../README.md).
#define RVMODEL_ACCESS_FAULT_ADDRESS 0x1F000000

##### TERMINATION #####

// run-naxriscv.sh passes --pass-symbol nax_pass, and the simulator ends the run with SUCCESS when
// that address commits. It overwrites the word at nax_pass with a 4-byte nop, so the instruction
// there must not be compressed. The fence lets the console stores drain first. A store to
// NAX_FAILURE ends the run with FAILURE.
#define RVMODEL_HALT_PASS  \
  fence                   ;\
  .option push            ;\
  .option norvc           ;\
  .balign 4               ;\
  .global nax_pass        ;\
  nax_pass:               ;\
    j nax_pass            ;\
  .option pop             ;

#define RVMODEL_HALT_FAIL \
  li t0, NAX_FAILURE      ;\
  sw x0, 0(t0)            ;\
  self_loop_fail:         ;\
    j self_loop_fail      ;

##### IO #####

#define RVMODEL_IO_WRITE_STR(_R1, _R2, _R3, _STR_PTR) \
1:                           ;                        \
  lbu  _R1, 0(_STR_PTR)      ; /* Load byte */        \
  beqz _R1, 3f               ; /* Exit if null */     \
  li   _R2, NAX_PUTC         ;                        \
  sb   _R1, 0(_R2)           ;                        \
  addi _STR_PTR, _STR_PTR, 1 ; /* Next char */        \
  j 1b                       ; /* Loop */             \
3:

##### Interrupt Latency #####

#define RVMODEL_INTERRUPT_LATENCY 200

##### Machine Timer #####

// mtime advances once every 10 cycles and is writable (patches/naxriscv-sim-mtime.patch).
#define RVMODEL_MTIME_ADDRESS     (NAX_CLINT_BASE + 0xBFF8)
#define RVMODEL_MTIMECMP_ADDRESS  (NAX_CLINT_BASE + 0x4000)
#define RVMODEL_MSIP_ADDRESS      (NAX_CLINT_BASE + 0x0)

// From U-mode, the T-SBI calls that arm the timer take a few thousand cycles (a few hundred ticks).
#define RVMODEL_TIMER_INT_SOON_DELAY 500

##### Machine Interrupts #####

#define RVMODEL_SET_MEXT_INT(_R1, _R2)                                        \
    li _R1, NAX_MEXT_INT               ;                                      \
    li _R2, 1                          ;                                      \
    sw _R2, 0(_R1)

#define RVMODEL_CLR_MEXT_INT(_R1, _R2)                                        \
    li _R1, NAX_MEXT_INT               ;                                      \
    sw zero, 0(_R1)

##### Supervisor Interrupts #####

#define RVMODEL_SET_SEXT_INT(_R1, _R2)                                        \
    li _R1, NAX_SEXT_INT               ;                                      \
    li _R2, 1                          ;                                      \
    sw _R2, 0(_R1)

#define RVMODEL_CLR_SEXT_INT(_R1, _R2)                                        \
    li _R1, NAX_SEXT_INT               ;                                      \
    sw zero, 0(_R1)

#endif // _RVMODEL_MACROS_H
