# rvmodel_macros.h
# RVMODEL macro definitions for CV32E40X core
# SPDX-License-Identifier: Apache-2.0

#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

#define RVMODEL_DATA_SECTION

#define STANDARD_SM_SUPPORTED

##### STARTUP #####
//#define RVMODEL_BOOT \

// Custom RVMODEL_BOOT_TO_MMODE overrides default RVTEST_BOOT_TO_MMODE
// if defined.  For most DUTs, the default should work and this macro
// should not be defined.  If no M-mode or CSRs are implemented, define this
// macro as blank to bypass the boot process.  If a nonconforming
// M-mode is implemented, define this macro to set up the necessary
// state in a fashion similar to RVTEST_BOOT_TO_MMODE.
//#define RVMODEL_BOOT_TO_MMODE

# Address to use for load/store fault tests that should cause an access fault on the DUT.
// CV32E40X raises access fault only for misaligned accesses in I/O regions (PMA controlled).
// With PMA_NUM_REGIONS=0, no explicit I/O regions are defined so access faults may not be
// reproducible. Comment out RVMODEL_ACCESS_FAULT_ADDRESS to prevent testing them.
//#define RVMODEL_ACCESS_FAULT_ADDRESS 0x00000000

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

##### Interrupt Latency #####

#define RVMODEL_INTERRUPT_LATENCY 10
// CV32E40X mtvec: BASE[31:7] WARL (writable), BASE[6:2] WARL(0x0) hardwired 0.
// User Manual csr-mtvec: "always aligned to 128 bytes." RTL CSR_BASIC_MTVEC_MASK=0xFFFFFF81 (bit 7 writable).
#define RVMODEL_MTVEC_ALIGN 7

##### Machine Timer #####
#define RVMODEL_MAX_CYCLES_PER_TIMER_TICK 1

#define RVMODEL_TIMER_INT_SOON_DELAY 100
/*
 * NOTE: CV32E40X has a time CSR (shadow of time_i input port).
 * MTIME and MTIMECMP are provided by the CLINT peripheral at 0x02000000.
 * Define the addresses below when the testbench wires up the CLINT.
 */
//#define RVMODEL_MTIME_ADDRESS    0x02004000
//#define RVMODEL_MTIMECMP_ADDRESS 0x02004008

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

#endif // _RVMODEL_MACROS_H
