
.macro TEST_CASES_RUNNER_RW LOWER_MODE, VA, level, TEST_CASE

  RVTEST_GOTO_LOWER_MODE \LOWER_MODE

  LI(a5, \VA)
  addi a2, a2, 16

  // Test store permission
  \TEST_CASE\()_store:
  sb  a2, 0(a5)
  nop

  // Test load permission
  \TEST_CASE\()_load:
  lbu  a3, 0(a5)
  nop

  RVTEST_GOTO_MMODE

  // Signature Update
  RVTEST_SIGUPD(x2, x5, x4, a2, \TEST_CASE\()_store, \TEST_CASE\()_store_str)
  RVTEST_SIGUPD(x2, x5, x4, a3, \TEST_CASE\()_load, \TEST_CASE\()_load_str)
.endm
