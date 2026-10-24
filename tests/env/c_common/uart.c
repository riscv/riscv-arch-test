/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#include "uart.h"

/* ===== UART driver type selection =====
 * Platforms define PLATFORM_UART_TYPE in their platform_config.h.
 * Default is NS16550 (full initialization).
 *   - UART_TYPE_NS16550 (0): Full NS16550 init (QEMU, FPGA, real HW)
 *   - UART_TYPE_SAIL    (1): HTIF-based output for Sail RISC-V model */
#define UART_TYPE_NS16550   0
#define UART_TYPE_SAIL      1

#ifndef PLATFORM_UART_TYPE
#define PLATFORM_UART_TYPE  UART_TYPE_NS16550
#endif

/* ===================================================================== */
#if PLATFORM_UART_TYPE == UART_TYPE_SAIL
/* ===== SAIL HTIF-based UART driver =====
 *
 * SAIL does not have an MMIO UART device. The address 0x10000000 is
 * unmapped and any access triggers a load-access-fault, causing an
 * infinite trap loop.
 *
 * Instead, SAIL uses HTIF (Host-Target Interface) for terminal output.
 * Characters are sent by writing to the 'tohost' symbol with encoding:
 *   tohost = (device << 56) | (cmd << 48) | payload
 * where device=1 (console), cmd=1 (write char), payload=character.
 *
 * The tohost/fromhost symbols are defined in the .tohost section
 * (provided by rvmodel_macros.h for Sail).
 */

/* Use __UINT64_TYPE__ to match the declaration in rvmodel_macros.h
 * (which is pre-included before types.h). On RV64 this is 'unsigned long',
 * while types.h defines uint64_t as 'unsigned long long'. */
extern volatile __UINT64_TYPE__ tohost;
extern volatile __UINT64_TYPE__ fromhost;

#define HTIF_DEVICE_CONSOLE  1
#define HTIF_CMD_WRITE       1
#define HTIF_TOHOST(dev, cmd, payload) \
    (((__UINT64_TYPE__)(dev) << 56) | ((__UINT64_TYPE__)(cmd) << 48) | (__UINT64_TYPE__)(payload))

void uart_init(void) {
    /* HTIF requires no initialization */
}

void uart_putc(char c) {
#ifdef UART_SILENT_MODE
    /* Skip all HTIF console writes in silent mode.
     * Test termination is unaffected: RVMODEL_HALT_PASS/FAIL write
     * tohost directly from assembly, so pass/fail is still reported
     * through the simulator exit code. */
    (void)c;
    return;
#endif
    /* Wait until previous HTIF command is consumed */
    while (tohost != 0)
        ;
    tohost = HTIF_TOHOST(HTIF_DEVICE_CONSOLE, HTIF_CMD_WRITE, (uint8_t)c);
}

/* ===================================================================== */
#else /* UART_TYPE_NS16550 — MMIO NS16550 UART driver */
/* ===================================================================== */

/* ===== NS16550 UART Register Offsets ===== */
#define UART_THR    0   /* Transmitter Holding Register (write) */
#define UART_RBR    0   /* Receiver Buffer Register (read) */
#define UART_IER    1   /* Interrupt Enable Register */
#define UART_FCR    2   /* FIFO Control Register (write) */
#define UART_LCR    3   /* Line Control Register */
#define UART_MCR    4   /* Modem Control Register */
#define UART_LSR    5   /* Line Status Register */
#define UART_DLL    0   /* Divisor Latch Low (when DLAB=1) */
#define UART_DLM    1   /* Divisor Latch High (when DLAB=1) */

#define UART_LSR_TX_EMPTY       (1 << 5)  /* THR empty */
#define UART_LSR_TX_BOTH_EMPTY  (1 << 6)  /* THR + shift register both empty */
#define UART_LCR_DLAB       (1 << 7)
#define UART_LCR_8BIT       0x03
#define UART_FCR_ENABLE     0x01
#define UART_FCR_CLEAR      0x06  /* Clear RX + TX FIFOs */
#define UART_MCR_DTR_RTS    0x03  /* Data Terminal Ready + Request To Send */

/* Register spacing: most 16550-compatible UARTs use byte spacing (shift=0),
 * but some (e.g. snps,dw-apb-uart with reg-shift=<2>) use wider spacing.
 * The effective byte offset for register N is: N << PLATFORM_UART_REG_SHIFT. */
#ifndef PLATFORM_UART_REG_SHIFT
#define PLATFORM_UART_REG_SHIFT 0
#endif

#ifndef PLATFORM_UART_IO_WIDTH
#define PLATFORM_UART_IO_WIDTH 1
#endif

/* 32-bit I/O width (reg-io-width = <4>): registers must be accessed as
 * 32-bit words. Common on AXI/APB-mapped UARTs. */
#if PLATFORM_UART_IO_WIDTH >= 4
static uintptr_t uart_base = PLATFORM_UART0_BASE;

static inline void uart_reg_write(unsigned int reg, uint8_t val) {
    volatile uint32_t *addr = (volatile uint32_t *)(uart_base + (reg << PLATFORM_UART_REG_SHIFT));
    *addr = (uint32_t)val;
}

static inline uint8_t uart_reg_read(unsigned int reg) {
    volatile const uint32_t *addr = (volatile const uint32_t *)(uart_base + (reg << PLATFORM_UART_REG_SHIFT));
    return (uint8_t)*addr;
}
#else
static volatile uint8_t *uart_base = (volatile uint8_t *)PLATFORM_UART0_BASE;

static inline void uart_reg_write(unsigned int reg, uint8_t val) {
    uart_base[reg << PLATFORM_UART_REG_SHIFT] = val;
}

static inline uint8_t uart_reg_read(unsigned int reg) {
    return uart_base[reg << PLATFORM_UART_REG_SHIFT];
}
#endif

void uart_init(void)
{
#ifdef UART_SILENT_MODE
    /* Skip all UART hardware init in silent mode.
     * Output is captured in the memory buffer only. */
    return;
#endif

    /* Full NS16550 initialization (QEMU, FPGA, real hardware).
     * Sequence matches the DesignWare APB UART (snps,dw-apb-uart)
     * recovery procedure: disable IRQ → baud → format → modem →
     * FIFO reset → status clear. */

    /* 1. Disable interrupts */
    uart_reg_write(UART_IER, 0x00);

    /* 2. Set baud rate: enable DLAB, set divisor */
    uart_reg_write(UART_LCR, UART_LCR_DLAB);
#if defined(UART_DLL_VALUE) && defined(UART_DLM_VALUE)
    uart_reg_write(UART_DLL, UART_DLL_VALUE);
    uart_reg_write(UART_DLM, UART_DLM_VALUE);
#else
    uart_reg_write(UART_DLL, 0x03);  /* 38400 baud at 1.8432 MHz */
    uart_reg_write(UART_DLM, 0x00);
#endif

    /* 3. 8 data bits, no parity, 1 stop bit (clears DLAB) */
    uart_reg_write(UART_LCR, UART_LCR_8BIT);

    /* 4. Assert DTR and RTS modem control lines.
     *    Required for TX path on DesignWare APB UART, especially
     *    after taking over from Linux where a system reset may
     *    deassert these lines. */
    uart_reg_write(UART_MCR, UART_MCR_DTR_RTS);

    /* 5. Enable FIFO and clear both RX and TX FIFOs.
     *    Clearing is essential when taking over from a previous
     *    owner (e.g. Linux after system reset), where residual
     *    FIFO state can cause LSR.TEMT (bit 6) to stay low. */
    uart_reg_write(UART_FCR, UART_FCR_ENABLE | UART_FCR_CLEAR);

    /* 6. Drain any stale data from RX FIFO */
    while (uart_reg_read(UART_LSR) & 0x01)
        (void)uart_reg_read(UART_RBR);

    /* 7. Final status clear: read IIR + LSR to ack any pending
     *    interrupt and clear line-status flags. */
    (void)uart_reg_read(UART_FCR);  /* read IIR (same offset as FCR) */
    (void)uart_reg_read(UART_LSR);
}

#ifdef UART_OUTPUT_BUFFER_SIZE
static volatile char uart_output_buf[UART_OUTPUT_BUFFER_SIZE];
static volatile unsigned int uart_output_pos = 0;
#endif

void uart_putc(char c) {
#ifdef UART_OUTPUT_BUFFER_SIZE
    /* Always write to memory buffer for GDB reading.
     * Ensures output is captured even when UART hardware
     * cannot transmit (e.g., baud clock not running). */
    if (uart_output_pos < UART_OUTPUT_BUFFER_SIZE) {
        uart_output_buf[uart_output_pos++] = c;
    }
#endif

#ifdef UART_SILENT_MODE
    /* Skip all UART hardware access in silent mode.
     * Output is captured in the memory buffer for GDB reading. */
    return;
#endif

    /* Wait until THR is empty.
     * On platforms with UART_TX_TIMEOUT_CYCLES defined, use THRE (bit 5)
     * with a timeout to avoid hanging when the baud clock is unreliable.
     * Otherwise, use TEMT (bit 6) for strict shift-register-empty check. */
#ifdef UART_TX_TIMEOUT_CYCLES
    {
        int timeout = UART_TX_TIMEOUT_CYCLES;
        while ((uart_reg_read(UART_LSR) & UART_LSR_TX_EMPTY) == 0 && timeout-- > 0)
            ;
    }
#else
    while ((uart_reg_read(UART_LSR) & UART_LSR_TX_BOTH_EMPTY) == 0)
        ;
#endif
    uart_reg_write(UART_THR, (uint8_t)c);
}

#endif /* PLATFORM_UART_TYPE */

void uart_puts(const char *s) {
    while (*s) {
        if (*s == '\n')
            uart_putc('\r');
        uart_putc(*s++);
    }
}

/* ===== Minimal printf implementation ===== */

/* Variable argument list support (bare-metal) */
typedef __builtin_va_list va_list;
#define va_start(ap, last) __builtin_va_start(ap, last)
#define va_end(ap)         __builtin_va_end(ap)
#define va_arg(ap, type)   __builtin_va_arg(ap, type)

static void print_dec(long val) {
    char buf[24];
    int i = 0;
    int neg = 0;
    unsigned long uval;

    if (val < 0) {
        neg = 1;
        uval = (unsigned long)(-val);
    } else {
        uval = (unsigned long)val;
    }

    if (uval == 0) {
        uart_putc('0');
        return;
    }

    while (uval > 0) {
        buf[i++] = '0' + (uval % 10);
        uval /= 10;
    }

    if (neg)
        uart_putc('-');

    while (i > 0)
        uart_putc(buf[--i]);
}

static void print_unsigned(unsigned long val) {
    char buf[24];
    int i = 0;

    if (val == 0) {
        uart_putc('0');
        return;
    }

    while (val > 0) {
        buf[i++] = '0' + (val % 10);
        val /= 10;
    }

    while (i > 0)
        uart_putc(buf[--i]);
}

static void print_hex(unsigned long val, int width) {
    static const char hex_chars[] = "0123456789abcdef";
    char buf[17];
    int i = 0;

    if (val == 0 && width <= 0) {
        uart_putc('0');
        return;
    }

    while (val > 0 || i < width) {
        buf[i++] = hex_chars[val & 0xf];
        val >>= 4;
        if (i >= 16) break;
    }

    while (i > 0)
        uart_putc(buf[--i]);
}

void printf(const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);

    while (*fmt) {
        if (*fmt != '%') {
            if (*fmt == '\n')
                uart_putc('\r');
            uart_putc(*fmt++);
            continue;
        }

        fmt++; /* skip '%' */

        /* Parse width for zero-padded hex (e.g., %08x) */
        int width = 0;
        int zero_pad = 0;
        if (*fmt == '0') {
            zero_pad = 1;
            fmt++;
        }
        while (*fmt >= '0' && *fmt <= '9') {
            width = width * 10 + (*fmt - '0');
            fmt++;
        }

        /* Handle 'l' and 'll' length modifiers */
        int long_count = 0;
        while (*fmt == 'l') {
            long_count++;
            fmt++;
        }

        switch (*fmt) {
        case 'd': {
            long val;
            if (long_count >= 1)
                val = va_arg(ap, long);
            else
                val = va_arg(ap, int);
            print_dec(val);
            break;
        }
        case 'u': {
            unsigned long val;
            if (long_count >= 1)
                val = va_arg(ap, unsigned long);
            else
                val = va_arg(ap, unsigned int);
            print_unsigned(val);
            break;
        }
        case 'x':
        case 'X': {
            unsigned long val;
            if (long_count >= 1)
                val = va_arg(ap, unsigned long);
            else
                val = va_arg(ap, unsigned int);
            if (zero_pad && width > 0)
                print_hex(val, width);
            else
                print_hex(val, 0);
            break;
        }
        case 'p': {
            unsigned long val = (unsigned long)(uintptr_t)va_arg(ap, void *);
            uart_puts("0x");
            print_hex(val, sizeof(void *) * 2);
            break;
        }
        case 's': {
            const char *s = va_arg(ap, const char *);
            if (s == NULL) s = "(null)";
            uart_puts(s);
            break;
        }
        case 'c': {
            char c = (char)va_arg(ap, int);
            uart_putc(c);
            break;
        }
        case '%':
            uart_putc('%');
            break;
        default:
            uart_putc('%');
            uart_putc(*fmt);
            break;
        }
        fmt++;
    }

    va_end(ap);
}
