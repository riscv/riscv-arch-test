  LA (t2, rvtest_data_1)    // Configure test region as NAPOT
  srl t2, t2, PMP_SHIFT

  .if (UDB_PMP_GRANULARITY <= 5)                    // G=3 -> 32 Bytes (Minimum size of test region)
      LI (t1, 0x3)                                // Range = 2^(2+3) = 32 Bytes
  .else
      LI (t1, ((1<<(UDB_PMP_GRANULARITY - 2))-1)>>1)      // Range = 2^(G+3) Bytes
  .endif

  or t2, t2, t1
  csrw pmpaddr{n}, t2
  sfence.vma
