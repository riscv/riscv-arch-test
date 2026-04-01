# rvmodel_macros.h
# RVMODEL macro definitions for OpenHW CV32A65X core
# SPDX-License-Identifier: Apache-2.0

#ifndef _COMPLIANCE_MODEL_H
#define _COMPLIANCE_MODEL_H

#define RVMODEL_DATA_SECTION \
        .pushsection .tohost,"aw",@progbits;                \
        .align 8; .global tohost; tohost: .dword 0;         \
        .align 8; .global fromhost; fromhost: .dword 0;     \
        .popsection;

##### STARTUP #####

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
  self_loop_pass:         ;\
    j self_loop_pass      ;\

# Terminate test with a fail indication.
# When the test is run in simulation, this should end the simulation.
#define RVMODEL_HALT_FAIL \
  li x1, 3                ;\
  la t0, tohost           ;\
  write_tohost_fail:      ;\
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

##### Access Fault #####

#define RVMODEL_ACCESS_FAULT_ADDRESS 0x00000000

##### Machine Timer #####

# Standard CLINT-style timer addresses for the CVA6 subsystem.
#define RVMODEL_MTIME_ADDRESS    0x0200BFF8
#define RVMODEL_MTIMECMP_ADDRESS 0x02004000


##### Machine Interrupts #####

# External (MEIP) and Timer (MTIP) are supported.
# Logic is empty as these are level-sensitive signals driven by the testbench. 

#define RVMODEL_SET_MEXT_INT(_R1,_R2)
#define RVMODEL_CLR_MEXT_INT(_R1,_R2)
#define RVMODEL_SET_MSW_INT(_R1,_R2)      /* Disabled: MSIP not supported on cv32a65x  */
#define RVMODEL_CLR_MSW_INT(_R1,_R2)      /* Disabled: MSIP not supported on cv32a65x  */

#####  Supervisor Interrupts #####

# Supervisor mode is NOT supported on cv32a65x. 
#define RVMODEL_SET_SEXT_INT(_R1,_R2)
#define RVMODEL_CLR_SEXT_INT(_R1,_R2)
#define RVMODEL_SET_SSW_INT(_R1,_R2)
#define RVMODEL_CLR_SSW_INT(_R1,_R2)

#endif // _COMPLIANCE_MODEL_H
