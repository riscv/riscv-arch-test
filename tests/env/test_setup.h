# test_setup.h
# Main riscv-arch-test test macros
# Jordan Carlin jcarlin@hmc.edu October 2025
# SPDX-License-Identifier: BSD-3-Clause

/*************************************** RVTEST_BEGIN **************************************/
/**** RVTEST_BEGIN sets up the test environment and is run before the actual test code. ****/
/**** - sets up main entry point labels                                                 ****/
/**** - runs model specific boot code                                                   ****/
/**** - instantiate prologs using RVTEST_TRAP_PROLOG() if rvtests_xtrap_routine defined ****/
/**** - initializes regs                                                                ****/
/**** - defines rvtest_code_begin global label                                          ****/
/*******************************************************************************************/
.macro RVTEST_BEGIN
  // Set text section for code begin
  .section .text.init
  .global rvtest_entry_point
  rvtest_entry_point:

  // Include model specific boot code
  RVMODEL_BOOT
  RVMODEL_IO_INIT

  // Disable assembler/linker optimizations
  .option push
  .option rvc
  .align UNROLLSZ
  .option norvc
  .section .text.init

  // Test initialization
  .global rvtest_init
  rvtest_init:
    INSTANTIATE_MODE_MACRO RVTEST_TRAP_PROLOG // instantiate priv mode specific prologs
    RVTEST_INIT_GPRS // 0xF0E1D2C3B4A59687

  // Start of test
  .global rvtest_code_begin
  rvtest_code_begin:
    // Setup signature pointer and canary check
    RVTEST_SIGBASE(x3, signature_base)
    LI(T1, CANARY_VALUE)
    #ifdef SELFCHECK
      RVTEST_SIGUPD(x3, x4, x5, T1) # sig_begin_canary
    #else
      # nops to match selfchecking test length
      nop
      nop
      nop
      nop
    #endif
    // Initialize test data pointer
    LA(x4, rvtest_data_begin)
  .option pop
.endm
/*********************************** end of RVTEST_BEGIN ***********************************/


/************************************* RVTEST_CODE_END *************************************/
/**** RVTEST_CODE_END is run after the actual test code.                                ****/
/**** - Switch to M Mode                                                                ****/
/**** - Instantiate epilogs using RVTEST_TRAP_EPILOG() if rvtests_xtrap_routine defined ****/
/**** - Instantiate trap handlers for each priv mode                                    ****/
/**** - Include headers that contain code (not macros) that would throw off the address ****/
/**** - Terminate test with call to RVMODEL_HALT                                        ****/
/*******************************************************************************************/
.macro RVTEST_CODE_END
  // Disable assembler/linker optimizations
  .option push
  .option norvc
  .global rvtest_code_end       // define the label and make it available
  .global cleanup_epilogs       // ****ALERT: tests must populate x1 with a point to the end of regular sig area TODO: Is this still true?
  /**** MPRV must be clear here !!! ****/

  // Switch to M-mode
  rvtest_code_end:
    RVTEST_GOTO_MMODE // If only M-mode used by tests, this has no effect

  // Restore xTVEC, trampoline, regs for each mode in opposite order that they were saved
  cleanup_epilogs:
    #ifdef rvtest_mtrap_routine
      #ifdef rvtest_strap_routine
        #ifdef rvtest_vtrap_routine
          RVTEST_TRAP_EPILOG V  // actual v-mode prolog/epilog/handler code
        #endif
        RVTEST_TRAP_EPILOG S    // actual s-mode prolog/epilog/handler code
      #endif
      RVTEST_TRAP_EPILOG M      // actual m-mode prolog/epilog/handler code
    #endif

  // Skip around trap handlers, go to RVMODEL_HALT
  j exit_cleanup

  # TODO: This should be removed once priv tests are self-checking
  abort_tests:
    LREG    T4, sig_bgn_off(sp)   // calculate Mmode sig_end addr in handler's mode
    LREG    T1, sig_seg_siz(sp)
    add     T1, T1, T4            // construct sig seg end
    LI(     T1, 0xBAD0DAD0)       // early abort signature value at sig_end, independent of mtrap_sigptr
    SREG    T1, -4(T4)            // save into last signature canary
    j       exit_cleanup          // skip around handlers, go to RVMODEL_HALT

  // Instantiate trap handlers for each priv mode
  INSTANTIATE_MODE_MACRO RVTEST_TRAP_HANDLER

  // Include test failure handling code
  RVTEST_FAILURE_CODE

  // Terminate test
  exit_cleanup:
    LA(T1, successstr)
    RVMODEL_IO_WRITE_STR(T1, successstr)
    RVMODEL_HALT_PASS
  .option pop
.endm
/******************************** end of RVTEST_CODE_END ***********************************/


/************************************ RVTEST_DATA_BEGIN ************************************/
/**** RVTEST_DATA_BEGIN appears after RVTEST_CODE_END and creates several data regions  ****/
/**** - Scratch region for temporary data storage                                       ****/
/**** - Save areas for each priv mode trap handler                                      ****/
/**** - Defines the start of the test data region                                       ****/
/*******************************************************************************************/
.macro RVTEST_DATA_BEGIN
  // Scratch region of memory for tests (ie for loads/stores that are not part of signature)
  .section .bss
  .align 4
  scratch:
    .space 136 // Reserve 136 bytes of uninitialized memory

  // Start of data region
  .data
  .align 4

  // Create separate save areas for each priv mode trap handler
  INSTANTIATE_MODE_MACRO RVTEST_TRAP_SAVEAREA

  // Data for use in test
  .align 4
  .global rvtest_data_begin
  rvtest_data_begin:
.endm
/********************************** end of RVTEST_DATA_BEGIN *******************************/


/************************************* RVTEST_DATA_END *************************************/
/**** RVTEST_DATA_END appears after test data                                           ****/
/**** - MMU identity mapped page tables                                                 ****/
/**** - End of data region label (rvtest_data_end)                                      ****/
/*******************************************************************************************/
.macro RVTEST_DATA_END
  // Create identity mapped page tables here if mmu is present
  // TODO: Is this still needed?
  .align 12
  #ifndef RVTEST_NO_IDENTY_MAP
    #ifdef rvtest_strap_routine
      // This is a valid global pte entry w/ all permissions. If at root level, it forms an identity map.
      rvtest_Sroot_pg_tbl:
        RVTEST_PTE_IDENT_MAP(0,LVLS,RVTEST_ALLPERMS)
      #ifdef rvtest_vtrap_routine
        rvtest_Vroot_pg_tbl:
        RVTEST_PTE_IDENT_MAP(0,LVLS,RVTEST_ALLPERMS)
      #endif
    #endif
  #endif

  // Failure detection data (strings and scratch space)
  RVTEST_FAILURE_DATA

  // End of data region
  .global rvtest_data_end
  rvtest_data_end:

  // Model specific data region (tohost/fromhost, etc). Defined in model_test.h
  RVMODEL_DATA_SECTION
.endm
/*********************************** end of RVTEST_DATA_END ********************************/


/************************************* RVTEST_SIG_SETUP ************************************/
/**** RVTEST_SIG_SETUP creates signature region to support self-checking tests          ****/
/**** - Main signature region for results from test, initialized with correct values    ****/
/****   for self-checking                                                               ****/
/**** - Trap handler signature region                                                   ****/
/*******************************************************************************************/
.macro RVTEST_SIG_SETUP
  .align 4
  .global begin_signature
  begin_signature:
  .global rvtest_sig_begin
  rvtest_sig_begin:

    // Create canary at beginning of signature region to detect overwrites
    sig_begin_canary:
      CANARY

    // Main signature region
    signature_base:
      #ifdef SELFCHECK
        // Preload signature region with correct values for self-checking
        #include SIGNATURE_FILE
      #else
        // Initialize signature region to known value for initial pass
        .fill SIGUPD_COUNT*(XLEN/32),4,0xdeadbeef
      #endif

    // Signature region for trap handlers
    #ifdef rvtest_mtrap_routine
      tsig_begin_canary:
        CANARY
      mtrap_sigptr:
        .fill 64*(XLEN/32),4,0xdeadbeef
      tsig_end_canary:
        CANARY
    #endif

    // Create canary at end of signature region to detect overwrites
    sig_end_canary:
      CANARY

  .align 4
  .global rvtest_sig_end
  rvtest_sig_end:
  .global end_signature
  end_signature:
.endm
/*********************************** end of RVTEST_SIG_SETUP *********************************/
