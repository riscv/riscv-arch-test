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

  // Include model specific boot code
  call rvmodel_boot

  // Create new section so that .align directives in the test code don't affect the
  // entry point address. The assembler increases a section's overall alignment to
  // the largest .align in that section, so any large .align used in a test would
  // increase .text.init's alignment, shifting rvtest_entry_point to an unexpected
  // address. Placing test code in its own section avoids that because the .text.rvtest
  // section will have its own alignment. This requires .text.init and .text.rvtest
  // to be in separate output sections in the linker script.
  .section .text.rvtest

  // Test initialization
  .global rvtest_init
  rvtest_init:
    RVTEST_INIT_REGS // 0xF0E1D2C3B4A59687
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
      RVTEST_SIGUPD(x2, x5, x4, T1, canary_check, canary_mismatch) # signature_base canary
    #else
      // Increment sig pointer to skip the CANARY
      addi DEFAULT_SIG_REG, DEFAULT_SIG_REG, SIG_STRIDE
      // NOPs to keep the emitted code size/bytes aligned with the RVTEST_SIGUPD sequence
      // used in self-check mode (including its embedded pointer words/dwords).
      nop
      nop
      nop
      nop
      nop
      #if __riscv_xlen == 64
        nop
        nop
      #endif
    #endif
    // Initialize test data pointer
    LA(DEFAULT_DATA_REG, rvtest_data_begin)
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
  // ***dh 4/8/26 is this still the right thing to do if there is no conforming M-mode?
  rvtest_code_end:
    RVTEST_GOTO_MMODE // If only M-mode used by tests, this has no effect

  // Restore xTVEC, trampoline, regs for each mode in opposite order that they were saved
  cleanup_epilogs:
    #ifdef rvtest_mtrap_routine
      #ifdef S_SUPPORTED
        #ifdef H_SUPPORTED
          RVTEST_TRAP_EPILOG V        // actual v-mode prolog/epilog/handler code
          RVTEST_TRAP_EPILOG H        // actual h-mode prolog/epilog/handler code
        #endif
        RVTEST_TRAP_EPILOG S          // actual s-mode prolog/epilog/handler code
      #endif
      RVTEST_TRAP_EPILOG M            // actual m-mode prolog/epilog/handler code
    #endif

  #ifdef rvtest_mtrap_routine
    LI(     T4, 0xBAD0DEAD)           // T5 holds 0xBAD0DEAD if abort_test was executed
    bne     T4, T5, check_trap_sig_offset
    jal     T2, failedtest_trap_x7_x9
    RVTEST_WORD_PTR abort_test
    RVTEST_WORD_PTR abortstr
    .word   CSR_MEPC

    // Check trap signature offset to make sure the correct number of traps occurred
    check_trap_sig_offset:
      LA(     T1, Mtrap_sig)
      LREG    T1, 0(T1)               // Trap signature pointer
      LA(     T2, mtrap_sigptr)       // Base address of trap signature region
      sub     T1, T1, T2              // Calculate offset
      RVTEST_SIGUPD(x2, x5, x4, T1, check_trap_sig_offset, trap_sig_offset_mismatch)
  #endif

  // Terminate test
  exit_cleanup:
    LA(a0, successstr)
    call rvmodel_io_write_str
    call rvmodel_halt_pass

  // Terminate test with a failure message
  abort_test:
    LI(     T5, 0xBAD0DEAD)
    j       cleanup_epilogs

  // Instantiate trap handlers for each priv mode
  INSTANTIATE_MODE_MACRO RVTEST_TRAP_HANDLER

  // Include test failure handling code
  RVTEST_FAILURE_CODE

  // All model-specific (RVMODEL_*) code lives in the dedicated .text.rvmodel
  // section, placed AFTER .data by the linker script. This isolates variable-
  // sized macro expansions (they differ between the DUT build and the Sail
  // reference build) from the .text section so that test-visible symbols in
  // .data (scratch, begin_signature, etc.) have identical addresses in both
  // the .elf and .sig.elf builds.
  .pushsection .text.rvmodel,"ax",@progbits
  // Model specific boot code
  rvmodel_boot:
    #ifdef RVMODEL_BOOT
      RVMODEL_BOOT
    #endif
    #ifdef RVMODEL_IO_INIT
      RVMODEL_IO_INIT(T1, T2, T3)
    #endif
    // always boot to at least M-mode
    RVTEST_BOOT_TO_MMODE
    #ifndef BOOT_TO_MMODE
      // continue to a lower privilege mode depending on the type of test
      #ifdef S_SUPPORTED
        RVTEST_BOOT_TO_SMODE
      #endif
      #ifndef S_REQUIRED
        // continue to U-mode if U-mode supported and S-mode not required
        #ifdef U_SUPPORTED
          RVTEST_BOOT_TO_UMODE
        #endif
      #endif
    #endif
    LA (T1, rvtest_init)
    jr T1                         // Jump back to the start of the test

  rvmodel_io_write_str:
    // a0 = string pointer; T1-T3 (x6-x8) are scratch. Clobbers ra.
    RVMODEL_IO_WRITE_STR(T1, T2, T3, a0)
    ret

  rvmodel_halt_pass:
    RVMODEL_HALT_PASS
    j . // Explicit non-returning tail if the macro returns (it should not)

  rvmodel_halt_fail:
    RVMODEL_HALT_FAIL
    j . // Explicit non-returning tail if the macro returns (it should not)

  // ***DH 4/8/26 check this is proper gating
  #ifdef rvtest_mtrap_routine
    rvtest_set_msw_int:
      RVMODEL_SET_MSW_INT(T2, T5)
      ret

    rvtest_clr_msw_int:
      RVMODEL_CLR_MSW_INT(T2, T5)
      ret

    rvtest_set_mext_int:
      RVMODEL_SET_MEXT_INT(T2, T5)
      ret

    rvtest_clr_mext_int:
      RVMODEL_CLR_MEXT_INT(T2, T5)
      ret

    rvtest_set_ssw_int:
      RVMODEL_SET_SSW_INT(T2, T5)
      ret

    rvtest_clr_ssw_int:
      RVMODEL_CLR_SSW_INT(T2, T5)
      csrci sip, 2
      ret

    rvtest_set_sext_int:
      RVMODEL_SET_SEXT_INT(T2, T5)
      ret

    rvtest_clr_sext_int:
      RVMODEL_CLR_SEXT_INT(T2, T5)
      LI(T3, 512)
      csrc sip, T3
      ret
  #endif

  nop // Padding to ensure valid memory at the edge of the section

  .popsection

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
  // Initialized with distinct values so tests can detect unintended zeroing or aliasing,
  // while remaining obviously recognizable as uninitialized scratch defaults.
  // 264 bytes = 33 doublewords (needed for atomic reservation tests with offsets up to 256 bytes)
  .data
  .align 8
  scratch:
    .dword 0xDEAD0001FFFEBEEF, 0xDEAD0002FFFDBEEF
    .dword 0xDEAD0003FFFCBEEF, 0xDEAD0004FFFBBEEF
    .dword 0xDEAD0005FFFABEEF, 0xDEAD0006FFF9BEEF
    .dword 0xDEAD0007FFF8BEEF, 0xDEAD0008FFF7BEEF
    .dword 0xDEAD0009FFF6BEEF, 0xDEAD000AFFF5BEEF
    .dword 0xDEAD000BFFF4BEEF, 0xDEAD000CFFF3BEEF
    .dword 0xDEAD000DFFF2BEEF, 0xDEAD000EFFF1BEEF
    .dword 0xDEAD000FFFF0BEEF, 0xDEAD0010FFEFBEEF
    .dword 0xDEAD0011FFEEBEEF, 0xDEAD0012FFEDBEEF
    .dword 0xDEAD0013FFECBEEF, 0xDEAD0014FFEBBEEF
    .dword 0xDEAD0015FFEABEEF, 0xDEAD0016FFE9BEEF
    .dword 0xDEAD0017FFE8BEEF, 0xDEAD0018FFE7BEEF
    .dword 0xDEAD0019FFE6BEEF, 0xDEAD001AFFE5BEEF
    .dword 0xDEAD001BFFE4BEEF, 0xDEAD001CFFE3BEEF
    .dword 0xDEAD001DFFE2BEEF, 0xDEAD001EFFE1BEEF
    .dword 0xDEAD001FFFE0BEEF, 0xDEAD0020FFDFBEEF
    .dword 0xDEAD0021FFDEBEEF

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
  #ifdef S_SUPPORTED
    .align 12
    rvtest_Sroot_pg_tbl:
      .zero(4096)                // 4KB page table
    #ifdef H_SUPPORTED
      .align 14
      rvtest_Hroot_pg_tbl:
        .zero(16384)               // 16KB page table
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

    // Main signature region
    #ifdef RVTEST_SELFCHECK
        signature_base:
          // Preload signature region with correct values for self-checking
          #include SIGNATURE_FILE
    #else
      // Canary is the first entry in the signature region; the dynamic canary
      // check at test start reads and verifies this value to ensure the signature
      // mechanism is functioning correctly.
      signature_base:
        CANARY
        // Initialize remaining signature region to known value for initial pass
        .fill SIGUPD_COUNT*(SIG_STRIDE>>2),4,0xdeadbeef

      // Signature region for trap handlers
      #ifdef rvtest_mtrap_routine
        tsig_begin_canary:
          TRAP_CANARY

        mtrap_sigptr:
            .fill TRAP_SIGUPD_COUNT*(SIG_STRIDE>>2),4,0xdeadbeef
      #endif

      // Create canary at end of signature region to detect overwrites
      sig_end_canary:
        CANARY
    #endif

  .align 4
  .global rvtest_sig_end
  rvtest_sig_end:
  .global end_signature
  end_signature:

  // Model specific data region (tohost/fromhost, etc). Defined in rvmodel_macros.h.
  // Placed after the signature so variable-size DUT data does not affect any
  // test-visible symbol addresses.
  RVMODEL_DATA_SECTION
.endm
/*********************************** end of RVTEST_SIG_SETUP *********************************/

/*****************************************************************/
/**** initialize regs, just to make sure you catch any errors ****/
/*****************************************************************/

.macro DBLSHIFTR dstreg,     oldreg,    tmpreg, shamt       //this is just a rotate  using xtmp as a tmp
        slli    \tmpreg\(), \oldreg\(),   XLEN-\shamt
        srli    \dstreg\(), \oldreg\(),        \shamt
        or      \dstreg\(), \dstreg\(), \tmpreg\()
.endm

/* init regs, to ensure you catch any errors */
.macro RVTEST_INIT_REGS
  // *** move these to ***boot_to_m_mode
    #ifndef RVTEST_E
     LI (x16, (0x7D5BFDDB7D5BFDDB & MASK))
     DBLSHIFTR x17, x16, x15, 7
     DBLSHIFTR x18, x17, x15, 7
     DBLSHIFTR x19, x18, x15, 7
     DBLSHIFTR x20, x19, x15, 7
     DBLSHIFTR x21, x20, x15, 7
     DBLSHIFTR x22, x21, x15, 7
     DBLSHIFTR x23, x22, x15, 7
     DBLSHIFTR x24, x23, x15, 7
     DBLSHIFTR x25, x24, x15, 7
     DBLSHIFTR x26, x25, x15, 7
     DBLSHIFTR x27, x26, x15, 7
     DBLSHIFTR x28, x27, x15, 7
     DBLSHIFTR x29, x28, x15, 7
     DBLSHIFTR x30, x29, x15, 7
     DBLSHIFTR x31, x30, x15, 7
    #endif
    LI (x1,  (0xFEEDBEADFEEDBEAD & MASK))
    DBLSHIFTR x2,  x1,  x15, 7
    DBLSHIFTR x3,  x2,  x15, 7
    DBLSHIFTR x4,  x3,  x15, 7
    DBLSHIFTR x5,  x4,  x15, 7
    DBLSHIFTR x6,  x5,  x15, 7
    DBLSHIFTR x7,  x6,  x15, 7
    DBLSHIFTR x8,  x7,  x15, 7
    DBLSHIFTR x9,  x8,  x15, 7
    DBLSHIFTR x10, x9,  x15, 7
    DBLSHIFTR x11, x10, x15, 7
    DBLSHIFTR x12, x11, x15, 7
    DBLSHIFTR x13, x12, x15, 7
    DBLSHIFTR x14, x13, x15, 7
    LI (x15, (0xFAB7FBB6FAB7FBB6 & MASK))
.endm

/************************************ RVTEST_BOOT_TO_M_MODE ********************************/
/**** Set up M-mode trap handler and initialize M-mode CSRs                             ****/
/**** Can be overridden by DUT-specific RVMODEL_BOOT_TO_MMODE if no conforming M-mode   ****/
/*******************************************************************************************/
.macro RVTEST_BOOT_TO_MMODE
  // Run custom RVMODEL flavor if the DUT provides it to override this default boot
  #ifdef RVMODEL_BOOT_TO_MMODE
    RVMODEL_BOOT_TO_MMODE
  #else
    // Default implementation assumes conforming M-mode
    // We are in M-mode now at initial boot time

    // Disable interrupts
    csrw mie, zero
    csrw mip, zero

    // initialize trap CSRs to known values
    csrw mideleg, zero  // don't delegate interrupts (until S-mode handler is set up)
    csrw medeleg, zero  // don't delegate exceptions (until S-mode handler is set up)
    csrw mepc, zero
    csrw mtval, zero
    csrw mcause, zero

    // Set up trap handlers for all modes
    // *** this code needs a close review
    RVTEST_TRAP_PROLOG M
    //RVTEST_TRAP_PROLOG S
    //INSTANTIATE_MODE_MACRO RVTEST_TRAP_PROLOG // instantiate priv mode specific prologs

    // *** change rvtest_mtrap_routine stuff everywhere to TBD
    // *** change rvtest_strap_routine to S_SUPPORTED
    // *** change rvtest_htrap_routine to H_SUPPORTED

    // Initialize M-mode CSRs

    // Put mstatus in a known initial state.
    // mstatus.SIE = 0: Disable S-mode interrupts
    // mstatus.MIE = 0: Disable M-mode interrupts
    // mstatus.SPIE = 0: Clear S-mode previous interrupt enable bit
    // mstatus.UBE = 0: User-mode Little Endian
    // mstatus.MPIE = 0: Clear M-mode previous interrupt enable bit
    // mstatus.SPP = 0: Clear previous privilege mode bit (set to U-mode)
    // mstatus.XS = 00: Set custom state to OFF
    // mstatus.MPRV = 0: Disable MPRV so memory accesses are in M-mode
    // mstatus.SUM = 0: Disable supervisor access to user memory
    // mstatus.MXR = 0: Disable Make eXecutable Readable
    // mstatus.TVM = 0: Disable Trap Virtual Memory
    // mstatus.TW = 0: Disable Timeout Wait
    // mstatus.TSR = 0: Enable SRET instruction when S-mode supported
    // mstatus.VS = 11: Set vector state to dirty if supported (V)
    // mstatus.MPP = 11: Set previous privilege mode to M-mode
    // mstatus.FS = 11: Set floating-point state to dirty if supported (F or Zfinx)
    // mstatus.UXL = XLEN (RV64 only)
    // mstatus.SXL = XLEN (RV64 only)
    // mstatus.SBE = 0: Set S-mode to little endian if supported
    // mstatus.MBE = 0: Set M-mode to little endian if supported
    // mstatus.GVA = 0: Guest virtual address
    // mstatus.MPV = 0: Previous virtualization OFF
    // mstatus.MPELP = 0: Disable landing pads
    // mstatus.MDT = 0: Disable double trap
    #if __riscv_xlen == 64
      #define MSTATUS_UXL_64         0x0000000200000000
      #define MSTATUS_SXL_64         0x0000000800000000
      li t0, MSTATUS_MPP | MSTATUS_UXL_64 | MSTATUS_SXL_64
      csrw mstatus, t0  // Set just all these fields
    #else    // RV32
      li t0, MSTATUS_MPP
      csrw mstatus, t0
      csrw mstatush, zero // Clear all these fields
    #endif
    #if defined(F_SUPPORTED) || defined(ZFINX_SUPPORTED)
      li t0, MSTATUS_FS
      csrs mstatus, t0 // Set FS to dirty to enable floating-point
      csrw fcsr, zero // Initialize fcsr
    #endif
    #ifdef V_SUPPORTED
      li t0, MSTATUS_VS
      csrs mstatus, t0 // Set VS to dirty to enable vector
      // csrr VLENB_CACHE, vlenb // carryover from RVTEST_V_ENABLE; delete when not needed anywhere
    #endif

    // Disable all privileged environment configuration, and enable unprivileged configuration
    // Privileged tests that want to use these features should turn them on
    // Unprivileged tests don't make SBI calls so the features should already be enabled
    // menvcfg.STCE = 0: Disable Sstc supervisor timer compare
    // menvcfg.PBMTE = 0: Disable Svpbmt page-based memory types
    // menvcfg.ADUE = 0: Disable Svadu A/D bit update
    // menvcfg.CDE = 0: Disable counter delegation ***check
    // menvcfg.DTE = 0: Disable Ssdbltrp double traps
    // menvcfg.PMM = 00: Disable Smnpm pointer masking at next lower privilege mode
    // menvcfg.SSE = 0: Disable Zicfiss shadow stacks
    // menvcfg.LPE = 0: Disable Zicfilp landing pads
    // menvcfg.FIOM = 0: Disable Fence of I/O Implies Memory
    // menvcfg.CBZE = 1: Enable Zicboz cache block zero instructions
    // menvcfg.CBCFE = 1: Enable Zicbom cache block clean/flush instructions
    // menvcfg.CBIE = 11: Enable Zicbom cache block invalidate instructions to perform invalidate operation
    li t0, MENVCFG_CBIE | MENVCFG_CBCFE | MENVCFG_CBZE
    csrw menvcfg, t0
    #if __riscv_xlen == 32
      csrw menvcfgh, zero // Clear upper bits if they exist
    #endif

    // Enable necessary state for unpriv instructions and access from lower privilege modes
    // Disable privileged extensions until they are turned on explicitly by tests that need them
    // mstateen0.SE0 = 1: enable access to hststateen0, hstatene0h, ssstateen0
    // mstateen0.ENVCFG = 1: enable access to henvcfg, henvcfgh, senvcfg
    // mstateen0.CSRIND = 0: disable access to Sscrind siselect, sireg* registers (until turned on for those tests)
    // mstateen0.AIA = 0: disable access to Ssaia advanced interrupt architecture state
    // mstateen0.IMSIC = 0: disable access to MISIC state
    // mstateen0.P1P13 = 0: disable access to hedelegh for 1P13 until turned on
    // mstateen0.SRMCFG = 0: disable access to srmcfg for Ssqosid until turned on
    // mstateen0.CTR = 0: disable access to Smctr control transfer records until turned on
    // mstateen0.JVT = 1: Enable jvt for Zcmt
    // mstateen0.FCSR = 1: Enable fcsr access for Zfinx only if supported ZFINX_SUPPORTED (to avoid conflicts with F)
    // mstateen0.C = 0: Disable custom state
    #if __riscv_xlen == 64
      li t0, MSTATEEN_HSTATEEN | MSTATEEN0_HENVCFG | MSTATEEN0_JVT
      csrw mstateen0, t0  // Set just all these fields
    #else    // RV32
      li t0, MSTATEENH_HSTATEEN | MSTATEEN0H_HENVCFG
      csrw mstateen0h, t0 // Set just all these fields
      li t0, MSTATEEN0_JVT
      csrw mstateen0, t0 // Set just this field
    #endif
    #ifdef ZFINX_SUPPORTED
      li t0, MSTATEEN0_FCSR
      csrs mstateen0, t0 // Set mstateen0.FCSR
      li t0,
    #endif

    // Enable all performance counters if they exist
    // This is reserved if mcountinhibit is not implemented, and might trap or have unspecified behavior
    //   *** define a UDB parameter to determine whether mcountinhibit is implemented
    csrw mcountinhibit, zero

    // Initialize counter event selectors to 0.  They must be implemented.
    csrw mhpmevent3, zero
    csrw mhpmevent4, zero
    csrw mhpmevent5, zero
    csrw mhpmevent6, zero
    csrw mhpmevent7, zero
    csrw mhpmevent8, zero
    csrw mhpmevent9, zero
    csrw mhpmevent10, zero
    csrw mhpmevent11, zero
    csrw mhpmevent12, zero
    csrw mhpmevent13, zero
    csrw mhpmevent14, zero
    csrw mhpmevent15, zero
    csrw mhpmevent16, zero
    csrw mhpmevent17, zero
    csrw mhpmevent18, zero
    csrw mhpmevent19, zero
    csrw mhpmevent20, zero
    csrw mhpmevent21, zero
    csrw mhpmevent22, zero
    csrw mhpmevent23, zero
    csrw mhpmevent24, zero
    csrw mhpmevent25, zero
    csrw mhpmevent26, zero
    csrw mhpmevent27, zero
    csrw mhpmevent28, zero
    csrw mhpmevent29, zero
    csrw mhpmevent30, zero
    csrw mhpmevent31, zero
    #if __riscv_xlen == 32
      csrw mhpmevent3, zero
      csrw mhpmevent4, zero
      csrw mhpmevent5, zero
      csrw mhpmevent6, zero
      csrw mhpmevent7, zero
      csrw mhpmevent8, zero
      csrw mhpmevent9, zero
      csrw mhpmevent10, zero
      csrw mhpmevent11, zero
      csrw mhpmevent12, zero
      csrw mhpmevent13, zero
      csrw mhpmevent14, zero
      csrw mhpmevent15, zero
      csrw mhpmevent16, zero
      csrw mhpmevent17, zero
      csrw mhpmevent18, zero
      csrw mhpmevent19, zero
      csrw mhpmevent20, zero
      csrw mhpmevent21, zero
      csrw mhpmevent22, zero
      csrw mhpmevent23, zero
      csrw mhpmevent24, zero
      csrw mhpmevent25, zero
      csrw mhpmevent26, zero
      csrw mhpmevent27, zero
      csrw mhpmevent28, zero
      csrw mhpmevent29, zero
      csrw mhpmevent30, zero
      csrw mhpmevent31, zero
    #endif

    // msseccfg.MLL, MMWP, RLB, USEED, and SSEED reset to defined values.
    // if Pointer Masking is supported, mseccfg.PMM should be initialized to 0 to turn it off
    // might as well turn off everything
    #ifdef SMMPM_SUPPORTED
      csrw msseccfg, zero
    #endif


    #ifdef SMRNMI_SUPPORTED
      // if Resumable NMI supported, also clear all RNMI-related fields, especially mnstatus.NMIE
      csrw mnstatus, zero // Clear all fields in mnstatus as well if it exists
    #endif

    #if RVMODEL_NUM_PMPS > 0
      // set up PMP so user and supervisor mode can access full address space
      CSRW(pmpcfg0, 0xF)   // configure PMP0 to TOR RWX
      LI(t0, -1)
      CSRW(pmpaddr0, t0)   // configure PMP0 top of range to 0xFFF...FFF to allow all addresses
      // sfence.vma is required after PMP entries are changed to sync the PMP with the virtual
      // memory system and any PMP or address translation caches. sfence.vma should not be
      // performed in a system that does not support virtual memory because it might raise
      // an illegal instruction.
      #if defined(SV32_SUPPORTED) || defined(SV39_SUPPORTED)
        sfence.vma
      #endif
    #endif
  #endif
.endm

/************************************ RVTEST_BOOT_TO_S_MODE ********************************/
/**** Set up S-mode trap handler and initialize S-mode CSRs                             ****/
/**** Switch into S-mode                                                                ****/
/*******************************************************************************************/
.macro RVTEST_BOOT_TO_SMODE
  // We start in M-mode after initial boot but cannot assume it is conforming
  // so access to M-mode features must be through a SBI

  // Run custom RVMODEL flavor if the DUT provides it to override this default boot
  #ifdef RVMODEL_BOOT_TO_SMODE
    RVMODEL_BOOT_TO_SMODE
  #else
    // Default implementation assumes conforming M-mode
    // We are in M-mode now at initial boot time

    // Set up trap handler for S-mode
    // *** uncomment this when rvtest_strap_routine etc. is replaced with S/H_SUPPORTED
    // RVTEST_TRAP_PROLOG S
    // if Hypervisor supported, also set up HS and VS-mode trap handlers
    // *** how does h differ from S?
    #ifdef H_SUPPORTED
      //RVTEST_TRAP_PROLOG H
      //RVTEST_TRAP_PROLOG V
    #endif

  // Initialize S-mode CSRs
  #endif
.endm

/************************************ RVTEST_BOOT_TO_U_MODE ********************************/
/**** Switch into U-mode    ***describe                                                            ****/
/*******************************************************************************************/
.macro RVTEST_BOOT_TO_UMODE
  // We arrive here in S-mode if S_SUPPORTED, else in M-mode.
  // Cannot assume M-mode is conforming, so access M-mode features through SBI
.endm
