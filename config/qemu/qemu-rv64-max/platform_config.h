/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef PLATFORM_QEMU_RV64_MAX_H
#define PLATFORM_QEMU_RV64_MAX_H

/* This header is included via CFLAGS -include for C code only.
 * Assembly-only constants are in rvmodel_macros.h (included via ASFLAGS). */

/* ===== QEMU virt platform address map ===== */

/* UART (NS16550 compatible) */
#define PLATFORM_UART0_BASE     0x10000000UL


/* Memory */
#ifndef PLATFORM_MEM_BASE
#define PLATFORM_MEM_BASE       0x80000000UL
#endif

#define PLATFORM_MEM_SIZE       0x10000000UL    /* 256 MB */

/* QEMU test device address (used by PMP rules that need to cover the
 * finisher region; the actual halt behavior is in rvmodel_macros.h) */
#define PLATFORM_TEST_DEVICE            0x100000UL

/* Platform name */
#define CONFIG_NAME           "QEMU RV64 MAX"


/* Some Case will crash qemu，mark those test as SKIP */
#define QEMU_SKIP_TESTS  1

/* ===== CLINT / Machine Timer addresses (for C code) =====
 * These mirror the values in rvmodel_macros.h for C code use.
 * Assembly code uses the originals in rvmodel_macros.h. */
#define PLATFORM_CLINT_BASE       0x02000000UL
/* Interrupt-controller / software-interrupt device capabilities (consumed by
 * common/capabilities.h to derive MSWI_AVAILABLE). */
#define CLINT_SUPPORTED            /* SiFive CLINT: MSIP@+0x0, MTIMECMP@+0x4000, MTIME@+0xBFF8 */
#define MSWI_SUPPORTED             /* machine software-interrupt device (msip MMIO) present */
#define PLATFORM_MSIP_ADDR        PLATFORM_CLINT_BASE
#define PLATFORM_MTIMECMP_ADDR    (PLATFORM_CLINT_BASE + 0x4000UL)
#define PLATFORM_MTIME_ADDR       (PLATFORM_CLINT_BASE + 0xBFF8UL)

#endif /* PLATFORM_QEMU_RV64_MAX_H */
