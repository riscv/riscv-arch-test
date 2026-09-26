#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

#define RVMODEL_DATA_SECTION \
        .pushsection .tohost,"aw",@progbits;                \
        .balign 8; .global tohost; tohost: .dword 0;         \
        .balign 8; .global fromhost; fromhost: .dword 0;     \
        .popsection;

#define STANDARD_SM_SUPPORTED

##### STARTUP #####

# Perform boot operations. Can be empty or left undefined unless needed for
# DUT-specific behavior such as turning on a memory controller or
# initializing custom state.

#define APLIC_BASE       0x0c000000 /* machine APLIC domain base address */
#define SAPLIC_BASE      0x0d000000 /* supervisor APLIC domain base address (child of machine domain) */

/* Machine APLIC domain registers: source 1 is delivered to M-mode (MEXT) */
#define ADDR_DOMAINCFG  (APLIC_BASE + 0x0000) /* control the whole APLIC domain */
#define ADDR_SOURCECFG1 (APLIC_BASE + 0x0004) /* determines how source 1 becomes pending */
#define ADDR_SOURCECFG2 (APLIC_BASE + 0x0008) /* source 2 config: delegate down to the supervisor domain */
#define ADDR_SETIE0     (APLIC_BASE + 0x1e00) /* controls which source numbers are enabled */
#define ADDR_SETIPNUM   (APLIC_BASE + 0x1cdc) /* write interrupt source number to here to set that source interrupt pending */
#define ADDR_CLRIPNUM   (APLIC_BASE + 0x1ddc) /* write interrupt source number to here to clear that source interrupt pending */
#define ADDR_TARGET1    (APLIC_BASE + 0x3004) /* controls where interrupt source 1 is delivered to with what priority level */
#define ADDR_IDELIVERY0 (APLIC_BASE + 0x4000) /* controls whether hart 0 can receive APLIC interrupts */
#define ADDR_ITHRESH0   (APLIC_BASE + 0x4008) /* defines the threshold for hart 0 - set this to 0 allows all interrupt */

/* Supervisor APLIC domain registers: source 2 is delivered to S-mode (SEXT) */
#define ADDR_S_DOMAINCFG  (SAPLIC_BASE + 0x0000)
#define ADDR_S_SOURCECFG2 (SAPLIC_BASE + 0x0008) /* determines how source 2 becomes pending in the supervisor domain */
#define ADDR_S_SETIE0     (SAPLIC_BASE + 0x1e00)
#define ADDR_S_SETIPNUM   (SAPLIC_BASE + 0x1cdc)
#define ADDR_S_CLRIPNUM   (SAPLIC_BASE + 0x1ddc)
#define ADDR_S_TARGET2    (SAPLIC_BASE + 0x3008) /* source 2 delivery target in the supervisor domain */
#define ADDR_S_IDELIVERY0 (SAPLIC_BASE + 0x4000)
#define ADDR_S_ITHRESH0   (SAPLIC_BASE + 0x4008)

#define SM_EDGE1        4 /* setting a source as rising edge sensitive */
#define SOURCECFG_DELEGATE 0x400 /* D=1, child_index=0: delegate a source to the child (supervisor) domain */
#define DOMAINCFG_RUN   0x80000100 /* direct mode (not through MSI) [bit 2 = 0] and allow APLIC to deliver interrupts [bit 8 = 1]*/
#define TARGET1_H0_P1   0x00000001 /* hart 0 and interrupts have priority 1 */
#define SETIE_SRC1      0x2 /* enable source 1 (bit 1) */
#define SETIE_SRC2      0x4 /* enable source 2 (bit 2) */

#define RVMODEL_BOOT \
  /* ---- IMSIC: let the APLIC deliver directly to the M-level and S-level files (eidelivery = 0x40000000) ---- */ \
  li      t0, IMSIC_EIDELIVERY; \
  li      t1, 0x40000000; \
  csrw    miselect, t0; \
  csrw    mireg, t1; \
  csrw    siselect, t0; \
  csrw    sireg, t1; \
  /* ---- Machine APLIC domain: source 1 -> MEXT ---- */ \
  li      t1, ADDR_SOURCECFG1; /* setting up for APLIC */\
  li      t2, SM_EDGE1; \
  sw      t2, 0(t1); \
  li      t1, ADDR_TARGET1; \
  li      t2, TARGET1_H0_P1; \
  sw      t2, 0(t1); \
  li      t1, ADDR_SOURCECFG2; /* delegate source 2 down to the supervisor domain */ \
  li      t2, SOURCECFG_DELEGATE; \
  sw      t2, 0(t1); \
  li      t1, ADDR_DOMAINCFG; \
  li      t2, DOMAINCFG_RUN; \
  sw      t2, 0(t1); \
  li      t1, ADDR_IDELIVERY0; /* allow hart 0 to receive interrupts */ \
  li      t2, 1; \
  sw      t2, 0(t1); \
  li      t1, ADDR_ITHRESH0; \
  sw      zero, 0(t1); \
  li      t1, ADDR_SETIE0; /* Enables source 1*/ \
  li      t2, SETIE_SRC1; \
  sw      t2, 0(t1); \
  /* ---- Supervisor APLIC domain: source 2 -> SEXT ---- */ \
  li      t1, ADDR_S_SOURCECFG2; /* source 2 is rising edge sensitive in the supervisor domain */ \
  li      t2, SM_EDGE1; \
  sw      t2, 0(t1); \
  li      t1, ADDR_S_TARGET2; \
  li      t2, TARGET1_H0_P1; \
  sw      t2, 0(t1); \
  li      t1, ADDR_S_DOMAINCFG; \
  li      t2, DOMAINCFG_RUN; \
  sw      t2, 0(t1); \
  li      t1, ADDR_S_IDELIVERY0; /* allow hart 0 to receive supervisor interrupts */ \
  li      t2, 1; \
  sw      t2, 0(t1); \
  li      t1, ADDR_S_ITHRESH0; \
  sw      zero, 0(t1); \
  li      t1, ADDR_S_SETIE0; /* Enables source 2 */ \
  li      t2, SETIE_SRC2; \
  sw      t2, 0(t1); \
  /* ---- IMSIC: enable the guest interrupt files ---- */ \
  IMSIC_ENABLE_GUEST_FILES

/* Whisper's IMSIC (whisper.json "imsic") serves only the guest external interrupts; the APLIC above delivers MEXT
 * and SEXT directly. The M-level interrupt file is at IMSIC_M_FILE and the S-level file at IMSIC_S_FILE, followed
 * by one guest interrupt file per 4 KiB page; GEILEN is guest_interrupt_count in whisper.json, which
 * UDB_NUM_EXTERNAL_GUEST_INTERRUPTS matches. Writing an interrupt identity to a file's seteipnum_le register
 * (offset 0) makes it pending. The macros below use identity IMSIC_EIID, which RVMODEL_BOOT enables in every guest
 * file. */
#define IMSIC_M_FILE           0x24000000
#define IMSIC_S_FILE           0x28000000
#define IMSIC_GUEST_FILE(_GEI) (IMSIC_S_FILE + ((_GEI) << 12))
#define IMSIC_GEILEN           UDB_NUM_EXTERNAL_GUEST_INTERRUPTS
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
  self_loop_pass:         ;\
    j self_loop_pass      ;\

# Terminate test with a fail indication.
# When the test is run in simulation, this should end the simulation.
#define RVMODEL_HALT_FAIL \
  li x1, 3                ;\
  la t0, tohost           ;\
  write_tohost_fail:      ;\
    sw x1, 0(t0)          ;\
    sw x0, 4(t0)          ;\
  self_loop_fail:         ;\
    j self_loop_fail      ;\

##### IO #####

# Initialization steps needed prior to writing to the console
# _R1, _R2, and _R3 can be used as temporary registers if needed.
# Do not modify any other registers (or make sure to restore them).
# Can be empty or left undefined if no initialization is needed.
 //#define RVMODEL_IO_INIT(_R1, _R2, _R3)

# Prints a null-terminated string using a DUT specific mechanism.
# A pointer to the string is passed in _STR_PTR.
# _R1, _R2, and _R3 can be used as temporary registers if needed.
# Do not modify any other registers (or make sure to restore them).
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

##### Access Fault #####

#define RVMODEL_ACCESS_FAULT_ADDRESS 0x00000000

##### Machine Interrupts #####

// Interrupt latency configuration
#define RVMODEL_INTERRUPT_LATENCY 10

#define RVMODEL_TIMER_INT_SOON_DELAY 10000

##### Machine Timer #####
#define RVMODEL_MAX_CYCLES_PER_TIMER_TICK 1

#define RVMODEL_MTIMECMP_ADDRESS  0x02004000  /* Address of mtimecmp CSR */

#define RVMODEL_MTIME_ADDRESS  0x0200BFF8  /* Address of mtime CSR */

// using APLIC to trigger external interrupts
// - writing source number to ADDR_SETIPNUM sets the interrupt pending
// - writing source number to ADDR_CLRIPNUM clears the pending interrupt
#define RVMODEL_SET_MEXT_INT(_R1, _R2) \
  li      _R1, ADDR_SETIPNUM; /* sets the interrupt to pending*/ \
  li      _R2, 1; \
  sw      _R2, 0(_R1); /* setting source 1 interrupt */

#define RVMODEL_CLR_MEXT_INT(_R1, _R2) \
  li      _R1, ADDR_CLRIPNUM; /* clear the pending interrupt*/ \
  li      _R2, 1; \
  sw      _R2, 0(_R1); /* clear source 1 interrupt */

#define CLINT_BASE_ADDRESS 0x02000000
#define RVMODEL_MSIP_ADDRESS (CLINT_BASE_ADDRESS + 0x0)

##### Supervisor Interrupts #####

#define WHISPER_SSIP_ADDRESS (CLINT_BASE_ADDRESS + 0xC000)

// using the supervisor APLIC domain to trigger supervisor external interrupts
// - source 2 is delegated from the machine domain to the supervisor domain (see RVMODEL_BOOT)
// - writing source number 2 to ADDR_S_SETIPNUM sets the interrupt pending
// - writing source number 2 to ADDR_S_CLRIPNUM clears the pending interrupt
#define RVMODEL_SET_SEXT_INT(_R1, _R2) \
  li      _R1, ADDR_S_SETIPNUM; /* sets the interrupt to pending */ \
  li      _R2, 2; \
  sw      _R2, 0(_R1); /* setting source 2 interrupt */

#define RVMODEL_CLR_SEXT_INT(_R1, _R2) \
  li      _R1, ADDR_S_CLRIPNUM; /* clear the pending interrupt */ \
  li      _R2, 2; \
  sw      _R2, 0(_R1); /* clear source 2 interrupt */


#endif // _RVMODEL_MACROS_H
