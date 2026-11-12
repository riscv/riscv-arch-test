# rvmodel_macros.h
# RVMODEL macro definitions for CV32E40S core
# SPDX-License-Identifier: Apache-2.0

#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

// Device addresses, interrupt timings and STANDARD_SM_SUPPORTED are in the
// dut_environment block of the config's UDB yaml. Only the driver library
// (librvmodel.a) is built from this file; test objects never see it.

#define RVMODEL_DATA_SECTION

##### STARTUP #####

# Perform boot operations.
# CV32E40S resets mcountinhibit=0x5 (cycle+instret inhibited). Clear it so
# cycle/instret increment as Zicntr tests expect.
# .option arch, +zicsr is needed because I tests compile with -march=rv32i
# which does not include Zicsr (binutils >= 2.38).
//#define RVMODEL_BOOT \

##### TERMINATION #####

# Terminate test with a pass indication.
#define RVMODEL_HALT_PASS  \
  li x1, 123456789                ;\
  li x2, 0x20000000       ;\
  write_halt_pass:      ;\
    sw x1, 0(x2)          ;\
    sw x0, 4(x2)          ;\
  self_loop_pass:         ;\
    j self_loop_pass      ;\

# Terminate test with a fail indication.
#define RVMODEL_HALT_FAIL \
  li x1, 1                ;\
  li x2, 0x20000000       ;\
  write_halt_fail:      ;\
    sw x1, 0(x2)          ;\
    sw x0, 4(x2)          ;\
  self_loop_fail:         ;\
    j self_loop_fail      ;\

##### IO #####

#define RVMODEL_IO_INIT(_R1, _R2, _R3)

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

##### Machine Interrupts #####

#define RVMODEL_SET_MEXT_INT(_R1, _R2)
#define RVMODEL_CLR_MEXT_INT(_R1, _R2)

#endif // _RVMODEL_MACROS_H
