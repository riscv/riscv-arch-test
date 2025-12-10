#ifndef _COMPLIANCE_MODEL_H
#define _COMPLIANCE_MODEL_H

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

#define RVMODEL_SET_MSW_INT

#define RVMODEL_CLEAR_MSW_INT

#define RVMODEL_CLEAR_MTIMER_INT

#define RVMODEL_CLEAR_MEXT_INT

#endif // _COMPLIANCE_MODEL_H
