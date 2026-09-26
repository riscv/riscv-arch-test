# rvmodel_macros.h
# DUT-specific macro definitions for Spike
# Jordan Carlin jcarlin@hmc.edu Jan 2026
# SPDX-License-Identifier: BSD-3-Clause

#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

#define RVMODEL_DATA_SECTION \
        .pushsection .tohost,"aw",@progbits;                \
        .balign 8; .global tohost; tohost: .dword 0;         \
        .balign 8; .global fromhost; fromhost: .dword 0;     \
        .popsection

#define STANDARD_SM_SUPPORTED

##### STARTUP #####

# Perform boot operations. Can be empty or left undefined unless needed for
# DUT-specific behavior such as turning on a memory controller or
# initializing custom state.
// RVMODEL_BOOT is defined with the interrupt controllers below when Smaia is supported

// Custom RVMODEL_BOOT_TO_MMODE overrides default RVTEST_BOOT_TO_MMODE
// if defined.  For most DUTs, the default should work and this macro
// should not be defined.  If no M-mode or CSRs are implemented, define this
// macro as blank to bypass the boot process.  If a nonconforming
// M-mode is implemented, define this macro to set up the necessary
// state in a fashion similar to RVTEST_BOOT_TO_MMODE.
//#define RVMODEL_BOOT_TO_MMODE

##### TERMINATION #####

# Terminate test with a pass indication.
# When the test is run in simulation, this should end the simulation.
#define RVMODEL_HALT_PASS  \
  li x1, 1                ;\
  la t0, tohost           ;\
  write_tohost_pass:      ;\
    sw x1, 0(t0)          ;\
    sw x0, 4(t0)          ;\
    j write_tohost_pass   ;\

# Terminate test with a fail indication.
# When the test is run in simulation, this should end the simulation.
#define RVMODEL_HALT_FAIL \
  li x1, 3                ;\
  la t0, tohost           ;\
  write_tohost_fail:      ;\
    sw x1, 0(t0)          ;\
    sw x0, 4(t0)          ;\
    j write_tohost_fail   ;\

##### IO #####

# Example UART implementation.
# Expects a PC16550-compatible UART.
# Change these addresses to match your memory map
.EQU UART_BASE_ADDR, 0x10000000
.EQU UART_THR, (UART_BASE_ADDR + 0)
.EQU UART_LCR, (UART_BASE_ADDR + 3)
.EQU UART_LSR, (UART_BASE_ADDR + 5)

# Initialization steps needed prior to writing to the console
# _R1, _R2, and _R3 can be used as temporary registers if needed.
# Do not modify any other registers (or make sure to restore them).
# Can be empty or left undefined if no initialization is needed.
#define RVMODEL_IO_INIT(_R1, _R2, _R3)    \
  uart_init:                ;\
    li _R1, UART_LCR         ; /* Load address of UART LCR */    \
    li _R2, 3                ; /* 8-bit characters, 1 stop bit, no parity */ \
    sb _R2, 0(_R1)           ; \

# Prints a null-terminated string using a DUT specific mechanism.
# A pointer to the string is passed in _STR_PTR.
# _R1, _R2, and _R3 can be used as temporary registers if needed.
# Do not modify any other registers (or make sure to restore them).
#define RVMODEL_IO_WRITE_STR(_R1, _R2, _R3, _STR_PTR)               \
1:                           ;                       \
  lbu _R1, 0(_STR_PTR)        ;/* Load byte */        \
  beqz _R1, 3f                ;/* Exit if null */     \
2: /* uart_putc */           ;                      \
  li _R2, UART_LSR ;\
  4: /* uart_putc_wait_busy */ \
    lbu _R3, 0(_R2) ;\
    andi _R3, _R3, 0x20 ;/* check line status register bit 5 */ \
    beqz _R3, 4b ;/* wait until Transmit Holding Register Empty is set */ \
  /* uart_putc_send */ \
    li _R2, UART_THR ; /* transmit character */ \
    sb _R1, 0(_R2) ;\
  addi _STR_PTR, _STR_PTR, 1 ;/* Next char */        \
  j 1b                       ;/* Loop */             \
3:

##### Access Fault #####

#define RVMODEL_ACCESS_FAULT_ADDRESS 0x00000000

##### Machine Timer #####

#define RVMODEL_MTIME_ADDRESS  0x0200BFF8  /* Address of mtime CSR */

#define RVMODEL_MTIMECMP_ADDRESS 0x02004000 /* Address of mtimecmp CSR */

##### Machine Interrupts #####

#define RVMODEL_INTERRUPT_LATENCY 4096

#define RVMODEL_TIMER_INT_SOON_DELAY 1000

#define RVMODEL_MAX_CYCLES_PER_TIMER_TICK 5000

#define CLINT_BASE_ADDRESS 0x02000000
#define RVMODEL_MSIP_ADDRESS (CLINT_BASE_ADDRESS + 0x0)

#ifdef SMAIA_SUPPORTED

/* With Smaia, Spike replaces the PLIC with an APLIC in MSI mode feeding an IMSIC per hart. The M-level interrupt
 * file is at IMSIC_M_FILE and the S-level file at IMSIC_S_FILE, followed by one guest interrupt file per 4 KiB
 * page; GEILEN is 31 (riscv/platform.h), whatever the XLEN. Writing an interrupt identity to a file's seteipnum_le
 * register (offset 0) makes it pending. The macros below use identity IMSIC_EIID, which RVMODEL_BOOT enables in
 * the M-level file and in every guest file. */
#define IMSIC_M_FILE           0x24000000
#define IMSIC_S_FILE           0x28000000
#define IMSIC_GUEST_FILE(_GEI) (IMSIC_S_FILE + ((_GEI) << 12))
#define IMSIC_GEILEN           31
#define IMSIC_EIID             1
#define IMSIC_EIDELIVERY       0x70  /* indirect register numbers, AIA section 3.8 */
#define IMSIC_EITHRESHOLD      0x72
#define IMSIC_EIE0             0xC0

/* Enable delivery of identity IMSIC_EIID with no threshold in the file reached through _SEL and _REG
 * (miselect and mireg, or vsiselect and vsireg). */
#define IMSIC_ENABLE_FILE(_SEL, _REG) \
  li t0, IMSIC_EIDELIVERY;  csrw _SEL, t0; li t1, 1; csrw _REG, t1; \
  li t0, IMSIC_EITHRESHOLD; csrw _SEL, t0; csrw _REG, zero; \
  li t0, IMSIC_EIE0;        csrw _SEL, t0; li t1, 1 << IMSIC_EIID; csrs _REG, t1;

#if defined(H_SUPPORTED) && defined(SSAIA_SUPPORTED)
  /* hstatus.VGEIN selects the guest file that vsiselect and vsireg reach; walk it over 1..IMSIC_GEILEN */
  #define IMSIC_ENABLE_GUEST_FILES \
    csrr t2, hstatus; \
    li t3, 1; \
    1: slli t0, t3, 12; csrw hstatus, t0; \
    IMSIC_ENABLE_FILE(vsiselect, vsireg) \
    addi t3, t3, 1; li t0, IMSIC_GEILEN; bleu t3, t0, 1b; \
    csrw hstatus, t2;
#else
  #define IMSIC_ENABLE_GUEST_FILES
#endif

#define RVMODEL_BOOT \
  IMSIC_ENABLE_FILE(miselect, mireg) \
  IMSIC_ENABLE_GUEST_FILES

/* Machine external interrupt: pend IMSIC_EIID in the M-level file, and claim it through mtopei to clear.
 * RVMODEL_CLR_MEXT_INT runs below M-mode, so it claims through the T-SBI. */
#define RVMODEL_SET_MEXT_INT(_R1, _R2) \
  li _R1, IMSIC_EIID;                  \
  li _R2, IMSIC_M_FILE;                \
  sw _R1, 0(_R2);

#define RVMODEL_CLR_MEXT_INT_M(_R1, _R2) \
  csrw mtopei, zero;

#define RVMODEL_CLR_MEXT_INT(_R1, _R2) \
  RVTEST_TSBI_CSR_WRITE(CSR_MTOPEI, 0)

/* The clear below M-mode takes one trap (the T-SBI ecall), which rvtest_trap_count sees. This tells sail_macros.h
 * to give the Sail clear the same trap, so the trap counts in the Sail signature match. */
#define RVMODEL_CLR_MEXT_INT_TSBI

/* Supervisor external interrupts use the software-writable mip.SEIP, the default when RVMODEL_SET/CLR_SEXT_INT
 * are left undefined. */

/* Guest external interrupt _GEI: pend IMSIC_EIID in guest file _GEI, which makes hgeip bit _GEI read 1.
 * To clear, claim it through vstopei with hstatus.VGEIN = _GEI, then restore hstatus.  Below M-mode the
 * vstopei access needs mstateen0.IMSIC = 1.  vsiselect is left untouched. */
#if defined(H_SUPPORTED) && defined(SSAIA_SUPPORTED)
  #define RVMODEL_SET_GUEST_EXT_INT(_GEI, _R1, _R2) \
    li _R1, IMSIC_EIID;                            \
    LI(_R2, IMSIC_GUEST_FILE(_GEI));               \
    sw _R1, 0(_R2);

  #define RVMODEL_CLR_GUEST_EXT_INT(_GEI, _R1, _R2) \
    csrr _R1, hstatus;                             \
    li _R2, HSTATUS_VGEIN;                         \
    csrc hstatus, _R2;                             \
    li _R2, (_GEI) << 12;                          \
    csrs hstatus, _R2;                             \
    csrw vstopei, zero;                            \
    csrw hstatus, _R1;
#endif

#else // SMAIA_SUPPORTED: PLIC

#define PLIC_BASE_ADDRESS    0x0c000000
#define PLIC_ENABLE_ADDRESS  0x0c002000
#define PLIC_THRESH_ADDRESS  0x0c200000
#define PLIC_CLAIM_ADDRESS   0x0c200004
#define PLIC_SENABLE_ADDRESS 0x0c002080   /* For S mode */
#define PLIC_STHRESH_ADDRESS 0x0c201000
#define PLIC_SCLAIM_ADDRESS  0x0c201004
#define NS16550_BASE_ADDRESS 0x10000000
#define UART_INT_SRC         1            /* NS16550 interrupt source ID in Spike */

/* Generates machine external interrupt via PLIC + NS16550 UART transmitter interrupt.
 * The UART throws an interrupt because the THR (Transmit Holding Register) defaults to empty.
 * Steps:
 * - Configures PLIC UART_INT_SRC to priority 7
 * - Enables UART_INT_SRC in PLIC
 * - Sets PLIC priority threshold to 0
 * - Sets UART IER.ETBEI (Interrupt Enable Register - Enable Transmitter Holding Register Empty Interrupt)
 * The PLIC sees that the UART source is enabled and has priority greater than the threshold,
 * so PLIC asserts Machine External Interrupt. */
#define RVMODEL_SET_MEXT_INT(_R1, _R2)          \
  li _R1, 7;                                     \
  li _R2, PLIC_BASE_ADDRESS;                     \
  sw _R1, (4*UART_INT_SRC)(_R2);                 \
  li _R1, (1 << UART_INT_SRC);                   \
  li _R2, PLIC_ENABLE_ADDRESS;                   \
  sw _R1, 0(_R2);                                \
  li _R2, PLIC_THRESH_ADDRESS;                   \
  sw zero, 0(_R2);                               \
  li _R1, 0x02;                                  \
  li _R2, NS16550_BASE_ADDRESS;                  \
  sb _R1, 1(_R2);

/* Clears machine external interrupt:
 * - Turns off UART interrupt by disabling IER.ETBEI
 * - Reads the PLIC Claim register and writes it back to deassert Machine External Interrupt */
#define RVMODEL_CLR_MEXT_INT(_R1, _R2)          \
  li _R2, NS16550_BASE_ADDRESS;                  \
  sb zero, 1(_R2);                               \
  li _R2, PLIC_CLAIM_ADDRESS;                    \
  lw _R1, 0(_R2);                                 \
  sw _R1, 0(_R2);                               \
  li _R2, PLIC_ENABLE_ADDRESS;  /* Since SEXT and MEXT interrupt contexts share the same source, PLIC must be disabled for MEXT context so that it can properly trigger SEXT */\
  sw zero, 0(_R2);

##### Supervisor Interrupts #####

#define RVMODEL_SET_SEXT_INT(_R1, _R2)          \
  li _R1, 7;                                     \
  li _R2, PLIC_BASE_ADDRESS;                     \
  sw _R1, (4*UART_INT_SRC)(_R2);                 \
  li _R1, (1 << UART_INT_SRC);                   \
  li _R2, PLIC_SENABLE_ADDRESS;                   \
  sw _R1, 0(_R2);                                \
  li _R2, PLIC_STHRESH_ADDRESS;                   \
  sw zero, 0(_R2);                               \
  li _R1, 0x02;                                  \
  li _R2, NS16550_BASE_ADDRESS;                  \
  sb _R1, 1(_R2);

/* PLIC does not need to be disabled when clearing SEXT INT since Spike checks the contexts in order (M -> S)
 * Leaving PLIC enabled with S context does not affect MEXT
*/
#define RVMODEL_CLR_SEXT_INT(_R1, _R2)          \
  li _R2, NS16550_BASE_ADDRESS;                  \
  sb zero, 1(_R2);                               \
  li _R2, PLIC_SCLAIM_ADDRESS;                    \
  lw _R1, 0(_R2);                               \
  sw _R1, 0(_R2);

#endif // SMAIA_SUPPORTED

#endif // _RVMODEL_MACROS_H
