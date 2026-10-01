// rvtest_invisible_trap_handler.h
// RISC-V Architecture Test Framework — Invisible Trap Handler
//
// Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
// SPDX-License-Identifier: Apache-2.0
//
// Invisible trap handler for emulated instructions.
//
// The M-mode trap entry saves T1 through T6 and sp before it enters this code.
// This handler fetches the trapped instruction, calls the DUT hook, and then
// tries the framework time-CSR emulation. A handled instruction resumes without
// a trap signature. An unhandled instruction returns to the normal trap path.

.macro RVTEST_INVISIBLE_TIME_HANDLER PC_REG, INSTRUCTION_REG, ACTION_REG, DEST_REG, VALUE_REG
  // Match CSRRS/CSRRC time reads with rs1/uimm equal to zero.
  li      \VALUE_REG, INSN_FIELD_CSR | INSN_FIELD_RS1 | INSN_FIELD_OPCODE | (2 << 12)
  and     \DEST_REG, \INSTRUCTION_REG, \VALUE_REG
  li      \VALUE_REG, (CSR_TIME << 20) | (2 << 12) | 0x73
  beq     \DEST_REG, \VALUE_REG, invisible_Mtime_check_access
  #if UDB_MXLEN == 32
    li      \VALUE_REG, (CSR_TIMEH << 20) | (2 << 12) | 0x73
    bne     \DEST_REG, \VALUE_REG, invisible_Mtime_done
  #else
    j       invisible_Mtime_done
  #endif

  invisible_Mtime_check_access:
    // Check counter permissions before emulating the missing CSR.
    csrr    \DEST_REG, mstatus
    li      \VALUE_REG, MSTATUS_MPP
    and     \DEST_REG, \DEST_REG, \VALUE_REG
    beq     \DEST_REG, \VALUE_REG, invisible_Mtime_read    // If in M-mode, proceed to read the time CSR
    csrr    \VALUE_REG, mcounteren
    andi    \VALUE_REG, \VALUE_REG, MCOUNTEREN_TIME
    beqz    \VALUE_REG, invisible_Mtime_done
    #ifdef H_SUPPORTED
      // From VS or VU (mstatus.MPV = 1), a clear hcounteren.TM, or a clear scounteren.TM
      // in VU, raises a virtual-instruction exception rather than an illegal-instruction one.
      #if UDB_MXLEN == 32
        csrr    \VALUE_REG, CSR_MSTATUSH
        andi    \VALUE_REG, \VALUE_REG, (1 << MPV_LSB)
      #else
        csrr    \VALUE_REG, mstatus
        srli    \VALUE_REG, \VALUE_REG, (32 + MPV_LSB)
        andi    \VALUE_REG, \VALUE_REG, 1
      #endif
      beqz    \VALUE_REG, invisible_Mtime_not_virtual
      csrr    \VALUE_REG, CSR_HCOUNTEREN
      andi    \VALUE_REG, \VALUE_REG, MCOUNTEREN_TIME
      beqz    \VALUE_REG, invisible_Mtime_virtual
      bnez    \DEST_REG, invisible_Mtime_read              // VS-mode
      csrr    \VALUE_REG, scounteren
      andi    \VALUE_REG, \VALUE_REG, MCOUNTEREN_TIME
      bnez    \VALUE_REG, invisible_Mtime_read
    invisible_Mtime_virtual:
      li      \ACTION_REG, 3
      j       invisible_Mtime_done
    invisible_Mtime_not_virtual:
    #endif
    #ifdef S_SUPPORTED
      bnez    \DEST_REG, invisible_Mtime_read              // S-mode access only needs mcounteren.TIME
      csrr    \VALUE_REG, scounteren
      andi    \VALUE_REG, \VALUE_REG, MCOUNTEREN_TIME      // U-mode access also needs scounteren.TIME
      beqz    \VALUE_REG, invisible_Mtime_done
    #endif

  invisible_Mtime_read:
    // T6 is saved by the trap entry, so it is free here.
    li      \VALUE_REG, RVMODEL_MTIME_ADDRESS
    #if UDB_MXLEN == 32
      lw      \DEST_REG, 4(\VALUE_REG)
      lw      \VALUE_REG, 0(\VALUE_REG)
    #else
      ld      \VALUE_REG, 0(\VALUE_REG)
    #endif
    #ifdef H_SUPPORTED
      // time reads as mtime + htimedelta in VS and VU.
      #if UDB_MXLEN == 32
        csrr    T6, CSR_MSTATUSH
        andi    T6, T6, (1 << MPV_LSB)
        beqz    T6, invisible_Mtime_select
        csrr    T6, CSR_HTIMEDELTA
        add     \VALUE_REG, \VALUE_REG, T6
        sltu    T6, \VALUE_REG, T6                   // carry out of the low word
        add     \DEST_REG, \DEST_REG, T6
        csrr    T6, CSR_HTIMEDELTAH
        add     \DEST_REG, \DEST_REG, T6
      #else
        csrr    T6, mstatus
        srli    T6, T6, (32 + MPV_LSB)
        andi    T6, T6, 1
        beqz    T6, invisible_Mtime_select
        csrr    T6, CSR_HTIMEDELTA
        add     \VALUE_REG, \VALUE_REG, T6
      #endif
    #endif
  invisible_Mtime_select:
    #if UDB_MXLEN == 32
      // timeh differs from time in CSR address bit 7, which is instruction bit 27.
      srli    T6, \INSTRUCTION_REG, 27
      andi    T6, T6, 1
      beqz    T6, invisible_Mtime_rd
      mv      \VALUE_REG, \DEST_REG
    #endif
  invisible_Mtime_rd:
    // The CSR rd field uses the standard bits 11:7 location.
    srli    \DEST_REG, \INSTRUCTION_REG, 7
    andi    \DEST_REG, \DEST_REG, (INSN_FIELD_RD >> 7)
    li      \ACTION_REG, 2
  invisible_Mtime_done:
.endm

.macro RVTEST_INVISIBLE_TRAP_HANDLER_CODE
  invisible_Mhandler:
    // Reconstruct the illegal instruction.
    // Load with the trapped mode's access rights from mstatus.MPP. SUM and MXR
    // permit reads from executable or readable lower-mode pages. MPRV also honors
    // mstatus.MPV, so a fetch from VS or VU uses the guest's two-stage translation.
    csrr    T1, mepc
    li      T3, MSTATUS_MPRV | MSTATUS_SUM | MSTATUS_MXR
    csrrs   T4, mstatus, T3
    lhu     T2, 0(T1)
    andi    T3, T2, 3                         // bits 1:0 identify a compressed instruction
    xori    T3, T3, 3                         // zero means a 32-bit instruction
    bnez    T3, invisible_Minstruction_restore_status
    lhu     T3, 2(T1)
    slli    T3, T3, 16
    or      T2, T2, T3
  invisible_Minstruction_restore_status:
    csrw    mstatus, T4                      // restore mstatus

  invisible_Memulate:
    li      T3, 0
    // T1=mepc and T2=instruction are read-only. T3=action, T4=destination GPR number, and T5=value.
    #ifdef RVMODEL_INVISIBLE_TRAP_HANDLER
      RVMODEL_INVISIBLE_TRAP_HANDLER(T1, T2, T3, T4, T5)
      bnez    T3, invisible_Mdispatch
    #endif
    #ifdef RVTEST_EMULATE_TIME_CSR
      RVTEST_INVISIBLE_TIME_HANDLER T1, T2, T3, T4, T5
    #endif

  invisible_Mdispatch:
    // Action 0 indicates no emulation was done.
    beqz    T3, invisible_Mnot_handled
    // Action 1 means the handler updated all architectural state directly.
    addi    T3, T3, -1
    beqz    T3, invisible_Mtrap_return
    // Action 2 writes T5 to the GPR number in T4 before returning.
    addi    T3, T3, -1
    beqz    T3, invisible_Mwrite_gpr
    #ifdef H_SUPPORTED
      // Action 3 raises a virtual-instruction exception.
      addi    T3, T3, -1
      beqz    T3, invisible_Mvirtual_instruction
      addi    T3, T3, 1
    #endif

    // An invalid action is an integration error. Restore its value, report it, and stop the test.
    addi    T3, T3, 2
  invisible_Minvalid_action:
    LA(a0, invisible_Minvalid_action_str)
    call    rvmodel_io_write_str
    mv      a0, T3
    li      a1, UDB_MXLEN
    call    failedtest_hex_to_str
    LA(a0, ascii_buffer)
    call    rvmodel_io_write_str
    LA(a0, failstr)
    call    rvmodel_io_write_str
    call    rvmodel_halt_fail

  #ifdef H_SUPPORTED
  invisible_Mvirtual_instruction:
    // Take the exception in HS-mode if medeleg[22] delegates it, otherwise in M-mode.
    li      T5, CAUSE_VIRTUAL_INSTRUCTION
    csrr    T1, mstatus
    csrr    T4, CSR_MEDELEG
    srli    T4, T4, CAUSE_VIRTUAL_INSTRUCTION
    andi    T4, T4, 1
    bnez    T4, invisible_Mforward_hs
    csrw    mcause, T5
    #ifdef UDB_REPORT_ENCODING_IN_MTVAL_ON_ILLEGAL_INSTRUCTION
      csrw    mtval, T2
    #else
      csrw    mtval, zero
    #endif
    j       invisible_Mnot_handled_in_M
  #endif

  invisible_Mnot_handled:
    // Keep an unhandled instruction on the normal illegal-instruction path.
    li      T5, CAUSE_ILLEGAL_INSTRUCTION     // the custom hook may use T5 as scratch
    #ifdef S_SUPPORTED
      // medeleg[2] is clear while lower-mode code runs so M-mode can try
      // invisible emulation first. Forward an unhandled trap only when the
      // saved shadow value of medeleg[2] requests delegation.
      csrr    T1, mstatus
      LI(     T4, MSTATUS_MPP)
      and     T3, T1, T4
      beq     T3, T4, invisible_Mnot_handled_in_M
      LREG    T4, medeleg_illegal_sv_off(sp)
      beqz    T4, invisible_Mnot_handled_in_M

      #ifdef H_SUPPORTED
        // From VS or VU, hedeleg[2] delegates the exception on to VS-mode.
        #if UDB_MXLEN == 32
          csrr    T4, CSR_MSTATUSH
          andi    T4, T4, (1 << MPV_LSB)
        #else
          srli    T4, T1, 32
          andi    T4, T4, (1 << MPV_LSB)
        #endif
        beqz    T4, invisible_Mforward_hs
        csrr    T4, CSR_HEDELEG
        andi    T4, T4, (1 << CAUSE_ILLEGAL_INSTRUCTION)
        bnez    T4, invisible_Mforward_vs
      #endif

    invisible_Mforward_hs:
      // Copy the M-mode trap state to the corresponding S-mode CSRs (xepc, xcause, xtval).
      // T1 holds mstatus and T5 the cause.
      csrr    T4, mepc
      csrw    sepc, T4
      csrw    scause, T5
      #ifdef H_SUPPORTED
        LI(     T3, CAUSE_VIRTUAL_INSTRUCTION)
        bne     T5, T3, invisible_Mforward_hs_illegal_tval
        #ifdef UDB_REPORT_ENCODING_IN_VSTVAL_ON_VIRTUAL_INSTRUCTION
          csrw    stval, T2
        #else
          csrw    stval, zero
        #endif
        j       invisible_Mforward_hs_tval_done
      invisible_Mforward_hs_illegal_tval:
      #endif
      #ifdef UDB_REPORT_ENCODING_IN_STVAL_ON_ILLEGAL_INSTRUCTION
        csrw    stval, T2
      #else
        csrw    stval, zero
      #endif
      invisible_Mforward_hs_tval_done:

      #ifdef H_SUPPORTED
        // Reproduce HS-mode trap entry: htval and htinst are zero, SPV and GVA are
        // written, and SPVP is written only from a guest. Clearing MPV makes the mret
        // below enter HS-mode.
        csrw    htval, zero
        csrw    htinst, zero
        LI(     T3, HSTATUS_SPV | HSTATUS_GVA)
        csrc    hstatus, T3
        #if UDB_MXLEN == 32
          csrr    T4, CSR_MSTATUSH
          andi    T4, T4, (1 << MPV_LSB)
        #else
          srli    T4, T1, 32
          andi    T4, T4, (1 << MPV_LSB)
        #endif
        beqz    T4, invisible_Mforward_host
        LI(     T3, HSTATUS_SPV | HSTATUS_SPVP)
        csrs    hstatus, T3
        srli    T4, T1, MPP_LSB
        andi    T4, T4, 1                         // nominal privilege: VS = 1, VU = 0
        bnez    T4, invisible_Mforward_clear_mpv
        LI(     T3, HSTATUS_SPVP)
        csrc    hstatus, T3
      invisible_Mforward_clear_mpv:
        #if UDB_MXLEN == 32
          li      T3, (1 << MPV_LSB)
          csrc    CSR_MSTATUSH, T3
        #else
          LI(     T3, MSTATUS_MPV)
          csrc    mstatus, T3
        #endif
      invisible_Mforward_host:
      #endif

      // Reproduce S-mode trap entry: SPIE gets the prior SIE value, SIE is cleared,
      // and SPP records whether the interrupted mode was S or U.
      andi    T4, T1, MSTATUS_SIE
      slli    T4, T4, 4                         // SIE -> SPIE
      srli    T3, T1, MPP_LSB
      andi    T3, T3, 1                         // trapped S-mode -> SPP=1
      slli    T3, T3, 8
      or      T3, T3, T4
      LI(     T4, MSTATUS_SIE | MSTATUS_SPIE | MSTATUS_SPP)
      csrc    mstatus, T4
      csrs    mstatus, T3

      // Make the final mret enter S-mode at the stvec base. Exceptions do not
      // use a vectored offset, even when stvec.MODE is vectored.
      csrr    T1, stvec
      j       invisible_Mforward_enter

      #ifdef H_SUPPORTED
    invisible_Mforward_vs:
      // Reproduce VS-mode trap entry for an illegal instruction. vsstatus takes the
      // S-mode trap entry fields, SPP records whether the guest was in VS or VU, and
      // hstatus is unchanged. MPV stays set, so the mret below enters VS-mode.
      csrr    T4, mepc
      csrw    CSR_VSEPC, T4
      csrw    CSR_VSCAUSE, T5
      #ifdef UDB_REPORT_ENCODING_IN_VSTVAL_ON_ILLEGAL_INSTRUCTION
        csrw    CSR_VSTVAL, T2
      #else
        csrw    CSR_VSTVAL, zero
      #endif
      csrr    T3, CSR_VSSTATUS
      andi    T4, T3, MSTATUS_SIE
      slli    T4, T4, 4                         // SIE -> SPIE
      srli    T3, T1, MPP_LSB
      andi    T3, T3, 1                         // trapped VS-mode -> SPP=1
      slli    T3, T3, 8
      or      T3, T3, T4
      LI(     T4, MSTATUS_SIE | MSTATUS_SPIE | MSTATUS_SPP)
      csrc    CSR_VSSTATUS, T4
      csrs    CSR_VSSTATUS, T3
      csrr    T1, CSR_VSTVEC
      #endif

    invisible_Mforward_enter:
      andi    T1, T1, -4
      csrw    mepc, T1
      LI(     T4, MSTATUS_MPP)
      csrc    mstatus, T4
      LI(     T4, MPP_SMODE)
      csrs    mstatus, T4
      // Restore the saved M-mode registers, then execute mret into S-mode or VS-mode.
      SREG    zero, rvmodel_sv_off(sp)           // clear the fast-handler handoff marker
      LA(     T4, resto_Mrtn)
      jr      T4
    #endif

  invisible_Mnot_handled_in_M:
    #ifdef RVTEST_USE_FAST_TRAP_HANDLER
      LREG    T4, rvmodel_sv_off(sp)
      bnez    T4, invisible_Mfast_not_handled
    #endif
    j       invisible_Mnormal_trap

  #ifdef RVTEST_USE_FAST_TRAP_HANDLER
    invisible_Mfast_not_handled:
      // Restore the saved registers and resume the fast illegal-instruction path.
      SREG    zero, rvmodel_sv_off(sp)
      LREG    T1, trap_sv_off+1*REGWIDTH(sp)
      LREG    T2, trap_sv_off+2*REGWIDTH(sp)
      LREG    T3, trap_sv_off+3*REGWIDTH(sp)
      LREG    T4, trap_sv_off+4*REGWIDTH(sp)
      LREG    T5, trap_sv_off+5*REGWIDTH(sp)
      LREG    T6, trap_sv_off+6*REGWIDTH(sp)
      LREG    sp, trap_sv_off+7*REGWIDTH(sp)
      j       fast_Millegalinstruction
  #endif

  invisible_Mnormal_trap:
    // Continue through the regular trap handler.
    SREG    zero, rvmodel_sv_off(sp)           // clear the fast-handler handoff marker
    LA(     T4, invisible_Mcontinue)
    jr      T4

  // Write T5 to the GPR number in T4. Writes to registers saved by the trap
  // entry update their save slots so the restore keeps the result.
  invisible_Mwrite_gpr:
    // Scale the GPR number by the jump-table entry size.
  #if UDB_MXLEN == 32
    slli    T4, T4, 2
  #else
    slli    T4, T4, 3
  #endif
    LA(     T3, invisible_Mgpr_table)
    add     T4, T4, T3
    LREG    T4, 0(T4)
    jr      T4

    .balign REGWIDTH
  invisible_Mgpr_table:
    RVTEST_WORD_PTR invisible_Mwrite_x0
    RVTEST_WORD_PTR invisible_Mwrite_x1
    RVTEST_WORD_PTR invisible_Mwrite_x2
    RVTEST_WORD_PTR invisible_Mwrite_x3
    RVTEST_WORD_PTR invisible_Mwrite_x4
    RVTEST_WORD_PTR invisible_Mwrite_x5
    RVTEST_WORD_PTR invisible_Mwrite_x6
    RVTEST_WORD_PTR invisible_Mwrite_x7
    RVTEST_WORD_PTR invisible_Mwrite_x8
    RVTEST_WORD_PTR invisible_Mwrite_x9
    RVTEST_WORD_PTR invisible_Mwrite_x10
    RVTEST_WORD_PTR invisible_Mwrite_x11
    RVTEST_WORD_PTR invisible_Mwrite_x12
    RVTEST_WORD_PTR invisible_Mwrite_x13
    RVTEST_WORD_PTR invisible_Mwrite_x14
    RVTEST_WORD_PTR invisible_Mwrite_x15
  #ifndef E_SUPPORTED
    RVTEST_WORD_PTR invisible_Mwrite_x16
    RVTEST_WORD_PTR invisible_Mwrite_x17
    RVTEST_WORD_PTR invisible_Mwrite_x18
    RVTEST_WORD_PTR invisible_Mwrite_x19
    RVTEST_WORD_PTR invisible_Mwrite_x20
    RVTEST_WORD_PTR invisible_Mwrite_x21
    RVTEST_WORD_PTR invisible_Mwrite_x22
    RVTEST_WORD_PTR invisible_Mwrite_x23
    RVTEST_WORD_PTR invisible_Mwrite_x24
    RVTEST_WORD_PTR invisible_Mwrite_x25
    RVTEST_WORD_PTR invisible_Mwrite_x26
    RVTEST_WORD_PTR invisible_Mwrite_x27
    RVTEST_WORD_PTR invisible_Mwrite_x28
    RVTEST_WORD_PTR invisible_Mwrite_x29
    RVTEST_WORD_PTR invisible_Mwrite_x30
    RVTEST_WORD_PTR invisible_Mwrite_x31
  #else
    .rept 16
    RVTEST_WORD_PTR invisible_Mwrite_x0
    .endr
  #endif

  invisible_Mwrite_x0:  j invisible_Mtrap_return
  invisible_Mwrite_x1:  mv x1, T5;  j invisible_Mtrap_return
  invisible_Mwrite_x2:  SREG T5, trap_sv_off+7*REGWIDTH(sp); j invisible_Mtrap_return
  invisible_Mwrite_x3:  mv x3, T5;  j invisible_Mtrap_return
  invisible_Mwrite_x4:  mv x4, T5;  j invisible_Mtrap_return
  invisible_Mwrite_x5:  mv x5, T5;  j invisible_Mtrap_return
  invisible_Mwrite_x6:  SREG T5, trap_sv_off+1*REGWIDTH(sp); j invisible_Mtrap_return
  invisible_Mwrite_x7:  SREG T5, trap_sv_off+2*REGWIDTH(sp); j invisible_Mtrap_return
  invisible_Mwrite_x8:  SREG T5, trap_sv_off+3*REGWIDTH(sp); j invisible_Mtrap_return
  invisible_Mwrite_x9:  SREG T5, trap_sv_off+4*REGWIDTH(sp); j invisible_Mtrap_return
  invisible_Mwrite_x10: mv x10, T5; j invisible_Mtrap_return
  invisible_Mwrite_x11: mv x11, T5; j invisible_Mtrap_return
  invisible_Mwrite_x12: mv x12, T5; j invisible_Mtrap_return
  invisible_Mwrite_x13: mv x13, T5; j invisible_Mtrap_return
  invisible_Mwrite_x14: SREG T5, trap_sv_off+5*REGWIDTH(sp); j invisible_Mtrap_return
  invisible_Mwrite_x15: SREG T5, trap_sv_off+6*REGWIDTH(sp); j invisible_Mtrap_return
  #ifndef E_SUPPORTED
    invisible_Mwrite_x16: mv x16, T5; j invisible_Mtrap_return
    invisible_Mwrite_x17: mv x17, T5; j invisible_Mtrap_return
    invisible_Mwrite_x18: mv x18, T5; j invisible_Mtrap_return
    invisible_Mwrite_x19: mv x19, T5; j invisible_Mtrap_return
    invisible_Mwrite_x20: mv x20, T5; j invisible_Mtrap_return
    invisible_Mwrite_x21: mv x21, T5; j invisible_Mtrap_return
    invisible_Mwrite_x22: mv x22, T5; j invisible_Mtrap_return
    invisible_Mwrite_x23: mv x23, T5; j invisible_Mtrap_return
    invisible_Mwrite_x24: mv x24, T5; j invisible_Mtrap_return
    invisible_Mwrite_x25: mv x25, T5; j invisible_Mtrap_return
    invisible_Mwrite_x26: mv x26, T5; j invisible_Mtrap_return
    invisible_Mwrite_x27: mv x27, T5; j invisible_Mtrap_return
    invisible_Mwrite_x28: mv x28, T5; j invisible_Mtrap_return
    invisible_Mwrite_x29: mv x29, T5; j invisible_Mtrap_return
    invisible_Mwrite_x30: mv x30, T5; j invisible_Mtrap_return
    invisible_Mwrite_x31: mv x31, T5; j invisible_Mtrap_return
  #endif

  invisible_Mtrap_return:
    // Skip the trapped instruction and return to the interrupted code.
    SREG    zero, rvmodel_sv_off(sp)            // clear the fast-handler handoff marker
    andi    T4, T2, 3                           // compressed instructions have bits 1:0 != 3
    xori    T4, T4, 3
    seqz    T4, T4                              // 1 for a 32-bit instruction
    slli    T4, T4, 1
    addi    T4, T4, 2                           // instruction width: 2 or 4
    csrr    T1, mepc
    add     T1, T1, T4
    csrw    mepc, T1
    LA(     T4, resto_Mrtn)
    jr      T4
.endm
