# rvmodel_macros.h
# RVMODEL macro definitions for OpenHW CVA6 (cv64a60ax) core
# SPDX-License-Identifier: Apache-2.0

#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

#define CLINT_BASE_ADDRESS 0x02000000
#define PLIC_BASE_ADDRESS  0x0C000000

#define RVMODEL_DATA_SECTION \
        .pushsection .tohost,"aw",@progbits;                \
        .align 8; .global tohost; tohost: .dword 0;         \
        .align 8; .global fromhost; fromhost: .dword 0;     \
        .popsection

#define STANDARD_SM_SUPPORTED

##### STARTUP #####

# Perform boot operations. Can be empty or left undefined unless needed for
# DUT-specific behavior such as turning on a memory controller or
# initializing custom state.
// #define RVMODEL_BOOT

// Custom RVMODEL_BOOT_TO_MMODE overrides default RVTEST_BOOT_TO_MMODE
// if defined.  For most DUTs, the default should work and this macro
// should not be defined.  If no M-mode or CSRs are implemented, define this
// macro as blank to bypass the boot process.  If a nonconforming
// M-mode is implemented, define this macro to set up the necessary
// state in a fashion similar to RVTEST_BOOT_TO_MMODE.
//#define RVMODEL_BOOT_TO_MMODE

##### TERMINATION #####

// CVA6 uses HTIF (Host-Target Interface) to terminate simulation.
// Writing to 'tohost' with value 1 indicates success, 3 indicates failure.

# Terminate test with a pass indication.
# When the test is run in simulation, this should end the simulation.
#define RVMODEL_HALT_PASS  \
  li x1, 1                ;\
  la t0, tohost           ;\
  write_tohost_pass:      ;\
    sw x1, 0(t0)          ;\
    sw x0, 4(t0)          ;\
    j write_tohost_pass   ;\


# Terminate test with a fail indication.
# When the test is run in simulation, this should end the simulation.
#define RVMODEL_HALT_FAIL \
  li x1, 3                ;\
  la t0, tohost           ;\
  write_tohost_fail:      ;\
    sw x1, 0(t0)          ;\
    sw x0, 4(t0)          ;\
    j write_tohost_fail   ;\


##### IO #####

# Initialization steps needed prior to writing to the console
# _R1, _R2, and _R3 can be used as temporary registers if needed.
# Do not modify any other registers (or make sure to restore them).
# Can be empty or left undefined if no initialization is needed.
// #define RVMODEL_IO_INIT(_R1, _R2, _R3)


# Prints a null-terminated string using a DUT specific mechanism.
# A pointer to the string is passed in _STR_PTR.
# _R1, _R2, and _R3 can be used as temporary registers if needed.
# Do not modify any other registers (or make sure to restore them).
#define RVMODEL_IO_WRITE_STR(_R1, _R2, _R3, _STR_PTR)               \
1:                           ;                       \
  lbu _R1, 0(_STR_PTR)        ;/* Load byte */        \
  beqz _R1, 3f                ;/* Exit if null */     \
2: /* htif_putc */           ;                      \
  la _R2, tohost       ;   \
  sw _R1, 0(_R2)     ; \
  /* device=1 (terminal), cmd=1 (output) */ \
  li _R1, 0x01010000 ;\
  sw _R1, 4(_R2)   ;\
  addi _STR_PTR, _STR_PTR, 1 ;/* Next char */        \
  j 1b                       ;/* Loop */             \
3:

##### Access Fault #####

#define RVMODEL_ACCESS_FAULT_ADDRESS 0x00000000

##### Machine Timer #####

#define RVMODEL_MTIMECMP_ADDRESS  0x02004000  /* Address of mtimecmp CSR */

#define RVMODEL_MTIME_ADDRESS  0x0200BFF8  /* Address of mtime CSR */

##### Machine Interrupts #####

// Interrupt latency configuration
#define RVMODEL_INTERRUPT_LATENCY 1

#define RVMODEL_TIMER_INT_SOON_DELAY 100

/* CVA6 PLIC Context 0 M-Mode Registers mapping */
#define PLIC_PRIORITY_1         (PLIC_BASE_ADDRESS + 0x000004)
#define PLIC_ENABLE_CTX0        (PLIC_BASE_ADDRESS + 0x002000)
#define PLIC_THRESHOLD_CTX0     (PLIC_BASE_ADDRESS + 0x200000)
#define PLIC_CLAIM_CTX0         (PLIC_BASE_ADDRESS + 0x200004)

#define RVMODEL_SET_MEXT_INT(_R1, _R2)        \
  li _R1, 7;                                  \
  li _R2, PLIC_PRIORITY_1;                    \
  sw _R1, 0(_R2);                             \
  li _R1, 1;                                  \
  li _R2, PLIC_ENABLE_CTX0;                   \
  sw _R1, 0(_R2);                             \
  li _R2, PLIC_THRESHOLD_CTX0;                \
  sw zero, 0(_R2);

#define RVMODEL_CLR_MEXT_INT(_R1, _R2)        \
  li _R2, PLIC_CLAIM_CTX0;                    \
  lw _R1, 0(_R2);                             \
  sw _R1, 0(_R2);

#define RVMODEL_MSIP_ADDRESS (CLINT_BASE_ADDRESS + 0x0)
#define RVMODEL_SET_MSW_INT(_R1, _R2)        \
  li _R1, 1;                 \
  li _R2, RVMODEL_MSIP_ADDRESS;              \
  sw _R1, 0(_R2);

#define RVMODEL_CLR_MSW_INT(_R1, _R2)        \
  li _R2, RVMODEL_MSIP_ADDRESS;              \
  sw zero, 0(_R2);


##### Supervisor Interrupts #####

/* CVA6 PLIC Context 1 S-Mode Registers mapping */
#define PLIC_ENABLE_CTX1        (PLIC_BASE_ADDRESS + 0x002080)
#define PLIC_THRESHOLD_CTX1     (PLIC_BASE_ADDRESS + 0x201000)
#define PLIC_CLAIM_CTX1         (PLIC_BASE_ADDRESS + 0x201004)

/* CVA6 CLINT Supervisor Software Interrupt (ssip) mapped via ssip bit */
#define RVMODEL_SSIP_ADDRESS    (CLINT_BASE_ADDRESS + 0x4000)

#define RVMODEL_SET_SEXT_INT(_R1, _R2)        \
  li _R1, 7;                                  \
  li _R2, PLIC_PRIORITY_1;                    \
  sw _R1, 0(_R2);                             \
  li _R1, 1;                                  \
  li _R2, PLIC_ENABLE_CTX1;                   \
  sw _R1, 0(_R2);                             \
  li _R2, PLIC_THRESHOLD_CTX1;                \
  sw zero, 0(_R2);

#define RVMODEL_CLR_SEXT_INT(_R1, _R2)        \
  li _R2, PLIC_CLAIM_CTX1;                    \
  lw _R1, 0(_R2);                             \
  sw _R1, 0(_R2);

#define RVMODEL_SET_SSW_INT(_R1, _R2)        \
  li _R1, 1;                                  \
  li _R2, RVMODEL_SSIP_ADDRESS;               \
  sw _R1, 0(_R2);

#define RVMODEL_CLR_SSW_INT(_R1, _R2)        \
  li _R2, RVMODEL_SSIP_ADDRESS;               \
  sw zero, 0(_R2);

#endif // _RVMODEL_MACROS_H
