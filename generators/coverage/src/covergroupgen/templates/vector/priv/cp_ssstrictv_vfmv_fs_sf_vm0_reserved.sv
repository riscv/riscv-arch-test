// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vfmv_fs_sf_vm0_reserved
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // vfmv.f.s (funct6=010000, funct3=001) and vfmv.s.f (funct6=010000, funct3=101) with vm=0 are reserved
    vfmv_fs_sf_funct6: coverpoint ins.current.insn[31:26] {
        bins vfmv = {6'b010000};
    }

    vfmv_fs_sf_funct3: coverpoint ins.current.insn[14:12] {
        bins vfmv_f_s = {3'b001};
        bins vfmv_s_f = {3'b101};
    }

    vm_masked: coverpoint ins.current.insn[25] {
        bins masked = {1'b0};
    }

    cp_ssstrictv_vfmv_fs_sf_vm0_reserved: cross std_trap_vec, vfmv_fs_sf_funct6, vfmv_fs_sf_funct3, vm_masked;

//// end cp_ssstrictv_vfmv_fs_sf_vm0_reserved //////////////////////////////////////////////////////////////
