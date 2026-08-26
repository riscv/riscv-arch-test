
{HR}
// Test case 1: Access satp in M-mode using csrrw, csrrs, csrrc | Expected: Successful access
{HR}

  li a0, 1
  csrw satp, a0
  test1_csrw:
  RVTEST_SIGUPD_CSR_READ(satp, a4, test1_csrw, test1_csrw_str)

  li a0, 2
  csrs satp, a0
  test1_csrs:
  RVTEST_SIGUPD_CSR_READ(satp, a4, test1_csrs, test1_csrs_str)

  li a0, 1
  csrc satp, a0
  test1_csrc:
  RVTEST_SIGUPD_CSR_READ(satp, a4, test1_csrc, test1_csrc_str)


{HR}
// Test case 2: Access satp in S-mode using csrrw, csrrs, csrrc | Expected: Successful access
{HR}

  RVTEST_GOTO_LOWER_MODE Smode

  li a0, 4
  csrw satp, a0
  test2_csrw:
  RVTEST_SIGUPD_CSR_READ(satp, a4, test2_csrw, test2_csrw_str)

  li a0, 8
  csrs satp, a0
  test2_csrs:
  RVTEST_SIGUPD_CSR_READ(satp, a4, test2_csrs, test2_csrs_str)

  li a0, 4
  csrc satp, a0
  test2_csrc:
  RVTEST_SIGUPD_CSR_READ(satp, a4, test2_csrc, test2_csrc_str)

  RVTEST_GOTO_MMODE


{HR}
// Test case 3: Access satp in U-mode using csrrw, csrrs, csrrc | Expected: 3 Illegal instruction exceptions
{HR}

  RVTEST_GOTO_LOWER_MODE Umode

  li a0, 3
  csrw satp, a0

  li a0, 12
  csrs satp, a0

  li a0, 6
  csrc satp, a0

  RVTEST_GOTO_MMODE

  test3:
  RVTEST_SIGUPD_CSR_READ(satp, a4, test3, test3_str)
