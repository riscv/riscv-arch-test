# rvmodel_macros.h
# DUT-specific macro definitions for Qemu
# Jordan Carlin jcarlin@hmc.edu Feb 2026
# SPDX-License-Identifier: BSD-3-Clause

#ifndef _COMPLIANCE_MODEL_H
#define _COMPLIANCE_MODEL_H

#define RVMODEL_DATA_SECTION \
        .pushsection .data,"aw",@progbits;                             \
        .align 3; .global _semihost_exit_pass;                          \
        _semihost_exit_pass: .dword 0x20026; .dword 0;                  \
        .align 3; .global _semihost_exit_fail;                          \
        _semihost_exit_fail: .dword 0x20023; .dword 1;                  \
        .popsection

##### STARTUP #####

# Perform boot operations. Can be empty.
#define RVMODEL_BOOT


##### TERMINATION #####

# QEMU uses semihosting to terminate the simulation.
# Semihosting triggers commands by using a special sequence of three instructions.
# See https://docs.riscv.org/reference/platform-software/semihosting/_attachments/riscv-semihosting.pdf
# for details. Note: QEMU semihosting sequences cannot cross page boundaries.
# The semihosting codes used here are described below. The subsequent link has more details on all semihosting codes.
# On RV64, SYS_EXIT expects a1 = pointer to {reason, subcode} parameter block.
# On RV32, SYS_EXIT expects a1 = reason value directly.
# 0x20026 = ADP_Stopped_ApplicationExit (exit code 0)
# 0x20023 = ADP_Stopped_InternalError (exit code 1)
# https://github.com/ARM-software/abi-aa/blob/main/semihosting/semihosting.rst

#if __riscv_xlen == 64

  # Terminate test with a pass indication.
  # When the test is run in simulation, this should end the simulation.
  #define RVMODEL_HALT_PASS     \
    .option push               ;\
    .option norvc              ;\
    /* load exit code (see above) */ \
    la a1, _semihost_exit_pass ;\
    li a0, 0x18                ;\
    /* align to ensure semihosting instructions don't cross a page boundary */ \
    .balign 16                 ;\
    /* semihosting special sequence */ \
    slli x0, x0, 0x1f          ;\
    ebreak                     ;\
    srai x0, x0, 7             ;\
    .option pop

  # Terminate test with a fail indication.
  # When the test is run in simulation, this should end the simulation.
  #define RVMODEL_HALT_FAIL     \
    .option push               ;\
    .option norvc              ;\
    /* load exit code (see above) */ \
    la a1, _semihost_exit_fail ;\
    li a0, 0x18                ;\
    /* align to ensure semihosting instructions don't cross a page boundary */ \
    .balign 16                 ;\
    /* semihosting special sequence */ \
    slli x0, x0, 0x1f          ;\
    ebreak                     ;\
    srai x0, x0, 7             ;\
    .option pop

#else /* RV32 */

  # Terminate test with a pass indication.
  # When the test is run in simulation, this should end the simulation.
  #define RVMODEL_HALT_PASS     \
    .option push               ;\
    .option norvc              ;\
    /* load exit code (see above) */ \
    li a1, 0x20026             ;\
    li a0, 0x18                ;\
    /* align to ensure semihosting instructions don't cross a page boundary */ \
    .balign 16                 ;\
    /* semihosting special sequence */ \
    slli x0, x0, 0x1f          ;\
    ebreak                     ;\
    srai x0, x0, 7             ;\
    .option pop

  # Terminate test with a fail indication.
  # When the test is run in simulation, this should end the simulation.
  #define RVMODEL_HALT_FAIL     \
    .option push               ;\
    .option norvc              ;\
    /* load exit code (see above) */ \
    li a1, 0x20023             ;\
    li a0, 0x18                ;\
    /* align to ensure semihosting instructions don't cross a page boundary */ \
    .balign 16                 ;\
    /* semihosting special sequence */ \
    slli x0, x0, 0x1f          ;\
    ebreak                     ;\
    srai x0, x0, 7             ;\
    .option pop

#endif

##### IO #####

# Example UART implementation.
# Expects a PC16550-compatible UART.
# Change these addresses to match your memory map
.EQU UART_BASE_ADDR, 0x10000000
.EQU UART_THR, (UART_BASE_ADDR + 0)
.EQU UART_LCR, (UART_BASE_ADDR + 3)
.EQU UART_LSR, (UART_BASE_ADDR + 5)

# Initialization steps needed prior to writing to the console
# _R1, _R2, and _R3 can be used as temporary registers if needed.
# Do not modify any other registers (or make sure to restore them).
#define RVMODEL_IO_INIT(_R1, _R2, _R3)    \
  uart_init:                ;\
    li _R1, UART_LCR         ; /* Load address of UART LCR */    \
    li _R2, 3                ; /* 8-bit characters, 1 stop bit, no parity */ \
    sb _R2, 0(_R1)           ; \

# Prints a null-terminated string using a DUT specific mechanism.
# A pointer to the string is passed in _STR_PTR.
# _R1, _R2, and _R3 can be used as temporary registers if needed.
# Do not modify any other registers (or make sure to restore them).
#define RVMODEL_IO_WRITE_STR(_R1, _R2, _R3, _STR_PTR)               \
1:                           ;                       \
  lbu _R1, 0(_STR_PTR)        ;/* Load byte */        \
  beqz _R1, 3f                ;/* Exit if null */     \
2: /* uart_putc */           ;                      \
  li _R2, UART_LSR ;\
  4: /* uart_putc_wait_busy */ \
    lbu _R3, 0(_R2) ;\
    andi _R3, _R3, 0x20 ;/* check line status register bit 5 */ \
    beqz _R3, 4b ;/* wait until Transmit Holding Register Empty is set */ \
  /* uart_putc_send */ \
    li _R2, UART_THR ; /* transmit character */ \
    sb _R1, 0(_R2) ;\
  addi _STR_PTR, _STR_PTR, 1 ;/* Next char */        \
  j 1b                       ;/* Loop */             \
3:

#define RVMODEL_INTERRUPT_LATENCY 10

#define RVMODEL_TIMER_INT_SOON_DELAY 100

##### Access Fault #####

#define RVMODEL_ACCESS_FAULT_ADDRESS 0x00000000

##### Machine Timer #####

#define RVMODEL_MTIME_ADDRESS  0x0200BFF8  /* Address of mtime CSR */

#define RVMODEL_MTIMECMP_ADDRESS 0x02004000 /* Address of mtimecmp CSR */

##### Machine Interrupts #####

#define QEMU_CLINT_BASE 0x02000000
#define QEMU_MSIP_ADDRESS (QEMU_CLINT_BASE + 0x0)

#define RVMODEL_SET_MEXT_INT(_R1, _R2)

#define RVMODEL_CLR_MEXT_INT(_R1, _R2)

#define RVMODEL_SET_MSW_INT(_R1, _R2) \
  li _R1, 1; \
  li _R2, QEMU_MSIP_ADDRESS; \
  sw _R1, 0(_R2);

#define RVMODEL_CLR_MSW_INT(_R1, _R2) \
  li _R2, QEMU_MSIP_ADDRESS; \
  sw zero, 0(_R2);

##### Supervisor Interrupts #####

#define QEMU_SSIP_ADDRESS (QEMU_CLINT_BASE + 0xC000)

#define RVMODEL_SET_SEXT_INT(_R1, _R2)

#define RVMODEL_CLR_SEXT_INT(_R1, _R2)

#define RVMODEL_SET_SSW_INT(_R1, _R2) \
  li _R1, 1; \
  li _R2, QEMU_SSIP_ADDRESS; \
  sw _R1, 0(_R2);

#define RVMODEL_CLR_SSW_INT(_R1, _R2) \
  li _R2, QEMU_SSIP_ADDRESS; \
  sw zero, 0(_R2);

#endif // _COMPLIANCE_MODEL_H
