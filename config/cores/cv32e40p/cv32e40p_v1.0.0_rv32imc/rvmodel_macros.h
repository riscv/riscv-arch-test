# rvmodel_macros.h
# RVMODEL macro definitions for CV32E40P core
# SPDX-License-Identifier: Apache-2.0

#ifndef _COMPLIANCE_MODEL_H
#define _COMPLIANCE_MODEL_H

#define RVMODEL_DATA_SECTION \
        .pushsection .tohost,"aw",@progbits;                \
        .align 8; .global tohost; tohost: .dword 0;         \
        .align 8; .global fromhost; fromhost: .dword 0;     \
        .popsection;

##### STARTUP #####

# Perform boot operations. Can be empty.
# cv32e40p supports both direct (MODE=0) and vectored (MODE=1) mtvec.
# Direct mode (MODE=0) requires 4-byte alignment only — use .align 2 before handler.
#define RVMODEL_BOOT                                                     \
  .option push                                                       ;   \
  .option arch, +zicsr                                               ;   \
  la    t0, _cv32e40p_trap_handler                                   ;   \
  csrw  mtvec, t0                                                    ;   \
  j     _cv32e40p_boot_cont                                          ;   \
  .align 2                                                           ;   \
_cv32e40p_trap_handler:                                              ;   \
  addi  sp, sp, -12                                                  ;   \
  sw    t0, 0(sp)                                                    ;   \
  sw    t1, 4(sp)                                                    ;   \
  sw    t2, 8(sp)                                                    ;   \
  csrr  t0, mepc                                                     ;   \
  lhu   t1, 0(t0)                                                    ;   \
  andi  t1, t1, 3                                                    ;   \
  li    t2, 3                                                        ;   \
  beq   t1, t2, _cv32e40p_trap_32bit                                 ;   \
  addi  t0, t0, 2                                                    ;   \
  j     _cv32e40p_trap_done                                          ;   \
_cv32e40p_trap_32bit:                                                ;   \
  addi  t0, t0, 4                                                    ;   \
_cv32e40p_trap_done:                                                 ;   \
  csrw  mepc, t0                                                     ;   \
  lw    t0, 0(sp)                                                    ;   \
  lw    t1, 4(sp)                                                    ;   \
  lw    t2, 8(sp)                                                    ;   \
  addi  sp, sp, 12                                                   ;   \
  mret                                                               ;   \
_cv32e40p_boot_cont:                                                 ;   \
  .option pop

# Address to use for load/store fault tests that should cause an access fault on the DUT.
#define RVMODEL_ACCESS_FAULT_ADDRESS 0x00000000

##### TERMINATION #####

# Terminate test with a pass indication.
#define RVMODEL_HALT_PASS  \
  li x1, 123456789                ;\
  li x2, 0x20000000       ;\
  write_tohost_pass:      ;\
    sw x1, 0(x2)          ;\
    sw x0, 4(x2)          ;\
  self_loop_pass:         ;\
    j self_loop_pass      ;\

# Terminate test with a fail indication.
#define RVMODEL_HALT_FAIL \
  li x1, 1                ;\
  li x2, 0x20000000       ;\
  write_tohost_fail:      ;\
    sw x1, 0(x2)          ;\
    sw x0, 4(x2)          ;\
  self_loop_fail:         ;\
    j self_loop_fail      ;\

##### IO #####

#define RVMODEL_IO_INIT(_R1, _R2, _R3)

#define RVMODEL_IO_WRITE_STR(_R1, _R2, _R3, _STR_PTR) \
1:                           ;                        \
  lbu  _R1, 0(_STR_PTR)      ; /* Load byte */        \
  beqz _R1, 3f               ; /* Exit if null */     \
2:                           ;                        \
  li   _R2, 0x10000000       ; /* virtual printer */  \
  sw   _R1, 0(_R2)           ;                        \
  addi _STR_PTR, _STR_PTR, 1 ; /* Next char */        \
  j 1b                       ; /* Loop */             \
3:

##### Machine Timer #####

#define RVMODEL_MTIME_ADDRESS    0x0200BFF8
#define RVMODEL_MTIMECMP_ADDRESS 0x02004000

##### Machine Interrupts #####

#define RVMODEL_SET_MEXT_INT(_R1, _R2)
#define RVMODEL_CLR_MEXT_INT(_R1, _R2)
#define RVMODEL_SET_MSW_INT(_R1, _R2)
#define RVMODEL_CLR_MSW_INT(_R1, _R2)

##### Supervisor Interrupts #####

#define RVMODEL_SET_SEXT_INT(_R1, _R2)
#define RVMODEL_CLR_SEXT_INT(_R1, _R2)
#define RVMODEL_SET_SSW_INT(_R1, _R2)
#define RVMODEL_CLR_SSW_INT(_R1, _R2)

#endif // _COMPLIANCE_MODEL_H
