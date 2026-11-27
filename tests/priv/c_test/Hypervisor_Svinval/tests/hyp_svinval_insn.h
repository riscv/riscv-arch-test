/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * hyp_svinval_insn.h - Svinval HINVAL Instruction Macros for Hypervisor
 *
 * Defines inline assembly macros for the Svinval instructions used in
 * Hypervisor scenarios:
 *   - HINVAL.VVMA rs1, rs2   (VS-stage TLB invalidation)
 *   - HINVAL.GVMA rs1, rs2   (G-stage TLB invalidation)
 *   - SFENCE.W.INVAL          (ordering guarantee)
 *   - SFENCE.INVAL.IR         (completion of pending invalidations)
 *
 * Encoding format (R-type, opcode=SYSTEM 0x73):
 *   hinval.vvma rs1, rs2:  funct7=0x13, rs2=asid, rs1=vaddr, rd=x0
 *   hinval.gvma rs1, rs2:  funct7=0x33, rs2=vmid, rs1=gpa>>2, rd=x0
 *   sfence.w.inval:        funct7=0x0C, rs1=x0, rs2=x0, rd=x0
 *   sfence.inval.ir:       funct7=0x0C, rs1=x0, rs2=x1, rd=x0
 */

#ifndef HYP_SVINVAL_INSN_H
#define HYP_SVINVAL_INSN_H

#include "types.h"

/*
 * SINVAL.VMA vaddr, asid
 * Flush S-mode TLB entries for the given (vaddr, asid) pair.
 * Valid in M-mode or S-mode. Used for Svinval extension detection.
 */
#define SINVAL_VMA(vaddr, asid) \
    ({ asm volatile(".insn r 0x73, 0, 0x0B, x0, %0, %1" \
                    :: "r"((uintptr_t)(vaddr)), "r"((uintptr_t)(asid)) : "memory"); })

/*
 * HINVAL.VVMA vaddr, asid
 * Flush VS-stage TLB entries for the given (vaddr, asid) pair.
 * Only valid in M-mode or HS-mode.
 */
#define HINVAL_VVMA(vaddr, asid) \
    ({ asm volatile(".insn r 0x73, 0, 0x13, x0, %0, %1" \
                    :: "r"((uintptr_t)(vaddr)), "r"((uintptr_t)(asid)) : "memory"); })

/*
 * HINVAL.GVMA gpa_shifted, vmid
 * Flush G-stage TLB entries for the given (gpa>>2, vmid) pair.
 * Only valid in M-mode or HS-mode (with mstatus.TVM=0).
 */
#define HINVAL_GVMA(gpa_shifted, vmid) \
    ({ asm volatile(".insn r 0x73, 0, 0x33, x0, %0, %1" \
                    :: "r"((uintptr_t)(gpa_shifted)), "r"((uintptr_t)(vmid)) : "memory"); })

/*
 * SFENCE.W.INVAL
 * Ordering guarantee: all preceding HINVAL instructions are ordered
 * before all subsequent SFENCE.INVAL.IR instructions.
 */
#define SFENCE_W_INVAL() \
    ({ asm volatile(".insn r 0x73, 0, 0x0C, x0, x0, x0" ::: "memory"); })

/*
 * SFENCE.INVAL.IR
 * Completion guarantee: all preceding HINVAL instructions (ordered by
 * SFENCE.W.INVAL) have their TLB invalidation effects visible.
 */
#define SFENCE_INVAL_IR() \
    ({ asm volatile(".insn r 0x73, 0, 0x0C, x0, x0, x1" ::: "memory"); })

#endif /* HYP_SVINVAL_INSN_H */
