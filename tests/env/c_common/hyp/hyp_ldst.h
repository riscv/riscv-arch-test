/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef HYP_LDST_H
#define HYP_LDST_H

/* ===================================================================
 * HLV / HLVX / HSV instruction wrappers
 *
 * These hypervisor virtual-machine load/store instructions are valid
 * in M-mode or HS-mode (and U-mode when hstatus.HU=1). They perform
 * accesses to guest virtual memory using two-stage address translation
 * (vsatp + hgatp). The effective privilege is controlled by
 * hstatus.SPVP (0=VU, 1=VS).
 *
 * Executing these in V=1 (VS/VU-mode) triggers a virtual-instruction
 * exception (cause=22).
 *
 * Encoding: R-type with opcode=SYSTEM (0x73), funct3=0x4, rd/rs1/rs2
 * as specified per instruction variant.
 * =================================================================== */

#include "types.h"

/* ===================================================================
 * HLV — Hypervisor Load from Virtual memory
 * =================================================================== */

/* HLV.B: load signed byte from guest VA */
int8_t   hlv_b(uintptr_t addr);

/* HLV.BU: load unsigned byte from guest VA */
uint8_t  hlv_bu(uintptr_t addr);

/* HLV.H: load signed halfword from guest VA */
int16_t  hlv_h(uintptr_t addr);

/* HLV.HU: load unsigned halfword from guest VA */
uint16_t hlv_hu(uintptr_t addr);

/* HLV.W: load signed word from guest VA */
int32_t  hlv_w(uintptr_t addr);

/* HLV.WU: load unsigned word from guest VA (RV64 only) */
uint32_t hlv_wu(uintptr_t addr);

/* HLV.D: load doubleword from guest VA (RV64 only) */
uint64_t hlv_d(uintptr_t addr);

/* ===================================================================
 * HLVX — Hypervisor Load with eXecute permission
 *
 * Like HLV but checks execute permission instead of read permission
 * on the VS-stage PTE. Used by hypervisors to emulate instruction
 * fetch from guest memory.
 * =================================================================== */

/* HLVX.HU: load unsigned halfword, execute permission */
uint16_t hlvx_hu(uintptr_t addr);

/* HLVX.WU: load unsigned word, execute permission */
uint32_t hlvx_wu(uintptr_t addr);

/* ===================================================================
 * HSV — Hypervisor Store to Virtual memory
 * =================================================================== */

/* HSV.B: store byte to guest VA */
void hsv_b(uintptr_t addr, uint8_t val);

/* HSV.H: store halfword to guest VA */
void hsv_h(uintptr_t addr, uint16_t val);

/* HSV.W: store word to guest VA */
void hsv_w(uintptr_t addr, uint32_t val);

/* HSV.D: store doubleword to guest VA (RV64 only) */
void hsv_d(uintptr_t addr, uint64_t val);

#endif /* HYP_LDST_H */
