// RISC-V Compliance Test Header File
// Copyright (c) 2017, Codasip Ltd. All Rights Reserved.
// See LICENSE for license details.
//
// Description: Common header file for RV32I tests

#ifndef _COMPLIANCE_TEST_H
#define _COMPLIANCE_TEST_H

#include "riscv_test.h"

//-----------------------------------------------------------------------
// RV Compliance Macros
//-----------------------------------------------------------------------

#define TESTUTIL_BASE 0x20000
#define TESTUTIL_ADDR_HALT (TESTUTIL_BASE + 0x0)
#define TESTUTIL_ADDR_BEGIN_SIGNATURE (TESTUTIL_BASE + 0x4)
#define TESTUTIL_ADDR_END_SIGNATURE (TESTUTIL_BASE + 0x8)

#define RV_COMPLIANCE_HALT                                                    \
        /* tell simulation about location of begin_signature */               \
        la t0, begin_signature;                                               \
        li t1, TESTUTIL_ADDR_BEGIN_SIGNATURE;                                 \
        sw t0, 0(t1);                                                         \
        /* tell simulation about location of end_signature */                 \
        la t0, end_signature;                                                 \
        li t1, TESTUTIL_ADDR_END_SIGNATURE;                                   \
        sw t0, 0(t1);                                                         \
        /* dump signature and terminate simulation */                         \
        li t0, 1;                                                             \
        li t1, TESTUTIL_ADDR_HALT;                                            \
        sw t0, 0(t1);                                                         \
        RVTEST_PASS                                                           \

#define RV_COMPLIANCE_RV32M                                                   \
        RVTEST_RV32M                                                          \

#define RV_COMPLIANCE_CODE_BEGIN                                              \
        RVTEST_CODE_BEGIN_OLD \

#define RV_COMPLIANCE_CODE_END                                                \
        RVTEST_CODE_END_OLD \

#define RV_COMPLIANCE_DATA_BEGIN                                              \
        RVTEST_DATA_BEGIN_OLD \

#define RV_COMPLIANCE_DATA_END                                                \
        RVTEST_DATA_END_OLD \

#endif
// RISC-V Compliance IO Test Header File

/*
 * Copyright (c) 2005-2018 Imperas Software Ltd., www.imperas.com
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied.
 *
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 */

#ifndef _COMPLIANCE_IO_H
#define _COMPLIANCE_IO_H

//-----------------------------------------------------------------------
// RV IO Macros (Non functional)
//-----------------------------------------------------------------------

#define RVTEST_IO_INIT
#define RVTEST_IO_WRITE_STR(_SP, _STR)
#define RVTEST_IO_CHECK()
#define RVTEST_IO_ASSERT_GPR_EQ(_SP, _R, _I)
#define RVTEST_IO_ASSERT_SFPR_EQ(_F, _R, _I)
#define RVTEST_IO_ASSERT_DFPR_EQ(_D, _R, _I)

#endif // _COMPLIANCE_IO_H
