
.p2align 12
rvtest_data_1_l0_rw:
  .word 0xbeefcaf1          // Random word
  .word 0xbeefcaf2          // Random word
  .skip ((1 << 10) - 3)*4
  .word 0xbeefcaf3          // Random word

.p2align 12
rvtest_data_1_l0_x:
  nop
  addi a4, a2, REGWIDTH
  jr ra
  nop
  .word 0xbeefcaf1          // Random word
  .word 0xbeefcaf2          // Random word
  .skip ((1 << 10) - 7)*4
  jr ra
