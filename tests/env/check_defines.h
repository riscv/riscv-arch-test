# check_defines.h
# Ensures all RVMODEL macros are defined: device values (from dut_environment.h) in
# every build, and the DUT's macros (from rvmodel_macros.h) in the driver build
# Define _M flavors of RVMODEL_CLR_<type>_INT_M to match non-M if not defined by user
# Jordan Carlin jcarlin@hmc.edu December 2025
# SPDX-License-Identifier: BSD-3-Clause

########## test.S CHECKS ##########
#ifndef RVTEST_DRIVER
  #ifndef TEST_FILE
    #error "TEST_FILE not defined. It should be passed on the compiler command line."
  #endif

  #ifndef SIGUPD_COUNT
    #error "SIGUPD_COUNT not defined. It should be defined at the beginning of the test file."
  #endif
#endif

// TRAP_SIGUPD_COUNT is the number of expected traps. Each trap uses 4 signature
// words, or 6 when H is supported.
#ifndef TRAP_SIGUPD_COUNT
  #define TRAP_SIGUPD_COUNT 3750
#endif

#ifdef H_SUPPORTED
  #define TRAP_SIGUPD_WORDS ((TRAP_SIGUPD_COUNT)*6)
#else
  #define TRAP_SIGUPD_WORDS ((TRAP_SIGUPD_COUNT)*4)
#endif

########## GLOBAL XLEN CHECK  ##########
#ifndef __riscv_xlen
  #error "__riscv_xlen not defined."
#endif

########## rvmodel_macros.h CHECKS ##########
// INVISIBLE_TRAP_HANDLER in the config's dut_environment block says the DUT's
// driver provides RVMODEL_INVISIBLE_TRAP_HANDLER; test objects cannot see the macro.
#if defined(RVTEST_DUT_INVISIBLE_TRAP_HANDLER) || defined(RVTEST_EMULATE_TIME_CSR)
  #define RVTEST_INVISIBLE_TRAP_HANDLER
#endif

// Only the driver (rvmodel_driver.S) sees the DUT's rvmodel_macros.h, or the
// reference model's sail_macros.h, so the implementation checks run there.
#ifdef RVTEST_DRIVER

#ifndef RVMODEL_DATA_SECTION
  #error "RVMODEL_DATA_SECTION not defined. Make sure to define it in rvmodel_macros.h."
#endif

##### TERMINATION #####
#ifndef RVMODEL_HALT_PASS
  #error "RVMODEL_HALT_PASS not defined. Make sure to define it in rvmodel_macros.h."
#endif

#ifndef RVMODEL_HALT_FAIL
  #error "RVMODEL_HALT_FAIL not defined. Make sure to define it in rvmodel_macros.h."
#endif

##### IO #####
#ifndef RVMODEL_IO_WRITE_STR
  #error "RVMODEL_IO_WRITE_STR not defined. Make sure to define it in rvmodel_macros.h."
#endif

##### INVISIBLE TRAP HANDLER #####
#if defined(RVMODEL_INVISIBLE_TRAP_HANDLER) && !defined(RVTEST_DUT_INVISIBLE_TRAP_HANDLER)
  #error "RVMODEL_INVISIBLE_TRAP_HANDLER is defined but the config does not declare it. Set INVISIBLE_TRAP_HANDLER: true in the dut_environment block of the UDB config."
#endif
#if defined(RVTEST_DUT_INVISIBLE_TRAP_HANDLER) && !defined(RVMODEL_INVISIBLE_TRAP_HANDLER)
  #error "The config's dut_environment block sets INVISIBLE_TRAP_HANDLER, but rvmodel_macros.h does not define RVMODEL_INVISIBLE_TRAP_HANDLER."
#endif

##### UNSUPPORTED #####
// These would expand inside the test object, which is built without
// rvmodel_macros.h and is the same for the DUT and the reference model.
#ifdef RVMODEL_FENCEI
  #error "RVMODEL_FENCEI is not supported. The reference model must execute the same instruction stream as the DUT, so instruction-stream sync must be fence.i (declare Zifencei in the config) or unnecessary (coherent I-cache)."
#endif
#if defined(RVMODEL_BOOT_TO_MMODE) || defined(RVMODEL_BOOT_TO_SMODE) || defined(RVMODEL_BOOT_TO_UMODE)
  #error "RVMODEL_BOOT_TO_MMODE/SMODE/UMODE are not supported. Put DUT-specific boot code in RVMODEL_BOOT, and leave STANDARD_SM_SUPPORTED out of the dut_environment block if the DUT has no standard M-mode."
#endif

#endif // RVTEST_DRIVER (implementation checks)

##### ADDRESSES #####
// If RVMODEL_ACCESS_FAULT_ADDRESS is not defined, no access faults are tested

##### MTIME #####
// If RVMODEL_MTIME_ADDRESS is not defined, no machine timer interrupts are tested

#ifdef RVTEST_EMULATE_TIME_CSR
  #ifndef RVMODEL_MTIME_ADDRESS
    #error "RVMODEL_MTIME_ADDRESS is required to emulate the time CSR"
  #endif
#endif

#ifdef RVMODEL_MTIME_ADDRESS
  // If RVMODEL_MTIME_ADDRESS is defined, these other MTIME-related macros must also be defined
  // because the tests will need them to cause timer interrupts and test timer functionality.
  // If these macros are not defined, the tests will fail to assemble due to the checks below.
  #ifndef RVMODEL_MTIMECMP_ADDRESS
    #error "RVMODEL_MTIMECMP_ADDRESS not defined. Define it in the dut_environment block of the UDB config."
  #endif
#endif

##### Interrupt Delays #####
#ifndef RVMODEL_INTERRUPT_LATENCY
  #error "RVMODEL_INTERRUPT_LATENCY not defined. Define it in the dut_environment block of the UDB config."
#endif
#ifndef RVMODEL_TIMER_INT_SOON_DELAY
  #error "RVMODEL_TIMER_INT_SOON_DELAY not defined. Define it in the dut_environment block of the UDB config."
#endif

#ifndef RVMODEL_MAX_CYCLES_PER_TIMER_TICK
  #define RVMODEL_MAX_CYCLES_PER_TIMER_TICK 1
#endif

##### Machine Interrupts #####
// UDB_{MEI,MTI,MSI}_INTR_IMPL say which machine interrupts the platform can raise. Each one that
// is implemented needs a way to raise it, and a platform providing a raise must also provide the
// matching clear. The raises and clears are in the driver, so those checks run in the driver build.
#if defined(UDB_MTI_INTR_IMPL) && !defined(RVMODEL_MTIMECMP_ADDRESS)
  #error "UDB_MTI_INTR_IMPL is set but RVMODEL_MTIMECMP_ADDRESS is not defined. Define it in the dut_environment block of the UDB config."
#endif

#ifdef RVTEST_DRIVER

#if defined(UDB_MEI_INTR_IMPL) && !defined(RVMODEL_SET_MEXT_INT)
  #error "UDB_MEI_INTR_IMPL is set but RVMODEL_SET_MEXT_INT is not defined. Define it in rvmodel_macros.h."
#endif

#if defined(UDB_MSI_INTR_IMPL) && !defined(RVMODEL_MSIP_ADDRESS) && !defined(RVMODEL_SET_MSW_INT)
  #error "UDB_MSI_INTR_IMPL is set but neither RVMODEL_MSIP_ADDRESS nor RVMODEL_SET_MSW_INT is defined. Define RVMODEL_MSIP_ADDRESS in the dut_environment block of the UDB config, or RVMODEL_SET_MSW_INT in rvmodel_macros.h."
#endif

#ifdef RVMODEL_SET_MEXT_INT
  #ifndef RVMODEL_CLR_MEXT_INT
    #error "RVMODEL_SET_MEXT_INT is defined but RVMODEL_CLR_MEXT_INT is not. Define both in rvmodel_macros.h."
  #endif

  #ifndef RVMODEL_CLR_MEXT_INT_M
    #define RVMODEL_CLR_MEXT_INT_M RVMODEL_CLR_MEXT_INT
  #endif

  #ifndef RVMODEL_SET_MEXT_INT_M
    #define RVMODEL_SET_MEXT_INT_M RVMODEL_SET_MEXT_INT
  #endif
#endif

#ifdef RVMODEL_SET_MSW_INT
  #ifndef RVMODEL_CLR_MSW_INT
    #error "RVMODEL_SET_MSW_INT is defined but RVMODEL_CLR_MSW_INT is not. Define both in rvmodel_macros.h."
  #endif

  #ifndef RVMODEL_CLR_MSW_INT_M
    #define RVMODEL_CLR_MSW_INT_M RVMODEL_CLR_MSW_INT
  #endif
#endif

##### Supervisor Interrupts #####
#ifdef S_SUPPORTED
  // RVMODEL_SET_SEXT_INT / RVMODEL_CLR_SEXT_INT are optional: platforms without a supervisor
  // external interrupt controller leave them undefined and the trap handler uses mip.SEIP.

  #ifndef RVMODEL_CLR_SEXT_INT_M
    #ifdef RVMODEL_CLR_SEXT_INT
      #define RVMODEL_CLR_SEXT_INT_M RVMODEL_CLR_SEXT_INT
    #endif
  #endif

  #ifndef RVMODEL_SET_SEXT_INT_M
    #ifdef RVMODEL_SET_SEXT_INT
      #define RVMODEL_SET_SEXT_INT_M RVMODEL_SET_SEXT_INT
    #endif
  #endif

  // RVMODEL_SET_SSW_INT / RVMODEL_CLR_SSW_INT are optional: platforms without a supervisor
  // software interrupt controller leave them undefined and the trap handler uses mip.SSIP.

  #ifndef RVMODEL_CLR_SSW_INT_M
    #ifdef RVMODEL_CLR_SSW_INT
      #define RVMODEL_CLR_SSW_INT_M RVMODEL_CLR_SSW_INT
    #endif
  #endif
#endif

#endif // RVTEST_DRIVER (interrupt implementation checks)

##### Configuration Limitations #####
#if UDB_NUM_PMP_ENTRIES > 0
  #ifndef UDB_PMP_NAPOT_SUPPORTED
    #error "DUTs with PMP but without NAPOT support are not currently supported by ACTs. Please report this as an issue on the riscv/riscv-arch-test repository."
  #endif
  #if UDB_NUM_USABLE_PMP_ENTRIES < 8
    #error "DUTs with fewer than 8 usable PMP entries are not currently supported by ACTs. Please report this as an issue on the riscv/riscv-arch-test repository."
  #endif
#endif
