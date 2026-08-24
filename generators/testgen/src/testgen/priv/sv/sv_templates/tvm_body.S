
main:

  // Set mstatus.TVM
  LI(   a0, MSTATUS_TVM)
  csrs  mstatus, a0

  tvm:
  RVTEST_SIGUPD_CSR_READ(mstatus, a4, tvm, tvm_str)

{HR}
// Test case 1: Access satp in M-mode | mstatus.TVM set | Expected: Successful access
{HR}

  csrw satp, zero

{HR}
// Test case 2: Access sfence.vma in M-mode | mstatus.TVM set | Expected: Successful access
{HR}

  sfence.vma

{HR}
// Test case 3: Access satp in S-mode | mstatus.TVM set | Expected: 3 Illegal instruction exceptions
{HR}

  RVTEST_GOTO_LOWER_MODE Smode

  csrw satp, zero

  csrs satp, zero

  csrc satp, zero

  RVTEST_GOTO_MMODE

{HR}
// Test case 4: Access satp in S-mode | mstatus.TVM set | Expected: Illegal instruction exception
{HR}

  RVTEST_GOTO_LOWER_MODE Smode

  sfence.vma

  RVTEST_GOTO_MMODE


{HR}
RVTEST_CODE_END
RVTEST_DATA_BEGIN

{HR}

tvm_str:   .string "\"Mismatch in mstatus value while setting TVM bit!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
