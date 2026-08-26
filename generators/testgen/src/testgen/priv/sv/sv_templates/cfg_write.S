  LI (t2, {cfg})
  {label}:
  RVTEST_SIGUPD_CSR_WRITE(pmpcfg0, t2, {label}, {label}_str)
  sfence.vma
