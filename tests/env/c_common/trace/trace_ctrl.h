/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Trace control MMIO register access API.
 * Based on RISC-V Trace Control Interface Specification v1.0 (Ratified).
 */

#ifndef TRACE_CTRL_H
#define TRACE_CTRL_H

#include "types.h"

/* ===================================================================
 * Trace Encoder Register Offsets
 * =================================================================== */
#define TRTE_CONTROL_OFFSET          0x000
#define TRTE_IMPL_OFFSET             0x004
#define TRTE_INST_FEATURES_OFFSET    0x008
#define TRTE_TIMESTAMP_CTRL_OFFSET   0x00C

/* ===================================================================
 * Trace RAM Sink Register Offsets
 * =================================================================== */
#define TRRAM_CONTROL_OFFSET         0x000
#define TRRAM_START_LOW_OFFSET       0x010
#define TRRAM_START_HIGH_OFFSET      0x014
#define TRRAM_LIMIT_LOW_OFFSET       0x018
#define TRRAM_LIMIT_HIGH_OFFSET      0x01C
#define TRRAM_WP_LOW_OFFSET          0x020
#define TRRAM_WP_HIGH_OFFSET         0x024
#define TRRAM_RP_LOW_OFFSET          0x028
#define TRRAM_RP_HIGH_OFFSET         0x02C
#define TRRAM_DATA_OFFSET            0x040

/* ===================================================================
 * trRamControl bit field definitions
 * =================================================================== */
#define TRRAM_ACTIVE_BIT             (1UL << 0)  /* Primary activate/reset */
#define TRRAM_ENABLE_BIT             (1UL << 1)  /* Sink enable */
#define TRRAM_EMPTY_BIT              (1UL << 3)  /* RO: buffers empty */
#define TRRAM_MODE_BIT               (1UL << 4)  /* 0=SRAM, 1=SMEM */

/* ===================================================================
 * trTeControl bit field definitions
 * =================================================================== */
#define TRTE_ACTIVE_BIT              (1UL << 0)
#define TRTE_ENABLE_BIT              (1UL << 1)
#define TRTE_INST_TRACING_BIT        (1UL << 2)
#define TRTE_EMPTY_BIT               (1UL << 3)

#define TRTE_INST_MODE_SHIFT         4
#define TRTE_INST_MODE_MASK          (0x7UL << 4)

#define TRTE_CONTEXT_BIT             (1UL << 9)
#define TRTE_INST_TRIG_ENABLE_BIT    (1UL << 11)
#define TRTE_INST_STALL_OVERFLOW_BIT (1UL << 12)
#define TRTE_INST_STALL_ENA_BIT      (1UL << 13)
#define TRTE_INHIBIT_SRC_BIT         (1UL << 15)

#define TRTE_INST_SYNC_MODE_SHIFT    16
#define TRTE_INST_SYNC_MODE_MASK     (0x3UL << 16)

#define TRTE_INST_SYNC_MAX_SHIFT     20
#define TRTE_INST_SYNC_MAX_MASK      (0xFUL << 20)

#define TRTE_FORMAT_SHIFT            24
#define TRTE_FORMAT_MASK             (0x7UL << 24)

/* trTeInstMode values */
#define TRTE_INST_MODE_DISABLED      0
#define TRTE_INST_MODE_BTM           3    /* Branch Trace Messaging */
#define TRTE_INST_MODE_HTM           6    /* History Trace Messaging */
#define TRTE_INST_MODE_VENDOR        7

/* trTeInstSyncMode values */
#define TRTE_SYNC_MODE_OFF           0
#define TRTE_SYNC_MODE_MSG_COUNT     1
#define TRTE_SYNC_MODE_CYCLE_COUNT   2
#define TRTE_SYNC_MODE_HALFWORD_COUNT 3

/* trTeFormat values */
#define TRTE_FORMAT_ETRACE           0
#define TRTE_FORMAT_NTRACE           1

/* ===================================================================
 * trTeImpl bit field definitions
 * =================================================================== */
#define TRTE_VER_MAJOR_SHIFT         0
#define TRTE_VER_MAJOR_MASK          (0xFUL << 0)

#define TRTE_VER_MINOR_SHIFT         4
#define TRTE_VER_MINOR_MASK          (0xFUL << 4)

#define TRTE_COMP_TYPE_SHIFT         8
#define TRTE_COMP_TYPE_MASK          (0xFUL << 8)

#define TRTE_PROTOCOL_MAJOR_SHIFT    16
#define TRTE_PROTOCOL_MAJOR_MASK     (0xFUL << 16)

#define TRTE_PROTOCOL_MINOR_SHIFT    20
#define TRTE_PROTOCOL_MINOR_MASK     (0xFUL << 20)

/* Component types */
#define TRTE_COMP_TYPE_ENCODER       0x1
#define TRTE_COMP_TYPE_FUNNEL        0x8
#define TRTE_COMP_TYPE_RAM_SINK      0x9
#define TRTE_COMP_TYPE_PIB_SINK      0xA
#define TRTE_COMP_TYPE_ATB_BRIDGE    0xE

/* ===================================================================
 * trTeInstFeatures bit field definitions
 * =================================================================== */
#define TRTE_INST_NO_ADDR_DIFF_BIT   (1UL << 0)
#define TRTE_INST_NO_TRAP_ADDR_BIT   (1UL << 1)
#define TRTE_INST_EN_SEQ_JUMP_BIT    (1UL << 2)
#define TRTE_INST_EN_IMPLICIT_RET_BIT (1UL << 3)
#define TRTE_INST_EN_BRANCH_PRED_BIT (1UL << 4)
#define TRTE_INST_EN_JUMP_CACHE_BIT  (1UL << 5)

#define TRTE_INST_IMPLICIT_RET_MODE_SHIFT 6
#define TRTE_INST_IMPLICIT_RET_MODE_MASK  (0x3UL << 6)

#define TRTE_INST_EN_REPEAT_HIST_BIT (1UL << 8)
#define TRTE_INST_EN_ALL_JUMPS_BIT   (1UL << 9)
#define TRTE_INST_EXTEND_ADDR_MSB_BIT (1UL << 10)

#define TRTE_SRC_ID_SHIFT            16
#define TRTE_SRC_ID_MASK             (0xFFFUL << 16)

#define TRTE_SRC_BITS_SHIFT          28
#define TRTE_SRC_BITS_MASK           (0xFUL << 28)

/* trTeInstImplicitReturnMode values */
#define TRTE_IMPLICIT_RET_OFF        0
#define TRTE_IMPLICIT_RET_SIMPLE     1    /* Simple counting */
#define TRTE_IMPLICIT_RET_PARTIAL    2    /* Partial address compare */
#define TRTE_IMPLICIT_RET_FULL       3    /* Full address compare */

/* ===================================================================
 * trTeTimestampCtrl bit field definitions
 * =================================================================== */
#define TRTS_ENABLE_BIT              (1UL << 0)
#define TRTS_QUALIFY_ENABLE_BIT      (1UL << 1)

/* ===================================================================
 * Trace control API functions
 * =================================================================== */

/* Initialize trace control with base addresses */
void trace_ctrl_init(uintptr_t encoder_base, uintptr_t ramsink_base);

/* Detection: check if trace encoder exists (reads trTeImpl.compType) */
bool trace_detect(void);

/* Activate/deactivate trace encoder (trTeActive bit) */
void trace_activate(void);
void trace_deactivate(void);
bool trace_is_active(void);

/* Enable/disable trace output (trTeEnable bit) */
void trace_enable(void);
void trace_disable(void);
bool trace_is_enabled(void);

/* Start/stop instruction trace generation (trTeInstTracing bit).
 * Per Spec this must be written by the trace tool AFTER trTeEnable=1;
 * without it the encoder is enabled but emits no instruction trace. */
void trace_set_inst_tracing(bool enable);
bool trace_is_inst_tracing(void);

/* Set/get trace mode (trTeInstMode field) */
bool trace_set_mode(uint8_t mode);
uint8_t trace_get_mode(void);

/* Read/write full trTeControl register */
uint32_t trace_read_control(void);
void trace_write_control(uint32_t val);

/* Read implementation registers */
uint32_t trace_read_impl(void);
uint32_t trace_read_features(void);
uint32_t trace_read_timestamp_ctrl(void);

/* Check if trace queue is empty (trTeEmpty bit) */
bool trace_is_empty(void);

/* Configure periodic synchronization */
void trace_set_sync_config(uint8_t mode, uint8_t max_interval);

/* Enable/disable context reporting (Ownership messages) */
void trace_set_context_enable(bool enable);

/* Inhibit SRC field */
void trace_set_inhibit_src(bool inhibit);

/* Stall on overflow control */
void trace_set_stall_enable(bool enable);

/* Timestamp control */
void trace_set_timestamp_enable(bool enable);

/* Feature control: sequential jump optimization */
void trace_set_sequential_jump(bool enable);

/* Feature control: implicit return mode */
void trace_set_implicit_return_mode(uint8_t mode);

/* Feature control: repeated history optimization */
void trace_set_repeated_history(bool enable);

/* Feature control: report all jumps */
void trace_set_all_jumps(bool enable);

/* Feature control: virtual address MSB extension */
void trace_set_extend_addr_msb(bool enable);

/* Source ID configuration */
void trace_set_src_id(uint32_t id);
uint32_t trace_get_src_id(void);
uint8_t trace_get_src_bits(void);

/* ===================================================================
 * RAM Sink API
 * =================================================================== */

/* Configure RAM sink buffer (start and limit addresses) */
void trace_ram_configure(uint64_t start, uint64_t limit);

/* Activate the RAM sink (trRamActive) and select SMEM mode.
 * Per Spec, buffer registers (start/limit/WP) are inaccessible while
 * trRamActive=0, so this MUST be called before trace_ram_configure(). */
void trace_ram_activate_smem(void);

/* Enable/disable RAM sink data storage (trRamEnable).
 * Disabling flushes any queued trace data out to memory. */
void trace_ram_enable(void);
void trace_ram_disable(void);

/* Check whether the RAM sink is operating in SMEM (system-memory) mode. */
bool trace_ram_is_smem(void);

/* Get write pointer (current position in buffer) */
uint64_t trace_ram_get_wp(void);

/* Get read pointer */
uint64_t trace_ram_get_rp(void);

/* Set read pointer */
void trace_ram_set_rp(uint64_t rp);

/* Read trace data from RAM sink */
size_t trace_ram_read_bytes(uint8_t *buf, size_t maxlen);

/* Reset RAM sink pointers */
void trace_ram_reset(void);

/* Check if RAM sink is available */
bool trace_ram_detect(void);

#endif /* TRACE_CTRL_H */
