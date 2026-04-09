# Coverage Work Status

Last verified: 2026-04-09

### Vf — Complete

All custom coverpoints at 100%.

### Vls — Complete

Extensions: `Vls8,Vls16,Vls32,Vls64`

Full-suite 100% coverage verified (all extensions combined, RV32+RV64):

- rv64: 1085 covergroups all at 100%
- rv32: 957 covergroups all at 100%

All 7 custom coverpoints and all standard coverpoints at 100%.

| Coverpoint                       | Status    |
| -------------------------------- | --------- |
| cp_custom_vwholeRegLS_vill       | completed |
| cp_custom_vwholeRegLS_lmul       | completed |
| cp_custom_maskLS                 | completed |
| cp_custom_ls_indexed             | completed |
| cp_custom_ffLS_update_vl         | completed |
| cp_custom_indexed_emul_data_only | completed |
| cp_custom_masked_v0_operand      | completed |

### Key fixes for full-suite coverage

- **sig.elf for coverage traces**: Changed build_plan.py to use sig.elf instead of final.elf for RVVI trace generation — avoids selfcheck halting
- **Store vd preload cap**: Capped vd_emul to lmul for stores to prevent misaligned register access
- **Zero data padding**: `.fill 128, 1, 0` in genVsedges for VLEN=1024 whole-register loads
- **Unreachable bin removal**: Removed `bins one = {0}` from cr_vl_lmul_e16_emul1max_sew8.sv
- **cmp_vd_vs2_sew_lte handler**: Added handler for indexed LS vd==vs2 overlap tests with SEW guard
- **cr*vtype_agnostic*\*\_nomask handlers**: Added handlers for whole-register LS agnostic bins
- **Template ifdef fixes**: COVER_VLSCUSTOM* → COVER_VLS*

### References

- Custom definitions: `working-testplans/duplicates/Vector - Vls_custom_definitions.csv`
- Standard definitions: `docs/ctp/src/v.adoc`
- Simulator issues: `simulator-issues.md`
