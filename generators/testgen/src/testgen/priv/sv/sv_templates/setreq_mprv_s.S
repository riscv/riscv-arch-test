
.macro SET_REQ_MSTATUS_VAL
  LI(   t0, MSTATUS_MPRV)
  csrs  mstatus, t0
  LI(   t0, 0x1800)
  csrc  mstatus, t0
  LI(   t0, 0x800)
  csrs  mstatus, t0          // Set to Smode
.endm
