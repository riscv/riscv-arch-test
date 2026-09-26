# rvmodel_macros.h
# RVMODEL macro definitions for CVA6 + Ara (cv64a6_imafdcv_sv39, 4 lanes, VLEN 512)
# Written against Ara  @ 34bd3bc152421b4601a7bf3d6e8e91ffb545c99e
#                 CVA6 @ 99eac9a649001bdf5b8f9da52e0ca73d5c48db1c
# SPDX-License-Identifier: Apache-2.0

#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

# No HTIF. Termination is a store to a control register, not a tohost symbol, so
# there is no .tohost section to emit.
#define RVMODEL_DATA_SECTION

#define STANDARD_SM_SUPPORTED

# The Ara SoC decodes exactly three windows: DRAM at 0x8000_0000, a mock UART at
# 0xC000_0000 and the control registers at 0xD000_0000.
#   Quote: "DRAMBase = 64'h8000_0000, UARTBase = 64'hC000_0000, CTRLBase = 64'hD000_0000"
#   https://github.com/pulp-platform/ara/blob/34bd3bc152421b4601a7bf3d6e8e91ffb545c99e/hardware/src/ara_soc.sv#L83
.EQU ARA_UART_BASE, 0xC0000000
.EQU ARA_CTRL_BASE, 0xD0000000

##### STARTUP #####

# Nothing to program: the reset vector is the DRAM base where the test is linked, the
# UART needs no initialisation, and there is no memory controller to bring up.
//#define RVMODEL_BOOT

##### TERMINATION #####

# A 64-bit store to the control registers' exit word ends the simulation. The
# testbench passes (exit_o >> 1) to $finish, so storing 0 exits 0 and storing 1
# exits 0 too (1 >> 1 == 0) - the fail path must therefore store a value of at
# least 2 to produce a non-zero exit code. This is NOT the HTIF tohost protocol,
# and the cv32a65x macros (which store to a `tohost` symbol) simply hang this DUT.
#   Quote: "assign exit_o           = {exit, logic'(|wr_active_q[7:0])};"
#   https://github.com/pulp-platform/ara/blob/34bd3bc152421b4601a7bf3d6e8e91ffb545c99e/hardware/src/ctrl_registers.sv#L108
#   Quote: "$info(\"Core Test \", $sformatf(\"*** SUCCESS *** (tohost = %0d)\", (exit_o >> 1)));
#           ... $finish(exit_o >> 1);"
#   https://github.com/pulp-platform/ara/blob/34bd3bc152421b4601a7bf3d6e8e91ffb545c99e/hardware/tb/ara_tb_verilator.sv#L51
#
# The runner does not rely on the exit code alone: it also scans the console for the
# RVCP-SUMMARY lines and for the testbench's timeout message, because a cycle-limit
# timeout also exits 0.
#define RVMODEL_HALT_PASS   \
  li t0, ARA_CTRL_BASE     ;\
  li t1, 0                 ;\
  sd t1, 0(t0)             ;\
  self_loop_pass:          ;\
    j self_loop_pass       ;

#define RVMODEL_HALT_FAIL   \
  li t0, ARA_CTRL_BASE     ;\
  li t1, 2                 ;\
  sd t1, 0(t0)             ;\
  self_loop_fail:          ;\
    j self_loop_fail       ;

##### IO #####

# The mock UART's transmit holding register is at offset 0 and every byte written to
# it is printed by the testbench. There is no status register to poll and no
# initialisation sequence.
#   Quote: "UARTBase = 64'hC000_0000"
#   https://github.com/pulp-platform/ara/blob/34bd3bc152421b4601a7bf3d6e8e91ffb545c99e/hardware/src/ara_soc.sv#L84
# Verified on the Verilator model: a byte store loop prints to stdout with no setup.
#define RVMODEL_IO_WRITE_STR(_R1, _R2, _R3, _STR_PTR) \
1:                           ;                        \
  lbu  _R1, 0(_STR_PTR)      ; /* Load byte */        \
  beqz _R1, 3f               ; /* Exit if null */     \
2:                           ;                        \
  li   _R2, ARA_UART_BASE    ;                        \
  sb   _R1, 0(_R2)           ;                        \
  addi _STR_PTR, _STR_PTR, 1 ; /* Next char */        \
  j 1b                       ; /* Loop */             \
3:

##### Access Fault #####

# 0x5000_0000 lies outside all three windows the Ara SoC decodes (DRAM at 0x8000_0000,
# UART at 0xC000_0000, control registers at 0xD000_0000), and outside every region
# declared in sail.json, so the reference model raises a clean access fault there.
#
# THE DUT CANNOT RAISE A DATA ACCESS FAULT AT ALL. With NrPMPEntries overridden to 0 by
# the SoC, the only two sources of a load/store access fault in CVA6 are a PMP violation
# (pmp_data_if.sv:130-132) and a page-table-walk access exception (cva6_mmu.sv:699-707),
# which itself needs PMP. Measured on the Verilator model: a scalar `ld` from
# 0x5000_0000 raises no exception, never retires, and deadlocks the core as soon as an
# instruction needs the destination register; a vector load from the same address hangs
# the model outright.
#
# The macro is defined anyway, deliberately. ACT's Vls8/Vls16/Vls32/Vls64,
# Exceptions*, Sstvala and SvZicbo generators reference RVMODEL_ACCESS_FAULT_ADDRESS
# WITHOUT guarding on whether it is defined, so leaving it undefined does not merely
# skip those testcases - it fails assembly ("non-constant expression in .if") and the
# whole suite never builds. Defining it confines the damage to the individual ELFs that
# actually probe the address: those hang and are caught by the runner's cycle-limit
# check, and every other test in the same suite still runs. See the discrepancy notes.
#define RVMODEL_ACCESS_FAULT_ADDRESS 0x50000000

##### Interrupt Latency #####

#define RVMODEL_INTERRUPT_LATENCY 10

##### Machine Timer #####

# There is no mtime/mtimecmp device and no timer interrupt: ara_system.sv ties
# time_irq_i to zero. The `time` CSR is not implemented either - it is declared in
# riscv_pkg but never handled in csr_regfile.sv, so it falls through to
# read_access_exception. Measured: `csrr a0, time` raises mcause 2 with mtval set to
# the instruction encoding.
# Leaving RVMODEL_MTIME_ADDRESS undefined disables all machine-timer interrupt
# testing, which is the documented behaviour in check_defines.h, and is why Zicntr
# is not declared in the UDB configuration.
//#define RVMODEL_MTIME_ADDRESS
//#define RVMODEL_MTIMECMP_ADDRESS
#define RVMODEL_TIMER_INT_SOON_DELAY 100

##### Machine Interrupts #####

# Every interrupt input of the system is tied to zero, so no interrupt can be
# generated by any means. Measured: writing all ones to mie leaves mip reading 0.
#   Quote: ".irq_i ('0 ), .ipi_i ('0 ), .time_irq_i ('0 ), .debug_req_i ('0 ),"
#   https://github.com/pulp-platform/ara/blob/34bd3bc152421b4601a7bf3d6e8e91ffb545c99e/hardware/src/ara_system.sv#L144
# The macros must still be defined; they are no-ops and the interrupt suites are
# excluded in ci.yaml.
#define RVMODEL_SET_MEXT_INT(_R1, _R2)
#define RVMODEL_CLR_MEXT_INT(_R1, _R2)
#define RVMODEL_SET_MSW_INT(_R1, _R2)
#define RVMODEL_CLR_MSW_INT(_R1, _R2)

##### Supervisor Interrupts #####

#define RVMODEL_SET_SEXT_INT(_R1, _R2)
#define RVMODEL_CLR_SEXT_INT(_R1, _R2)
#define RVMODEL_SET_SSW_INT(_R1, _R2)
#define RVMODEL_CLR_SSW_INT(_R1, _R2)

#endif // _RVMODEL_MACROS_H
