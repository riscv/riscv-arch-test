///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
// SPMP (S-level Physical Memory Protection) Test Suite
//
// Copyright (C) 2026 RISC-V International
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SSPMPSM
`define SSPMP_LAST_SELECTOR (12'h100 + `UDB_NUM_PMP_ENTRIES - 1)
`define SSPMP_FIRST_OOB_SELECTOR (12'h100 + `UDB_NUM_PMP_ENTRIES)

///////////////////////////////////////////
// CSR Access Covergroup
///////////////////////////////////////////
covergroup SspmpSm_csr_cg with function sample(ins_t ins);
    option.per_instance = 0;

    `include "general/RISCV_coverage_standard_coverpoints.svh"

    //------------------------------------------
    // cp_spmp_indirect_access: Test indirect CSR access via siselect/sireg/sireg2
    // Covers: writing siselect with SPMP range values (0x100-0x13F),
    //         then reading/writing sireg (spmpaddr) and sireg2 (spmpcfg)
    //------------------------------------------
    siselect_val: coverpoint ins.current.csr[12'h150] {
        bins spmp_entry[4] = {[12'h100:`SSPMP_LAST_SELECTOR]};
    }

    cp_spmp_indirect_access: coverpoint ins.current.insn iff
        ((ins.current.insn[31:20] inside {12'h150, 12'h151, 12'h152}) &&
         (ins.current.csr[12'h150] inside {[12'h100:`SSPMP_LAST_SELECTOR]})) {
        wildcard bins csrrw_sireg  = {CSRRW};
        wildcard bins csrrs_sireg  = {CSRRS};
        wildcard bins csrrc_sireg  = {CSRRC};
    }

    //------------------------------------------
    // cp_spmpaddr_write: Write and readback spmpaddr via sireg
    //------------------------------------------
    cp_spmpaddr_write: coverpoint ins.current.csr[12'h151] iff
        (ins.current.csr[12'h150] >= 12'h100 &&
         ins.current.csr[12'h150] <= `SSPMP_LAST_SELECTOR) {
        bins addr_zero = {0};
        bins addr_nonzero = {[1:$]};
    }

    //------------------------------------------
    // cp_spmpcfg_write: Write and readback spmpcfg via sireg2
    // Tracks each address-matching mode through the A field.
    //------------------------------------------
    cp_spmpcfg_write: coverpoint ins.current.csr[12'h152][4:3] iff
        (ins.current.csr[12'h150] >= 12'h100 &&
         ins.current.csr[12'h150] <= `SSPMP_LAST_SELECTOR) {
        // A field encodings (bits [4:3])
        bins a_off   = {2'b00};
        bins a_tor   = {2'b01};
        bins a_na4   = {2'b10};
        bins a_napot = {2'b11};
    }

    //------------------------------------------
    // cp_spmp_lock: Setting the L bit
    //------------------------------------------
    cp_spmp_lock: coverpoint ins.current.csr[12'h152][7] iff
        (ins.current.csr[12'h150] >= 12'h100 &&
         ins.current.csr[12'h150] <= `SSPMP_LAST_SELECTOR) {
        bins locked = {1};
        bins unlocked = {0};
    }

    //------------------------------------------
    // cp_spmp_lock_write_ignored: Writes to locked entry via siselect are ignored
    //------------------------------------------
    cp_spmp_lock_write_ignored: coverpoint {
        ins.current.insn[14:12],
        ((ins.current.insn[31:20] == 12'h151 &&
          ins.prev.csr[12'h151] == ins.current.csr[12'h151]) ||
         (ins.current.insn[31:20] == 12'h152 &&
          ins.prev.csr[12'h152] == ins.current.csr[12'h152]))
    } iff (ins.prev.csr[12'h152][7] == 1 &&
           ins.current.csr[12'h150] >= 12'h100 &&
           ins.current.csr[12'h150] <= `SSPMP_LAST_SELECTOR &&
           ins.current.insn[31:20] inside {12'h151, 12'h152} &&
           (ins.current.insn[14:12] == 3'b001 ||
            (ins.current.insn[14:12] inside {3'b010, 3'b011} &&
             ins.current.rs1_val != '0))) {
        bins locked_csrrw = {4'b001_1};
        bins locked_csrrs = {4'b010_1};
        bins locked_csrrc = {4'b011_1};
    }

    //------------------------------------------
    // cp_spmp_lock_tor_prevaddr: Locked TOR entry also locks previous spmpaddr
    //------------------------------------------
    cp_spmp_lock_tor_prevaddr: coverpoint {
        ins.current.insn[14:12],
        (ins.prev.csr[12'h151] == ins.current.csr[12'h151])
    } iff (ins.current.insn[31:20] == 12'h151 &&
           ins.current.csr[12'h150] == 12'h101) {
        // The test has already locked entry 2 in TOR mode. Selecting entry 1
        // hides entry 2's cfg from sireg2, so observe the required effect:
        // a CSRRW to entry 1's spmpaddr leaves its value unchanged.
        bins locked_tor_prevaddr_write_ignored = {4'b001_1};
    }

    //------------------------------------------
    // Building blocks for siselect OOB differentiation.
    // siselect_oob:   tells us we are hitting an out-of-bounds SPMP index.
    // csr_op_type:    read (CSRRS rs1=x0) vs write (CSRRW/CSRRS/CSRRC with non-zero rs1).
    // sireg_read_val: captured read value of sireg/sireg2 during the OOB access.
    //------------------------------------------
    siselect_oob: coverpoint ins.current.csr[12'h150] {
        type_option.weight = 0;
        `ifndef UDB_NUM_PMP_ENTRIES_64
            bins unimplemented_entry = {[`SSPMP_FIRST_OOB_SELECTOR:12'h13F]};
        `endif
        bins reserved_selector = {[12'h140:12'h1FF]};
    }

    csr_op_type: coverpoint ins.current.insn[14:12] {
        type_option.weight = 0;
        // funct3=010 is CSRRS; when used via CSRR(...) macro rs1=x0, it is a pure read.
        // Tests generated by the SPMP testgen use CSRR for reads and CSRW (CSRRW with
        // rd=x0, funct3=001) for writes, so funct3 alone cleanly separates read/write.
        bins read_op  = {3'b010};
        bins write_op = {3'b001, 3'b011, 3'b101, 3'b110, 3'b111};
    }

    sireg_read_val_zero: coverpoint ins.current.csr[12'h151] iff
        (((ins.current.csr[12'h150] >= `SSPMP_FIRST_OOB_SELECTOR) &&
          (ins.current.csr[12'h150] <= 12'h13F)) ||
         (ins.current.csr[12'h150] inside {[12'h140:12'h1FF]})) {
        type_option.weight = 0;
        bins read_zero = {0};
    }

    //------------------------------------------
    // cp_spmp_oob_read_zero: Out-of-bounds siselect reads must return zero
    //   Maps to normative rule: siselect_oob_access
    //------------------------------------------
    cp_spmp_oob_read_zero: cross siselect_oob, csr_op_type, sireg_read_val_zero {
        bins oob_read_returns_zero = binsof(csr_op_type.read_op) &&
                                     binsof(sireg_read_val_zero.read_zero);
        ignore_bins not_read = binsof(csr_op_type.write_op);
    }

    //------------------------------------------
    // cp_spmp_oob_write_ignored: Out-of-bounds siselect writes must be silently ignored
    //   Maps to normative rule: siselect_oob_access
    //   The readback after an OOB write still returns zero (no state change).
    //------------------------------------------
    cp_spmp_oob_write_ignored: cross siselect_oob, csr_op_type, sireg_read_val_zero {
        bins oob_write_no_state_change = binsof(csr_op_type.write_op) &&
                                         binsof(sireg_read_val_zero.read_zero);
        ignore_bins not_write = binsof(csr_op_type.read_op);
    }

    //------------------------------------------
    // Building blocks for mpmpdeleg.pmpnum differentiation.
    // pmpnum_val:    the written pmpnum value.
    // delegation_active: inferred from pmpnum != number_of_writable_pmp_entries.
    //                pmpnum below the implemented PMP count delegates at least one entry.
    // spmp_access_result: whether a subsequent SPMP access returned zero (no delegation)
    //                or a real value (delegation active).
    //------------------------------------------
    pmpnum_val: coverpoint ins.current.csr[12'h316][6:0] {
        type_option.weight = 0;
        bins zero       = {0};
        bins partial[4] = {[1:(`UDB_NUM_PMP_ENTRIES-1)]};
        bins max        = {[`UDB_NUM_PMP_ENTRIES:$]};
    }

    delegation_active: coverpoint ins.current.csr[12'h316][6:0] {
        type_option.weight = 0;
        bins delegating     = {[0:(`UDB_NUM_PMP_ENTRIES-1)]};
        bins not_delegating = {[`UDB_NUM_PMP_ENTRIES:$]};
    }

    // Sample the SPMP readback value (sireg) to classify as zero (no delegation)
    // or non-zero (delegation live).
    spmp_access_result: coverpoint ins.current.csr[12'h151] {
        type_option.weight = 0;
        bins spmp_zero     = {0};
        bins spmp_nonzero  = {[1:$]};
    }

    //------------------------------------------
    // cp_mpmpdeleg_pmpnum_field: general pmpnum WARL field coverage
    //   Maps to normative rule: mpmpdeleg_pmpnum_field
    //------------------------------------------
    cp_mpmpdeleg_pmpnum_field: coverpoint ins.current.csr[12'h316][6:0] {
        bins zero_all_delegated = {0};
        bins partial[4]         = {[1:(`UDB_NUM_PMP_ENTRIES-1)]};
        bins max_none_delegated = {[`UDB_NUM_PMP_ENTRIES:$]};
    }

    //------------------------------------------
    // cp_mpmpdeleg_pmpnum_zero: explicit pmpnum=0 (all entries delegated)
    //   Crosses pmpnum=0 with a delegated SPMP read returning non-zero state.
    //   Maps to normative rule: mpmpdeleg_pmpnum_zero_delegates_all
    //------------------------------------------
    cp_mpmpdeleg_pmpnum_zero: cross pmpnum_val, delegation_active, spmp_access_result {
        bins zero_and_delegating = binsof(pmpnum_val.zero) &&
                                   binsof(delegation_active.delegating) &&
                                   binsof(spmp_access_result.spmp_nonzero);
    }

    //------------------------------------------
    // cp_mpmpdeleg_no_delegation: pmpnum=max disables SPMP; SPMP reads return zero.
    //   Maps to normative rule: mpmpdeleg_no_delegation_disables
    //------------------------------------------
    cp_mpmpdeleg_no_delegation: cross pmpnum_val, delegation_active, spmp_access_result {
        bins max_no_deleg_reads_zero = binsof(pmpnum_val.max) &&
                                       binsof(delegation_active.not_delegating) &&
                                       binsof(spmp_access_result.spmp_zero);
    }

    //------------------------------------------
    // cp_mpmpdeleg_locked: Cannot set pmpnum below locked PMP entry
    //------------------------------------------
    `ifdef XLEN64
        pmp7_locked: coverpoint ins.current.csr[12'h3A0][63] {
            type_option.weight = 0;
            bins locked = {1};
        }
    `else
        pmp7_locked: coverpoint ins.current.csr[12'h3A1][31] {
            type_option.weight = 0;
            bins locked = {1};
        }
    `endif

    pmpnum_write_request: coverpoint ins.current.rs1_val[6:0] iff
        (ins.current.insn[31:20] == 12'h316 && ins.current.insn[14:12] == 3'b001) {
        type_option.weight = 0;
        bins below_locked_pmp7 = {7'd4};
        bins architectural_max = {7'd64};
    }

    pmpnum_write_readback: coverpoint ins.current.csr[12'h316][6:0] iff
        (ins.current.insn[31:20] == 12'h316 && ins.current.insn[14:12] == 3'b001) {
        type_option.weight = 0;
        bins no_delegation = {[`UDB_NUM_PMP_ENTRIES:$]};
    }

    pmpnum_write_unchanged: coverpoint
        (ins.prev.csr[12'h316][6:0] == ins.current.csr[12'h316][6:0]) iff
        (ins.current.insn[31:20] == 12'h316 && ins.current.insn[14:12] == 3'b001) {
        type_option.weight = 0;
        bins changed = {0};
        bins ignored = {1};
    }

    cp_mpmpdeleg_locked: cross pmp7_locked, pmpnum_write_request,
                                pmpnum_write_readback, pmpnum_write_unchanged {
        bins architectural_max_allowed = binsof(pmp7_locked.locked) &&
                                         binsof(pmpnum_write_request.architectural_max) &&
                                         binsof(pmpnum_write_readback.no_delegation);
        bins below_locked_entry_rejected = binsof(pmp7_locked.locked) &&
                                           binsof(pmpnum_write_request.below_locked_pmp7) &&
                                           binsof(pmpnum_write_unchanged.ignored);
    }

    //------------------------------------------
    // cp_sfence_ordering: SFENCE.VMA x0,x0 after an SPMP CSR write.
    //   Per Spec §2.7: software must execute SFENCE.VMA rs1=x0,rs2=x0 to order
    //   subsequent S/U memory accesses against preceding SPMP CSR writes.
    //   We look for an SFENCE.VMA whose previous instruction wrote sireg/sireg2
    //   with siselect in the SPMP range (i.e. touched an SPMP CSR via the
    //   indirect-access path).  spmpen writes are not modelled here because
    //   this covergroup samples siselect state, not the prev instruction's
    //   target CSR address.
    //   Maps to normative rule: sspmp_sfence_vma_ordering
    //------------------------------------------
    sfence_vma_insn: coverpoint ins.current.insn {
        type_option.weight = 0;
        // SFENCE.VMA encoding: funct7=0001001, rs2, rs1, funct3=000, rd=00000, opcode=1110011
        // With rs1=x0, rs2=x0 the rs1/rs2 fields are zero.
        wildcard bins sfence_x0_x0 = {32'b0001001_00000_00000_000_00000_1110011};
    }

    prev_wrote_spmp_csr: coverpoint ins.prev.insn[31:20] iff
        (ins.prev.csr[12'h150] inside {[12'h100:`SSPMP_LAST_SELECTOR]}) {
        type_option.weight = 0;
        bins prev_sireg  = {12'h151};
        bins prev_sireg2 = {12'h152};
    }

    cp_sfence_ordering: cross sfence_vma_insn, prev_wrote_spmp_csr {
        bins sfence_after_spmp_write = binsof(sfence_vma_insn.sfence_x0_x0) &&
                                       (binsof(prev_wrote_spmp_csr.prev_sireg) ||
                                        binsof(prev_wrote_spmp_csr.prev_sireg2));
    }

    //------------------------------------------
    // cp_mmode_indirect_access: M-mode access to SPMP via miselect/mireg
    //------------------------------------------
    cp_mmode_indirect_access: coverpoint ins.current.csr[12'h350] iff
        (ins.prev.mode == 2'b11) {
        bins spmp_range[4] = {[12'h100:`SSPMP_LAST_SELECTOR]};
    }

    //------------------------------------------
    // cp_spmp_lock_clear_mmode: M-mode can clear L bit via miselect
    //------------------------------------------
    cp_spmp_lock_clear_mmode: coverpoint {
        ins.prev.csr[12'h352][7],
        ins.current.csr[12'h352][7]
    } iff (ins.prev.mode == 2'b11 &&
           ins.current.insn[31:20] == 12'h352 &&
           ins.current.insn[14:12] == 3'b001 &&
           ins.current.csr[12'h350] >= 12'h100 &&
           ins.current.csr[12'h350] <= `SSPMP_LAST_SELECTOR) {
        bins clear_lock = {2'b10};  // was locked, now unlocked
    }

endgroup

///////////////////////////////////////////
// Permission Enforcement Covergroup
///////////////////////////////////////////
covergroup SspmpSm_perm_cg with function sample(ins_t ins);
    option.per_instance = 0;

    `include "general/RISCV_coverage_standard_coverpoints.svh"

    //------------------------------------------
    // Access type building block
    //------------------------------------------
    access_type: coverpoint ins.current.trap {
        type_option.weight = 0;
        bins no_trap = {0};
        bins trap    = {1};
    }

    //------------------------------------------
    // cp_smode_rule: S-mode-only rule (SHARED=0, U=0)
    // S-mode: Enforced with R/W/X permissions
    // U-mode: Denied
    //------------------------------------------
    smode_rule_rwx: coverpoint ins.current.csr[12'h152][2:0] iff
        (ins.current.csr[12'h152][9] == 0 &&
         ins.current.csr[12'h152][8] == 0) {
        type_option.weight = 0;
        // The spec names encodings as RWX; csr[2:0] is physically {X,W,R}.
        bins r_only = {3'b001};
        bins rw     = {3'b011};
        bins rx     = {3'b101};
        bins rwx    = {3'b111};
        bins x_only = {3'b100};
    }

    cp_smode_rule: cross smode_rule_rwx, priv_mode_s_u, access_type;

    //------------------------------------------
    // cp_umode_rule: U-mode rule (SHARED=0, U=1)
    // U-mode: Enforced
    // S-mode (SUM=1): EnforceNoX
    // S-mode (SUM=0): Denied
    //------------------------------------------
    umode_rule_rwx: coverpoint ins.current.csr[12'h152][2:0] iff
        (ins.current.csr[12'h152][9] == 0 &&
         ins.current.csr[12'h152][8] == 1) {
        type_option.weight = 0;
        bins r_only = {3'b001};
        bins rw     = {3'b011};
        bins rx     = {3'b101};
        bins rwx    = {3'b111};
        bins x_only = {3'b100};
    }

    cp_umode_rule: cross umode_rule_rwx, priv_mode_u, access_type;

    //------------------------------------------
    // SUM/EnforceNoX differentiation.
    // Per Spec §2.4 & Figure 4:
    //   - U-mode rule + SUM=0 + S-mode access  -> Deny (fault=yes)
    //   - U-mode rule + SUM=1 + S-mode R/W     -> Enforce (fault=no)
    //   - U-mode rule + SUM=1 + S-mode X       -> EnforceNoX (fault=yes on fetch)
    //
    // cp_sum_effect maps to the "sum_effect" rule: SUM=1 enables S-mode data access.
    // cp_enforce_no_x maps to "enforceNoX": SUM=1 still denies S-mode execute.
    // cp_sum_denied  maps to the SUM=0 deny case (implicitly exercises both rules).
    //------------------------------------------
    sum_bit: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "sum")[0] {
        type_option.weight = 0;
        bins sum_0 = {0};
        bins sum_1 = {1};
    }

    // Was the access an instruction fetch (X) or data (R/W)?  Detect by cause:
    //   12 = instruction page fault, 13 = load page fault, 15 = store page fault.
    x_access_faulted: coverpoint ins.current.csr[12'h142] iff (ins.current.trap == 1) {
        type_option.weight = 0;
        bins fetch_fault = {12};
    }
    data_access_outcome: coverpoint ins.current.trap {
        type_option.weight = 0;
        bins no_trap = {0};
        bins trap    = {1};
    }

    // cp_sum_effect: SUM=1 ∧ S-mode data access ∧ no trap  (data goes through)
    // Any U-mode rule with R=1 allows S-mode data access under SUM=1: r_only,
    // rw, rx, and rwx all qualify.  x_only (R=0) would still trap on load, so
    // it is excluded.
    cp_sum_effect: cross umode_rule_rwx, sum_bit, priv_mode_s, data_access_outcome {
        bins sum1_data_allowed = binsof(sum_bit.sum_1) &&
                                 binsof(priv_mode_s) &&
                                 binsof(data_access_outcome.no_trap) &&
                                 (binsof(umode_rule_rwx.r_only) ||
                                  binsof(umode_rule_rwx.rw)     ||
                                  binsof(umode_rule_rwx.rx)     ||
                                  binsof(umode_rule_rwx.rwx));
    }

    // cp_enforce_no_x: SUM=1 ∧ S-mode instruction fetch ∧ fetch fault  (X denied)
    cp_enforce_no_x: cross umode_rule_rwx, sum_bit, priv_mode_s, x_access_faulted {
        bins sum1_fetch_denied = binsof(sum_bit.sum_1) &&
                                 binsof(priv_mode_s) &&
                                 binsof(x_access_faulted.fetch_fault) &&
                                 (binsof(umode_rule_rwx.rx) ||
                                  binsof(umode_rule_rwx.rwx) ||
                                  binsof(umode_rule_rwx.x_only));
    }

    // cp_sum_denied: SUM=0 ∧ S-mode access ∧ trap  (entire U-mode region inaccessible)
    cp_sum_denied: cross umode_rule_rwx, sum_bit, priv_mode_s, data_access_outcome {
        bins sum0_smode_denied = binsof(sum_bit.sum_0) &&
                                 binsof(priv_mode_s) &&
                                 binsof(data_access_outcome.trap);
    }

    //------------------------------------------
    // cp_mxr_effect: MXR bit effect (Make eXecutable Readable)
    //------------------------------------------
    mxr_bit: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "mxr")[0] {
        type_option.weight = 0;
        bins mxr_0 = {0};
        bins mxr_1 = {1};
    }

    cp_mxr_effect: cross smode_rule_rwx, mxr_bit, access_type;

    //------------------------------------------
    // cp_shared_rule: Shared-Region rule (SHARED=1, U=1)
    // Both S and U mode: Enforced
    // RWX=000: Enforce/Enforce (no access)
    // RWX=100: Enforce/Enforce
    // RWX=110: Enforce/Read-only
    // RWX=001: Enforce/Enforce
    // RWX=101: Enforce/Enforce
    // RWX=111: Enforce/Exec-only
    //------------------------------------------
    shared_rule_rwx: coverpoint ins.current.csr[12'h152][2:0] iff
        (ins.current.csr[12'h152][9] == 1 &&
         ins.current.csr[12'h152][8] == 1) {
        type_option.weight = 0;
        bins none     = {3'b000};
        bins r_only   = {3'b001};
        bins rw       = {3'b011};
        bins x_only   = {3'b100};
        bins rx       = {3'b101};
        bins rwx      = {3'b111};
    }

    cp_shared_rule: cross shared_rule_rwx, priv_mode_s_u, access_type;

    //------------------------------------------
    // cp_shared_sum_ignored: Shared-region S-mode data access is independent
    // of sstatus.SUM. The generator performs the same permitted load with
    // SUM clear and set.
    //------------------------------------------
    shared_sum_load_insn: coverpoint ins.current.insn {
        type_option.weight = 0;
        wildcard bins lw = {LW};
    }

    cp_shared_sum_ignored: cross shared_rule_rwx, sum_bit, priv_mode_s,
                                  shared_sum_load_insn, data_access_outcome {
        bins sum0_load_allowed = binsof(shared_rule_rwx.r_only) &&
                                 binsof(sum_bit.sum_0) &&
                                 binsof(priv_mode_s) &&
                                 binsof(shared_sum_load_insn.lw) &&
                                 binsof(data_access_outcome.no_trap);
        bins sum1_load_allowed = binsof(shared_rule_rwx.r_only) &&
                                 binsof(sum_bit.sum_1) &&
                                 binsof(priv_mode_s) &&
                                 binsof(shared_sum_load_insn.lw) &&
                                 binsof(data_access_outcome.no_trap);
    }

    //------------------------------------------
    // cp_reserved_encoding: conceptual RWX=010/011 are reserved.
    // In the physical {X,W,R} slice these are 010 and 110 respectively.
    //------------------------------------------
    cp_reserved_encoding: coverpoint ins.current.csr[12'h152][2:0] iff
        (ins.current.csr[12'h150] >= 12'h100 &&
         ins.current.csr[12'h150] <= `SSPMP_LAST_SELECTOR) {
        bins rwx_010 = {3'b010};
        bins rwx_011 = {3'b110};
    }

    //------------------------------------------
    // cp_no_match_deny: No matching entry denies access
    //------------------------------------------
    cp_no_match_deny: coverpoint ins.current.trap iff
        (ins.prev.mode != 2'b11) {  // Not M-mode
        bins denied = {1};
    }

    //------------------------------------------
    // SPMP fault coverpoints (page fault exception codes)
    //------------------------------------------
    cp_spmp_fault_instr: coverpoint ins.current.csr[12'h142] iff (ins.current.trap == 1) {
        bins instr_page_fault = {12};
    }

    cp_spmp_fault_load: coverpoint ins.current.csr[12'h142] iff (ins.current.trap == 1) {
        bins load_page_fault = {13};
    }

    cp_spmp_fault_store: coverpoint ins.current.csr[12'h142] iff (ins.current.trap == 1) {
        bins store_page_fault = {15};
    }

    //------------------------------------------
    // cp_mmode_bypass: M-mode memory access bypasses SPMP
    //------------------------------------------
    cp_mmode_bypass: coverpoint ins.current.trap iff
        (ins.prev.mode == 2'b11) {
        bins no_trap = {0};
    }

endgroup

///////////////////////////////////////////
// Address Matching Covergroup
///////////////////////////////////////////
covergroup SspmpSm_addr_cg with function sample(ins_t ins);
    option.per_instance = 0;

    `include "general/RISCV_coverage_standard_coverpoints.svh"

    //------------------------------------------
    // cp_addr_match_off: A=OFF, entry is disabled
    //------------------------------------------
    cp_addr_match_off: coverpoint ins.current.csr[12'h152][4:3] iff
        (ins.current.csr[12'h150] >= 12'h100 &&
         ins.current.csr[12'h150] <= `SSPMP_LAST_SELECTOR) {
        bins off = {2'b00};
    }

    //------------------------------------------
    // cp_addr_match_tor: A=TOR, top-of-range matching
    //------------------------------------------
    cp_addr_match_tor: coverpoint ins.current.csr[12'h152][4:3] iff
        (ins.current.csr[12'h150] >= 12'h100 &&
         ins.current.csr[12'h150] <= `SSPMP_LAST_SELECTOR) {
        bins tor = {2'b01};
    }

    //------------------------------------------
    // cp_addr_match_na4: A=NA4, naturally aligned 4-byte region
    //------------------------------------------
    cp_addr_match_na4: coverpoint ins.current.csr[12'h152][4:3] iff
        (ins.current.csr[12'h150] >= 12'h100 &&
         ins.current.csr[12'h150] <= `SSPMP_LAST_SELECTOR) {
        bins na4 = {2'b10};
    }

    //------------------------------------------
    // cp_addr_match_napot: A=NAPOT, naturally aligned power-of-two region
    //------------------------------------------
    cp_addr_match_napot: coverpoint ins.current.csr[12'h152][4:3] iff
        (ins.current.csr[12'h150] >= 12'h100 &&
         ins.current.csr[12'h150] <= `SSPMP_LAST_SELECTOR) {
        bins napot = {2'b11};
    }

    //------------------------------------------
    // cp_addr_match_tor_entry0: TOR on entry 0 (implicit lower bound = 0)
    //   Spec §2.3: "Particularly, if spmpcfg[0].A is set to TOR, zero is used for the lower bound."
    //   Maps to normative rule: spmpcfg-a_tor_entry0
    //------------------------------------------
    siselect_entry0: coverpoint ins.current.csr[12'h150] {
        type_option.weight = 0;
        bins entry0 = {12'h100};
    }
    cp_addr_match_tor_entry0: cross siselect_entry0, cp_addr_match_tor {
        bins tor_on_entry0 = binsof(siselect_entry0.entry0) &&
                             binsof(cp_addr_match_tor);
    }

    //------------------------------------------
    // Priority/match differentiation.
    //
    // match_priority: "lowest-numbered SPMP entry that matches any byte of an access
    //                 ... determines whether that access is allowed or denied."
    //                 (Spec §2.5.2)
    // match_irrespective_perm_bits: "matching is done irrespective of the SHARED, U,
    //                                R, W, and X bits."  (Spec §2.5.4)
    //
    // These are orthogonal:
    //   - match_priority is about WHICH entry wins when multiple match.
    //   - match_irrespective_perm_bits is about WHETHER an entry matches at all
    //     (the address-match decision ignores RWX).
    //------------------------------------------
    // Which SPMP entry is currently selected (proxy for entry_index).
    entry_index: coverpoint ins.current.csr[12'h150] {
        type_option.weight = 0;
        bins entry0 = {12'h100};
        bins entry1 = {12'h101};
        bins higher = {[12'h102:`SSPMP_LAST_SELECTOR]};
    }

    // RWX bit combinations of the current spmpcfg value.
    perm_bits: coverpoint ins.current.csr[12'h152][2:0] {
        type_option.weight = 0;
        bins rwx_none = {3'b000};
        bins rwx_r    = {3'b001};
        bins rwx_rw   = {3'b011};
        bins rwx_rx   = {3'b101};
        bins rwx_rwx  = {3'b111};
    }

    match_result: coverpoint ins.current.trap {
        type_option.weight = 0;
        bins deny  = {1};
        bins allow = {0};
    }

    // cp_priority_match: first-match-wins behaviour when multiple entries cover the
    // same region.  Cross entry_index × match_result exercises the priority decision.
    //   Maps to normative rule: match_priority
    cp_priority_match: cross entry_index, match_result {
        bins entry0_wins_deny = binsof(entry_index.entry0) && binsof(match_result.deny);
        bins entry1_after_entry0_off = binsof(entry_index.entry1) && binsof(match_result.allow);
        ignore_bins higher_entries = binsof(entry_index.higher);
    }

    // cp_match_irrespective_perm_bits: address-match decision is independent of RWX.
    // Cross entry_index × perm_bits × match_result demonstrates that the same address
    // matches regardless of whether RWX bits are set.
    //   Maps to normative rule: match_irrespective_perm_bits
    cp_match_irrespective_perm_bits: cross entry_index, perm_bits, match_result {
        bins match_rwx_none = binsof(perm_bits.rwx_none) && binsof(match_result.deny);
        bins match_rwx_rw   = binsof(perm_bits.rwx_rw);
        bins match_rwx_rx   = binsof(perm_bits.rwx_rx);
        bins match_rwx_rwx  = binsof(perm_bits.rwx_rwx);
    }

endgroup

///////////////////////////////////////////
// SPMP and Paging Covergroup
///////////////////////////////////////////
covergroup SspmpSm_paging_cg with function sample(ins_t ins);
    option.per_instance = 0;

    //------------------------------------------
    // cp_satp_bare_spmp: satp.mode == Bare with Sspmp active
    //------------------------------------------
    cp_satp_bare_spmp: coverpoint ins.current.csr[12'h180] {
        `ifdef XLEN64
            bins bare_mode = {0} with (item[63:60] == 4'b0000);
        `else
            bins bare_mode = {0} with (item[31] == 1'b0);
        `endif
    }

endgroup

///////////////////////////////////////////
// Sspmpen (spmpen CSR) Covergroup
///////////////////////////////////////////
covergroup SspmpSm_spmpen_cg with function sample(ins_t ins);
    option.per_instance = 0;

    `include "general/RISCV_coverage_standard_coverpoints.svh"

    //------------------------------------------
    // cp_spmpen_readwrite: Basic read/write of spmpen register
    // Covers: write all-ones / zero / individual bits and readback
    //------------------------------------------
    cp_spmpen_readwrite: coverpoint ins.current.csr[12'h183] {
        bins all_zeros = {0};
        `ifdef XLEN64
            bins all_ones = {64'hFFFF_FFFF_FFFF_FFFF};
            bins bit0     = {64'h1};
            bins bit1     = {64'h2};
            bins bit2     = {64'h4};
            bins bit3     = {64'h8};
        `else
            bins all_ones = {32'hFFFF_FFFF};
            bins bit0     = {32'h1};
            bins bit1     = {32'h2};
            bins bit2     = {32'h4};
            bins bit3     = {32'h8};
        `endif
        bins other[4]  = default;
    }

    //------------------------------------------
    // cp_spmpenh_readwrite: RV32 alias for spmpen[63:32]
    //------------------------------------------
    `ifndef XLEN64
        cp_spmpenh_readwrite: coverpoint ins.current.csr[12'h193] {
            bins all_zeros = {32'h0000_0000};
            bins all_ones  = {32'hFFFF_FFFF};
            bins other[4]  = default;
        }
    `endif

    //------------------------------------------
    // cp_spmpen_activation: Entry active iff spmpen[i] & spmpcfg[i].A != 0
    // Tests toggling spmpen[i] with A=NAPOT and A=OFF
    //------------------------------------------
    spmpen_entry0_enabled: coverpoint ins.current.csr[12'h183][0] {
        type_option.weight = 0;
        bins disabled = {0};
        bins enabled  = {1};
    }

    spmpen_entry0_a: coverpoint ins.current.csr[12'h152][4:3] iff
        (ins.current.csr[12'h150] == 12'h100) {
        type_option.weight = 0;
        bins off   = {2'b00};
        bins napot = {2'b11};
    }

    spmpen_load_insn: coverpoint ins.current.insn {
        type_option.weight = 0;
        wildcard bins lw = {LW};
    }

    spmpen_access_outcome: coverpoint ins.current.trap {
        type_option.weight = 0;
        bins allowed = {0};
        bins denied  = {1};
    }

    cp_spmpen_activation: cross spmpen_entry0_enabled, spmpen_entry0_a,
                                 priv_mode_s, spmpen_load_insn, spmpen_access_outcome {
        bins disabled_napot_allows = binsof(spmpen_entry0_enabled.disabled) &&
                                     binsof(spmpen_entry0_a.napot) &&
                                     binsof(priv_mode_s) &&
                                     binsof(spmpen_load_insn.lw) &&
                                     binsof(spmpen_access_outcome.allowed);
        bins enabled_napot_denies = binsof(spmpen_entry0_enabled.enabled) &&
                                    binsof(spmpen_entry0_a.napot) &&
                                    binsof(priv_mode_s) &&
                                    binsof(spmpen_load_insn.lw) &&
                                    binsof(spmpen_access_outcome.denied);
        bins enabled_off_allows = binsof(spmpen_entry0_enabled.enabled) &&
                                  binsof(spmpen_entry0_a.off) &&
                                  binsof(priv_mode_s) &&
                                  binsof(spmpen_load_insn.lw) &&
                                  binsof(spmpen_access_outcome.allowed);
    }

    //------------------------------------------
    // cp_spmpen_locked_readonly: spmpen[i] is read-only when spmpcfg[i].L == 1.
    // A write attempt (CSRRC to clear, or CSRRW) targeting CSR_SPMPEN while
    // the selected SPMP entry is locked must be silently rejected -- the bit
    // retains its previous value.
    //
    // We sample on instructions that target CSR_SPMPEN (insn[31:20] == 0x183)
    // while miselect points at the locked entry (entry 1 in the test):
    //   * locked_csrrc_attempt: funct3=011 (CSRRC) with L=1 and spmpen[1]=1 --
    //     the clear was attempted and the bit stayed set (rejection observed).
    //   * locked_bit_still_set: funct3=010 (CSRRS-read via `csrr rd, spmpen`)
    //     with L=1 and spmpen[1]=1 -- the post-rejection verification read
    //     confirms the locked bit is still set.
    //
    // The earlier "locked_clear = 2'b10" bin was unreachable under correct
    // hardware (a rejected clear leaves the bit set), so detection moved to
    // the CSR-write-attempt itself rather than the resulting bit value.
    //------------------------------------------
    cp_spmpen_locked_readonly: coverpoint {
        ins.current.insn[14:12],       // funct3: 001=CSRRW, 010=CSRRS/read, 011=CSRRC
        ins.current.csr[12'h352][7],   // L bit of currently-selected SPMP entry (via mireg2)
        ins.current.csr[12'h183][1]    // spmpen[1]
    } iff (ins.current.insn[31:20] == 12'h183 &&               // insn targets CSR_SPMPEN
           ins.current.csr[12'h350] == 12'h101) {              // miselect = SPMP entry 1
        bins locked_csrrc_attempt = {5'b011_1_1};  // CSRRC attempt; bit stayed set
        bins locked_bit_still_set = {5'b010_1_1};  // CSRR verifies bit is still 1
    }

endgroup

///////////////////////////////////////////
// Sample function
///////////////////////////////////////////
function void sspmpsm_sample(int hart, int issue, ins_t ins);
    SspmpSm_csr_cg.sample(ins);
    SspmpSm_perm_cg.sample(ins);
    SspmpSm_addr_cg.sample(ins);
    SspmpSm_paging_cg.sample(ins);
    SspmpSm_spmpen_cg.sample(ins);
endfunction

`undef SSPMP_LAST_SELECTOR
`undef SSPMP_FIRST_OOB_SELECTOR
