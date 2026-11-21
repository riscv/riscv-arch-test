/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef HYP_CSR_H
#define HYP_CSR_H

/* ===================================================================
 * Hypervisor CSR helpers (G-stage subset)
 *
 * Thin wrappers around hgatp / hstatus / hedeleg / hideleg / henvcfg
 * needed by G-stage independent translation tests.
 *
 * All functions assume execution in M-mode or HS-mode (no V=1 access
 * checks performed in software – HW will trap as needed).
 * =================================================================== */

#include "hyp_defs.h"
#include "csr_ops.h"   /* M/S-level named accessors (single source) */

/* ----- hgatp ----- */
uintptr_t hgatp_read(void);

/* Spec-correct write: applies the WARL masking required by the
 * H-extension spec before issuing csrw:
 *   - MODE = Bare      → PPN and VMID are forced to zero
 *   - MODE = Sv*x4     → PPN[1:0] are forced to zero (16KB-aligned root)
 * This shim guarantees the caller-observable behaviour is spec-strict
 * even on implementations whose HW does not enforce these WARL
 * constraints itself (e.g. current QEMU `virt`). All normal callers
 * should use this. */
void      hgatp_write(uintptr_t value);

/* Raw write: no software masking, the value is written to hgatp
 * verbatim. Use ONLY for explicit WARL-probing test cases (e.g.
 * GHCSR-05 reserved-MODE rejection probing) that need to observe
 * unmodified hardware response. */
void      hgatp_write_raw(uintptr_t value);

void      hgatp_set(int mode, unsigned vmid, uintptr_t root_ppn);
void      hgatp_set_bare(void);

/* ----- hstatus ----- */
uintptr_t hstatus_read(void);
void      hstatus_write(uintptr_t value);
void      hstatus_set_spv(bool v);
void      hstatus_set_spvp(unsigned priv);
unsigned  hstatus_get_gva(void);
unsigned  hstatus_get_spv(void);

/* ----- hedeleg / hideleg ----- */
void      hedeleg_write(uintptr_t value);
uintptr_t hedeleg_read(void);
void      hideleg_write(uintptr_t value);
uintptr_t hideleg_read(void);

/* ----- henvcfg ----- */
void      henvcfg_write(uintptr_t value);
uintptr_t henvcfg_read(void);

/* Open the Smstateen ENVCFG gate so henvcfg/senvcfg are reachable from HS/VS
 * mode (see hyp_csr.c). A suite that manipulates envcfg from S(HS)-mode calls
 * this once from its setup; no-op when Smstateen is not declared. */
void      hyp_enable_envcfg_access(void);

/* ----- menvcfg / mstatus / senvcfg (M/S-level, non-H) -----
 * Provided by csr_ops.h (included above): menvcfg_read/write,
 * mstatus_read/write, senvcfg_read/write. */

/* ----- hcounteren / htimedelta (write-only, used by reset) ----- */
void      hcounteren_write(uintptr_t value);
void      htimedelta_write(uintptr_t value);

/* ----- HFENCE.GVMA all (rs1=x0, rs2=x0) ----- */
static inline void hfence_gvma_all(void) {
    /* hfence.gvma x0, x0  =>  0x62000073 */
    asm volatile (".word 0x62000073" ::: "memory");
}

/* ----- HFENCE.VVMA all (rs1=x0, rs2=x0) ----- */
static inline void hfence_vvma_all(void) {
    /* hfence.vvma x0, x0  =>  0x22000073 */
    asm volatile (".word 0x22000073" ::: "memory");
}

/* ===================================================================
 * hgatp mode probe
 * =================================================================== */

/**
 * hgatp_supports_mode - Test whether a given G-stage translation mode
 *                       is implemented on this platform.
 *
 * Writes the requested mode to hgatp (PPN=0, VMID=0), reads back,
 * then restores the original value. Returns true iff the MODE field
 * reads back as the requested value.
 *
 * This is the canonical "probe-and-restore" technique required by all
 * H sub-extension tests that need to condition test execution on
 * platform capabilities (Sv39x4 / Sv48x4 / Sv57x4 support).
 */
bool hgatp_supports_mode(int mode);

/* ===================================================================
 * hstatus field control
 * =================================================================== */

/* VTSR: VS-mode SRET triggers virtual-instruction exception */
void hstatus_set_vtsr(bool enable);

/* VTW: VS-mode WFI triggers virtual-instruction exception */
void hstatus_set_vtw(bool enable);

/* VTVM: VS-mode SFENCE.VMA/sinval.vma/satp access triggers virtual-inst */
void hstatus_set_vtvm(bool enable);

/* HU: allow U-mode to execute HLV/HLVX/HSV */
void hstatus_set_hu(bool enable);

/* ===================================================================
 * Trap delegation
 * =================================================================== */

/**
 * hyp_delegate_to_vs - Configure trap delegation to VS-mode
 *
 * First ensures medeleg/mideleg delegate to HS-mode, then writes
 * hedeleg/hideleg to further delegate to VS-mode.
 */
void hyp_delegate_to_vs(uintptr_t hedeleg_mask, uintptr_t hideleg_mask);

/**
 * hyp_undelegate - Clear all hypervisor delegation
 */
void hyp_undelegate(void);

/* ===================================================================
 * Virtual interrupt injection (hvip)
 * =================================================================== */

void hvip_set_vssi(bool pending);   /* VS software interrupt */
void hvip_set_vsti(bool pending);   /* VS timer interrupt */
void hvip_set_vsei(bool pending);   /* VS external interrupt */

/* hvip read/write */
uintptr_t hvip_read(void);
void      hvip_write(uintptr_t value);

/* ===================================================================
 * henvcfg fine-grained control
 * =================================================================== */

void henvcfg_set_pbmte(bool enable);  /* Svpbmt for VS-stage */
void henvcfg_set_adue(bool enable);   /* Hardware A/D update for VS-stage */
void henvcfg_set_stce(bool enable);   /* vstimecmp enable */

/* ===================================================================
 * hcounteren / htimedelta extended API
 * =================================================================== */

void hcounteren_set(uintptr_t mask);
void hcounteren_clear(uintptr_t mask);
uintptr_t hcounteren_read(void);
void htimedelta_set(uint64_t delta);

/* ===================================================================
 * mcounteren / scounteren (M/S-level)
 * Provided by csr_ops.h (included above). H-extension suites that need
 * the counter-access chain (mcounteren -> hcounteren -> scounteren)
 * still include hyp_csr.h for hcounteren below.
 * =================================================================== */

/* ===================================================================
 * vstvec (CSR 0x205) -- VS-mode trap vector
 *
 * Needed by shvstvecd tests (vectored VS interrupt delivery).
 * Accessed from HS/M-mode to configure VS-mode's trap entry point.
 * =================================================================== */

uintptr_t vstvec_read(void);
void      vstvec_write(uintptr_t value);
void      vstvec_set_mode(int mode);        /* VSTVEC_MODE_DIRECT/VECTORED */
uintptr_t vstvec_get_base(void);
int       vstvec_get_mode(void);

/* ===================================================================
 * vstval (CSR 0x243) -- VS-mode trap value
 *
 * Needed by shvstvala tests (VS trap value population).
 * =================================================================== */

uintptr_t vstval_read(void);
void      vstval_write(uintptr_t value);

/* ===================================================================
 * vsie (CSR 0x204) / vsip (CSR 0x244) -- VS-mode interrupt registers
 *
 * Direct HS/M-mode access for alias-chain verification tests.
 * =================================================================== */

uintptr_t vsie_read(void);
void      vsie_write(uintptr_t value);

uintptr_t vsip_read(void);
void      vsip_write(uintptr_t value);

/* ===================================================================
 * vsstatus (CSR 0x200) -- VS-mode status register
 *
 * Direct HS/M-mode access to vsstatus for field manipulation and
 * context-status verification (FS/VS/SD/UXL etc.).
 * =================================================================== */

uintptr_t vsstatus_read(void);
void      vsstatus_write(uintptr_t value);

/* Context-status field accessors (2-bit fields: FS, VS in vsstatus/mstatus).
 * @shift is the field's bit offset (e.g. SSTATUS_FS_SHIFT, SSTATUS_VS_SHIFT).
 * Returns/accepts the raw 2-bit value (0=Off, 1=Initial, 2=Clean, 3=Dirty). */
#define XSTATUS_FIELD_MASK  0x3UL

static inline unsigned vsstatus_get_field(unsigned shift) {
    return (unsigned)((vsstatus_read() >> shift) & XSTATUS_FIELD_MASK);
}

static inline void vsstatus_set_field(unsigned shift, unsigned val) {
    uintptr_t v = vsstatus_read();
    v = (v & ~(XSTATUS_FIELD_MASK << shift)) |
        ((uintptr_t)(val & XSTATUS_FIELD_MASK) << shift);
    vsstatus_write(v);
}

static inline unsigned mstatus_get_field(unsigned shift) {
    /* mstatus is M-level; under the T-SBI S-mode-normal model the hart
     * runs in HS-mode, so proxy the read. FS/VS survive the proxy ecall
     * (trap entry only rewrites the RETCTL bits MPP/MPIE/MIE). */
    return (unsigned)((tsbi_csr_read(CSR_MSTATUS) >> shift) & XSTATUS_FIELD_MASK);
}

static inline void mstatus_set_field(unsigned shift, unsigned val) {
    /* FS/VS are context-status config bits, not return-path RETCTL bits,
     * so they are proxy-safe: clear then set the 2-bit field. */
    uintptr_t mask = XSTATUS_FIELD_MASK << shift;
    tsbi_csr_clear(CSR_MSTATUS, mask);
    tsbi_csr_set(CSR_MSTATUS, (uintptr_t)(val & XSTATUS_FIELD_MASK) << shift);
}

/* ===================================================================
 * vsatp (CSR 0x280) -- VS-stage address translation
 *
 * Direct HS/M-mode access to vsatp for mode probing and configuration.
 * =================================================================== */

uintptr_t vsatp_read(void);
void      vsatp_write(uintptr_t value);

/* ===================================================================
 * satp (CSR 0x180) -- S-mode address translation
 *
 * Direct read/write for mode probing (from M-mode or with TVM=0).
 * =================================================================== */

uintptr_t satp_read(void);
void      satp_write(uintptr_t value);

/* ===================================================================
 * satp / vsatp mode probe (extends hgatp_supports_mode)
 * =================================================================== */

/**
 * satp_probe_mode - Write MODE to satp and return the whole satp read-back.
 *
 * Probe-and-restore, performed inside one M-mode excursion: satp translates
 * the mode that writes it, so probing a non-Bare MODE from S/HS-mode with
 * PPN=0 would fault on the next instruction fetch. M-mode fetches ignore
 * satp, so the write/read-back/restore sequence is safe there.
 *
 * Returns the satp value read back while the probe MODE was written; use
 * SATP_GET_MODE() on it to see which MODE stuck (an unsupported MODE makes
 * the write be ignored, so the previous value -- Bare -- reads back).
 */
uintptr_t satp_probe_mode(int mode);

/**
 * satp_supports_mode - Test whether satp supports a given MODE.
 *
 * Probe-and-restore via satp_probe_mode().
 * Per spec, writing an unsupported MODE causes the entire write to be
 * ignored (satp remains unchanged). So if read-back MODE matches the
 * requested value, it is supported.
 *
 * Callable from any privilege level.
 */
bool satp_supports_mode(int mode);

/**
 * vsatp_supports_mode - Test whether vsatp supports a given MODE.
 *
 * Same probe-and-restore technique, targets CSR 0x280 from HS/M-mode.
 * Per shvsatpa spec, vsatp must support the same set of modes as satp.
 */
bool vsatp_supports_mode(int mode);

/**
 * hgatp_mode_for_satp - Map satp SvNN mode to hgatp SvNNx4.
 *
 * Per shgatpa spec, for each satp SvNN the corresponding hgatp SvNNx4
 * must be supported. They share the same numeric encoding.
 */
static inline int hgatp_mode_for_satp(int satp_mode) {
    return satp_mode;
}

/* ===================================================================
 * ASID / VMID width probing
 *
 * Required by shvsatpa Group 6 (ASID width consistency).
 * =================================================================== */

unsigned satp_asid_width(void);
unsigned vsatp_asid_width(void);
unsigned hgatp_vmid_width(void);

/* ===================================================================
 * Counter implementation detection (shcounterenw)
 * =================================================================== */

uint32_t counteren_probe_implemented(void);
bool     hpmcounter_is_writable(int idx);

/* ===================================================================
 * Smstateen / Ssstateen CSR wrappers
 *
 * mstateen0-3 (M-mode: 0x30C-0x30F)
 * hstateen0-3 (HS-mode: 0x60C-0x60F)
 * sstateen0-3 (S-mode: 0x10C-0x10F; in VS-mode maps to vsstateen)
 *
 * Key semantics:
 *   - mstateen[n] bit 63 controls HS/VS/VU access to hstateen[n]
 *   - hstateen[n] bit 63 controls VS/VU access to sstateen[n]
 *   - When controlling bit=0, lower-priv access traps (illegal-inst
 *     or virtual-inst if V=1)
 * =================================================================== */

/* mstateen/hstateen/sstateen read/write/set_bits/clear_bits are provided
 * by csr_ops.h (included above). Only the bit-63 hierarchy convenience
 * wrappers remain here. */

/* Bit 63 convenience (hierarchy control) */
static inline void mstateen_set_bit63(int idx, bool enable) {
    /* mstateen0..3 are contiguous (0x30C..0x30F). Callers run in S(HS)-mode
     * where these M-level CSRs are unreachable, so proxy via tsbi_csr_*. */
    if (enable) tsbi_csr_set(CSR_MSTATEEN0 + idx, STATEEN_BIT63);
    else        tsbi_csr_clear(CSR_MSTATEEN0 + idx, STATEEN_BIT63);
}

static inline void hstateen_set_bit63(int idx, bool enable) {
    if (enable) hstateen_set_bits(idx, STATEEN_BIT63);
    else        hstateen_clear_bits(idx, STATEEN_BIT63);
}

/* Extension availability compile-time booleans (<EXT>_AVAILABLE, 1/0) are
 * centralized in common/capabilities.h, force-included into every translation
 * unit (see common/Makefile.common). SMSTATEEN_AVAILABLE, SSCSRIND_AVAILABLE
 * and SMCSRIND_AVAILABLE used to be defined here; they now come from there.
 * A suite that touches the stateen CSRs must still launch the simulator with
 * the declared extension (e.g. Spike _smstateen). */

/* ===================================================================
 * Indirect CSR accessors (Smcsrind / Sscsrind / Ssccfg)
 *
 * The miselect/mireg, siselect/sireg* and vsiselect/vsireg* plain
 * CSRR/CSRW wrappers are provided by csr_ops.h (included above).
 * Trap-armed probing variants (e.g. *_read_safe) stay suite-local.
 * =================================================================== */

/* ===================================================================
 * Generic atomic set/clear bit helpers (single CSRS/CSRC instruction)
 *
 * H-level only (henvcfg/hvip/hstatus/vsstatus). The M/S-level
 * menvcfg/senvcfg set_bits/clear_bits are provided by csr_ops.h.
 * =================================================================== */

void henvcfg_set_bits(uintptr_t mask);
void henvcfg_clear_bits(uintptr_t mask);
void hvip_set_bits(uintptr_t mask);
void hvip_clear_bits(uintptr_t mask);
void hstatus_set_bits(uintptr_t mask);
void hstatus_clear_bits(uintptr_t mask);
void vsstatus_set_bits(uintptr_t mask);
void vsstatus_clear_bits(uintptr_t mask);

/* ===================================================================
 * Sstc timer CSRs and hip / htimedelta read accessors
 * =================================================================== */

uintptr_t stimecmp_read(void);
void      stimecmp_write(uintptr_t v);
uintptr_t vstimecmp_read(void);
void      vstimecmp_write(uintptr_t v);
uintptr_t time_read(void);
uintptr_t hip_read(void);
uintptr_t htimedelta_read(void);

#endif /* HYP_CSR_H */
