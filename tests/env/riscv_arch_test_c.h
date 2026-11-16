// riscv_arch_test_c.h
// Minimal ACT runtime API for C tests
// Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
// SPDX-License-Identifier: Apache-2.0

#ifndef RISCV_ARCH_TEST_C_H
#define RISCV_ARCH_TEST_C_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "encoding.h"
#include "tsbi.h"

// Printing functions. These use RVMODEL_IO_WRITE_STR.
int putchar(int ch);
int puts(const char *s);
int printf(const char *fmt, ...);

// Test termination functions. These use the RVMODEL_HALT_PASS and RVMODEL_HALT_FAIL mechanisms.
// The termination functions automatically print the RVCP-SUMMARY message.
void rvtest_pass(void) __attribute__((noreturn));
void rvtest_fail(void) __attribute__((noreturn));
void print_error(const char *fmt, ...) __attribute__((noreturn)); // Print an error message and then exit with a failure.

// T-SBI call. op is a T-SBI operation code from tsbi.h. arg1 and arg2 go in a1 and a2.
// Returns the value that T-SBI puts in a0.
// Example: tsbi_call(TSBI_CSR_READ(CSR_MHARTID), 0, 0) reads mhartid.
// Only CSRs in the T-SBI CSR table are supported.
// Use the tsbi_goto_* functions for privilege-mode switches, not tsbi_call.
unsigned long tsbi_call(unsigned int op, unsigned long arg1, unsigned long arg2);

// CSR accesses. csr is a CSR number such as CSR_MSTATUS from encoding.h.
static inline unsigned long tsbi_csr_read(unsigned int csr) { return tsbi_call(TSBI_CSR_READ(csr), 0, 0); }
static inline void tsbi_csr_write(unsigned int csr, unsigned long val) { (void)tsbi_call(TSBI_CSR_WRITE(csr), val, 0); }
static inline void tsbi_csr_set(unsigned int csr, unsigned long bits) { (void)tsbi_call(TSBI_CSR_SET(csr), bits, 0); }
static inline void tsbi_csr_clear(unsigned int csr, unsigned long bits) { (void)tsbi_call(TSBI_CSR_CLEAR(csr), bits, 0); }

// Privilege-mode switches. Each returns to the caller in the new mode.
void tsbi_goto_mmode(void);
void tsbi_goto_smode(void);
void tsbi_goto_umode(void);
void tsbi_goto_vsmode(void);
void tsbi_goto_vumode(void);

// sfence.vma x0, x0. Requires S.
static inline void tsbi_sfence_vma(void) { (void)tsbi_call(TSBI_SFENCE_VMA, 0, 0); }

// Physical-memory accesses. These must not fault.
static inline uint32_t tsbi_lw(uintptr_t addr) { return (uint32_t)tsbi_call(TSBI_LW, addr, 0); }
static inline void tsbi_sw(uintptr_t addr, uint32_t val) { (void)tsbi_call(TSBI_SW, addr, val); }
#if __riscv_xlen == 64
static inline uint64_t tsbi_ld(uintptr_t addr) { return tsbi_call(TSBI_LD, addr, 0); }
static inline void tsbi_sd(uintptr_t addr, uint64_t val) { (void)tsbi_call(TSBI_SD, addr, val); }
#endif

#endif // RISCV_ARCH_TEST_C_H
