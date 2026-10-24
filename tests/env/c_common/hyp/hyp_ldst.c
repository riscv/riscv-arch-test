/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * common/hyp/hyp_ldst.c — HLV / HLVX / HSV instruction wrappers
 *
 * All H-extension virtual-machine load/store instructions share the
 * SYSTEM opcode (0x73) with funct3=0x4. They are differentiated by
 * funct7 and rs2 fields:
 *
 *   HLV.B    funct7=0x30, rs2=0x00  (rd=result, rs1=addr)
 *   HLV.BU   funct7=0x30, rs2=0x01
 *   HLV.H    funct7=0x32, rs2=0x00
 *   HLV.HU   funct7=0x32, rs2=0x01
 *   HLV.W    funct7=0x34, rs2=0x00
 *   HLV.WU   funct7=0x34, rs2=0x01
 *   HLV.D    funct7=0x36, rs2=0x00
 *   HLVX.HU  funct7=0x32, rs2=0x03
 *   HLVX.WU  funct7=0x34, rs2=0x03
 *   HSV.B    funct7=0x31, rs2=src, rs1=addr, rd=0
 *   HSV.H    funct7=0x33, rs2=src, rs1=addr, rd=0
 *   HSV.W    funct7=0x35, rs2=src, rs1=addr, rd=0
 *   HSV.D    funct7=0x37, rs2=src, rs1=addr, rd=0
 *
 * We use .insn r encoding format:
 *   .insn r opcode, funct3, funct7, rd, rs1, rs2
 * =================================================================== */

#include "hyp_ldst.h"

/* ===================================================================
 * HLV — Load from guest virtual memory
 * =================================================================== */

int8_t hlv_b(uintptr_t addr) {
    long result;
    /* HLV.B rd, (rs1): funct7=0x30, rs2=x0, funct3=4 */
    asm volatile (
        ".insn r 0x73, 0x4, 0x30, %0, %1, x0"
        : "=r"(result) : "r"(addr) : "memory"
    );
    return (int8_t)result;
}

uint8_t hlv_bu(uintptr_t addr) {
    long result;
    /* HLV.BU rd, (rs1): funct7=0x30, rs2=x1, funct3=4 */
    asm volatile (
        ".insn r 0x73, 0x4, 0x30, %0, %1, x1"
        : "=r"(result) : "r"(addr) : "memory"
    );
    return (uint8_t)result;
}

int16_t hlv_h(uintptr_t addr) {
    long result;
    /* HLV.H rd, (rs1): funct7=0x32, rs2=x0, funct3=4 */
    asm volatile (
        ".insn r 0x73, 0x4, 0x32, %0, %1, x0"
        : "=r"(result) : "r"(addr) : "memory"
    );
    return (int16_t)result;
}

uint16_t hlv_hu(uintptr_t addr) {
    long result;
    /* HLV.HU rd, (rs1): funct7=0x32, rs2=x1, funct3=4 */
    asm volatile (
        ".insn r 0x73, 0x4, 0x32, %0, %1, x1"
        : "=r"(result) : "r"(addr) : "memory"
    );
    return (uint16_t)result;
}

int32_t hlv_w(uintptr_t addr) {
    long result;
    /* HLV.W rd, (rs1): funct7=0x34, rs2=x0, funct3=4 */
    asm volatile (
        ".insn r 0x73, 0x4, 0x34, %0, %1, x0"
        : "=r"(result) : "r"(addr) : "memory"
    );
    return (int32_t)result;
}

uint32_t hlv_wu(uintptr_t addr) {
    long result;
    /* HLV.WU rd, (rs1): funct7=0x34, rs2=x1, funct3=4 */
    asm volatile (
        ".insn r 0x73, 0x4, 0x34, %0, %1, x1"
        : "=r"(result) : "r"(addr) : "memory"
    );
    return (uint32_t)result;
}

uint64_t hlv_d(uintptr_t addr) {
    long result;
    /* HLV.D rd, (rs1): funct7=0x36, rs2=x0, funct3=4 */
    asm volatile (
        ".insn r 0x73, 0x4, 0x36, %0, %1, x0"
        : "=r"(result) : "r"(addr) : "memory"
    );
    return (uint64_t)result;
}

/* ===================================================================
 * HLVX — Load with eXecute permission check
 * =================================================================== */

uint16_t hlvx_hu(uintptr_t addr) {
    long result;
    /* HLVX.HU rd, (rs1): funct7=0x32, rs2=x3, funct3=4 */
    asm volatile (
        ".insn r 0x73, 0x4, 0x32, %0, %1, x3"
        : "=r"(result) : "r"(addr) : "memory"
    );
    return (uint16_t)result;
}

uint32_t hlvx_wu(uintptr_t addr) {
    long result;
    /* HLVX.WU rd, (rs1): funct7=0x34, rs2=x3, funct3=4 */
    asm volatile (
        ".insn r 0x73, 0x4, 0x34, %0, %1, x3"
        : "=r"(result) : "r"(addr) : "memory"
    );
    return (uint32_t)result;
}

/* ===================================================================
 * HSV — Store to guest virtual memory
 * =================================================================== */

void hsv_b(uintptr_t addr, uint8_t val) {
    /* HSV.B rs2, (rs1): funct7=0x31, rd=x0, funct3=4 */
    asm volatile (
        ".insn r 0x73, 0x4, 0x31, x0, %0, %1"
        :: "r"(addr), "r"((uintptr_t)val) : "memory"
    );
}

void hsv_h(uintptr_t addr, uint16_t val) {
    /* HSV.H rs2, (rs1): funct7=0x33, rd=x0, funct3=4 */
    asm volatile (
        ".insn r 0x73, 0x4, 0x33, x0, %0, %1"
        :: "r"(addr), "r"((uintptr_t)val) : "memory"
    );
}

void hsv_w(uintptr_t addr, uint32_t val) {
    /* HSV.W rs2, (rs1): funct7=0x35, rd=x0, funct3=4 */
    asm volatile (
        ".insn r 0x73, 0x4, 0x35, x0, %0, %1"
        :: "r"(addr), "r"((uintptr_t)val) : "memory"
    );
}

void hsv_d(uintptr_t addr, uint64_t val) {
    /* HSV.D rs2, (rs1): funct7=0x37, rd=x0, funct3=4 */
    asm volatile (
        ".insn r 0x73, 0x4, 0x37, x0, %0, %1"
        :: "r"(addr), "r"((uintptr_t)val) : "memory"
    );
}
