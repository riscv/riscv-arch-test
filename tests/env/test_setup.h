# test_setup.h
# Main riscv-arch-test test macros
# Jordan Carlin jcarlin@hmc.edu October 2025, Sadhvi Narayanan sanarayanan@hmc.edu February 2026
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

  // Globally disable linker relaxation
  // The linker tries to simplify some code sequences (auipc + addi, jumps, etc.) by default.
  // This disables that behavior to ensure tests match the desired assembly. The unusual structure
  // of the ACT tests (compared to standard production code) also has a tendency to hit bugs in the
  // relaxation process (including incorrect addresses being loaded and c.nops being inserted when
  // they shouldn't be), so just disable it since we don't care about optimizations.
  .option push
  .option norelax

  // Disable assembler/linker optimizations for RVTEST_BEGIN
  .option push
  .option rvc
  .align UNROLLSZ
  .option norvc
  .section .text.init

  // Include model specific boot code
  j rvmodel_boot

  // Test initialization
  .global rvtest_init
  rvtest_init:
    INSTANTIATE_MODE_MACRO RVTEST_TRAP_PROLOG // instantiate priv mode specific prologs
    RVTEST_INIT_REGS // 0xF0E1D2C3B4A59687

    #ifdef rvtest_mtrap_routine
      #if RVMODEL_NUM_PMPS > 0
        // set up PMP so user and supervisor mode can access full address space
        // gated by rvtest_mtrap_routine so unpriv tests won't touch PMP unnecessarily
        CSRW(pmpcfg0, 0xF)   // configure PMP0 to TOR RWX
        LI(t0, -1)
        CSRW(pmpaddr0, t0)   // configure PMP0 top of range to 0xFFF...FFF to allow all addresses
        sfence.vma
      #endif
    #endif

  // Start of test
  .global rvtest_code_begin
  rvtest_code_begin:

    // Initialize signature pointer
    LA(DEFAULT_SIG_REG, signature_base)

    // Initial signature check to confirm self-checking is working
    canary_check:
    LI(T1, CANARY_VALUE)
    #ifdef RVTEST_SELFCHECK
      // Can't use DEFAULT_*_REG macros here because of macro expansion order
      // DEFAULT_SIG_REG = x2, DEFAULT_TEMP_REG = x4, DEFAULT_LINK_REG = x5
      RVTEST_SIGUPD(x2, x5, x4, T1, canary_check, canary_mismatch) # sig_begin_canary
    #else
      // nops to match selfchecking test length
      RVTEST_SIGUPD_NOPS
    #endif
    // Initialize test data pointer
    LA(DEFAULT_DATA_REG, rvtest_data_begin)

    // Enable floating-point with mstatus.FS if applicable
    #ifdef RVTEST_FP
      RVTEST_FP_ENABLE(T1)
    #endif

    // Enable vector extension with mstatus.VS if applicable
    #ifdef RVTEST_VECTOR
      RVTEST_V_ENABLE(T1, T2) // TODO: These registers might need to change
    #endif
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
  // Disable assembler/linker optimizations for RVTEST_CODE_END
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
          RVTEST_TRAP_EPILOG V        // actual v-mode prolog/epilog/handler code
        #endif
        #ifdef rvtest_htrap_routine
          RVTEST_TRAP_EPILOG H        // actual h-mode prolog/epilog/handler code
        #endif
        RVTEST_TRAP_EPILOG S          // actual s-mode prolog/epilog/handler code
      #endif
      RVTEST_TRAP_EPILOG M            // actual m-mode prolog/epilog/handler code
    #endif

    LI(     T4, 0xBAD0DEAD)           // T5 holds 0xBAD0DEAD if abort_test was executed
    bne     T4, T5, exit_cleanup      // Exit with a success message if not being aborted
    jal     T3, failedtest_x8_x7
    RVTEST_WORD_PTR "abortstr"

  // Terminate test
  exit_cleanup:
    LA(T4, successstr)
    RVMODEL_IO_WRITE_STR(T1, T2, T3, T4)
    RVMODEL_HALT_PASS

  // Terminate test with a failure message
  abort_test:
    LI(     T5, 0xBAD0DEAD)
    j       cleanup_epilogs

  // Instantiate trap handlers for each priv mode
  INSTANTIATE_MODE_MACRO RVTEST_TRAP_HANDLER

  // Include test failure handling code
  RVTEST_FAILURE_CODE

  // Model specific boot code
  rvmodel_boot:
    RVMODEL_BOOT
    RVMODEL_IO_INIT(T1, T2, T3)
    LA (T1, rvtest_init)
    jr T1                         // Jump back to the start of the test

  // rvtest macros are used to invoke the rvmodel specific interrupt macros and those rvmodels macros need to be at the end of the program because their length is variable and we don't want their lengths to affect the relative addresses of program
  #ifdef rvtest_mtrap_routine
    RVTEST_INTERRUPTS
  #endif

  nop // Padding to ensure valid memory after jr in case it's at the edge of the .text section

  .option pop

  // Pop the .option norelax from RVTEST_BEGIN
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
    .space 264 // Reserve enough scratch space (needed for atomic reservation tests with offsets up to 256 bytes)

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
/**** - MMU page tables (filled with invalid PTEs)                                      ****/
/**** - End of data region label (rvtest_data_end)                                      ****/
/*******************************************************************************************/
.macro RVTEST_DATA_END

  // Root page tables
  #ifdef rvtest_strap_routine
    .align 12
    rvtest_Sroot_pg_tbl:
      .zero(4096)                // 4KB page table
    #ifdef rvtest_htrap_routine
      .align 14
      rvtest_Hroot_pg_tbl:
      .zero(16384)               // 16KB page table
    #endif
    #ifdef rvtest_vtrap_routine
      .align 12
      rvtest_Vroot_pg_tbl:
        .zero(4096)              // 4KB page table
    #endif
  #endif

  // Failure detection data (strings and scratch space)
  RVTEST_FAILURE_DATA

  // End of data region
  .global rvtest_data_end
  rvtest_data_end:

  // Model specific data region (tohost/fromhost, etc). Defined in rvmodel_macros.h
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
      #ifdef RVTEST_SELFCHECK
        // Preload signature region with correct values for self-checking
        #include SIGNATURE_FILE
      #else
        // Initialize signature region to known value for initial pass
        .fill SIGUPD_COUNT*SIG_STRIDE,4,0xdeadbeef
      #endif

    // Signature region for trap handlers
    #ifdef rvtest_mtrap_routine
      tsig_begin_canary:
        CANARY
      mtrap_sigptr:
        .fill 20000*(XLEN/32),4,0xdeadbeef
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
