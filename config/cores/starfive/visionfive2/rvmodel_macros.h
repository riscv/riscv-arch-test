// SPDX-License-Identifier: Apache-2.0
// rvmodel_macros.h
// DUT-specific macro implementations for the StarFive VisionFive 2 (JH7110 SoC)
//
// Board:     StarFive VisionFive 2
// SoC:       JH7110 (quad-core RV64GC)
// Boot flow: SPL -> OpenSBI (M-mode) -> U-Boot -> [ELF loaded via 'go' command]
//
// IMPORTANT: OpenSBI claims M-mode by the time U-Boot runs.
// Therefore include_priv_tests must be set to false in test_config.yaml.
// All ACT tests run in S-mode or U-mode under OpenSBI supervision.
//
// UART: NS16550-compatible at base address 0x10000000 (UART0 on JH7110)
// DRAM: Starts at 0x40000000 (load ELFs here via U-Boot 'go' command)
// CLINT: At 0x2000000 (managed by OpenSBI; do NOT write directly)
//
// Usage: Load ELF via U-Boot:
//   => tftpboot 0x42000000 <test>.elf
//   => go 0x42000000
//   (PASS/FAIL printed over UART as: RVCP-SUMMARY: TEST PASSED/FAILED)

#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

// ---------------------------------------------------------------------------
// DATA SECTION: tohost/fromhost symbols required by the ACT framework.
// On real hardware these are not polled by a testbench, but must still
// exist as symbols for the ELF to link correctly. PASS/FAIL is instead
// communicated over UART (see RVMODEL_HALT_PASS / RVMODEL_HALT_FAIL below).
// ---------------------------------------------------------------------------
#define RVMODEL_DATA_SECTION                                        \
        .pushsection .tohost,"aw",@progbits;                        \
        .align 8; .global tohost;   tohost:   .dword 0;            \
        .align 8; .global fromhost; fromhost: .dword 0;            \
        .popsection;

// ---------------------------------------------------------------------------
// UART register layout (NS16550 / 8250 compatible)
// JH7110 UART0 base: 0x10000000
// Register width: 8-bit, stride: 1 byte (byte-addressable)
// ---------------------------------------------------------------------------
.EQU VF2_UART_BASE,  0x10000000
.EQU VF2_UART_THR,  (VF2_UART_BASE + 0)   /* Transmit Holding Register */
.EQU VF2_UART_IER,  (VF2_UART_BASE + 1)   /* Interrupt Enable Register */
.EQU VF2_UART_FCR,  (VF2_UART_BASE + 2)   /* FIFO Control Register     */
.EQU VF2_UART_LCR,  (VF2_UART_BASE + 3)   /* Line Control Register     */
.EQU VF2_UART_MCR,  (VF2_UART_BASE + 4)   /* Modem Control Register    */
.EQU VF2_UART_LSR,  (VF2_UART_BASE + 5)   /* Line Status Register      */

// ---------------------------------------------------------------------------
// RVMODEL_BOOT: Called at the very start of rvtest_entry_point.
// OpenSBI has already initialized UART, so we only need to ensure
// the FIFO is enabled and the format is 8N1.
// ---------------------------------------------------------------------------
#define RVMODEL_BOOT                                                \
  vf2_uart_boot:                                                   ;\
    li   t0, VF2_UART_LCR                                          ;\
    li   t1, 0x03          /* 8-bit, 1 stop bit, no parity */      ;\
    sb   t1, 0(t0)                                                  ;\
    li   t0, VF2_UART_FCR                                          ;\
    li   t1, 0x07          /* Enable & clear TX/RX FIFOs */        ;\
    sb   t1, 0(t0)                                                  ;\
    li   t0, VF2_UART_IER                                          ;\
    sb   zero, 0(t0)       /* Disable all UART interrupts */        ;\

// ---------------------------------------------------------------------------
// RVMODEL_IO_INIT: Additional IO initialization (UART already done in BOOT).
// _R1, _R2, _R3 are available as scratch registers.
// ---------------------------------------------------------------------------
#define RVMODEL_IO_INIT(_R1, _R2, _R3)  /* UART initialized in RVMODEL_BOOT */

// ---------------------------------------------------------------------------
// RVMODEL_IO_WRITE_STR: Print null-terminated string over UART.
// Polls LSR bit 5 (THRE - Transmit Holding Register Empty) before each byte.
// _STR_PTR: register holding pointer to string (modified by macro).
// _R1, _R2, _R3: scratch registers.
// ---------------------------------------------------------------------------
#define RVMODEL_IO_WRITE_STR(_R1, _R2, _R3, _STR_PTR)              \
  vf2_uart_str_loop##_STR_PTR:                                      \
    lbu  _R1, 0(_STR_PTR)          /* load next character */       ;\
    beqz _R1, vf2_uart_str_done##_STR_PTR /* stop at null */       ;\
  vf2_uart_wait##_STR_PTR:                                          \
    li   _R2, VF2_UART_LSR                                         ;\
    lbu  _R3, 0(_R2)               /* read LSR */                   ;\
    andi _R3, _R3, 0x20            /* check THRE (bit 5) */         ;\
    beqz _R3, vf2_uart_wait##_STR_PTR /* wait until TX ready */    ;\
    li   _R2, VF2_UART_THR                                         ;\
    sb   _R1, 0(_R2)               /* transmit character */         ;\
    addi _STR_PTR, _STR_PTR, 1    /* advance pointer */             ;\
    j    vf2_uart_str_loop##_STR_PTR                                ;\
  vf2_uart_str_done##_STR_PTR:

// ---------------------------------------------------------------------------
// RVMODEL_HALT_PASS: Signal test PASSED.
// Writes tohost=1 (for any host-side monitor), then spins.
// The RVCP-SUMMARY string is printed by the ACT framework before calling
// rvmodel_halt_pass, so no extra print is needed here.
// ---------------------------------------------------------------------------
#define RVMODEL_HALT_PASS                                           \
    li   x1, 1                     /* tohost pass code = 1 */      ;\
    la   t0, tohost                                                 ;\
  vf2_write_pass:                                                   ;\
    sw   x1, 0(t0)                 /* write to tohost */            ;\
    sw   zero, 4(t0)                                                ;\
  vf2_spin_pass:                                                    ;\
    j    vf2_spin_pass             /* infinite loop */              ;\

// ---------------------------------------------------------------------------
// RVMODEL_HALT_FAIL: Signal test FAILED.
// Writes tohost=3 (fail code), then spins.
// ---------------------------------------------------------------------------
#define RVMODEL_HALT_FAIL                                           \
    li   x1, 3                     /* tohost fail code = 3 */      ;\
    la   t0, tohost                                                 ;\
  vf2_write_fail:                                                   ;\
    sw   x1, 0(t0)                 /* write to tohost */            ;\
    sw   zero, 4(t0)                                                ;\
  vf2_spin_fail:                                                    ;\
    j    vf2_spin_fail             /* infinite loop */              ;\

// ---------------------------------------------------------------------------
// ACCESS FAULT: The JH7110 memory map has unmapped regions at low addresses.
// Address 0x00000000 is not mapped and will trigger a load/store access fault.
// Note: Under OpenSBI, access faults may be handled differently than bare metal.
// Set to "na" if access faults cannot be reliably triggered in your setup.
// ---------------------------------------------------------------------------
#define RVMODEL_ACCESS_FAULT_ADDRESS 0x00000000

// ---------------------------------------------------------------------------
// TIMER/INTERRUPT MACROS
// OpenSBI manages the CLINT on VisionFive 2. Direct CLINT writes from S-mode
// will be intercepted by OpenSBI via SBI ecalls. These macros are left empty
// because include_priv_tests: false excludes all M-mode timer/interrupt tests.
// ---------------------------------------------------------------------------
#define RVMODEL_MTIME_ADDRESS        /* Not directly accessible; managed by OpenSBI */
#define RVMODEL_MTIMECMP_ADDRESS     /* Not directly accessible; managed by OpenSBI */
#define RVMODEL_TIMER_INT_SOON_DELAY 0
#define RVMODEL_INTERRUPT_LATENCY    0

#define RVMODEL_SET_MEXT_INT(_R1, _R2)   /* Not supported: OpenSBI owns M-mode */
#define RVMODEL_CLR_MEXT_INT(_R1, _R2)
#define RVMODEL_SET_MSW_INT(_R1, _R2)    /* Not supported: OpenSBI owns CLINT */
#define RVMODEL_CLR_MSW_INT(_R1, _R2)
#define RVMODEL_SET_SEXT_INT(_R1, _R2)   /* Platform-specific PLIC; not implemented */
#define RVMODEL_CLR_SEXT_INT(_R1, _R2)
#define RVMODEL_SET_SSW_INT(_R1, _R2)    /* Use SBI ecall in future extension */
#define RVMODEL_CLR_SSW_INT(_R1, _R2)

#endif // _RVMODEL_MACROS_H
