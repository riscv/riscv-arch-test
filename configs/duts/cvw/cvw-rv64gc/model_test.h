#ifndef _COMPLIANCE_MODEL_H
#define _COMPLIANCE_MODEL_H

# Expects a PC16550-compatible UART.
# Change these addresses to match your memory map
.EQU UART_ENABLED, 1                     # set to 0 to not print
.EQU UART_BASE_ADDR, 0x10000000
.EQU UART_THR, (UART_BASE_ADDR + 0)
.EQU UART_RBR, (UART_BASE_ADDR + 0)
.EQU UART_LCR, (UART_BASE_ADDR + 3)
.EQU UART_LSR, (UART_BASE_ADDR + 5)

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

#define RVMODEL_IO_INIT    \
  uart_init:                ;\
    LI(T1, UART_ENABLED)    ;\
    beqz T1, 1f             ; /* skip if UART is not enabled */ \
    li T1, UART_LCR         ; /* Load address of UART LCR */    \
    li T2, 3                ; /* 8-bit characters, 1 stop bit, no parity */ \
    sb T2, 0(T1)

# Prints a null-terminated string (_STR) using a DUT specific
# mechanism. _R can be used as a temporary register if needed.
# Do not modify any other registers (or make sure to restore them).
#define RVMODEL_IO_WRITE_STR(_R, _STR)               \
  la x30, _STR               ;/* Load string addr */ \
1:                           ;                       \
  lbu a0, 0(x30)             ; /* Load byte */       \
  beqz a0, 2f                ; /* Exit if null */    \
  call uart_putc             ; /* Print char */      \
  addi x30, x30, 1           ; /* Next char */       \
  j 1b                       ; /* Loop */            \
2:

#define RVMODEL_SET_MSW_INT

#define RVMODEL_CLEAR_MSW_INT

#define RVMODEL_CLEAR_MTIMER_INT

#define RVMODEL_CLEAR_MEXT_INT

uart_putc:
    li t1, UART_ENABLED
    beqz t1, 1f             # skip if UART is not enabled
    li t1, UART_LSR
  uart_putc_wait_busy:
    lbu t2, 0(t1)
    andi t2, t2, 0x20 # check line status register bit 5
    beqz t2, uart_putc_wait_busy # wait until Transmit Holding Register Empty is set
  uart_putc_send:
    li t1, UART_THR # transmit character
    sb a0, 0(t1)
  1:
    ret

#endif // _COMPLIANCE_MODEL_H
