
.macro TEST_CASES_RUNNER LOWER_MODE, VA_W, VA_R, VA_X, level, TEST_CASE

  // Adjust offset of VAs to point to test region
  .set VA_SHIFT, (\level*10)+12
  LI(a0, (\VA_W>>VA_SHIFT)<<VA_SHIFT)
  LI(a1, (\VA_R>>VA_SHIFT)<<VA_SHIFT)
  LI(a5, (\VA_X>>VA_SHIFT)<<VA_SHIFT)
  LA(t0, rvtest_data_1)
  slli t0, t0, 32-VA_SHIFT
  srli t0, t0, 32-VA_SHIFT
  add  a0, a0, t0             // a0 has VA for Store
  add  a1, a1, t0             // a1 has VA for Load
  add  a5, a5, t0             // a5 has VA for Execute

  RVTEST_GOTO_LOWER_MODE \LOWER_MODE

  VERIFICATION_RWX \TEST_CASE

  RVTEST_GOTO_MMODE

  // Signature Update
  RVTEST_SIGUPD(x2, x5, x4, a2, \TEST_CASE\()_store, \TEST_CASE\()_store_str)
  RVTEST_SIGUPD(x2, x5, x4, a3, \TEST_CASE\()_load, \TEST_CASE\()_load_str)
  RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_exec, \TEST_CASE\()_exec_str)

  // Read PTEs to check if DA bits have been updated correctly
  .if \level == LEVEL1
      LA(a0, rvtest_Sroot_pg_tbl)
  .elseif \level == LEVEL0
      LA(a0, rvtest_slvl0_pg_tbl)
  .endif
  \TEST_CASE\()_read_store_pte:
  lw   a4, 4(a0)                   // PTE used during Store
  RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_read_store_pte, \TEST_CASE\()_read_store_pte_str)
  \TEST_CASE\()_read_load_pte:
  lw   a4, 8(a0)                   // PTE used during Load
  RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_read_load_pte, \TEST_CASE\()_read_load_pte_str)
  \TEST_CASE\()_read_exec_pte:
  lw   a4, 12(a0)                  // PTE used during Fetch
  RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_read_exec_pte, \TEST_CASE\()_read_exec_pte_str)

.endm
