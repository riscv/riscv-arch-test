# rvmodel_macros.h
# RVMODEL macro definitions for OpenHW CV32E20 core
# SPDX-License-Identifier: Apache-2.0

#ifndef _COMPLIANCE_MODEL_H
#define _COMPLIANCE_MODEL_H

#define RVMODEL_DATA_SECTION \
        .pushsection .tohost,"aw",@progbits;                \
        .align 8; .global tohost; tohost: .dword 0;         \
        .align 8; .global fromhost; fromhost: .dword 0;     \
        .popsection;

##### STARTUP #####

# Perform boot operations. Can be empty.
#define RVMODEL_BOOT

# Address to use for load/store fault tests that should cause an access fault on the DUT.
#define RVMODEL_ACCESS_FAULT_ADDRESS 0x00000000

##### TERMINATION #####

# Terminate test with a pass indication.
# When the test is run in simulation, this should end the simulation.
#define RVMODEL_HALT_PASS  \
  li x1, 123456789        ;\
  li t0, 0x20000000       ;\
  write_halt_pass:        ;\
    sw x1, 0(t0)          ;\
    sw x0, 4(t0)          ;\
  self_loop_pass:         ;\
    j self_loop_pass      ;\

# Terminate test with a fail indication.
# When the test is run in simulation, this should end the simulation.
#define RVMODEL_HALT_FAIL \
  li x1, 1                ;\
  li t0, 0x20000000       ;\
  write_halt_fail:        ;\
    sw x1, 0(t0)          ;\
    sw x0, 4(t0)          ;\
  self_loop_fail:         ;\
    j self_loop_fail      ;\

##### IO #####

# Initialization steps needed prior to writing to the console
# _R1, _R2, and _R3 can be used as temporary registers if needed.
# Do not modify any other registers (or make sure to restore them).
#define RVMODEL_IO_INIT(_R1, _R2, _R3)

# Prints a null-terminated string using a DUT specific mechanism.
# A pointer to the string is passed in _STR_PTR.
# _R1, _R2, and _R3 can be used as temporary registers if needed.
# Do not modify any other registers (or make sure to restore them).
#define RVMODEL_IO_WRITE_STR(_R1, _R2, _R3, _STR_PTR) \
1:                           ;                        \
  lbu  _R1, 0(_STR_PTR)      ; /* Load byte */        \
  beqz _R1, 3f               ; /* Exit if null */     \
2:                           ;                        \
  li   _R2, 0x10000000       ; /* virtual printer */  \
  sw   _R1, 0(_R2)           ;                        \
  addi _STR_PTR, _STR_PTR, 1 ; /* Next char */        \
  j 1b                       ; /* Loop */             \
3:

##### Machine Timer #####
/*
 * NOTE: The following parameters are intentionally left empty.
 *
 * Running 'make CONFIG_FILES=' will include Machine-mode (sm) tests that
 * will FAIL because these platform-level memory-mapped registers are
 * not defined. This is a temporary state.
 *
 * To properly run the suite by excluding these specific tests (the recommended
 * workaround), refer to the instructions here:
 * https://github.com/riscv/riscv-arch-test/issues/1135#issuecomment-4140522435
 */
#define RVMODEL_MTIME_ADDRESS  /* unimplemented */

#define RVMODEL_MTIMECMP_ADDRESS   /* unimplemented */
##### Machine Interrupts #####

#define RVMODEL_SET_MEXT_INT(_R1, _R2)

#define RVMODEL_CLR_MEXT_INT(_R1, _R2)

#define RVMODEL_SET_MSW_INT(_R1, _R2)

#define RVMODEL_CLR_MSW_INT(_R1, _R2)

##### Supervisor Interrupts #####

#define RVMODEL_SET_SEXT_INT(_R1, _R2)

#define RVMODEL_CLR_SEXT_INT(_R1, _R2)

#define RVMODEL_SET_SSW_INT(_R1, _R2)

#define RVMODEL_CLR_SSW_INT(_R1, _R2)

#endif // _COMPLIANCE_MODEL_H
