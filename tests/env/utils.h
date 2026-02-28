# utils.h
# Utility macros for riscv-arch-test
# Jordan Carlin jcarlin@hmc.edu November 2025
# SPDX-License-Identifier: BSD-3-Clause

# General utility macros
#define MIN(a,b) (((a)<(b))?(a):(b))
#define MAX(a,b) (((a)>(b))?(a):(b))
#define BIT(addr, bit) (((addr)>>(bit))&1)
#define MASK (((1<<(XLEN-1))-1) + (1<<(XLEN-1))) // XLEN bits of 1s
#define MASK_XLEN(val)  val&MASK // shortens 64b values to XLEN when XLEN==32

# Constants and sign extension macros (TODO: Check which of these are actually needed for ACT 4.0)
#define WDSZ 32
#define WDSGN (WDSZ -1)
#define WDMSK ((1 << WDSZ) -1)
#define SEXT_WRD(x) ((x & WDMSK) | (-BIT((x), WDSGN)<< WDSZ))
#define IMMSZ 12
#define IMMSGN (IMMSZ -1)
#define IMMMSK ((1 << IMMSZ)-1)
#define SEXT_IMM(x) ((x & IMMMSK) | (-BIT((x), IMMSGN)<< IMMSZ))

#define LIMMSZ (WDSZ - IMMSZ)
#define LIMMSGN (LIMMSZ -1)
#define LIMMMSK ((1 <<LIMMSZ)-1)
#define SEXT_LIMM(x) ((x &LIMMMSK) | (-BIT((x),LIMMSGN)<<LIMMSZ))

#define WDBYTSZ (WDSZ >> 3)  // in units of #bytes
#define WDBYTMSK (WDBYTSZ-1)

# XLEN specific macros
#define REGWIDTH (XLEN>>3)      // in units of #bytes
#define ALIGNSZ ((XLEN>>5)+2)   // log2(XLEN): 2,3,4 for XLEN 32,64,128

#if   XLEN==32
    #define SREG sw
    #define LREG lw
#elif XLEN==64
    #define SREG sd
    #define LREG ld
#else
    #define SREG sq
    #define LREG lq
#endif

# FLEN specific macros
#define FREGWIDTH (FLEN>>3)      // in units of #bytes

#ifdef ZFINX
  #define FLREG LREG
  #define FSREG SREG
#else
  #if FLEN==32
    #define FLREG flw
    #define FSREG fsw
  #elif FLEN==64
    #define FLREG fld
    #define FSREG fsd
  #elif FLEN==128
    #define FLREG flq
    #define FSREG fsq
  #endif
#endif

// Default VDSEW to 0 for non-vector tests
#ifndef VDSEW
  #define VDSEW 0
#endif
#define VDSEWWIDTH (VDSEW>>3)  // in units of #bytes

// Max data size alignment for signature and data region
// Max of XLEN, FLEN, and SEW
#if XLEN>FLEN
  #define _SIG_STRIDE_1 REGWIDTH
#else
  #define _SIG_STRIDE_1 FREGWIDTH
#endif

#if (VDSEWWIDTH > _SIG_STRIDE_1)
  #define SIG_STRIDE VDSEWWIDTH
#else
  #define SIG_STRIDE _SIG_STRIDE_1
#endif

// Define XLEN-sized pointer directive
#if XLEN == 64
  #define RVTEST_WORD_PTR .dword
#else
  #define RVTEST_WORD_PTR .word
#endif


// RVTEST_TESTDATA_LOAD_INT(data_ptr, dest_reg) loads an integer value from the
// test data section into dest_reg and increments the data_ptr pointer by SIG_STRIDE.
// This macro is used to load integer test values from the .data section.
//  _DATA_PTR - Pointer register to current position in test data section (will be incremented)
//  _DEST_REG - Destination register to load the value into
#define RVTEST_TESTDATA_LOAD_INT(_DATA_PTR, _DEST_REG)  \
  LREG _DEST_REG, 0(_DATA_PTR)                          ;\
  addi _DATA_PTR, _DATA_PTR, SIG_STRIDE

// RVTEST_TESTDATA_LOAD_FLOAT(data_ptr, dest_reg) loads a floating-point value from the
// test data section into dest_reg and increments the data_ptr pointer by SIG_STRIDE.
// This macro is used to load floating point test values from the .data section.
//  _DATA_PTR - Pointer register to current position in test data section (will be incremented)
//  _DEST_REG - Floating point destination register to load the value into
// The default version loads the full FLEN width. Variants for smaller widths use an _SIZE suffix.
#define RVTEST_TESTDATA_LOAD_FLOAT(_DATA_PTR, _DEST_REG)  \
  FLREG _DEST_REG, 0(_DATA_PTR)                          ;\
  addi _DATA_PTR, _DATA_PTR, SIG_STRIDE

#define RVTEST_TESTDATA_LOAD_FLOAT_SINGLE(_DATA_PTR, _DEST_REG)  \
  flw _DEST_REG, 0(_DATA_PTR)                          ;\
  addi _DATA_PTR, _DATA_PTR, SIG_STRIDE

#define RVTEST_TESTDATA_LOAD_FLOAT_DOUBLE(_DATA_PTR, _DEST_REG)  \
  fld _DEST_REG, 0(_DATA_PTR)                          ;\
  addi _DATA_PTR, _DATA_PTR, SIG_STRIDE

#define RVTEST_TESTDATA_LOAD_FLOAT_HALF(_DATA_PTR, _DEST_REG)  \
  flh _DEST_REG, 0(_DATA_PTR)                          ;\
  addi _DATA_PTR, _DATA_PTR, SIG_STRIDE

#define RVTEST_TESTDATA_LOAD_FLOAT_QUAD(_DATA_PTR, _DEST_REG)  \
  flq _DEST_REG, 0(_DATA_PTR)                          ;\
  addi _DATA_PTR, _DATA_PTR, SIG_STRIDE


// RVTEST_FP_ENABLE enables the floating-point unit
// - Sets mstatus.fs to INITIAL
// - Clears fcsr
#define RVTEST_FP_ENABLE(HELPER_GPR)                 \
  LI(HELPER_GPR, (MSTATUS_FS & (MSTATUS_FS >> 1)))  ;\
  csrs mstatus, HELPER_GPR                          ;\
  csrwi fcsr, 0

// RVTEST_V_ENABLE enables the vector unit
// Perform the following steps:
// - Set mstatus.vs to INITIAL
// - Read out vlenb and store in VLENB_CACHE
#define RVTEST_V_ENABLE(VLENB_CACHE, HELPER_GPR)       \
    LI(HELPER_GPR, (MSTATUS_VS & (MSTATUS_VS >> 1)))  ;\
    csrs mstatus, HELPER_GPR                          ;\
    csrr VLENB_CACHE, vlenb


//-----------------------------------------------------------------------
//Fixed length la, li macros; # of ops is ADDR_SZ dependent, not data dependent
//-----------------------------------------------------------------------

/**** fixed length LI macro ****/
// this generates a constants using the standard addi or lui/addi sequences
// but also handles cases that are contiguous bit masks in any position,
// and also constants handled with the addi/lui/addi but are shifted left
#if (XLEN<64)
  #define LI(reg, imm)                                                            ;\
    .option push                                                                  ;\
    .option norelax                                                               ;\
    .option norvc                                                                 ;\
    .set immx,    (imm & MASK)    /* trim to XLEN (noeffect on RV64)        */    ;\
    .set absimm,  ((immx^(-BIT(immx,XLEN-1)))&MASK) /* cvt to posnum to simplify code */  ;\
    .set cry,     (BIT(imm, IMMSGN))                                              ;\
    .set imm12,   (SEXT_IMM(immx))                                                ;\
    .if     ((absimm>>IMMSGN)==0) /* fits 12b signed imm (properly sgnext)? */    ;\
      li   reg, imm12             /* yes, <= 12bit, will be simple li       */    ;\
    .else                                                                         ;\
      lui  reg, (((immx>>IMMSZ)+cry) & LIMMMSK)     /* <= 32b, use lui/addi */    ;\
      .if   ((imm&IMMMSK)!=0)     /* but skip this if lower bits are zero   */    ;\
        addi reg, reg, imm12                                                      ;\
      .endif                                                                      ;\
    .endif                                                                        ;\
    .option pop
#else
  #define LI(reg, imm)                                                            ;\
    .option push                                                                  ;\
    .option norelax                                                               ;\
    .option norvc                                                                 ;\
    .set immx,    (imm & MASK)    /* trim to XLEN (noeffect on RV64)      */      ;\
  /***************** used in loop that detects bitmasks                   */      ;\
    .set edge1,   1               /* 1st "1" bit pos scanning r to l      */      ;\
    .set edge2,   0               /* 1st "0" bit pos scanning r to l      */      ;\
    .set fnd1,    -1              /* found 1st "1" bit pos scanning r to l */     ;\
    .set fnd2,    -1              /* found 1st "0" bit pos scanning r to l */     ;\
    .set imme,    ((immx^(-BIT(immx,0     )))&MASK) /* cvt to even, cvt back at end */    ;\
    .set pos,      0                                                              ;\
  /***************** used in code that checks for 32b immediates          */      ;\
    .set absimm,  ((immx^(-BIT(immx,XLEN-1)))&MASK) /* cvt to posnum to simplify code */  ;\
    .set cry,     (BIT(immx, IMMSGN))                                             ;\
    .set imm12,   (SEXT_IMM(immx))                                                ;\
  /***************** used in code that generates bitmasks                 */      ;\
    .set even,    (1-BIT(imm, 0)) /* imm has at least 1 trailing zero     */      ;\
    .set cryh,    (BIT(immx, IMMSGN+32))                                          ;\
  /******** loop finding rising/falling edge fm LSB-MSB given even operand ****/  ;\
    .rept XLEN                                                                    ;\
      .if   (fnd1<0)              /* looking for first edge?              */      ;\
        .if (BIT(imme,pos)==1)    /* look for falling edge[pos]           */      ;\
          .set  edge1,pos         /* fnd falling edge, don't chk for more */      ;\
          .set  fnd1,0                                                            ;\
        .endif                                                                    ;\
      .elseif (fnd2<0)            /* looking for second edge?             */      ;\
        .if (BIT(imme,pos)==0)    /* yes, found rising edge[pos]?         */      ;\
          .set  edge2, pos        /* fnd rising  edge, don't chk for more */      ;\
          .set  fnd2,0                                                            ;\
        .endif                                                                    ;\
      .endif                                                                      ;\
      .set    pos,  pos+1         /* keep looking (even if already found) */      ;\
    .endr                                                                         ;\
  /***************** used in code that generates shifted 32b values       */      ;\
    .set immxsh, (immx>>edge1)    /* *sh variables only used if positive  */      ;\
    .set imm12sh,(SEXT_IMM(immxsh))/* look @1st 12b of shifted imm val    */      ;\
    .set crysh,     (BIT(immxsh, IMMSGN))                                         ;\
    .set absimmsh, immxsh         /* pos, no inversion needed, just shift */      ;\
  /*******does it fit into std li or lui+li sequence****************************/ ;\
    .if     ((absimm>>IMMSGN)==0) /* fits 12b signed imm (properly sgnext)? */    ;\
      li   reg, imm12             /* yes, <= 12bit, will be simple li       */    ;\
    .elseif ((absimm+ (cry << IMMSZ) >> WDSGN)==0)/*fits 32b sgnimm?(w/ sgnext)?*/;\
      lui  reg, (((immx>>IMMSZ)+cry) & LIMMMSK)     /* <= 32b, use lui/addi */    ;\
      .if   ((imm&IMMMSK)!=0)     /* but skip this if lower bits are zero   */    ;\
        addi reg, reg, imm12                                                      ;\
      .endif                                                                      ;\
  /*********** look for  0->1->0 masks, or inverse sgl/multbit *************/     ;\
    .elseif ( even && (fnd2<0))           /* only rising  edge, so 111000   */    ;\
      li      reg, -1                                                             ;\
      slli    reg, reg, edge1             /* make 111s --> 000s mask        */    ;\
    .elseif (!even && (fnd2<0))           /* only falling edge, so 000111   */    ;\
      li      reg, -1                                                             ;\
      srli    reg, reg, XLEN-edge1        /* make 000s --> 111s mask        */    ;\
    .elseif (imme == (1<<edge1))          /* check for single bit case      */    ;\
      li      reg, 1                                                              ;\
      slli    reg, reg, edge1             /* make 0001000 sgl bit mask      */    ;\
      .if   (!even)                                                               ;\
        xori    reg, reg, -1              /* orig odd, cvt to 1110111 mask  */    ;\
      .endif                                                                      ;\
    .elseif (imme == ((1<<edge2) - (1<<edge1))) /* chk for multibit case    */    ;\
      li      reg, -1                                                             ;\
      srli    reg, reg, XLEN-(edge2-edge1)     /* make multibit 1s mask     */    ;\
      slli    reg, reg, edge1             /* and put it into position       */    ;\
      .if   (!even)                                                               ;\
        xori    reg, reg, -1              /* orig odd, cvt to 1110111 mask  */    ;\
      .endif                                                                      ;\
    /************** look for 12b or 32b imms with trailing zeroes ***********/    ;\
    .elseif ((immx==imme)&&((absimmsh>>IMMSGN)==0))/* fits 12b after shift? */    ;\
      li      reg, imm12sh                /* <= 12bit, will be simple li    */    ;\
      slli    reg, reg, edge1             /* add trailing zeros             */    ;\
    .elseif ((immx==imme)&&(((absimmsh>>WDSGN)+crysh)==0)) /* fits 32 <<shift? */ ;\
      lui     reg, ((immxsh>>IMMSZ)+crysh)&LIMMMSK     /* <=32b, use lui/addi */  ;\
      .if   ((imm12sh&IMMMSK)!=0)         /* but skip this if low bits ==0  */    ;\
        addi    reg, reg, imm12sh                                                 ;\
      .endif                                                                      ;\
      slli    reg, reg, edge1             /* add trailing zeros             */    ;\
    .else                                 /* give up, use fixed 8op sequence*/    ;\
    /******* TBD add sp case of zero short imms, rmv add/merge shifts  ******/    ;\
      lui     reg, ((immx>>(XLEN-LIMMSZ))+cryh)&LIMMMSK     /* 1st 20b (63:44) */ ;\
      addi    reg, reg, SEXT_IMM(immx>>32)                /* nxt 12b (43:32) */   ;\
      slli    reg, reg, 11        /* following are <12b, don't need SEXT     */   ;\
      addi    reg, reg, (immx>>21) & (IMMMSK>>1)          /* nxt 11b (31:21) */   ;\
      slli    reg, reg, 11                                /* mk room for 11b */   ;\
      addi    reg, reg, (immx>>10) & (IMMMSK>>1)          /* nxt 11b (20:10) */   ;\
      slli    reg, reg, 10                                /* mk room for 10b */   ;\
      .if   ((imm&(IMMMSK>>2))!=0) /* but skip this if lower bits are zero   */   ;\
        addi    reg, reg, (immx)     & (IMMMSK>>2)        /* lst 10b (09:00) */   ;\
      .endif                                                                      ;\
      .if (XLEN==32)                                                              ;\
        .warning "Should never get here for RV32"                                 ;\
      .endif                                                                      ;\
    .endif                                                                        ;\
  .option pop
#endif

# Alignment size for LA macro. Must be larger than the longest instruction
# sequence that the la pseudo-instruction can expand into (to account for the jump hack).
# On some rv64 targets, this may need to be increased to 6.
#ifndef UNROLLSZ
  #define UNROLLSZ 5
#endif

/**** fixed length LA macro; alignment and rvc/norvc unknown before execution ****/
#define LA(reg,val) ;\
  .ifnc(reg, X0)    ;\
    .option push    ;\
    .option rvc     ;\
    .align UNROLLSZ ;\
    .option norvc   ;\
    la reg,val      ;\
    .align UNROLLSZ ;\
    .option pop     ;\
  .endif

// CSR Macros
// each access is followed by a nop in case the access causes a trap
// because the trap return skips the next instruction

#define CSRRW(_R2, _CSR, _R1) \
    csrrw _R2, _CSR, _R1      ;\
    nop

#define CSRRS(_R2, _CSR, _R1) \
    csrrs _R2, _CSR, _R1      ;\
    nop

#define CSRRC(_R2, _CSR, _R1) \
    csrrc _R2, _CSR, _R1      ;\
    nop

#define CSRR(_R2, _CSR) \
    csrr _R2, _CSR      ;\
    nop

#define CSRW(_CSR, _R1) \
    csrw _CSR, _R1      ;\
    nop

#define CSRS(_CSR, _R1) \
    csrs _CSR, _R1      ;\
    nop

#define CSRC(_CSR, _R1) \
    csrc _CSR, _R1      ;\
    nop

// Macros for instructions that can trap
// each instruction is followed by a nop in case the access causes a trap
// because the trap return skips the next instruction

#define SFENCE_VMA \
    sfence.vma         ;\
    nop

// Utility Macros

// Place 1 in msb
#if XLEN == 64
#define SET_MSB(_R) \
    LI(_R, 0x8000000000000000)
#else  /* XLEN == 32 */
#define SET_MSB(_R) \
    LI(_R, 0x80000000)
#endif

// Interrupt Macros
// Idle for interrupt latency
#define RVTEST_IDLE_FOR_INTERRUPT \
   .rept RVMODEL_INTERRUPT_LATENCY; \
       nop; \
   .endr


// Using generic RVTEST macros that can be invoked by tests, which then jump to the appropriate RVMODEL macros that implement the interrupt setup for the specific target platform.
// This allows tests to be portable across different platforms with different interrupt implementations.
#define RVTEST_SET_MSW_INT \
  jal rvtest_set_msw_int     /* Trigger machine software interrupt */

#define RVTEST_CLR_MSW_INT \
  jal rvtest_clr_msw_int     /* Clear machine software interrupt */

#define RVTEST_SET_MEXT_INT \
  jal rvtest_set_mext_int     /* Trigger machine external interrupt */

#define RVTEST_CLR_MEXT_INT \
  jal rvtest_clr_mext_int     /* Clear machine external interrupt */

#define RVTEST_SET_SSW_INT \
  jal rvtest_set_ssw_int     /* Trigger supervisor software interrupt */

#define RVTEST_CLR_SSW_INT \
  jal rvtest_clr_ssw_int     /* Clear supervisor software interrupt */

#define RVTEST_SET_SEXT_INT \
  jal rvtest_set_sext_int     /* Trigger supervisor external interrupt */

#define RVTEST_CLR_SEXT_INT \
  jal rvtest_clr_sext_int     /* Clear supervisor external interrupt */


// V-mode interrupts not yet supported in Sail reference model
// Define as empty to prevent assembly errors
#define RVTEST_SET_VSW_INT
#define RVTEST_CLR_VSW_INT
#define RVTEST_SET_VEXT_INT
#define RVTEST_CLR_VEXT_INT

// Timer interrupts (no parameters)
#define RVTEST_CLR_STIMER_INT
#define RVTEST_CLR_VTIMER_INT

// RVMODEL macros for DUT specific interrupts. These implement the actual interrupt setup for the DUT and are invoked by the generic RVTEST macros.
#define RVTEST_INTERRUPTS \
  rvtest_set_msw_int: ; \
    RVMODEL_SET_MSW_INT(T2, T5) ; \
    ret ; \
  rvtest_clr_msw_int: ; \
    RVMODEL_CLR_MSW_INT(T2, T5) ; \
    ret ; \
  rvtest_set_mext_int: ; \
    RVMODEL_SET_MEXT_INT(T2, T5) ; \
    ret ; \
  rvtest_clr_mext_int: ; \
    RVMODEL_CLR_MEXT_INT(T2, T5) ; \
    ret ; \
  rvtest_set_ssw_int: ; \
    RVMODEL_SET_SSW_INT(T2, T5) ; \
    ret ; \
  rvtest_clr_ssw_int: ; \
    RVMODEL_CLR_SSW_INT(T2, T5) ; \
    csrci sip, 2 ; \
    ret ; \
  rvtest_set_sext_int: ; \
    RVMODEL_SET_SEXT_INT(T2, T5) ; \
    ret ; \
  rvtest_clr_sext_int: ; \
    RVMODEL_CLR_SEXT_INT(T2, T5) ; \
    li T3, 512 ; \
    csrc sip, T3 ; \
    ret
