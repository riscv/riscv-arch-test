# rvmodel_macros.h
# DUT-specific macro definitions for Imperas ISS
# Jordan Carlin jcarlin@hmc.edu Jan 2026 and David_Harris@hmc.edu March 2026
# SPDX-License-Identifier: BSD-3-Clause

#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

#define CLINT_BASE_ADDRESS 0x02000000

#define RVMODEL_DATA_SECTION \
        .pushsection .tohost,"aw",@progbits;                \
        .balign 8; .global tohost; tohost: .dword 0;         \
        .balign 8; .global fromhost; fromhost: .dword 0;     \
        .popsection

#define STANDARD_SM_SUPPORTED

##### STARTUP #####

# Perform boot operations. Can be empty or left undefined unless needed for
# DUT-specific behavior such as turning on a memory controller or
# initializing custom state.
//#define RVMODEL_BOOT

// Custom RVMODEL_BOOT_TO_MMODE overrides default RVTEST_BOOT_TO_MMODE
// if defined.  For most DUTs, the default should work and this macro
// should not be defined.  If no M-mode or CSRs are implemented, define this
// macro as blank to bypass the boot process.  If a nonconforming
// M-mode is implemented, define this macro to set up the necessary
// state in a fashion similar to RVTEST_BOOT_TO_MMODE.
//#define RVMODEL_BOOT_TO_MMODE

##### TERMINATION #####

// HTIF (Host-Target Interface) to terminate simulation.
// Writing to 'tohost' with value 1 indicates success, 3 indicates failure.
// As of 3/23/26, Imperas ISS does not differentiate success and failure conditions, but just looks for the _test_exit label.

# Terminate test with a pass indication.
# When the test is run in simulation, this should end the simulation.
#define RVMODEL_HALT_PASS  \
  li x1, 1                ;\
  la t0, tohost           ;\
  _test_exit:             ;\
    sw x1, 0(t0)          ;\
    sw x0, 4(t0)          ;\
    j _test_exit          ;\


# Terminate test with a fail indication.
# When the test is run in simulation, this should end the simulation.
#define RVMODEL_HALT_FAIL \
  li x1, 3                ;\
  la t0, tohost           ;\
  j _test_exit            ;\


##### IO #####

# Initialization steps needed prior to writing to the console
# _R1, _R2, and _R3 can be used as temporary registers if needed.
# Do not modify any other registers (or make sure to restore them).
# Can be empty or left undefined if no initialization is needed.
//#define RVMODEL_IO_INIT(_R1, _R2, _R3)


# Prints a null-terminated string using a DUT specific mechanism.
# A pointer to the string is passed in _STR_PTR.
# _R1, _R2, and _R3 can be used as temporary registers if needed.
# Do not modify any other registers (or make sure to restore them).
#define RVMODEL_IO_WRITE_STR(_R1, _R2, _R3, _STR_PTR) \
1:                           ;                        \
  lbu  _R1, 0(_STR_PTR)      ; /* Load byte */        \
  beqz _R1, 3f               ; /* Exit if null */     \
2:                           ;                        \
  li   _R2, 0x10010000       ; /* virtual printer */  \
  sw   _R1, 0(_R2)           ;                        \
  addi _STR_PTR, _STR_PTR, 1 ; /* Next char */        \
  j 1b                       ; /* Loop */             \
3:

##### Access Fault #####

#define RVMODEL_ACCESS_FAULT_ADDRESS 0x00000000

##### Machine Timer #####

#define RVMODEL_MTIMECMP_ADDRESS  0x02004000  /* Address of mtimecmp CSR */

#define RVMODEL_MTIME_ADDRESS  0x0200BFF8  /* Address of mtime CSR */

##### Machine Interrupts #####
#define RVMODEL_MAX_CYCLES_PER_TIMER_TICK 128

// Interrupt latency configuration
#define RVMODEL_INTERRUPT_LATENCY 10

#define RVMODEL_TIMER_INT_SOON_DELAY 100

// TODO: remove support for external machine and supervisor interrupts for Imperas configs when UDB adds parameter
// In the meantime, leave as nop

#define RVMODEL_SET_MEXT_INT(_R1, _R2)        nop
#define RVMODEL_CLR_MEXT_INT(_R1, _R2)        nop

#define RVMODEL_MSIP_ADDRESS (CLINT_BASE_ADDRESS + 0x0)

##### Supervisor Interrupts #####

#define RVMODEL_SET_SEXT_INT(_R1, _R2)        nop
#define RVMODEL_CLR_SEXT_INT(_R1, _R2)        nop

#endif // _RVMODEL_MACROS_H
