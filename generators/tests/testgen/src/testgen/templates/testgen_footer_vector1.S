
// Instantiate trap handlers and other epilog code, call RVMODEL_HALT at end of test
RVTEST_CODE_END

// Create scratch data sections and label for test data
RVTEST_DATA_BEGIN
.align 4

rvtest_data:
.word 0xb0bacafe
.word 0xb0bacafe

vector_data:
