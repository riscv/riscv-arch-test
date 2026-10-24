/*
 * SPDX-License-Identifier: Apache-2.0
 */

#include "act4_compat.h"

#include "uart.h"

/* ACT4 passes -DTEST_FILE="<name>" on the command line; the fallback keeps
 * this file usable by a standalone build. */
#ifndef TEST_FILE
#define TEST_FILE "c_test"
#endif

void act4_report_summary(int failed) {
    printf("\nRVCP-SUMMARY: TEST %s - Test File \"%s\"\n", failed ? "FAILED" : "PASSED", TEST_FILE);
}
