
.macro CHANGE_PTE_TO_BE
  // After PTE_SETUP_{SUF} completes, a0 has the PTE (PPN and Permission bits) while t1 has the PTE address
  li a3, 0
  li a4, 0
  li a5, {shift}
  .rept({width})
    andi a3, a0, 0xFF
    srli a0, a0, 8
    sll  a3, a3, a5
    or   a4, a4, a3
    addi a5, a5, -8
  .endr
  SREG a4, 0(t1)
.endm
