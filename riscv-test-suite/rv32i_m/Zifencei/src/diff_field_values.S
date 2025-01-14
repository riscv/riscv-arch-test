// This test will check the behavior of fence.i by setting other field 
// values of the fence instruction apart from the opcode
 
// Developed by: Maria Rehman

#include "model_test.h"
#include "arch_test.h"

# Test Virtual Machine (TVM) used by program.
RVTEST_ISA("RV32I_Zifencei")

# Test code region
.section .text.init
.globl rvtest_entry_point
rvtest_entry_point:
RVMODEL_BOOT
RVTEST_CODE_BEGIN
RVMODEL_IO_ASSERT_GPR_EQ(x31, x0, 0x00000000)
RVMODEL_IO_WRITE_STR(x31, "# Test Begin\n")

#ifdef TEST_CASE_1
  RVTEST_CASE(1,"// check ISA:=regex(.*32.*); check ISA:=regex(.*I.*); check ISA:=regex(.*Zifencei.*); def TEST_CASE_1=True", fencei)

    # ---------------------------------------------------------------------------------------------
    RVMODEL_IO_WRITE_STR(x31, "# Test part A - test fence\n");

    # Addresses for test data and results
    LA(     x16,test_A_data)
    LA(     x17,test_A_res)

    # Register initialization
    LI(     x3,0)

    # Load test data
    lw      x1, 0(x16)
    lw      x2, 4(x16)
    fence.i  # Synchronize after loading data
   // .word 0x0000100f   this is equal to the fence.i
                                       // For this fence.i instruction field value test used,
                                       // immediate field value == "0000_0000_0000" 
				       // rs1 reg ==  (00000)
				       // rd reg ==  (0)
				       // func3  == 001
				       // Opcode == 0001111
				       // Instruction binary == 0000_0000_0000_0000_0001_0000_0000_1111

    # Test
    LA(     x20,instr_A_src)
    LA(     x21,instr_A_dst)
    lw      x15, 0(x20)
    // fence.i  # Synchronize after loading instruction data
                                       // For this fence.i instruction field value test used,
                                       // immediate field value == "0000_0000_1111" 
				       // rs1 reg ==  x15 (01111)
				       // rd reg == x18 (10010)
				       // func3  == 001
				       // Opcode == 0001111
				       // Instruction binary == 0000_0000_1111_0111_1001_1001_0000_1111
    .word 0x00f7990f
    
    sw      x15, 0(x21)
    // fence.i  # Synchronize after storing data
    				       // For this fence.i instruction field value test used,
                                       // immediate field value == "1111_1111_1111" 
				       // rs1 reg ==  x5 (00101)
				       // rd reg == x19 (10011)
				       // func3  == 001
				       // Opcode == 0001111
				       // Instruction binary == 1111_1111_1111_0010_1001_1001_0000_1111
    .word 0xfff2990f
    
instr_A_dst:
    lui     x2, 0
    // fence.i  # Synchronize after modifying x2
    				       // For this fence.i instruction field value test used,
                                       // immediate field value == "0000_0000_1111" 
				       // rs1 reg ==  x5 (00101)
				       // rd reg == x0 (0)
				       // func3  == 001
				       // Opcode == 0001111
				       // Instruction binary == 0000_0000_1111_0010_1001_0000_0000_1111
    .word 0x00f2900f

    # Store results
    sw      x1, 0(x17)
    sw      x2, 4(x17)
    sw      x3, 8(x17)
    sw      x15, 12(x17)
    // fence.i  # Synchronize after storing results
        			       // For this fence.i instruction field value test used,
                                       // immediate field value == "0000_0000_0000" 
				       // rs1 reg ==  x0 (00000)
				       // rd reg == x20 (10100)
				       // func3  == 001
				       // Opcode == 0001111
				       // Instruction binary == 0000_0000_0000_0000_0001_1010_0000_1111
    .word 0x00001a0f
    

    //
    // Assert
    //
    RVMODEL_IO_ASSERT_GPR_EQ(x17, x2,  0x00000012)
    RVMODEL_IO_ASSERT_GPR_EQ(x17, x3,  0x00000042)
    RVMODEL_IO_ASSERT_GPR_EQ(x17, x15, 0x001101B3)

    RVMODEL_IO_WRITE_STR(x31, "# Test part A1  - Complete\n");

    RVMODEL_IO_WRITE_STR(x31, "# Test End\n")

#endif

 # ---------------------------------------------------------------------------------------------
    # HALT
    RVMODEL_HALT

RVTEST_CODE_END

RVTEST_DATA_BEGIN
# Input data section.
    .data
    .align 4

instr_A_src:
    add     x3, x2, x1

test_A_data:
    .word 0x30
    .word 0x12
RVTEST_DATA_END


# Output data section.
RVMODEL_DATA_BEGIN
rvtest_sig_begin:
sig_begin_canary:
CANARY;
test_A_res:
    .fill 4, 4, 0xdeadbeef

#ifdef rvtest_mtrap_routine
mtrap_sigptr:
  .fill 4, 4, 0xdeadbeef
#endif

#ifdef rvtest_gpr_save
gpr_save:
    .fill 32*(XLEN/32), 4, 0xdeadbeef
#endif

sig_end_canary:
CANARY;
rvtest_sig_end:
RVMODEL_DATA_END

