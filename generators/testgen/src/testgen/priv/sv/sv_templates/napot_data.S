
.p2align 16
rvtest_data_1:
  nop
  addi a4, a2, 4
  jr ra
  nop
  .word 0xbeefcaf1          // Random word
  .word 0xbeefcaf2          // Random word
  jr ra
  .skip (2 << 12) - (7*4)
  nop
  addi a4, a2, 4
  jr ra
  nop
  .word 0xbeefcaf3          // Random word
  .word 0xbeefcaf4          // Random word
  jr ra
  .skip (13 << 12) - (7*4)
  nop
  addi a4, a2, 4
  jr ra
  nop
  .word 0xbeefcaf3          // Random word
  .word 0xbeefcaf4          // Random word
  jr ra
