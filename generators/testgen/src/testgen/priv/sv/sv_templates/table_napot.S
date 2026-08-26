  LA (t2, {table})
  srl t2, t2, PMP_SHIFT
  LI (t1, ((1<<(UDB_PMP_GRANULARITY - 2))-1)>>1)    // Minimum range is 8 Bytes (1 PTE). Increases as G increases
  or t2, t2, t1
  csrw pmpaddr0, t2
