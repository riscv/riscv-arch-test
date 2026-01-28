//
// Copyright (C) 2024 Harvey Mudd College & Oklahoma State University, Habib University, UET Lahore
//
// SPDX-License-Identifier: Apache-2.0
///////////////////////////////////////////

// Define special purpose registers before including test_macros_vector.h
#define DATA_BASE x4
#define SIG_BASE x3
#define VLENB_CACHE x5
#define HELPER_GPR x6

#include "test_macros_vector.h"

RVTEST_ISA("RV32IMV_Zicsr, RV64IMV_Zicsr")

# Test code region
.section .text.init
.globl rvtest_entry_point
rvtest_entry_point:
RVMODEL_BOOT
RVTEST_CODE_BEGIN

#ifdef TEST_CASE_1

RVTEST_CASE(1,"//check ISA:=regex(.*I.*M.*V.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; def rvtest_dtrap_routine=True; def TEST_CASE_1=True",ZicsrV)

RVTEST_V_ENABLE()
RVTEST_SIGBASE(SIG_BASE, signature_base)

#define SEWMIN 8
#define ELEN 64

#if SEWMIN == 64
    #define SEWSIZE e64
    #define VLESEWMIN vle64.v
    #define RVTEST_SIGUPD_V_SEWMIN(BR, TMPR, AVL, VREG) RVTEST_SIGUPD_V(BR, TMPR, AVL, 64, VREG)
#elif SEWMIN == 32
    #define SEWSIZE e32
    #define VLESEWMIN vle32.v
    #define RVTEST_SIGUPD_V_SEWMIN(BR, TMPR, AVL, VREG) RVTEST_SIGUPD_V(BR, TMPR, AVL, 32, VREG)
#elif SEWMIN == 16
    #define SEWSIZE e16
    #define VLESEWMIN vle16.v
    #define RVTEST_SIGUPD_V_SEWMIN(BR, TMPR, AVL, VREG) RVTEST_SIGUPD_V(BR, TMPR, AVL, 16, VREG)
#else
    #define SEWSIZE e8
    #define VLESEWMIN vle8.v
    #define RVTEST_SIGUPD_V_SEWMIN(BR, TMPR, AVL, VREG) RVTEST_SIGUPD_V(BR, TMPR, AVL, 8, VREG)
#endif
