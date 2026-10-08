///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage: PMP entries that match part of an access
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

// Classifies a load, store or AMO by how the PMP entries match its bytes. The deciding entry is
// the lowest-numbered entry that matches any byte of the access. Shared by the partial-match
// coverpoints of the PMP covergroups (tests from priv/extensions/pmp/partial.py).
//
// pmpaddr values come from the trace, which logs them as read back when written. A test writes
// pmpaddr while its entry is OFF, so at G >= 1 the low G bits read as zero and a NAPOT region larger
// than one grain decodes as a smaller one. The partial-match tests only rely on NAPOT regions of
// 8 bytes at G <= 1, which are unaffected; the background entry may decode as a small region at the
// top of memory, which only changes pmp_partial_t.rest_matched.

`ifndef PMP_PARTIAL_SVH
`define PMP_PARTIAL_SVH

// Test-selection parameters of the partial-match tests, as single macros for `ifdef.
`ifdef UDB_NUM_USABLE_PMP_ENTRIES_16
  `define PMP_PARTIAL_ENTRIES
`elsif UDB_NUM_USABLE_PMP_ENTRIES_64
  `define PMP_PARTIAL_ENTRIES
`endif
`ifdef UDB_PMP_GRANULARITY_2
  `define PMP_PARTIAL_GRAIN_8         // G <= 1
`elsif UDB_PMP_GRANULARITY_3
  `define PMP_PARTIAL_GRAIN_8
`endif

typedef enum logic [2:0] {
  PMP_PARTIAL_NONE,     // not a load, store or AMO, or no entry matches any byte
  PMP_PARTIAL_FULL,     // the deciding entry matches every byte
  PMP_PARTIAL_COVERED,  // the deciding entry matches every byte; the next matching entry only some
  PMP_PARTIAL_LOWER,    // the deciding entry matches the lowest bytes only
  PMP_PARTIAL_UPPER,    // the deciding entry matches the highest bytes only
  PMP_PARTIAL_BOTH,     // the deciding entry matches the lowest bytes, the next matching entry the rest
  PMP_PARTIAL_MIDDLE    // the deciding entry matches neither the lowest nor the highest byte
} pmp_partial_kind_t;

typedef enum logic [1:0] {
  PMP_ACCESS_ALIGNED,
  PMP_ACCESS_IN_GRANULE16,   // misaligned, inside one naturally aligned 16-byte granule
  PMP_ACCESS_CROSSES_GRANULE16
} pmp_access_align_t;

typedef struct packed {
  pmp_partial_kind_t kind;
  pmp_access_align_t align;
  logic [7:0]        cfg;           // pmpcfg byte of the deciding entry
  logic              rest_matched;  // another entry matches a byte that the deciding entry does not
} pmp_partial_t;

// Bytes accessed by a load, store, LR, SC or AMO, or 0 for any other instruction. Compressed
// quadrant 2 (the sp-based forms) is not decoded: the partial-match tests do not use it.
function automatic int pmp_access_bytes(logic [31:0] insn);
  if (insn[1:0] == 2'b00) begin
    case (insn[15:13])
      3'b001, 3'b101: return 8;                            // c.fld, c.fsd
      3'b010, 3'b110: return 4;                            // c.lw, c.sw
      3'b011, 3'b111: return (`UDB_MXLEN == 64) ? 8 : 4;   // c.ld, c.sd on RV64; c.flw, c.fsw on RV32
      3'b100: return insn[12] ? 0 : (insn[10] ? 2 : 1);    // Zcb: c.lh, c.lhu, c.sh or c.lbu, c.sb
      default: return 0;
    endcase
  end
  if (insn[1:0] != 2'b11) return 0;
  case (insn[6:0])
    7'b0000011, 7'b0100011: return 1 << insn[13:12];                          // loads, stores
    7'b0000111, 7'b0100111: return (insn[14:12] inside {[1:4]}) ? 1 << insn[14:12] : 0;  // FP (not vector)
    7'b0101111: return 1 << insn[14:12];                                      // LR, SC, AMOs
    default: return 0;
  endcase
endfunction

function automatic pmp_partial_t pmp_partial(ins_t ins);
  pmp_partial_t result;
  int bytes;
  logic [`UDB_MXLEN-1:0] vaddr, pmpaddr;
  logic [63:0] first, last, region, top, prev_top;
  logic [63:0] lo [64], hi [64];   // entry i matches bytes lo[i] to hi[i]; none when lo[i] > hi[i]
  logic [7:0] cfg [64];
  logic contains_first, contains_last;
  int d, s, napot_ones;

  result = '{kind: PMP_PARTIAL_NONE, align: PMP_ACCESS_ALIGNED, cfg: 8'b0, rest_matched: 1'b0};
  bytes = pmp_access_bytes(ins.current.insn);
  if (bytes == 0) return result;

  // LR, SC and AMOs address rs1 directly; the other accesses add the immediate.
  vaddr = (ins.current.insn[6:0] == 7'b0101111) ? ins.current.rs1_val : ins.current.rs1_val + ins.current.imm;
  first = 64'(vaddr);
  last  = first + bytes - 1;
  if (first % bytes == 0)          result.align = PMP_ACCESS_ALIGNED;
  else if (first[63:4] == last[63:4]) result.align = PMP_ACCESS_IN_GRANULE16;
  else                             result.align = PMP_ACCESS_CROSSES_GRANULE16;

  prev_top = '0;
  for (int i = 0; i < `UDB_NUM_PMP_ENTRIES; i++) begin
    pmpaddr = get_csr_val_addr(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_PMPADDR0 + i, "pmpaddr", "pmpaddr");
    `ifdef UDB_MXLEN_32
      cfg[i] = get_csr_val_addr(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_PMPCFG0 + i/4, "pmpcfg", "pmpcfg") >> (8*(i%4));
    `else
      cfg[i] = get_csr_val_addr(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_PMPCFG0 + 2*(i/8), "pmpcfg", "pmpcfg") >> (8*(i%8));
    `endif
    top = 64'(pmpaddr) << 2;
    lo[i] = 1;
    hi[i] = 0;
    case (cfg[i][4:3])
      2'b01: if (top > prev_top) begin lo[i] = prev_top; hi[i] = top - 1; end   // TOR
      2'b10: begin lo[i] = top; hi[i] = top + 3; end                           // NA4
      2'b11: begin                                                             // NAPOT
        napot_ones = 0;
        while (napot_ones < `UDB_MXLEN && pmpaddr[napot_ones]) napot_ones++;
        region = 64'd1 << (napot_ones + 3);
        lo[i] = top & ~(region - 1);
        hi[i] = lo[i] + region - 1;
      end
      default: ;                                                               // OFF
    endcase
    prev_top = top;
  end

  // d: the deciding entry; s: the next entry that matches any byte.
  d = -1;
  s = -1;
  for (int i = 0; i < `UDB_NUM_PMP_ENTRIES; i++) begin
    if (lo[i] <= hi[i] && lo[i] <= last && first <= hi[i]) begin
      if (d < 0) d = i;
      else if (s < 0) s = i;
    end
  end
  if (d < 0) return result;

  result.cfg = cfg[d];
  contains_first = lo[d] <= first && first <= hi[d];
  contains_last  = lo[d] <= last && last <= hi[d];
  for (int i = d + 1; i < `UDB_NUM_PMP_ENTRIES; i++) begin
    if (lo[i] <= hi[i] && ((!contains_first && lo[i] < lo[d] && first <= hi[i] && lo[i] <= last) ||
                           (!contains_last && hi[i] > hi[d] && lo[i] <= last && first <= hi[i])))
      result.rest_matched = 1'b1;
  end

  if (contains_first && contains_last)
    result.kind = (s >= 0 && !(lo[s] <= first && last <= hi[s])) ? PMP_PARTIAL_COVERED : PMP_PARTIAL_FULL;
  else if (contains_first)
    result.kind = (s >= 0 && lo[s] <= last && last <= hi[s] && !(lo[s] <= first)) ? PMP_PARTIAL_BOTH : PMP_PARTIAL_LOWER;
  else if (contains_last)
    result.kind = PMP_PARTIAL_UPPER;
  else
    result.kind = PMP_PARTIAL_MIDDLE;
  return result;
endfunction

`endif
