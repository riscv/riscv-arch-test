# model_test.h
# Trickbox macro definitions for Spike
# Jordan Carlin jcarlin@hmc.edu Jan 2026
# SPDX-License-Identifier: BSD-3-Clause

#ifndef _COMPLIANCE_MODEL_H
#define _COMPLIANCE_MODEL_H

#define RVMODEL_DATA_SECTION \
        .pushsection .tohost,"aw",@progbits;                \
        .align 8; .global tohost; tohost: .dword 0;         \
        .align 8; .global fromhost; fromhost: .dword 0;     \
        .popsection

##### STARTUP #####

# Perform boot operations. Can be empty.
#define RVMODEL_BOOT

##### TERMINATION #####

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
# TODO: Not printing successfully
#define RVMODEL_IO_WRITE_STR(_R1, _R2, _R3, _STR_PTR)               \
1:                           ;                       \
  lbu _R1, 0(_STR_PTR)        ;/* Load byte */        \
  beqz _R1, 3f                ;/* Exit if null */     \
2: /* htif_putc */           ;                      \
  la _R2, tohost       ;   \
  /* device=1 (terminal), cmd=1 (output) */ \
  li _R3, 0x0101000000000000 ;\
  or _R3, _R1, _R3           ;/* Combine char with cmd */ \
  sw _R3, 0(_R2)             ;/* Write to tohost */  \
  addi _STR_PTR, _STR_PTR, 1 ;/* Next char */        \
  j 1b                       ;/* Loop */             \
3:

##### Machine Timer #####

# Set the machine timer (mtime) to the value in the register _R1.
# _R2 can be used as a temporary register (e.g. address of mtime).
# For RV32, only write the lower 32 bits of mtime and RVMODEL_SET_MTIMEH for upper 32 bits.
#define RVMODEL_MTIME_ADDR  0x0200BFF8  /* Address of mtime CSR */
#define RVMODEL_SET_MTIME(_R1, _R2)        \
    li   _R2, RVMODEL_MTIME_ADDR        ; /* MTIME address */ \
    SREG _R1, 0(_R2)            ; /* Set MTIME low */

#define RVMODEL_SET_MTIMEH(_R1, _R2)       \
    li   _R2, RVMODEL_MTIME_ADDR        ; /* MTIME address */ \
    SREG _R1, 4(_R2)            ; /* Set MTIME high */


##### Machine Interrupts #####

#define RVMODEL_SET_MEXT_INT

#define RVMODEL_CLR_MEXT_INT

#define RVMODEL_SET_MTIMER_INT

#define RVMODEL_CLR_MTIMER_INT

#define RVMODEL_SET_MTIMER_INT_SOON

#define RVMODEL_SET_MSW_INT

#define RVMODEL_CLR_MSW_INT

##### Supervisor Interrupts #####

#define RVMODEL_SET_SEXT_INT

#define RVMODEL_CLR_SEXT_INT

#define RVMODEL_SET_STIMER_INT

#define RVMODEL_CLR_STIMER_INT

#define RVMODEL_SET_STIMER_INT_SOON

#define RVMODEL_SET_SSW_INT

#define RVMODEL_CLR_SSW_INT

##### Hypervisor Interrupts #####

#define RVMODEL_SET_VEXT_INT

#define RVMODEL_CLR_VEXT_INT

#define RVMODEL_SET_VTIMER_INT

#define RVMODEL_CLR_VTIMER_INT

#define RVMODEL_SET_VTIMER_INT_SOON

#define RVMODEL_SET_VSW_INT

#define RVMODEL_CLR_VSW_INT

#endif // _COMPLIANCE_MODEL_H
