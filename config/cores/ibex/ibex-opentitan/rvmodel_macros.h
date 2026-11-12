# rvmodel_macros.h
# RVMODEL macro definitions for the lowRISC Ibex core in Ibex Simple System
# Written against lowRISC/ibex commit e9f55342edbd27e9e17a0e41b1c95a81abb5eac8
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0

#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

// Device addresses, interrupt timings and STANDARD_SM_SUPPORTED are in the
// dut_environment block of the config's UDB yaml. Only the driver library
// (librvmodel.a) is built from this file; test objects never see it.

#define RVMODEL_DATA_SECTION

# Ibex Simple System device map.
#   https://github.com/lowRISC/ibex/blob/e9f55342edbd27e9e17a0e41b1c95a81abb5eac8/examples/simple_system/rtl/ibex_simple_system.sv#L118-L123
.EQU IBEX_SIM_CHAR_OUT, 0x00020000
.EQU IBEX_SIM_CTRL,     0x00020008

##### TERMINATION #####

# Writing 1 to bit 0 of SIM_CTRL halts the simulation.
#   https://github.com/lowRISC/ibex/blob/e9f55342edbd27e9e17a0e41b1c95a81abb5eac8/shared/rtl/sim/simulator_ctrl.sv#L14
#define RVMODEL_HALT_PASS  \
  li t0, IBEX_SIM_CTRL    ;\
  li t1, 1                ;\
  sw t1, 0(t0)            ;\
  self_loop_pass:         ;\
    j self_loop_pass      ;

#define RVMODEL_HALT_FAIL \
  li t0, IBEX_SIM_CTRL    ;\
  li t1, 1                ;\
  sw t1, 0(t0)            ;\
  self_loop_fail:         ;\
    j self_loop_fail      ;

##### IO #####

# A byte store to CHAR_OUT is appended to ibex_simple_system.log.
#   https://github.com/lowRISC/ibex/blob/e9f55342edbd27e9e17a0e41b1c95a81abb5eac8/shared/rtl/sim/simulator_ctrl.sv#L11
#define RVMODEL_IO_WRITE_STR(_R1, _R2, _R3, _STR_PTR) \
1:                           ;                        \
  lbu  _R1, 0(_STR_PTR)      ; /* Load byte */        \
  beqz _R1, 3f               ; /* Exit if null */     \
2:                           ;                        \
  li   _R2, IBEX_SIM_CHAR_OUT ;                       \
  sb   _R1, 0(_R2)           ;                        \
  addi _STR_PTR, _STR_PTR, 1 ; /* Next char */        \
  j 1b                       ; /* Loop */             \
3:

#endif // _RVMODEL_MACROS_H
