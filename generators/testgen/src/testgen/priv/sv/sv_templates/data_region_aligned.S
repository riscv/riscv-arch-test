
.p2align 12
.p2align (UDB_PMP_GRANULARITY)
rvtest_data_1:
  nop
  addi a4, a2, 4
  jr ra
  nop
  .word 0xbeefcaf1          // Random word
  .word 0xbeefcaf2          // Random word
  nop
  jr ra

.p2align (UDB_PMP_GRANULARITY)
