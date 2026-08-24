
.macro TEST_CASES_RUNNER_X LOWER_MODE, VA, level, TEST_CASE

  RVTEST_GOTO_LOWER_MODE \LOWER_MODE

  LI(  a5, \VA)
  \TEST_CASE\()_exec:
  jalr ra, a5, 0
  nop

  RVTEST_GOTO_MMODE

  // Signature Update
  RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_exec, \TEST_CASE\()_exec_str)
.endm
