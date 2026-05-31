#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

#define RVMODEL_DATA_SECTION \
        .pushsection .tohost,"aw",@progbits;                \
        .align 8; .global tohost; tohost: .dword 0;         \
        .align 8; .global fromhost; fromhost: .dword 0;     \
        .popsection;

#define STANDARD_SM_SUPPORTED

##### STARTUP #####

# Perform boot operations. Can be empty or left undefined unless needed for
# DUT-specific behavior such as turning on a memory controller or
# initializing custom state.

#define APLIC_BASE       0x0c000000 /* reference base address */

#define ADDR_DOMAINCFG  (APLIC_BASE + 0x0000) /* control the whole APLIC domain */
#define ADDR_SOURCECFG1 (APLIC_BASE + 0x0004) /* determines how source 1 becomes pending */
#define ADDR_SETIE0     (APLIC_BASE + 0x1e00) /* controls which source numbers are enabled */
#define ADDR_SETIPNUM   (APLIC_BASE + 0x1cdc) /* write interrupt source number to here to set that source interrupt pending */
#define ADDR_CLRIPNUM   (APLIC_BASE + 0x1ddc) /* write interrupt source number to here to clear that source interrupt pending */
#define ADDR_TARGET1    (APLIC_BASE + 0x3004) /* controls where interrupt source 1 is delivered to with what priority level */
#define ADDR_IDELIVERY0 (APLIC_BASE + 0x4000) /* controls whether hart 0 can receive APLIC interrupts */
#define ADDR_ITHRESH0   (APLIC_BASE + 0x4008) /* defines the threshold for hart 0 - set this to 0 allows all interrupt */

#define SM_EDGE1        4 /* setting source 1 as rising edge sensitive */
#define DOMAINCFG_RUN   0x80000100 /* direct mode (not through MSI) [bit 2 = 0] and allow APLIC to deliver interrupts [bit 8 = 1]*/
#define TARGET1_H0_P1   0x00000001 /* hart 0 and interrupts have priority 1 */

#define RVMODEL_BOOT \
  li      t1, ADDR_SOURCECFG1; /* setting up for APLIC */\
  li      t2, SM_EDGE1; \
  sw      t2, 0(t1); \
  li      t1, ADDR_TARGET1; \
  li      t2, TARGET1_H0_P1; \
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
  li      t2, 2; \
  sw      t2, 0(t1);

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

#define RVMODEL_TIMER_INT_SOON_DELAY 100

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

// using CLINT to trigger software interrupts
#define RVMODEL_SET_MSW_INT(_R1, _R2) \
  li      _R2, RVMODEL_MSIP_ADDRESS; \
  li      _R1, 1; \
  sw      _R1, 0(_R2); \

#define RVMODEL_CLR_MSW_INT(_R1, _R2) \
  li      _R1, RVMODEL_MSIP_ADDRESS; \
  sw      x0, 0(_R1);

##### Supervisor Interrupts #####

#define WHISPER_SSIP_ADDRESS (CLINT_BASE_ADDRESS + 0xC000)

#define RVMODEL_SET_SEXT_INT(_R1, _R2)

#define RVMODEL_CLR_SEXT_INT(_R1, _R2)

#define RVMODEL_SET_SSW_INT(_R1, _R2) \
  li _R1, 1; \
  li _R2, WHISPER_SSIP_ADDRESS; \
  sw _R1, 0(_R2);

#define RVMODEL_CLR_SSW_INT(_R1, _R2) \
  li _R2, WHISPER_SSIP_ADDRESS; \
  sw zero, 0(_R2);

#endif // _RVMODEL_MACROS_H
