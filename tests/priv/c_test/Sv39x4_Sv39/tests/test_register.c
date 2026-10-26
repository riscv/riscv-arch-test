/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * test_register.c - Two-Stage Translation Test Registration
 *
 * 纯聚合文件：#include test_helpers.h + 全部 25 个 group test 源文件。
 * SUITE_VSATP_MODE / SUITE_HGATP_MODE 由各目录 Makefile 通过 -D 传入，
 * 若未定义则 common/hyp/two_stage_helpers.h 提供默认值 (Sv39 + Sv39x4)。
 *
 * 所有 9 个目录共享此文件（借用目录通过 symlink）。
 */

#include "test_helpers.h"

/* Group 1  */ #include "test_vs_only.c"
/* Group 2  */ #include "test_vsatp_csr.c"
/* Group 3  */ #include "test_same_width.c"
/* Group 4  */ #include "test_cross_width.c"
/* Group 5  */ #include "test_non_identity.c"
/* Group 6  */ #include "test_implicit_gstage_fault.c"
/* Group 7  */ #include "test_perm_cross.c"
/* Group 8  */ #include "test_mxr.c"
/* Group 9  */ #include "test_sum.c"
/* Group 10 */ #include "test_hfence_vvma.c"
/* Group 11 */ #include "test_hfence_gvma.c"
/* Group 12 */ #include "test_sfence_vma.c"
/* Group 13 */ #include "test_hlv_hsv.c"
/* Group 14 */ #include "test_mprv_mpv.c"
/* Group 15 */ #include "test_ad_two_stage.c"
/* Group 16 */ #include "test_page_straddle.c"
/* Group 17 */ #include "test_g_bit.c"
/* Group 18 */ #include "test_pbmte.c"
/* Group 19 */ #include "test_pmp.c"
/* Group 20 */ #include "test_priority.c"
/* Group 21 */ #include "test_hgatp_warl.c"
/* Group 22 */ #include "test_svinval.c"
/* Group 23 */ #include "test_large_page.c"
/* Group 24 */ #include "test_ppn_width.c"
/* Group 25 */ #include "test_hgatp_bare_joint.c"
/* Granular */ #include "test_granular_matrix.c"
