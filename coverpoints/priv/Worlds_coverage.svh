///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Based on the RISC-V Worlds (World-ID) test plan
//
// SPDX-License-Identifier: Apache-2.0
//
// Description:
//   Coverage for the RISC-V Worlds extensions Smwid, Smlwid, Smlwidlist, Smwiddeleg and Sswid:
//   accesses to the mwid, mlwid, mlwidlist, mwiddeleg and slwid CSRs from each privilege mode,
//   the lock bit of mwid, and the software-check exceptions with xtval = illegal world fault (4)
//   raised when the WID of a privilege mode is not authorized.
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_WORLDS

`define ILLEGAL_WORLD_FAULT 4

covergroup Worlds_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // CSR accesses
    csrrw: coverpoint ins.current.insn {
        wildcard bins csrrs = {CSRRS};
        wildcard bins csrrw = {CSRRW};
    }
    csr: coverpoint ins.current.insn[31:20] {
        bins mwid      = {12'h749};
        bins mlwid     = {12'h390};
        bins mlwidlist = {12'h74A};
        bins mwiddeleg = {12'h748};
        bins slwid     = {12'h190};
    }
    mwid_access: coverpoint ins.current.insn[31:20] { bins mwid = {12'h749}; }
    mlwid_access: coverpoint ins.current.insn[31:20] { bins mlwid = {12'h390}; }
    mlwidlist_access: coverpoint ins.current.insn[31:20] { bins mlwidlist = {12'h74A}; }
    mwiddeleg_access: coverpoint ins.current.insn[31:20] { bins mwiddeleg = {12'h748}; }
    slwid_access: coverpoint ins.current.insn[31:20] { bins slwid = {12'h190}; }

    illegal: coverpoint ins.current.csr[12'h342] {
        bins illegal_instruction = {2};
    }
    software_check: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MCAUSE) {
        bins software_check = {18};
    }
    illegal_world_fault: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MTVAL) {
        bins illegal_world_fault = {`ILLEGAL_WORLD_FAULT};
    }
    mprv: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_CURRENT, CSR_MSTATUS, "mprv")[0] {
        bins set = {1};
    }
    mpp: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_CURRENT, CSR_MSTATUS, "mpp") {
        bins s = {1};
        bins u = {0};
    }
    load_store: coverpoint ins.current.insn {
        wildcard bins lw = {LW};
        wildcard bins sw = {SW};
    }
    mwid_lock: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MWID)[`XLEN-1] {
        bins locked = {1};
    }
    mwid_write: coverpoint ins.current.insn {
        wildcard bins csrrw_mwid = {32'b011101001001_?????_001_?????_1110011};
    }

    // Smwid
    cp_mwid_reset: cross priv_mode_m, csrrw, mwid_access;
    cp_mwid_warl: cross priv_mode_m, csrrw, mwid_access;
    cp_mwid_illegal_access: cross priv_mode_s_u, mwid_access, illegal;
    cp_mwid_lock: cross priv_mode_m, mwid_write, mwid_lock;

    // Smlwid
    cp_mlwid_reset: cross priv_mode_m, csrrw, mlwid_access;
    cp_mlwid_warl: cross priv_mode_m, csrrw, mlwid_access;
    cp_mlwid_fetch: cross priv_mode_s_u, software_check, illegal_world_fault;
    cp_mlwid_mprv: cross priv_mode_m, mprv, mpp, load_store, software_check, illegal_world_fault;
    cp_mlwid_illegal_access: cross priv_mode_s_u, mlwid_access, illegal;

    // Smlwidlist
    cp_mlwidlist_reset: cross priv_mode_m, csrrw, mlwidlist_access;
    cp_mlwidlist_warl: cross priv_mode_m, csrrw, mlwidlist_access;
    cp_mlwidlist_restricts: cross priv_mode_m_s_u, software_check, illegal_world_fault;
    cp_mlwidlist_lock: cross priv_mode_m, mwid_lock, csrrw, mlwidlist_access;

    // Smwiddeleg / Sswid
    cp_mwiddeleg_reset: cross priv_mode_m, csrrw, mwiddeleg_access;
    cp_sswid_disabled: cross priv_mode_m_s, slwid_access, illegal;
    cp_mwiddeleg_warl: cross priv_mode_m, csrrw, mwiddeleg_access;
    cp_mwiddeleg_subset_of_mlwidlist: cross priv_mode_m, csrrw, mlwidlist_access, mwiddeleg_access;
    cp_slwid_warl: cross priv_mode_m_s, csrrw, slwid_access;
    cp_slwid_fetch: cross priv_mode_m_u, software_check, illegal_world_fault;
    cp_mwiddeleg_illegal_access: cross priv_mode_s_u, csr, illegal;

endgroup

function void worlds_sample(int hart, int issue, ins_t ins);
    Worlds_cg.sample(ins);
endfunction
