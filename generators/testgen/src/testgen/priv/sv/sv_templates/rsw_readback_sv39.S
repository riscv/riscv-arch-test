  // Read PTE to make sure that the accesses didn't affect the RSW field
  .if \level == LEVEL2
    LA(  a4, rvtest_Sroot_pg_tbl)
    \TEST_CASE\()_read_pte:
    ld   a4, 40(a4)
  .elseif \level == LEVEL1
    LA(  a4, rvtest_slvl1_pg_tbl)
    \TEST_CASE\()_read_pte:
    ld   a4, 32(a4)
  .elseif \level == LEVEL0
    LA(  a4, rvtest_slvl0_pg_tbl)
    \TEST_CASE\()_read_pte:
    ld   a4, 16(a4)
  .endif
