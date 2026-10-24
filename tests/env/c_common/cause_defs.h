/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef CAUSE_DEFS_H
#define CAUSE_DEFS_H

/* ===================================================================
 * RISC-V Exception / Interrupt Cause Codes
 *
 * Synchronous exception cause codes (mcause/scause low bits).
 * Safe for both C and assembly inclusion (plain integer constants).
 * =================================================================== */

/* ----- Synchronous exception cause codes ----- */
#define CAUSE_INST_ADDR_MISALIGN    0
#define CAUSE_INST_ACCESS_FAULT     1   /* Instruction access fault (PMP/PMA) */
#define CAUSE_ILLEGAL_INST          2
#define CAUSE_BREAKPOINT            3
#define CAUSE_LOAD_ADDR_MISALIGN    4
#define CAUSE_LOAD_ACCESS_FAULT     5   /* Load access fault (PMP/PMA) */
#define CAUSE_STORE_ADDR_MISALIGN   6
#define CAUSE_STORE_ACCESS_FAULT    7   /* Store/AMO access fault (PMP/PMA) */
#define CAUSE_ECALL_FROM_U          8
#define CAUSE_ECALL_FROM_S          9
#define CAUSE_ECALL_FROM_M          11
#define CAUSE_INST_PAGE_FAULT       12
#define CAUSE_LOAD_PAGE_FAULT       13
/* 14: Reserved by RISC-V privileged spec */
#define CAUSE_STORE_PAGE_FAULT      15
#define CAUSE_DOUBLE_TRAP           16  /* Double-trap exception (Ssdbltrp) */
#define CAUSE_SOFTWARE_CHECK        18  /* Software-check exception (CFI) */
#define CAUSE_HARDWARE_ERROR        19  /* Hardware-error exception */

/* mtval encodings for software-check exception (cause=18) */
#define SWCHECK_NONE                0
#define SWCHECK_LANDING_PAD_FAULT   2   /* Zicfilp: Landing Pad Fault */
#define SWCHECK_SHADOW_STACK_FAULT  3   /* Zicfiss: Shadow Stack Fault */

/* Short aliases for PMP-specific causes */
#define CAUSE_IAF   CAUSE_INST_ACCESS_FAULT
#define CAUSE_LAF   CAUSE_LOAD_ACCESS_FAULT
#define CAUSE_SAF   CAUSE_STORE_ACCESS_FAULT
#define CAUSE_ECU   CAUSE_ECALL_FROM_U
#define CAUSE_ECS   CAUSE_ECALL_FROM_S
#define CAUSE_ECM   CAUSE_ECALL_FROM_M
#define CAUSE_ILI   CAUSE_ILLEGAL_INST

/* Short aliases for page fault causes */
#define CAUSE_IPF   CAUSE_INST_PAGE_FAULT
#define CAUSE_LPF   CAUSE_LOAD_PAGE_FAULT
#define CAUSE_SPF   CAUSE_STORE_PAGE_FAULT

/* ===================================================================
 * Hypervisor cause codes (mcause/scause low bits)
 * =================================================================== */
#define CAUSE_ECALL_FROM_VS            10
#define CAUSE_INST_GUEST_PAGE_FAULT    20
#define CAUSE_LOAD_GUEST_PAGE_FAULT    21
#define CAUSE_VIRTUAL_INSTRUCTION      22
#define CAUSE_STORE_GUEST_PAGE_FAULT   23

/* ===================================================================
 * Interrupt cause codes (mcause/scause low bits when interrupt bit set)
 *
 * These are the IRQ numbers extracted from mcause/scause after
 * masking off the CAUSE_INTERRUPT_BIT.
 * =================================================================== */
#define IRQ_S_SOFTWARE      1
#define IRQ_VS_SOFTWARE     2   /* Hypervisor: VS-level software interrupt */
#define IRQ_M_SOFTWARE      3
#define IRQ_S_TIMER         5
#define IRQ_VS_TIMER        6   /* Hypervisor: VS-level timer interrupt */
#define IRQ_M_TIMER         7
#define IRQ_S_EXTERNAL      9
#define IRQ_VS_EXTERNAL     10  /* Hypervisor: VS-level external interrupt */
#define IRQ_M_EXTERNAL      11

/* ===================================================================
 * LCOFI interrupt bit (bit 13)
 * =================================================================== */
#define MIP_LCOFIP        (1ULL << 13)
#define MIE_LCOFIE        (1ULL << 13)
#define IRQ_LCOFI         13

/* ===================================================================
 * Interrupt bit in mcause
 * =================================================================== */
#ifndef CAUSE_INTERRUPT_BIT
#if __riscv_xlen == 64
#define CAUSE_INTERRUPT_BIT  (1ULL << 63)
#else
#define CAUSE_INTERRUPT_BIT  (1ULL << 31)
#endif
#endif

/* Interrupt cause: S-mode timer */
#define CAUSE_S_TIMER_INTERRUPT  5
#define SCAUSE_INTERRUPT         CAUSE_INTERRUPT_BIT

/* ===================================================================
 * Inline helpers for cause register field extraction (C only)
 * =================================================================== */
#ifndef __ASSEMBLER__
#include "types.h"

/** Check if a cause value represents an interrupt (MSB set). */
static inline int cause_is_interrupt(uintptr_t cause) {
    return (cause & CAUSE_INTERRUPT_BIT) != 0;
}

/** Extract the exception/interrupt code (strip the interrupt bit). */
static inline uintptr_t cause_get_code(uintptr_t cause) {
    return cause & ~CAUSE_INTERRUPT_BIT;
}

/** Check if a cause value is a guest-page-fault (20, 21, or 23).
 * Used by hgatp=Bare tests to assert no guest-page-fault can occur. */
static inline int cause_is_guest_page_fault(uintptr_t cause) {
    return cause == CAUSE_INST_GUEST_PAGE_FAULT ||
           cause == CAUSE_LOAD_GUEST_PAGE_FAULT ||
           cause == CAUSE_STORE_GUEST_PAGE_FAULT;
}

/** Check if a cause is a load-class alignment/access fault (4 or 5).
 * norm:mcause_exccode_ld_ldrsv: a load and a load-reserved (lr.w/lr.d)
 * report the load class. The atomic suites use this to classify a
 * misaligned or faulting lr / load-acquire. */
static inline int cause_is_load_align_fault(uintptr_t cause) {
    return cause == CAUSE_LOAD_ADDR_MISALIGN ||
           cause == CAUSE_LOAD_ACCESS_FAULT;
}

/** Check if a cause is a store/AMO-class alignment/access fault (6 or 7).
 * norm:mcause_exccode_st_sc_amo: a store, store-conditional (sc.w/sc.d),
 * AMO and amocas report the store/AMO class - never the load class. */
static inline int cause_is_store_amo_align_fault(uintptr_t cause) {
    return cause == CAUSE_STORE_ADDR_MISALIGN ||
           cause == CAUSE_STORE_ACCESS_FAULT;
}

/** Check if a cause is any alignment/access fault (load or store/AMO
 * class, i.e. 4/5/6/7). */
static inline int cause_is_align_fault(uintptr_t cause) {
    return cause_is_load_align_fault(cause) ||
           cause_is_store_amo_align_fault(cause);
}
#endif /* __ASSEMBLER__ */

#endif /* CAUSE_DEFS_H */
