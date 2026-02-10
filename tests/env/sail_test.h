# sail_test.h
# RVMODEL macro definitions for Sail reference model
# Jordan Carlin jcarlin@hmc.edu October 2025
# SPDX-License-Identifier: BSD-3-Clause

#ifndef _COMPLIANCE_MODEL_H
#define _COMPLIANCE_MODEL_H

#define CLINT_BASE_ADDR 0x02000000
#define PLIC_BASE_ADDR 0x0C000000
#define GPIO_BASE_ADDR 0x10060000
#define MTIME           (CLINT_BASE_ADDR + 0xBFF8)
#define MSIP            (CLINT_BASE_ADDR)
#define MTIMECMP        (CLINT_BASE_ADDR + 0x4000)
#define MTIMECMPH       (CLINT_BASE_ADDR + 0x4004)
#define THRESHOLD_0     (PLIC_BASE_ADDR + 0x200000)
#define THRESHOLD_1     (PLIC_BASE_ADDR + 0x201000)
#define INT_PRIORITY_3  (PLIC_BASE_ADDR + 0x00000C)
#define INT_EN_00       (PLIC_BASE_ADDR + 0x002000)
#define INT_EN_10       (PLIC_BASE_ADDR + 0x002080)
#define GPIO_OUTPUT_EN  (GPIO_BASE_ADDR + 0x08)
#define GPIO_OUTPUT_VAL (GPIO_BASE_ADDR + 0x0C)


#define RVMODEL_DATA_SECTION \
        .pushsection .tohost,"aw",@progbits;                \
        .align 8; .global tohost; tohost: .dword 0;         \
        .align 8; .global fromhost; fromhost: .dword 0;     \
        .popsection

##### STARTUP #####

# Perform boot operations. Can be empty.
#define RVMODEL_BOOT

##### TERMINATION #####

# Terminate test with a pass indication.
# When the test is run in simulation, this should end the simulation.
#define RVMODEL_HALT_PASS  \
  li x1, 1                ;\
  la t0, tohost           ;\
  write_tohost_pass:      ;\
    sw x1, 0(t0)          ;\
    sw x0, 4(t0)          ;\
    j write_tohost_pass   ;\

# Terminate test with a fail indication.
# When the test is run in simulation, this should end the simulation.
#define RVMODEL_HALT_FAIL \
  li x1, 3                ;\
  la t0, tohost           ;\
  write_tohost_fail:      ;\
    sw x1, 0(t0)          ;\
    sw x0, 4(t0)          ;\
    j write_tohost_fail   ;\

##### IO #####

# Initialization steps needed prior to writing to the console
# _R1, _R2, and _R3 can be used as temporary registers if needed.
# Do not modify any other registers (or make sure to restore them).
#define RVMODEL_IO_INIT(_R1, _R2, _R3)

# Prints a null-terminated string using a DUT specific mechanism.
# A pointer to the string is passed in _STR_PTR.
# _R1, _R2, and _R3 can be used as temporary registers if needed.
# Do not modify any other registers (or make sure to restore them).
#define RVMODEL_IO_WRITE_STR(_R1, _R2, _R3, _STR_PTR)               \
1:                           ;                       \
  lbu _R1, 0(_STR_PTR)        ;/* Load byte */        \
  beqz _R1, 3f                ;/* Exit if null */     \
2: /* htif_putc */           ;                      \
  la _R2, tohost       ;   \
  sw _R1, 0(_R2)     ; \
  /* device=1 (terminal), cmd=1 (output) */ \
  li _R1, 0x01010000 ;\
  sw _R1, 4(_R2)   ;\
  addi _STR_PTR, _STR_PTR, 1 ;/* Next char */        \
  j 1b                       ;/* Loop */             \
3:

##### Machine Timer #####

# Set the machine timer (mtime) to the value in the register _R1.
# _R2 can be used as a temporary register (e.g. address of mtime).
# For RV32, only write the lower 32 bits of mtime and RVMODEL_SET_MTIMEH for upper 32 bits.
#define RVMODEL_MTIME_ADDR  0x0200BFF8  /* Address of mtime CSR */
#define RVMODEL_SET_MTIME(_R1, _R2)        \
    li   _R2, RVMODEL_MTIME_ADDR        ; /* MTIME address */ \
    SREG _R1, 0(_R2)            ; /* Set MTIME low */

#define RVMODEL_SET_MTIMEH(_R1, _R2)       \
    li   _R2, RVMODEL_MTIME_ADDR        ; /* MTIME address */ \
    SREG _R1, 4(_R2)            ; /* Set MTIME high */


##### Machine Interrupts #####

#define RVMODEL_SET_MEXT_INT

#define RVMODEL_CLR_MEXT_INT

#define RVMODEL_SET_MTIMER_INT \
  la t0, MTIME;                \
  la t1, MTIMECMP;             \
  LREG t2, 0(t0);              \
  SREG t2, 0(t1);              \
  nop;                         \
#ifdef __riscv_xlen \
  #if __riscv_xlen == 32 \
      lw t2, 4(t0);            \
      sw t2, 4(t1);            \
      nop;                     \
  #endif \
#else \
  ERROR: __riscv_xlen not defined; \
#endif

#define RVMODEL_CLR_MTIMER_INT \
  li t0, -1;                    \
  la t2, MTIMECMP;              \
  SREG t0, 0(t2);               \
#ifdef __riscv_xlen \
  #if __riscv_xlen == 32 \
      sw t0, 4(t2);             \
  #endif \
#else \
  ERROR: __riscv_xlen not defined; \
#endif

#define RVMODEL_SET_MTIMER_INT_SOON
la t0, MTIME; \
la t4, MTIMECMP; \
#ifdef __riscv_xlen \
  #if __riscv_xlen == 64 \
      ld t0, 0(t0); \
      addi t0, t0, 0x100; \
      sd t0, 0(t4); \
  #elif __riscv_xlen == 32 \
      lw t1, 0(t0); \
      lw t2, 4(t0); \
      addi t3, t1, 0x100; \
      bgtu t1, t3, 1f; \
      j 2f; \
  1: addi t2, t2, 1; \
  2: sw t3, 0(t4); \
      sw t2, 4(t4); \
  #endif \
#else \
  ERROR: __riscv_xlen not defined; \
#endif

#define RVMODEL_SET_MSW_INT \
  li t1, 1;                 \
  li t2, MSIP;              \
  sw t1, 0(t2);


#define RVMODEL_CLR_MSW_INT \
  li t2, MSIP;              \
  sw zero, 0(t2);

##### Supervisor Interrupts #####

#define RVMODEL_SET_SEXT_INT

#define RVMODEL_CLR_SEXT_INT

#define RVMODEL_SET_STIMER_INT

#define RVMODEL_CLR_STIMER_INT

#define RVMODEL_SET_STIMER_INT_SOON

#define RVMODEL_SET_SSW_INT

#define RVMODEL_CLR_SSW_INT

##### Hypervisor Interrupts #####

#define RVMODEL_SET_VEXT_INT

#define RVMODEL_CLR_VEXT_INT

#define RVMODEL_SET_VTIMER_INT

#define RVMODEL_CLR_VTIMER_INT

#define RVMODEL_SET_VTIMER_INT_SOON

#define RVMODEL_SET_VSW_INT

#define RVMODEL_CLR_VSW_INT

#endif // _COMPLIANCE_MODEL_H
