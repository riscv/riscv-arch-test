/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef HYP_FENCE_H
#define HYP_FENCE_H

/* ===================================================================
 * HFENCE.VVMA / HFENCE.GVMA instruction wrappers
 *
 * These instructions flush TLB entries for the two stages of
 * address translation controlled by the hypervisor:
 *   - HFENCE.VVMA: flushes VS-stage (vsatp) TLB entries
 *   - HFENCE.GVMA: flushes G-stage (hgatp) TLB entries
 *
 * Both are only valid in M-mode or HS-mode. Executing them in
 * VS/VU-mode triggers a virtual-instruction exception (cause=22).
 *
 * Encoding (R-type, opcode=SYSTEM 0x73):
 *   HFENCE.VVMA rs1, rs2:  funct7=0x11, rs2=asid, rs1=vaddr, rd=0
 *   HFENCE.GVMA rs1, rs2:  funct7=0x31, rs2=vmid, rs1=gpa>>2, rd=0
 * =================================================================== */

#include "types.h"

/**
 * hfence_vvma - Flush VS-stage TLB entries
 *
 * Similar to sfence.vma but targets vsatp-controlled VS-stage
 * translation. Only effective in M-mode or HS-mode.
 *
 * @vaddr: guest virtual address to flush (0 = flush all addresses)
 * @asid:  guest ASID to flush (0 = flush all ASIDs)
 */
void hfence_vvma(uintptr_t vaddr, uintptr_t asid);

/* hfence_vvma_all() is provided as a static inline in hyp_csr.h. */

/**
 * hfence_gvma - Flush G-stage TLB entries
 *
 * Targets hgatp-controlled G-stage translation.
 * Only effective in M-mode or HS-mode (with mstatus.TVM=0).
 *
 * @gpa_shifted: guest physical address >> 2 (0 = flush all)
 * @vmid:        Virtual Machine ID (0 = flush all VMIDs)
 */
void hfence_gvma(uintptr_t gpa_shifted, uintptr_t vmid);

/* hfence_gvma_all() is provided as a static inline in hyp_csr.h. */

#endif /* HYP_FENCE_H */
