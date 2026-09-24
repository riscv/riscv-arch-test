# rvmodel_macros.h
# RVMODEL macro definitions for the YosysHQ PicoRV32 core (picorv32_axi, RV32IMC)
# SPDX-License-Identifier: Apache-2.0

#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

#define RVMODEL_DATA_SECTION

// STANDARD_SM_SUPPORTED is deliberately NOT defined.
// PicoRV32 implements no CSR instructions and no privileged state: there is no
// csrrw/csrrs/csrrc path and no mtvec/mepc/mcause/mtval/mscratch/mstatus anywhere
// in picorv32.v. Quote (README.md, "Custom Instructions for IRQ Handling"):
//   "The IRQ handling features in PicoRV32 do not follow the RISC-V Privileged
//    ISA specification. Instead PicoRV32 implements a very simple custom
//    interrupt handling scheme."
// https://github.com/YosysHQ/picorv32/blob/ef203c2b0a3fb793280f5114941416c425c5b461/README.md#custom-instructions-for-irq-handling

##### STARTUP #####

# Perform boot operations. Can be empty or left undefined unless needed for
# DUT-specific behavior such as turning on a memory controller or
# initializing custom state.
//#define RVMODEL_BOOT

// Custom RVMODEL_BOOT_TO_MMODE overrides default RVTEST_BOOT_TO_MMODE
// if defined.  For most DUTs, the default should work and this macro
// should not be defined.  If no standard M-mode CSRs are implemented, leave
// STANDARD_SM_SUPPORTED undefined instead.  If a nonconforming
// M-mode is implemented, define this macro to set up the necessary
// state in a fashion similar to RVTEST_BOOT_TO_MMODE.
//
// PicoRV32 implements no CSRs, so STANDARD_SM_SUPPORTED is left undefined and the
// default boot code, which touches CSRs only for a standard M-mode, does nothing.
//#define RVMODEL_BOOT_TO_MMODE

# Address to use for load/store fault tests that should cause an access fault on the DUT.
// PicoRV32 generates no access faults: the AXI testbench answers every in-range
// address and $finishes on an out-of-range one. Leave undefined so they are not tested.
//#define RVMODEL_ACCESS_FAULT_ADDRESS 0x00000000

##### TERMINATION #####

# Terminate test with a pass indication.
# When the test is run in simulation, this should end the simulation.
//
// The picorv32 testbench latches `tests_passed` when the word 123456789
// (0x075BCD15) is written to 0x2000_0000, and only ends the simulation when the
// core asserts `trap`, so the pass path must do both.
// https://github.com/YosysHQ/picorv32/blob/ef203c2b0a3fb793280f5114941416c425c5b461/testbench.v#L418-L420
// With ENABLE_IRQ=0, `ebreak` drives `trap` permanently (a halt, not a
// recoverable exception), which is the natural halt trigger.
// https://github.com/YosysHQ/picorv32/blob/ef203c2b0a3fb793280f5114941416c425c5b461/picorv32.v#L1605-L1611
#define RVMODEL_HALT_PASS   \
  li x1, 123456789         ;\
  li t0, 0x20000000        ;\
  write_halt_pass:         ;\
    sw x1, 0(t0)           ;\
  self_loop_pass:          ;\
    ebreak                 ;\
    j self_loop_pass       ;\

# Terminate test with a fail indication.
# When the test is run in simulation, this should end the simulation.
// `tests_passed` is left clear, so the runner reports a failure.
#define RVMODEL_HALT_FAIL   \
  self_loop_fail:          ;\
    ebreak                 ;\
    j self_loop_fail       ;\

##### IO #####

# Initialization steps needed prior to writing to the console
# _R1, _R2, and _R3 can be used as temporary registers if needed.
# Do not modify any other registers (or make sure to restore them).
# Can be empty or left undefined if no initialization is needed.
// The picorv32 console is a bare write port with no status register.
//#define RVMODEL_IO_INIT(_R1, _R2, _R3)

# Prints a null-terminated string using a DUT specific mechanism.
# A pointer to the string is passed in _STR_PTR.
# _R1, _R2, and _R3 can be used as temporary registers if needed.
# Do not modify any other registers (or make sure to restore them).
// A word write to 0x1000_0000 emits one character.
// https://github.com/YosysHQ/picorv32/blob/ef203c2b0a3fb793280f5114941416c425c5b461/testbench.v#L398-L417
#define RVMODEL_IO_WRITE_STR(_R1, _R2, _R3, _STR_PTR) \
1:                           ;                        \
  lbu  _R1, 0(_STR_PTR)      ; /* Load byte */        \
  beqz _R1, 3f               ; /* Exit if null */     \
2:                           ;                        \
  li   _R2, 0x10000000       ; /* console */          \
  sw   _R1, 0(_R2)           ;                        \
  addi _STR_PTR, _STR_PTR, 1 ; /* Next char */        \
  j 1b                       ; /* Loop */             \
3:

##### Interrupt Latency #####

// PicoRV32 takes no standard interrupts at all, and is built here with
// ENABLE_IRQ=0, so nothing in the interrupt family is reachable. These are
// required by tests/env/check_defines.h even when unused.
#define RVMODEL_INTERRUPT_LATENCY 10

##### Machine Timer #####

// No mtime and no mtimecmp exist anywhere in the picorv32 testbench, so
// RVMODEL_MTIME_ADDRESS is left undefined and timer interrupts are not tested.
#define RVMODEL_MAX_CYCLES_PER_TIMER_TICK 1
#define RVMODEL_TIMER_INT_SOON_DELAY 10000

##### Machine Interrupts #####

// The testbench's only interrupt stimulus is two free-running cycle counters
// driving irq[4] and irq[5]; there is no software-controllable interrupt path.
// https://github.com/YosysHQ/picorv32/blob/ef203c2b0a3fb793280f5114941416c425c5b461/testbench.v#L79-L87
#define RVMODEL_SET_MEXT_INT(_R1, _R2)
#define RVMODEL_CLR_MEXT_INT(_R1, _R2)
#define RVMODEL_SET_MSW_INT(_R1, _R2)
#define RVMODEL_CLR_MSW_INT(_R1, _R2)

#endif // _RVMODEL_MACROS_H
