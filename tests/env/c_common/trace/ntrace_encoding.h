/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 *
 * N-Trace (Nexus-based Trace) message encoding definitions.
 * Based on RISC-V N-Trace Specification v1.0 (Ratified, 2024-11-21).
 */

#ifndef NTRACE_ENCODING_H
#define NTRACE_ENCODING_H

#include "types.h"

/* ===================================================================
 * TCODE values - Message type identifiers
 * =================================================================== */
#define TCODE_OWNERSHIP              2
#define TCODE_DIRECT_BRANCH          3
#define TCODE_INDIRECT_BRANCH        4
#define TCODE_ERROR                  8
#define TCODE_PROG_TRACE_SYNC        9
#define TCODE_DIRECT_BRANCH_SYNC     11
#define TCODE_INDIRECT_BRANCH_SYNC   12
#define TCODE_RESOURCE_FULL          27
#define TCODE_INDIRECT_BRANCH_HIST   28
#define TCODE_INDIRECT_BRANCH_HIST_SYNC 29
#define TCODE_REPEAT_BRANCH          30
#define TCODE_PROG_TRACE_CORRELATION 33

/* ===================================================================
 * MSEO encoding - 2-bit message sequence control
 * MSEO occupies bits [1:0] of each trace byte
 * =================================================================== */
#define MSEO_START_OR_MIDDLE         0x0  /* Start of message or middle of field */
#define MSEO_END_VAR_FIELD           0x1  /* End of variable-length field (not msg end) */
#define MSEO_RESERVED                0x2  /* Reserved - should not appear */
#define MSEO_END_MESSAGE             0x3  /* End of message or idle (when MDO=0x3F) */

/* Extract MSEO from a trace byte */
#define NTRACE_MSEO(byte)            ((byte) & 0x3)

/* Extract MDO from a trace byte (6 bits, [7:2]) */
#define NTRACE_MDO(byte)             (((byte) >> 2) & 0x3F)

/* Idle byte: MSEO=11, MDO=111111 */
#define NTRACE_IDLE_BYTE             0xFF

/* ===================================================================
 * Field maximum sizes (in bits)
 * =================================================================== */
#define NTRACE_MAX_TCODE_BITS        6
#define NTRACE_MAX_SRC_BITS          12
#define NTRACE_MAX_ICNT_BITS         22
#define NTRACE_MAX_ADDR_BITS         63   /* Full PC without LSB */
#define NTRACE_MAX_HIST_BITS         32   /* Includes stop-bit */
#define NTRACE_MAX_TSTAMP_BITS       64
#define NTRACE_MAX_HREPEAT_BITS      18
#define NTRACE_MAX_BCNT_BITS         18

/* ===================================================================
 * Fixed-size field widths
 * =================================================================== */
#define NTRACE_TCODE_WIDTH           6
#define NTRACE_BTYPE_WIDTH           2
#define NTRACE_SYNC_WIDTH            4
#define NTRACE_ETYPE_WIDTH           4
#define NTRACE_EVCODE_WIDTH          4
#define NTRACE_CDF_WIDTH             2
#define NTRACE_RCODE_WIDTH           4

/* ===================================================================
 * B-TYPE values - Branch type for indirect branches
 * =================================================================== */
#define BTYPE_INDIRECT_JUMP          0    /* Indirect jump/call/return or sync */
#define BTYPE_EXCEPTION_OR_INTERRUPT 1    /* Exception or interrupt (if can't distinguish) */
#define BTYPE_EXCEPTION              2    /* Exception (when distinguishable) */
#define BTYPE_INTERRUPT              3    /* Interrupt (when distinguishable) */

/* ===================================================================
 * SYNC values - Synchronization reason
 * =================================================================== */
#define SYNC_EXTERNAL_TRIGGER        0    /* External trace trigger */
#define SYNC_EXIT_RESET              1    /* Exit from reset */
#define SYNC_PERIODIC                2    /* Periodic synchronization */
#define SYNC_EXIT_DEBUG              3    /* Exit from debug mode */
#define SYNC_SEQ_ICNT_FULL           4    /* Sequential I-CNT full (BTM only) */
#define SYNC_TRACE_ENABLE            5    /* Trace re-enabled */
#define SYNC_TRACE_EVENT             6    /* Debug watchpoint (action=4) */
#define SYNC_FIFO_OVERRUN            7    /* Restart from FIFO overrun */
#define SYNC_POWER_DOWN              9    /* Exit from power-down */

/* ===================================================================
 * RCODE values - Resource full reason
 * =================================================================== */
#define RCODE_ICNT_FULL              0    /* I-CNT counter overflow */
#define RCODE_HIST_FULL              1    /* HIST register full */
#define RCODE_REPEAT_HIST            2    /* Repeated HIST pattern */

/* ===================================================================
 * ETYPE values - Error type
 * =================================================================== */
#define ETYPE_FIFO_OVERRUN           0    /* FIFO overrun */

/* ===================================================================
 * ECODE bits - Error code flags
 * =================================================================== */
#define ECODE_PROG_TRACE_LOST        (1 << 2)  /* Program trace message(s) lost */
#define ECODE_OWNERSHIP_LOST         (1 << 3)  /* Ownership trace message(s) lost */

/* ===================================================================
 * EVCODE values - Event code for ProgTraceCorrelation
 * =================================================================== */
#define EVCODE_HART_STOP             0    /* Hart halted (debug mode entry) */
#define EVCODE_TRACE_DISABLE         4    /* Trace disabled by filter */

/* ===================================================================
 * CDF values - Context Data Format for ProgTraceCorrelation
 * =================================================================== */
#define CDF_BTM_NO_HIST              0    /* BTM mode, no HIST */
#define CDF_HTM_WITH_HIST            1    /* HTM mode, contains HIST */

/* ===================================================================
 * PROCESS FORMAT values for Ownership message
 * =================================================================== */
#define PROCESS_FMT_PRV_ONLY         0    /* Only V/PRV fields */
#define PROCESS_FMT_SCONTEXT         2    /* Contains scontext */
#define PROCESS_FMT_HCONTEXT         3    /* Contains hcontext */

/* ===================================================================
 * Privilege encoding for Ownership PROCESS field
 * =================================================================== */
#define PRV_U                        0    /* User mode */
#define PRV_S                        1    /* Supervisor mode */
#define PRV_M                        3    /* Machine mode */

/* ===================================================================
 * HIST field helpers
 * =================================================================== */

/* Empty HIST: only stop-bit set (bit 0 = 1, all others = 0) */
#define HIST_EMPTY                   0x1

/* Extract stop-bit (MSB of HIST value) */
#define HIST_STOP_BIT(hist)          ((hist) != 0 && ((hist) & (1 << (31 - __builtin_clz(hist)))) != 0)

/* Count branch entries in HIST (excluding stop-bit) */
static inline unsigned hist_branch_count(uint32_t hist)
{
    if (hist == HIST_EMPTY)
        return 0;
    /* Number of bits minus 1 (stop-bit) */
    return (32 - __builtin_clz(hist)) - 1;
}

/* ===================================================================
 * I-CNT helpers
 * =================================================================== */

/* I-CNT increment for 16-bit instruction */
#define ICNT_16BIT_INSN              1

/* I-CNT increment for 32-bit instruction */
#define ICNT_32BIT_INSN              2

/* ===================================================================
 * Address compression helpers
 * =================================================================== */

/* Calculate U-ADDR from current and previous addresses */
#define CALC_UADDR(curr, prev)       (((curr) ^ (prev)) >> 1)

/* Reconstruct address from U-ADDR and previous address */
#define RECONSTRUCT_ADDR(uaddr, prev) (((uaddr) << 1) ^ (prev))

/* ===================================================================
 * Maximum message size
 * =================================================================== */
#define NTRACE_MAX_MSG_BYTES         38   /* IndirectBranchHistSync with all fields */

/* ===================================================================
 * Decoded message structure
 * =================================================================== */
typedef struct {
    uint8_t  tcode;           /* Message type (TCODE) */
    uint16_t src;             /* SRC field (if present), up to 12 bits */
    uint8_t  sync;            /* SYNC field (for sync messages) */
    uint8_t  btype;           /* B-TYPE (for indirect branches) */
    uint8_t  etype;           /* ETYPE (for Error) */
    uint8_t  evcode;          /* EVCODE (for ProgTraceCorrelation) */
    uint8_t  cdf;             /* CDF (for ProgTraceCorrelation) */
    uint8_t  rcode;           /* RCODE (for ResourceFull) */
    uint32_t icnt;            /* I-CNT value */
    uint64_t addr;            /* F-ADDR or U-ADDR */
    uint32_t hist;            /* HIST field (HTM mode) */
    uint64_t tstamp;          /* TSTAMP field */
    uint32_t bcnt;            /* B-CNT (for RepeatBranch) */
    uint32_t hrepeat;         /* HREPEAT (for ResourceFull RCODE=2) */
    uint32_t rdata[2];        /* RDATA for ResourceFull */
    uint8_t  process_fmt;     /* PROCESS FORMAT for Ownership */
    uint8_t  prv;             /* PRV field for Ownership */
    uint8_t  v;               /* V bit for Ownership */
    uint32_t scontext;        /* scontext for Ownership */
    uint32_t ecode;           /* ECODE for Error */
    bool     has_src;         /* Whether SRC field is present */
    bool     has_tstamp;      /* Whether TSTAMP field is present */
    bool     has_hist;        /* Whether HIST field is present */
    bool     is_full_addr;    /* true=F-ADDR, false=U-ADDR */
} ntrace_msg_t;

#endif /* NTRACE_ENCODING_H */
