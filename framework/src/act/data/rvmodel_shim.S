// rvmodel_shim.S
// Certification-kit model shim: the ONLY translation unit that expands the
// DUT's private RVMODEL_* macros.
//
// The customer assembles this file against their own rvmodel_macros.h and
// links the result with the pre-assembled, certified test objects. Nothing in
// this file is certified; everything it provides is reachable only through the
// fixed symbol names below.
//
// SPDX-License-Identifier: Apache-2.0

// check_defines.h requires these; the shim contains no testcases of its own.
#define TEST_FILE "rvmodel_shim.S"
#define SIGUPD_COUNT 0

// The shim deliberately does NOT include riscv_arch_test.h.
//
// That header pulls in rvtest_setup.h, which contains `#include SIGNATURE_FILE`
// inside .macro RVTEST_SIG_SETUP. The C preprocessor runs before the assembler
// and does not respect .macro boundaries, so that include fires even though the
// macro is never invoked here -- the shim has no signature and no testcases.
//
// Including only what the shim actually needs also keeps the set of headers
// shipped in a certification kit as small as possible.
#include "rvtest_config.h"
#undef H_SUPPORTED // matches riscv_arch_test.h: Sail does not support Hypervisor yet
#include "derived_config.h"
#include "encoding.h"
#include "utils.h"
#include "rvmodel_macros.h"
#include "dut_environment.h"
// Checks the DUT macros this file is about to expand. Note RVMODEL_SHIM_EXTERN
// is NOT defined for the shim: the implementation checks are exactly the ones
// that matter here, because supplying those implementations is the shim's job.
#include "check_defines.h"

  .pushsection .text.rvmodel,"ax",@progbits

  // ---- Boot hooks -------------------------------------------------------
  // The framework boot sequence (RVTEST_BOOT_TO_MMODE, RVTEST_INIT_REGS, the
  // identity map) stays in the certified object. Only these two DUT hooks live
  // here. Both are plain ABI calls: ra holds the return address, T1-T3 are
  // scratch, everything else must be preserved.
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
  // Called from the trap handler's interrupt dispatch routines, NOT via the
  // plain ABI. Contract (see RVTEST_MODEL_INT_CLR in rvtest_trap_handler.h):
  //   - may clobber ONLY ra, T2 and T5; T2/T5 are restored by resto_Xrtn
  //   - a0/a1 are LIVE (a0 may hold a T-SBI return value) — do not touch them
  //   - the caller spills/reloads ra around the call, so `ret` is safe
  // These are separate from the a0/a1 entry points above because the register
  // contracts differ; do not merge them.
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
