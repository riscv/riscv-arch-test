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
  wfi
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
  RVTEST_TSBI_CSR_READ(CSR_MHARTID)
  beqz  a0, 1f
c_park_done_hart:
  wfi
  j     c_park_done_hart
1:
  call  c_test_exit
  j     .

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
