/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * common/hyp/hyp_fence.c — HFENCE.VVMA / HFENCE.GVMA wrappers
 *
 * Uses .insn r encoding since GCC/binutils may not recognize the
 * hfence.vvma / hfence.gvma mnemonics on all toolchain versions.
 *
 * HFENCE.VVMA encoding (R-type):
 *   [31:25] funct7=0010001 (0x11)
 *   [24:20] rs2 = asid register
 *   [19:15] rs1 = vaddr register
 *   [14:12] funct3 = 000
 *   [11:7]  rd = 00000
 *   [6:0]   opcode = 1110011 (SYSTEM)
 *
 * HFENCE.GVMA encoding (R-type):
 *   [31:25] funct7=0110001 (0x31)
 *   [24:20] rs2 = vmid register
 *   [19:15] rs1 = gpa_shifted register
 *   [14:12] funct3 = 000
 *   [11:7]  rd = 00000
 *   [6:0]   opcode = 1110011 (SYSTEM)
 * =================================================================== */

#include "hyp_fence.h"

/* ===================================================================
 * HFENCE.VVMA
 * =================================================================== */

void hfence_vvma(uintptr_t vaddr, uintptr_t asid) {
    /* hfence.vvma rs1, rs2
     * Use .insn r to encode with register operands.
     * opcode=0x73(SYSTEM), funct3=0, funct7=0x11, rd=x0 */
    asm volatile (
        ".insn r 0x73, 0, 0x11, x0, %0, %1"
        :: "r"(vaddr), "r"(asid)
        : "memory"
    );
}

/* hfence_vvma_all() is provided as a static inline in hyp_csr.h. */

/* ===================================================================
 * HFENCE.GVMA
 * =================================================================== */

void hfence_gvma(uintptr_t gpa_shifted, uintptr_t vmid) {
    /* hfence.gvma rs1, rs2
     * opcode=0x73(SYSTEM), funct3=0, funct7=0x31, rd=x0 */
    asm volatile (
        ".insn r 0x73, 0, 0x31, x0, %0, %1"
        :: "r"(gpa_shifted), "r"(vmid)
        : "memory"
    );
}

/* hfence_gvma_all() is provided as a static inline in hyp_csr.h. */
