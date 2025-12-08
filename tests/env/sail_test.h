# sail_test.h
# Trickbox macro definitions for Sail reference model
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
        .popsection;

#define RVMODEL_HALT_PASS  \
  li x1, 1                ;\
  write_tohost:           ;\
    sw x1, tohost, t0     ;\
    j write_tohost        ;\

#define RVMODEL_HALT_FAIL \
  li x1, 3                ;\
  write_tohost_fail:      ;\
    sw x1, tohost, t0     ;\
    j write_tohost_fail   ;\

#define RVMODEL_BOOT

#define RVMODEL_IO_INIT

# Prints a null-terminated string (_STR) using a DUT specific
# mechanism. _R can be used as a temporary register if needed.
# Do not modify any other registers (or make sure to restore them).
#define RVMODEL_IO_WRITE_STR(_R, _STR)               \
  la x30, _STR                ;/* Load string addr */ \
1:                           ;\
  lbu a0, 0(x30)              ;/* Load byte */        \
  beqz a0, 2f                ;/* Exit if null */     \
  call htif_putc             ;/* Print char */       \
  addi x30, x30, 1             ;/* Next char */        \
  j 1b                       ;/* Loop */             \
2:


#define RVMODEL_SET_MSW_INT       \
 li t1, 1;                         \
 li t2, 0x2000000;                 \
 sw t1, 0(t2);


#define RVMODEL_CLR_MSW_INT     \
 li t2, 0x2000000;                 \
 sw x0, 0(t2);

#define RVMODEL_CLR_MTIMER_INT \
li t0, -1; \
la t2, MTIMECMP; \
SREG t0, 0(t2); \
#ifdef __riscv_xlen \
    #if __riscv_xlen == 32 \
        sw t0, 4(t2); \
    #endif \
#else \
    ERROR: __riscv_xlen not defined; \
#endif


#define RVMODEL_MCLR_SSW_INT \
csrrci t6, mip, 2;


#define RVMODEL_SCLR_SSW_INT \
csrrci t6, sip, 2;


#define RVMODEL_MCLR_STIMER_INT \
li t0, 32; \
csrrc t6, mip, t0;


#define RVMODEL_CLR_SEXT_INT \
la t0, THRESHOLD_0; \
li t2, 7; \
sw t2, 0(t0); \
la t0, THRESHOLD_1; \
li t2, 7; \
sw t2, 0(t0); \
la t0, INT_PRIORITY_3; \
sw zero, 0(t0); \
la t0, INT_EN_00; \
sw zero, 0(t0); \
la t0, GPIO_BASE_ADDR; \
sw zero, 0x18(t0); \
sw zero, 0x20(t0); \
sw zero, 0x28(t0); \
sw zero, 0x30(t0);

#define RVMODEL_CLR_MSIP \
la t0, CLINT_BASE_ADDR; \
SREG zero, 0(t0);

#define RVMODEL_CLR_MEXT_INT \
la t0, THRESHOLD_0; \
li t2, 7; \
sw t2, 0(t0); \
la t0, THRESHOLD_1; \
li t2, 7; \
sw t2, 0(t0); \
la t0, INT_PRIORITY_3; \
sw zero, 0(t0); \
la t0, INT_EN_00; \
sw zero, 0(t0); \
la t0, GPIO_BASE_ADDR; \
sw zero, 0x18(t0); \
sw zero, 0x20(t0); \
sw zero, 0x28(t0); \
sw zero, 0x30(t0);

#define RVMODEL_CAUSE_MTIMER_INT_NOW \
la t0, MTIME; \
la t1, MTIMECMP; \
LREG t2, 0(t0); \
SREG t2, 0(t1); \
nop; \
#ifdef __riscv_xlen \
    #if __riscv_xlen == 32 \
        lw t2, 4(t0); \
        sw t2, 4(t1); \
        nop; \
    #endif \
#else \
    ERROR: __riscv_xlen not defined; \
#endif

#define RVMODEL_CAUSE_MTIMER_INT_SOON \
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


#define RVMODEL_CAUSE_MEXT_INT \
la t0, THRESHOLD_0; \
sw zero, 0(t0); /* set M-mode threshold low */ \
la t0, THRESHOLD_1; \
li t1, 7; \
sw t1, 0(t0); \
la t0, INT_PRIORITY_3; \
li t1, 1; \
sw t1, 0(t0); \
la t0, GPIO_BASE_ADDR; \
li t1, 1; \
sw t1, 0x08(t0); /* enable output */ \
sw t1, 0x04(t0); /* enable input */ \
sw zero, 0x18(t0); \
sw zero, 0x20(t0); \
sw zero, 0x28(t0); \
sw zero, 0x30(t0); \
la t0, INT_EN_00; \
li t1, 0b1000; \
sw t1, 0(t0); \
la t0, GPIO_BASE_ADDR; \
li t1, 1; \
sw t1, 0x28(t0); /* enable high interrupt */ \
sw t1, 0x0C(t0); /* write high -> trigger */ \
nop; \
nop; \
nop;
  
#define RVMODEL_CAUSE_SEXT_INT \
la t0, THRESHOLD_0; \
li t1, 7; \
sw t1, 0(t0); \
la t0, THRESHOLD_1; \
sw zero, 0(t0); \
la t0, INT_PRIORITY_3; \
li t1, 1; \
sw t1, 0(t0); \
la t0, GPIO_BASE_ADDR; \
li t1, 1; \
sw t1, 0x08(t0); \
sw t1, 0x04(t0); \
sw zero, 0x18(t0); \
sw zero, 0x20(t0); \
sw zero, 0x28(t0); \
sw zero, 0x30(t0); \
la t0, INT_EN_10; \
li t1, 0b1000; \
sw t1, 0(t0); \
la t0, GPIO_BASE_ADDR; \
li t1, 1; \
sw t1, 0x28(t0); \
sw t1, 0x0C(t0); \
nop; \
nop; \
nop;

htif_putc:
    la x31, tohost
    sw a0, 0(x31)
    // device=1 (terminal), cmd=1 (output)
    li a0, 0x01010000
    sw a0, 4(x31)
    ret

#endif // _COMPLIANCE_MODEL_H
