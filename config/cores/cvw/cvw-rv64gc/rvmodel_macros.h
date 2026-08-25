#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

#define RVMODEL_DATA_SECTION \
        .pushsection .tohost,"aw",@progbits;                \
        .balign 8; .global tohost; tohost: .dword 0;         \
        .balign 8; .global fromhost; fromhost: .dword 0;     \
        .popsection;

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
# Can be empty or left undefined if no initialization is needed.
#define RVMODEL_IO_INIT(_R1, _R2, _R3) \
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

##### Access Fault #####

#define RVMODEL_ACCESS_FAULT_ADDRESS 0x00000000

##### Interrupt Latency #####

#define RVMODEL_INTERRUPT_LATENCY 10

##### Machine Timer #####

// Wally's mtime advances one tick per core clock, and the code between arming
// mtimecmp and reaching the lower privilege mode (three CLINT stores plus
// RVTEST_GOTO_LOWER_MODE) can take well over 100 cycles on a pipelined core
// with caches.  With a delay of 100 the timer interrupt fires while still in
// M-mode with MIE=1, so the trap records MPP=M instead of MPP=U/S.
#define RVMODEL_TIMER_INT_SOON_DELAY 1000

#define RVMODEL_MTIME_ADDRESS  0x0200BFF8  /* Address of mtime CSR */

#define RVMODEL_MTIMECMP_ADDRESS 0x02004000 /* Address of mtimecmp CSR */

##### Machine Interrupts #####

#define CLINT_BASE_ADDRESS 0x02000000
#define RVMODEL_MSIP_ADDRESS (CLINT_BASE_ADDRESS + 0x0)


#define PLIC_BASE_ADDRESS    0x0c000000
#define PLIC_ENABLE_ADDRESS  0x0c002000
#define PLIC_THRESH_ADDRESS  0x0c200000
#define PLIC_CLAIM_ADDRESS   0x0c200004
#define PLIC_SENABLE_ADDRESS 0x0c002080   /* For S mode */
#define PLIC_STHRESH_ADDRESS 0x0c201000
#define PLIC_SCLAIM_ADDRESS  0x0c201004

#define NS16550_BASE_ADDRESS 0x10000000
#define UART_INT_SRC         10

#define RVMODEL_SET_MEXT_INT(_R1, _R2)          \
  li _R1, 7;                                     \
  li _R2, PLIC_BASE_ADDRESS;                     \
  sw _R1, (4*UART_INT_SRC)(_R2);                 \
  li _R1, (1 << UART_INT_SRC);                   \
  li _R2, PLIC_ENABLE_ADDRESS;                   \
  sw _R1, 0(_R2);                                \
  li _R2, PLIC_THRESH_ADDRESS;                   \
  sw zero, 0(_R2);                               \
  li _R1, 0x02;                                  \
  li _R2, NS16550_BASE_ADDRESS;                  \
  sb _R1, 1(_R2);

#define RVMODEL_CLR_MEXT_INT(_R1, _R2)          \
  li _R2, NS16550_BASE_ADDRESS;                  \
  sb zero, 1(_R2);                               \
  li _R2, PLIC_CLAIM_ADDRESS;                    \
  lw _R1, 0(_R2);                                 \
  sw _R1, 0(_R2);                               \
  li _R2, PLIC_ENABLE_ADDRESS;  /* Since SEXT and MEXT interrupt contexts share the same source, PLIC must be disabled for MEXT context so that it can properly trigger SEXT */\
  sw zero, 0(_R2);

#define RVMODEL_SET_MSW_INT(_R1, _R2) \
  li _R1, 1; \
  li _R2, RVMODEL_MSIP_ADDRESS; \
  sw _R1, 0(_R2);

#define RVMODEL_CLR_MSW_INT(_R1, _R2) \
  li _R2, RVMODEL_MSIP_ADDRESS; \
  sw zero, 0(_R2);

##### Supervisor Interrupts #####

#define CVW_SSIP_ADDRESS (CLINT_BASE_ADDRESS + 0xC000)

#define RVMODEL_SET_SEXT_INT(_R1, _R2)          \
  li _R1, 7;                                     \
  li _R2, PLIC_BASE_ADDRESS;                     \
  sw _R1, (4*UART_INT_SRC)(_R2);                 \
  li _R1, (1 << UART_INT_SRC);                   \
  li _R2, PLIC_SENABLE_ADDRESS;                   \
  sw _R1, 0(_R2);                                \
  li _R2, PLIC_STHRESH_ADDRESS;                   \
  sw zero, 0(_R2);                               \
  li _R1, 0x02;                                  \
  li _R2, NS16550_BASE_ADDRESS;                  \
  sb _R1, 1(_R2);

#define RVMODEL_CLR_SEXT_INT(_R1, _R2)          \
  li _R2, NS16550_BASE_ADDRESS;                  \
  sb zero, 1(_R2);                               \
  li _R2, PLIC_SCLAIM_ADDRESS;                    \
  lw _R1, 0(_R2);                               \
  sw _R1, 0(_R2); \
  li _R2, PLIC_SENABLE_ADDRESS;  /* Disable the S-context UART enable that SET_SEXT turned on, so a later MEXT test does not also raise SEIP via the shared source */\
  sw zero, 0(_R2);

#define RVMODEL_SET_SSW_INT(_R1, _R2) \
  li _R1, 1; \
  li _R2, CVW_SSIP_ADDRESS; \
  sw _R1, 0(_R2);

#define RVMODEL_CLR_SSW_INT(_R1, _R2) \
  li _R2, CVW_SSIP_ADDRESS; \
  sw zero, 0(_R2);

#endif // _RVMODEL_MACROS_H
