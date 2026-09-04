///////////////////////////////////////////
//
// Common mcontrol6 configuration coverpoints, shared by the SdtrigSm
// mcontrol6-based covergroups (a, combined_accesses, cache_operations,
// mcontrol6). `include this inside a covergroup, after
// general/RISCV_coverage_standard_coverpoints.svh.
//
// SPDX-License-Identifier: Apache-2.0
//
///////////////////////////////////////////

mcontrol6_type: coverpoint ins.current.csr[CSR_TDATA1][XLEN-1:XLEN-4] { bins mcontrol6 = {4'b0110}; }
dmode_0:       coverpoint ins.current.csr[CSR_TDATA1][XLEN-5] { bins zero = {1'b0}; }
action:        coverpoint ins.current.csr[CSR_TDATA1][15:12] { bins breakpoint = {4'b0000}; }
uncertainen_0: coverpoint ins.current.csr[CSR_TDATA1][5]     { bins exact = {1'b0}; }
chain_off:     coverpoint ins.current.csr[CSR_TDATA1][11]    { bins off = {1'b0}; }
match_eq:      coverpoint ins.current.csr[CSR_TDATA1][10:7]  { bins eq = {4'b0000}; }
select_adr:    coverpoint ins.current.csr[CSR_TDATA1][21]    { bins adr = {1'b0}; }
priv_m: coverpoint {ins.current.csr[CSR_TDATA1][6], ins.current.csr[CSR_TDATA1][4],
                    ins.current.csr[CSR_TDATA1][3], ins.current.csr[CSR_TDATA1][24],
                    ins.current.csr[CSR_TDATA1][23]} { bins m = {5'b10000}; }
triggernum: coverpoint ins.current.csr[CSR_TSELECT] { bins all_triggers[] = {[UDB_NUM_TRIGGERS-1:0]}; }

mcontrol6: cross mcontrol6_type, dmode_0, action, uncertainen_0;
