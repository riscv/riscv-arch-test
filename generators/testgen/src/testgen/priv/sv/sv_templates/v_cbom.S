
// Test cache-block management operations
.macro VERIFICATION_RWX TEST_CASE
  addi a2, a2, 16

  \TEST_CASE\()_clean:
  cbo.clean (a5)
  addi a2, a2, 4

  \TEST_CASE\()_flush:
  cbo.flush (a5)
  addi a3, a2, 4

  \TEST_CASE\()_inval:
  cbo.inval (a5)
  addi a4, a2, 4

.endm
