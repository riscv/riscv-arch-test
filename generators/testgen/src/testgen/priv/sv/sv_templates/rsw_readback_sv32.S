  // Read PTE to make sure that the accesses didn't affect the RSW field
  .if \level == LEVEL1
    LA(  a4, rvtest_Sroot_pg_tbl)
    \TEST_CASE\()_read_pte:
    lw   a4, 64(a4)
  .elseif \level == LEVEL0
    LA(  a4, rvtest_slvl0_pg_tbl)
    \TEST_CASE\()_read_pte:
    lw   a4, 28(a4)
  .endif
