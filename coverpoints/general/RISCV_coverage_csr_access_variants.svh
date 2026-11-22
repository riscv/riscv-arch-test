///////////////////////////////////////////
// CSR write encodings used by privilege and read-only trap tests.
// SPDX-License-Identifier: Apache-2.0
///////////////////////////////////////////

// CSRRW with rd!=x0 and an all-ones source is covered by the existing read-only address sweep.
csr_access_variant: coverpoint ins.current.insn {
    wildcard bins csrrw_x0_rdnz = {CSRRW} iff (ins.current.insn[11:7] != 0 && ins.current.insn[19:15] == 0);
    wildcard bins csrrw_x0_rd0 = {CSRRW} iff (ins.current.insn[11:7] == 0 && ins.current.insn[19:15] == 0);
    wildcard bins csrrw_ones_rd0 = {CSRRW} iff (ins.current.insn[11:7] == 0 && ins.current.insn[19:15] != 0 && ins.current.rs1_val == '1);
    wildcard bins csrrwi_zero_rdnz = {CSRRWI} iff (ins.current.insn[11:7] != 0 && ins.current.insn[19:15] == 0);
    wildcard bins csrrwi_zero_rd0 = {CSRRWI} iff (ins.current.insn[11:7] == 0 && ins.current.insn[19:15] == 0);
    wildcard bins csrrwi_ones_rdnz = {CSRRWI} iff (ins.current.insn[11:7] != 0 && ins.current.insn[19:15] == 31);
    wildcard bins csrrwi_ones_rd0 = {CSRRWI} iff (ins.current.insn[11:7] == 0 && ins.current.insn[19:15] == 31);
    wildcard bins csrrs_zero_rdnz = {CSRRS} iff (ins.current.insn[11:7] != 0 && ins.current.insn[19:15] != 0 && ins.current.rs1_val == 0);
    wildcard bins csrrs_zero_rd0 = {CSRRS} iff (ins.current.insn[11:7] == 0 && ins.current.insn[19:15] != 0 && ins.current.rs1_val == 0);
    wildcard bins csrrs_ones_rdnz = {CSRRS} iff (ins.current.insn[11:7] != 0 && ins.current.insn[19:15] != 0 && ins.current.rs1_val == '1);
    wildcard bins csrrs_ones_rd0 = {CSRRS} iff (ins.current.insn[11:7] == 0 && ins.current.insn[19:15] != 0 && ins.current.rs1_val == '1);
    wildcard bins csrrc_zero_rdnz = {CSRRC} iff (ins.current.insn[11:7] != 0 && ins.current.insn[19:15] != 0 && ins.current.rs1_val == 0);
    wildcard bins csrrc_zero_rd0 = {CSRRC} iff (ins.current.insn[11:7] == 0 && ins.current.insn[19:15] != 0 && ins.current.rs1_val == 0);
    wildcard bins csrrc_ones_rdnz = {CSRRC} iff (ins.current.insn[11:7] != 0 && ins.current.insn[19:15] != 0 && ins.current.rs1_val == '1);
    wildcard bins csrrc_ones_rd0 = {CSRRC} iff (ins.current.insn[11:7] == 0 && ins.current.insn[19:15] != 0 && ins.current.rs1_val == '1);
    wildcard bins csrrsi_ones_rdnz = {CSRRSI} iff (ins.current.insn[11:7] != 0 && ins.current.insn[19:15] == 31);
    wildcard bins csrrsi_ones_rd0 = {CSRRSI} iff (ins.current.insn[11:7] == 0 && ins.current.insn[19:15] == 31);
    wildcard bins csrrci_ones_rdnz = {CSRRCI} iff (ins.current.insn[11:7] != 0 && ins.current.insn[19:15] == 31);
    wildcard bins csrrci_ones_rd0 = {CSRRCI} iff (ins.current.insn[11:7] == 0 && ins.current.insn[19:15] == 31);
}
