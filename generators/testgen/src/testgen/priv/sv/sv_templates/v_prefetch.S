
// Test prefetch instructions
.macro VERIFICATION_RWX

  prefetch.i 0(a5)
  nop

  prefetch.r 0(a5)
  nop

  prefetch.w 0(a5)
  nop

.endm
