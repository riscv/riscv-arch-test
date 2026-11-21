// c_test_start.S
// Startup code for ACT C tests
// Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
// SPDX-License-Identifier: Apache-2.0

#ifdef RVTEST_NOSIG
#define SIGUPD_COUNT 0
#define TRAP_SIGUPD_COUNT 0
#endif

#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

  // Park harts beyond the configured hart count.
  RVTEST_TSBI_CSR_READ(CSR_MHARTID)
  LA(t1, c_num_harts)
  LREG  t1, 0(t1)
  bltu  a0, t1, 1f
c_park_extra_hart:
  j     c_park_extra_hart
1:

  // Stacks grow down from __stack_top in __stack_size chunks.
  LA(sp, __stack_top)
  LA(t1, c_stack_size)
  LREG  t1, 0(t1)
1:
  beqz  a0, 2f
  sub   sp, sp, t1
  addi  a0, a0, -1
  j     1b
2:
  andi  sp, sp, -16

  // Hart 0 initializes .bss before releasing the other harts.
  RVTEST_TSBI_CSR_READ(CSR_MHARTID)
  bnez  a0, c_wait_release
  LA(t1, __bss_start)
  LA(t2, __bss_end)
1:
  bgeu  t1, t2, 2f
  SREG  zero, 0(t1)
  addi  t1, t1, REGWIDTH
  j     1b
2:
  LA(t1, c_boot_release)
  LI(t2, 1)
  fence rw, w
  sw    t2, 0(t1)
  j     c_released

c_wait_release:
  LA(t1, c_boot_release)
1:
  lw    t2, 0(t1)
  beqz  t2, 1b
  fence r, rw

c_released:
  call  main

  // Only hart 0 reports the C test result.
  mv    s1, a0
  RVTEST_TSBI_CSR_READ(CSR_MHARTID)
  beqz  a0, 1f
c_park_done_hart:
  j     c_park_done_hart
1:
  mv    a0, s1
  call  c_test_exit
c_test_exit_returned:
  j     c_test_exit_returned

// C interface to T-SBI: a0 = operation code, a1 and a2 = arguments; result in a0.
// The RV64 ABI sign-extends the 32-bit operation code. T-SBI expects it zero-extended.
.global tsbi_call
tsbi_call:
#if __riscv_xlen == 64
  slli  a0, a0, 32
  srli  a0, a0, 32
#endif
  ecall
  ret

// T-SBI privilege-mode switches for C. Each returns to its caller in the new mode.
.global tsbi_goto_mmode
tsbi_goto_mmode:
  RVTEST_TSBI_GOTO_MMODE
  ret

.global tsbi_goto_smode
tsbi_goto_smode:
  RVTEST_TSBI_GOTO_SMODE
  ret

.global tsbi_goto_umode
tsbi_goto_umode:
  RVTEST_TSBI_GOTO_UMODE
  ret

#ifdef H_SUPPORTED
.global tsbi_goto_vsmode
tsbi_goto_vsmode:
  RVTEST_TSBI_GOTO_VSMODE
  ret

.global tsbi_goto_vumode
tsbi_goto_vumode:
  RVTEST_TSBI_GOTO_VUMODE
  ret
#endif

// Route pass/fail through ACT cleanup so DUT trap state is unwound normally.
.global c_halt_pass
c_halt_pass:
  j     rvtest_code_end

.global c_halt_fail
c_halt_fail:
  j     rvtest_fail_summary

RVTEST_CODE_END

RVTEST_DATA_BEGIN

.p2align 3
c_boot_release:
  .word 0

// Linker-defined constants are loaded through data slots so this works for
// memory maps whose absolute addresses cannot be materialized directly.
c_stack_size:
  RVTEST_WORD_PTR __stack_size
c_num_harts:
  RVTEST_WORD_PTR __num_harts

RVTEST_DATA_END

RVTEST_SIG_SETUP
