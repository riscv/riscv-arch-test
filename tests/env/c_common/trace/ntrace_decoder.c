/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 *
 * N-Trace message decoder implementation.
 */

#include "ntrace_decoder.h"

/* ===================================================================
 * Bit extraction helpers
 * =================================================================== */

/*
 * Extract bits from a byte stream.
 * data: pointer to start of byte array
 * bit_offset: bit offset from start (LSB first within each byte)
 * num_bits: number of bits to extract (max 64)
 * Returns extracted value.
 */
static uint64_t extract_bits(const uint8_t *data, size_t bit_offset, int num_bits)
{
    uint64_t result = 0;
    size_t byte_idx = bit_offset / 8;
    int bit_idx = bit_offset % 8;

    for (int i = 0; i < num_bits; i++) {
        size_t curr_byte = byte_idx + (bit_idx + i) / 8;
        int curr_bit = (bit_idx + i) % 8;

        if (data[curr_byte] & (1 << curr_bit))
            result |= (1ULL << i);
    }

    return result;
}

/* ===================================================================
 * Variable-length field decoder
 *
 * N-Trace variable-length fields use MSEO to indicate continuation:
 * - MSEO=00 or MSEO=01: field continues or ends
 * - MSEO=11: end of message (also ends field)
 *
 * Each byte contributes 6 bits of data (MDO) and 2 bits of control (MSEO).
 * =================================================================== */

/*
 * Decode a variable-length field.
 * Returns number of bytes consumed, or -1 on error.
 * value: output decoded value
 * bits_decoded: output number of bits in value
 * is_end_of_msg: output true if field ended with MSEO=11
 */
static int decode_varlen_field(const uint8_t *data, size_t len, uint64_t *value,
                              int *bits_decoded, bool *is_end_of_msg)
{
    uint64_t result = 0;
    int bits = 0;
    size_t pos = 0;

    while (pos < len) {
        uint8_t byte = data[pos];
        uint8_t mseo = NTRACE_MSEO(byte);
        uint8_t mdo = NTRACE_MDO(byte);

        /* Check for reserved MSEO */
        if (mseo == MSEO_RESERVED)
            return -1;

        /* Extract 6 bits of data */
        if (bits < 64) {
            result |= ((uint64_t)mdo << bits);
            bits += 6;
        }

        pos++;

        /* Check field/message end */
        if (mseo == MSEO_END_MESSAGE) {
            if (is_end_of_msg)
                *is_end_of_msg = true;
            break;
        }

        if (mseo == MSEO_END_VAR_FIELD) {
            if (is_end_of_msg)
                *is_end_of_msg = false;
            break;
        }

        /* MSEO=00: continue to next byte */
    }

    *value = result;
    *bits_decoded = bits;
    return pos;
}

/*
 * Decode a fixed-width field (no MSEO interpretation).
 * Returns number of bytes consumed.
 */
static int decode_fixed_field(const uint8_t *data, size_t len, int num_bits,
                             uint64_t *value)
{
    int num_bytes = (num_bits + 5) / 6;  /* Round up to whole bytes */

    if ((size_t)num_bytes > len)
        return -1;

    *value = 0;
    for (int i = 0; i < num_bytes; i++) {
        uint8_t mdo = NTRACE_MDO(data[i]);
        *value |= ((uint64_t)mdo << (i * 6));
    }

    /* Mask to exact bit width */
    if (num_bits < 64)
        *value &= ((1ULL << num_bits) - 1);

    return num_bytes;
}

/* ===================================================================
 * Skip idle bytes
 * =================================================================== */
static size_t skip_idle(const uint8_t *data, size_t len)
{
    size_t pos = 0;
    while (pos < len && data[pos] == NTRACE_IDLE_BYTE)
        pos++;
    return pos;
}

/* ===================================================================
 * Message decoder
 * =================================================================== */

void ntrace_decoder_init(ntrace_decoder_ctx_t *ctx, const uint8_t *data, size_t len,
                        uint8_t src_bits, bool has_tstamp)
{
    ctx->data = data;
    ctx->len = len;
    ctx->pos = 0;
    ctx->prev_addr = 0;
    ctx->prev_tstamp = 0;
    ctx->src_bits = src_bits;
    ctx->has_tstamp = has_tstamp;
}

bool ntrace_decode_next(ntrace_decoder_ctx_t *ctx, ntrace_msg_t *msg)
{
    if (ctx->pos >= ctx->len)
        return false;

    /* Skip idle bytes */
    ctx->pos += skip_idle(ctx->data + ctx->pos, ctx->len - ctx->pos);

    if (ctx->pos >= ctx->len)
        return false;

    const uint8_t *start = ctx->data + ctx->pos;
    size_t remaining = ctx->len - ctx->pos;
    size_t offset = 0;

    /* Initialize message */
    msg->has_src = (ctx->src_bits > 0);
    msg->has_tstamp = ctx->has_tstamp;
    msg->has_hist = false;
    msg->is_full_addr = false;

    /* ---- Decode TCODE (always first field, 6 bits fixed) ---- */
    int consumed = decode_fixed_field(start + offset, remaining - offset,
                                     NTRACE_TCODE_WIDTH, (uint64_t *)&msg->tcode);
    if (consumed < 0)
        return false;
    offset += consumed;

    /* ---- Decode SRC (if present, fixed-length, width = src_bits) ----
     * Per RISC-V N-Trace Spec (Unified N-Trace Message Structure):
     * SRC is a fixed-length field, not a variable-length field. It must
     * always consume exactly src_bits of MDO data regardless of MSEO bits.
     */
    if (msg->has_src) {
        uint64_t src_val;
        consumed = decode_fixed_field(start + offset, remaining - offset,
                                     ctx->src_bits, &src_val);
        if (consumed < 0)
            return false;
        msg->src = (uint16_t)src_val;
        offset += consumed;
    }

    /* ---- Decode message-specific fields based on TCODE ---- */
    switch (msg->tcode) {

    case TCODE_OWNERSHIP: {
        /* PROCESS field (variable-length) */
        uint64_t process;
        int proc_bits;
        bool end_msg;
        consumed = decode_varlen_field(start + offset, remaining - offset,
                                      &process, &proc_bits, &end_msg);
        if (consumed < 0)
            return false;
        offset += consumed;

        /* Extract FORMAT (low 2 bits) */
        msg->process_fmt = process & 0x3;
        msg->prv = (process >> 2) & 0x3;
        msg->v = (process >> 4) & 0x1;

        /* Extract scontext if FORMAT=10 */
        if (msg->process_fmt == PROCESS_FMT_SCONTEXT)
            msg->scontext = (uint32_t)(process >> 5);

        if (end_msg)
            break;
        break;
    }

    case TCODE_DIRECT_BRANCH: {
        /* I-CNT (variable-length) */
        uint64_t icnt;
        int icnt_bits;
        bool end_msg;
        consumed = decode_varlen_field(start + offset, remaining - offset,
                                      &icnt, &icnt_bits, &end_msg);
        if (consumed < 0)
            return false;
        msg->icnt = (uint32_t)icnt;
        offset += consumed;
        if (end_msg)
            break;
        break;
    }

    case TCODE_INDIRECT_BRANCH: {
        /* B-TYPE (2 bits fixed) */
        uint64_t btype;
        consumed = decode_fixed_field(start + offset, remaining - offset,
                                     NTRACE_BTYPE_WIDTH, &btype);
        if (consumed < 0)
            return false;
        msg->btype = (uint8_t)btype;
        offset += consumed;

        /* I-CNT (variable-length) */
        uint64_t icnt;
        int icnt_bits;
        bool end_msg;
        consumed = decode_varlen_field(start + offset, remaining - offset,
                                      &icnt, &icnt_bits, &end_msg);
        if (consumed < 0)
            return false;
        msg->icnt = (uint32_t)icnt;
        offset += consumed;
        if (end_msg)
            break;

        /* U-ADDR (variable-length, XOR-compressed address).
         * Keep raw U-ADDR in msg->addr for test verification; update the
         * decoder's previous address to the reconstructed full PC so that
         * subsequent U-ADDR fields can be decoded correctly. */
        uint64_t uaddr;
        int addr_bits;
        consumed = decode_varlen_field(start + offset, remaining - offset,
                                      &uaddr, &addr_bits, &end_msg);
        if (consumed < 0)
            return false;
        msg->addr = uaddr;
        msg->is_full_addr = false;
        ctx->prev_addr = (uaddr << 1) ^ ctx->prev_addr;
        offset += consumed;
        if (end_msg)
            break;
        break;
    }

    case TCODE_ERROR: {
        /* ETYPE (4 bits fixed) */
        uint64_t etype;
        consumed = decode_fixed_field(start + offset, remaining - offset,
                                     NTRACE_ETYPE_WIDTH, &etype);
        if (consumed < 0)
            return false;
        msg->etype = (uint8_t)etype;
        offset += consumed;

        /* ECODE (variable-length) */
        uint64_t ecode;
        int ecode_bits;
        bool end_msg;
        consumed = decode_varlen_field(start + offset, remaining - offset,
                                      &ecode, &ecode_bits, &end_msg);
        if (consumed < 0)
            return false;
        msg->ecode = (uint32_t)ecode;
        offset += consumed;
        if (end_msg)
            break;
        break;
    }

    case TCODE_PROG_TRACE_SYNC:
    case TCODE_DIRECT_BRANCH_SYNC: {
        /* SYNC (4 bits fixed) */
        uint64_t sync;
        consumed = decode_fixed_field(start + offset, remaining - offset,
                                     NTRACE_SYNC_WIDTH, &sync);
        if (consumed < 0)
            return false;
        msg->sync = (uint8_t)sync;
        offset += consumed;

        /* I-CNT (variable-length) */
        uint64_t icnt;
        int icnt_bits;
        bool end_msg;
        consumed = decode_varlen_field(start + offset, remaining - offset,
                                      &icnt, &icnt_bits, &end_msg);
        if (consumed < 0)
            return false;
        msg->icnt = (uint32_t)icnt;
        offset += consumed;
        if (end_msg)
            break;

        /* F-ADDR (variable-length, full address).
         * Per N-Trace Spec, F-ADDR is PC >> 1; reconstruct full PC. */
        uint64_t faddr;
        int addr_bits;
        consumed = decode_varlen_field(start + offset, remaining - offset,
                                      &faddr, &addr_bits, &end_msg);
        if (consumed < 0)
            return false;
        msg->addr = faddr << 1;
        msg->is_full_addr = true;
        /* Sync messages reset the decoder's previous address reference so that
         * subsequent U-ADDR fields are XOR-decompressed relative to the sync
         * address. */
        ctx->prev_addr = msg->addr;
        offset += consumed;
        if (end_msg)
            break;
        break;
    }

    case TCODE_INDIRECT_BRANCH_SYNC: {
        /* SYNC (4 bits fixed) */
        uint64_t sync;
        consumed = decode_fixed_field(start + offset, remaining - offset,
                                     NTRACE_SYNC_WIDTH, &sync);
        if (consumed < 0)
            return false;
        msg->sync = (uint8_t)sync;
        offset += consumed;

        /* B-TYPE (2 bits fixed) */
        uint64_t btype;
        consumed = decode_fixed_field(start + offset, remaining - offset,
                                     NTRACE_BTYPE_WIDTH, &btype);
        if (consumed < 0)
            return false;
        msg->btype = (uint8_t)btype;
        offset += consumed;

        /* I-CNT (variable-length) */
        uint64_t icnt;
        int icnt_bits;
        bool end_msg;
        consumed = decode_varlen_field(start + offset, remaining - offset,
                                      &icnt, &icnt_bits, &end_msg);
        if (consumed < 0)
            return false;
        msg->icnt = (uint32_t)icnt;
        offset += consumed;
        if (end_msg)
            break;

        /* F-ADDR (variable-length, full address).
         * Per N-Trace Spec, F-ADDR is PC >> 1; reconstruct full PC. */
        uint64_t faddr;
        int addr_bits;
        consumed = decode_varlen_field(start + offset, remaining - offset,
                                      &faddr, &addr_bits, &end_msg);
        if (consumed < 0)
            return false;
        msg->addr = faddr << 1;
        msg->is_full_addr = true;
        /* Sync messages reset the previous address reference. */
        ctx->prev_addr = msg->addr;
        offset += consumed;
        if (end_msg)
            break;
        break;
    }

    case TCODE_RESOURCE_FULL: {
        /* RCODE (4 bits fixed) */
        uint64_t rcode;
        consumed = decode_fixed_field(start + offset, remaining - offset,
                                     NTRACE_RCODE_WIDTH, &rcode);
        if (consumed < 0)
            return false;
        msg->rcode = (uint8_t)rcode;
        offset += consumed;

        /* RDATA[0] (variable-length) */
        uint64_t rdata0;
        int rdata0_bits;
        bool end_msg;
        consumed = decode_varlen_field(start + offset, remaining - offset,
                                      &rdata0, &rdata0_bits, &end_msg);
        if (consumed < 0)
            return false;
        msg->rdata[0] = (uint32_t)rdata0;
        offset += consumed;
        if (end_msg)
            break;

        /* RDATA[1] for RCODE=2 (variable-length, optional) */
        if (msg->rcode == RCODE_REPEAT_HIST) {
            uint64_t rdata1;
            int rdata1_bits;
            consumed = decode_varlen_field(start + offset, remaining - offset,
                                          &rdata1, &rdata1_bits, &end_msg);
            if (consumed < 0)
                return false;
            msg->rdata[1] = (uint32_t)rdata1;
            msg->hrepeat = (uint32_t)rdata1;
            offset += consumed;
            if (end_msg)
                break;
        }
        break;
    }

    case TCODE_INDIRECT_BRANCH_HIST: {
        /* B-TYPE (2 bits fixed) */
        uint64_t btype;
        consumed = decode_fixed_field(start + offset, remaining - offset,
                                     NTRACE_BTYPE_WIDTH, &btype);
        if (consumed < 0)
            return false;
        msg->btype = (uint8_t)btype;
        offset += consumed;

        /* I-CNT (variable-length) */
        uint64_t icnt;
        int icnt_bits;
        bool end_msg;
        consumed = decode_varlen_field(start + offset, remaining - offset,
                                      &icnt, &icnt_bits, &end_msg);
        if (consumed < 0)
            return false;
        msg->icnt = (uint32_t)icnt;
        offset += consumed;
        if (end_msg)
            break;

        /* U-ADDR (variable-length) */
        uint64_t uaddr;
        int addr_bits;
        consumed = decode_varlen_field(start + offset, remaining - offset,
                                      &uaddr, &addr_bits, &end_msg);
        if (consumed < 0)
            return false;
        msg->addr = uaddr;
        msg->is_full_addr = false;
        offset += consumed;
        if (end_msg)
            break;

        /* HIST (variable-length) */
        uint64_t hist;
        int hist_bits;
        consumed = decode_varlen_field(start + offset, remaining - offset,
                                      &hist, &hist_bits, &end_msg);
        if (consumed < 0)
            return false;
        msg->hist = (uint32_t)hist;
        msg->has_hist = true;
        offset += consumed;
        if (end_msg)
            break;
        break;
    }

    case TCODE_INDIRECT_BRANCH_HIST_SYNC: {
        /* SYNC (4 bits fixed) */
        uint64_t sync;
        consumed = decode_fixed_field(start + offset, remaining - offset,
                                     NTRACE_SYNC_WIDTH, &sync);
        if (consumed < 0)
            return false;
        msg->sync = (uint8_t)sync;
        offset += consumed;

        /* B-TYPE (2 bits fixed) */
        uint64_t btype;
        consumed = decode_fixed_field(start + offset, remaining - offset,
                                     NTRACE_BTYPE_WIDTH, &btype);
        if (consumed < 0)
            return false;
        msg->btype = (uint8_t)btype;
        offset += consumed;

        /* I-CNT (variable-length) */
        uint64_t icnt;
        int icnt_bits;
        bool end_msg;
        consumed = decode_varlen_field(start + offset, remaining - offset,
                                      &icnt, &icnt_bits, &end_msg);
        if (consumed < 0)
            return false;
        msg->icnt = (uint32_t)icnt;
        offset += consumed;
        if (end_msg)
            break;

        /* F-ADDR (variable-length, full address).
         * Per N-Trace Spec, F-ADDR is PC >> 1; reconstruct full PC. */
        uint64_t faddr;
        int addr_bits;
        consumed = decode_varlen_field(start + offset, remaining - offset,
                                      &faddr, &addr_bits, &end_msg);
        if (consumed < 0)
            return false;
        msg->addr = faddr << 1;
        msg->is_full_addr = true;
        /* Sync messages reset the previous address reference. */
        ctx->prev_addr = msg->addr;
        offset += consumed;
        if (end_msg)
            break;

        /* HIST (variable-length) */
        uint64_t hist;
        int hist_bits;
        consumed = decode_varlen_field(start + offset, remaining - offset,
                                      &hist, &hist_bits, &end_msg);
        if (consumed < 0)
            return false;
        msg->hist = (uint32_t)hist;
        msg->has_hist = true;
        offset += consumed;
        if (end_msg)
            break;
        break;
    }

    case TCODE_REPEAT_BRANCH: {
        /* B-CNT (variable-length) */
        uint64_t bcnt;
        int bcnt_bits;
        bool end_msg;
        consumed = decode_varlen_field(start + offset, remaining - offset,
                                      &bcnt, &bcnt_bits, &end_msg);
        if (consumed < 0)
            return false;
        msg->bcnt = (uint32_t)bcnt;
        offset += consumed;
        if (end_msg)
            break;
        break;
    }

    case TCODE_PROG_TRACE_CORRELATION: {
        /* EVCODE (4 bits fixed) */
        uint64_t evcode;
        consumed = decode_fixed_field(start + offset, remaining - offset,
                                     NTRACE_EVCODE_WIDTH, &evcode);
        if (consumed < 0)
            return false;
        msg->evcode = (uint8_t)evcode;
        offset += consumed;

        /* CDF (2 bits fixed) */
        uint64_t cdf;
        consumed = decode_fixed_field(start + offset, remaining - offset,
                                     NTRACE_CDF_WIDTH, &cdf);
        if (consumed < 0)
            return false;
        msg->cdf = (uint8_t)cdf;
        offset += consumed;

        /* I-CNT (variable-length) */
        uint64_t icnt;
        int icnt_bits;
        bool end_msg;
        consumed = decode_varlen_field(start + offset, remaining - offset,
                                      &icnt, &icnt_bits, &end_msg);
        if (consumed < 0)
            return false;
        msg->icnt = (uint32_t)icnt;
        offset += consumed;
        if (end_msg)
            break;

        /* HIST (variable-length, only if CDF=1) */
        if (msg->cdf == CDF_HTM_WITH_HIST) {
            uint64_t hist;
            int hist_bits;
            consumed = decode_varlen_field(start + offset, remaining - offset,
                                          &hist, &hist_bits, &end_msg);
            if (consumed < 0)
                return false;
            msg->hist = (uint32_t)hist;
            msg->has_hist = true;
            offset += consumed;
            if (end_msg)
                break;
        }
        break;
    }

    default:
        /* Unknown TCODE - skip to end of message */
        while (offset < remaining) {
            uint8_t mseo = NTRACE_MSEO(start[offset]);
            offset++;
            if (mseo == MSEO_END_MESSAGE)
                break;
        }
        break;
    }

    /* ---- Decode optional TSTAMP (if enabled and not end of message) ---- */
    if (msg->has_tstamp) {
        uint64_t tstamp;
        int tstamp_bits;
        bool end_msg;
        consumed = decode_varlen_field(start + offset, remaining - offset,
                                      &tstamp, &tstamp_bits, &end_msg);
        if (consumed > 0) {
            msg->tstamp = tstamp;
            offset += consumed;
        }
    }

    ctx->pos += offset;

    /* Update decoder state */
    if (msg->is_full_addr)
        ctx->prev_addr = msg->addr;  /* msg->addr is already reconstructed PC */

    if (msg->has_tstamp)
        ctx->prev_tstamp = msg->tstamp;

    return true;
}

int ntrace_decode_stream(const uint8_t *data, size_t len, ntrace_msg_t *msgs,
                        int max_msgs, uint8_t src_bits, bool has_tstamp)
{
    ntrace_decoder_ctx_t ctx;
    ntrace_decoder_init(&ctx, data, len, src_bits, has_tstamp);

    int count = 0;
    while (count < max_msgs && ntrace_decode_next(&ctx, &msgs[count]))
        count++;

    return count;
}

int ntrace_find_by_tcode(const ntrace_msg_t *msgs, int count, uint8_t tcode,
                        ntrace_msg_t *results, int max_results)
{
    int found = 0;
    for (int i = 0; i < count && found < max_results; i++) {
        if (msgs[i].tcode == tcode)
            results[found++] = msgs[i];
    }
    return found;
}

int ntrace_count_tcode(const ntrace_msg_t *msgs, int count, uint8_t tcode)
{
    int cnt = 0;
    for (int i = 0; i < count; i++) {
        if (msgs[i].tcode == tcode)
            cnt++;
    }
    return cnt;
}

const char *ntrace_tcode_name(uint8_t tcode)
{
    switch (tcode) {
    case TCODE_OWNERSHIP:              return "Ownership";
    case TCODE_DIRECT_BRANCH:          return "DirectBranch";
    case TCODE_INDIRECT_BRANCH:        return "IndirectBranch";
    case TCODE_ERROR:                  return "Error";
    case TCODE_PROG_TRACE_SYNC:        return "ProgTraceSync";
    case TCODE_DIRECT_BRANCH_SYNC:     return "DirectBranchSync";
    case TCODE_INDIRECT_BRANCH_SYNC:   return "IndirectBranchSync";
    case TCODE_RESOURCE_FULL:          return "ResourceFull";
    case TCODE_INDIRECT_BRANCH_HIST:   return "IndirectBranchHist";
    case TCODE_INDIRECT_BRANCH_HIST_SYNC: return "IndirectBranchHistSync";
    case TCODE_REPEAT_BRANCH:          return "RepeatBranch";
    case TCODE_PROG_TRACE_CORRELATION: return "ProgTraceCorrelation";
    default:                           return "Unknown";
    }
}
