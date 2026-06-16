# rvmodel_macros.h
# RVMODEL macro definitions for OpenHW CV32E20 core
# SPDX-License-Identifier: Apache-2.0

#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

#define RVMODEL_DATA_SECTION

#define STANDARD_SM_SUPPORTED

##### STARTUP #####

# Perform boot operations. Can be empty or left undefined unless needed for
# DUT-specific behavior such as turning on a memory controller or
# initializing custom state.
//#define RVMODEL_BOOT

// Custom RVMODEL_BOOT_TO_MMODE overrides default RVTEST_BOOT_TO_MMODE
// if defined.  For most DUTs, the default should work and this macro
// should not be defined.  If no M-mode or CSRs are implemented, define this
// macro as blank to bypass the boot process.  If a nonconforming
// M-mode is implemented, define this macro to set up the necessary
// state in a fashion similar to RVTEST_BOOT_TO_MMODE.
//#define RVMODEL_BOOT_TO_MMODE

# Address to use for load/store fault tests that should cause an access fault on the DUT.
// This DUT does not generate access faults.  Comment out RVMODEL_ACCESS_FAULT_ADDRESS to prevent testing them.
//#define RVMODEL_ACCESS_FAULT_ADDRESS 0x00000000

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
# Can be empty or left undefined if no initialization is needed.
//#define RVMODEL_IO_INIT(_R1, _R2, _R3)

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

##### MTVEC Alignment #####

##### Interrupt Latency #####

#define RVMODEL_INTERRUPT_LATENCY 10

##### Machine Timer #####
#define RVMODEL_MAX_CYCLES_PER_TIMER_TICK 1

#define RVMODEL_TIMER_INT_SOON_DELAY 100

// CLINT machine timer in mm_ram at Sail's CLINT base (matches sail_macros.h).
#define RVMODEL_MTIME_ADDRESS     0x0200BFF8
#define RVMODEL_MTIMECMP_ADDRESS  0x02004000
##### Machine Interrupts #####

// Drive cv32e20 core irq pins via the cv32e20-dv mm_ram Sail-protocol
// simple_interrupt_generator at 0x15000020 (DUT testbench peripheral).
// Per sail-riscv doc/SimpleInterruptGenerator.md v1.0:
//   base+0: version register (read-only)
//   base+4: platform register (write set/clear)
//     bit 31 = 1 (set) / 0 (clear); bit 3 = MSI, bit 11 = MEI

#define RVMODEL_SET_MEXT_INT(_R1, _R2)                                  \
    li _R1, 0x80000800           ; /* set | MEI (bit 11) */             \
    li _R2, 0x15000024           ; /* simple_interrupt_generator + 4 */ \
    sw _R1, 0(_R2)

#define RVMODEL_CLR_MEXT_INT(_R1, _R2)                                  \
    li _R1, 0x00000800           ; /* clear | MEI (bit 11) */           \
    li _R2, 0x15000024           ;                                      \
    sw _R1, 0(_R2)

#define RVMODEL_SET_MSW_INT(_R1, _R2)                                   \
    li _R1, 0x80000008           ; /* set | MSI (bit 3) */              \
    li _R2, 0x15000024           ;                                      \
    sw _R1, 0(_R2)

#define RVMODEL_CLR_MSW_INT(_R1, _R2)                                   \
    li _R1, 0x00000008           ; /* clear | MSI (bit 3) */            \
    li _R2, 0x15000024           ;                                      \
    sw _R1, 0(_R2)

##### Supervisor Interrupts #####

#define RVMODEL_SET_SEXT_INT(_R1, _R2)

#define RVMODEL_CLR_SEXT_INT(_R1, _R2)

#define RVMODEL_SET_SSW_INT(_R1, _R2)

#define RVMODEL_CLR_SSW_INT(_R1, _R2)

#endif // _RVMODEL_MACROS_H
