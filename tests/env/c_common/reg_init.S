#include "encoding.h"

/*
 * Boot-time register-file initialization
 *
 * Reset leaves the architectural register files undefined: hardware can
 * power up with arbitrary values, so a test that happens to read an
 * uninitialized register would observe platform-dependent data. This
 * file holds the clearing routines that entry.S calls during boot.
 *
 *   _fp_reg_init  - clear f0-f31 and fcsr; degenerates to a plain ret
 *                   when the platform config declares no FP extension,
 *                   so entry.S can call it unconditionally.
 *
 * The GPR clearing stays in entry.S (CLEAR_GPRS macro): the first clear
 * runs before sp exists and must not clobber a return address, so it has
 * to be inlined at the reset vector rather than called.
 *
 * Further register files (e.g. the vector registers, gated by
 * mstatus.VS and advertised by misa.V) belong here as well, following
 * the same save-state / clear / restore-state pattern.
 */

/* ===================================================================
 * Constants
 *
 * Plain shift literals: the BIT()/BIT_MASK() helpers in types.h are
 * guarded by #ifndef __ASSEMBLER__ and are therefore invisible here.
 * =================================================================== */
#define MSTATUS_FS_MASK     (3 << 13)   /* mstatus.FS field, bits [14:13] */
#define MSTATUS_FS_INITIAL  (1 << 13)   /* FS = Initial */

/* misa extension bits (norm:misa_extensions_enc_tbl): bit = letter - 'A' */
#define MISA_D              (1 << 3)    /* double-precision FP -> FLEN 64 */
#define MISA_F              (1 << 5)    /* single-precision FP -> FLEN 32 */
#define MISA_Q              (1 << 16)   /* quad-precision FP   -> FLEN 128 */

/* f0-f31 register numbers, expanded by .irp in every FP zeroing path */
#define FP_REG_NUMS \
    0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,\
    16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31

/* FLW / FLD / FLQ frd, 0(a0) - I-type, LOAD-FP major opcode:
 *   [31:20] imm = 0 | [19:15] rs1 = a0 | [14:12] funct3 | [11:7] rd | [6:0]
 */
#define FP_LOAD_OP      0x07
#define FP_LOAD_RS1     10              /* a0 = _fp_zero_window */
#define FP_FUNCT3_W     2               /* FLW: FLEN = 32  */
#define FP_FUNCT3_D     3               /* FLD: FLEN = 64  */
#define FP_FUNCT3_Q     4               /* FLQ: FLEN = 128 */

/* Emit one FP load as a raw encoding.
 *
 * The FLW/FLD/FLQ mnemonics would have to be enabled with ".option
 * arch, +f/+d/+q", which binutils rejects as soon as the suite MARCH
 * carries an extension that is architecturally exclusive with D: the
 * Zcmp suite builds with rv64imach_zicsr_zifencei_zcmp and dies with
 * "zcmp is incompatible with `d' and `c', or `zcd' extension". Giving
 * this object its own -march is no alternative either - ld then refuses
 * to merge the RISC-V target attributes ("failed to merge target
 * specific data"). Raw encodings add no ISA attribute, so the boot path
 * assembles and links unchanged for every suite and every MARCH.
 *
 * This is a GAS macro, not a function-like cpp macro: cpp cannot pass
 * the .irp argument \n through, the backslash is not a valid token.
 */
.macro FP_LOAD funct3, rd
    .word   FP_LOAD_OP | ((\rd) << 7) | ((\funct3) << 12) | (FP_LOAD_RS1 << 15)
.endm

/* ===================================================================
 * _fp_reg_init - clear the floating-point register file at boot
 *
 * Reset leaves f0-f31 and fcsr undefined, so zero them once here to
 * give every test a deterministic FP state.
 *
 * FP state is only accessible while mstatus.FS != Off
 * (norm:mstatus_fs_vs_xs_off_op), so FS is temporarily set to Initial
 * and the boot-time mstatus value is written back afterwards. Changing
 * FS never disturbs the FP register contents (norm:mstatus_fs_wr:
 * "setting fs=Off does not destroy the state"), so the zeroed values
 * survive while no test observes a boot-modified FS/SD field.
 *
 * misa is checked at run time even though the platform config already
 * declares the FP extensions: a simulator may be invoked with an ISA
 * string narrower than the config (spike defaults to
 * rv64imac_zicsr_zifencei, i.e. no F/D at all), and executing an FP
 * instruction there would trap before main() is even reached.
 *
 * A load narrower than FLEN NaN-boxes its result (upper bits all ones)
 * instead of zeroing the register, so the widest FP load the hart
 * advertises is used against a 16-byte zero window: FLQ for misa.Q,
 * FLD for misa.D, FLW for the single-precision case. All three are
 * emitted as raw encodings - see FP_LOAD above for why.
 *
 * Clobbers: a0, t0-t3. Caller: entry.S, after mtvec is installed and
 * BSS is cleared (so an unexpected FP trap is reported by
 * m_trap_handler) and before the final GPR clear and the call to main.
 * =================================================================== */
    .section .text
    .global _fp_reg_init

#if defined(F_SUPPORTED) || defined(D_SUPPORTED) || defined(Q_SUPPORTED)

_fp_reg_init:
    csrr    t0, misa
    li      t1, MISA_F
    and     t1, t0, t1
    beqz    t1, _fp_reg_init_done   /* no FP state: leave mstatus alone */

    /* Save mstatus, then set FS = Initial so FP state is accessible */
    csrr    t1, mstatus
    li      t2, ~MSTATUS_FS_MASK
    and     t3, t1, t2
    li      t2, MSTATUS_FS_INITIAL
    or      t3, t3, t2
    csrw    mstatus, t3

    la      a0, _fp_zero_window

#ifdef Q_SUPPORTED
    li      t2, MISA_Q              /* FLEN = 128 */
    and     t2, t0, t2
    beqz    t2, _fp_check_d
    .irp    n, FP_REG_NUMS
    FP_LOAD FP_FUNCT3_Q, \n         /* flq fN, 0(a0) - N = 0..31 */
    .endr
    j       _fp_restore
_fp_check_d:
#endif

#ifdef D_SUPPORTED
    li      t2, MISA_D              /* FLEN = 64 */
    and     t2, t0, t2
    beqz    t2, _fp_zero_single
    .irp    n, FP_REG_NUMS
    FP_LOAD FP_FUNCT3_D, \n         /* fld fN, 0(a0) - N = 0..31 */
    .endr
    j       _fp_restore
_fp_zero_single:
#endif

    .irp    n, FP_REG_NUMS          /* FLEN = 32 */
    FP_LOAD FP_FUNCT3_W, \n         /* flw fN, 0(a0) - N = 0..31 */
    .endr

_fp_restore:
    csrw    fcsr, zero              /* frm = RNE (0), fflags = 0 */
    csrw    mstatus, t1             /* restore the boot mstatus value */
_fp_reg_init_done:
    ret

    /* 16-byte aligned zero source for the clearing above; wide enough
     * for FLEN = 32, 64 and 128. FLQ additionally requires the source
     * to be naturally aligned, hence the .balign. */
    .section .rodata
    .balign 16
_fp_zero_window:
    .zero   16

#else  /* no FP extension declared by the platform config */

_fp_reg_init:
    ret

#endif
