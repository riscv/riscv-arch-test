// SPDX-License-Identifier: Apache-2.0
// Copyright (c) 2025 RISC-V International

// FeatureExtractor.S
// Detects whether the M extension is implemented by executing DIV.
// If DIV traps, only I is printed. If DIV succeeds, I and M are printed.


##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, Zicsr, Sm]
# MARCH: rv${XLEN}i_zicsr
##### END_TEST_CONFIG #####

#define TEST_FILE "FeatureExtractor.S"
#define SIGUPD_COUNT 4

#include "riscv_arch_test.h"

RVTEST_BEGIN

main:
    // Mtrap_sig stores the current trap-signature write pointer.
    // If DIV traps, the framework trap handler advances this pointer.
    LA      s0, Mtrap_sig
    LREG    s1, 0(s0)

    // Probe M extension.
    // Raw encoding of: div a2, a0, a1
    // This allows the file to compile with rv64i_zicsr.
    li      a0, 10
    li      a1, 2

    .option push
    .option norvc
    .word   0x02b54633
    .option pop

    nop

    // Check whether trap-signature pointer changed.
    LREG    s2, 0(s0)
    sub     s3, s2, s1        // s3 == 0 means no trap, so M exists.

    // Print YAML.
    LA      a3, str_yaml_header
    RVMODEL_IO_WRITE_STR(t0, t1, t2, a3)

    LA      a3, str_ext_I
    RVMODEL_IO_WRITE_STR(t0, t1, t2, a3)

    bnez    s3, skip_M

    LA      a3, str_ext_M
    RVMODEL_IO_WRITE_STR(t0, t1, t2, a3)

skip_M:
    RVTEST_CODE_END


RVTEST_DATA_BEGIN

.align 3

str_yaml_header:
    .asciz "implemented_extensions:\n"

str_ext_I:
    .asciz "  - { name: I, version: '= 2.1' }\n"

str_ext_M:
    .asciz "  - { name: M, version: '= 2.0' }\n"

RVTEST_DATA_END

RVTEST_SIG_SETUP