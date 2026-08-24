
// Test RWX permissions
.macro VERIFICATION_RWX TEST_CASE
  addi a2, a2, 16

  // Test store permission
  \TEST_CASE\()_store:
  sw  a2, 20(a5)
  nop

  // Test load permission
  \TEST_CASE\()_load:
  lw a3, 20(a5)
  nop

  LA(a5, rvtest_data_1)       // Using physical address for fetch

  // Test execute permission
  \TEST_CASE\()_exec:
  jalr ra, a5, 0
  nop
.endm
