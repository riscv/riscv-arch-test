# rvtest_config_check.h
# Checks that compare the hart with the values its UDB config implies
# SPDX-License-Identifier: Apache-2.0

// Included when a test defines RVTEST_CONFIG_CHECKS (the ConfigCheck suite).
//
// The expected value of a config check comes from the UDB config, not from the
// reference model, and the code is the same in the signature and self-check builds.
// So a mismatch on the reference model means sail.json disagrees with the UDB config,
// and the build stops there; a mismatch on the DUT means the DUT disagrees with it.
// Each mismatch prints the testcase string and both values, and the test carries on,
// so one run lists every disagreement. The test fails at the end if there was any.

// RVTEST_CONFIG_CHECK(_OBS, _CFG, _STR_PTR)
// Compare _OBS, a value read from the hart, with _CFG, the value the config implies.
// Clobbers ra, a0-a2 and DEFAULT_LINK_REG/DEFAULT_TEMP_REG on a mismatch, like a T-SBI call.
#define RVTEST_CONFIG_CHECK(_OBS, _CFG, _STR_PTR)   \
    .option push                                    ;\
    .option norvc                                   ;\
    beq _OBS, _CFG, 1f                              ;\
    mv a1, _OBS                                     ;\
    mv a2, _CFG                                     ;\
    LA(a0, _STR_PTR)                                ;\
    jal DEFAULT_LINK_REG, rvtest_config_mismatch    ;\
1:                                                  ;\
    .option pop

// rvtest_config_probe_trap is a legal mtvec/stvec base in both modes, so the tvec
// probes can write its address with either mode.
#define RVTEST_CONFIG_PROBE_ALIGN 4
#if defined(UDB_MTVEC_BASE_ALIGNMENT_DIRECT) && UDB_MTVEC_BASE_ALIGNMENT_DIRECT > RVTEST_CONFIG_PROBE_ALIGN
  #undef RVTEST_CONFIG_PROBE_ALIGN
  #define RVTEST_CONFIG_PROBE_ALIGN UDB_MTVEC_BASE_ALIGNMENT_DIRECT
#endif
#if defined(UDB_MTVEC_BASE_ALIGNMENT_VECTORED) && UDB_MTVEC_BASE_ALIGNMENT_VECTORED > RVTEST_CONFIG_PROBE_ALIGN
  #undef RVTEST_CONFIG_PROBE_ALIGN
  #define RVTEST_CONFIG_PROBE_ALIGN UDB_MTVEC_BASE_ALIGNMENT_VECTORED
#endif
#if defined(UDB_STVEC_BASE_ALIGNMENT_VECTORED) && UDB_STVEC_BASE_ALIGNMENT_VECTORED > RVTEST_CONFIG_PROBE_ALIGN
  #undef RVTEST_CONFIG_PROBE_ALIGN
  #define RVTEST_CONFIG_PROBE_ALIGN UDB_STVEC_BASE_ALIGNMENT_VECTORED
#endif

// A hart with only vectored mode still sends exceptions to BASE.
#if defined(UDB_MTVEC_MODES_1) && !defined(UDB_MTVEC_MODES_0)
  #define RVTEST_CONFIG_PROBE_MODE 1
#else
  #define RVTEST_CONFIG_PROBE_MODE 0
#endif

// RVTEST_CONFIG_PROBE_BEGIN / RVTEST_CONFIG_PROBE_END
// Between these, an M-mode trap skips the trapping instruction and leaves its cause in
// mcause, without a trap record. A probe clears mcause, executes one 4-byte instruction
// and reads mcause back, so an instruction that traps on one hart and not on another
// is reported by RVTEST_CONFIG_CHECK instead of breaking the trap signature. CSR
// accesses that the config says are legal run here too, so a missing CSR is a mismatch
// rather than an unexpected trap. The test's mtvec is kept in memory. Clobbers a0, a1.
#define RVTEST_CONFIG_PROBE_BEGIN                   \
    csrr a0, CSR_MTVEC                              ;\
    LA(a1, rvtest_config_mtvec)                     ;\
    SREG a0, 0(a1)                                  ;\
    LA(a0, rvtest_config_probe_trap)                ;\
    ori a0, a0, RVTEST_CONFIG_PROBE_MODE            ;\
    csrw CSR_MTVEC, a0

#define RVTEST_CONFIG_PROBE_END                     \
    LA(a0, rvtest_config_mtvec)                     ;\
    LREG a0, 0(a0)                                  ;\
    csrw CSR_MTVEC, a0

.macro RVTEST_CONFIG_CHECK_CODE
  // Report one mismatch and return to the test.
  // a0 = testcase string, a1 = observed value, a2 = value the config implies.
  // Returns through DEFAULT_LINK_REG. rvmodel_io_write_str clobbers T1-T3 and
  // failedtest_hex_to_str clobbers a2-a5, so those are saved here.
  rvtest_config_mismatch:
    LA(DEFAULT_TEMP_REG, rvtest_config_save)
    SREG a0, 0*REGWIDTH(DEFAULT_TEMP_REG)
    SREG a1, 1*REGWIDTH(DEFAULT_TEMP_REG)
    SREG a2, 2*REGWIDTH(DEFAULT_TEMP_REG)
    SREG T1, 3*REGWIDTH(DEFAULT_TEMP_REG)
    SREG T2, 4*REGWIDTH(DEFAULT_TEMP_REG)
    SREG T3, 5*REGWIDTH(DEFAULT_TEMP_REG)
    SREG a3, 6*REGWIDTH(DEFAULT_TEMP_REG)
    SREG a4, 7*REGWIDTH(DEFAULT_TEMP_REG)
    SREG a5, 8*REGWIDTH(DEFAULT_TEMP_REG)
    LA(a1, rvtest_config_mismatches)
    LREG a2, 0(a1)
    addi a2, a2, 1
    SREG a2, 0(a1)
    LA(a0, rvtest_config_mismatch_str)
    call rvmodel_io_write_str
    LA(DEFAULT_TEMP_REG, rvtest_config_save)
    LREG a0, 0*REGWIDTH(DEFAULT_TEMP_REG)
    call rvmodel_io_write_str
    LA(a0, rvtest_config_cfg_str)
    call rvmodel_io_write_str
    LA(DEFAULT_TEMP_REG, rvtest_config_save)
    LREG a0, 2*REGWIDTH(DEFAULT_TEMP_REG)
    li a1, UDB_MXLEN
    jal failedtest_hex_to_str
    LA(a0, ascii_buffer)
    call rvmodel_io_write_str
    LA(a0, rvtest_config_obs_str)
    call rvmodel_io_write_str
    LA(DEFAULT_TEMP_REG, rvtest_config_save)
    LREG a0, 1*REGWIDTH(DEFAULT_TEMP_REG)
    li a1, UDB_MXLEN
    jal failedtest_hex_to_str
    LA(a0, ascii_buffer)
    call rvmodel_io_write_str
    LA(DEFAULT_TEMP_REG, rvtest_config_save)
    LREG T1, 3*REGWIDTH(DEFAULT_TEMP_REG)
    LREG T2, 4*REGWIDTH(DEFAULT_TEMP_REG)
    LREG T3, 5*REGWIDTH(DEFAULT_TEMP_REG)
    LREG a3, 6*REGWIDTH(DEFAULT_TEMP_REG)
    LREG a4, 7*REGWIDTH(DEFAULT_TEMP_REG)
    LREG a5, 8*REGWIDTH(DEFAULT_TEMP_REG)
    jr DEFAULT_LINK_REG

  // Probes are 4 bytes long, so skipping one is mepc + 4.
  .balign RVTEST_CONFIG_PROBE_ALIGN
  rvtest_config_probe_trap:
    csrr a0, CSR_MEPC
    addi a0, a0, 4
    csrw CSR_MEPC, a0
    mret
.endm

// Runs at the end of the test, in M-mode, before the signature checks.
.macro RVTEST_CONFIG_CHECK_VERDICT
  rvtest_config_verdict:
    LA(T1, rvtest_config_mismatches)
    LREG T1, 0(T1)
    beqz T1, rvtest_config_verdict_done
    LA(a0, failstr)
    call rvmodel_io_write_str
    LA(a0, rvtest_config_count_str)
    call rvmodel_io_write_str
    LA(a0, rvtest_config_mismatches)
    LREG a0, 0(a0)
    li a1, UDB_MXLEN
    jal failedtest_hex_to_str
    LA(a0, ascii_buffer)
    call rvmodel_io_write_str
    LA(a0, rvtest_config_fail_str)
    call rvmodel_io_write_str
    call rvmodel_halt_fail
  rvtest_config_verdict_done:
.endm

.macro RVTEST_CONFIG_CHECK_DATA
  .p2align 3
  rvtest_config_mismatches:
    .dword 0
  rvtest_config_save:
    .fill 9, 8, 0
  rvtest_config_mtvec:
    .dword 0
  rvtest_config_mismatch_str:
    .string "\nRVCP-CONFIG: mismatch "
  rvtest_config_cfg_str:
    .string "\nRVCP-CONFIG:   config   "
  rvtest_config_obs_str:
    .string "RVCP-CONFIG:   observed "
  rvtest_config_count_str:
    .string "RVCP-CONFIG: mismatches: "
  rvtest_config_fail_str:
    .ascii "RVCP-CONFIG: the hart disagrees with the UDB config on each value above.\n"
    .asciz "RVCP-CONFIG: On the reference model, sail.json is wrong; on the DUT, the config or the DUT is.\n"
.endm
