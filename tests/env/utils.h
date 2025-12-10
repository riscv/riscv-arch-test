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

#if XLEN>FLEN
  #define SIGALIGN REGWIDTH
#else
  #define SIGALIGN FREGWIDTH
#endif

#if   XLEN==32
    #define SREG sw
    #define LREG lw
    #define XLEN_WIDTH 5
#elif XLEN==64
    #define SREG sd
    #define LREG ld
    #define XLEN_WIDTH 6
#else
    #define SREG sq
    #define LREG lq
    #define XLEN_WIDTH 7
#endif

# FLEN specific macros
#if FLEN==32
    #define FLREG flw
    #define FSREG fsw
    #define FREGWIDTH 4
#elif FLEN==64
    #define FLREG fld
    #define FSREG fsd
    #define FREGWIDTH 8
#elif FLEN==128
    #define FLREG flq
    #define FSREG fsq
    #define FREGWIDTH 16
#endif

#if ZFINX==1
    #define FLREG ld
    #define FSREG sd
    #define FREGWIDTH 8
    #define FLEN 64
    #if XLEN==64
        #define SIGALIGN 8
    #else
        #define SIGALIGN 4
    #endif
    #elif ZDINX==1
        #define FLREG LREG
        #define FSREG SREG
        #define FREGWIDTH 8
        #define FLEN 64
    #elif ZHINX==1
        #define FLREG lw
        #define FSREG sw
        #define FREGWIDTH 4
        #define FLEN 32
#endif

//-----------------------------------------------------------------------
//Fixed length la, li macros; # of ops is ADDR_SZ dependent, not data dependent
//-----------------------------------------------------------------------

// this generates a constants using the standard addi or lui/addi sequences
// but also handles cases that are contiguous bit masks in any position,
// and also constants handled with the addi/lui/addi but are shifted left

#ifndef UNROLLSZ
  #define UNROLLSZ 5
#endif

/**** fixed length LI macro ****/
#if (XLEN<64)
  #define LI(reg, imm)                                                            ;\
  .set immx,    (imm & MASK)    /* trim to XLEN (noeffect on RV64)      */      ;\
  .set absimm,  ((immx^(-BIT(immx,XLEN-1)))&MASK) /* cvt to posnum to simplify code */  ;\
  .set cry,     (BIT(imm, IMMSGN))                                              ;\
  .set imm12,   (SEXT_IMM(immx))                                                ;\
  .if     ((absimm>>IMMSGN)==0) /* fits 12b signed imm (properly sgnext)? */    ;\
        li   reg, imm12         /* yes, <= 12bit, will be simple li       */    ;\
  .else                                                                         ;\
        lui  reg, (((immx>>IMMSZ)+cry) & LIMMMSK) /* <= 32b, use lui/addi */    ;\
    .if   ((imm&IMMMSK)!=0)     /* but skip this if lower bits are zero   */    ;\
        addi reg, reg, imm12                                                    ;\
    .endif                                                                      ;\
  .endif
  #else
#define LI(reg, imm)                                                            ;\
  .option push                                                                  ;\
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
/***************** used in code that generates bitmasks                  */      ;\
  .set even,    (1-BIT(imm, 0)) /* imm has at least 1 trailing zero     */      ;\
  .set cryh,    (BIT(immx, IMMSGN+32))                                          ;\
/******** loop finding rising/falling edge fm LSB-MSB given even operand ****/  ;\
  .rept XLEN                                                                    ;\
    .if     (fnd1<0)            /* looking for first edge?              */      ;\
      .if (BIT(imme,pos)==1)    /* look for falling edge[pos]           */      ;\
        .set  edge1,pos         /* fnd falling edge, don’t chk for more */      ;\
        .set  fnd1,0                                                            ;\
      .endif                                                                    ;\
    .elseif (fnd2<0)            /* looking for second edge?             */      ;\
      .if (BIT(imme,pos)==0)    /* yes, found rising edge[pos]?         */      ;\
         .set  edge2, pos       /* fnd rising  edge, don’t chk for more */      ;\
         .set  fnd2,0                                                           ;\
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
        li   reg, imm12         /* yes, <= 12bit, will be simple li       */    ;\
  .elseif ((absimm+ (cry << IMMSZ) >> WDSGN)==0)/*fits 32b sgnimm?(w/ sgnext)?*/;\
        lui  reg, (((immx>>IMMSZ)+cry) & LIMMMSK) /* <= 32b, use lui/addi */    ;\
    .if   ((imm&IMMMSK)!=0)     /* but skip this if lower bits are zero   */    ;\
        addi reg, reg, imm12                                                    ;\
    .endif                                                                      ;\
 /*********** look for  0->1->0 masks, or inverse sgl/multbit *************/    ;\
  .elseif ( even && (fnd2<0))           /* only rising  edge, so 111000   */    ;\
        li      reg, -1                                                         ;\
        slli    reg, reg, edge1         /* make 111s --> 000s mask        */    ;\
  .elseif (!even && (fnd2<0))           /* only falling edge, so 000111   */    ;\
        li      reg, -1                                                         ;\
        srli    reg, reg, XLEN-edge1    /* make 000s --> 111s mask        */    ;\
  .elseif (imme == (1<<edge1))          /* check for single bit case      */    ;\
        li      reg, 1                                                          ;\
        slli    reg, reg, edge1         /* make 0001000 sgl bit mask      */    ;\
    .if   (!even)                                                               ;\
        xori    reg, reg, -1            /* orig odd, cvt to 1110111 mask  */    ;\
    .endif                                                                      ;\
  .elseif (imme == ((1<<edge2) - (1<<edge1))) /* chk for multibit case    */    ;\
        li      reg, -1                                                         ;\
        srli    reg, reg, XLEN-(edge2-edge1) /* make multibit 1s mask     */    ;\
        slli    reg, reg, edge1         /* and put it into position       */    ;\
    .if   (!even)                                                               ;\
        xori    reg, reg, -1            /* orig odd, cvt to 1110111 mask  */    ;\
    .endif                                                                      ;\
  /************** look for 12b or 32b imms with trailing zeroes ***********/    ;\
  .elseif ((immx==imme)&&((absimmsh>>IMMSGN)==0))/* fits 12b after shift? */    ;\
        li      reg, imm12sh            /* <= 12bit, will be simple li    */    ;\
        slli    reg, reg, edge1         /* add trailing zeros             */    ;\
  .elseif ((immx==imme)&&(((absimmsh>>WDSGN)+crysh)==0)) /* fits 32 <<shift? */  ;\
        lui     reg, ((immxsh>>IMMSZ)+crysh)&LIMMMSK /* <=32b, use lui/addi */  ;\
    .if   ((imm12sh&IMMMSK)!=0)         /* but skip this if low bits ==0  */    ;\
        addi    reg, reg, imm12sh                                               ;\
    .endif                                                                      ;\
        slli    reg, reg, edge1         /* add trailing zeros             */    ;\
  .else                                 /* give up, use fixed 8op sequence*/    ;\
  /******* TBD add sp case of zero short imms, rmv add/merge shifts  ******/    ;\
        lui     reg, ((immx>>(XLEN-LIMMSZ))+cryh)&LIMMMSK /* 1st 20b (63:44) */ ;\
        addi    reg, reg, SEXT_IMM(immx>>32)            /* nxt 12b (43:32) */   ;\
        slli    reg, reg, 11    /* following are <12b, don't need SEXT     */   ;\
        addi    reg, reg, (immx>>21) & (IMMMSK>>1)      /* nxt 11b (31:21) */   ;\
        slli    reg, reg, 11                            /* mk room for 11b */   ;\
        addi    reg, reg, (immx>>10) & (IMMMSK>>1)      /* nxt 11b (20:10) */   ;\
        slli    reg, reg, 10                            /* mk room for 10b */   ;\
    .if   ((imm&(IMMMSK>>2))!=0) /* but skip this if lower bits are zero   */   ;\
        addi    reg, reg, (immx)     & (IMMMSK>>2)      /* lst 10b (09:00) */   ;\
    .endif                                                                      ;\
    .if (XLEN==32)                                                              ;\
        .warning "Should never get here for RV32"                               ;\
    .endif                                                                      ;\
 .endif                                                                         ;\
 .option pop
 #endif

/**** fixed length LA macro; alignment and rvc/norvc unknown before execution ****/
#define LA(reg,val)     ;\
    .ifnc(reg, X0)       ;\
        .option push    ;\
        .option rvc     ;\
        .align UNROLLSZ ;\
        .option norvc   ;\
        la reg,val      ;\
        .align UNROLLSZ ;\
        .option pop     ;\
    .endif
#define ADDI(dst, src, imm) /* helper*/ ;\
.if ((imm<=2048) & (imm>=-2048))        ;\
        addi    dst, src, imm           ;\
.else                                   ;\
        LI(     dst, imm)               ;\
        addi    dst, src, dst           ;\
.endif
