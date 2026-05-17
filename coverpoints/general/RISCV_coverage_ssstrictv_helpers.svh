///////////////////////////////////////////
// RISCV_coverage_ssstrictv_helpers.svh
//
// Minimal subset of standard vector coverpoint helpers that the cp_ssstrictv_*
// templates reference (std_trap_vec, vtype_lmul_*, mask_enabled, vd_v0,
// vstart_zero, vl_nonzero, vtype_prev_vill_*, vtype_all_lmulge1, and the
// vd/vs1/vs2 unaligned-LMUL coverpoints).
//
// Scoped to SsstrictV covergroups only — the broader
// RISCV_coverage_standard_coverpoints_vector.svh would also pull in dozens of
// 32-bin sweeps (vd_all_reg, vs1_all_reg, vs2_all_reg, ...) and SEW/LMUL
// matrices that are not required by SsstrictV's testplan and would inflate
// the corpus past the linker's ±1MiB JAL range.
///////////////////////////////////////////

    vtype_prev_vill_clear: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") {
        type_option.weight = 0;
        bins vill_not_set = {0};
    }

    vtype_prev_vill_set: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") {
        type_option.weight = 0;
        bins vill_set = {1};
    }

    vstart_zero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") {
        type_option.weight = 0;
        bins target = {0};
    }

    vl_nonzero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") {
        type_option.weight = 0;
        bins target = {[`XLEN'h10000:`XLEN'h1]};
    }

    mask_enabled: coverpoint ins.current.insn[25] {
        type_option.weight = 0;
        bins enabled = {1'b0};
    }

    vd_v0: coverpoint ins.current.insn[11:7] {
        type_option.weight = 0;
        bins zero = {5'b00000};
    }

    std_trap_vec : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "vs") != 0
                    }
    {
        bins true = {1'b1};
    }

    vtype_all_lmulge1: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        type_option.weight = 0;
        bins one    = {0};
        bins two    = {1};
        bins four   = {2};
        bins eight  = {3};
    }

    vtype_lmul_1: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        type_option.weight = 0;
        bins one = {0};
    }

    vtype_lmul_2: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        type_option.weight = 0;
        bins two = {1};
    }

    vtype_lmul_4: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        type_option.weight = 0;
        bins two = {2};
    }

    vtype_lmul_8: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        type_option.weight = 0;
        bins two = {3};
    }

    vd_all_reg_unaligned_lmul_2: coverpoint ins.current.insn[11:7] {
        type_option.weight = 0;
        wildcard ignore_bins divisible_by_2 = {5'b????0};
    }

    vd_all_reg_unaligned_lmul_4: coverpoint ins.current.insn[11:7] {
        type_option.weight = 0;
        wildcard ignore_bins divisible_by_4 = {5'b???00};
    }

    vd_all_reg_unaligned_lmul_8: coverpoint ins.current.insn[11:7] {
        type_option.weight = 0;
        wildcard ignore_bins divisible_by_8 = {5'b??000};
    }

    vs1_all_reg_unaligned_lmul_2: coverpoint ins.current.insn[19:15] {
        type_option.weight = 0;
        wildcard ignore_bins divisible_by_2 = {5'b????0};
    }

    vs1_all_reg_unaligned_lmul_4: coverpoint ins.current.insn[19:15] {
        type_option.weight = 0;
        wildcard ignore_bins divisible_by_4 = {5'b???00};
    }

    vs1_all_reg_unaligned_lmul_8: coverpoint ins.current.insn[19:15] {
        type_option.weight = 0;
        wildcard ignore_bins divisible_by_8 = {5'b??000};
    }

    vs2_all_reg_unaligned_lmul_2: coverpoint ins.current.insn[24:20] {
        type_option.weight = 0;
        wildcard ignore_bins divisible_by_2 = {5'b????0};
    }

    vs2_all_reg_unaligned_lmul_4: coverpoint ins.current.insn[24:20] {
        type_option.weight = 0;
        wildcard ignore_bins divisible_by_4 = {5'b???00};
    }

    vs2_all_reg_unaligned_lmul_8: coverpoint ins.current.insn[24:20] {
        type_option.weight = 0;
        wildcard ignore_bins divisible_by_8 = {5'b??000};
    }

    vd_eq_vs1 : coverpoint (ins.current.insn[11:7] == ins.current.insn[19:15]) {
        type_option.weight = 0;
        bins target = {1'b1};
    }

    vd_eq_vs2 : coverpoint (ins.current.insn[11:7] == ins.current.insn[24:20]) {
        type_option.weight = 0;
        bins target = {1'b1};
    }

    vd_ne_vs1 : coverpoint (ins.current.insn[19:15] != ins.current.insn[11:7]) {
        type_option.weight = 0;
        bins target = {1'b1};
    }

    vd_ne_vs2 : coverpoint (ins.current.insn[24:20] != ins.current.insn[11:7]) {
        type_option.weight = 0;
        bins target = {1'b1};
    }

    vs2_eq_vs1 : coverpoint (ins.current.insn[19:15] == ins.current.insn[24:20]) {
        type_option.weight = 0;
        bins target = {1'b1};
    }

    vs2_reg_aligned_lmul_2: coverpoint ins.current.insn[24:20] {
        type_option.weight = 0;
        wildcard bins divisible_by_2 = {5'b????0};
    }

    vs2_reg_aligned_lmul_8: coverpoint ins.current.insn[24:20] {
        type_option.weight = 0;
        wildcard bins divisible_by_8 = {5'b??000};
    }

    vs1_reg_aligned_lmul_8: coverpoint ins.current.insn[19:15] {
        type_option.weight = 0;
        wildcard bins divisible_by_8 = {5'b??000};
    }

    vs1_vd_overlap_lmul1: coverpoint (ins.current.insn[19:16] == ins.current.insn[11:8]) {
        type_option.weight = 0;
        bins overlapping = {1'b1};
    }

    vs1_vd_overlap_lmul2: coverpoint (ins.current.insn[19:17] == ins.current.insn[11:9]) {
        type_option.weight = 0;
        bins overlapping = {1'b1};
    }

    vs1_vd_overlap_lmul4: coverpoint (ins.current.insn[19:18] == ins.current.insn[11:10]) {
        type_option.weight = 0;
        bins overlapping = {1'b1};
    }

    vs1_vd_no_overlap_lmul1: coverpoint (ins.current.insn[19:16] == ins.current.insn[11:8]) {
        type_option.weight = 0;
        bins overlapping = {1'b0};
    }

    vs2_vd_overlap_lmul1: coverpoint (ins.current.insn[24:21] == ins.current.insn[11:8]) {
        type_option.weight = 0;
        bins overlapping = {1'b1};
    }

    vs2_vd_overlap_lmul2: coverpoint (ins.current.insn[24:22] == ins.current.insn[11:9]) {
        type_option.weight = 0;
        bins overlapping = {1'b1};
    }

    vs2_vd_overlap_lmul4: coverpoint (ins.current.insn[24:23] == ins.current.insn[11:10]) {
        type_option.weight = 0;
        bins overlapping = {1'b1};
    }

    vs2_vd_no_overlap_lmul1: coverpoint (ins.current.insn[24:21] == ins.current.insn[11:8]) {
        type_option.weight = 0;
        bins overlapping = {1'b0};
    }

    vs2_ne_vs1 : coverpoint (ins.current.insn[19:15] != ins.current.insn[24:20]) {
        type_option.weight = 0;
        bins target = {1'b1};
    }

    vd_reg_aligned_lmul_2: coverpoint ins.current.insn[11:7] {
        type_option.weight = 0;
        wildcard bins divisible_by_2 = {5'b????0};
    }

    vd_reg_aligned_lmul_4: coverpoint ins.current.insn[11:7] {
        type_option.weight = 0;
        wildcard bins divisible_by_4 = {5'b???00};
    }

    vd_reg_aligned_lmul_8: coverpoint ins.current.insn[11:7] {
        type_option.weight = 0;
        wildcard bins divisible_by_8 = {5'b??000};
    }

    vtype_all_lmulgt1: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        type_option.weight = 0;
        bins two    = {1};
        bins four   = {2};
        bins eight  = {3};
    }

    vtype_all_sew_supported: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
        type_option.weight = 0;
        `ifdef SEW8_SUPPORTED
        bins eight      = {0};
        `endif
        `ifdef SEW16_SUPPORTED
        bins sixteen    = {1};
        `endif
        `ifdef SEW32_SUPPORTED
        bins thirtytwo  = {2};
        `endif
        `ifdef SEW64_SUPPORTED
        bins sixtyfour  = {3};
        `endif

        `ifndef SEW8_SUPPORTED
        `ifndef SEW16_SUPPORTED
        `ifndef SEW32_SUPPORTED
        `ifndef SEW64_SUPPORTED
        bins sew_not_supported  = {[3'b000:3'b111]};
        `endif
        `endif
        `endif
        `endif
    }

    vtype_sew_supported : coverpoint check_vtype_sew_supported(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew")) {
        type_option.weight = 0;
        bins supported = {1};
    }
