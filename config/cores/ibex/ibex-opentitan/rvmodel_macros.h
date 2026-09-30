# rvmodel_macros.h
# RVMODEL macro definitions for the lowRISC Ibex core in Ibex Simple System
# Written against lowRISC/ibex commit e9f55342edbd27e9e17a0e41b1c95a81abb5eac8
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0

#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

#define RVMODEL_DATA_SECTION

#define STANDARD_SM_SUPPORTED

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

##### Access faults #####

# RVMODEL_ACCESS_FAULT_ADDRESS is left undefined because no fetch address faults. Simple System
# ties the instruction error off and indexes the RAM with addr[19:2] for every fetch.
#   https://github.com/lowRISC/ibex/blob/e9f55342edbd27e9e17a0e41b1c95a81abb5eac8/examples/simple_system/rtl/ibex_simple_system.sv#L134
#   https://github.com/lowRISC/ibex/blob/e9f55342edbd27e9e17a0e41b1c95a81abb5eac8/shared/rtl/ram_2p.sv#L48

##### Interrupt Latency #####

#define RVMODEL_INTERRUPT_LATENCY 10

##### Machine Timer #####

# mtime increments once per clock cycle.
#   https://github.com/lowRISC/ibex/blob/e9f55342edbd27e9e17a0e41b1c95a81abb5eac8/shared/rtl/timer.sv#L35-L38
#define RVMODEL_MTIME_ADDRESS     0x00030000
#define RVMODEL_MTIMECMP_ADDRESS  0x00030008
# Arming the timer from U-mode takes four T-SBI round trips of about 900 cycles each, so the
# delay must exceed about 2700 cycles for the interrupt to arrive after the setup returns.
#define RVMODEL_TIMER_INT_SOON_DELAY 10000

#endif // _RVMODEL_MACROS_H
