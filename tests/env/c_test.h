// c_test.h
// Minimal ACT runtime API for C tests
// Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
// SPDX-License-Identifier: Apache-2.0

#ifndef C_TEST_H
#define C_TEST_H

// Printing functions. These use RVMODEL_IO_WRITE_STR.
int putchar(int ch);
int puts(const char *s);
int printf(const char *fmt, ...);

// Test termination functions. These use the RVMODEL_HALT_PASS and RVMODEL_HALT_FAIL mechanisms.
// The termination functions automatically print the RVCP-SUMMARY message.
void rvtest_pass(void) __attribute__((noreturn));
void rvtest_fail(void) __attribute__((noreturn));
void print_error(const char *fmt, ...) __attribute__((noreturn)); // Print an error message and then exit with a failure.

#endif // C_TEST_H
