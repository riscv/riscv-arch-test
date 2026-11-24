///////////////////////////////////////////
// CSR instruction forms used by the privilege and read-only trap tests.
// SPDX-License-Identifier: Apache-2.0
///////////////////////////////////////////

csr_access_op: coverpoint ins.current.insn {
    wildcard bins csrrw  = {CSRRW};
    wildcard bins csrrs  = {CSRRS};
    wildcard bins csrrc  = {CSRRC};
    wildcard bins csrrwi = {CSRRWI};
    wildcard bins csrrsi = {CSRRSI};
    wildcard bins csrrci = {CSRRCI};
}
// rs1 or uimm
csr_access_src: coverpoint ins.current.insn[19:15] {
    bins zero    = {0};
    bins nonzero = {[1:31]};
}
csr_access_rd: coverpoint ins.current.insn[11:7] {
    bins x0      = {0};
    bins nonzero = {[1:31]};
}
// Forms that attempt a write: CSRRW/CSRRWI always, CSRRS/CSRRC/CSRRSI/CSRRCI when rs1 or uimm is nonzero
csr_write_form: coverpoint ins.current.insn {
    wildcard bins csrrw_x0 = {CSRRW}  iff (ins.current.insn[19:15] == 0);
    wildcard bins csrrw    = {CSRRW}  iff (ins.current.insn[19:15] != 0);
    wildcard bins csrrwi_0 = {CSRRWI} iff (ins.current.insn[19:15] == 0);
    wildcard bins csrrwi   = {CSRRWI} iff (ins.current.insn[19:15] != 0);
    wildcard bins csrrs    = {CSRRS}  iff (ins.current.insn[19:15] != 0);
    wildcard bins csrrc    = {CSRRC}  iff (ins.current.insn[19:15] != 0);
    wildcard bins csrrsi   = {CSRRSI} iff (ins.current.insn[19:15] != 0);
    wildcard bins csrrci   = {CSRRCI} iff (ins.current.insn[19:15] != 0);
}
