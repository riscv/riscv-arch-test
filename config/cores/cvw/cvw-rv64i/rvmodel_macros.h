#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

#define RVMODEL_DATA_SECTION \
        .pushsection .tohost,"aw",@progbits;                \
        .balign 8; .global tohost; tohost: .dword 0;         \
        .balign 8; .global fromhost; fromhost: .dword 0;     \
        .popsection;

// STANDARD_SM_SUPPORTED is deliberately undefined: rv32i and rv64i have no Zicsr and no M-mode CSRs,
// so the tests boot and run without touching any CSR.

##### STARTUP #####

# Perform boot operations. Can be empty or left undefined unless needed for
# DUT-specific behavior such as turning on a memory controller or
# initializing custom state.
//#define RVMODEL_BOOT

// Custom RVMODEL_BOOT_TO_MMODE overrides default RVTEST_BOOT_TO_MMODE
// if defined.  For most DUTs, the default should work and this macro
// should not be defined.  If the DUT has no standard M-mode CSRs, do not
// define STANDARD_SM_SUPPORTED.  If a nonconforming
// M-mode is implemented, define this macro to set up the necessary
// state in a fashion similar to RVTEST_BOOT_TO_MMODE.
//#define RVMODEL_BOOT_TO_MMODE

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

// No UART in this configuration: print through the HTIF console instead.  Each character is
// stored to tohost with device 1, command 1 in bits 63:48, which the testbench prints.  On RV32
// the upper word goes to tohost+4 first and is cleared afterwards, so a later result store to
// the lower word of tohost is not mistaken for a character.
#if __riscv_xlen == 64
#define RVMODEL_IO_WRITE_STR(_R1, _R2, _R3, _STR_PTR) \
1:                            ;                       \
  lbu  _R1, 0(_STR_PTR)       ;/* Load byte */        \
  beqz _R1, 3f                ;/* Exit if null */     \
  la   _R2, tohost            ;                       \
  li   _R3, 0x0101000000000000;/* device 1, cmd 1 */  \
  or   _R1, _R1, _R3          ;                       \
  sd   _R1, 0(_R2)            ;/* putchar */          \
  addi _STR_PTR, _STR_PTR, 1  ;/* Next char */        \
  j    1b                     ;/* Loop */             \
3:
#else
#define RVMODEL_IO_WRITE_STR(_R1, _R2, _R3, _STR_PTR) \
1:                            ;                       \
  lbu  _R1, 0(_STR_PTR)       ;/* Load byte */        \
  beqz _R1, 3f                ;/* Exit if null */     \
  la   _R2, tohost            ;                       \
  li   _R3, 0x01010000        ;/* device 1, cmd 1 */  \
  sw   _R3, 4(_R2)            ;/* upper word first */ \
  sw   _R1, 0(_R2)            ;/* putchar */          \
  sw   zero, 4(_R2)           ;                       \
  addi _STR_PTR, _STR_PTR, 1  ;/* Next char */        \
  j    1b                     ;/* Loop */             \
3:
#endif

##### Access Fault #####

#define RVMODEL_ACCESS_FAULT_ADDRESS 0x00000000

// No CLINT, PLIC or interrupts in this configuration, and no M-mode CSRs to take them, so no interrupt macros.

#endif // _RVMODEL_MACROS_H
