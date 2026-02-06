#ifndef _COMPLIANCE_MODEL_H
#define _COMPLIANCE_MODEL_H

#define RVMODEL_DATA_SECTION \
        .pushsection .tohost,"aw",@progbits;                \
        .align 8; .global tohost; tohost: .dword 0;         \
        .align 8; .global fromhost; fromhost: .dword 0;     \
        .popsection;

#define RVMODEL_BOOT

# Terminate test with a pass indication.
#define RVMODEL_HALT_PASS  \
  li x1, 123456789                ;\
  la t0, 0x20000000       ;\
  write_tohost_pass:      ;\
    sw x1, 0(t0)          ;\
    sw x0, 4(t0)          ;\
  self_loop_pass:         ;\
    j self_loop_pass      ;\

# Terminate test with a fail indication.
#define RVMODEL_HALT_FAIL \
  li x1, 1                ;\
  la t0, 0x20000000       ;\
  write_tohost_fail:      ;\
    sw x1, 0(t0)          ;\
    sw x0, 4(t0)          ;\
  self_loop_fail:         ;\
    j self_loop_fail      ;\

#define RVMODEL_SET_MEXT_INT

#define RVMODEL_CLR_MEXT_INT

#define RVMODEL_SET_MTIMER_INT

#define RVMODEL_CLR_MTIMER_INT

#define RVMODEL_SET_MTIMER_INT_SOON

#define RVMODEL_SET_MSW_INT

#define RVMODEL_CLR_MSW_INT

#define RVMODEL_SET_MTIME

#define RVMODEL_SET_MTIMEH

#define RVMODEL_SET_VEXT_INT

#define RVMODEL_CLR_VEXT_INT

#define RVMODEL_SET_VTIMER_INT

#define RVMODEL_CLR_VTIMER_INT

#define RVMODEL_SET_VTIMER_INT_SOON

#define RVMODEL_SET_VSW_INT

#define RVMODEL_CLR_VSW_INT

#define RVMODEL_SET_SEXT_INT

#define RVMODEL_CLR_SEXT_INT

#define RVMODEL_SET_STIMER_INT

#define RVMODEL_CLR_STIMER_INT

#define RVMODEL_SET_STIMER_INT_SOON

#define RVMODEL_SET_SSW_INT

#define RVMODEL_CLR_SSW_INT


#define RVMODEL_WRITE_GEIP

#define RVMODEL_IO_INIT(_R1, _R2, _R3)

# Prints a null-terminated string by writting each byte in the string
# to the address of the 'virtual printer'.
# A pointer to the string is passed in _STR_PTR.
# _R1, _R2, and _R3 can be used as temporary registers if needed.
# Do not modify any other registers (or make sure to restore them).
#define RVMODEL_IO_WRITE_STR(_R1, _R2, _R3, _STR_PTR) \
1:                           ;                        \
  lbu  _R1, 0(_STR_PTR)      ; /* Load byte */        \
  beqz _R1, 3f               ; /* Exit if null */     \
2:                           ;                        \
  la   _R2, 0x10000000       ; /* virtual printer */  \
  sw   _R1, 0(_R2)           ;                        \
  addi _STR_PTR, _STR_PTR, 1 ; /* Next char */        \
  j 1b                       ; /* Loop */             \
3:

#endif 

