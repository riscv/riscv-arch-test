/*
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef C_COMMON_ACT4_COMPAT_H
#define C_COMMON_ACT4_COMPAT_H

/*
 * Report the result to the ACT4 test harness.
 *
 * run_tests.py decides pass/fail from an `RVCP-SUMMARY: TEST <result> -
 * Test File "<name>"` line on the console; without one, a test that exits 0
 * is still reported as failed. `failed` is the number of failed test cases,
 * i.e. what test_print_summary() returns.
 */
void act4_report_summary(int failed);

#endif /* C_COMMON_ACT4_COMPAT_H */
