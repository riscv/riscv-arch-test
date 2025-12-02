# sail_test.h
# Trickbox macro definitions for Sail reference model
# Jordan Carlin jcarlin@hmc.edu October 2025
# SPDX-License-Identifier: BSD-3-Clause

#ifndef _COMPLIANCE_MODEL_H
#define _COMPLIANCE_MODEL_H

#define RVMODEL_DATA_SECTION \
        .pushsection .tohost,"aw",@progbits;                \
        .align 8; .global tohost; tohost: .dword 0;         \
        .align 8; .global fromhost; fromhost: .dword 0;     \
        .popsection;

#define RVMODEL_HALT_PASS  \
  li x1, 1                ;\
  la t0, tohost           ;\
  write_tohost_pass:      ;\
    sw x1, 0(t0)          ;\
    sw x0, 4(t0)          ;\
    j write_tohost_pass   ;\

#define RVMODEL_HALT_FAIL \
  li x1, 3                ;\
  la t0, tohost           ;\
  write_tohost_fail:      ;\
    sw x1, 0(t0)          ;\
    sw x0, 4(t0)          ;\
    j write_tohost_fail   ;\

#define RVMODEL_BOOT

#define RVMODEL_IO_INIT

# Prints a null-terminated string (_STR) using a DUT specific
# mechanism. _R can be used as a temporary register if needed.
# Do not modify any other registers (or make sure to restore them).
#define RVMODEL_IO_WRITE_STR(_R, _STR)               \
  la x30, _STR                ;/* Load string addr */ \
1:                           ;\
  lbu a0, 0(x30)              ;/* Load byte */        \
  beqz a0, 2f                ;/* Exit if null */     \
  call htif_putc             ;/* Print char */       \
  addi x30, x30, 1             ;/* Next char */        \
  j 1b                       ;/* Loop */             \
2:

#define RVMODEL_SET_MSW_INT

#define RVMODEL_CLEAR_MSW_INT

#define RVMODEL_CLEAR_MTIMER_INT

#define RVMODEL_CLEAR_MEXT_INT

htif_putc:
    la x31, tohost
    sw a0, 0(x31)
    // device=1 (terminal), cmd=1 (output)
    li a0, 0x01010000
    sw a0, 4(x31)
    ret

#endif // _COMPLIANCE_MODEL_H
