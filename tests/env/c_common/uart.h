/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef COMMON_UART_H
#define COMMON_UART_H

#include "types.h"

/* Initialize UART hardware */
void uart_init(void);

/* Output a single character */
void uart_putc(char c);

/* Output a null-terminated string */
void uart_puts(const char *s);

/* Minimal printf implementation */
void printf(const char *fmt, ...);

#endif /* COMMON_UART_H */
