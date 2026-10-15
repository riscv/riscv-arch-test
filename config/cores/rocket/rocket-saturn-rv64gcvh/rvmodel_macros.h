# rvmodel_macros.h
# RVMODEL macro definitions for Rocket + Saturn + H in the Chipyard Verilator test harness
# (Chipyard ACTRocketSaturnHConfig).
# Written against Chipyard    @ 0acc1e1de2d3284bcd4d876956932a013ffe1949 (1.14.0)
#                 rocket-chip @ 55bcad0f59436de98ea510334121de8546b9e9d7
# SPDX-License-Identifier: Apache-2.0

#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

# The harness speaks HTIF: fesvr finds tohost/fromhost in the ELF symbol table and polls them
# over the serial-TileLink (TSI) port.
#define RVMODEL_DATA_SECTION \
        .pushsection .tohost,"aw",@progbits;                \
        .balign 8; .global tohost; tohost: .dword 0;         \
        .balign 8; .global fromhost; fromhost: .dword 0;     \
        .popsection

#define STANDARD_SM_SUPPORTED

# The PLIC (0x0C00_0000) has one source, the SiFive UART at 0x1002_0000 (source 1). Context 0 is
# hart 0 M-mode and context 1 is hart 0 S-mode. The UART's transmit-watermark interrupt is
# pending whenever the transmit FIFO holds fewer entries than txmark, so txmark = 1 with an
# empty FIFO raises it, and clearing ie.txwm drops it.
#define PLIC_BASE_ADDRESS    0x0C000000
#define PLIC_ENABLE_ADDRESS  0x0C002000
#define PLIC_SENABLE_ADDRESS 0x0C002080
#define PLIC_THRESH_ADDRESS  0x0C200000
#define PLIC_CLAIM_ADDRESS   0x0C200004
#define PLIC_STHRESH_ADDRESS 0x0C201000
#define PLIC_SCLAIM_ADDRESS  0x0C201004
#define UART_BASE_ADDRESS    0x10020000
#define UART_INT_SRC         1

##### STARTUP #####

# The Chipyard boot ROM parks the hart in wfi with mie = MSIE and mstatus.MIE = 1 until fesvr
# raises msip, then mrets to the ELF entry point with mie.MSIE still set.
#   https://github.com/ucb-bar/testchipip/blob/26f821be94252b9c4c83511a3376a51ffc138551/src/main/resources/testchipip/bootrom/bootrom.S#L35
# Clear mie so the test starts with every interrupt disabled, as it does on the reference model.
# The PLIC enable registers have no reset value, so disable the UART source in both hart 0
# contexts; otherwise a supervisor external interrupt can also raise mip.MEIP.
# vxrm and vxsat "can have arbitrary values at reset" (V spec) and reset to vcsr = 4 here, while
# the framework initializes only fcsr, so clear vcsr (with mstatus.VS briefly enabled).
#define RVMODEL_BOOT \
  csrw mie, zero;                          \
  li t0, PLIC_ENABLE_ADDRESS;              \
  sw zero, 0(t0);                          \
  li t0, PLIC_SENABLE_ADDRESS;             \
  sw zero, 0(t0);                          \
  li t0, 0x600;                            \
  csrs mstatus, t0;                        \
  csrw 0x00F, zero;         /* vcsr */   \
  csrc mstatus, t0;

##### TERMINATION #####

# HTIF exit: tohost = (exit_code << 1) | 1. fesvr turns a nonzero exit code into a nonzero
# simulator exit status.
#define RVMODEL_HALT_PASS  \
  li x1, 1                ;\
  la t0, tohost           ;\
  write_tohost_pass:      ;\
    sd x1, 0(t0)          ;\
    j write_tohost_pass   ;\

#define RVMODEL_HALT_FAIL \
  li x1, 3                ;\
  la t0, tohost           ;\
  write_tohost_fail:      ;\
    sd x1, 0(t0)          ;\
    j write_tohost_fail   ;\

##### IO #####

# HTIF console: device 1 (bcd), command 1 (putchar). fesvr polls tohost over TSI and clears it
# when it takes a command, so wait for tohost to read 0 before writing the next character.
# The bcd device does not acknowledge a write through fromhost.
#define RVMODEL_IO_WRITE_STR(_R1, _R2, _R3, _STR_PTR) \
1:                                ;                   \
  lbu _R1, 0(_STR_PTR)            ;                   \
  beqz _R1, 3f                    ;                   \
  la _R2, tohost                  ;                   \
4:                                ;                   \
  ld _R3, 0(_R2)                  ;                   \
  bnez _R3, 4b                    ;                   \
  li _R3, 0x0101000000000000      ;                   \
  or _R3, _R3, _R1                ;                   \
  sd _R3, 0(_R2)                  ;                   \
  addi _STR_PTR, _STR_PTR, 1      ;                   \
  j 1b                            ;                   \
3:

##### Access Fault #####

# Nothing is mapped at 0x4000_0000, so every access there takes an access fault.
#define RVMODEL_ACCESS_FAULT_ADDRESS 0x40000000

##### Machine Timer #####

# CLINT at 0x0200_0000. mtime advances once per 1000 core cycles in the harness (timebase
# 500 kHz, core clock 500 MHz in the device tree).
#define CLINT_BASE_ADDRESS 0x02000000
#define RVMODEL_MTIME_ADDRESS    (CLINT_BASE_ADDRESS + 0xBFF8)
#define RVMODEL_MTIMECMP_ADDRESS (CLINT_BASE_ADDRESS + 0x4000)
#define RVMODEL_MSIP_ADDRESS     (CLINT_BASE_ADDRESS + 0x0)

#define RVMODEL_MAX_CYCLES_PER_TIMER_TICK 1000
# 8 ticks (8000 cycles) covers the four T-SBI round trips that arm the timer from U-mode.
#define RVMODEL_TIMER_INT_SOON_DELAY 8
# An interrupt raised through the CLINT or the PLIC reaches mip within a few tens of cycles.
#define RVMODEL_INTERRUPT_LATENCY 1000

##### External Interrupts #####


#define RVMODEL_SET_MEXT_INT(_R1, _R2)          \
  li _R1, 1;                                     \
  li _R2, PLIC_BASE_ADDRESS;                     \
  sw _R1, (4*UART_INT_SRC)(_R2);                 \
  li _R1, (1 << UART_INT_SRC);                   \
  li _R2, PLIC_ENABLE_ADDRESS;                   \
  sw _R1, 0(_R2);                                \
  li _R2, PLIC_THRESH_ADDRESS;                   \
  sw zero, 0(_R2);                               \
  li _R2, UART_BASE_ADDRESS;                     \
  li _R1, 1;                                     \
  sb _R1, 0xA(_R2);                              \
  sw _R1, 0x10(_R2);

# Drop the UART interrupt, then claim and complete it. The M context is disabled afterwards so
# that it does not also see a later supervisor external interrupt.
#define RVMODEL_CLR_MEXT_INT(_R1, _R2)          \
  li _R2, UART_BASE_ADDRESS;                     \
  sw zero, 0x10(_R2);                            \
  li _R2, PLIC_CLAIM_ADDRESS;                    \
  lw _R1, 0(_R2);                                \
  sw _R1, 0(_R2);                                \
  li _R2, PLIC_ENABLE_ADDRESS;                   \
  sw zero, 0(_R2);

##### Supervisor Interrupts #####

#define RVMODEL_SET_SEXT_INT(_R1, _R2)          \
  li _R1, 1;                                     \
  li _R2, PLIC_BASE_ADDRESS;                     \
  sw _R1, (4*UART_INT_SRC)(_R2);                 \
  li _R1, (1 << UART_INT_SRC);                   \
  li _R2, PLIC_SENABLE_ADDRESS;                  \
  sw _R1, 0(_R2);                                \
  li _R2, PLIC_STHRESH_ADDRESS;                  \
  sw zero, 0(_R2);                               \
  li _R2, UART_BASE_ADDRESS;                     \
  li _R1, 1;                                     \
  sb _R1, 0xA(_R2);                              \
  sw _R1, 0x10(_R2);

#define RVMODEL_CLR_SEXT_INT(_R1, _R2)          \
  li _R2, UART_BASE_ADDRESS;                     \
  sw zero, 0x10(_R2);                            \
  li _R2, PLIC_SCLAIM_ADDRESS;                   \
  lw _R1, 0(_R2);                                \
  sw _R1, 0(_R2);                                \
  li _R2, PLIC_SENABLE_ADDRESS;                  \
  sw zero, 0(_R2);

#endif // _RVMODEL_MACROS_H
