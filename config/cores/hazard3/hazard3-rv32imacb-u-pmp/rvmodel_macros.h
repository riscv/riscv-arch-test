# rvmodel_macros.h
# RVMODEL macro definitions for the Hazard3 core (the RP2350 CPU)
# Written against Wren6991/Hazard3 commit 8af992930f71a69b0e06c38734c1094f41a05ca0 (v1.1.1)
# SPDX-License-Identifier: Apache-2.0

#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

#define RVMODEL_DATA_SECTION

#define STANDARD_SM_SUPPORTED

# Hazard3's reference testbench decodes one IO window at 0xC000_0000. Every register
# below is an offset into it.
#   Quote: "static const unsigned int IO_BASE = 0xc0000000;"
#   Quote: "IO_PRINT_CHAR = 0x000, IO_PRINT_U32 = 0x004, IO_EXIT = 0x008,
#           IO_SET_SOFTIRQ = 0x010, IO_CLR_SOFTIRQ = 0x014, IO_GLOBMON_EN = 0x018,
#           IO_POISON_ADDR = 0x01c, IO_SET_IRQ = 0x020, IO_CLR_IRQ = 0x030,
#           IO_MTIME = 0x100, IO_MTIMEH = 0x104, IO_MTIMECMP0 = 0x108, IO_MTIMECMP0H = 0x10c"
#   https://github.com/Wren6991/Hazard3/blob/8af992930f71a69b0e06c38734c1094f41a05ca0/test/sim/tb_common/include/tb_constants.h#L14-L31
.EQU H3_IO_BASE,        0xc0000000
.EQU H3_IO_PRINT_CHAR,  0x000
.EQU H3_IO_EXIT,        0x008
.EQU H3_IO_SET_SOFTIRQ, 0x010
.EQU H3_IO_CLR_SOFTIRQ, 0x014
.EQU H3_IO_GLOBMON_EN,  0x018
.EQU H3_IO_SET_IRQ,     0x020
.EQU H3_IO_CLR_IRQ,     0x030
.EQU H3_IO_MTIMECMP0,   0x108
.EQU H3_IO_MTIMECMP0H,  0x10c

##### STARTUP #####

# Three pieces of DUT-specific initialisation, all of them required:
#
# 1. mcountinhibit.CY and .IR reset to 1, so mcycle and minstret are stopped out of
#    reset. Every Zicntr/Sm counter test would read a frozen counter.
#      Quote: "| 2 | `ir` | When 1, inhibit counting of `minstret`/`minstreth`. Resets to 1."
#      Quote: "| 0 | `cy` | When 1, inhibit counting of `mcycle`/`mcycleh`. Resets to 1."
#      https://github.com/Wren6991/Hazard3/blob/8af992930f71a69b0e06c38734c1094f41a05ca0/doc/sections/csr.adoc#L371-L372
#
# 2. The testbench's mtimecmp resets to 0 while mtime starts at 0 and increments every
#    cycle, so the machine timer interrupt is asserted from cycle 0. Any test that sets
#    mie.MTIE before arming mtimecmp would take an immediate spurious timer interrupt.
#    Disarm it by writing all-ones, high word first.
#      Quote: "mtime = 0; mtimecmp[0] = 0;"
#      https://github.com/Wren6991/Hazard3/blob/8af992930f71a69b0e06c38734c1094f41a05ca0/test/sim/tb_common/tb_memio.cpp#L7-L9
#      Quote: "++mtime; tb.set_timer_irq((uint8_t)((mtime >= mtimecmp[0]) | (mtime >= mtimecmp[1]) << 1));"
#      https://github.com/Wren6991/Hazard3/blob/8af992930f71a69b0e06c38734c1094f41a05ca0/test/sim/tb_common/tb_memio.cpp#L162-L164
#
# 3. Enable the testbench's AHB5 global exclusive monitor. Hazard3 always queries the
#    global monitor for LR/SC and AMO, and the testbench ties HEXOKAY high until the
#    monitor is enabled, which would make every sc.w with a live local reservation
#    succeed regardless of address.
#      Quote: "Exclusive transfer success. Hazard3 always queries the global monitor, so
#      tie this input _high_ if you do not implement global exclusive monitoring"
#      https://github.com/Wren6991/Hazard3/blob/8af992930f71a69b0e06c38734c1094f41a05ca0/doc/sections/configuration_and_integration.adoc#L292
#      Quote: "resp.exokay = !memio.monitor_enabled;"
#      https://github.com/Wren6991/Hazard3/blob/8af992930f71a69b0e06c38734c1094f41a05ca0/test/sim/tb_verilator/tb.cpp#L89
#
# RVMODEL_BOOT runs before RVTEST_INIT_REGS, so t0/t1 are free.
#define RVMODEL_BOOT \
  csrw mcountinhibit, zero                ;\
  li   t0, H3_IO_BASE                     ;\
  li   t1, -1                             ;\
  sw   t1, H3_IO_MTIMECMP0H(t0)           ;\
  sw   t1, H3_IO_MTIMECMP0(t0)            ;\
  li   t1, 1                              ;\
  sw   t1, H3_IO_GLOBMON_EN(t0)           ;

# Address to use for load/store tests that should cause an access fault on the DUT.
# The testbench backs 16 MB of RAM at 0x8000_0000 and decodes the IO window at
# 0xC000_0000; every other address returns an AHB error response, which Hazard3 reports
# as a load or store access fault (cause 5 / 7). Verified by directed probe: a store to
# 0x9000_0000 traps with mcause 7.
#   Quote: "} else { resp.err = true; }"  (the final else of the address decode)
#   https://github.com/Wren6991/Hazard3/blob/8af992930f71a69b0e06c38734c1094f41a05ca0/test/sim/tb_common/tb_memio.cpp#L126
#define RVMODEL_ACCESS_FAULT_ADDRESS 0x90000000

##### TERMINATION #####

# A word written to IO_EXIT ends the simulation, and with --cpuret the testbench's
# process exit status is that word. Verified: 0 -> 0, 7 -> 7, cycle limit -> 255.
#   Quote: "} else if (req.addr == IO_BASE + IO_EXIT) { if (!memio.exit_req) {
#           memio.exit_req = true; memio.exit_code = req.wdata; } }"
#   https://github.com/Wren6991/Hazard3/blob/8af992930f71a69b0e06c38734c1094f41a05ca0/test/sim/tb_common/tb_memio.cpp#L92-L96
#   Quote: "} else if (args.propagate_return_code && memio.exit_req) { return memio.exit_code; }"
#   https://github.com/Wren6991/Hazard3/blob/8af992930f71a69b0e06c38734c1094f41a05ca0/test/sim/tb_verilator/tb.cpp#L213-L214
#define RVMODEL_HALT_PASS  \
  li t0, H3_IO_BASE       ;\
  sw x0, H3_IO_EXIT(t0)   ;\
  self_loop_pass:         ;\
    j self_loop_pass      ;

#define RVMODEL_HALT_FAIL \
  li t0, H3_IO_BASE       ;\
  li t1, 1                ;\
  sw t1, H3_IO_EXIT(t0)   ;\
  self_loop_fail:         ;\
    j self_loop_fail      ;

##### IO #####

# A byte written to IO_PRINT_CHAR is printed verbatim; there is no character filtering
# and no store-merging hazard, because Hazard3 issues every store to the bus with no
# buffering or write combining.
#   Quote: "} else if (req.addr == IO_BASE + IO_PRINT_CHAR) { fprintf(tb.logfile, \"%c\", (char)(req.wdata & 0xff)); }"
#   https://github.com/Wren6991/Hazard3/blob/8af992930f71a69b0e06c38734c1094f41a05ca0/test/sim/tb_common/tb_memio.cpp#L88-L89
#   Quote: "All stores are issued to the external bus, even if they alias with a later
#   store; there is no dead store elimination or write merging. Stores are issued
#   immediately to the bus without buffering inside the core."
#   https://github.com/Wren6991/Hazard3/blob/8af992930f71a69b0e06c38734c1094f41a05ca0/doc/sections/bus_behaviour.adoc#L52
#define RVMODEL_IO_WRITE_STR(_R1, _R2, _R3, _STR_PTR) \
1:                           ;                        \
  lbu  _R1, 0(_STR_PTR)      ; /* Load byte */        \
  beqz _R1, 3f               ; /* Exit if null */     \
2:                           ;                        \
  li   _R2, H3_IO_BASE       ;                        \
  sb   _R1, H3_IO_PRINT_CHAR(_R2) ;                   \
  addi _STR_PTR, _STR_PTR, 1 ; /* Next char */        \
  j 1b                       ; /* Loop */             \
3:

##### Interrupt Latency #####

#define RVMODEL_INTERRUPT_LATENCY 10

##### Machine Timer #####

# The testbench's mtime advances by one on every clock cycle, so one timer tick is one
# core cycle.
#   Quote: "void mem_io_state::step(tb_top &tb) { ++mtime; ..."
#   https://github.com/Wren6991/Hazard3/blob/8af992930f71a69b0e06c38734c1094f41a05ca0/test/sim/tb_common/tb_memio.cpp#L160-L164
#define RVMODEL_MAX_CYCLES_PER_TIMER_TICK 1

#define RVMODEL_TIMER_INT_SOON_DELAY 100

# Hazard3 has no time/timeh CSR, but the testbench provides the standard 64-bit RISC-V
# machine timer as a memory-mapped mtime/mtimecmp pair, so ACT emulates time reads from
# it (TIME_CSR_IMPLEMENTED is false in the UDB config) and the timer interrupt tests run.
#   Quote: "| 7 | `mtip` | Timer interrupt pending. Level-sensitive interrupt signal from
#   outside the core. Connected to a standard, external RISC-V 64-bit timer."
#   https://github.com/Wren6991/Hazard3/blob/8af992930f71a69b0e06c38734c1094f41a05ca0/doc/sections/csr.adoc#L180
#define RVMODEL_MTIME_ADDRESS     0xc0000100
#define RVMODEL_MTIMECMP_ADDRESS  0xc0000108

##### Machine Interrupts #####

# The testbench drives the core's level-sensitive irq / soft_irq pins from a pair of
# set/clear registers, and the state is sticky until explicitly cleared.
#   Quote: "} else if (req.addr == IO_BASE + IO_SET_SOFTIRQ) { memio.soft_irq_state |= req.wdata;
#           tb.set_soft_irq(memio.soft_irq_state); } else if (req.addr == IO_BASE + IO_CLR_SOFTIRQ) {
#           memio.soft_irq_state &= ~req.wdata; ... }"
#   https://github.com/Wren6991/Hazard3/blob/8af992930f71a69b0e06c38734c1094f41a05ca0/test/sim/tb_common/tb_memio.cpp#L97-L102
#   Quote: "} else if (req.addr == IO_BASE + IO_SET_IRQ) { memio.irq_state |= req.wdata; ... }"
#   https://github.com/Wren6991/Hazard3/blob/8af992930f71a69b0e06c38734c1094f41a05ca0/test/sim/tb_common/tb_memio.cpp#L107-L112
#
# irq[] is the external interrupt input. With EXTENSION_XH3IRQ = 0 (see README.md) the
# core ORs the whole irq bus into the standard mip.MEIP rather than routing it through
# the nonstandard 512-source controller, so asserting irq[0] is exactly a machine
# external interrupt.
#   Quote: "input wire [NUM_IRQS-1:0] irq,       // -> mip.meip"
#   https://github.com/Wren6991/Hazard3/blob/8af992930f71a69b0e06c38734c1094f41a05ca0/test/sim/tb_common/hdl/tb.v#L55
#   Quote: "end else begin: no_irq_ctrl ... external_irq_pending_r <= |irq;"
#   https://github.com/Wren6991/Hazard3/blob/8af992930f71a69b0e06c38734c1094f41a05ca0/hdl/hazard3_csr.v#L464-L474

#define RVMODEL_SET_MEXT_INT(_R1, _R2)                                        \
    li _R1, H3_IO_BASE                 ;                                      \
    li _R2, 1                          ; /* irq[0] */                         \
    sw _R2, H3_IO_SET_IRQ(_R1)

#define RVMODEL_CLR_MEXT_INT(_R1, _R2)                                        \
    li _R1, H3_IO_BASE                 ;                                      \
    li _R2, 1                          ;                                      \
    sw _R2, H3_IO_CLR_IRQ(_R1)

#define RVMODEL_SET_MSW_INT(_R1, _R2)                                         \
    li _R1, H3_IO_BASE                 ;                                      \
    li _R2, 1                          ; /* soft_irq[0] == hart 0 */          \
    sw _R2, H3_IO_SET_SOFTIRQ(_R1)

#define RVMODEL_CLR_MSW_INT(_R1, _R2)                                         \
    li _R1, H3_IO_BASE                 ;                                      \
    li _R2, 1                          ;                                      \
    sw _R2, H3_IO_CLR_SOFTIRQ(_R1)

##### Supervisor Interrupts #####
# Hazard3 has M and U mode only; S-mode is not implemented, so these can never be
# reached, but ACT requires them to be defined when S_SUPPORTED is set (it is not).
#   Quote: "Debug, Machine and User privilege/execution modes"
#   https://github.com/Wren6991/Hazard3/blob/8af992930f71a69b0e06c38734c1094f41a05ca0/doc/sections/introduction.adoc#L20

#define RVMODEL_SET_SEXT_INT(_R1, _R2)
#define RVMODEL_CLR_SEXT_INT(_R1, _R2)
#define RVMODEL_SET_SSW_INT(_R1, _R2)
#define RVMODEL_CLR_SSW_INT(_R1, _R2)

#endif // _RVMODEL_MACROS_H
