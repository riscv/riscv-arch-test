///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Instruction Disassembler
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
// Written: Jordan Carlin jcarlin@hmc.edu February 2024
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`include "coverage/RISCV_decode_pkg.svh"
`include "coverage/RISCV_disassemble_helpers.svh"

function string disassemble (logic [31:0] instrRaw);

  import RISCV_decode_pkg::*;

  string decoded;

  // Mask top bits if compressed instruction
  automatic bit compressedInstruction = instrRaw[1:0] != 2'b11;
  automatic bit [31:0] instr = compressedInstruction ? {16'b0, instrRaw[15:0]} : instrRaw;

  // Registers
  automatic bit [4:0] rs1Bits  = instr[19:15];
  automatic bit [4:0] rs2Bits  = instr[24:20];
  automatic bit [4:0] rdBits   = instr[11:7];
  automatic bit [4:0] crs2Bits = instr[6:2];

  // Register names
  automatic string rs1  = get_gpr_name(rs1Bits);
  automatic string rs2  = get_gpr_name(rs2Bits);
  automatic string rd   = get_gpr_name(rdBits);
  automatic string crs2 = get_gpr_name(crs2Bits);
  automatic string rs1p = get_c_gpr_name(instr[9:7]);
  automatic string rs2p = get_c_gpr_name(instr[4:2]);
  automatic string fs1  = get_fpr_name(instr[19:15]);
  automatic string fs2  = get_fpr_name(instr[24:20]);
  automatic string fs3  = get_fpr_name(instr[31:27]);
  automatic string fd   = get_fpr_name(instr[11:7]);
  automatic string cfs2 = get_fpr_name(instr[6:2]);
  automatic string fs1p = get_c_fpr_name(instr[9:7]);
  automatic string fs2p = get_c_fpr_name(instr[4:2]);
  automatic string vs1  = get_vr_name(rs1Bits);
  automatic string vs2  = get_vr_name(rs2Bits);
  automatic string vs3  = get_vr_name(rdBits);
  automatic string vd   = get_vr_name(rdBits);

  // Immediates
  automatic bit signed [11:0] immIType = (instr[31:20]);
  automatic bit signed [11:0] immSType = ({instr[31:25], instr[11:7]});
  automatic bit signed [12:0] immBType = ({instr[31], instr[7], instr[30:25], instr[11:8], 1'b0});
  automatic bit signed [19:0] immUType = {instr[31:12]};
  automatic bit signed [20:0] immJType = ({instr[31], instr[19:12], instr[20], instr[30:21], 1'b0});
  automatic bit        [5:0]  uimm     = instr[25:20];
  automatic bit        [1:0]  bs       = instr[31:30];
  automatic bit        [4:0]  uimm5    = instr[19:15];
  automatic bit signed [4:0]  imm5     = instr[19:15];

  // Compressed immediates
  automatic bit signed [5:0]  immCIType     = {instr[12], instr[6:2]};
  automatic bit        [5:0]  immUCIType    = {instr[12], instr[6:2]};
  automatic bit        [7:0]  immCILSPType  = {instr[3:2], instr[12], instr[6:4], 2'b00};
  automatic bit        [8:0]  immCILSPDType = {instr[4:2], instr[12], instr[6:5], 3'b000};
  automatic bit signed [9:0]  immCIASPType  = {instr[12], instr[4:3], instr[5], instr[2], instr[6], 4'b0000};
  automatic bit        [9:0]  immCIWType    = {instr[10:7], instr[12:11], instr[5], instr[6], 2'b0};
  automatic bit        [8:0]  immCSSDType   = {instr[9:7], instr[12:10], 3'b0};
  automatic bit        [6:0]  immCLSType    = {instr[5], instr[12:10], instr[6], 2'b0};
  automatic bit        [7:0]  immCLSDType   = {instr[6:5], instr[12:10], 3'b0};
  automatic bit        [1:0]  immCLSHType   = {instr[5], 1'b0};
  automatic bit        [1:0]  immCLSBType   = {instr[5], instr[6]};
  automatic bit signed [8:0]  immCBType     = {instr[12], instr[6:5], instr[2], instr[11:10], instr[4:3], 1'b0};
  automatic bit        [5:0]  immCBpType    = {instr[12], instr[6:2]};
  automatic bit signed [11:0] immCJType     = {instr[12], instr[8], instr[10:9], instr[6], instr[7], instr[2], instr[11], instr[5:3], 1'b0};
  automatic bit        [8:0]  immCSSType    = {instr[8:7], instr[12:9], 2'b0};

  // Other fields
  automatic bit     [2:0] frm  = instr[14:12];
  automatic string        csr  = get_csr_name(instr[31:20]);

  // Vector fields
  automatic string  vm    = instr[25] ? "" : ", v0.t";
  automatic string  eSEW  = get_vtype_eSEW_name(instr[25:23]);
  automatic string  mLMUL = get_vtype_mLMUL_name(instr[22:20]);
  automatic string  ta    = get_vtype_ta_name(instr[27]);
  automatic string  ma    = get_vtype_ma_name(instr[26]);

  casez (instr)
    // Hints
    PAUSE:   $sformat(decoded, "pause");
    // Base Instructions
    ADD:     $sformat(decoded, "add %s, %s, %s", rd, rs1, rs2);
    SUB:     $sformat(decoded, "sub %s, %s, %s", rd, rs1, rs2);
    AND:     $sformat(decoded, "and %s, %s, %s", rd, rs1, rs2);
    OR:      $sformat(decoded, "or %s, %s, %s", rd, rs1, rs2);
    XOR:     $sformat(decoded, "xor %s, %s, %s", rd, rs1, rs2);
    SLT:     $sformat(decoded, "slt %s, %s, %s", rd, rs1, rs2);
    SLTU:    $sformat(decoded, "sltu %s, %s, %s", rd, rs1, rs2);
    SLL:     $sformat(decoded, "sll %s, %s, %s", rd, rs1, rs2);
    SRL:     $sformat(decoded, "srl %s, %s, %s", rd, rs1, rs2);
    SRA:     $sformat(decoded, "sra %s, %s, %s", rd, rs1, rs2);
    ADDI:    $sformat(decoded, "addi %s, %s, %0d", rd, rs1, immIType);
    ANDI:    $sformat(decoded, "andi %s, %s, %0d", rd, rs1, immIType);
    ORI:     $sformat(decoded, "ori %s, %s, %0d", rd, rs1, immIType);
    XORI:    $sformat(decoded, "xori %s, %s, %0d", rd, rs1, immIType);
    SLTI:    $sformat(decoded, "slti %s, %s, %0d", rd, rs1, immIType);
    SLTIU:   $sformat(decoded, "sltiu %s, %s, %0d", rd, rs1, immIType);
  `ifdef XLEN32
    SLLI_RV32: $sformat(decoded, "slli %s, %s, %0d", rd, rs1, uimm[4:0]);
    SRAI_RV32: $sformat(decoded, "srai %s, %s, %0d", rd, rs1, uimm[4:0]);
    SRLI_RV32: $sformat(decoded, "srli %s, %s, %0d", rd, rs1, uimm[4:0]);
  `else
    SLLI:      $sformat(decoded, "slli %s, %s, %0d", rd, rs1, uimm);
    SRAI:      $sformat(decoded, "srai %s, %s, %0d", rd, rs1, uimm);
    SRLI:      $sformat(decoded, "srli %s, %s, %0d", rd, rs1, uimm);
  `endif
    AUIPC:   $sformat(decoded, "auipc %s, %0d", rd, immUType);
    LUI:     $sformat(decoded, "lui %s, %0d", rd, immUType);
    BEQ:     $sformat(decoded, "beq %s, %s, %0d", rs1, rs2, immBType);
    BGE:     $sformat(decoded, "bge %s, %s, %0d", rs1, rs2, immBType);
    BGEU:    $sformat(decoded, "bgeu %s, %s, %0d", rs1, rs2, immBType);
    BLT:     $sformat(decoded, "blt %s, %s, %0d", rs1, rs2, immBType);
    BLTU:    $sformat(decoded, "bltu %s, %s, %0d", rs1, rs2, immBType);
    BNE:     $sformat(decoded, "bne %s, %s, %0d", rs1, rs2, immBType);
    EBREAK:  $sformat(decoded, "ebreak");
    ECALL:   $sformat(decoded, "ecall");
    MRET:    $sformat(decoded, "mret");
    WFI:     $sformat(decoded, "wfi");
    FENCE:   $sformat(decoded, "fence");
    JAL:     $sformat(decoded, "jal %s, %0d", rd, immJType);
    JALR:    $sformat(decoded, "jalr %s, %0d(%s)", rd, immIType, rs1);
    LB:      $sformat(decoded, "lb %s, %0d(%s)", rd, immIType, rs1);
    LBU:     $sformat(decoded, "lbu %s, %0d(%s)", rd, immIType, rs1);
    LH:      $sformat(decoded, "lh %s, %0d(%s)", rd, immIType, rs1);
    LHU:     $sformat(decoded, "lhu %s, %0d(%s)", rd, immIType, rs1);
    LW:      $sformat(decoded, "lw %s, %0d(%s)", rd, immIType, rs1);
    SB:      $sformat(decoded, "sb %s, %0d(%s)", rs2, immSType, rs1);
    SH:      $sformat(decoded, "sh %s, %0d(%s)", rs2, immSType, rs1);
    SW:      $sformat(decoded, "sw %s, %0d(%s)", rs2, immSType, rs1);
  `ifdef XLEN64 // Extra RV64 Base Instructions
    ADDIW: $sformat(decoded, "addiw %s, %s, %0d", rd, rs1, immIType);
    ADDW:  $sformat(decoded, "addw %s, %s, %s", rd, rs1, rs2);
    LD:    $sformat(decoded, "ld %s, %0d(%s)", rd, immIType, rs1);
    LWU:   $sformat(decoded, "lwu %s, %0d(%s)", rd, immIType, rs1);
    SD:    $sformat(decoded, "sd %s, %0d(%s)", rs2, immSType, rs1);
    SLLIW: $sformat(decoded, "slliw %s, %s, %0d", rd, rs1, uimm[4:0]);
    SLLW:  $sformat(decoded, "sllw %s, %s, %s", rd, rs1, rs2);
    SRAIW: $sformat(decoded, "sraiw %s, %s, %0d", rd, rs1, uimm[4:0]);
    SRAW:  $sformat(decoded, "sraw %s, %s, %s", rd, rs1, rs2);
    SRLIW: $sformat(decoded, "srliw %s, %s, %0d", rd, rs1, uimm[4:0]);
    SRLW:  $sformat(decoded, "srlw %s, %s, %s", rd, rs1, rs2);
    SUBW:  $sformat(decoded, "subw %s, %s, %s", rd, rs1, rs2);
  `endif
    // Supervisor Mode Instructions
    SFENCE_VMA: $sformat(decoded, "sfence.vma %s, %s", rs1, rs2);
    SRET:       $sformat(decoded, "sret");
    // Svinval instructinos
    SFENCE_INVAL_IR: $sformat(decoded, "sfence.inval.ir");
    SFENCE_W_INVAL:  $sformat(decoded, "sfence.w.inval");
    SINVAL_VMA:      $sformat(decoded, "sinval.vma %s, %s", rs1, rs2);
    // Zicboz Extension
    CBO_ZERO: $sformat(decoded, "cbo.zero (%s)", rs1);
    // Zicbom Extension
    CBO_CLEAN: $sformat(decoded, "cbo.clean (%s)", rs1);
    CBO_FLUSH: $sformat(decoded, "cbo.flush (%s)", rs1);
    CBO_INVAL: $sformat(decoded, "cbo.inval (%s)", rs1);
    // Zicbop Extension
    PREFETCH_I: $sformat(decoded, "prefetch.i %0d(%s)", immIType, rs1);
    PREFETCH_R: $sformat(decoded, "prefetch.r %0d(%s)", immIType, rs1);
    PREFETCH_W: $sformat(decoded, "prefetch.w %0d(%s)", immIType, rs1);
    // Zicond Extension
    CZERO_EQZ: $sformat(decoded, "czero.eqz %s, %s, %s", rd, rs1, rs2);
    CZERO_NEZ: $sformat(decoded, "czero.nez %s, %s, %s", rd, rs1, rs2);
    // Zicsr Extension
    CSRRW:  $sformat(decoded, "csrrw %s, %0d, %s", rd, csr, rs1);
    CSRRS:  $sformat(decoded, "csrrs %s, %0d, %s", rd, csr, rs1);
    CSRRC:  $sformat(decoded, "csrrc %s, %0d, %s", rd, csr, rs1);
    CSRRWI: $sformat(decoded, "csrrwi %s, %0d, %0d", rd, csr, rs1Bits);
    CSRRSI: $sformat(decoded, "csrrsi %s, %0d, %0d", rd, csr, rs1Bits);
    CSRRCI: $sformat(decoded, "csrrci %s, %0d, %0d", rd, csr, rs1Bits);
    // Zifencei Extension
    FENCE_I: $sformat(decoded, "fence.i");
    // M Extension
    MUL:    $sformat(decoded, "mul %s, %s, %s", rd, rs1, rs2);
    MULH:   $sformat(decoded, "mulh %s, %s, %s", rd, rs1, rs2);
    MULHSU: $sformat(decoded, "mulhsu %s, %s, %s", rd, rs1, rs2);
    MULHU:  $sformat(decoded, "mulhu %s, %s, %s", rd, rs1, rs2);
    DIV:    $sformat(decoded, "div %s, %s, %s", rd, rs1, rs2);
    DIVU:   $sformat(decoded, "divu %s, %s, %s", rd, rs1, rs2);
    REM:    $sformat(decoded, "rem %s, %s, %s", rd, rs1, rs2);
    REMU:   $sformat(decoded, "remu %s, %s, %s", rd, rs1, rs2);
  `ifdef XLEN64
    MULW:  $sformat(decoded, "mulw %s, %s, %s", rd, rs1, rs2);
    DIVW:  $sformat(decoded, "divw %s, %s, %s", rd, rs1, rs2);
    DIVUW: $sformat(decoded, "divuw %s, %s, %s", rd, rs1, rs2);
    REMW:  $sformat(decoded, "remw %s, %s, %s", rd, rs1, rs2);
    REMUW: $sformat(decoded, "remuw %s, %s, %s", rd, rs1, rs2);
  `endif
    // Zaamo Extension
    AMOADD_W:  $sformat(decoded, "amoadd.w %s, %s, (%s)", rd, rs2, rs1);
    AMOAND_W:  $sformat(decoded, "amoand.w %s, %s, (%s)", rd, rs2, rs1);
    AMOMAX_W:  $sformat(decoded, "amomax.w %s, %s, (%s)", rd, rs2, rs1);
    AMOMAXU_W: $sformat(decoded, "amomaxu.w %s, %s, (%s)", rd, rs2, rs1);
    AMOMIN_W:  $sformat(decoded, "amomin.w %s, %s, (%s)", rd, rs2, rs1);
    AMOMINU_W: $sformat(decoded, "amominu.w %s, %s, (%s)", rd, rs2, rs1);
    AMOOR_W:   $sformat(decoded, "amoor.w %s, %s, (%s)", rd, rs2, rs1);
    AMOSWAP_W: $sformat(decoded, "amoswap.w %s, %s, (%s)", rd, rs2, rs1);
    AMOXOR_W:  $sformat(decoded, "amoxor.w %s, %s, (%s)", rd, rs2, rs1);
  `ifdef XLEN64
    AMOADD_D:  $sformat(decoded, "amoadd.d %s, %s, (%s)", rd, rs2, rs1);
    AMOAND_D:  $sformat(decoded, "amoand.d %s, %s, (%s)", rd, rs2, rs1);
    AMOMAX_D:  $sformat(decoded, "amomax.d %s, %s, (%s)", rd, rs2, rs1);
    AMOMAXU_D: $sformat(decoded, "amomaxu.d %s, %s, (%s)", rd, rs2, rs1);
    AMOMIN_D:  $sformat(decoded, "amomin.d %s, %s, (%s)", rd, rs2, rs1);
    AMOMINU_D: $sformat(decoded, "amominu.d %s, %s, (%s)", rd, rs2, rs1);
    AMOOR_D:   $sformat(decoded, "amoor.d %s, %s, (%s)", rd, rs2, rs1);
    AMOSWAP_D: $sformat(decoded, "amoswap.d %s, %s, (%s)", rd, rs2, rs1);
    AMOXOR_D:  $sformat(decoded, "amoxor.d %s, %s, (%s)", rd, rs2, rs1);
  `endif
    // Zalrsc Extension
    LR_W:      $sformat(decoded, "lr.w %s, (%s)", rd, rs1);
    SC_W:      $sformat(decoded, "sc.w %s, %s, (%s)", rd, rs2, rs1);
  `ifdef XLEN64
    LR_D:      $sformat(decoded, "lr.d %s, (%s)", rd, rs1);
    SC_D:      $sformat(decoded, "sc.d %s, %s, (%s)", rd, rs2, rs1);
  `endif
    // F Extension
    FMADD_S:   $sformat(decoded, "fmadd.s %s, %s, %s, %s, %s", fd, fs1, fs2, fs3, get_frm_string(frm));
    FMSUB_S:   $sformat(decoded, "fmsub.s %s, %s, %s, %s, %s", fd, fs1, fs2, fs3, get_frm_string(frm));
    FNMADD_S:  $sformat(decoded, "fnmadd.s %s, %s, %s, %s, %s", fd, fs1, fs2, fs3, get_frm_string(frm));
    FNMSUB_S:  $sformat(decoded, "fnmsub.s %s, %s, %s, %s, %s", fd, fs1, fs2, fs3, get_frm_string(frm));
    FADD_S:    $sformat(decoded, "fadd.s %s, %s, %s, %s", fd, fs1, fs2, get_frm_string(frm));
    FSUB_S:    $sformat(decoded, "fsub.s %s, %s, %s, %s", fd, fs1, fs2, get_frm_string(frm));
    FMUL_S:    $sformat(decoded, "fmul.s %s, %s, %s, %s", fd, fs1, fs2, get_frm_string(frm));
    FDIV_S:    $sformat(decoded, "fdiv.s %s, %s, %s, %s", fd, fs1, fs2, get_frm_string(frm));
    FSQRT_S:   $sformat(decoded, "fsqrt.s %s, %s, %s", fd, fs1, get_frm_string(frm));
    FSGNJ_S:   $sformat(decoded, "fsgnj.s %s, %s, %s", fd, fs1, fs2);
    FSGNJN_S:  $sformat(decoded, "fsgnjn.s %s, %s, %s", fd, fs1, fs2);
    FSGNJX_S:  $sformat(decoded, "fsgnjx.s %s, %s, %s", fd, fs1, fs2);
    FMAX_S:    $sformat(decoded, "fmax.s %s, %s, %s", fd, fs1, fs2);
    FMIN_S:    $sformat(decoded, "fmin.s %s, %s, %s", fd, fs1, fs2);
    FEQ_S:     $sformat(decoded, "feq.s %s, %s, %s", rd, fs1, fs2);
    FLE_S:     $sformat(decoded, "fle.s %s, %s, %s", rd, fs1, fs2);
    FLT_S:     $sformat(decoded, "flt.s %s, %s, %s", rd, fs1, fs2);
    FCLASS_S:  $sformat(decoded, "fclass.s %s, %s", rd, fs1);
    FLW:       $sformat(decoded, "flw %s, %0d(%s)", fd, immIType, rs1);
    FSW:       $sformat(decoded, "fsw %s, %0d(%s)", fs2, immSType, rs1);
    FCVT_S_W:  $sformat(decoded, "fcvt.s.w %s, %s, %s", fd, rs1, get_frm_string(frm));
    FCVT_S_WU: $sformat(decoded, "fcvt.s.wu %s, %s, %s", fd, rs1, get_frm_string(frm));
    FCVT_W_S:  $sformat(decoded, "fcvt.w.s %s, %s, %s", rd, fs1, get_frm_string(frm));
    FCVT_WU_S: $sformat(decoded, "fcvt.wu.s %s, %s, %s", rd, fs1, get_frm_string(frm));
    FMV_W_X:   $sformat(decoded, "fmv.w.x %s, %s", fd, rs1);
    FMV_X_W:   $sformat(decoded, "fmv.x.w %s, %s", rd, fs1);
  `ifdef XLEN64
    FCVT_L_S:  $sformat(decoded, "fcvt.l.s %s, %s, %s", rd, fs1, get_frm_string(frm));
    FCVT_LU_S: $sformat(decoded, "fcvt.lu.s %s, %s, %s", rd, fs1, get_frm_string(frm));
    FCVT_S_L:  $sformat(decoded, "fcvt.s.l %s, %s, %s", fd, rs1, get_frm_string(frm));
    FCVT_S_LU: $sformat(decoded, "fcvt.s.lu %s, %s, %s", fd, rs1, get_frm_string(frm));
  `endif
    // D Extension
    FMADD_D:   $sformat(decoded, "fmadd.d %s, %s, %s, %s, %s", fd, fs1, fs2, fs3, get_frm_string(frm));
    FMSUB_D:   $sformat(decoded, "fmsub.d %s, %s, %s, %s, %s", fd, fs1, fs2, fs3, get_frm_string(frm));
    FNMADD_D:  $sformat(decoded, "fnmadd.d %s, %s, %s, %s, %s", fd, fs1, fs2, fs3, get_frm_string(frm));
    FNMSUB_D:  $sformat(decoded, "fnmsub.d %s, %s, %s, %s, %s", fd, fs1, fs2, fs3, get_frm_string(frm));
    FADD_D:    $sformat(decoded, "fadd.d %s, %s, %s, %s", fd, fs1, fs2, get_frm_string(frm));
    FSUB_D:    $sformat(decoded, "fsub.d %s, %s, %s, %s", fd, fs1, fs2, get_frm_string(frm));
    FMUL_D:    $sformat(decoded, "fmul.d %s, %s, %s, %s", fd, fs1, fs2, get_frm_string(frm));
    FDIV_D:    $sformat(decoded, "fdiv.d %s, %s, %s, %s", fd, fs1, fs2, get_frm_string(frm));
    FSQRT_D:   $sformat(decoded, "fsqrt.d %s, %s, %s", fd, fs1, get_frm_string(frm));
    FSGNJ_D:   $sformat(decoded, "fsgnj.d %s, %s, %s", fd, fs1, fs2);
    FSGNJN_D:  $sformat(decoded, "fsgnjn.d %s, %s, %s", fd, fs1, fs2);
    FSGNJX_D:  $sformat(decoded, "fsgnjx.d %s, %s, %s", fd, fs1, fs2);
    FMAX_D:    $sformat(decoded, "fmax.d %s, %s, %s", fd, fs1, fs2);
    FMIN_D:    $sformat(decoded, "fmin.d %s, %s, %s", fd, fs1, fs2);
    FEQ_D:     $sformat(decoded, "feq.d %s, %s, %s", rd, fs1, fs2);
    FLE_D:     $sformat(decoded, "fle.d %s, %s, %s", rd, fs1, fs2);
    FLT_D:     $sformat(decoded, "flt.d %s, %s, %s", rd, fs1, fs2);
    FLD:       $sformat(decoded, "fld %s, %0d(%s)", fd, immIType, rs1);
    FSD:       $sformat(decoded, "fsd %s, %0d(%s)", fs2, immSType, rs1);
    FCLASS_D:  $sformat(decoded, "fclass.d %s, %s", rd, fs1);
    FCVT_D_S:  $sformat(decoded, "fcvt.d.s %s, %s, %s", fd, fs1, get_frm_string(frm));
    FCVT_D_W:  $sformat(decoded, "fcvt.d.w %s, %s, %s", fd, rs1, get_frm_string(frm));
    FCVT_D_WU: $sformat(decoded, "fcvt.d.wu %s, %s, %s", fd, rs1, get_frm_string(frm));
    FCVT_S_D:  $sformat(decoded, "fcvt.s.d %s, %s, %s", fd, fs1, get_frm_string(frm));
    FCVT_W_D:  $sformat(decoded, "fcvt.w.d %s, %s, %s", rd, fs1, get_frm_string(frm));
    FCVT_WU_D: $sformat(decoded, "fcvt.wu.d %s, %s, %s", rd, fs1, get_frm_string(frm));
  `ifdef XLEN64
    FCVT_D_L:  $sformat(decoded, "fcvt.d.l %s, %s, %s", fd, rs1, get_frm_string(frm));
    FCVT_D_LU: $sformat(decoded, "fcvt.d.lu %s, %s, %s", fd, rs1, get_frm_string(frm));
    FCVT_L_D:  $sformat(decoded, "fcvt.l.d %s, %s, %s", rd, fs1, get_frm_string(frm));
    FCVT_LU_D: $sformat(decoded, "fcvt.lu.d %s, %s, %s", rd, fs1, get_frm_string(frm));
    FMV_D_X:   $sformat(decoded, "fmv.d.x %s, %s, %s", fd, rs1, get_frm_string(frm));
    FMV_X_D:   $sformat(decoded, "fmv.x.d %s, %s, %s", rd, fs1, get_frm_string(frm));
  `endif
    // Q Extension
    FMADD_Q:   $sformat(decoded, "fmadd.q %s, %s, %s, %s, %s", fd, fs1, fs2, fs3, get_frm_string(frm));
    FMSUB_Q:   $sformat(decoded, "fmsub.q %s, %s, %s, %s, %s", fd, fs1, fs2, fs3, get_frm_string(frm));
    FNMADD_Q:  $sformat(decoded, "fnmadd.q %s, %s, %s, %s, %s", fd, fs1, fs2, fs3, get_frm_string(frm));
    FNMSUB_Q:  $sformat(decoded, "fnmsub.q %s, %s, %s, %s, %s", fd, fs1, fs2, fs3, get_frm_string(frm));
    FADD_Q:    $sformat(decoded, "fadd.q %s, %s, %s, %s", fd, fs1, fs2, get_frm_string(frm));
    FSUB_Q:    $sformat(decoded, "fsub.q %s, %s, %s, %s", fd, fs1, fs2, get_frm_string(frm));
    FMUL_Q:    $sformat(decoded, "fmul.q %s, %s, %s, %s", fd, fs1, fs2, get_frm_string(frm));
    FDIV_Q:    $sformat(decoded, "fdiv.q %s, %s, %s, %s", fd, fs1, fs2, get_frm_string(frm));
    FSQRT_Q:   $sformat(decoded, "fsqrt.q %s, %s, %s", fd, fs1, get_frm_string(frm));
    FSGNJ_Q:   $sformat(decoded, "fsgnj.q %s, %s, %s", fd, fs1, fs2);
    FSGNJN_Q:  $sformat(decoded, "fsgnjn.q %s, %s, %s", fd, fs1, fs2);
    FSGNJX_Q:  $sformat(decoded, "fsgnjx.q %s, %s, %s", fd, fs1, fs2);
    FMAX_Q:    $sformat(decoded, "fmax.q %s, %s, %s", fd, fs1, fs2);
    FMIN_Q:    $sformat(decoded, "fmin.q %s, %s, %s", fd, fs1, fs2);
    FEQ_Q:     $sformat(decoded, "feq.q %s, %s, %s", rd, fs1, fs2);
    FLE_Q:     $sformat(decoded, "fle.q %s, %s, %s", rd, fs1, fs2);
    FLT_Q:     $sformat(decoded, "flt.q %s, %s, %s", rd, fs1, fs2);
    FCLASS_Q:  $sformat(decoded, "fclass.q %s, %s", rd, fs1);
    FLQ:       $sformat(decoded, "flq %s, %0d(%s)", fd, immIType, rs1);
    FSQ:       $sformat(decoded, "fsq %s, %0d(%s)", fs2, immSType, rs1);
    FCVT_D_Q:  $sformat(decoded, "fcvt.d.q %s, %s, %s", fd, fs1, get_frm_string(frm));
    FCVT_Q_D:  $sformat(decoded, "fcvt.q.d %s, %s, %s", fd, fs1, get_frm_string(frm));
    FCVT_Q_S:  $sformat(decoded, "fcvt.q.s %s, %s, %s", fd, fs1, get_frm_string(frm));
    FCVT_Q_W:  $sformat(decoded, "fcvt.q.w %s, %s, %s", fd, rs1, get_frm_string(frm));
    FCVT_Q_WU: $sformat(decoded, "fcvt.q.wu %s, %s, %s", fd, rs1, get_frm_string(frm));
    FCVT_S_Q:  $sformat(decoded, "fcvt.s.q %s, %s, %s", fd, fs1, get_frm_string(frm));
    FCVT_W_Q:  $sformat(decoded, "fcvt.w.q %s, %s, %s", fd, rs1, get_frm_string(frm));
    FCVT_WU_Q: $sformat(decoded, "fcvt.wu.q %s, %s, %s", fd, rs1, get_frm_string(frm));
  `ifdef XLEN64
    FCVT_L_Q:  $sformat(decoded, "fcvt.l.q %s, %s, %s", rd, fs1, get_frm_string(frm));
    FCVT_LU_Q: $sformat(decoded, "fcvt.lu.q %s, %s, %s", rd, fs1, get_frm_string(frm));
    FCVT_Q_L:  $sformat(decoded, "fcvt.q.l %s, %s, %s", fd, rs1, get_frm_string(frm));
    FCVT_Q_LU: $sformat(decoded, "fcvt.q.lu %s, %s, %s", fd, rs1, get_frm_string(frm));
  `endif
    // Zfh Extension
    FMADD_H:   $sformat(decoded,"fmadd.h %s, %s, %s, %s, %s", fd, fs1, fs2, fs3, get_frm_string(frm));
    FMSUB_H:   $sformat(decoded,"fmsub.h %s, %s, %s, %s, %s", fd, fs1, fs2, fs3, get_frm_string(frm));
    FNMADD_H:  $sformat(decoded,"fnmadd.h %s, %s, %s, %s, %s", fd, fs1, fs2, fs3, get_frm_string(frm));
    FNMSUB_H:  $sformat(decoded,"fnmsub.h %s, %s, %s, %s, %s", fd, fs1, fs2, fs3, get_frm_string(frm));
    FADD_H:    $sformat(decoded,"fadd.h %s, %s, %s, %s", fd, fs1, fs2, get_frm_string(frm));
    FSUB_H:    $sformat(decoded,"fsub.h %s, %s, %s, %s", fd, fs1, fs2, get_frm_string(frm));
    FMUL_H:    $sformat(decoded,"fmul.h %s, %s, %s, %s", fd, fs1, fs2, get_frm_string(frm));
    FDIV_H:    $sformat(decoded,"fdiv.h %s, %s, %s, %s", fd, fs1, fs2, get_frm_string(frm));
    FSQRT_H:   $sformat(decoded,"fsqrt.h %s, %s, %s", fd, fs1, get_frm_string(frm));
    FSGNJ_H:   $sformat(decoded,"fsgnj.h %s, %s, %s", fd, fs1, fs2);
    FSGNJN_H:  $sformat(decoded,"fsgnjn.h %s, %s, %s", fd, fs1, fs2);
    FSGNJX_H:  $sformat(decoded,"fsgnjx.h %s, %s, %s", fd, fs1, fs2);
    FMAX_H:    $sformat(decoded,"fmax.h %s, %s, %s", fd, fs1, fs2);
    FMIN_H:    $sformat(decoded,"fmin.h %s, %s, %s", fd, fs1, fs2);
    FEQ_H:     $sformat(decoded,"feq.h %s, %s, %s", rd, fs1, fs2);
    FLE_H:     $sformat(decoded,"fle.h %s, %s, %s", rd, fs1, fs2);
    FLT_H:     $sformat(decoded,"flt.h %s, %s, %s", rd, fs1, fs2);
    FCLASS_H:  $sformat(decoded,"fclass.h %s, %s", rd, fs1);
    FLH:       $sformat(decoded,"flh %s, %0d(%s)", fd, immIType, rs1);
    FSH:       $sformat(decoded,"fsh %s, %0d(%s)", fs2, immSType, rs1);
    FCVT_H_S:  $sformat(decoded,"fcvt.h.s %s, %s, %s", fd, fs1, get_frm_string(frm));
    FCVT_H_W:  $sformat(decoded,"fcvt.h.w %s, %s, %s", fd, rs1, get_frm_string(frm));
    FCVT_H_WU: $sformat(decoded,"fcvt.h.wu %s, %s, %s", fd, rs1, get_frm_string(frm));
    FCVT_S_H:  $sformat(decoded,"fcvt.s.h %s, %s, %s", fd, fs1, get_frm_string(frm));
    FCVT_W_H:  $sformat(decoded,"fcvt.w.h %s, %s, %s", rd, fs1, get_frm_string(frm));
    FCVT_WU_H: $sformat(decoded,"fcvt.wu.h %s, %s, %s", rd, fs1, get_frm_string(frm));
    FMV_H_X:   $sformat(decoded,"fmv.h.x %s, %s, %s", fd, rs1, get_frm_string(frm));
    FMV_X_H:   $sformat(decoded,"fmv.x.h %s, %s, %s", rd, fs1, get_frm_string(frm));
  `ifdef XLEN64
    FCVT_H_L:  $sformat(decoded,"fcvt.h.l %s, %s, %s", fd, rs1, get_frm_string(frm));
    FCVT_H_LU: $sformat(decoded,"fcvt.h.lu %s, %s, %s", fd, rs1, get_frm_string(frm));
    FCVT_L_H:  $sformat(decoded,"fcvt.l.h %s, %s, %s", rd, fs1, get_frm_string(frm));
    FCVT_LU_H: $sformat(decoded,"fcvt.lu.h %s, %s, %s", rd, fs1, get_frm_string(frm));
  `endif
    // Zfh + D Extensions
    FCVT_D_H: $sformat(decoded,"fcvt.d.h %s, %s, %s", fd, fs1, get_frm_string(frm));
    FCVT_H_D: $sformat(decoded,"fcvt.h.d %s, %s, %s", fd, fs1, get_frm_string(frm));
    // Zfh + Q Extensions
    FCVT_H_Q: $sformat(decoded,"fcvt.h.q %s, %s, %s", fd, fs1, get_frm_string(frm));
    FCVT_Q_H: $sformat(decoded,"fcvt.q.h %s, %s, %s", fd, fs1, get_frm_string(frm));
    // Zfa Extension
    FLEQ_S:     $sformat(decoded, "fleq.s %s, %s, %s", rd, fs1, fs2);
    FLI_S:      $sformat(decoded, "fli.s %s, %s", fd, rs1);
    FLTQ_S:     $sformat(decoded, "fltq.s %s, %s, %s", rd, fs1, fs2);
    FMAXM_S:    $sformat(decoded, "fmaxm.s %s, %s, %s", fd, fs1, fs2);
    FMINM_S:    $sformat(decoded, "fminm.s %s, %s, %s", fd, fs1, fs2);
    FROUND_S:   $sformat(decoded, "fround.s %s, %s, %s", fd, fs1, get_frm_string(frm));
    FROUNDNX_S: $sformat(decoded, "froundnx.s %s, %s, %s", fd, fs1, get_frm_string(frm));
    // Zfa + D Extensions
    FCVTMOD_W_D: $sformat(decoded, "fcvtmod.w.d %s, %s", rd, fs1);
    FLEQ_D:      $sformat(decoded, "fleq.d %s, %s, %s", rd, fs1, fs2);
    FLI_D:       $sformat(decoded, "fli.d %s, %s", fd, rs1);
    FLTQ_D:      $sformat(decoded, "fltq.d %s, %s, %s", rd, fs1, fs2);
    FMAXM_D:     $sformat(decoded, "fmaxm.d %s, %s, %s", fd, fs1, fs2);
    FMINM_D:     $sformat(decoded, "fminm.d %s, %s, %s", fd, fs1, fs2);
    FROUND_D:    $sformat(decoded, "fround.d %s, %s, %s", fd, fs1, get_frm_string(frm));
    FROUNDNX_D:  $sformat(decoded, "froundnx.d %s, %s, %s", fd, fs1, get_frm_string(frm));
  `ifdef XLEN32  // RV32 Only Zfa + D Extensions
    FMVP_D_X: $sformat(decoded, "fmvp.d.x %s, %s, %s", fd, rs1, rs2);
    FMVH_X_D: $sformat(decoded, "fmvh.x.d %s, %s", rd, fs1);
  `endif
    // Zfa + Q Extensions
    FLEQ_Q:     $sformat(decoded, "fleq.q %s, %s, %s", rd, fs1, fs2);
    FLI_Q:      $sformat(decoded, "fli.q %s, %s", fd, rs1);
    FLTQ_Q:     $sformat(decoded, "fltq.q %s, %s, %s", rd, fs1, fs2);
    FMAXM_Q:    $sformat(decoded, "fmaxm.q %s, %s, %s", fd, fs1, fs2);
    FMINM_Q:    $sformat(decoded, "fminm.q %s, %s, %s", fd, fs1, fs2);
    FROUND_Q:   $sformat(decoded, "fround.q %s, %s, %s", fd, fs1, get_frm_string(frm));
    FROUNDNX_Q: $sformat(decoded, "froundnx.q %s, %s, %s", fd, fs1, get_frm_string(frm));
  `ifdef XLEN64 // RV64 Only Zfa + Q Extensions
    FMVP_Q_X: $sformat(decoded, "fmvp.q.x %s, %s, %s", fd, rs1, rs2);
    FMVH_X_Q: $sformat(decoded, "fmvh.x.q %s, %s", rd, fs1);
  `endif
    // Zfh + Zfa Extensions
    FLEQ_H:     $sformat(decoded, "fleq.h %s, %s, %s", rd, fs1, fs2);
    FLI_H:      $sformat(decoded, "fli.h %s, %s", fd, rs1);
    FLTQ_H:     $sformat(decoded, "fltq.h %s, %s, %s", rd, fs1, fs2);
    FMAXM_H:    $sformat(decoded, "fmaxm.h %s, %s, %s", fd, fs1, fs2);
    FMINM_H:    $sformat(decoded, "fminm.h %s, %s, %s", fd, fs1, fs2);
    FROUND_H:   $sformat(decoded, "fround.h %s, %s, %s", fd, fs1, get_frm_string(frm));
    FROUNDNX_H: $sformat(decoded, "froundnx.h %s, %s, %s", fd, fs1, get_frm_string(frm));
    // Zba Extension
    SH1ADD: $sformat(decoded, "sh1add %s, %s, %s", rd, rs1, rs2);
    SH2ADD: $sformat(decoded, "sh2add %s, %s, %s", rd, rs1, rs2);
    SH3ADD: $sformat(decoded, "sh3add %s, %s, %s", rd, rs1, rs2);
  `ifdef XLEN64
    ADD_UW:    $sformat(decoded, "add.uw %s, %s, %s", rd, rs1, rs2);
    SH1ADD_UW: $sformat(decoded, "sh1add.uw %s, %s, %s", rd, rs1, rs2);
    SH2ADD_UW: $sformat(decoded, "sh2add.uw %s, %s, %s", rd, rs1, rs2);
    SH3ADD_UW: $sformat(decoded, "sh3add.uw %s, %s, %s", rd, rs1, rs2);
    SLLI_UW:   $sformat(decoded, "slli.uw %s, %s, %0d", rd, rs1, uimm);
  `endif
    // Zbb Extension
    ANDN:   $sformat(decoded, "andn %s, %s, %s", rd, rs1, rs2);
    CLZ:    $sformat(decoded, "clz %s, %s", rd, rs1);
    CPOP:   $sformat(decoded, "cpop %s, %s", rd, rs1);
    CTZ:    $sformat(decoded, "ctz %s, %s", rd, rs1);
    MAX:    $sformat(decoded, "max %s, %s, %s", rd, rs1, rs2);
    MAXU:   $sformat(decoded, "maxu %s, %s, %s", rd, rs1, rs2);
    MIN:    $sformat(decoded, "min %s, %s, %s", rd, rs1, rs2);
    MINU:   $sformat(decoded, "minu %s, %s, %s", rd, rs1, rs2);
    ORC_B:  $sformat(decoded, "orc.b %s, %s", rd, rs1);
    ORN:    $sformat(decoded, "orn %s, %s, %s", rd, rs1, rs2);
    ROL:    $sformat(decoded, "rol %s, %s, %s", rd, rs1, rs2);
    ROR:    $sformat(decoded, "ror %s, %s, %s", rd, rs1, rs2);
    SEXT_B: $sformat(decoded, "sext.b %s, %s", rd, rs1);
    SEXT_H: $sformat(decoded, "sext.h %s, %s", rd, rs1);
    XNOR:   $sformat(decoded, "xnor %s, %s, %s", rd, rs1, rs2);
  `ifdef XLEN32
    REV8_RV32: $sformat(decoded, "rev8 %s, %s", rd, rs1);
    RORI_RV32: $sformat(decoded, "rori %s, %s, %0d", rd, rs1, uimm[4:0]);
    ZEXT_H_RV32: $sformat(decoded, "zext.h %s, %s", rd, rs1);
  `else // XLEN64
    REV8:      $sformat(decoded, "rev8 %s, %s", rd, rs1);
    RORI:      $sformat(decoded, "rori %s, %s, %0d", rd, rs1, uimm);
    ZEXT_H:      $sformat(decoded, "zext.h %s, %s", rd, rs1);
    CLZW:   $sformat(decoded, "clzw %s, %s", rd, rs1);
    CPOPW:  $sformat(decoded, "cpopw %s, %s", rd, rs1);
    CTZW:   $sformat(decoded, "ctzw %s, %s", rd, rs1);
    ROLW:   $sformat(decoded, "rolw %s, %s, %s", rd, rs1, rs2);
    RORIW:  $sformat(decoded, "roriw %s, %s, %0d", rd, rs1, uimm[4:0]);
    RORW:   $sformat(decoded, "rorw %s, %s, %s", rd, rs1, rs2);
  `endif
    // Zbc Extension
    CLMUL:  $sformat(decoded, "clmul %s, %s, %s", rd, rs1, rs2);
    CLMULH: $sformat(decoded, "clmulh %s, %s, %s", rd, rs1, rs2);
    CLMULR: $sformat(decoded, "clmulr %s, %s, %s", rd, rs1, rs2);
    // Zbs Extension
    BCLR:  $sformat(decoded, "bclr %s, %s %s", rd, rs1, rs2);
    BEXT:  $sformat(decoded, "bext %s, %s %s", rd, rs1, rs2);
    BINV:  $sformat(decoded, "binv %s, %s %s", rd, rs1, rs2);
    BSET:  $sformat(decoded, "bset %s, %s %s", rd, rs1, rs2);
  `ifdef XLEN32
    BCLRI_RV32: $sformat(decoded, "bclri %s, %s, %0d", rd, rs1, uimm[4:0]);
    BEXTI_RV32: $sformat(decoded, "bexti %s, %s, %0d", rd, rs1, uimm[4:0]);
    BINVI_RV32: $sformat(decoded, "binvi %s, %s, %0d", rd, rs1, uimm[4:0]);
    BSETI_RV32: $sformat(decoded, "bseti %s, %s, %0d", rd, rs1, uimm[4:0]);
  `else // XLEN64
    BCLRI:      $sformat(decoded, "bclri %s, %s, %0d", rd, rs1, uimm);
    BEXTI:      $sformat(decoded, "bexti %s, %s, %0d", rd, rs1, uimm);
    BINVI:      $sformat(decoded, "binvi %s, %s, %0d", rd, rs1, uimm);
    BSETI:      $sformat(decoded, "bseti %s, %s, %0d", rd, rs1, uimm);
  `endif
    // Zbkb Extension
    BREV8: $sformat(decoded, "brev8 %s, %s", rd, rs1);
    PACK:  $sformat(decoded, "pack %s, %s, %s", rd, rs1, rs2);
    PACKH: $sformat(decoded, "packh %s, %s, %s", rd, rs1, rs2);
  `ifdef XLEN32
    UNZIP: $sformat(decoded, "unzip %s, %s", rd, rs1);
    ZIP:   $sformat(decoded, "zip %s, %s", rd, rs1);
  `else // XLEN64
    PACKW: $sformat(decoded, "packw %s, %s, %s", rd, rs1, rs2);
  `endif
    // Zbkx Extension
    XPERM4: $sformat(decoded, "xperm4 %s, %s, %s", rd, rs1, rs2);
    XPERM8: $sformat(decoded, "xperm8 %s, %s, %s", rd, rs1, rs2);
    // Zknd Extension
  `ifdef XLEN32
    AES32DSI:  $sformat(decoded, "aes32dsi %s, %s, %s, %0d", rd, rs1, rs2, bs);
    AES32DSMI: $sformat(decoded, "aes32dsmi %s, %s, %s, %0d", rd, rs1, rs2, bs);
  `else // XLEN64
    AES64DS:  $sformat(decoded, "aes64ds %s, %s, %s", rd, rs1, rs2);
    AES64DSM: $sformat(decoded, "aes64dsm %s, %s, %s", rd, rs1, rs2);
    AES64IM:  $sformat(decoded, "aes64im %s, %s", rd, rs1);
  `endif
    // Zkne Extension
  `ifdef XLEN32
    AES32ESI:  $sformat(decoded, "aes32esi %s, %s, %s, %0d", rd, rs1, rs2, bs);
    AES32ESMI: $sformat(decoded, "aes32esmi %s, %s, %s, %0d", rd, rs1, rs2, bs);
  `else // XLEN64
    AES64ES:  $sformat(decoded, "aes64es %s, %s, %s", rd, rs1, rs2);
    AES64ESM: $sformat(decoded, "aes64esm %s, %s, %s", rd, rs1, rs2);
  `endif
    // Zknd OR Zkne Extension
  `ifdef XLEN64
    AES64KS1I: $sformat(decoded, "aes64ks1i %s, %s, %0d", rd, rs1, instr[23:20]);
    AES64KS2:  $sformat(decoded, "aes64ks2 %s, %s, %s", rd, rs1, rs2);
  `endif
    // Zknh Extension
    SHA256SIG0: $sformat(decoded, "sha256sig0 %s, %s", rd, rs1);
    SHA256SIG1: $sformat(decoded, "sha256sig1 %s, %s", rd, rs1);
    SHA256SUM0: $sformat(decoded, "sha256sum0 %s, %s", rd, rs1);
    SHA256SUM1: $sformat(decoded, "sha256sum1 %s, %s", rd, rs1);
  `ifdef XLEN32
    SHA512SIG0H: $sformat(decoded, "sha512sig0h %s, %s, %s", rd, rs1, rs2);
    SHA512SIG0L: $sformat(decoded, "sha512sig0l %s, %s, %s", rd, rs1, rs2);
    SHA512SIG1H: $sformat(decoded, "sha512sig1h %s, %s, %s", rd, rs1, rs2);
    SHA512SIG1L: $sformat(decoded, "sha512sig1l %s, %s, %s", rd, rs1, rs2);
    SHA512SUM0R: $sformat(decoded, "sha512sum0r %s, %s, %s", rd, rs1, rs2);
    SHA512SUM1R: $sformat(decoded, "sha512sum1r %s, %s, %s", rd, rs1, rs2);
  `else // XLEN64
    SHA512SIG0: $sformat(decoded, "sha512sig0 %s, %s", rd, rs1);
    SHA512SIG1: $sformat(decoded, "sha512sig1 %s, %s", rd, rs1);
    SHA512SUM0: $sformat(decoded, "sha512sum0 %s, %s", rd, rs1);
    SHA512SUM1: $sformat(decoded, "sha512sum1 %s, %s", rd, rs1);
  `endif
    // Zca Extension
    C_ADDI4SPN: begin
        if (immCIWType != '0) begin
            $sformat(decoded, "c.addi4spn %s, sp, %0d", rs2p, immCIWType);
        end else begin
            C_ILLEGAL: $sformat(decoded, "c.illegal");
        end
    end
    C_LW:                             $sformat(decoded, "c.lw %s, %0d(%s)", rs2p, immCLSType, rs1p);
    C_SW:                             $sformat(decoded, "c.sw %s, %0d(%s)", rs2p, immCLSType, rs1p);
    C_NOP: if(rdBits == '0 & immCIType == '0) $sformat(decoded, "c.nop");
    C_ADDI: if(rdBits != '0 & immCIType != '0) $sformat(decoded, "c.addi %s, %0d", rd, immCIType);
    C_LI:   if(rdBits != '0) $sformat(decoded, "c.li %s, %0d", rd, immCIType);
    C_ADDI16SP: if(rdBits == 5'd2 & immCIASPType != '0) $sformat(decoded, "c.addi16sp sp, %0d", immCIASPType);
    C_LUI: if(rdBits != '0 & rdBits != 5'd2 & immCIType != '0) $sformat(decoded, "c.lui %s, %0d", rd, immCIType);
    C_SRLI: $sformat(decoded, "c.srli %s, %0d", rs1p, immCBpType);
    C_SRAI: $sformat(decoded, "c.srai %s, %0d", rs1p, immCBpType);
    C_ANDI: $sformat(decoded, "c.andi %s, %0d", rs1p, $signed(immCBpType));
    C_SUB:  $sformat(decoded, "c.sub %s, %s", rs1p, rs2p);
    C_XOR:  $sformat(decoded, "c.xor %s, %s", rs1p, rs2p);
    C_OR:   $sformat(decoded, "c.or %s, %s", rs1p, rs2p);
    C_AND:  $sformat(decoded, "c.and %s, %s", rs1p, rs2p);
    C_J:    $sformat(decoded, "c.j %0d", immCJType);
    C_BEQZ: $sformat(decoded, "c.beqz %s, %0d", rs1p, immCBType);
    C_BNEZ: $sformat(decoded, "c.bnez %s, %0d", rs1p, immCBType);
    C_SLLI: if(rdBits != '0) $sformat(decoded, "c.slli %s, %0d", rd, immUCIType);
    C_LWSP: if(rdBits != '0) $sformat(decoded, "c.lwsp %s, %0d", rd, immCILSPType);
    C_JR:   if(rdBits != '0 & crs2Bits == '0) $sformat(decoded, "c.jr %s", rd);
    C_MV:   if(rdBits != '0 & crs2Bits != '0) $sformat(decoded, "c.mv %s, %s", rd, crs2);
    C_EBREAK: if(rdBits == '0 & crs2Bits == '0) $sformat(decoded, "c.ebreak");
    C_JALR: if(rdBits != '0 & crs2Bits == '0) $sformat(decoded, "c.jalr %s", rd);
    C_ADD:  if(rdBits != '0 & crs2Bits != '0) $sformat(decoded, "c.add %s, %s", rd, crs2);
    C_SWSP: $sformat(decoded, "c.swsp %s, %0d", crs2, immCSSType);

  `ifdef XLEN32
    C_JAL:  $sformat(decoded, "c.jal %0d", immCJType);
  `else // XLEN64
    C_LD:   $sformat(decoded, "c.ld %s, %0d(%s)", rs2p, immCLSDType, rs1p);
    C_SD:   $sformat(decoded, "c.sd %s, %0d(%s)", rs2p, immCLSDType, rs1p);
    C_ADDIW: if(rdBits != '0) $sformat(decoded, "c.addiw %s, %0d", rd, immCIType);
    C_SUBW:  $sformat(decoded, "c.subw %s, %s", rs1p, rs2p);
    C_ADDW:  $sformat(decoded, "c.addw %s, %s", rs1p, rs2p);
    C_LDSP:  if(rdBits != '0) $sformat(decoded, "c.ldsp %s, %0d", rd, immCILSPDType);
    C_SDSP:  $sformat(decoded, "c.sdsp %s, %0d", crs2, immCSSDType);
  `endif
    // Zcb Extension
    C_LBU: $sformat(decoded, "c.lbu %s, %0d(%s)", rs2p, immCLSBType, rs1p);
    C_LH:  $sformat(decoded, "c.lh %s, %0d(%s)", rs2p, immCLSHType, rs1p);
    C_LHU: $sformat(decoded, "c.lhu %s, %0d(%s)", rs2p, immCLSHType, rs1p);
    C_SB:  $sformat(decoded, "c.sb %s, %0d(%s)", rs2p, immCLSBType, rs1p);
    C_SH:  $sformat(decoded, "c.sh %s, %0d(%s)", rs2p, immCLSHType, rs1p);
    C_ZEXT_B: $sformat(decoded, "c.zext.b %s", rs1p);
    C_SEXT_B: $sformat(decoded, "c.sext.b %s", rs1p);
    C_ZEXT_H: $sformat(decoded, "c.zext.h %s", rs1p);
    C_SEXT_H: $sformat(decoded, "c.sext.h %s", rs1p);
    C_NOT:    $sformat(decoded, "c.not %s", rs1p);
    C_MUL:   $sformat(decoded, "c.mul %s, %s", rs1p, rs2p);
  `ifdef XLEN64
    C_ZEXT_W: $sformat(decoded, "c.zext.w %s", rs1p);
  `endif
    // Zcf Extension
  `ifdef XLEN32
    C_FLW:  $sformat(decoded, "c.flw %s, %0d(%s)", fs2p, immCLSType, rs1p);
    C_FSW:  $sformat(decoded, "c.fsw %s, %0d(%s)", fs2p, immCLSType, rs1p);
    C_FLWSP: $sformat(decoded, "c.flwsp %s, %0d", fd, immCILSPType);
    C_FSWSP: $sformat(decoded, "c.fswsp %s, %0d", cfs2, immCSSType);
  `endif
    // Zcd Extension
    C_FLD:  $sformat(decoded, "c.fld %s, %0d(%s)", fs2p, immCLSDType, rs1p);
    C_FSD:  $sformat(decoded, "c.fsd %s, %0d(%s)", fs2p, immCLSDType, rs1p);
    C_FLDSP: $sformat(decoded, "c.fldsp %s, %0d", fd, immCILSPDType);
    C_FSDSP: $sformat(decoded, "c.fsdsp %s, %0d", cfs2, immCSSDType);

    //V Extension
    VADD_VV:      $sformat(decoded, "vadd.vv %s, %s, %s%s",       vd, vs2, vs1, vm);
    VADD_VX:      $sformat(decoded, "vadd.vx %s, %s, %s%s",       vd, vs2, rs1, vm);
    VADD_VI:      $sformat(decoded, "vadd.vi %s, %s, %0d%s",      vd, vs2, imm5, vm);
    VWADD_VV:     $sformat(decoded, "vwadd.vv %s, %s, %s%s",      vd, vs2, vs1, vm);
    VWADD_VX:     $sformat(decoded, "vwadd.vx %s, %s, %s%s",      vd, vs2, rs1, vm);
    VWADDU_VV:    $sformat(decoded, "vwaddu.vv %s, %s, %s%s",     vd, vs2, vs1, vm);
    VWADDU_VX:    $sformat(decoded, "vwaddu.vx %s, %s, %s%s",     vd, vs2, rs1, vm);
    VWADD_WV:     $sformat(decoded, "vwadd.wv %s, %s, %s%s",      vd, vs2, vs1, vm);
    VWADD_WX:     $sformat(decoded, "vwadd.wx %s, %s, %s%s",      vd, vs2, rs1, vm);
    VWADDU_WV:    $sformat(decoded, "vwaddu.wv %s, %s, %s%s",     vd, vs2, vs1, vm);
    VWADDU_WX:    $sformat(decoded, "vwaddu.wx %s, %s, %s%s",     vd, vs2, rs1, vm);

    VSUB_VV:      $sformat(decoded, "vsub.vv %s, %s, %s%s",       vd, vs2, vs1, vm);
    VSUB_VX:      $sformat(decoded, "vsub.vx %s, %s, %s%s",       vd, vs2, rs1, vm);
    VWSUB_VV:     $sformat(decoded, "vwsub.vv %s, %s, %s%s",      vd, vs2, vs1, vm);
    VWSUB_VX:     $sformat(decoded, "vwsub.vx %s, %s, %s%s",      vd, vs2, rs1, vm);
    VWSUBU_VV:    $sformat(decoded, "vwsubu.vv %s, %s, %s%s",     vd, vs2, vs1, vm);
    VWSUBU_VX:    $sformat(decoded, "vwsubu.vx %s, %s, %s%s",     vd, vs2, rs1, vm);
    VWSUB_WV:     $sformat(decoded, "vwsub.wv %s, %s, %s%s",       vd, vs2, vs1, vm);
    VWSUB_WX:     $sformat(decoded, "vwsub.wx %s, %s, %s%s",       vd, vs2, rs1, vm);
    VWSUBU_WV:    $sformat(decoded, "vwsubu.wv %s, %s, %s%s",      vd, vs2, vs1, vm);
    VWSUBU_WX:    $sformat(decoded, "vwsubu.wx %s, %s, %s%s",      vd, vs2, rs1, vm);
    VRSUB_VX:     $sformat(decoded, "vrsub.vx %s, %s, %s%s",      vd, vs2, rs1, vm);
    VRSUB_VI:     $sformat(decoded, "vrsub.vi %s, %s, %0d%s",     vd, vs2, imm5, vm);

    VZEXT_VF2:    $sformat(decoded, "vzext.vf2 %s, %s%s",         vd, vs2, vm);
    VZEXT_VF4:    $sformat(decoded, "vzext.vf4 %s, %s%s",         vd, vs2, vm);
    VZEXT_VF8:    $sformat(decoded, "vzext.vf8 %s, %s%s",         vd, vs2, vm);
    VSEXT_VF2:    $sformat(decoded, "vsext.vf2 %s, %s%s",         vd, vs2, vm);
    VSEXT_VF4:    $sformat(decoded, "vsext.vf4 %s, %s%s",         vd, vs2, vm);
    VSEXT_VF8:    $sformat(decoded, "vsext.vf8 %s, %s%s",         vd, vs2, vm);

    VADC_VVM:     $sformat(decoded, "vadc.vvm %s, %s, %s, v0",    vd, vs2, vs1);
    VADC_VXM:     $sformat(decoded, "vadc.vxm %s, %s, %s, v0",    vd, vs2, rs1);
    VADC_VIM:     $sformat(decoded, "vadc.vim %s, %s, %0d, v0",   vd, vs2, imm5);
    VSBC_VVM:     $sformat(decoded, "vsbc.vvm %s, %s, %s, v0",    vd, vs2, vs1);
    VSBC_VXM:     $sformat(decoded, "vsbc.vxm %s, %s, %s, v0",    vd, vs2, rs1);
    VMADC_VV:     $sformat(decoded, "vmadc.vv %s, %s, %s",        vd, vs2, vs1);
    VMADC_VX:     $sformat(decoded, "vmadc.vx %s, %s, %s",        vd, vs2, rs1);
    VMADC_VI:     $sformat(decoded, "vmadc.vi %s, %s, %0d",       vd, vs2, imm5);
    VMADC_VVM:    $sformat(decoded, "vmadc.vvm %s, %s, %s, v0",   vd, vs2, vs1);
    VMADC_VXM:    $sformat(decoded, "vmadc.vxm %s, %s, %s, v0",   vd, vs2, rs1);
    VMADC_VIM:    $sformat(decoded, "vmadc.vim %s, %s, %0d, v0",  vd, vs2, imm5);
    VMSBC_VV:     $sformat(decoded, "vmsbc.vv %s, %s, %s",        vd, vs2, vs1);
    VMSBC_VX:     $sformat(decoded, "vmsbc.vx %s, %s, %s",        vd, vs2, rs1);
    VMSBC_VVM:    $sformat(decoded, "vmsbc.vvm %s, %s, %s, v0",   vd, vs2, vs1);
    VMSBC_VXM:    $sformat(decoded, "vmsbc.vxm %s, %s, %s, v0",   vd, vs2, rs1);

    VAND_VV:      $sformat(decoded, "vand.vv %s, %s, %s%s",       vd, vs2, vs1, vm);
    VAND_VX:      $sformat(decoded, "vand.vx %s, %s, %s%s",       vd, vs2, rs1, vm);
    VAND_VI:      $sformat(decoded, "vand.vi %s, %s, %0d%s",      vd, vs2, imm5, vm);
    VOR_VV:       $sformat(decoded, "vor.vv %s, %s, %s%s",        vd, vs2, vs1, vm);
    VOR_VX:       $sformat(decoded, "vor.vx %s, %s, %s%s",        vd, vs2, rs1, vm);
    VOR_VI:       $sformat(decoded, "vor.vi %s, %s, %0d%s",       vd, vs2, imm5, vm);
    VXOR_VV:      $sformat(decoded, "vxor.vv %s, %s, %s%s",       vd, vs2, vs1, vm);
    VXOR_VX:      $sformat(decoded, "vxor.vx %s, %s, %s%s",       vd, vs2, rs1, vm);
    VXOR_VI:      $sformat(decoded, "vxor.vi %s, %s, %0d%s",      vd, vs2, imm5, vm);
    VSLL_VV:      $sformat(decoded, "vsll.vv %s, %s, %s%s",       vd, vs2, vs1, vm);
    VSLL_VX:      $sformat(decoded, "vsll.vx %s, %s, %s%s",       vd, vs2, rs1, vm);
    VSLL_VI:      $sformat(decoded, "vsll.vi %s, %s, %0d%s",      vd, vs2, uimm5, vm);
    VSRL_VV:      $sformat(decoded, "vsrl.vv %s, %s, %s%s",       vd, vs2, vs1, vm);
    VSRL_VX:      $sformat(decoded, "vsrl.vx %s, %s, %s%s",       vd, vs2, rs1, vm);
    VSRL_VI:      $sformat(decoded, "vsrl.vi %s, %s, %0d%s",      vd, vs2, uimm5, vm);
    VNSRL_WV:     $sformat(decoded, "vnsrl.wv %s, %s, %s%s",      vd, vs2, vs1, vm);
    VNSRL_WX:     $sformat(decoded, "vnsrl.wx %s, %s, %s%s",      vd, vs2, rs1, vm);
    VNSRL_WI:     $sformat(decoded, "vnsrl.wi %s, %s, %0d%s",     vd, vs2, uimm5, vm);
    VSRA_VV:      $sformat(decoded, "vsra.vv %s, %s, %s%s",       vd, vs2, vs1, vm);
    VSRA_VX:      $sformat(decoded, "vsra.vx %s, %s, %s%s",       vd, vs2, rs1, vm);
    VSRA_VI:      $sformat(decoded, "vsra.vi %s, %s, %0d%s",      vd, vs2, uimm5, vm);
    VNSRA_WV:     $sformat(decoded, "vnsra.wv %s, %s, %s%s",      vd, vs2, vs1, vm);
    VNSRA_WX:     $sformat(decoded, "vnsra.wx %s, %s, %s%s",      vd, vs2, rs1, vm);
    VNSRA_WI:     $sformat(decoded, "vnsra.wi %s, %s, %0d%s",     vd, vs2, uimm5, vm);

    VMSEQ_VV:     $sformat(decoded, "vmseq.vv %s, %s, %s%s",       vd, vs2, vs1, vm);
    VMSEQ_VX:     $sformat(decoded, "vmseq.vx %s, %s, %s%s",       vd, vs2, rs1, vm);
    VMSEQ_VI:     $sformat(decoded, "vmseq.vi %s, %s, %0d%s",      vd, vs2, imm5, vm);
    VMSNE_VV:     $sformat(decoded, "vmsne.vv %s, %s, %s%s",       vd, vs2, vs1, vm);
    VMSNE_VX:     $sformat(decoded, "vmsne.vx %s, %s, %s%s",       vd, vs2, rs1, vm);
    VMSNE_VI:     $sformat(decoded, "vmsne.vi %s, %s, %0d%s",      vd, vs2, imm5, vm);
    VMSLT_VV:     $sformat(decoded, "vmslt.vv %s, %s, %s%s",       vd, vs2, vs1, vm);
    VMSLT_VX:     $sformat(decoded, "vmslt.vx %s, %s, %s%s",       vd, vs2, rs1, vm);
    VMSLTU_VV:    $sformat(decoded, "vmsltu.vv %s, %s, %s%s",      vd, vs2, vs1, vm);
    VMSLTU_VX:    $sformat(decoded, "vmsltu.vx %s, %s, %s%s",      vd, vs2, rs1, vm);
    VMSLE_VV:     $sformat(decoded, "vmsle.vv %s, %s, %s%s",       vd, vs2, vs1, vm);
    VMSLE_VX:     $sformat(decoded, "vmsle.vx %s, %s, %s%s",       vd, vs2, rs1, vm);
    VMSLE_VI:     $sformat(decoded, "vmsle.vi %s, %s, %0d%s",      vd, vs2, imm5, vm);
    VMSLEU_VV:    $sformat(decoded, "vmsleu.vv %s, %s, %s%s",      vd, vs2, vs1, vm);
    VMSLEU_VX:    $sformat(decoded, "vmsleu.vx %s, %s, %s%s",      vd, vs2, rs1, vm);
    VMSLEU_VI:    $sformat(decoded, "vmsleu.vi %s, %s, %0d%s",     vd, vs2, imm5, vm);
    VMSGT_VX:     $sformat(decoded, "vmsgt.vx %s, %s, %s%s",       vd, vs2, rs1, vm);
    VMSGT_VI:     $sformat(decoded, "vmsgt.vi %s, %s, %0d%s",      vd, vs2, imm5, vm);
    VMSGTU_VX:    $sformat(decoded, "vmsgtu.vx %s, %s, %s%s",      vd, vs2, rs1, vm);
    VMSGTU_VI:    $sformat(decoded, "vmsgtu.vi %s, %s, %0d%s",     vd, vs2, imm5, vm);

    VMIN_VV:      $sformat(decoded, "vmin.vv %s, %s, %s%s",       vd, vs2, vs1, vm);
    VMIN_VX:      $sformat(decoded, "vmin.vx %s, %s, %s%s",       vd, vs2, rs1, vm);
    VMINU_VV:     $sformat(decoded, "vminu.vv %s, %s, %s%s",      vd, vs2, vs1, vm);
    VMINU_VX:     $sformat(decoded, "vminu.vx %s, %s, %s%s",      vd, vs2, rs1, vm);
    VMAX_VV:      $sformat(decoded, "vmax.vv %s, %s, %s%s",       vd, vs2, vs1, vm);
    VMAX_VX:      $sformat(decoded, "vmax.vx %s, %s, %s%s",       vd, vs2, rs1, vm);
    VMAXU_VV:     $sformat(decoded, "vmaxu.vv %s, %s, %s%s",      vd, vs2, vs1, vm);
    VMAXU_VX:     $sformat(decoded, "vmaxu.vx %s, %s, %s%s",      vd, vs2, rs1, vm);

    VMUL_VV:      $sformat(decoded, "vmul.vv %s, %s, %s%s",       vd, vs2, vs1, vm);
    VMUL_VX:      $sformat(decoded, "vmul.vx %s, %s, %s%s",       vd, vs2, rs1, vm);
    VMULH_VV:     $sformat(decoded, "vmulh.vv %s, %s, %s%s",      vd, vs2, vs1, vm);
    VMULH_VX:     $sformat(decoded, "vmulh.vx %s, %s, %s%s",      vd, vs2, rs1, vm);
    VMULHU_VV:    $sformat(decoded, "vmulhu.vv %s, %s, %s%s",     vd, vs2, vs1, vm);
    VMULHU_VX:    $sformat(decoded, "vmulhu.vx %s, %s, %s%s",     vd, vs2, rs1, vm);
    VMULHSU_VV:   $sformat(decoded, "vmulhsu.vv %s, %s, %s%s",    vd, vs2, vs1, vm);
    VMULHSU_VX:   $sformat(decoded, "vmulhsu.vx %s, %s, %s%s",    vd, vs2, rs1, vm);
    VWMUL_VV:     $sformat(decoded, "vwmul.vv %s, %s, %s%s",      vd, vs2, vs1, vm);
    VWMUL_VX:     $sformat(decoded, "vwmul.vx %s, %s, %s%s",      vd, vs2, rs1, vm);
    VWMULU_VV:    $sformat(decoded, "vwmulu.vv %s, %s, %s%s",     vd, vs2, vs1, vm);
    VWMULU_VX:    $sformat(decoded, "vwmulu.vx %s, %s, %s%s",     vd, vs2, rs1, vm);
    VWMULSU_VV:   $sformat(decoded, "vwmulsu.vv %s, %s, %s%s",    vd, vs2, vs1, vm);
    VWMULSU_VX:   $sformat(decoded, "vwmulsu.vx %s, %s, %s%s",    vd, vs2, rs1, vm);
    VDIV_VV:      $sformat(decoded, "vdiv.vv %s, %s, %s%s",       vd, vs2, vs1, vm);
    VDIV_VX:      $sformat(decoded, "vdiv.vx %s, %s, %s%s",       vd, vs2, rs1, vm);
    VDIVU_VV:     $sformat(decoded, "vdivu.vv %s, %s, %s%s",      vd, vs2, vs1, vm);
    VDIVU_VX:     $sformat(decoded, "vdivu.vx %s, %s, %s%s",      vd, vs2, rs1, vm);
    VREM_VV:      $sformat(decoded, "vrem.vv %s, %s, %s%s",       vd, vs2, vs1, vm);
    VREM_VX:      $sformat(decoded, "vrem.vx %s, %s, %s%s",       vd, vs2, rs1, vm);
    VREMU_VV:     $sformat(decoded, "vremu.vv %s, %s, %s%s",      vd, vs2, vs1, vm);
    VREMU_VX:     $sformat(decoded, "vremu.vx %s, %s, %s%s",      vd, vs2, rs1, vm);

    VMACC_VV:     $sformat(decoded, "vmacc.vv %s, %s, %s%s",      vd, vs1, vs2, vm);
    VMACC_VX:     $sformat(decoded, "vmacc.vx %s, %s, %s%s",      vd, rs1, vs2, vm);
    VNMSAC_VV:    $sformat(decoded, "vnmsac.vv %s, %s, %s%s",     vd, vs1, vs2, vm);
    VNMSAC_VX:    $sformat(decoded, "vnmsac.vx %s, %s, %s%s",     vd, rs1, vs2, vm);
    VMADD_VV:     $sformat(decoded, "vmadd.vv %s, %s, %s%s",      vd, vs1, vs2, vm);
    VMADD_VX:     $sformat(decoded, "vmadd.vx %s, %s, %s%s",      vd, rs1, vs2, vm);
    VNMSUB_VV:    $sformat(decoded, "vnmsub.vv %s, %s, %s%s",     vd, vs1, vs2, vm);
    VNMSUB_VX:    $sformat(decoded, "vnmsub.vx %s, %s, %s%s",     vd, rs1, vs2, vm);
    VWMACC_VV:    $sformat(decoded, "vwmacc.vv %s, %s, %s%s",     vd, vs1, vs2, vm);
    VWMACC_VX:    $sformat(decoded, "vwmacc.vx %s, %s, %s%s",     vd, rs1, vs2, vm);
    VWMACCU_VV:   $sformat(decoded, "vwmaccu.vv %s, %s, %s%s",    vd, vs1, vs2, vm);
    VWMACCU_VX:   $sformat(decoded, "vwmaccu.vx %s, %s, %s%s",    vd, rs1, vs2, vm);
    VWMACCSU_VV:  $sformat(decoded, "vwmaccsu.vv %s, %s, %s%s",   vd, vs1, vs2, vm);
    VWMACCSU_VX:  $sformat(decoded, "vwmaccsu.vx %s, %s, %s%s",   vd, rs1, vs2, vm);
    VWMACCUS_VX:  $sformat(decoded, "vwmaccus.vx %s, %s, %s%s",   vd, rs1, vs2, vm);

    VMERGE_VVM:   $sformat(decoded, "vmerge.vvm %s, %s, %s, v0",  vd, vs2, vs1);
    VMERGE_VXM:   $sformat(decoded, "vmerge.vxm %s, %s, %s, v0",  vd, vs2, rs1);
    VMERGE_VIM:   $sformat(decoded, "vmerge.vim %s, %s, %0d, v0", vd, vs2, imm5);
    VMV_V_V:      $sformat(decoded, "vmv.v.v %s, %s",             vd, vs1);
    VMV_V_X:      $sformat(decoded, "vmv.v.x %s, %s",             vd, rs1);
    VMV_V_I:      $sformat(decoded, "vmv.v.i %s, %0d",            vd, imm5);

    VSADD_VV:     $sformat(decoded, "vsadd.vv %s, %s, %s%s",      vd, vs2, vs1, vm);
    VSADD_VX:     $sformat(decoded, "vsadd.vx %s, %s, %s%s",      vd, vs2, rs1, vm);
    VSADD_VI:     $sformat(decoded, "vsadd.vi %s, %s, %0d%s",     vd, vs2, imm5, vm);
    VSADDU_VV:    $sformat(decoded, "vsaddu.vv %s, %s, %s%s",     vd, vs2, vs1, vm);
    VSADDU_VX:    $sformat(decoded, "vsaddu.vx %s, %s, %s%s",     vd, vs2, rs1, vm);
    VSADDU_VI:    $sformat(decoded, "vsaddu.vi %s, %s, %0d%s",    vd, vs2, imm5, vm);
    VSSUB_VV:     $sformat(decoded, "vssub.vv %s, %s, %s%s",      vd, vs2, vs1, vm);
    VSSUB_VX:     $sformat(decoded, "vssub.vx %s, %s, %s%s",      vd, vs2, rs1, vm);
    VSSUBU_VV:    $sformat(decoded, "vssubu.vv %s, %s, %s%s",     vd, vs2, vs1, vm);
    VSSUBU_VX:    $sformat(decoded, "vssubu.vx %s, %s, %s%s",     vd, vs2, rs1, vm);
    VAADD_VV:     $sformat(decoded, "vaadd.vv %s, %s, %s%s",      vd, vs2, vs1, vm);
    VAADD_VX:     $sformat(decoded, "vaadd.vx %s, %s, %s%s",      vd, vs2, rs1, vm);
    VAADDU_VV:    $sformat(decoded, "vaaddu.vv %s, %s, %s%s",     vd, vs2, vs1, vm);
    VAADDU_VX:    $sformat(decoded, "vaaddu.vx %s, %s, %s%s",     vd, vs2, rs1, vm);
    VASUB_VV:     $sformat(decoded, "vasub.vv %s, %s, %s%s",      vd, vs2, vs1, vm);
    VASUB_VX:     $sformat(decoded, "vasub.vx %s, %s, %s%s",      vd, vs2, rs1, vm);
    VASUBU_VV:    $sformat(decoded, "vasubu.vv %s, %s, %s%s",     vd, vs2, vs1, vm);
    VASUBU_VX:    $sformat(decoded, "vasubu.vx %s, %s, %s%s",     vd, vs2, rs1, vm);

    VSMUL_VV:     $sformat(decoded, "vsmul.vv %s, %s, %s%s",      vd, vs2, vs1, vm);
    VSMUL_VX:     $sformat(decoded, "vsmul.vx %s, %s, %s%s",      vd, vs2, rs1, vm);
    VSSRL_VV:     $sformat(decoded, "vssrl.vv %s, %s, %s%s",      vd, vs2, vs1, vm);
    VSSRL_VX:     $sformat(decoded, "vssrl.vx %s, %s, %s%s",      vd, vs2, rs1, vm);
    VSSRL_VI:     $sformat(decoded, "vssrl.vi %s, %s, %0d%s",     vd, vs2, uimm5, vm);
    VSSRA_VV:     $sformat(decoded, "vssra.vv %s, %s, %s%s",      vd, vs2, vs1, vm);
    VSSRA_VX:     $sformat(decoded, "vssra.vx %s, %s, %s%s",      vd, vs2, rs1, vm);
    VSSRA_VI:     $sformat(decoded, "vssra.vi %s, %s, %0d%s",     vd, vs2, uimm5, vm);
    VNCLIP_WV:    $sformat(decoded, "vnclip.wv %s, %s, %s%s",     vd, vs2, vs1, vm);
    VNCLIP_WX:    $sformat(decoded, "vnclip.wx %s, %s, %s%s",     vd, vs2, rs1, vm);
    VNCLIP_WI:    $sformat(decoded, "vnclip.wi %s, %s, %0d%s",    vd, vs2, uimm5, vm);
    VNCLIPU_WV:   $sformat(decoded, "vnclipu.wv %s, %s, %s%s",    vd, vs2, vs1, vm);
    VNCLIPU_WX:   $sformat(decoded, "vnclipu.wx %s, %s, %s%s",    vd, vs2, rs1, vm);
    VNCLIPU_WI:   $sformat(decoded, "vnclipu.wi %s, %s, %0d%s",   vd, vs2, uimm5, vm);

    VREDSUM_VS:   $sformat(decoded, "vredsum.vs %s, %s, %s%s",    vd, vs2, vs1, vm);
    VWREDSUM_VS:  $sformat(decoded, "vwredsum.vs %s, %s, %s%s",   vd, vs2, vs1, vm);
    VWREDSUMU_VS: $sformat(decoded, "vwredsumu.vs %s, %s, %s%s",  vd, vs2, vs1, vm);
    VREDMAX_VS:   $sformat(decoded, "vredmax.vs %s, %s, %s%s",    vd, vs2, vs1, vm);
    VREDMAXU_VS:  $sformat(decoded, "vredmaxu.vs %s, %s, %s%s",   vd, vs2, vs1, vm);
    VREDMIN_VS:   $sformat(decoded, "vredmin.vs %s, %s, %s%s",    vd, vs2, vs1, vm);
    VREDMINU_VS:  $sformat(decoded, "vredminu.vs %s, %s, %s%s",   vd, vs2, vs1, vm);
    VREDAND_VS:   $sformat(decoded, "vredand.vs %s, %s, %s%s",    vd, vs2, vs1, vm);
    VREDOR_VS:    $sformat(decoded, "vredor.vs %s, %s, %s%s",     vd, vs2, vs1, vm);
    VREDXOR_VS:   $sformat(decoded, "vredxor.vs %s, %s, %s%s",    vd, vs2, vs1, vm);

    VMAND_MM:     $sformat(decoded, "vmand.mm %s, %s, %s",        vd, vs2, vs1);
    VMNAND_MM:    $sformat(decoded, "vmnand.mm %s, %s, %s",       vd, vs2, vs1);
    VMANDN_MM:    $sformat(decoded, "vmandn.mm %s, %s, %s",       vd, vs2, vs1);
    VMOR_MM:      $sformat(decoded, "vmor.mm %s, %s, %s",         vd, vs2, vs1);
    VMNOR_MM:     $sformat(decoded, "vmnor.mm %s, %s, %s",        vd, vs2, vs1);
    VMORN_MM:     $sformat(decoded, "vmorn.mm %s, %s, %s",        vd, vs2, vs1);
    VMXOR_MM:     $sformat(decoded, "vmxor.mm %s, %s, %s",        vd, vs2, vs1);
    VMXNOR_MM:    $sformat(decoded, "vmxnor.mm %s, %s, %s",       vd, vs2, vs1);

    VCPOP_M:      $sformat(decoded, "vcpop.m %s, %s%s",           rd, vs2, vm);
    VFIRST_M:     $sformat(decoded, "vfirst.m %s, %s%s",          rd, vs2, vm);
    VMSBF_M:      $sformat(decoded, "vmsbf.m %s, %s%s",           vd, vs2, vm);
    VMSIF_M:      $sformat(decoded, "vmsif.m %s, %s%s",           vd, vs2, vm);
    VMSOF_M:      $sformat(decoded, "vmsof.m %s, %s%s",           vd, vs2, vm);
    VIOTA_M:      $sformat(decoded, "viota.m %s, %s%s",           vd, vs2, vm);
    VID_V:        $sformat(decoded, "vid.v %s%s",                 vd, vm);

    VMV_X_S:      $sformat(decoded, "vmv.x.s %s, %s",             rd, vs2);
    VMV_S_X:      $sformat(decoded, "vmv.s.x %s, %s",             vd, rs1);

    VSLIDEUP_VX:  $sformat(decoded, "vslideup.vx %s, %s, %s%s",      vd, vs2, rs1, vm);
    VSLIDEUP_VI:  $sformat(decoded, "vslideup.vi %s, %s, %0d%s",     vd, vs2, uimm5, vm);
    VSLIDEDOWN_VX:  $sformat(decoded, "vslidedown.vx %s, %s, %s%s",  vd, vs2, rs1, vm);
    VSLIDEDOWN_VI:  $sformat(decoded, "vslidedown.vi %s, %s, %0d%s", vd, vs2, uimm5, vm);
    VSLIDE1UP_VX:   $sformat(decoded, "vslide1up.vx %s, %s, %s%s",   vd, vs2, rs1, vm);
    VSLIDE1DOWN_VX: $sformat(decoded, "vslide1down.vx %s, %s, %s%s", vd, vs2, rs1, vm);
    VRGATHER_VV:  $sformat(decoded, "vrgather.vv %s, %s, %s%s",      vd, vs2, vs1, vm);
    VRGATHER_VX:  $sformat(decoded, "vrgather.vx %s, %s, %s%s",      vd, vs2, rs1, vm);
    VRGATHER_VI:  $sformat(decoded, "vrgather.vi %s, %s, %0d%s",     vd, vs2, uimm5, vm);
    VCOMPRESS_VM: $sformat(decoded, "vcompress.vm %s, %s, %s",       vd, vs2, vs1);

    VMV1R_V:      $sformat(decoded, "vmv1r.v %s, %s",             vd, vs2);
    VMV2R_V:      $sformat(decoded, "vmv2r.v %s, %s",             vd, vs2);
    VMV4R_V:      $sformat(decoded, "vmv4r.v %s, %s",             vd, vs2);
    VMV8R_V:      $sformat(decoded, "vmv8r.v %s, %s",             vd, vs2);

    VRGATHEREI16_VV:  $sformat(decoded, "vrgatherei16.vv %s, %s, %s%s",   vd, vs2, vs1, vm);

    // V Extension: Floating Point
    VFADD_VV:     $sformat(decoded, "vfadd.vv %s, %s, %s%s",       vd, vs2, vs1, vm);
    VFADD_VF:     $sformat(decoded, "vfadd.vf %s, %s, %s%s",       vd, vs2, fs1, vm);
    VFWADD_VV:    $sformat(decoded, "vfwadd.vv %s, %s, %s%s",      vd, vs2, vs1, vm);
    VFWADD_VF:    $sformat(decoded, "vfwadd.vf %s, %s, %s%s",      vd, vs2, fs1, vm);
    VFWADD_WV:    $sformat(decoded, "vfwadd.wv %s, %s, %s%s",      vd, vs2, vs1, vm);
    VFWADD_WF:    $sformat(decoded, "vfwadd.wf %s, %s, %s%s",      vd, vs2, fs1, vm);
    VFSUB_VV:     $sformat(decoded, "vfsub.vv %s, %s, %s%s",       vd, vs2, vs1, vm);
    VFSUB_VF:     $sformat(decoded, "vfsub.vf %s, %s, %s%s",       vd, vs2, fs1, vm);
    VFWSUB_VV:    $sformat(decoded, "vfwsub.vv %s, %s, %s%s",      vd, vs2, vs1, vm);
    VFWSUB_VF:    $sformat(decoded, "vfwsub.vf %s, %s, %s%s",      vd, vs2, fs1, vm);
    VFWSUB_WV:    $sformat(decoded, "vfwsub.wv %s, %s, %s%s",      vd, vs2, vs1, vm);
    VFWSUB_WF:    $sformat(decoded, "vfwsub.wf %s, %s, %s%s",      vd, vs2, fs1, vm);
    VFRSUB_VF:    $sformat(decoded, "vfrsub.vf %s, %s, %s%s",      vd, vs2, fs1, vm);

    VFMUL_VV:     $sformat(decoded, "vfmul.vv %s, %s, %s%s",       vd, vs2, vs1, vm);
    VFMUL_VF:     $sformat(decoded, "vfmul.vf %s, %s, %s%s",       vd, vs2, fs1, vm);
    VFWMUL_VV:    $sformat(decoded, "vfwmul.vv %s, %s, %s%s",      vd, vs2, vs1, vm);
    VFWMUL_VF:    $sformat(decoded, "vfwmul.vf %s, %s, %s%s",      vd, vs2, fs1, vm);
    VFDIV_VV:     $sformat(decoded, "vfdiv.vv %s, %s, %s%s",       vd, vs2, vs1, vm);
    VFDIV_VF:     $sformat(decoded, "vfdiv.vf %s, %s, %s%s",       vd, vs2, fs1, vm);
    VFRDIV_VF:    $sformat(decoded, "vfrdiv.vf %s, %s, %s%s",      vd, vs2, fs1, vm);

    VFMACC_VV:    $sformat(decoded, "vfmacc.vv %s, %s, %s%s",      vd, vs1, vs2, vm);
    VFMACC_VF:    $sformat(decoded, "vfmacc.vf %s, %s, %s%s",      vd, fs1, vs2, vm);
    VFNMACC_VV:   $sformat(decoded, "vfnmacc.vv %s, %s, %s%s",     vd, vs1, vs2, vm);
    VFNMACC_VF:   $sformat(decoded, "vfnmacc.vf %s, %s, %s%s",     vd, fs1, vs2, vm);
    VFMSAC_VV:    $sformat(decoded, "vfmsac.vv %s, %s, %s%s",      vd, vs1, vs2, vm);
    VFMSAC_VF:    $sformat(decoded, "vfmsac.vf %s, %s, %s%s",      vd, fs1, vs2, vm);
    VFNMSAC_VV:   $sformat(decoded, "vfnmsac.vv %s, %s, %s%s",     vd, vs1, vs2, vm);
    VFNMSAC_VF:   $sformat(decoded, "vfnmsac.vf %s, %s, %s%s",     vd, fs1, vs2, vm);
    VFMADD_VV:    $sformat(decoded, "vfmadd.vv %s, %s, %s%s",      vd, vs1, vs2, vm);
    VFMADD_VF:    $sformat(decoded, "vfmadd.vf %s, %s, %s%s",      vd, fs1, vs2, vm);
    VFNMADD_VV:   $sformat(decoded, "vfnmadd.vv %s, %s, %s%s",     vd, vs1, vs2, vm);
    VFNMADD_VF:   $sformat(decoded, "vfnmadd.vf %s, %s, %s%s",     vd, fs1, vs2, vm);
    VFMSUB_VV:    $sformat(decoded, "vfmsub.vv %s, %s, %s%s",      vd, vs1, vs2, vm);
    VFMSUB_VF:    $sformat(decoded, "vfmsub.vf %s, %s, %s%s",      vd, fs1, vs2, vm);
    VFNMSUB_VV:   $sformat(decoded, "vfnmsub.vv %s, %s, %s%s",     vd, vs1, vs2, vm);
    VFNMSUB_VF:   $sformat(decoded, "vfnmsub.vf %s, %s, %s%s",     vd, fs1, vs2, vm);
    VFWMACC_VV:   $sformat(decoded, "vfwmacc.vv %s, %s, %s%s",     vd, vs1, vs2, vm);
    VFWMACC_VF:   $sformat(decoded, "vfwmacc.vf %s, %s, %s%s",     vd, fs1, vs2, vm);
    VFWNMACC_VV:  $sformat(decoded, "vfwnmacc.vv %s, %s, %s%s",    vd, vs1, vs2, vm);
    VFWNMACC_VF:  $sformat(decoded, "vfwnmacc.vf %s, %s, %s%s",    vd, fs1, vs2, vm);
    VFWMSAC_VV:   $sformat(decoded, "vfwmsac.vv %s, %s, %s%s",     vd, vs1, vs2, vm);
    VFWMSAC_VF:   $sformat(decoded, "vfwmsac.vf %s, %s, %s%s",     vd, fs1, vs2, vm);
    VFWNMSAC_VV:  $sformat(decoded, "vfwnmsac.vv %s, %s, %s%s",    vd, vs1, vs2, vm);
    VFWNMSAC_VF:  $sformat(decoded, "vfwnmsac.vf %s, %s, %s%s",    vd, fs1, vs2, vm);

    VFSQRT_V:     $sformat(decoded, "vfsqrt.v %s, %s%s",       vd, vs2, vm);
    VFRSQRT7_V:   $sformat(decoded, "vfrsqrt7.v %s, %s%s",     vd, vs2, vm);
    VFREC7_V:     $sformat(decoded, "vfrec7.v %s, %s%s",       vd, vs2, vm);

    VFMIN_VV:     $sformat(decoded, "vfmin.vv %s, %s, %s%s",       vd, vs2, vs1, vm);
    VFMIN_VF:     $sformat(decoded, "vfmin.vf %s, %s, %s%s",       vd, vs2, fs1, vm);
    VFMAX_VV:     $sformat(decoded, "vfmax.vv %s, %s, %s%s",       vd, vs2, vs1, vm);
    VFMAX_VF:     $sformat(decoded, "vfmax.vf %s, %s, %s%s",       vd, vs2, fs1, vm);
    VFSGNJ_VV:    $sformat(decoded, "vfsgnj.vv %s, %s, %s%s",      vd, vs2, vs1, vm);
    VFSGNJ_VF:    $sformat(decoded, "vfsgnj.vf %s, %s, %s%s",      vd, vs2, fs1, vm);
    VFSGNJN_VV:   $sformat(decoded, "vfsgnjn.vv %s, %s, %s%s",     vd, vs2, vs1, vm);
    VFSGNJN_VF:   $sformat(decoded, "vfsgnjn.vf %s, %s, %s%s",     vd, vs2, fs1, vm);
    VFSGNJX_VV:   $sformat(decoded, "vfsgnjx.vv %s, %s, %s%s",     vd, vs2, vs1, vm);
    VFSGNJX_VF:   $sformat(decoded, "vfsgnjx.vf %s, %s, %s%s",     vd, vs2, fs1, vm);

    VFREDOSUM_VS:   $sformat(decoded, "vfredosum.vs %s, %s, %s%s",    vd, vs2, vs1, vm);
    VFWREDOSUM_VS:  $sformat(decoded, "vfwredosum.vs %s, %s, %s%s",   vd, vs2, vs1, vm);
    VFREDUSUM_VS:   $sformat(decoded, "vfredusum.vs %s, %s, %s%s",    vd, vs2, vs1, vm);
    VFWREDUSUM_VS:  $sformat(decoded, "vfwredusum.vs %s, %s, %s%s",   vd, vs2, vs1, vm);
    VFREDMAX_VS:    $sformat(decoded, "vfredmax.vs %s, %s, %s%s",     vd, vs2, vs1, vm);
    VFREDMIN_VS:    $sformat(decoded, "vfredmin.vs %s, %s, %s%s",     vd, vs2, vs1, vm);

    VMFEQ_VV:     $sformat(decoded, "vmfeq.vv %s, %s, %s%s",       vd, vs2, vs1, vm);
    VMFEQ_VF:     $sformat(decoded, "vmfeq.vf %s, %s, %s%s",       vd, vs2, fs1, vm);
    VMFNE_VV:     $sformat(decoded, "vmfne.vv %s, %s, %s%s",       vd, vs2, vs1, vm);
    VMFNE_VF:     $sformat(decoded, "vmfne.vf %s, %s, %s%s",       vd, vs2, fs1, vm);
    VMFLT_VV:     $sformat(decoded, "vmflt.vv %s, %s, %s%s",       vd, vs2, vs1, vm);
    VMFLT_VF:     $sformat(decoded, "vmflt.vf %s, %s, %s%s",       vd, vs2, fs1, vm);
    VMFLE_VV:     $sformat(decoded, "vmfle.vv %s, %s, %s%s",       vd, vs2, vs1, vm);
    VMFLE_VF:     $sformat(decoded, "vmfle.vf %s, %s, %s%s",       vd, vs2, fs1, vm);
    VMFGT_VF:     $sformat(decoded, "vmfgt.vf %s, %s, %s%s",       vd, vs2, fs1, vm);
    VMFGE_VF:     $sformat(decoded, "vmfge.vf %s, %s, %s%s",       vd, vs2, fs1, vm);

    VFMERGE_VFM:  $sformat(decoded, "vfmerge.vfm %s, %s, %s, v0",  vd, vs2, fs1);
    VFMV_V_F:     $sformat(decoded, "vfmv.v.f %s, %s",             vd, fs1);
    VFMV_F_S:     $sformat(decoded, "vfmv.f.s %s, %s",             fd, vs2);
    VFMV_S_F:     $sformat(decoded, "vfmv.s.f %s, %s",             vd, fs1);

    VFSLIDE1UP_VF:   $sformat(decoded, "vfslide1up.vf %s, %s, %s%s",   vd, vs2, fs1, vm);
    VFSLIDE1DOWN_VF: $sformat(decoded, "vfslide1down.vf %s, %s, %s%s", vd, vs2, fs1, vm);

    VFCVT_XU_F_V:       $sformat(decoded, "vfcvt.xu.f.v %s, %s%s",      vd, vs2, vm);
    VFWCVT_XU_F_V:      $sformat(decoded, "vfwcvt.xu.f.v %s, %s%s",     vd, vs2, vm);
    VFNCVT_XU_F_W:      $sformat(decoded, "vfncvt.xu.f.w %s, %s%s",     vd, vs2, vm);
    VFCVT_X_F_V:        $sformat(decoded, "vfcvt.x.f.v %s, %s%s",       vd, vs2, vm);
    VFWCVT_X_F_V:       $sformat(decoded, "vfwcvt.x.f.v %s, %s%s",      vd, vs2, vm);
    VFNCVT_X_F_W:       $sformat(decoded, "vfncvt.x.f.w %s, %s%s",      vd, vs2, vm);
    VFCVT_RTZ_XU_F_V:   $sformat(decoded, "vfcvt.rtz.xu.f.v %s, %s%s",  vd, vs2, vm);
    VFWCVT_RTZ_XU_F_V:  $sformat(decoded, "vfwcvt.rtz.xu.f.v %s, %s%s", vd, vs2, vm);
    VFNCVT_RTZ_XU_F_W:  $sformat(decoded, "vfncvt.rtz.xu.f.w %s, %s%s", vd, vs2, vm);
    VFCVT_RTZ_X_F_V:    $sformat(decoded, "vfcvt.rtz.x.f.v %s, %s%s",  vd, vs2, vm);
    VFWCVT_RTZ_X_F_V:   $sformat(decoded, "vfwcvt.rtz.x.f.v %s, %s%s", vd, vs2, vm);
    VFNCVT_RTZ_X_F_W:   $sformat(decoded, "vfncvt.rtz.x.f.w %s, %s%s", vd, vs2, vm);
    VFCVT_F_XU_V:       $sformat(decoded, "vfcvt.f.xu.v %s, %s%s",      vd, vs2, vm);
    VFWCVT_F_XU_V:      $sformat(decoded, "vfwcvt.f.xu.v %s, %s%s",     vd, vs2, vm);
    VFNCVT_F_XU_W:      $sformat(decoded, "vfncvt.f.xu.w %s, %s%s",     vd, vs2, vm);
    VFCVT_F_X_V:        $sformat(decoded, "vfcvt.f.x.v %s, %s%s",       vd, vs2, vm);
    VFWCVT_F_X_V:       $sformat(decoded, "vfwcvt.f.x.v %s, %s%s",      vd, vs2, vm);
    VFNCVT_F_X_W:       $sformat(decoded, "vfncvt.f.x.w %s, %s%s",      vd, vs2, vm);
    VFWCVT_F_F_V:       $sformat(decoded, "vfwcvt.f.f.v %s, %s%s",      vd, vs2, vm);
    VFNCVT_F_F_W:       $sformat(decoded, "vfncvt.f.f.w %s, %s%s",      vd, vs2, vm);
    VFNCVT_ROD_F_F_W:   $sformat(decoded, "vfncvt.rod.f.f.w %s, %s%s",  vd, vs2, vm);

    VFCLASS_V:          $sformat(decoded, "vfclass.v %s, %s%s",         vd, vs2, vm);

    // V Extension: Load/Store
    VLE8_V:       $sformat(decoded, "vle8.v %s, (%s)%s",          vd, rs1, vm);
    VLE16_V:      $sformat(decoded, "vle16.v %s, (%s)%s",         vd, rs1, vm);
    VLE32_V:      $sformat(decoded, "vle32.v %s, (%s)%s",         vd, rs1, vm);
    VLE64_V:      $sformat(decoded, "vle64.v %s, (%s)%s",         vd, rs1, vm);
    VLE8FF_V:     $sformat(decoded, "vle8ff.v %s, (%s)%s",        vd, rs1, vm);
    VLE16FF_V:    $sformat(decoded, "vle16ff.v %s, (%s)%s",       vd, rs1, vm);
    VLE32FF_V:    $sformat(decoded, "vle32ff.v %s, (%s)%s",       vd, rs1, vm);
    VLE64FF_V:    $sformat(decoded, "vle64ff.v %s, (%s)%s",       vd, rs1, vm);
    VLSE8_V:      $sformat(decoded, "vlse8.v %s, (%s), %s%s",     vd, rs1, rs2, vm);
    VLSE16_V:     $sformat(decoded, "vlse16.v %s, (%s), %s%s",    vd, rs1, rs2, vm);
    VLSE32_V:     $sformat(decoded, "vlse32.v %s, (%s), %s%s",    vd, rs1, rs2, vm);
    VLSE64_V:     $sformat(decoded, "vlse64.v %s, (%s), %s%s",    vd, rs1, rs2, vm);
    VLUXEI8_V:    $sformat(decoded, "vluxei8.v %s, (%s), %s%s",   vd, rs1, vs2, vm);
    VLUXEI16_V:   $sformat(decoded, "vluxei16.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLUXEI32_V:   $sformat(decoded, "vluxei32.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLUXEI64_V:   $sformat(decoded, "vluxei64.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLOXEI8_V:    $sformat(decoded, "vloxei8.v %s, (%s), %s%s",   vd, rs1, vs2, vm);
    VLOXEI16_V:   $sformat(decoded, "vloxei16.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLOXEI32_V:   $sformat(decoded, "vloxei32.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLOXEI64_V:   $sformat(decoded, "vloxei64.v %s, (%s), %s%s",  vd, rs1, vs2, vm);

    VLSEG2E8_V:      $sformat(decoded, "vlseg2e8.v %s, (%s)%s",         vd, rs1, vm);
    VLSEG2E16_V:     $sformat(decoded, "vlseg2e16.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG2E32_V:     $sformat(decoded, "vlseg2e32.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG2E64_V:     $sformat(decoded, "vlseg2e64.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG3E8_V:      $sformat(decoded, "vlseg3e8.v %s, (%s)%s",         vd, rs1, vm);
    VLSEG3E16_V:     $sformat(decoded, "vlseg3e16.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG3E32_V:     $sformat(decoded, "vlseg3e32.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG3E64_V:     $sformat(decoded, "vlseg3e64.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG4E8_V:      $sformat(decoded, "vlseg4e8.v %s, (%s)%s",         vd, rs1, vm);
    VLSEG4E16_V:     $sformat(decoded, "vlseg4e16.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG4E32_V:     $sformat(decoded, "vlseg4e32.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG4E64_V:     $sformat(decoded, "vlseg4e64.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG5E8_V:      $sformat(decoded, "vlseg5e8.v %s, (%s)%s",         vd, rs1, vm);
    VLSEG5E16_V:     $sformat(decoded, "vlseg5e16.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG5E32_V:     $sformat(decoded, "vlseg5e32.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG5E64_V:     $sformat(decoded, "vlseg5e64.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG6E8_V:      $sformat(decoded, "vlseg6e8.v %s, (%s)%s",         vd, rs1, vm);
    VLSEG6E16_V:     $sformat(decoded, "vlseg6e16.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG6E32_V:     $sformat(decoded, "vlseg6e32.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG6E64_V:     $sformat(decoded, "vlseg6e64.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG7E8_V:      $sformat(decoded, "vlseg7e8.v %s, (%s)%s",         vd, rs1, vm);
    VLSEG7E16_V:     $sformat(decoded, "vlseg7e16.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG7E32_V:     $sformat(decoded, "vlseg7e32.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG7E64_V:     $sformat(decoded, "vlseg7e64.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG8E8_V:      $sformat(decoded, "vlseg8e8.v %s, (%s)%s",         vd, rs1, vm);
    VLSEG8E16_V:     $sformat(decoded, "vlseg8e16.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG8E32_V:     $sformat(decoded, "vlseg8e32.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG8E64_V:     $sformat(decoded, "vlseg8e64.v %s, (%s)%s",        vd, rs1, vm);

    VLSEG2E8FF_V:      $sformat(decoded, "vlseg2e8ff.v %s, (%s)%s",         vd, rs1, vm);
    VLSEG2E16FF_V:     $sformat(decoded, "vlseg2e16ff.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG2E32FF_V:     $sformat(decoded, "vlseg2e32ff.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG2E64FF_V:     $sformat(decoded, "vlseg2e64ff.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG3E8FF_V:      $sformat(decoded, "vlseg3e8ff.v %s, (%s)%s",         vd, rs1, vm);
    VLSEG3E16FF_V:     $sformat(decoded, "vlseg3e16ff.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG3E32FF_V:     $sformat(decoded, "vlseg3e32ff.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG3E64FF_V:     $sformat(decoded, "vlseg3e64ff.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG4E8FF_V:      $sformat(decoded, "vlseg4e8ff.v %s, (%s)%s",         vd, rs1, vm);
    VLSEG4E16FF_V:     $sformat(decoded, "vlseg4e16ff.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG4E32FF_V:     $sformat(decoded, "vlseg4e32ff.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG4E64FF_V:     $sformat(decoded, "vlseg4e64ff.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG5E8FF_V:      $sformat(decoded, "vlseg5e8ff.v %s, (%s)%s",         vd, rs1, vm);
    VLSEG5E16FF_V:     $sformat(decoded, "vlseg5e16ff.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG5E32FF_V:     $sformat(decoded, "vlseg5e32ff.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG5E64FF_V:     $sformat(decoded, "vlseg5e64ff.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG6E8FF_V:      $sformat(decoded, "vlseg6e8ff.v %s, (%s)%s",         vd, rs1, vm);
    VLSEG6E16FF_V:     $sformat(decoded, "vlseg6e16ff.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG6E32FF_V:     $sformat(decoded, "vlseg6e32ff.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG6E64FF_V:     $sformat(decoded, "vlseg6e64ff.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG7E8FF_V:      $sformat(decoded, "vlseg7e8ff.v %s, (%s)%s",         vd, rs1, vm);
    VLSEG7E16FF_V:     $sformat(decoded, "vlseg7e16ff.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG7E32FF_V:     $sformat(decoded, "vlseg7e32ff.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG7E64FF_V:     $sformat(decoded, "vlseg7e64ff.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG8E8FF_V:      $sformat(decoded, "vlseg8e8ff.v %s, (%s)%s",         vd, rs1, vm);
    VLSEG8E16FF_V:     $sformat(decoded, "vlseg8e16ff.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG8E32FF_V:     $sformat(decoded, "vlseg8e32ff.v %s, (%s)%s",        vd, rs1, vm);
    VLSEG8E64FF_V:     $sformat(decoded, "vlseg8e64ff.v %s, (%s)%s",        vd, rs1, vm);

    VLSSEG2E8_V:      $sformat(decoded, "vlsseg2e8.v %s, (%s), %s%s",     vd, rs1, rs2, vm);
    VLSSEG2E16_V:     $sformat(decoded, "vlsseg2e16.v %s, (%s), %s%s",    vd, rs1, rs2, vm);
    VLSSEG2E32_V:     $sformat(decoded, "vlsseg2e32.v %s, (%s), %s%s",    vd, rs1, rs2, vm);
    VLSSEG2E64_V:     $sformat(decoded, "vlsseg2e64.v %s, (%s), %s%s",    vd, rs1, rs2, vm);
    VLSSEG3E8_V:      $sformat(decoded, "vlsseg3e8.v %s, (%s), %s%s",     vd, rs1, rs2, vm);
    VLSSEG3E16_V:     $sformat(decoded, "vlsseg3e16.v %s, (%s), %s%s",    vd, rs1, rs2, vm);
    VLSSEG3E32_V:     $sformat(decoded, "vlsseg3e32.v %s, (%s), %s%s",    vd, rs1, rs2, vm);
    VLSSEG3E64_V:     $sformat(decoded, "vlsseg3e64.v %s, (%s), %s%s",    vd, rs1, rs2, vm);
    VLSSEG4E8_V:      $sformat(decoded, "vlsseg4e8.v %s, (%s), %s%s",     vd, rs1, rs2, vm);
    VLSSEG4E16_V:     $sformat(decoded, "vlsseg4e16.v %s, (%s), %s%s",    vd, rs1, rs2, vm);
    VLSSEG4E32_V:     $sformat(decoded, "vlsseg4e32.v %s, (%s), %s%s",    vd, rs1, rs2, vm);
    VLSSEG4E64_V:     $sformat(decoded, "vlsseg4e64.v %s, (%s), %s%s",    vd, rs1, rs2, vm);
    VLSSEG5E8_V:      $sformat(decoded, "vlsseg5e8.v %s, (%s), %s%s",     vd, rs1, rs2, vm);
    VLSSEG5E16_V:     $sformat(decoded, "vlsseg5e16.v %s, (%s), %s%s",    vd, rs1, rs2, vm);
    VLSSEG5E32_V:     $sformat(decoded, "vlsseg5e32.v %s, (%s), %s%s",    vd, rs1, rs2, vm);
    VLSSEG5E64_V:     $sformat(decoded, "vlsseg5e64.v %s, (%s), %s%s",    vd, rs1, rs2, vm);
    VLSSEG6E8_V:      $sformat(decoded, "vlsseg6e8.v %s, (%s), %s%s",     vd, rs1, rs2, vm);
    VLSSEG6E16_V:     $sformat(decoded, "vlsseg6e16.v %s, (%s), %s%s",    vd, rs1, rs2, vm);
    VLSSEG6E32_V:     $sformat(decoded, "vlsseg6e32.v %s, (%s), %s%s",    vd, rs1, rs2, vm);
    VLSSEG6E64_V:     $sformat(decoded, "vlsseg6e64.v %s, (%s), %s%s",    vd, rs1, rs2, vm);
    VLSSEG7E8_V:      $sformat(decoded, "vlsseg7e8.v %s, (%s), %s%s",     vd, rs1, rs2, vm);
    VLSSEG7E16_V:     $sformat(decoded, "vlsseg7e16.v %s, (%s), %s%s",    vd, rs1, rs2, vm);
    VLSSEG7E32_V:     $sformat(decoded, "vlsseg7e32.v %s, (%s), %s%s",    vd, rs1, rs2, vm);
    VLSSEG7E64_V:     $sformat(decoded, "vlsseg7e64.v %s, (%s), %s%s",    vd, rs1, rs2, vm);
    VLSSEG8E8_V:      $sformat(decoded, "vlsseg8e8.v %s, (%s), %s%s",     vd, rs1, rs2, vm);
    VLSSEG8E16_V:     $sformat(decoded, "vlsseg8e16.v %s, (%s), %s%s",    vd, rs1, rs2, vm);
    VLSSEG8E32_V:     $sformat(decoded, "vlsseg8e32.v %s, (%s), %s%s",    vd, rs1, rs2, vm);
    VLSSEG8E64_V:     $sformat(decoded, "vlsseg8e64.v %s, (%s), %s%s",    vd, rs1, rs2, vm);

    VLUXSEG2EI8_V:    $sformat(decoded, "vluxseg2ei8.v %s, (%s), %s%s",   vd, rs1, vs2, vm);
    VLUXSEG2EI16_V:   $sformat(decoded, "vluxseg2ei16.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLUXSEG2EI32_V:   $sformat(decoded, "vluxseg2ei32.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLUXSEG2EI64_V:   $sformat(decoded, "vluxseg2ei64.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLUXSEG3EI8_V:    $sformat(decoded, "vluxseg3ei8.v %s, (%s), %s%s",   vd, rs1, vs2, vm);
    VLUXSEG3EI16_V:   $sformat(decoded, "vluxseg3ei16.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLUXSEG3EI32_V:   $sformat(decoded, "vluxseg3ei32.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLUXSEG3EI64_V:   $sformat(decoded, "vluxseg3ei64.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLUXSEG4EI8_V:    $sformat(decoded, "vluxseg4ei8.v %s, (%s), %s%s",   vd, rs1, vs2, vm);
    VLUXSEG4EI16_V:   $sformat(decoded, "vluxseg4ei16.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLUXSEG4EI32_V:   $sformat(decoded, "vluxseg4ei32.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLUXSEG4EI64_V:   $sformat(decoded, "vluxseg4ei64.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLUXSEG5EI8_V:    $sformat(decoded, "vluxseg5ei8.v %s, (%s), %s%s",   vd, rs1, vs2, vm);
    VLUXSEG5EI16_V:   $sformat(decoded, "vluxseg5ei16.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLUXSEG5EI32_V:   $sformat(decoded, "vluxseg5ei32.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLUXSEG5EI64_V:   $sformat(decoded, "vluxseg5ei64.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLUXSEG6EI8_V:    $sformat(decoded, "vluxseg6ei8.v %s, (%s), %s%s",   vd, rs1, vs2, vm);
    VLUXSEG6EI16_V:   $sformat(decoded, "vluxseg6ei16.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLUXSEG6EI32_V:   $sformat(decoded, "vluxseg6ei32.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLUXSEG6EI64_V:   $sformat(decoded, "vluxseg6ei64.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLUXSEG7EI8_V:    $sformat(decoded, "vluxseg7ei8.v %s, (%s), %s%s",   vd, rs1, vs2, vm);
    VLUXSEG7EI16_V:   $sformat(decoded, "vluxseg7ei16.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLUXSEG7EI32_V:   $sformat(decoded, "vluxseg7ei32.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLUXSEG7EI64_V:   $sformat(decoded, "vluxseg7ei64.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLUXSEG8EI8_V:    $sformat(decoded, "vluxseg8ei8.v %s, (%s), %s%s",   vd, rs1, vs2, vm);
    VLUXSEG8EI16_V:   $sformat(decoded, "vluxseg8ei16.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLUXSEG8EI32_V:   $sformat(decoded, "vluxseg8ei32.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLUXSEG8EI64_V:   $sformat(decoded, "vluxseg8ei64.v %s, (%s), %s%s",  vd, rs1, vs2, vm);

    VLOXSEG2EI8_V:    $sformat(decoded, "vloxseg2ei8.v %s, (%s), %s%s",   vd, rs1, vs2, vm);
    VLOXSEG2EI16_V:   $sformat(decoded, "vloxseg2ei16.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLOXSEG2EI32_V:   $sformat(decoded, "vloxseg2ei32.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLOXSEG2EI64_V:   $sformat(decoded, "vloxseg2ei64.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLOXSEG3EI8_V:    $sformat(decoded, "vloxseg3ei8.v %s, (%s), %s%s",   vd, rs1, vs2, vm);
    VLOXSEG3EI16_V:   $sformat(decoded, "vloxseg3ei16.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLOXSEG3EI32_V:   $sformat(decoded, "vloxseg3ei32.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLOXSEG3EI64_V:   $sformat(decoded, "vloxseg3ei64.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLOXSEG4EI8_V:    $sformat(decoded, "vloxseg4ei8.v %s, (%s), %s%s",   vd, rs1, vs2, vm);
    VLOXSEG4EI16_V:   $sformat(decoded, "vloxseg4ei16.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLOXSEG4EI32_V:   $sformat(decoded, "vloxseg4ei32.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLOXSEG4EI64_V:   $sformat(decoded, "vloxseg4ei64.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLOXSEG5EI8_V:    $sformat(decoded, "vloxseg5ei8.v %s, (%s), %s%s",   vd, rs1, vs2, vm);
    VLOXSEG5EI16_V:   $sformat(decoded, "vloxseg5ei16.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLOXSEG5EI32_V:   $sformat(decoded, "vloxseg5ei32.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLOXSEG5EI64_V:   $sformat(decoded, "vloxseg5ei64.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLOXSEG6EI8_V:    $sformat(decoded, "vloxseg6ei8.v %s, (%s), %s%s",   vd, rs1, vs2, vm);
    VLOXSEG6EI16_V:   $sformat(decoded, "vloxseg6ei16.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLOXSEG6EI32_V:   $sformat(decoded, "vloxseg6ei32.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLOXSEG6EI64_V:   $sformat(decoded, "vloxseg6ei64.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLOXSEG7EI8_V:    $sformat(decoded, "vloxseg7ei8.v %s, (%s), %s%s",   vd, rs1, vs2, vm);
    VLOXSEG7EI16_V:   $sformat(decoded, "vloxseg7ei16.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLOXSEG7EI32_V:   $sformat(decoded, "vloxseg7ei32.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLOXSEG7EI64_V:   $sformat(decoded, "vloxseg7ei64.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLOXSEG8EI8_V:    $sformat(decoded, "vloxseg8ei8.v %s, (%s), %s%s",   vd, rs1, vs2, vm);
    VLOXSEG8EI16_V:   $sformat(decoded, "vloxseg8ei16.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLOXSEG8EI32_V:   $sformat(decoded, "vloxseg8ei32.v %s, (%s), %s%s",  vd, rs1, vs2, vm);
    VLOXSEG8EI64_V:   $sformat(decoded, "vloxseg8ei64.v %s, (%s), %s%s",  vd, rs1, vs2, vm);

    VL1RE8_V:         $sformat(decoded, "vl1re8.v %s, (%s)",             vd, rs1);
    VL1RE16_V:        $sformat(decoded, "vl1re16.v %s, (%s)",            vd, rs1);
    VL1RE32_V:        $sformat(decoded, "vl1re32.v %s, (%s)",            vd, rs1);
    VL1RE64_V:        $sformat(decoded, "vl1re64.v %s, (%s)",            vd, rs1);
    VL2RE8_V:         $sformat(decoded, "vl2re8.v %s, (%s)",             vd, rs1);
    VL2RE16_V:        $sformat(decoded, "vl2re16.v %s, (%s)",            vd, rs1);
    VL2RE32_V:        $sformat(decoded, "vl2re32.v %s, (%s)",            vd, rs1);
    VL2RE64_V:        $sformat(decoded, "vl2re64.v %s, (%s)",            vd, rs1);
    VL4RE8_V:         $sformat(decoded, "vl4re8.v %s, (%s)",             vd, rs1);
    VL4RE16_V:        $sformat(decoded, "vl4re16.v %s, (%s)",            vd, rs1);
    VL4RE32_V:        $sformat(decoded, "vl4re32.v %s, (%s)",            vd, rs1);
    VL4RE64_V:        $sformat(decoded, "vl4re64.v %s, (%s)",            vd, rs1);
    VL8RE8_V:         $sformat(decoded, "vl8re8.v %s, (%s)",             vd, rs1);
    VL8RE16_V:        $sformat(decoded, "vl8re16.v %s, (%s)",            vd, rs1);
    VL8RE32_V:        $sformat(decoded, "vl8re32.v %s, (%s)",            vd, rs1);
    VL8RE64_V:        $sformat(decoded, "vl8re64.v %s, (%s)",            vd, rs1);

    VLM_V:            $sformat(decoded, "vlm.v %s, (%s)",                vd, rs1);

    VSSEG2E8_V:      $sformat(decoded, "vsseg2e8.v %s, (%s)%s",         vs3, rs1, vm);
    VSSEG2E16_V:     $sformat(decoded, "vsseg2e16.v %s, (%s)%s",        vs3, rs1, vm);
    VSSEG2E32_V:     $sformat(decoded, "vsseg2e32.v %s, (%s)%s",        vs3, rs1, vm);
    VSSEG2E64_V:     $sformat(decoded, "vsseg2e64.v %s, (%s)%s",        vs3, rs1, vm);
    VSSEG3E8_V:      $sformat(decoded, "vsseg3e8.v %s, (%s)%s",         vs3, rs1, vm);
    VSSEG3E16_V:     $sformat(decoded, "vsseg3e16.v %s, (%s)%s",        vs3, rs1, vm);
    VSSEG3E32_V:     $sformat(decoded, "vsseg3e32.v %s, (%s)%s",        vs3, rs1, vm);
    VSSEG3E64_V:     $sformat(decoded, "vsseg3e64.v %s, (%s)%s",        vs3, rs1, vm);
    VSSEG4E8_V:      $sformat(decoded, "vsseg4e8.v %s, (%s)%s",         vs3, rs1, vm);
    VSSEG4E16_V:     $sformat(decoded, "vsseg4e16.v %s, (%s)%s",        vs3, rs1, vm);
    VSSEG4E32_V:     $sformat(decoded, "vsseg4e32.v %s, (%s)%s",        vs3, rs1, vm);
    VSSEG4E64_V:     $sformat(decoded, "vsseg4e64.v %s, (%s)%s",        vs3, rs1, vm);
    VSSEG5E8_V:      $sformat(decoded, "vsseg5e8.v %s, (%s)%s",         vs3, rs1, vm);
    VSSEG5E16_V:     $sformat(decoded, "vsseg5e16.v %s, (%s)%s",        vs3, rs1, vm);
    VSSEG5E32_V:     $sformat(decoded, "vsseg5e32.v %s, (%s)%s",        vs3, rs1, vm);
    VSSEG5E64_V:     $sformat(decoded, "vsseg5e64.v %s, (%s)%s",        vs3, rs1, vm);
    VSSEG6E8_V:      $sformat(decoded, "vsseg6e8.v %s, (%s)%s",         vs3, rs1, vm);
    VSSEG6E16_V:     $sformat(decoded, "vsseg6e16.v %s, (%s)%s",        vs3, rs1, vm);
    VSSEG6E32_V:     $sformat(decoded, "vsseg6e32.v %s, (%s)%s",        vs3, rs1, vm);
    VSSEG6E64_V:     $sformat(decoded, "vsseg6e64.v %s, (%s)%s",        vs3, rs1, vm);
    VSSEG7E8_V:      $sformat(decoded, "vsseg7e8.v %s, (%s)%s",         vs3, rs1, vm);
    VSSEG7E16_V:     $sformat(decoded, "vsseg7e16.v %s, (%s)%s",        vs3, rs1, vm);
    VSSEG7E32_V:     $sformat(decoded, "vsseg7e32.v %s, (%s)%s",        vs3, rs1, vm);
    VSSEG7E64_V:     $sformat(decoded, "vsseg7e64.v %s, (%s)%s",        vs3, rs1, vm);
    VSSEG8E8_V:      $sformat(decoded, "vsseg8e8.v %s, (%s)%s",         vs3, rs1, vm);
    VSSEG8E16_V:     $sformat(decoded, "vsseg8e16.v %s, (%s)%s",        vs3, rs1, vm);
    VSSEG8E32_V:     $sformat(decoded, "vsseg8e32.v %s, (%s)%s",        vs3, rs1, vm);
    VSSEG8E64_V:     $sformat(decoded, "vsseg8e64.v %s, (%s)%s",        vs3, rs1, vm);

    VSSSEG2E8_V:      $sformat(decoded, "vssseg2e8.v %s, (%s), %s%s",     vs3, rs1, rs2, vm);
    VSSSEG2E16_V:     $sformat(decoded, "vssseg2e16.v %s, (%s), %s%s",    vs3, rs1, rs2, vm);
    VSSSEG2E32_V:     $sformat(decoded, "vssseg2e32.v %s, (%s), %s%s",    vs3, rs1, rs2, vm);
    VSSSEG2E64_V:     $sformat(decoded, "vssseg2e64.v %s, (%s), %s%s",    vs3, rs1, rs2, vm);
    VSSSEG3E8_V:      $sformat(decoded, "vssseg3e8.v %s, (%s), %s%s",     vs3, rs1, rs2, vm);
    VSSSEG3E16_V:     $sformat(decoded, "vssseg3e16.v %s, (%s), %s%s",    vs3, rs1, rs2, vm);
    VSSSEG3E32_V:     $sformat(decoded, "vssseg3e32.v %s, (%s), %s%s",    vs3, rs1, rs2, vm);
    VSSSEG3E64_V:     $sformat(decoded, "vssseg3e64.v %s, (%s), %s%s",    vs3, rs1, rs2, vm);
    VSSSEG4E8_V:      $sformat(decoded, "vssseg4e8.v %s, (%s), %s%s",     vs3, rs1, rs2, vm);
    VSSSEG4E16_V:     $sformat(decoded, "vssseg4e16.v %s, (%s), %s%s",    vs3, rs1, rs2, vm);
    VSSSEG4E32_V:     $sformat(decoded, "vssseg4e32.v %s, (%s), %s%s",    vs3, rs1, rs2, vm);
    VSSSEG4E64_V:     $sformat(decoded, "vssseg4e64.v %s, (%s), %s%s",    vs3, rs1, rs2, vm);
    VSSSEG5E8_V:      $sformat(decoded, "vssseg5e8.v %s, (%s), %s%s",     vs3, rs1, rs2, vm);
    VSSSEG5E16_V:     $sformat(decoded, "vssseg5e16.v %s, (%s), %s%s",    vs3, rs1, rs2, vm);
    VSSSEG5E32_V:     $sformat(decoded, "vssseg5e32.v %s, (%s), %s%s",    vs3, rs1, rs2, vm);
    VSSSEG5E64_V:     $sformat(decoded, "vssseg5e64.v %s, (%s), %s%s",    vs3, rs1, rs2, vm);
    VSSSEG6E8_V:      $sformat(decoded, "vssseg6e8.v %s, (%s), %s%s",     vs3, rs1, rs2, vm);
    VSSSEG6E16_V:     $sformat(decoded, "vssseg6e16.v %s, (%s), %s%s",    vs3, rs1, rs2, vm);
    VSSSEG6E32_V:     $sformat(decoded, "vssseg6e32.v %s, (%s), %s%s",    vs3, rs1, rs2, vm);
    VSSSEG6E64_V:     $sformat(decoded, "vssseg6e64.v %s, (%s), %s%s",    vs3, rs1, rs2, vm);
    VSSSEG7E8_V:      $sformat(decoded, "vssseg7e8.v %s, (%s), %s%s",     vs3, rs1, rs2, vm);
    VSSSEG7E16_V:     $sformat(decoded, "vssseg7e16.v %s, (%s), %s%s",    vs3, rs1, rs2, vm);
    VSSSEG7E32_V:     $sformat(decoded, "vssseg7e32.v %s, (%s), %s%s",    vs3, rs1, rs2, vm);
    VSSSEG7E64_V:     $sformat(decoded, "vssseg7e64.v %s, (%s), %s%s",    vs3, rs1, rs2, vm);
    VSSSEG8E8_V:      $sformat(decoded, "vssseg8e8.v %s, (%s), %s%s",     vs3, rs1, rs2, vm);
    VSSSEG8E16_V:     $sformat(decoded, "vssseg8e16.v %s, (%s), %s%s",    vs3, rs1, rs2, vm);
    VSSSEG8E32_V:     $sformat(decoded, "vssseg8e32.v %s, (%s), %s%s",    vs3, rs1, rs2, vm);
    VSSSEG8E64_V:     $sformat(decoded, "vssseg8e64.v %s, (%s), %s%s",    vs3, rs1, rs2, vm);

    VSUXSEG2EI8_V:    $sformat(decoded, "vsuxseg2ei8.v %s, (%s), %s%s",   vs3, rs1, vs2, vm);
    VSUXSEG2EI16_V:   $sformat(decoded, "vsuxseg2ei16.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSUXSEG2EI32_V:   $sformat(decoded, "vsuxseg2ei32.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSUXSEG2EI64_V:   $sformat(decoded, "vsuxseg2ei64.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSUXSEG3EI8_V:    $sformat(decoded, "vsuxseg3ei8.v %s, (%s), %s%s",   vs3, rs1, vs2, vm);
    VSUXSEG3EI16_V:   $sformat(decoded, "vsuxseg3ei16.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSUXSEG3EI32_V:   $sformat(decoded, "vsuxseg3ei32.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSUXSEG3EI64_V:   $sformat(decoded, "vsuxseg3ei64.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSUXSEG4EI8_V:    $sformat(decoded, "vsuxseg4ei8.v %s, (%s), %s%s",   vs3, rs1, vs2, vm);
    VSUXSEG4EI16_V:   $sformat(decoded, "vsuxseg4ei16.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSUXSEG4EI32_V:   $sformat(decoded, "vsuxseg4ei32.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSUXSEG4EI64_V:   $sformat(decoded, "vsuxseg4ei64.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSUXSEG5EI8_V:    $sformat(decoded, "vsuxseg5ei8.v %s, (%s), %s%s",   vs3, rs1, vs2, vm);
    VSUXSEG5EI16_V:   $sformat(decoded, "vsuxseg5ei16.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSUXSEG5EI32_V:   $sformat(decoded, "vsuxseg5ei32.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSUXSEG5EI64_V:   $sformat(decoded, "vsuxseg5ei64.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSUXSEG6EI8_V:    $sformat(decoded, "vsuxseg6ei8.v %s, (%s), %s%s",   vs3, rs1, vs2, vm);
    VSUXSEG6EI16_V:   $sformat(decoded, "vsuxseg6ei16.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSUXSEG6EI32_V:   $sformat(decoded, "vsuxseg6ei32.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSUXSEG6EI64_V:   $sformat(decoded, "vsuxseg6ei64.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSUXSEG7EI8_V:    $sformat(decoded, "vsuxseg7ei8.v %s, (%s), %s%s",   vs3, rs1, vs2, vm);
    VSUXSEG7EI16_V:   $sformat(decoded, "vsuxseg7ei16.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSUXSEG7EI32_V:   $sformat(decoded, "vsuxseg7ei32.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSUXSEG7EI64_V:   $sformat(decoded, "vsuxseg7ei64.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSUXSEG8EI8_V:    $sformat(decoded, "vsuxseg8ei8.v %s, (%s), %s%s",   vs3, rs1, vs2, vm);
    VSUXSEG8EI16_V:   $sformat(decoded, "vsuxseg8ei16.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSUXSEG8EI32_V:   $sformat(decoded, "vsuxseg8ei32.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSUXSEG8EI64_V:   $sformat(decoded, "vsuxseg8ei64.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);

    VSOXSEG2EI8_V:    $sformat(decoded, "vsoxseg2ei8.v %s, (%s), %s%s",   vs3, rs1, vs2, vm);
    VSOXSEG2EI16_V:   $sformat(decoded, "vsoxseg2ei16.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSOXSEG2EI32_V:   $sformat(decoded, "vsoxseg2ei32.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSOXSEG2EI64_V:   $sformat(decoded, "vsoxseg2ei64.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSOXSEG3EI8_V:    $sformat(decoded, "vsoxseg3ei8.v %s, (%s), %s%s",   vs3, rs1, vs2, vm);
    VSOXSEG3EI16_V:   $sformat(decoded, "vsoxseg3ei16.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSOXSEG3EI32_V:   $sformat(decoded, "vsoxseg3ei32.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSOXSEG3EI64_V:   $sformat(decoded, "vsoxseg3ei64.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSOXSEG4EI8_V:    $sformat(decoded, "vsoxseg4ei8.v %s, (%s), %s%s",   vs3, rs1, vs2, vm);
    VSOXSEG4EI16_V:   $sformat(decoded, "vsoxseg4ei16.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSOXSEG4EI32_V:   $sformat(decoded, "vsoxseg4ei32.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSOXSEG4EI64_V:   $sformat(decoded, "vsoxseg4ei64.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSOXSEG5EI8_V:    $sformat(decoded, "vsoxseg5ei8.v %s, (%s), %s%s",   vs3, rs1, vs2, vm);
    VSOXSEG5EI16_V:   $sformat(decoded, "vsoxseg5ei16.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSOXSEG5EI32_V:   $sformat(decoded, "vsoxseg5ei32.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSOXSEG5EI64_V:   $sformat(decoded, "vsoxseg5ei64.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSOXSEG6EI8_V:    $sformat(decoded, "vsoxseg6ei8.v %s, (%s), %s%s",   vs3, rs1, vs2, vm);
    VSOXSEG6EI16_V:   $sformat(decoded, "vsoxseg6ei16.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSOXSEG6EI32_V:   $sformat(decoded, "vsoxseg6ei32.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSOXSEG6EI64_V:   $sformat(decoded, "vsoxseg6ei64.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSOXSEG7EI8_V:    $sformat(decoded, "vsoxseg7ei8.v %s, (%s), %s%s",   vs3, rs1, vs2, vm);
    VSOXSEG7EI16_V:   $sformat(decoded, "vsoxseg7ei16.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSOXSEG7EI32_V:   $sformat(decoded, "vsoxseg7ei32.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSOXSEG7EI64_V:   $sformat(decoded, "vsoxseg7ei64.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSOXSEG8EI8_V:    $sformat(decoded, "vsoxseg8ei8.v %s, (%s), %s%s",   vs3, rs1, vs2, vm);
    VSOXSEG8EI16_V:   $sformat(decoded, "vsoxseg8ei16.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSOXSEG8EI32_V:   $sformat(decoded, "vsoxseg8ei32.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSOXSEG8EI64_V:   $sformat(decoded, "vsoxseg8ei64.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);

    VSE8_V:      $sformat(decoded, "vse8.v %s, (%s)%s",          vs3, rs1, vm);
    VSE16_V:     $sformat(decoded, "vse16.v %s, (%s)%s",         vs3, rs1, vm);
    VSE32_V:     $sformat(decoded, "vse32.v %s, (%s)%s",         vs3, rs1, vm);
    VSE64_V:     $sformat(decoded, "vse64.v %s, (%s)%s",         vs3, rs1, vm);
    VSSE8_V:     $sformat(decoded, "vsse8.v %s, (%s), %s%s",     vs3, rs1, rs2, vm);
    VSSE16_V:    $sformat(decoded, "vsse16.v %s, (%s), %s%s",    vs3, rs1, rs2, vm);
    VSSE32_V:    $sformat(decoded, "vsse32.v %s, (%s), %s%s",    vs3, rs1, rs2, vm);
    VSSE64_V:    $sformat(decoded, "vsse64.v %s, (%s), %s%s",    vs3, rs1, rs2, vm);
    VSUXEI8_V:   $sformat(decoded, "vsuxei8.v %s, (%s), %s%s",    vs3, rs1, vs2, vm);
    VSUXEI16_V:  $sformat(decoded, "vsuxei16.v %s, (%s), %s%s",   vs3, rs1, vs2, vm);
    VSUXEI32_V:  $sformat(decoded, "vsuxei32.v %s, (%s), %s%s",   vs3, rs1, vs2, vm);
    VSUXEI64_V:  $sformat(decoded, "vsuxei64.v %s, (%s), %s%s",   vs3, rs1, vs2, vm);
    VSOXEI8_V:   $sformat(decoded, "vsoxei8.v %s, (%s), %s%s",   vs3, rs1, vs2, vm);
    VSOXEI16_V:  $sformat(decoded, "vsoxei16.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSOXEI32_V:  $sformat(decoded, "vsoxei32.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);
    VSOXEI64_V:  $sformat(decoded, "vsoxei64.v %s, (%s), %s%s",  vs3, rs1, vs2, vm);

    VS1R_V:           $sformat(decoded, "vs1r.v %s, (%s)",                vs3, rs1);
    VS2R_V:           $sformat(decoded, "vs2r.v %s, (%s)",                vs3, rs1);
    VS4R_V:           $sformat(decoded, "vs4r.v %s, (%s)",                vs3, rs1);
    VS8R_V:           $sformat(decoded, "vs8r.v %s, (%s)",                vs3, rs1);

    VSM_V:            $sformat(decoded, "vsm.v %s, (%s)",                 vs3, rs1);

    VSETVLI:          $sformat(decoded, "vsetvli %s, %s, %s, %s, %s, %s", rd, rs1, eSEW, mLMUL, ta, ma);
    VSETIVLI:         $sformat(decoded, "vsetivli %s, %s, %s, %s, %s, %s", rd, uimm5, eSEW, mLMUL, ta, ma);
    VSETVL:           $sformat(decoded, "vsetvl %s, %s, %s",              rd, rs1, rs2);

    VANDN_VV:    $sformat(decoded, "vandn.vv %s, %s, %s%s", vd, vs2, vs1, vm);
    VANDN_VX:    $sformat(decoded, "vandn.vx %s, %s, %s%s", vd, vs2, rs1, vm);
    VBREV_V:     $sformat(decoded, "vbrev.v %s, %s%s", vd, vs2, vm);
    VBREV8_V:    $sformat(decoded, "vbrev8.v %s, %s%s", vd, vs2, vm);
    VREV8_V:     $sformat(decoded, "vrev8.v %s, %s%s", vd, vs2, vm);
    VCLZ_V:      $sformat(decoded, "vclz.v %s, %s%s", vd, vs2, vm);
    VCTZ_V:      $sformat(decoded, "vctz.v %s, %s%s", vd, vs2, vm);
    VCPOP_V:     $sformat(decoded, "vcpop.v %s, %s%s", vd, vs2, vm);
    VROL_VV:     $sformat(decoded, "vrol.vv %s, %s, %s%s", vd, vs2, vs1, vm);
    VROL_VX:     $sformat(decoded, "vrol.vx %s, %s, %s%s", vd, vs2, rs1, vm);
    VROR_VV:     $sformat(decoded, "vror.vv %s, %s, %s%s", vd, vs2, vs1, vm);
    VROR_VX:     $sformat(decoded, "vror.vx %s, %s, %s%s", vd, vs2, rs1, vm);
    VROR_VI:     $sformat(decoded, "vror.vi %s, %s, %0d%s", vd, vs2, uimm5, vm);
    VWSLL_VV:    $sformat(decoded, "vwsll.vv %s, %s, %s%s", vd, vs2, vs1, vm);
    VWSLL_VX:    $sformat(decoded, "vwsll.vx %s, %s, %s%s", vd, vs2, rs1, vm);
    VWSLL_VI:    $sformat(decoded, "vwsll.vi %s, %s, %0d%s", vd, vs2, uimm5, vm);

    VCLMUL_VV:   $sformat(decoded, "vclmul.vv %s, %s, %s%s", vd, vs2, vs1, vm);
    VCLMUL_VX:   $sformat(decoded, "vclmul.vx %s, %s, %s%s", vd, vs2, rs1, vm);
    VCLMULH_VV:  $sformat(decoded, "vclmulh.vv %s, %s, %s%s", vd, vs2, vs1, vm);
    VCLMULH_VX:  $sformat(decoded, "vclmulh.vx %s, %s, %s%s", vd, vs2, rs1, vm);

    VGHSH_VV:    $sformat(decoded, "vghsh.vv %s, %s, %s", vd, vs2, vs1);
    VGMUL_VV:    $sformat(decoded, "vgmul.vv %s, %s", vd, vs2);

    VAESDM_VV:   $sformat(decoded, "vaesdm.vv %s, %s", vd, vs2);
    VAESDM_VS:   $sformat(decoded, "vaesdm.vs %s, %s", vd, vs2);
    VAESDF_VV:   $sformat(decoded, "vaesdf.vv %s, %s", vd, vs2);
    VAESDF_VS:   $sformat(decoded, "vaesdf.vs %s, %s", vd, vs2);
    VAESEM_VV:   $sformat(decoded, "vaesem.vv %s, %s", vd, vs2);
    VAESEM_VS:   $sformat(decoded, "vaesem.vs %s, %s", vd, vs2);
    VAESEF_VV:   $sformat(decoded, "vaesef.vv %s, %s", vd, vs2);
    VAESEF_VS:   $sformat(decoded, "vaesef.vs %s, %s", vd, vs2);

    VAESZ_VS:     $sformat(decoded, "vaesz.vs %s, %s",                vd, vs2);
    VAESKF1_VI:   $sformat(decoded, "vaeskf1.vi %s, %0d",              vd, uimm5);
    VAESKF2_VI:   $sformat(decoded, "vaeskf2.vi %s, %0d",              vd, uimm5);

    VSHA2MS_VV:   $sformat(decoded, "vsha2ms.vv %s, %s, %s",              vd, vs2, vs1);
    VSHA2CH_VV:   $sformat(decoded, "vsha2ch.vv %s, %s, %s",              vd, vs2, vs1);
    VSHA2CL_VV:   $sformat(decoded, "vsha2cl.vv %s, %s, %s",              vd, vs2, vs1);

    default: decoded = "illegal";
  endcase



  // Return possibly truncated instruction and decoded assembly
  if (compressedInstruction)
    return $sformatf("%04h %s", instr[15:0], decoded);
  else
    return $sformatf("%08h %s", instr[31:0], decoded);

endfunction
