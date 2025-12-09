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
  la t0, tohost           ;\
  write_tohost_pass:      ;\
    sw x1, 0(t0)          ;\
    sw x0, 4(t0)          ;\
  self_loop_pass:         ;\
    j self_loop_pass      ;\

#define RVMODEL_HALT_FAIL \
  li x1, 3                ;\
  la t0, tohost           ;\
  write_tohost_fail:      ;\
    sw x1, 0(t0)          ;\
    sw x0, 4(t0)          ;\
  self_loop_fail:         ;\
    j self_loop_fail      ;\

#define RVMODEL_BOOT

# Expects a PC16550-compatible UART.
# Change these addresses to match your memory map
.EQU UART_BASE_ADDR, 0x10000000
.EQU UART_THR, (UART_BASE_ADDR + 0)
.EQU UART_RBR, (UART_BASE_ADDR + 0)
.EQU UART_LCR, (UART_BASE_ADDR + 3)
.EQU UART_LSR, (UART_BASE_ADDR + 5)

#define RVMODEL_IO_INIT    \
  uart_init:                ;\
    li T1, UART_LCR         ; /* Load address of UART LCR */    \
    li T2, 3                ; /* 8-bit characters, 1 stop bit, no parity */ \
    sb T2, 0(T1)            ; \

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


#endif // _COMPLIANCE_MODEL_H
