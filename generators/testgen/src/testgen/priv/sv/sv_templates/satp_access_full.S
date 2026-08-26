
main:
{access_cases}
{HR}
// Test case 4: Set satp.MODE to {Svn} | Expected: Successful
{HR}

  LI(a0, SATP_MODE_{SVN}<<{shift})      // satp.MODE = {Svn}
  csrw satp, a0
  test4_{svn}:
  RVTEST_SIGUPD_CSR_READ(satp, a4, test4_{svn}, test4_{svn}_str)


{HR}
// Test case 6: Zeros, ones and walking ones on satp.ASID | Expected: Successful
{HR}

  LI(a1, SATP_MODE_{SVN}<<{shift})      // satp.MODE = {Svn}

  // satp.ASID = All zeros
  mv   a0, a1
  csrw satp, a0
  test6_zeros:
  RVTEST_SIGUPD_CSR_READ(satp, a4, test6_zeros, test6_zeros_str)

  // satp.ASID = All ones
  LI(  a0, {asid_ones})
  slli a0, a0, {asid_shift}
  or   a0, a1, a0
  csrw satp, a0
  test6_ones:
  RVTEST_SIGUPD_CSR_READ(satp, a4, test6_ones, test6_ones_str)

  // satp.ASID = Walking Ones
  li   a2, 1
  slli a2, a2, {asid_shift}
  .rept({asid_bits})
    or   a0, a1, a2
    csrw satp, a0
    6:
    RVTEST_SIGUPD_CSR_READ(satp, a4, 6b, test6_walk_str)
    slli  a2, a2, 1
  .endr


{HR}
RVTEST_CODE_END
RVTEST_DATA_BEGIN


test1_csrw_str:   .string "\"Mismatch on csrw in Test Case 1!\""
test1_csrs_str:   .string "\"Mismatch on csrs in Test Case 1!\""
test1_csrc_str:   .string "\"Mismatch on csrc in Test Case 1!\""
test2_csrw_str:   .string "\"Mismatch on csrw in Test Case 2!\""
test2_csrs_str:   .string "\"Mismatch on csrs in Test Case 2!\""
test2_csrc_str:   .string "\"Mismatch on csrc in Test Case 2!\""
test3_str:        .string "\"Mismatch in Test Case 3!\""
test4_{svn}_str:   .string "\"Mismatch on setting satp.MODE={Svn} in Test Case 4!\""
test6_zeros_str:  .string "\"Mismatch on setting satp.ASID=Zeros in Test Case 6!\""
test6_ones_str:   .string "\"Mismatch on setting satp.ASID=Ones in Test Case 6!\""
test6_walk_str:   .string "\"Mismatch on walking ones in satp.ASID in Test Case 6!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
