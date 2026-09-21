# rvmodel_macros.h
# RVMODEL macro definitions for the lowRISC Ibex core in Ibex Simple System
# Written against lowRISC/ibex commit e9f55342edbd27e9e17a0e41b1c95a81abb5eac8
# SPDX-License-Identifier: Apache-2.0

#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

#define RVMODEL_DATA_SECTION

#define STANDARD_SM_SUPPORTED

# Ibex Simple System device map.
#   Quote: "assign cfg_device_addr_base[SimCtrl] = 32'h20000;
#           assign cfg_device_addr_base[Timer] = 32'h30000;"
#   https://github.com/lowRISC/ibex/blob/e9f55342edbd27e9e17a0e41b1c95a81abb5eac8/examples/simple_system/rtl/ibex_simple_system.sv#L120-L122
.EQU IBEX_SIM_CHAR_OUT, 0x00020000
.EQU IBEX_SIM_CTRL,     0x00020008

##### STARTUP #####

# mtimecmp resets to 0 while mtime starts counting immediately, so mip.MTIP is ALREADY
# PENDING at reset.  MEASURED: the very first `csrr mip` of a freshly reset core reads
# 0x00000080.  Push mtimecmp to all-ones before the tests run, or the first test that
# sets mstatus.MIE and mie.MTIE takes an immediate spurious timer interrupt.
#   Quote: "assign interrupt_d  = ((mtime_q >= mtimecmp_q) | interrupt_q) &
#           ~(mtimecmp_we | mtimecmph_we);"
#   https://github.com/lowRISC/ibex/blob/e9f55342edbd27e9e17a0e41b1c95a81abb5eac8/shared/rtl/timer.sv#L101
#   Quote: "mtimecmp_q <= 'b0;"  (reset value)
#   https://github.com/lowRISC/ibex/blob/e9f55342edbd27e9e17a0e41b1c95a81abb5eac8/shared/rtl/timer.sv#L94
#define RVMODEL_BOOT \
  li t0, RVMODEL_MTIMECMP_ADDRESS ;\
  li t1, -1                       ;\
  sw t1, 4(t0)                    ;\
  sw t1, 0(t0)                    ;

##### TERMINATION #####

# Writing 1 to bit 0 of SIM_CTRL halts the simulation.  There is only one halt path,
# so the process exit status carries no pass/fail information; run-ibex.sh decides the
# verdict from the RVCP-SUMMARY line in ibex_simple_system.log instead.
#   Quote: "* 0x8 - SIM_CTRL_ADDR - Write 1 to bit 0 to halt sim"
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

# A byte store to CHAR_OUT is appended to ibex_simple_system.log and flushed
# immediately.  Nothing reaches stdout, which is why run-ibex.sh reads the log.
#   Quote: "* 0x0 - CHAR_OUT_ADDR - [7:0] of write data output via output_char DPI call"
#   https://github.com/lowRISC/ibex/blob/e9f55342edbd27e9e17a0e41b1c95a81abb5eac8/shared/rtl/sim/simulator_ctrl.sv#L11
#   Quote: ".LogName("ibex_simple_system.log")"
#   https://github.com/lowRISC/ibex/blob/e9f55342edbd27e9e17a0e41b1c95a81abb5eac8/examples/simple_system/rtl/ibex_simple_system.sv#L345
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

# Simple System decodes exactly three devices (RAM at 0x0010_0000, SimCtrl at
# 0x0002_0000 and Timer at 0x0003_0000); every other address raises a bus error, which
# Ibex reports as a load/store access fault.  MEASURED: `lw` from 0x0040_0000 gives
# mcause 5 with mtval 0x00400000, and a jump there gives mcause 1 with mtval = PC.
# 0x0040_0000 is also outside every memory.regions entry in sail.json, so the
# reference model faults on it too.
#   Quote: "decode_err_resp <= host_sel_valid & !device_sel_valid;" and
#   "host_err_o[host]    = device_err_i[device_sel_resp]    | decode_err_resp;"
#   https://github.com/lowRISC/ibex/blob/e9f55342edbd27e9e17a0e41b1c95a81abb5eac8/shared/rtl/bus.sv#L99
#   https://github.com/lowRISC/ibex/blob/e9f55342edbd27e9e17a0e41b1c95a81abb5eac8/shared/rtl/bus.sv#L126
# NOTE: only the DATA side goes through this bus. The instruction port is wired
# straight to port B of the RAM with its error input tied off, so instruction
# fetches can never raise an access fault - see ci.yaml and the discrepancy report.
#   Quote: "assign instr_err = '0;"
#   https://github.com/lowRISC/ibex/blob/e9f55342edbd27e9e17a0e41b1c95a81abb5eac8/examples/simple_system/rtl/ibex_simple_system.sv#L134
#define RVMODEL_ACCESS_FAULT_ADDRESS 0x00400000

##### Interrupt Latency #####

#define RVMODEL_INTERRUPT_LATENCY 10
#define RVMODEL_MAX_CYCLES_PER_TIMER_TICK 1

##### Machine Timer #####

# Unlike most small cores, Simple System models a real RISC-V machine timer, so the
# Zicntr time-CSR emulation and the timer-interrupt tests are both reachable.
#   Quote: "localparam bit [9:0] MTIME_LOW = 0; ... localparam bit [9:0] MTIMECMP_LOW = 8;"
#   https://github.com/lowRISC/ibex/blob/e9f55342edbd27e9e17a0e41b1c95a81abb5eac8/shared/rtl/timer.sv#L35-L37
#   Quote: "A basic timer peripheral capable of generating interrupts based on the
#   RISC-V Machine Timer Registers"
#   https://github.com/lowRISC/ibex/blob/e9f55342edbd27e9e17a0e41b1c95a81abb5eac8/examples/simple_system/README.md#L9
# mtime increments once per clock cycle.
#   Quote: "// mtime increments every cycle / assign mtime_inc = mtime_q + 64'd1;"
#   https://github.com/lowRISC/ibex/blob/e9f55342edbd27e9e17a0e41b1c95a81abb5eac8/shared/rtl/timer.sv#L55-L56
#define RVMODEL_MTIME_ADDRESS     0x00030000
#define RVMODEL_MTIMECMP_ADDRESS  0x00030008
#define RVMODEL_TIMER_INT_SOON_DELAY 2000

##### Machine Interrupts #####

# Simple System ties irq_external_i and irq_software_i to zero; only irq_timer_i is
# driven.  There is therefore no way for software to raise a machine external or
# software interrupt, so these hooks are empty and the suites that depend on them are
# excluded in ci.yaml.
#   Quote: ".irq_software_i            (1'b0), ... .irq_external_i            (1'b0),"
#   https://github.com/lowRISC/ibex/blob/e9f55342edbd27e9e17a0e41b1c95a81abb5eac8/examples/simple_system/rtl/ibex_simple_system.sv#L281-L283
#define RVMODEL_SET_MEXT_INT(_R1, _R2)
#define RVMODEL_CLR_MEXT_INT(_R1, _R2)
#define RVMODEL_SET_MSW_INT(_R1, _R2)
#define RVMODEL_CLR_MSW_INT(_R1, _R2)

##### Supervisor Interrupts #####
# Ibex has M and U mode but no S-mode, so these can never occur.

#define RVMODEL_SET_SEXT_INT(_R1, _R2)
#define RVMODEL_CLR_SEXT_INT(_R1, _R2)
#define RVMODEL_SET_SSW_INT(_R1, _R2)
#define RVMODEL_CLR_SSW_INT(_R1, _R2)

#endif // _RVMODEL_MACROS_H
