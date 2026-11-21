/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 *
 * tsbi_proxy.c - T-SBI CSR / memory proxy engine (dynamic instruction injection)
 *
 * The T-SBI protocol hands the handler a COMPLETE instruction word in a0
 * (see tsbi.h SECTION 2/3).  The reference implementation's recommended way
 * to honour it (abstraction.adoc) is: write the word to memory, fence.i to
 * synchronise the instruction stream, execute it, and return to the test.
 * That is exactly what this file does.
 *
 * ERROR HANDLING - "Strategy A" (error flag + recovery):
 *   The injected instruction may fault on its own (non-existent CSR,
 *   insufficient privilege, unmapped MMIO...).  Before executing it we arm
 *   tsbi_proxy_record; if the nested trap arrives, the handler's P0 stage
 *   (the very first check, see trap.c) claims it, records the cause and
 *   redirects xEPC to `recover` - the point right after the injection call.
 *   The dispatch then returns TSBI_RESERVED_RET (-1) instead of letting the
 *   fault escape as an UNEXPECTED TRAP, which keeps negative tests alive.
 *
 *   This deliberately differs from the upstream reference implementation,
 *   which uses a static whitelist table in M-mode and halts the test on an
 *   unmatched encoding.  The protocol-visible contract is identical (a0 =
 *   encoding, a1 = argument, a0 = result); only the "how" differs, and the
 *   whitelist would remove our ability to assert on proxy failures.
 *
 * EXECUTABILITY: the test image is mapped RWX as a whole (no PMP execute
 * restriction), so a plain aligned static array is executable and no linker
 * script change is needed.
 */

#include "types.h"
#include "encoding.h"
#include "tsbi.h"

/* ===================================================================
 * Injection buffer and shared record
 *
 * Two words: the injected instruction followed by `ret` (jalr x0, ra, 0).
 * 16-byte aligned so the pair never straddles a cache/page boundary.
 * =================================================================== */
#define TSBI_RET_INSN   0x00008067u   /* ret == jalr x0, 0(ra) */

static uint32_t __attribute__((aligned(16))) tsbi_trampoline[2];

/* Shared with the handlers' P0 stage (declared in tsbi.h). */
tsbi_proxy_record_t tsbi_proxy_record;

/* ===================================================================
 * tsbi_proxy_faulted - did the most recent dispatch fault?
 *
 * Lets a negative test distinguish "proxy executed and returned -1 as the
 * CSR value" from "proxy could not execute the instruction at all".
 * =================================================================== */
bool tsbi_proxy_faulted(void)
{
    return tsbi_proxy_record.faulted;
}

/* ===================================================================
 * tsbi_csr_access_dispatch - execute a CSR instruction encoding
 *
 * @encoding: full CSR instruction word (TSBI_CSR_*_ENCODE)
 * @rs1_val : value handed to the instruction through a1 (WRITE/SET/CLEAR);
 *            ignored by READ, whose encoding uses rs1=x0
 *
 * Returns the CSR value for READ (the encoding puts rd=a0, so the result
 * lands directly in a0), or TSBI_RESERVED_RET if the injected instruction
 * faulted.  WRITE/SET/CLEAR encode rd=x0 and therefore have no meaningful
 * return value.
 *
 * NOTE: the caller (handler P2) is responsible for snapshotting its own
 * xstatus into tsbi_proxy_record.status_snap beforehand - only the handler
 * knows whether it runs in M (mstatus) or S/VS (sstatus) mode.  On the faulted
 * path P0 deliberately leaves xstatus alone (its xret has to resume the
 * handler, i.e. the .recover label below, at the SERVING level); the handler's
 * P2 then puts status_snap back once we have returned here, so the nested
 * trap's MPP/MPV overwrite cannot corrupt the privilege level the final xret
 * returns to.
 * =================================================================== */
uintptr_t tsbi_csr_access_dispatch(uint32_t encoding, uintptr_t rs1_val)
{
    /* Pre-set to the error value: on the recovery path the assembly below
     * never completes, so `result` must already hold something safe. */
    volatile uintptr_t result = TSBI_RESERVED_RET;

    tsbi_trampoline[0] = encoding;
    tsbi_trampoline[1] = TSBI_RET_INSN;
    asm volatile ("fence.i" ::: "memory");

    tsbi_proxy_record.armed   = true;
    tsbi_proxy_record.faulted = false;
    tsbi_proxy_record.cause   = 0;
    tsbi_proxy_record.recover = (uintptr_t)&&csr_done;

    {
        register uintptr_t _a1 asm("a1") = rs1_val;
        register uintptr_t _a0 asm("a0");
        /* a0 is an output only: READ's encoding writes it, the others leave
         * it alone (rd=x0).  ra is clobbered by the jalr. */
        asm volatile ("jalr ra, %2, 0"
                      : "=r"(_a0)
                      : "r"(_a1), "r"(tsbi_trampoline)
                      : "ra", "memory");
        result = _a0;
    }

csr_done:
    tsbi_proxy_record.armed = false;
    if (tsbi_proxy_record.faulted)
        return TSBI_RESERVED_RET;
    return result;
}

/* ===================================================================
 * tsbi_mem_access_dispatch - execute a memory-proxy instruction word
 *
 * @encoding: one of TSBI_LW / TSBI_LW4 / TSBI_LD / TSBI_SW / TSBI_SW4 /
 *            TSBI_SD (fixed words, see tsbi.h SECTION 3)
 * @addr    : physical address, handed over in a1 (the base register in all
 *            six encodings)
 * @val     : value to store, handed over in a2 (the stores encode rs2=a2);
 *            ignored by loads, whose encodings write a0 instead
 *
 * Returns the loaded value for loads, or TSBI_RESERVED_RET on a fault.  The
 * value returned for stores is meaningless.  Same Strategy-A protection as
 * the CSR path.
 *
 * This is what lets an S-mode test read mtime or poke MMIO that only the
 * serving level may touch.
 * =================================================================== */
uintptr_t tsbi_mem_access_dispatch(uint32_t encoding, uintptr_t addr,
                                   uintptr_t val)
{
    volatile uintptr_t result = TSBI_RESERVED_RET;

    tsbi_trampoline[0] = encoding;
    tsbi_trampoline[1] = TSBI_RET_INSN;
    asm volatile ("fence.i" ::: "memory");

    tsbi_proxy_record.armed   = true;
    tsbi_proxy_record.faulted = false;
    tsbi_proxy_record.cause   = 0;
    tsbi_proxy_record.recover = (uintptr_t)&&mem_done;

    {
        /* a1 = address (base register), a2 = value for the store forms,
         * a0 = loaded value for the load forms (output only). */
        register uintptr_t _a0 asm("a0");
        register uintptr_t _a1 asm("a1") = addr;
        register uintptr_t _a2 asm("a2") = val;
        asm volatile ("jalr ra, %3, 0"
                      : "=r"(_a0)
                      : "r"(_a1), "r"(_a2), "r"(tsbi_trampoline)
                      : "ra", "memory");
        result = _a0;
    }

mem_done:
    tsbi_proxy_record.armed = false;
    if (tsbi_proxy_record.faulted)
        return TSBI_RESERVED_RET;
    return result;
}
