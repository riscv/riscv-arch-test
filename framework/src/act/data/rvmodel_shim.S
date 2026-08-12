// rvmodel_shim.S
// The one translation unit that expands the DUT's private RVMODEL_* macros. The
// customer assembles this against their rvmodel_macros.h and links it with the
// certified objects; everything here is reached only through the symbol names below.
//
// SPDX-License-Identifier: Apache-2.0

// check_defines.h wants these; the shim has no testcases of its own.
#define TEST_FILE "rvmodel_shim.S"
#define SIGUPD_COUNT 0

// Don't include riscv_arch_test.h: it pulls rvtest_setup.h, whose
// `#include SIGNATURE_FILE` sits inside .macro RVTEST_SIG_SETUP and fires anyway
// (cpp runs before the assembler and ignores .macro). Include only what we need.
#include "rvtest_config.h"
#undef H_SUPPORTED // as in riscv_arch_test.h: Sail has no Hypervisor yet
#include "derived_config.h"
#include "encoding.h"
#include "utils.h"
#include "rvmodel_macros.h"
#include "dut_environment.h"
// RVMODEL_SHIM_EXTERN stays undefined here so check_defines.h enforces the
// implementation macros - which is the shim's job to supply.
#include "check_defines.h"

  .pushsection .text.rvmodel,"ax",@progbits

  // ---- Boot hooks -------------------------------------------------------
  // Only these two DUT hooks live here; the rest of boot stays in the object.
  // Plain ABI calls: ra = return, T1-T3 scratch, preserve everything else.
  .global rvmodel_dut_boot
  rvmodel_dut_boot:
    #ifdef RVMODEL_BOOT
      RVMODEL_BOOT
    #endif
    ret

  .global rvmodel_dut_io_init
  rvmodel_dut_io_init:
    #ifdef RVMODEL_IO_INIT
      RVMODEL_IO_INIT(T1, T2, T3)
    #endif
    ret

  // ---- IO and termination -----------------------------------------------
  .global rvmodel_io_write_str
  rvmodel_io_write_str:
    // a0 = string pointer; T1-T3 (x6-x8) are scratch. Clobbers ra.
    RVMODEL_IO_WRITE_STR(T1, T2, T3, a0)
    ret

  .global rvmodel_halt_pass
  rvmodel_halt_pass:
    RVMODEL_HALT_PASS
    j . // Explicit non-returning tail if the macro returns (it should not)

  .global rvmodel_halt_fail
  rvmodel_halt_fail:
    RVMODEL_HALT_FAIL
    j . // Explicit non-returning tail if the macro returns (it should not)

  // ---- Interrupt set/clear (ABI-call flavour, driven from test code) -----
  #ifdef STANDARD_SM_SUPPORTED
    .global rvtest_set_msw_int
    rvtest_set_msw_int:
      RVMODEL_SET_MSW_INT(a0, a1)
      ret

    .global rvtest_clr_msw_int
    rvtest_clr_msw_int:
      RVMODEL_CLR_MSW_INT(a0, a1)
      ret

    .global rvtest_set_mext_int
    rvtest_set_mext_int:
      RVMODEL_SET_MEXT_INT(a0, a1)
      ret

    .global rvtest_clr_mext_int
    rvtest_clr_mext_int:
      RVMODEL_CLR_MEXT_INT(a0, a1)
      ret
  #endif

  #ifdef S_SUPPORTED
    .global rvtest_set_ssw_int
    rvtest_set_ssw_int:
      RVMODEL_SET_SSW_INT(a0, a1)
      ret

    .global rvtest_clr_ssw_int
    rvtest_clr_ssw_int:
      RVMODEL_CLR_SSW_INT(a0, a1)
      li a0, 2
      csrc mip, a0              /* Always called from M-mode; mip.SSIP must be cleared via mip */
      ret

    .global rvtest_set_sext_int
    rvtest_set_sext_int:
      RVMODEL_SET_SEXT_INT(a0, a1)
      ret

    .global rvtest_clr_sext_int
    rvtest_clr_sext_int:
      RVMODEL_CLR_SEXT_INT(a0, a1)
      LI(a0, 512)
      csrc sip, a0 // clear sip.SEIP
      ret
  #endif

  // ---- Interrupt clear (handler-context flavour) ------------------------
  // Called from the trap handler (RVTEST_MODEL_INT_CLR), not via the ABI. May
  // clobber only ra/T2/T5; a0/a1 are live (a0 may carry a T-SBI return). The
  // caller spills ra, so `ret` is fine. Kept separate from the a0/a1 versions.
  .global rvmodel_clr_msw_int_h
  rvmodel_clr_msw_int_h:
    RVMODEL_CLR_MSW_INT(T2, T5)
    ret

  .global rvmodel_clr_mext_int_h
  rvmodel_clr_mext_int_h:
    RVMODEL_CLR_MEXT_INT(T2, T5)
    ret

  .global rvmodel_clr_ssw_int_h
  rvmodel_clr_ssw_int_h:
    RVMODEL_CLR_SSW_INT(T2, T5)
    ret

  .global rvmodel_clr_sext_int_h
  rvmodel_clr_sext_int_h:
    RVMODEL_CLR_SEXT_INT(T2, T5)
    ret

  nop // Padding to ensure valid memory at the edge of the section

  .popsection

  // ---- Model data region (tohost/fromhost, etc.) ------------------------
  RVMODEL_DATA_SECTION
