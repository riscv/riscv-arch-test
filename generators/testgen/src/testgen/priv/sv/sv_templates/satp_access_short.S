
main:
{HR}
// Test case 1: Set satp.MODE to {Svn} | Expected: Successful
{HR}

  LI(a0, SATP_MODE_{SVN}<<{shift})      // satp.MODE = {Svn}
  csrw satp, a0
  test1_{svn}:
  RVTEST_SIGUPD_CSR_READ(satp, a4, test1_{svn}, test1_{svn}_str)


{HR}
// Test case 3: Zeros, ones and walking ones on satp.ASID | Expected: Successful
{HR}

  LI(a1, SATP_MODE_{SVN}<<{shift})      // satp.MODE = {Svn}

  // satp.ASID = All zeros
  mv   a0, a1
  csrw satp, a0
  test3_zeros:
  RVTEST_SIGUPD_CSR_READ(satp, a4, test3_zeros, test3_zeros_str)

  // satp.ASID = All ones
  LI(  a0, {asid_ones})
  slli a0, a0, {asid_shift}
  or   a0, a1, a0
  csrw satp, a0
  test3_ones:
  RVTEST_SIGUPD_CSR_READ(satp, a4, test3_ones, test3_ones_str)

  // satp.ASID = Walking Ones
  li   a2, 1
  slli a2, a2, {asid_shift}
  .rept({asid_bits})
    or   a0, a1, a2
    csrw satp, a0
    6:
    RVTEST_SIGUPD_CSR_READ(satp, a4, 6b, test3_walk_str)
    slli  a2, a2, 1
  .endr


{HR}
RVTEST_CODE_END
RVTEST_DATA_BEGIN


test1_{svn}_str:   .string "\"Mismatch on setting satp.MODE={Svn} in Test Case 1!\""
test3_zeros_str:  .string "\"Mismatch on setting satp.ASID=Zeros in Test Case 3!\""
test3_ones_str:   .string "\"Mismatch on setting satp.ASID=Ones in Test Case 3!\""
test3_walk_str:   .string "\"Mismatch on walking ones in satp.ASID in Test Case 3!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
