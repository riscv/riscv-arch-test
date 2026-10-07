# rvtest_driver.h
# The DUT driver: every routine that expands a DUT-specific RVMODEL_* macro
# SPDX-License-Identifier: BSD-3-Clause

// Test objects never include rvmodel_macros.h. Wherever a test needs the DUT
// (boot, console output, halting, raising or clearing an interrupt) it calls one
// of the global symbols below. rvmodel_driver.S expands RVTEST_DRIVER_CODE once
// per config, either against the DUT's rvmodel_macros.h (the DUT's librvmodel.a)
// or against sail_macros.h (the reference model's driver, which produces the
// expected signature). The test object is the same in both cases.
//
// All code goes in .text.rvmodel and RVMODEL_DATA_SECTION in .tohost. The linker
// script places both after .data, so a driver of any size cannot move a
// signature-visible address.
//
// Calling convention: rvmodel_* hooks may clobber ra and T1-T3 (x6-x8); the
// rvtest_*_int_* routines may clobber ra and a0-a2, as before. Every routine
// returns with ret, which Zicfilp exempts from landing-pad checks.

#ifndef _RVTEST_DRIVER_H
#define _RVTEST_DRIVER_H

// A write to msip, mtimecmp, or stimecmp reaches mip only eventually. After
// clearing an interrupt source, poll mip until the pending bit reads 0, for at most
// RVMODEL_INTERRUPT_LATENCY iterations, so the interrupt is not taken again
// when the test next enables it. The _SU flavor reads mip through T-SBI.
.macro RVTEST_WAIT_MIP_CLEAR_M mask
  LI(a2, RVMODEL_INTERRUPT_LATENCY)
  1:
  csrr a0, mip
  andi a0, a0, \mask
  beqz a0, 2f // pending bit is clear
  beqz a2, 2f // latency exhausted
  addi a2, a2, -1
  j 1b
  2:
.endm

.macro RVTEST_WAIT_MIP_CLEAR_SU mask
  LI(a2, RVMODEL_INTERRUPT_LATENCY)
  1:
  RVTEST_TSBI_CSR_READ(CSR_MIP) // a0 = mip; a2 is preserved
  andi a0, a0, \mask
  beqz a0, 2f // pending bit is clear
  beqz a2, 2f // latency exhausted
  addi a2, a2, -1
  j 1b
  2:
.endm

.macro RVTEST_DRIVER_CODE
  .pushsection .text.rvmodel,"ax",@progbits
  .option push
  .option norvc
  .option norelax
  .balign 4

  // Model-specific boot hooks, called once from rvmodel_boot before any trap
  // handler is installed.
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

  .global rvmodel_io_write_str
  rvmodel_io_write_str:
    // a0 = string pointer; T1-T3 (x6-x8) are scratch. Clobbers ra.
    // Use rvmodel_io_write_str_c for C-ABI compatible version.
    RVMODEL_IO_WRITE_STR(T1, T2, T3, a0)
    ret

  .global rvmodel_io_write_str_c
  rvmodel_io_write_str_c:
    addi sp, sp, -16
    SREG ra, 0(sp)
    SREG s0, REGWIDTH(sp)
    call rvmodel_io_write_str
    LREG s0, REGWIDTH(sp)
    LREG ra, 0(sp)
    addi sp, sp, 16
    ret

  .global rvmodel_halt_pass
  rvmodel_halt_pass:
    RVMODEL_HALT_PASS
    j . // Explicit non-returning tail if the macro returns (it should not)

  .global rvmodel_halt_fail
  rvmodel_halt_fail:
    RVMODEL_HALT_FAIL
    j . // Explicit non-returning tail if the macro returns (it should not)

  // Interrupt clears called from a trap handler (see RVTEST_MODEL_INT_CLR0 in
  // rvtest_trap_handler.h). These may touch only ra, T2 and T5.
  .global rvmodel_clr_vsw_int_h
  rvmodel_clr_vsw_int_h:
    RVMODEL_CLR_VSW_INT
    ret

  .global rvmodel_clr_vtimer_int_h
  rvmodel_clr_vtimer_int_h:
    RVMODEL_CLR_VTIMER_INT
    ret

  .global rvmodel_clr_vext_int_h
  rvmodel_clr_vext_int_h:
    RVMODEL_CLR_VEXT_INT
    ret

  // Optional DUT emulation hook for the invisible trap handler. The test object
  // calls it only when the config's dut_environment block sets
  // INVISIBLE_TRAP_HANDLER. T1 = mepc and T2 = the instruction are inputs;
  // T3 = action, T4 = destination GPR and T5 = value are outputs.
  #ifdef RVMODEL_INVISIBLE_TRAP_HANDLER
    .global rvmodel_invisible_trap_handler
    rvmodel_invisible_trap_handler:
      RVMODEL_INVISIBLE_TRAP_HANDLER(T1, T2, T3, T4, T5)
      ret
  #endif


  //////////////////////
  // Interrupt functions
  // All these functions can touch a0 and a1 and a2
  //////////////////////

  // Note: _ms and _su are shared implementations
  // used for multiple privilege modes


  // Flavors to run from M-mode

  #ifdef STANDARD_SM_SUPPORTED

    .global rvtest_set_mtime_int_soon_m
    rvtest_set_mtime_int_soon_m:
      #if defined(RVMODEL_MTIME_ADDRESS) && defined(RVMODEL_MTIMECMP_ADDRESS) && defined(RVMODEL_TIMER_INT_SOON_DELAY)
        LI(a2, RVMODEL_TIMER_INT_SOON_DELAY)
        #if UDB_MXLEN == 32
          LA(a1, RVMODEL_MTIMECMP_ADDRESS)
          li a0, -1
          sw a0, 4(a1) // mtimecmp high word = all 1s so the split update cannot fire early
          LA(a1, RVMODEL_MTIME_ADDRESS)
          lw a0, 0(a1) // read mtime low word
          add a0, a0, a2 // add delay to mtime low word
          LA(a1, RVMODEL_MTIMECMP_ADDRESS)
          sw a0, 0(a1) // write to mtimecmp low word
          mv a2, a0 // Save mtimecmp low word
          LA(a1, RVMODEL_MTIME_ADDRESS)
          lw a0, 4(a1) // read mtime high word
          LI(a1, RVMODEL_TIMER_INT_SOON_DELAY)
          bgeu a2, a1, 1f // skip if didn't wrap
          addi a0, a0, 1 // increment mtime high word
          1:
          LA(a1, RVMODEL_MTIMECMP_ADDRESS)
          sw a0, 4(a1) // write to mtimecmp high word
        #else
          LA(a1, RVMODEL_MTIME_ADDRESS)
          ld a0, 0(a1) // read mtime
          add a0, a2, a0 // add delay to mtime
          LA(a1, RVMODEL_MTIMECMP_ADDRESS)
          sd a0, 0(a1) // write to mtimecmp
        #endif
      #endif
      ret

    .global rvtest_set_mtime_int_m
    rvtest_set_mtime_int_m:
      #ifdef RVMODEL_MTIMECMP_ADDRESS
        LA(a1, RVMODEL_MTIMECMP_ADDRESS)
        sw zero, 4(a1)
        sw zero, 0(a1)
      #endif
      ret

    .global rvtest_clr_mtime_int_m
    rvtest_clr_mtime_int_m:
      #ifdef RVMODEL_MTIMECMP_ADDRESS
        LA(a1, RVMODEL_MTIMECMP_ADDRESS)
        li a2, -1 // all 1s
        sw a2, 4(a1)      // don't bother with lower bits, which stay at 0
        RVTEST_WAIT_MIP_CLEAR_M 0x80 // mip.MTIP
      #endif
      ret

    .global rvtest_set_msw_int_m
    rvtest_set_msw_int_m:
      #ifdef RVMODEL_MSIP_ADDRESS
        LA(a1, RVMODEL_MSIP_ADDRESS)
        li a2, 1
        sw a2, 0(a1) // normal way to set MSI is to write a 1 to MSIP
      #elif defined(RVMODEL_SET_MSW_INT)
        RVMODEL_SET_MSW_INT(a0, a1) // if normal way isn't supported, use platform-specific method
      #endif
      ret

    .global rvtest_clr_msw_int_m
    rvtest_clr_msw_int_m:
      #ifdef RVMODEL_MSIP_ADDRESS
        LA(a1, RVMODEL_MSIP_ADDRESS)
        sw zero, 0(a1) // normal way to clear MSI is to write a 0 to MSIP
        RVTEST_WAIT_MIP_CLEAR_M 0x8 // mip.MSIP
      #elif defined(RVMODEL_CLR_MSW_INT_M)
        RVMODEL_CLR_MSW_INT_M(a0, a1) // if normal way isn't supported, use platform-specific method
      #endif
      ret

    .global rvtest_set_mext_int_m
    rvtest_set_mext_int_m:
      #ifdef RVMODEL_SET_MEXT_INT_M
        RVMODEL_SET_MEXT_INT_M(a0, a1) // platform-specific interrupt controller
      #endif
      ret

    .global rvtest_clr_mext_int_m
    rvtest_clr_mext_int_m:
      #ifdef RVMODEL_CLR_MEXT_INT_M
        RVMODEL_CLR_MEXT_INT_M(a0, a1) // platform-specific interrupt controller
      #endif
      ret

    #ifdef SSTC_SUPPORTED
      .global rvtest_set_sstc_int_soon_m
      rvtest_set_sstc_int_soon_m:
        #if defined(RVMODEL_MTIME_ADDRESS) && defined(RVMODEL_TIMER_INT_SOON_DELAY)
          LA(a1, RVMODEL_MTIME_ADDRESS)
          LI(a2, RVMODEL_TIMER_INT_SOON_DELAY)
          #if UDB_MXLEN == 32
            li a0, -1
            csrw stimecmph, a0 // stimecmp high word = all 1s so the split update cannot fire early
            lw a0, 0(a1) // read mtime low word
            add a1, a0, a2 // add delay to mtime low word
            csrw stimecmp, a1 // write low word of timer compare
            mv a2, a1 // save stimecmp low word
            LA(a1, RVMODEL_MTIME_ADDRESS)
            lw a0, 4(a1) // read mtime high word
            LI(a1, RVMODEL_TIMER_INT_SOON_DELAY)
            bgeu a2, a1, 1f // skip if didn't wrap
            addi a0, a0, 1 // increment mtime high word
            1:
            csrw stimecmph, a0 // write high word of timer compare
          #else
            ld a0, 0(a1) // read mtime
            add a1, a2, a0 // add delay to mtime
            csrw stimecmp, a1 // write to timer compare
          #endif
        #endif
        ret

      // Set STI using Sstc.  Assumes menvcfg.STCE=1
      .global rvtest_set_sstc_int_ms
      rvtest_set_sstc_int_ms:
        #if UDB_MXLEN == 32
          csrw stimecmph, zero // clear upper word of stimecmp
        #endif
        csrw stimecmp, zero // clear stimecmp, set STI
        ret

      // Clear STI using Sstc.  Assumes menvcfg.STCE=1
      .global rvtest_clr_sstc_int_m
      rvtest_clr_sstc_int_m:
        li a1, -1 // all 1s
        #if UDB_MXLEN == 32
          // Upper word first, which is what actually clears STI; the lower word then makes the
          // 64-bit stimecmp read all 1s as it does on RV64, and is never transiently armed.
          csrw stimecmph, a1 // set upper word of stimecmp to all 1s to clear STI
          csrw stimecmp, a1  // and the lower word, so the whole register is all 1s
        #else
          csrw stimecmp, a1 // set stimecmp to all 1s to clear STI
        #endif
        RVTEST_WAIT_MIP_CLEAR_M 0x20 // mip.STIP
        ret

      // Clear STI from S-mode using Sstc.  Assumes menvcfg.STCE=1
      .global rvtest_clr_sstc_int_s
      rvtest_clr_sstc_int_s:
        li a1, -1 // all 1s
        #if UDB_MXLEN == 32
          // Upper word first, which is what actually clears STI; the lower word then makes the
          // 64-bit stimecmp read all 1s as it does on RV64, and is never transiently armed.
          csrw stimecmph, a1 // set upper word of stimecmp to all 1s to clear STI
          csrw stimecmp, a1  // and the lower word, so the whole register is all 1s
        #else
          csrw stimecmp, a1 // set stimecmp to all 1s to clear STI
        #endif
        RVTEST_WAIT_MIP_CLEAR_SU 0x20 // mip.STIP
        ret
    #endif // SSTC_SUPPORTED

    #ifdef S_SUPPORTED
      .global rvtest_set_stime_int_m
      rvtest_set_stime_int_m:
        li a1, 1<<5 // STIP bit
        csrs mip, a1        // Trigger mip.STIP
        ret

      .global rvtest_clr_stime_int_m
      rvtest_clr_stime_int_m:
        li a1, 1<<5 // STIP bit
        csrc mip, a1        // Clear mip.STIP
        ret

      .global rvtest_set_ssw_int_m
      rvtest_set_ssw_int_m:
        // trigger with platform-specific interrupt controller if it exists, otherwise with mip.SSIP
        #ifdef RVMODEL_SET_SSW_INT
          RVMODEL_SET_SSW_INT(a0, a1)
        #else
          csrsi mip, 1<<1 // Trigger mip.SSIP
        #endif
        ret

      .global rvtest_clr_ssw_int_m
      rvtest_clr_ssw_int_m:
        // clear using both platform-specific interrupt controller if it exists and mip.SSIP
        #ifdef RVMODEL_CLR_SSW_INT_M
          RVMODEL_CLR_SSW_INT_M(a0, a1)
        #endif
        csrci mip, 1<<1             /* Always called from M-mode; mip.SSIP must be cleared via mip */
        ret

      .global rvtest_set_sext_int_m
      rvtest_set_sext_int_m:
        // trigger with platform-specific interrupt controller if it exists, otherwise with mip.SEIP
        #ifdef RVMODEL_SET_SEXT_INT_M
          RVMODEL_SET_SEXT_INT_M(a0, a1)
        #else
          li a1, 1<<9 // SEIP bit
          csrs mip, a1        // Trigger mip.SEIP
        #endif
        ret

      .global rvtest_clr_sext_int_m
      rvtest_clr_sext_int_m:
        // clear both platform-specific interrupt controller if it exists and mip.SEIP
        #ifdef RVMODEL_CLR_SEXT_INT_M
          RVMODEL_CLR_SEXT_INT_M(a0, a1)
        #endif
        li a1, 1<<9 // SEIP bit
        csrc mip, a1 // clear mip.SEIP
        ret
    #endif // S_SUPPORTED
  #endif

  // Flavors to run from supervisor mode

  #ifdef STANDARD_SM_SUPPORTED

    .global rvtest_set_mtime_int_soon_su
    rvtest_set_mtime_int_soon_su:
      #if defined(RVMODEL_MTIME_ADDRESS) && defined(RVMODEL_MTIMECMP_ADDRESS) && defined(RVMODEL_TIMER_INT_SOON_DELAY)
        LI(a2, RVMODEL_TIMER_INT_SOON_DELAY)
        #if UDB_MXLEN == 32
          LA(a1, RVMODEL_MTIMECMP_ADDRESS)
          li a2, -1
          RVTEST_TSBI_SWP4 // sw a2, 4(a1) // mtimecmp high word = all 1s so the split update cannot fire early
          LA(a1, RVMODEL_MTIME_ADDRESS)
          LI(a2, RVMODEL_TIMER_INT_SOON_DELAY)
          RVTEST_TSBI_LW // lw a0, 0(a1) // read mtime low word
          add a2, a0, a2 // add delay to mtime low word
          LA(a1, RVMODEL_MTIMECMP_ADDRESS)
          RVTEST_TSBI_SW // sw a2, 0(a1) // write to mtimecmp low word
          LA(a1, RVMODEL_MTIME_ADDRESS)
          RVTEST_TSBI_LWP4 // lw a0, 4(a1) // read mtime high word
          LI(a1, RVMODEL_TIMER_INT_SOON_DELAY)
          bgeu a2, a1, 1f // skip if didn't wrap
          addi a0, a0, 1 // increment mtime high word
          1:
          LA(a1, RVMODEL_MTIMECMP_ADDRESS)
          mv a2, a0 // Save mtimecmp high word
          RVTEST_TSBI_SWP4 // sw a2, 4(a1) // write to mtimecmp high word
        #else
          LA(a1, RVMODEL_MTIME_ADDRESS)
          RVTEST_TSBI_LD // ld a0, 0(a1) // read mtime
          add a2, a2, a0 // add delay to mtime
          LA(a1, RVMODEL_MTIMECMP_ADDRESS)
          RVTEST_TSBI_SD // sd a2, 0(a1) // write to mtimecmp
        #endif
      #endif
      ret


    .global rvtest_set_mtime_int_su
    rvtest_set_mtime_int_su:
      #ifdef RVMODEL_MTIMECMP_ADDRESS
        LA(a1, RVMODEL_MTIMECMP_ADDRESS)
        li a2, 0 // store zero
        #if UDB_MXLEN == 32
          RVTEST_TSBI_SW // sw a2, 0(a1)
          RVTEST_TSBI_SWP4 // sw a2, 4(a1)
        #else
          RVTEST_TSBI_SD // sd a2, 0(a1)
        #endif
      #endif
      ret

    .global rvtest_clr_mtime_int_su
    rvtest_clr_mtime_int_su:
      #ifdef RVMODEL_MTIMECMP_ADDRESS
        LA(a1, RVMODEL_MTIMECMP_ADDRESS)
        li a2, -1 // all 1s
        RVTEST_TSBI_SWP4 // sw a2, 4(a1)      // don't bother with lower bits, which stay at 0
        RVTEST_WAIT_MIP_CLEAR_SU 0x80 // mip.MTIP
      #endif
      ret

    .global rvtest_set_msw_int_su
    rvtest_set_msw_int_su:
      #ifdef RVMODEL_MSIP_ADDRESS
        LA(a1, RVMODEL_MSIP_ADDRESS)
        li a2, 1
        RVTEST_TSBI_SW // sw a2, 0(a1) // normal way to set MSI is to write a 1 to MSIP
      #elif defined(RVMODEL_SET_MSW_INT)
        RVMODEL_SET_MSW_INT(a0, a1) // if normal way isn't supported, use platform-specific method
      #endif
      ret

    .global rvtest_clr_msw_int_su
    rvtest_clr_msw_int_su:
      #ifdef RVMODEL_MSIP_ADDRESS
        LA(a1, RVMODEL_MSIP_ADDRESS)
        li a2, 0
        RVTEST_TSBI_SW // sw a2, 0(a1) // normal way to clear MSI is to write a 0 to MSIP
        RVTEST_WAIT_MIP_CLEAR_SU 0x8 // mip.MSIP
      #elif defined(RVMODEL_CLR_MSW_INT)
        RVMODEL_CLR_MSW_INT(a0, a1) // if normal way isn't supported, use platform-specific method
      #endif
      ret

    .global rvtest_set_mext_int_su
    rvtest_set_mext_int_su:
      #ifdef RVMODEL_SET_MEXT_INT
        RVMODEL_SET_MEXT_INT(a0, a1) // platform-specific interrupt controller
      #endif
      ret

    .global rvtest_clr_mext_int_su
    rvtest_clr_mext_int_su:
      #ifdef RVMODEL_CLR_MEXT_INT
        RVMODEL_CLR_MEXT_INT(a0, a1) // platform-specific interrupt controller
      #endif
      ret
  #endif

  #ifdef S_SUPPORTED
    #ifdef SSTC_SUPPORTED
      .global rvtest_set_sstc_int_soon_s
      rvtest_set_sstc_int_soon_s:
        #if defined(RVMODEL_MTIME_ADDRESS) && defined(RVMODEL_TIMER_INT_SOON_DELAY)
          LA(a1, RVMODEL_MTIME_ADDRESS)
          LI(a2, RVMODEL_TIMER_INT_SOON_DELAY)
          #if UDB_MXLEN == 32
            li a0, -1
            csrw stimecmph, a0 // stimecmp high word = all 1s so the split update cannot fire early
            RVTEST_TSBI_LW // lw a0, 0(a1) // read mtime low word
            add a0, a0, a2 // add delay to mtime low word
            csrw stimecmp, a0 // write low word of timer compare
            mv a2, a0 // save stimecmp low word
            RVTEST_TSBI_LWP4 // lw a0, 4(a1) // read mtime high word
            LI(a1, RVMODEL_TIMER_INT_SOON_DELAY)
            bgeu a2, a1, 1f // skip if didn't wrap
            addi a0, a0, 1 // increment mtime high word
            1:
            csrw stimecmph, a0 // write high word of timer compare
          #else
            RVTEST_TSBI_LD // ld a0, 0(a1) // read mtime
            add a1, a2, a0 // add delay to mtime
            csrw stimecmp, a1 // write to timer compare
          #endif
        #endif
        ret
    #endif // SSTC_SUPPORTED

    .global rvtest_set_stime_int_su
    rvtest_set_stime_int_su:
      RVTEST_TSBI_CSR_SET(CSR_MIP, 1<<5) // set mip.STIP
      ret

    .global rvtest_clr_stime_int_su
    rvtest_clr_stime_int_su:
      RVTEST_TSBI_CSR_CLEAR(CSR_MIP, 1<<5) // clear mip.STIP
      ret

    .global rvtest_set_ssw_int_su
    rvtest_set_ssw_int_su:
      // trigger with platform-specific interrupt controller if it exists, otherwise with mip.SSIP.
      // sip.SSIP is read-only zero unless SSI is delegated, so write mip.SSIP through T-SBI,
      // which works whether or not mideleg.SSI is set.
      #ifdef RVMODEL_SET_SSW_INT
        RVMODEL_SET_SSW_INT(a0, a1)
      #else
        RVTEST_TSBI_CSR_SET(CSR_MIP, 1<<1) // set mip.SSIP
      #endif
      ret

    .global rvtest_clr_ssw_int_su
    rvtest_clr_ssw_int_su:
      // clear using both platform-specific interrupt controller if it exists and mip.SSIP
      #ifdef RVMODEL_CLR_SSW_INT
        RVMODEL_CLR_SSW_INT(a0, a1)
      #endif
      RVTEST_TSBI_CSR_CLEAR(CSR_MIP, 1<<1) // clear mip.SSIP
      ret

    .global rvtest_set_sext_int_su
    rvtest_set_sext_int_su:
      // trigger with platform-specific interrupt controller if it exists, otherwise with mip.SEIP
      #ifdef RVMODEL_SET_SEXT_INT
        RVMODEL_SET_SEXT_INT(a0, a1)
      #else
        RVTEST_TSBI_CSR_SET(CSR_MIP, 1<<9) // set mip.SEIP
      #endif
      ret

    .global rvtest_clr_sext_int_su
    rvtest_clr_sext_int_su:
      // clear both platform-specific interrupt controller if it exists and mip.SEIP
      #ifdef RVMODEL_CLR_SEXT_INT
        RVMODEL_CLR_SEXT_INT(a0, a1)
      #endif
      RVTEST_TSBI_CSR_CLEAR(CSR_MIP, 1<<9) // clear mip.SEIP
      ret

    // Flavors to run from user mode

    #ifdef SSTC_SUPPORTED
      .global rvtest_set_sstc_int_soon_u
      rvtest_set_sstc_int_soon_u:
        #if defined(RVMODEL_MTIME_ADDRESS) && defined(RVMODEL_TIMER_INT_SOON_DELAY)
          LI(a2, RVMODEL_TIMER_INT_SOON_DELAY)
          #if UDB_MXLEN == 32
            li a1, -1
            RVTEST_TSBI_CSR_WRITE_A1(CSR_STIMECMPH) // stimecmp high word = all 1s so the split update cannot fire early
            LA(a1, RVMODEL_MTIME_ADDRESS)
            RVTEST_TSBI_LW // lw a0, 0(a1) // read mtime low word
            add a2, a0, a2 // stimecmp low word = mtime low word + delay
            mv a1, a2
            RVTEST_TSBI_CSR_WRITE_A1(CSR_STIMECMP) // write low word of timer compare
            LA(a1, RVMODEL_MTIME_ADDRESS)
            RVTEST_TSBI_LWP4 // lw a0, 4(a1) // read mtime high word
            LI(a1, RVMODEL_TIMER_INT_SOON_DELAY)
            bgeu a2, a1, 1f // skip if didn't wrap
            addi a0, a0, 1 // increment mtime high word
            1:
            mv a1, a0
            RVTEST_TSBI_CSR_WRITE_A1(CSR_STIMECMPH) // write high word of timer compare
          #else
            LA(a1, RVMODEL_MTIME_ADDRESS)
            RVTEST_TSBI_LD // ld a0, 0(a1) // read mtime
            add a1, a2, a0 // add delay to mtime
            RVTEST_TSBI_CSR_WRITE_A1(CSR_STIMECMP) // write timer compare
          #endif
        #endif
        ret

      // Set STI using Sstc.  Assumes menvcfg.STCE=1
      .global rvtest_set_sstc_int_u
      rvtest_set_sstc_int_u:
        #if UDB_MXLEN == 32
          RVTEST_TSBI_CSR_WRITE(CSR_STIMECMPH, 0) // clear upper word of stimecmp
        #endif
        RVTEST_TSBI_CSR_WRITE(CSR_STIMECMP, 0) // clear stimecmp, set STI
        ret

      // Clear STI using Sstc.  Assumes menvcfg.STCE=1
      .global rvtest_clr_sstc_int_u
      rvtest_clr_sstc_int_u:
        li a1, -1 // all 1s
        #if UDB_MXLEN == 32
          RVTEST_TSBI_CSR_WRITE_A1(CSR_STIMECMPH) // set upper word of stimecmp to all 1s to clear STI
          RVTEST_TSBI_CSR_WRITE_A1(CSR_STIMECMP)  // and the lower word, so the whole register is all 1s
        #else
          RVTEST_TSBI_CSR_WRITE_A1(CSR_STIMECMP) // set stimecmp to all 1s to clear STI
        #endif
        RVTEST_WAIT_MIP_CLEAR_SU 0x20 // mip.STIP
        ret
    #endif // SSTC_SUPPORTED
  #endif // S_SUPPORTED

  nop // Padding to ensure valid memory at the edge of the section
  .option pop
  .popsection

  // Model specific data region (tohost/fromhost, etc).
  RVMODEL_DATA_SECTION
.endm

#endif // _RVTEST_DRIVER_H
