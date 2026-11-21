/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 *
 * N-Trace message decoder API.
 */

#ifndef NTRACE_DECODER_H
#define NTRACE_DECODER_H

#include "types.h"
#include "ntrace_encoding.h"

/* ===================================================================
 * Decoder state for stream processing
 * =================================================================== */
typedef struct {
    const uint8_t *data;     /* Raw trace data */
    size_t         len;      /* Total data length */
    size_t         pos;      /* Current position */
    uint64_t       prev_addr; /* Previous address for U-ADDR reconstruction */
    uint64_t       prev_tstamp; /* Previous timestamp for relative TSTAMP */
    uint8_t        src_bits; /* SRC field width (from config) */
    bool           has_tstamp; /* Whether timestamps are enabled */
} ntrace_decoder_ctx_t;

/* ===================================================================
 * Decoder API
 * =================================================================== */

/*
 * Initialize decoder context.
 * src_bits: width of SRC field (0 if not present)
 * has_tstamp: whether TSTAMP fields are enabled
 */
void ntrace_decoder_init(ntrace_decoder_ctx_t *ctx, const uint8_t *data, size_t len,
                        uint8_t src_bits, bool has_tstamp);

/*
 * Decode next message from stream.
 * Returns true if a message was decoded, false if no more data.
 */
bool ntrace_decode_next(ntrace_decoder_ctx_t *ctx, ntrace_msg_t *msg);

/*
 * Decode entire trace stream into message array.
 * Returns number of messages decoded (up to max_msgs).
 */
int ntrace_decode_stream(const uint8_t *data, size_t len, ntrace_msg_t *msgs,
                        int max_msgs, uint8_t src_bits, bool has_tstamp);

/*
 * Helper: Find messages with specific TCODE in decoded array.
 * Returns count of matching messages.
 */
int ntrace_find_by_tcode(const ntrace_msg_t *msgs, int count, uint8_t tcode,
                        ntrace_msg_t *results, int max_results);

/*
 * Helper: Count messages with specific TCODE.
 */
int ntrace_count_tcode(const ntrace_msg_t *msgs, int count, uint8_t tcode);

/*
 * Helper: Get TCODE name string.
 */
const char *ntrace_tcode_name(uint8_t tcode);

#endif /* NTRACE_DECODER_H */
