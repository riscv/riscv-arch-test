
// Test cbo.zero
.macro VERIFICATION_RWX TEST_CASE
  addi a2, a2, 16

  \TEST_CASE\():
  cbo.zero (a5)
  addi a4, a2, 4

.endm
