# sail_test.h
# RVMODEL macro definitions for Sail reference model
# Jordan Carlin jcarlin@hmc.edu October 2025, Sadhvi Narayana sanarayanan@hmc.edu February 2026
# SPDX-License-Identifier: BSD-3-Clause

#ifndef _COMPLIANCE_MODEL_H
#define _COMPLIANCE_MODEL_H

#define CLINT_BASE_ADDRESS 0x02000000

#define RVMODEL_DATA_SECTION \
   .pushsection .tohost,"aw",@progbits;                \
   .align 8; .global tohost; tohost: .dword 0;         \
   .align 8; .global fromhost; fromhost: .dword 0;     \
   .popsection


##### STARTUP #####

# Perform boot operations. Can be empty.
#define RVMODEL_BOOT

##### TERMINATION #####

// SAIL uses HTIF (Host-Target Interface) to terminate simulation.
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
#define RVMODEL_IO_INIT(_R1, _R2, _R3)


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


// Interrupt latency configuration
#define RVMODEL_INTERRUPT_LATENCY 10

#define RVMODEL_TIMER_INT_SOON_DELAY 100

#define RVMODEL_ACCESS_FAULT_ADDRESS 0x00000000


// Add to test_setup.h after other macros:

##### Machine Timer #####


# Set the machine timer (mtime) to the value in the register _R1.
# _R2 can be used as a temporary register (e.g. address of mtime).
# For RV32, only write the lower 32 bits of mtime and RVMODEL_SET_MTIMEH for upper 32 bits.
#define RVMODEL_MTIMECMP_ADDRESS  0x02004000  /* Address of mtimecmp CSR */
#define RVMODEL_MTIME_ADDRESS  0x0200BFF8  /* Address of mtime CSR */
#define RVMODEL_SET_MTIME(_R1, _R2)        \
  li   _R2, RVMODEL_MTIME_ADDRESS        ; /* MTIME address */ \
  SREG _R1, 0(_R2)            ; /* Set MTIME low */


#define RVMODEL_SET_MTIMEH(_R1, _R2)       \
  li   _R2, RVMODEL_MTIME_ADDRESS        ; /* MTIME address */ \
  SREG _R1, 4(_R2)            ; /* Set MTIME high */


##### Machine Interrupts #####

// TODO: need to implement external interrupts in SAIL
#define RVMODEL_MEXT_ADDRESS  0x80000000  /* Address of a memory mapped machine external interrupt generator */
#define RVMODEL_SET_MEXT_INT(_R1, _R2)        \
  li _R1, 1;               \
  li _R2, RVMODEL_MEXT_ADDRESS; \
  sw _R1, 0(_R2)            ; /* Set MEXT interrupt */ \


#define RVMODEL_CLR_MEXT_INT(_R1, _R2)        \
  li _R2, RVMODEL_MEXT_ADDRESS; \
  sw zero, 0(_R2)            ; /* Clear MEXT interrupt */ \


#define CLINT_MSIP_ADDRESS (CLINT_BASE_ADDRESS + 0x0)

#define RVMODEL_SET_MSW_INT(_R1, _R2)        \
  li _R1, 1;                 \
  li _R2, CLINT_MSIP_ADDRESS;              \
  sw _R1, 0(_R2);


#define RVMODEL_CLR_MSW_INT(_R1, _R2)        \
  li _R2, CLINT_MSIP_ADDRESS;              \
  sw zero, 0(_R2);



##### Supervisor Interrupts #####

// TODO: change this when Jordan implements the SAIL SEXT interrupt generator
#define SAIL_SEXT_ADDRESS  0x80000004  /* Address of a memory mapped supervisor external interrupt generator */
#define RVMODEL_SET_SEXT_INT(_R1, _R2)        \
  li _R1, 1;               \
  li _R2, SAIL_SEXT_ADDRESS; \
  sw _R1, 0(_R2)            ; /* Set SEXT interrupt */ \


#define RVMODEL_CLR_SEXT_INT(_R1, _R2)        \
  li _R2, SAIL_SEXT_ADDRESS; \
  sw zero, 0(_R2)            ; /* Clear SEXT interrupt */


// TODO: check to see if SAIL support this, and we may want to implement this in WALLY
#define CLINT_SSIP_ADDRESS (CLINT_BASE_ADDRESS + 0xC000)
#define RVMODEL_SET_SSW_INT(_R1, _R2)        \
  li _R1, 1;                 \
  li _R2, CLINT_SSIP_ADDRESS;              \
  sw _R1, 0(_R2);


#define RVMODEL_CLR_SSW_INT(_R1, _R2)        \
  li _R2, CLINT_SSIP_ADDRESS;              \
  sw zero, 0(_R2);

#endif // _COMPLIANCE_MODEL_H
