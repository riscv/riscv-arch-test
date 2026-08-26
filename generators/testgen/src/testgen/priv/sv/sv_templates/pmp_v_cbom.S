
// Test cache-block management operations
.macro VERIFICATION_RWX

  cbo.clean (a5)
  nop

  cbo.flush (a5)
  nop

  cbo.inval (a5)
  nop

.endm
