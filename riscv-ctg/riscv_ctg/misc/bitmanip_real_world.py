import random
import os

#---------------------------------------------------Start String--------------------------------------------------

start_str = '''
#include "model_test.h"
#include "arch_test.h"
RVTEST_ISA("RV$xlenIK")

.section .text.init
.globl rvtest_entry_point
rvtest_entry_point:
RVMODEL_BOOT
RVTEST_CODE_BEGIN

#ifdef TEST_CASE_1

RVTEST_CASE(0,"//check ISA:=regex(.*$xlen.*);check ISA:=regex(.*RV$xlen.*I.*K.*);def TEST_CASE_1=True;",$inst)

RVTEST_CASE(1,"//check ISA:=regex(.*$xlen.*);check ISA:=regex(.*RV$xlen.*I.*$config.*);def TEST_CASE_1=True;",$inst)

RVTEST_SIGBASE( $swreg1,signature_$swreg1_1)'''

#---------------------------------------------Assembly String: aes64*----------------------------------------------

string1 = '''// $comment
// opcode: $inst; op1:$rs1; op2:$rs2; dest1:$rd1; dest2:$rd2; dest3:$rd3; op1val:$r1_val; op2val:$r2_val
li $rs1, $r1_val;
li $rs2, $r2_val;
xor $rs1, $rs1, $rs2;
$inst $rd1, $rs1, $rs2;
$inst $rd2, $rs2, $rs1;
xor $rd3, $rd2, $rs2;
RVTEST_SIGUPD($swreg1,$rd1,$offset1);
RVTEST_SIGUPD($swreg1,$rd2,$offset2);
RVTEST_SIGUPD($swreg1,$rd3,$offset3);'''

#---------------------------------Assembly String: SHA2, SM3 & aes64im - Pattern 1---------------------------------

string2 = '''// $comment
// opcode: $inst2; op1:$rs3; dest1:$rs1; op1val:$r1_val; op2val:$r2_val
li $rs1, $r1_val;
li $rs2, $r2_val;
$inst1 $rs3, $rs1, $rs2;
$inst2 $rs1, $rs3;
$inst1 $rs4, $rs1, $rs2;
RVTEST_SIGUPD($swreg1,$rs3,$offset1);
RVTEST_SIGUPD($swreg1,$rs1,$offset2);
RVTEST_SIGUPD($swreg1,$rs4,$offset3);'''

string2_not = '''// $comment
// opcode: $inst2; op1:$rs3; dest1:$rs1; op1val:$r1_val; op2val:$r2_val
li $rs1, $r1_val;
li $rs2, $r2_val;
$inst1 $rs3, $rs2;
$inst2 $rs1, $rs3;
$inst1 $rs4, $rs1;
RVTEST_SIGUPD($swreg1,$rs3,$offset1);
RVTEST_SIGUPD($swreg1,$rs1,$offset2);
RVTEST_SIGUPD($swreg1,$rs4,$offset3);'''

#---------------------------------Assembly String: SHA2, SM3 & aes64im - Pattern 2---------------------------------

string3 = '''// $comment
// opcode: $inst; op1:$rs1; dest1:$rs2;
LREG $rs1, $offset1($rs0);
$inst $rs2, $rs1;
RVTEST_SIGUPD($swreg1,$rs1,$offset2);
RVTEST_SIGUPD($swreg1,$rs2,$offset3);'''

#---------------------------------------Assembly String: SHA2-512 - Pattern 1--------------------------------------

string5 = '''// $comment
// opcode: $inst2; op1:$rs3; op2:$rs2; dest1:$rs1; op1val:$r1_val; op2val:$r2_val
li $rs1, $r1_val;
li $rs2, $r2_val;
$inst1 $rs3, $rs1, $rs2;
$inst2 $rs1, $rs3, $rs2;
$inst1 $rs4, $rs1, $rs2;
RVTEST_SIGUPD($swreg1,$rs3,$offset1);
RVTEST_SIGUPD($swreg1,$rs1,$offset2);
RVTEST_SIGUPD($swreg1,$rs4,$offset3);'''

string5_not = '''// $comment
// opcode: $inst2; op1:$rs3; op2:$rs2; dest1:$rs1; op1val:$r1_val; op2val:$r2_val
li $rs1, $r1_val;
li $rs2, $r2_val;
$inst1 $rs3, $rs2;
$inst2 $rs1, $rs3, $rs2;
$inst1 $rs4, $rs1;
RVTEST_SIGUPD($swreg1,$rs3,$offset1);
RVTEST_SIGUPD($swreg1,$rs1,$offset2);
RVTEST_SIGUPD($swreg1,$rs4,$offset3);'''

#---------------------------------------Assembly String: SHA2-512 - Pattern 2--------------------------------------

string6 = '''// $comment
// opcode: $inst; op1:$rs1; op2:$rs2; dest1:$rs3;
LREG $rs1, $offset1($rs0);
LREG $rs2, $offset2($rs0);
$inst $rs3, $rs1, $rs2;
RVTEST_SIGUPD($swreg1,$rs1,$offset3);
RVTEST_SIGUPD($swreg1,$rs3,$offset4);'''

#----------------------------------------------Assembly String: aes32*---------------------------------------------

string4 = '''// $comment
// opcode: $inst; op1:$rs1; op1:$rs2; op1:$rs3; op1:$rs4; dest:$rs5;
li  $rs1, $r1_val;
li  $rs2, $r2_val;
li  $rs3, $r3_val;
li  $rs4, $r4_val;
li  $rs5, $r5_val;
$inst $rs5, $rs1, 0;
$inst $rs5, $rs2, 1;
$inst $rs5, $rs3, 2;
$inst $rs5, $rs4, 3;
RVTEST_SIGUPD($swreg1,$rs5,$offset1);'''

#----------------------------------------------Assembly String: sm4ed, sm4ks ---------------------------------------------

string7 = '''// $comment
// opcode: $inst; $op1: $rs6; op2:$rs1; op2:$rs2; op2:$rs3; op2:$rs4; dest:$rs5;
li  $rs1, $r1_val;
li  $rs2, $r2_val;
li  $rs3, $r3_val;
li  $rs4, $r4_val;
li  $rs5, $r5_val;
li  $rs6, $r6_val;
$inst $rs5, $rs6, $rs1, 0;
$inst $rs5, $rs6, $rs2, 1;
$inst $rs5, $rs6, $rs3, 2;
$inst $rs5, $rs6, $rs4, 3;
RVTEST_SIGUPD($swreg1,$rs5,$offset1);'''

#----------------------------------------------------End String----------------------------------------------------

end_str = '''#endif

RVTEST_CODE_END
RVMODEL_HALT

RVTEST_DATA_BEGIN
.align 4
rvtest_data:
.word 0xbabecafe
RVTEST_DATA_END

RVMODEL_DATA_BEGIN


signature_$swreg1_1:
    .fill $fill_val*(XLEN/32),4,0xdeadbeef
    
#ifdef rvtest_mtrap_routine

mtrap_sigptr:
    .fill 64*(XLEN/32),4,0xdeadbeef

#endif

#ifdef rvtest_gpr_save

gpr_save:
    .fill 32*(XLEN/32),4,0xdeadbeef

#endif

RVMODEL_DATA_END'''

#-------------------------------------------------End String 1 & 2------------------------------------------------

end_str1 = '''#endif

RVTEST_CODE_END
RVMODEL_HALT

RVTEST_DATA_BEGIN
.align 4
rvtest_data:'''

end_str2 = '''RVTEST_DATA_END

RVMODEL_DATA_BEGIN


signature_$swreg1_1:
    .fill $fill_val*(XLEN/32),4,0xdeadbeef
    
#ifdef rvtest_mtrap_routine

mtrap_sigptr:
    .fill 64*(XLEN/32),4,0xdeadbeef

#endif

#ifdef rvtest_gpr_save

gpr_save:
    .fill 32*(XLEN/32),4,0xdeadbeef

#endif

RVMODEL_DATA_END'''

#----------------------------------------------------User Inputs---------------------------------------------------

instr_dict = {
	1: ["aes64ds","aes64dsm","aes64es","aes64esm","sm4ed","sm4ks"],
	2: ["sha256sig0","sha256sig1","sha256sum0","sha256sum1","sha512sig0",\
	    "sha512sig1","sha512sum0","sha512sum1","sm3p0","sm3p1","aes64im"],
	3: ["aes32dsi","aes32dsmi","aes32esi","aes32esmi"],
	4: ["sha256sig0","sha256sig1","sha256sum0","sha256sum1","sm3p0","sm3p1"],
	5: ["sha512sig0h","sha512sig0l","sha512sig1h","sha512sig1l","sha512sum0r","sha512sum1r"],
	6: ["sm4ed","sm4ks"],
	7: ["sm4ed","sm4ks"]}

instr_f = {
	1: ["xor"],
	2: ["xor","not","add"],
	3: ["none"],
	4: ["xor","not","add"],
	5: ["xor","not","add"], 
	6: ["none"],
	7: ["none"]
        }

xlen = {
	1: 64,
	2: 64,
	3: 32,
	4: 32,
	5: 32,
    6: 64,
    7: 32}

comment_dict = {
	1: ["1st Instruction => rs1 = $rs1; rs2 = $rs2 | 2nd Instruction => rs1 = $rs2; rs2 = $rs1\
 | Result of xor goes into $inst & vice versa"],
 	2: ["Forwarded $inst1 into $inst2 & the result back into $inst1","Checking load-to-use hazard!"],
 	3: ["Expected use-case sequence -> Aims to test things like pipeline forwarding"],
 	4: ["Forwarded $inst1 into $inst2 & the result back into $inst1","Checking load-to-use hazard!"],
 	5: ["Forwarded $inst1 into $inst2 & the result back into $inst1","Checking load-to-use hazard!"],
 	6: ["Expected use-case sequence -> Aims to test things like pipeline forwarding"],
	7: ["Expected use-case sequence -> Aims to test things like pipeline forwarding"]}

n_i = {
	1: [27,3],
	2: [28,30,3],
	3: [27,1],
	4: [28,30,3],
	5: [28,29,3],
	6: [27,1],
	7: [27,1]
	}

swreg1 = "x31"

seed = 10

#------------------------------------------------------------------------------------------------------------------

config_ZKn = ['aes64ds','aes64dsm','aes64es','aes64esm','sha256sig0','sha256sig1','sha256sum0','sha256sum1',\
			 'sha512sig0','sha512sig1','sha512sum0','sha512sum1','aes64im','aes32esi','aes32esmi','aes32dsi',\
			 'aes32dsmi','sha512sig0h','sha512sig0l','sha512sig1h','sha512sig1l','sha512sum0r','sha512sum1r']

config_ZKs = ['sm3p0','sm3p1','sm4ed','sm4ks']

if os.path.isdir(os.getcwd()+"/real_world_tests") == False:
	os.mkdir(os.getcwd()+"/real_world_tests")
	os.mkdir(os.getcwd()+"/real_world_tests/RV32IK")
	os.mkdir(os.getcwd()+"/real_world_tests/RV64IK")

for key in instr_dict:
	for z in instr_dict[key]:
		with open(os.getcwd()+'/real_world_tests/RV'+str(xlen[key])+'IK/'+z+'-rwp1.S','w') as out:
			offset_val = 0
			if z in config_ZKn:
				config = "ZKn"
			elif z in config_ZKs:
				config = "ZKs"
			sp = start_str.replace("$inst",z).replace("$swreg1",swreg1).replace("$xlen",str(xlen[key])).replace("$config",config)
			out.write(sp)
			out.write('\n\n')
			random.seed(seed)
			for i in range(1,n_i[key][0]):
				out.write("inst_"+str(i-1)+":\n")
				
				r1 = random.randint(0,2**xlen[key]-1)
				r2 = random.randint(0,2**xlen[key]-1)
				r3 = random.randint(0,2**xlen[key]-1)
				r4 = random.randint(0,2**xlen[key]-1)
				r5 = random.randint(0,2**xlen[key]-1)
				r6 = random.randint(0,2**xlen[key]-1)
				r1_str = '{0:#0{1}x}'.format(r1,int(xlen[key]/4)+2)
				r2_str = '{0:#0{1}x}'.format(r2,int(xlen[key]/4)+2)
				r3_str = '{0:#0{1}x}'.format(r3,int(xlen[key]/4)+2)
				r4_str = '{0:#0{1}x}'.format(r4,int(xlen[key]/4)+2)
				r5_str = '{0:#0{1}x}'.format(r5,int(xlen[key]/4)+2)
				r6_str = '{0:#0{1}x}'.format(r6,int(xlen[key]/4)+2)
				
				if key == 1:
					comment_str = comment_dict[key][0].replace("$rs1","x"+str(i)).replace("$rs2","x"+str(i+1)).replace("$inst",z)

					sp = string1.replace("$rs1","x"+str(i)).replace("$rs2","x"+str(i+1))\
					.replace("$rd1","x"+str(i+2)).replace("$rd2","x"+str(i+3)).replace("$rd3","x"+str(i+4))\
					.replace("$inst",z).replace("$swreg1",swreg1).replace("$offset1",str(offset_val))\
					.replace("$offset2",str(int(offset_val+xlen[key]/8)))\
					.replace("$offset3",str(int(offset_val+xlen[key]/4)))\
					.replace("$r1_val",r1_str).replace("$r2_val",r2_str).replace("$comment",comment_str)

					offset_val = int(offset_val + (xlen[key]*6)/16)
					out.write(sp)
					out.write('\n\n')

				elif key == 2 or key == 4 or key == 5:
					for j in instr_f[key]:
						comment_str = comment_dict[key][0].replace("$inst1",j).replace("$inst2",z)

						if key == 2 or key == 4:
                                                    if j == 'not':
                                                        sp = string2_not.replace("$rs1","x"+str(i)).replace("$rs2","x"+str(i+1))\
							.replace("$rs3","x"+str(i+2)).replace("$rs4","x"+str(i+3)).replace("$inst1",j)\
							.replace("$inst2",z).replace("$swreg1",swreg1).replace("$offset1",str(offset_val))\
							.replace("$offset2",str(int(offset_val+xlen[key]/8)))\
							.replace("$offset3",str(int(offset_val+xlen[key]/4)))\
							.replace("$r1_val",r1_str).replace("$r2_val",r2_str).replace("$comment",comment_str)
                                                    else:
                                                        sp = string2.replace("$rs1","x"+str(i)).replace("$rs2","x"+str(i+1))\
							.replace("$rs3","x"+str(i+2)).replace("$rs4","x"+str(i+3)).replace("$inst1",j)\
							.replace("$inst2",z).replace("$swreg1",swreg1).replace("$offset1",str(offset_val))\
							.replace("$offset2",str(int(offset_val+xlen[key]/8)))\
							.replace("$offset3",str(int(offset_val+xlen[key]/4)))\
							.replace("$r1_val",r1_str).replace("$r2_val",r2_str).replace("$comment",comment_str)
						elif key == 5:
                                                    if j == 'not':
                                                        sp = string5_not.replace("$rs1","x"+str(i)).replace("$rs2","x"+str(i+1))\
							.replace("$rs3","x"+str(i+2)).replace("$rs4","x"+str(i+3)).replace("$inst1",j)\
							.replace("$inst2",z).replace("$swreg1",swreg1).replace("$offset1",str(offset_val))\
							.replace("$offset2",str(int(offset_val+xlen[key]/8)))\
							.replace("$offset3",str(int(offset_val+xlen[key]/4)))\
							.replace("$r1_val",r1_str).replace("$r2_val",r2_str).replace("$comment",comment_str)
                                                    else :
                                                        sp = string5.replace("$rs1","x"+str(i)).replace("$rs2","x"+str(i+1))\
							.replace("$rs3","x"+str(i+2)).replace("$rs4","x"+str(i+3)).replace("$inst1",j)\
							.replace("$inst2",z).replace("$swreg1",swreg1).replace("$offset1",str(offset_val))\
							.replace("$offset2",str(int(offset_val+xlen[key]/8)))\
							.replace("$offset3",str(int(offset_val+xlen[key]/4)))\
							.replace("$r1_val",r1_str).replace("$r2_val",r2_str).replace("$comment",comment_str)

						offset_val = int(offset_val + (xlen[key]*6)/16)
						out.write(sp)
						out.write('\n\n')

				elif key == 3:
					comment_str = comment_dict[key][0]

					sp = string4.replace("$rs1","x"+str(i)).replace("$rs2","x"+str(i+1))\
					.replace("$rs3","x"+str(i+2)).replace("$rs4","x"+str(i+3)).replace("$rs5","x"+str(i+4))\
					.replace("$inst",z).replace("$swreg1",swreg1).replace("$offset1",str(offset_val))\
					.replace("$r1_val",r1_str).replace("$r2_val",r2_str).replace("$r3_val",r3_str)\
					.replace("$r4_val",r4_str).replace("$r5_val",r5_str)\
					.replace("$comment",comment_str)

					offset_val = offset_val + int(xlen[key]/8)
					out.write(sp)
					out.write('\n\n')
				elif key == 6 or key == 7:
					comment_str = comment_dict[key][0]

					sp = string7.replace("$rs1","x"+str(i)).replace("$rs2","x"+str(i+1))\
					.replace("$rs3","x"+str(i+2)).replace("$rs4","x"+str(i+3)).replace("$rs5","x"+str(i+4))\
					.replace("$rs6","x"+str(i+5))\
					.replace("$inst",z).replace("$swreg1",swreg1).replace("$offset1",str(offset_val))\
					.replace("$r1_val",r1_str).replace("$r2_val",r2_str).replace("$r3_val",r3_str)\
					.replace("$r4_val",r4_str).replace("$r5_val",r5_str)\
					.replace("$r6_val",r6_str)\
					.replace("$comment",comment_str)

					offset_val = offset_val + int(xlen[key]/8)
					out.write(sp)
					out.write('\n\n')
				
			ed = end_str.replace("$swreg1",swreg1)\
				.replace("$fill_val",str(((n_i[key][0])-1)*n_i[key][len(n_i[key])-1]*len(instr_f[key])))
			out.write(ed)
			out.write('\n')
			out.close()
			print("Test File Generated for "+str(xlen[key])+"-bit "+z+"-Test Pattern 1!")

		if key == 2 or key == 4 or key == 5:
			with open(os.getcwd()+'/real_world_tests/RV'+str(xlen[key])+'IK/'+z+'-rwp2.S','w') as out:
				offset_val1 = 0
				offset_val2 = 0
				if z in config_ZKn:
					config = "ZKn"
				elif z in config_ZKs:
					config = "ZKs"
				sp = start_str.replace("$inst",z).replace("$swreg1",swreg1).replace("$xlen",str(xlen[key])).replace("$config",config)
				out.write(sp)
				out.write('\n\n')
				out.write("la x1, rvtest_data")
				out.write('\n\n')
				random.seed(seed)
				for i in range(2,n_i[key][1]):
					out.write("inst_"+str(i-2)+":\n")

					comment_str = comment_dict[key][1]

					if key == 2 or key ==4:
						sp = string3.replace("$rs0","x1").replace("$rs1","x"+str(i))\
						.replace("$rs2","x"+str(i+1)).replace("$inst",z).replace("$swreg1",swreg1)\
						.replace("$offset1",str(offset_val1)).replace("$offset2",str(offset_val2))\
						.replace("$offset3",str(int(offset_val2+xlen[key]/8))).replace("$comment",comment_str)
					elif key == 5:
						sp = string6.replace("$rs0","x1").replace("$rs1","x"+str(i))\
						.replace("$rs2","x"+str(i+1)).replace("$rs3","x"+str(i+2))\
						.replace("$inst",z).replace("$swreg1",swreg1).replace("$offset1",str(offset_val1))\
						.replace("$offset2",str(int(offset_val1+xlen[key]/8))).replace("$offset3",str(offset_val2))\
						.replace("$offset4",str(int(offset_val2+xlen[key]/8))).replace("$comment",comment_str)

					offset_val1 = int(offset_val1 + xlen[key]/8)
					offset_val2 = int(offset_val2 + xlen[key]/4)
					out.write(sp)
					out.write('\n\n')

				out.write(end_str1)
				out.write('\n')
				for j in range(2,30):
                                    x = random.randint(0,2**xlen[key]-1)
                                    x_str = '{0:#0{1}x}'.format(x,int(xlen[key]/4)+2)
                                    if xlen[key] == 64:
                                        out.write(".dword "+x_str+"\n")
                                    else:
                                        out.write(".word "+x_str+"\n")

				ed = end_str2.replace("$swreg1",swreg1).replace("$fill_val",str((n_i[key][1]-2)*2))
				out.write(ed)
				out.write('\n')
				out.close()
				print("Test File Generated for "+str(xlen[key])+"-bit "+z+"-Test Pattern 2!")
