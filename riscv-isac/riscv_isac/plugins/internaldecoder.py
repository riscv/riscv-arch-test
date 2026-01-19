from ordered_set import OrderedSet
import riscv_isac.plugins as plugins

class disassembler():

    def __init__(self):
        OPCODES = {
            0b0110111: self.lui,
            0b0010111: self.auipc,
            0b1101111: self.jal,
            0b1100111: self.jalr,
            0b1100011: self.branch_ops,
            0b0000011: self.load_ops,
            0b0100011: self.store_ops,
            0b0010011: self.arithi_ops,
            0b0110011: self.arith_ops,
            0b0001111: self.mem_ops,
            0b1110011: self.priviledged_ops,
            0b0011011: self.rv64i_arithi_ops,
            0b0111011: self.rv64i_arith_ops,
            0b0101111: self.rv64_rv32_atomic_ops,
            0b0000111: self.flw_fld,
            0b0100111: self.fsw_fsd,
            0b1000011: self.fmadd,
            0b1000111: self.fmsub,
            0b1001011: self.fnmsub,
            0b1001111: self.fnmadd,
            0b1010011: self.rv32_rv64_float_ops,
            0b1110111: self.rvp_ops
        }
        """ Instruction Op-Codes dict for 32-bit instructions """

        C_OPCODES = {
            0b00: self.quad0,
            0b01: self.quad1,
            0b10: self.quad2
        }
        """ Instruction OP-CODES dict for 16-bit instructions """
        self.C_OPCODES = C_OPCODES
        self.OPCODES = OPCODES
        self.init_rvp_dictionary()
        self.rvp_rs1_is_64bit_set = OrderedSet('smal add64 radd64 uradd64 kadd64 ukadd64 sub64 rsub64 ursub64 ksub64 uksub64 wext wexti'.split())
        self.rvp_rs2_is_64bit_set = OrderedSet(     'add64 radd64 uradd64 kadd64 ukadd64 sub64 rsub64 ursub64 ksub64 uksub64'.split())
        self.rvp_rd_is_64bit_set  = OrderedSet('smul16 smulx16 umul16 umulx16 smul8 smulx8 umul8 umulx8 smal add64 radd64 uradd64 kadd64 ukadd64 sub64 rsub64 ursub64 ksub64 uksub64 smar64 smsr64 umar64 umsr64 kmar64 kmsr64 ukmar64 ukmsr64 smalbb smalbt smaltt smalda smalxda smalds smaldrs smalxds smslda smslxda mulr64 mulsr64 wext wexti'.split())

    def init_rvp_dictionary(self):
        # Create RVP Dictiory 0 for instruction:  clrs8  clrs16  clrs32  clo8  clo16  clo32  clz8  clz16  clz32  kabs8  kabs16  kabsw  sunpkd810  sunpkd820  sunpkd830  sunpkd831  sunpkd832  swap8  zunpkd810  zunpkd820  zunpkd830  zunpkd831  zunpkd832  kabs32
        self.rvp_dict_0 = {}
        self.rvp_dict_0[0xae000077] = 'clrs8'
        self.rvp_dict_0[0xae800077] = 'clrs16'
        self.rvp_dict_0[0xaf800077] = 'clrs32'
        self.rvp_dict_0[0xae300077] = 'clo8'
        self.rvp_dict_0[0xaeb00077] = 'clo16'
        self.rvp_dict_0[0xafb00077] = 'clo32'
        self.rvp_dict_0[0xae100077] = 'clz8'
        self.rvp_dict_0[0xae900077] = 'clz16'
        self.rvp_dict_0[0xaf900077] = 'clz32'
        self.rvp_dict_0[0xad000077] = 'kabs8'
        self.rvp_dict_0[0xad100077] = 'kabs16'
        self.rvp_dict_0[0xad400077] = 'kabsw'
        self.rvp_dict_0[0xac800077] = 'sunpkd810'
        self.rvp_dict_0[0xac900077] = 'sunpkd820'
        self.rvp_dict_0[0xaca00077] = 'sunpkd830'
        self.rvp_dict_0[0xacb00077] = 'sunpkd831'
        self.rvp_dict_0[0xad300077] = 'sunpkd832'
        self.rvp_dict_0[0xad800077] = 'swap8'
        self.rvp_dict_0[0xacc00077] = 'zunpkd810'
        self.rvp_dict_0[0xacd00077] = 'zunpkd820'
        self.rvp_dict_0[0xace00077] = 'zunpkd830'
        self.rvp_dict_0[0xacf00077] = 'zunpkd831'
        self.rvp_dict_0[0xad700077] = 'zunpkd832'
        self.rvp_dict_0[0xad200077] = 'kabs32'

        # Create RVP Dictiory 1 for instruction:  add8  add16  ave  bitrev  cmpeq8  cmpeq16  cras16  crsa16  kadd8  kadd16  kcras16  kcrsa16  khm8  khmx8  khm16  khmx16  ksll8  ksll16  kslra8  kslra8.u  kslra16  kslra16.u  ksub8  ksub16  maxw  minw  pbsad  pbsada  radd8  radd16  rcras16  rcrsa16  rsub8  rsub16  scmple8  scmple16  scmplt8  scmplt16  sll8  sll16  smaqa  smaqa.su  smax8  smax16  smin8  smin16  smul8  smulx8  smul16  smulx16  sra8  sra8.u  sra16  sra16.u  srl8  srl8.u  srl16  srl16.u  sub8  sub16  ucmple8  ucmple16  ucmplt8  ucmplt16  ukadd8  ukadd16  ukcras16  ukcrsa16  uksub8  uksub16  umaqa  umax8  umax16  umin8  umin16  umul8  umulx8  umul16  umulx16  uradd8  uradd16  urcras16  urcrsa16  ursub8  ursub16  wext
        self.rvp_dict_1 = {}
        self.rvp_dict_1[0x48000077] = 'add8'
        self.rvp_dict_1[0x40000077] = 'add16'
        self.rvp_dict_1[0xe0000077] = 'ave'
        self.rvp_dict_1[0xe6000077] = 'bitrev'
        self.rvp_dict_1[0x4e000077] = 'cmpeq8'
        self.rvp_dict_1[0x4c000077] = 'cmpeq16'
        self.rvp_dict_1[0x44000077] = 'cras16'
        self.rvp_dict_1[0x46000077] = 'crsa16'
        self.rvp_dict_1[0x18000077] = 'kadd8'
        self.rvp_dict_1[0x10000077] = 'kadd16'
        self.rvp_dict_1[0x14000077] = 'kcras16'
        self.rvp_dict_1[0x16000077] = 'kcrsa16'
        self.rvp_dict_1[0x8e000077] = 'khm8'
        self.rvp_dict_1[0x9e000077] = 'khmx8'
        self.rvp_dict_1[0x86000077] = 'khm16'
        self.rvp_dict_1[0x96000077] = 'khmx16'
        self.rvp_dict_1[0x6c000077] = 'ksll8'
        self.rvp_dict_1[0x64000077] = 'ksll16'
        self.rvp_dict_1[0x5e000077] = 'kslra8'
        self.rvp_dict_1[0x6e000077] = 'kslra8.u'
        self.rvp_dict_1[0x56000077] = 'kslra16'
        self.rvp_dict_1[0x66000077] = 'kslra16.u'
        self.rvp_dict_1[0x1a000077] = 'ksub8'
        self.rvp_dict_1[0x12000077] = 'ksub16'
        self.rvp_dict_1[0xf2000077] = 'maxw'
        self.rvp_dict_1[0xf0000077] = 'minw'
        self.rvp_dict_1[0xfc000077] = 'pbsad'
        self.rvp_dict_1[0xfe000077] = 'pbsada'
        self.rvp_dict_1[0x08000077] = 'radd8'
        self.rvp_dict_1[0x00000077] = 'radd16'
        self.rvp_dict_1[0x04000077] = 'rcras16'
        self.rvp_dict_1[0x06000077] = 'rcrsa16'
        self.rvp_dict_1[0x0a000077] = 'rsub8'
        self.rvp_dict_1[0x02000077] = 'rsub16'
        self.rvp_dict_1[0x1e000077] = 'scmple8'
        self.rvp_dict_1[0x1c000077] = 'scmple16'
        self.rvp_dict_1[0x0e000077] = 'scmplt8'
        self.rvp_dict_1[0x0c000077] = 'scmplt16'
        self.rvp_dict_1[0x5c000077] = 'sll8'
        self.rvp_dict_1[0x54000077] = 'sll16'
        self.rvp_dict_1[0xc8000077] = 'smaqa'
        self.rvp_dict_1[0xca000077] = 'smaqa.su'
        self.rvp_dict_1[0x8a000077] = 'smax8'
        self.rvp_dict_1[0x82000077] = 'smax16'
        self.rvp_dict_1[0x88000077] = 'smin8'
        self.rvp_dict_1[0x80000077] = 'smin16'
        self.rvp_dict_1[0xa8000077] = 'smul8'
        self.rvp_dict_1[0xaa000077] = 'smulx8'
        self.rvp_dict_1[0xa0000077] = 'smul16'
        self.rvp_dict_1[0xa2000077] = 'smulx16'
        self.rvp_dict_1[0x58000077] = 'sra8'
        self.rvp_dict_1[0x68000077] = 'sra8.u'
        self.rvp_dict_1[0x50000077] = 'sra16'
        self.rvp_dict_1[0x60000077] = 'sra16.u'
        self.rvp_dict_1[0x5a000077] = 'srl8'
        self.rvp_dict_1[0x6a000077] = 'srl8.u'
        self.rvp_dict_1[0x52000077] = 'srl16'
        self.rvp_dict_1[0x62000077] = 'srl16.u'
        self.rvp_dict_1[0x4a000077] = 'sub8'
        self.rvp_dict_1[0x42000077] = 'sub16'
        self.rvp_dict_1[0x3e000077] = 'ucmple8'
        self.rvp_dict_1[0x3c000077] = 'ucmple16'
        self.rvp_dict_1[0x2e000077] = 'ucmplt8'
        self.rvp_dict_1[0x2c000077] = 'ucmplt16'
        self.rvp_dict_1[0x38000077] = 'ukadd8'
        self.rvp_dict_1[0x30000077] = 'ukadd16'
        self.rvp_dict_1[0x34000077] = 'ukcras16'
        self.rvp_dict_1[0x36000077] = 'ukcrsa16'
        self.rvp_dict_1[0x3a000077] = 'uksub8'
        self.rvp_dict_1[0x32000077] = 'uksub16'
        self.rvp_dict_1[0xcc000077] = 'umaqa'
        self.rvp_dict_1[0x9a000077] = 'umax8'
        self.rvp_dict_1[0x92000077] = 'umax16'
        self.rvp_dict_1[0x98000077] = 'umin8'
        self.rvp_dict_1[0x90000077] = 'umin16'
        self.rvp_dict_1[0xb8000077] = 'umul8'
        self.rvp_dict_1[0xba000077] = 'umulx8'
        self.rvp_dict_1[0xb0000077] = 'umul16'
        self.rvp_dict_1[0xb2000077] = 'umulx16'
        self.rvp_dict_1[0x28000077] = 'uradd8'
        self.rvp_dict_1[0x20000077] = 'uradd16'
        self.rvp_dict_1[0x24000077] = 'urcras16'
        self.rvp_dict_1[0x26000077] = 'urcrsa16'
        self.rvp_dict_1[0x2a000077] = 'ursub8'
        self.rvp_dict_1[0x22000077] = 'ursub16'
        self.rvp_dict_1[0xce000077] = 'wext'

        # Create RVP Dictiory 2 for instruction:  insb  kslli8  sclip8  slli8  srai8  srai8.u  srli8  srli8.u  uclip8
        self.rvp_dict_2 = {}
        self.rvp_dict_2[0xac000077] = 'insb'
        self.rvp_dict_2[0x7c800077] = 'kslli8'
        self.rvp_dict_2[0x8c000077] = 'sclip8'
        self.rvp_dict_2[0x7c000077] = 'slli8'
        self.rvp_dict_2[0x78000077] = 'srai8'
        self.rvp_dict_2[0x78800077] = 'srai8.u'
        self.rvp_dict_2[0x7a000077] = 'srli8'
        self.rvp_dict_2[0x7a800077] = 'srli8.u'
        self.rvp_dict_2[0x8d000077] = 'uclip8'

        # Create RVP Dictiory 3 for instruction:  kslli16  sclip16  slli16  srai16  srai16.u  srli16  srli16.u  uclip16
        self.rvp_dict_3 = {}
        self.rvp_dict_3[0x75000077] = 'kslli16'
        self.rvp_dict_3[0x84000077] = 'sclip16'
        self.rvp_dict_3[0x74000077] = 'slli16'
        self.rvp_dict_3[0x70000077] = 'srai16'
        self.rvp_dict_3[0x71000077] = 'srai16.u'
        self.rvp_dict_3[0x72000077] = 'srli16'
        self.rvp_dict_3[0x73000077] = 'srli16.u'
        self.rvp_dict_3[0x85000077] = 'uclip16'

        # Create RVP Dictiory 4 for instruction:  sclip32  uclip32  wexti
        self.rvp_dict_4 = {}
        self.rvp_dict_4[0xe4000077] = 'sclip32'
        self.rvp_dict_4[0xf4000077] = 'uclip32'
        self.rvp_dict_4[0xde000077] = 'wexti'

        # Create RVP Dictiory 5 for instruction:  bitrevi
        self.rvp_dict_5 = {}
        self.rvp_dict_5[0xe8000077] = 'bitrevi'

        # Create RVP Dictiory 6 for instruction:  add64  kadd64  kaddh  kaddw  kdmbb  kdmbt  kdmtt  kdmabb  kdmabt  kdmatt  khmbb  khmbt  khmtt  kmabb  kmabt  kmatt  kmada  kmaxda  kmads  kmadrs  kmaxds  kmar64  kmda  kmxda  kmmac  kmmac.u  kmmawb  kmmawb.u  kmmawb2  kmmawb2.u  kmmawt  kmmawt.u  kmmawt2  kmmawt2.u  kmmsb  kmmsb.u  kmmwb2  kmmwb2.u  kmmwt2  kmmwt2.u  kmsda  kmsxda  kmsr64  ksllw  kslraw  kslraw.u  ksub64  ksubh  ksubw  kwmmul  kwmmul.u  maddr32  msubr32  mulr64  mulsr64  pkbb16  pkbt16  pktt16  pktb16  radd64  raddw  rsub64  rsubw  smal  smalbb  smalbt  smaltt  smalda  smalxda  smalds  smaldrs  smalxds  smar64  smbb16  smbt16  smtt16  smds  smdrs  smxds  smmul  smmul.u  smmwb  smmwb.u  smmwt  smmwt.u  smslda  smslxda  smsr64  sra.u  sub64  ukadd64  ukaddh  ukaddw  ukmar64  ukmsr64  uksub64  uksubh  uksubw  umar64  umsr64  uradd64  uraddw  ursub64  ursubw  kdmbb16  kdmbt16  kdmtt16  kdmabb16  kdmabt16  kdmatt16  khmbb16  khmbt16  khmtt16
        self.rvp_dict_6 = {}
        self.rvp_dict_6[0xc0001077] = 'add64'
        self.rvp_dict_6[0x90001077] = 'kadd64'
        self.rvp_dict_6[0x04001077] = 'kaddh'
        self.rvp_dict_6[0x00001077] = 'kaddw'
        self.rvp_dict_6[0x0a001077] = 'kdmbb'
        self.rvp_dict_6[0x1a001077] = 'kdmbt'
        self.rvp_dict_6[0x2a001077] = 'kdmtt'
        self.rvp_dict_6[0xd2001077] = 'kdmabb'
        self.rvp_dict_6[0xe2001077] = 'kdmabt'
        self.rvp_dict_6[0xf2001077] = 'kdmatt'
        self.rvp_dict_6[0x0c001077] = 'khmbb'
        self.rvp_dict_6[0x1c001077] = 'khmbt'
        self.rvp_dict_6[0x2c001077] = 'khmtt'
        self.rvp_dict_6[0x5a001077] = 'kmabb'
        self.rvp_dict_6[0x6a001077] = 'kmabt'
        self.rvp_dict_6[0x7a001077] = 'kmatt'
        self.rvp_dict_6[0x48001077] = 'kmada'
        self.rvp_dict_6[0x4a001077] = 'kmaxda'
        self.rvp_dict_6[0x5c001077] = 'kmads'
        self.rvp_dict_6[0x6c001077] = 'kmadrs'
        self.rvp_dict_6[0x7c001077] = 'kmaxds'
        self.rvp_dict_6[0x94001077] = 'kmar64'
        self.rvp_dict_6[0x38001077] = 'kmda'
        self.rvp_dict_6[0x3a001077] = 'kmxda'
        self.rvp_dict_6[0x60001077] = 'kmmac'
        self.rvp_dict_6[0x70001077] = 'kmmac.u'
        self.rvp_dict_6[0x46001077] = 'kmmawb'
        self.rvp_dict_6[0x56001077] = 'kmmawb.u'
        self.rvp_dict_6[0xce001077] = 'kmmawb2'
        self.rvp_dict_6[0xde001077] = 'kmmawb2.u'
        self.rvp_dict_6[0x66001077] = 'kmmawt'
        self.rvp_dict_6[0x76001077] = 'kmmawt.u'
        self.rvp_dict_6[0xee001077] = 'kmmawt2'
        self.rvp_dict_6[0xfe001077] = 'kmmawt2.u'
        self.rvp_dict_6[0x42001077] = 'kmmsb'
        self.rvp_dict_6[0x52001077] = 'kmmsb.u'
        self.rvp_dict_6[0x8e001077] = 'kmmwb2'
        self.rvp_dict_6[0x9e001077] = 'kmmwb2.u'
        self.rvp_dict_6[0xae001077] = 'kmmwt2'
        self.rvp_dict_6[0xbe001077] = 'kmmwt2.u'
        self.rvp_dict_6[0x4c001077] = 'kmsda'
        self.rvp_dict_6[0x4e001077] = 'kmsxda'
        self.rvp_dict_6[0x96001077] = 'kmsr64'
        self.rvp_dict_6[0x26001077] = 'ksllw'
        self.rvp_dict_6[0x6e001077] = 'kslraw'
        self.rvp_dict_6[0x7e001077] = 'kslraw.u'
        self.rvp_dict_6[0x92001077] = 'ksub64'
        self.rvp_dict_6[0x06001077] = 'ksubh'
        self.rvp_dict_6[0x02001077] = 'ksubw'
        self.rvp_dict_6[0x62001077] = 'kwmmul'
        self.rvp_dict_6[0x72001077] = 'kwmmul.u'
        self.rvp_dict_6[0xc4001077] = 'maddr32'
        self.rvp_dict_6[0xc6001077] = 'msubr32'
        self.rvp_dict_6[0xf0001077] = 'mulr64'
        self.rvp_dict_6[0xe0001077] = 'mulsr64'
        self.rvp_dict_6[0x0e001077] = 'pkbb16'
        self.rvp_dict_6[0x1e001077] = 'pkbt16'
        self.rvp_dict_6[0x2e001077] = 'pktt16'
        self.rvp_dict_6[0x3e001077] = 'pktb16'
        self.rvp_dict_6[0x80001077] = 'radd64'
        self.rvp_dict_6[0x20001077] = 'raddw'
        self.rvp_dict_6[0x82001077] = 'rsub64'
        self.rvp_dict_6[0x22001077] = 'rsubw'
        self.rvp_dict_6[0x5e001077] = 'smal'
        self.rvp_dict_6[0x88001077] = 'smalbb'
        self.rvp_dict_6[0x98001077] = 'smalbt'
        self.rvp_dict_6[0xa8001077] = 'smaltt'
        self.rvp_dict_6[0x8c001077] = 'smalda'
        self.rvp_dict_6[0x9c001077] = 'smalxda'
        self.rvp_dict_6[0x8a001077] = 'smalds'
        self.rvp_dict_6[0x9a001077] = 'smaldrs'
        self.rvp_dict_6[0xaa001077] = 'smalxds'
        self.rvp_dict_6[0x84001077] = 'smar64'
        self.rvp_dict_6[0x08001077] = 'smbb16'
        self.rvp_dict_6[0x18001077] = 'smbt16'
        self.rvp_dict_6[0x28001077] = 'smtt16'
        self.rvp_dict_6[0x58001077] = 'smds'
        self.rvp_dict_6[0x68001077] = 'smdrs'
        self.rvp_dict_6[0x78001077] = 'smxds'
        self.rvp_dict_6[0x40001077] = 'smmul'
        self.rvp_dict_6[0x50001077] = 'smmul.u'
        self.rvp_dict_6[0x44001077] = 'smmwb'
        self.rvp_dict_6[0x54001077] = 'smmwb.u'
        self.rvp_dict_6[0x64001077] = 'smmwt'
        self.rvp_dict_6[0x74001077] = 'smmwt.u'
        self.rvp_dict_6[0xac001077] = 'smslda'
        self.rvp_dict_6[0xbc001077] = 'smslxda'
        self.rvp_dict_6[0x86001077] = 'smsr64'
        self.rvp_dict_6[0x24001077] = 'sra.u'
        self.rvp_dict_6[0xc2001077] = 'sub64'
        self.rvp_dict_6[0xb0001077] = 'ukadd64'
        self.rvp_dict_6[0x14001077] = 'ukaddh'
        self.rvp_dict_6[0x10001077] = 'ukaddw'
        self.rvp_dict_6[0xb4001077] = 'ukmar64'
        self.rvp_dict_6[0xb6001077] = 'ukmsr64'
        self.rvp_dict_6[0xb2001077] = 'uksub64'
        self.rvp_dict_6[0x16001077] = 'uksubh'
        self.rvp_dict_6[0x12001077] = 'uksubw'
        self.rvp_dict_6[0xa4001077] = 'umar64'
        self.rvp_dict_6[0xa6001077] = 'umsr64'
        self.rvp_dict_6[0xa0001077] = 'uradd64'
        self.rvp_dict_6[0x30001077] = 'uraddw'
        self.rvp_dict_6[0xa2001077] = 'ursub64'
        self.rvp_dict_6[0x32001077] = 'ursubw'
        self.rvp_dict_6[0xda001077] = 'kdmbb16'
        self.rvp_dict_6[0xea001077] = 'kdmbt16'
        self.rvp_dict_6[0xfa001077] = 'kdmtt16'
        self.rvp_dict_6[0xd8001077] = 'kdmabb16'
        self.rvp_dict_6[0xe8001077] = 'kdmabt16'
        self.rvp_dict_6[0xf8001077] = 'kdmatt16'
        self.rvp_dict_6[0xdc001077] = 'khmbb16'
        self.rvp_dict_6[0xec001077] = 'khmbt16'
        self.rvp_dict_6[0xfc001077] = 'khmtt16'

        # Create RVP Dictiory 7 for instruction:  kslliw  sraiw.u
        self.rvp_dict_7 = {}
        self.rvp_dict_7[0x36001077] = 'kslliw'
        self.rvp_dict_7[0x34001077] = 'sraiw.u'

        # Create RVP Dictiory 8 for instruction:  srai.u
        self.rvp_dict_8 = {}
        self.rvp_dict_8[0xd4001077] = 'srai.u'

        # Create RVP Dictiory 9 for instruction:  kstas16  kstsa16  rstas16  rstsa16  stas16  stsa16  ukstas16  ukstsa16  urstas16  urstsa16  add32  cras32  crsa32  kadd32  kcras32  kcrsa32  kmabb32  kmabt32  kmatt32  kmaxda32  kmda32  kmxda32  kmads32  kmadrs32  kmaxds32  kmsda32  kmsxda32  ksll32  kslra32  kslra32.u  kstas32  kstsa32  ksub32  pkbb32  pkbt32  pktt32  pktb32  radd32  rcras32  rcrsa32  rstas32  rstsa32  rsub32  sll32  smax32  smbt32  smtt32  smds32  smdrs32  smxds32  smin32  sra32  sra32.u  srl32  srl32.u  stas32  stsa32  sub32  ukadd32  ukcras32  ukcrsa32  ukstas32  ukstsa32  uksub32  umax32  umin32  uradd32  urcras32  urcrsa32  urstas32  urstsa32  ursub32
        self.rvp_dict_9 = {}
        self.rvp_dict_9[0xc4002077] = 'kstas16'
        self.rvp_dict_9[0xc6002077] = 'kstsa16'
        self.rvp_dict_9[0xb4002077] = 'rstas16'
        self.rvp_dict_9[0xb6002077] = 'rstsa16'
        self.rvp_dict_9[0xf4002077] = 'stas16'
        self.rvp_dict_9[0xf6002077] = 'stsa16'
        self.rvp_dict_9[0xe4002077] = 'ukstas16'
        self.rvp_dict_9[0xe6002077] = 'ukstsa16'
        self.rvp_dict_9[0xd4002077] = 'urstas16'
        self.rvp_dict_9[0xd6002077] = 'urstsa16'
        self.rvp_dict_9[0x40002077] = 'add32'
        self.rvp_dict_9[0x44002077] = 'cras32'
        self.rvp_dict_9[0x46002077] = 'crsa32'
        self.rvp_dict_9[0x10002077] = 'kadd32'
        self.rvp_dict_9[0x14002077] = 'kcras32'
        self.rvp_dict_9[0x16002077] = 'kcrsa32'
        self.rvp_dict_9[0x5a002077] = 'kmabb32'
        self.rvp_dict_9[0x6a002077] = 'kmabt32'
        self.rvp_dict_9[0x7a002077] = 'kmatt32'
        self.rvp_dict_9[0x4a002077] = 'kmaxda32'
        self.rvp_dict_9[0x38002077] = 'kmda32'
        self.rvp_dict_9[0x3a002077] = 'kmxda32'
        self.rvp_dict_9[0x5c002077] = 'kmads32'
        self.rvp_dict_9[0x6c002077] = 'kmadrs32'
        self.rvp_dict_9[0x7c002077] = 'kmaxds32'
        self.rvp_dict_9[0x4c002077] = 'kmsda32'
        self.rvp_dict_9[0x4e002077] = 'kmsxda32'
        self.rvp_dict_9[0x64002077] = 'ksll32'
        self.rvp_dict_9[0x56002077] = 'kslra32'
        self.rvp_dict_9[0x66002077] = 'kslra32.u'
        self.rvp_dict_9[0xc0002077] = 'kstas32'
        self.rvp_dict_9[0xc2002077] = 'kstsa32'
        self.rvp_dict_9[0x12002077] = 'ksub32'
        self.rvp_dict_9[0x0e002077] = 'pkbb32'
        self.rvp_dict_9[0x1e002077] = 'pkbt32'
        self.rvp_dict_9[0x2e002077] = 'pktt32'
        self.rvp_dict_9[0x3e002077] = 'pktb32'
        self.rvp_dict_9[0x00002077] = 'radd32'
        self.rvp_dict_9[0x04002077] = 'rcras32'
        self.rvp_dict_9[0x06002077] = 'rcrsa32'
        self.rvp_dict_9[0xb0002077] = 'rstas32'
        self.rvp_dict_9[0xb2002077] = 'rstsa32'
        self.rvp_dict_9[0x02002077] = 'rsub32'
        self.rvp_dict_9[0x54002077] = 'sll32'
        self.rvp_dict_9[0x92002077] = 'smax32'
        self.rvp_dict_9[0x18002077] = 'smbt32'
        self.rvp_dict_9[0x28002077] = 'smtt32'
        self.rvp_dict_9[0x58002077] = 'smds32'
        self.rvp_dict_9[0x68002077] = 'smdrs32'
        self.rvp_dict_9[0x78002077] = 'smxds32'
        self.rvp_dict_9[0x90002077] = 'smin32'
        self.rvp_dict_9[0x50002077] = 'sra32'
        self.rvp_dict_9[0x60002077] = 'sra32.u'
        self.rvp_dict_9[0x52002077] = 'srl32'
        self.rvp_dict_9[0x62002077] = 'srl32.u'
        self.rvp_dict_9[0xf0002077] = 'stas32'
        self.rvp_dict_9[0xf2002077] = 'stsa32'
        self.rvp_dict_9[0x42002077] = 'sub32'
        self.rvp_dict_9[0x30002077] = 'ukadd32'
        self.rvp_dict_9[0x34002077] = 'ukcras32'
        self.rvp_dict_9[0x36002077] = 'ukcrsa32'
        self.rvp_dict_9[0xe0002077] = 'ukstas32'
        self.rvp_dict_9[0xe2002077] = 'ukstsa32'
        self.rvp_dict_9[0x32002077] = 'uksub32'
        self.rvp_dict_9[0xa2002077] = 'umax32'
        self.rvp_dict_9[0xa0002077] = 'umin32'
        self.rvp_dict_9[0x20002077] = 'uradd32'
        self.rvp_dict_9[0x24002077] = 'urcras32'
        self.rvp_dict_9[0x26002077] = 'urcrsa32'
        self.rvp_dict_9[0xd0002077] = 'urstas32'
        self.rvp_dict_9[0xd2002077] = 'urstsa32'
        self.rvp_dict_9[0x22002077] = 'ursub32'

        # Create RVP Dictiory 10 for instruction:  kslli32  slli32  srai32  srai32.u  srli32  srli32.u
        self.rvp_dict_10 = {}
        self.rvp_dict_10[0x84002077] = 'kslli32'
        self.rvp_dict_10[0x74002077] = 'slli32'
        self.rvp_dict_10[0x70002077] = 'srai32'
        self.rvp_dict_10[0x80002077] = 'srai32.u'
        self.rvp_dict_10[0x72002077] = 'srli32'
        self.rvp_dict_10[0x82002077] = 'srli32.u'

        # Create RVP Dictiory 11 for instruction:  bpick
        self.rvp_dict_11 = {}
        self.rvp_dict_11[0x00003077] = 'bpick'

    @plugins.decoderHookImpl
    def setup(self, arch):
        self.arch = arch

    FIRST2_MASK = 0x00000003
    OPCODE_MASK = 0x0000007f
    FUNCT3_MASK = 0x00007000
    FUNCT6_MASK = 0x3F000000
    FUNCT4_MASK = 0x3e000000

    RD_MASK = 0x00000f80
    RS1_MASK = 0x000f8000
    RS2_MASK = 0x01f00000
    RS3_MASK = 0xf8000000
    BS_MASK = 0xc0000000

    def extractOpcode(self, instr):
        return self.OPCODE_MASK & instr

    ''' Processing Instr from OPCODES '''
    def twos_comp(self, val, bits):
        if (val & (1 << (bits - 1))) != 0:
            val = val - (1 << bits)
        return val

    def lui(self, instrObj):
        instr = instrObj.instr
        imm = instr >> 12
        rd = ((instr & self.RD_MASK) >> 7, 'x')
        instrObj.rd = rd
        instrObj.imm = imm
        instrObj.instr_name = "lui"
        return instrObj

    def auipc(self, instrObj):
        instr = instrObj.instr
        imm = instr >> 12
        rd = ((instr & self.RD_MASK) >> 7, 'x')
        instrObj.rd = rd
        instrObj.imm = imm
        instrObj.instr_name = "auipc"
        return instrObj

    def jal(self, instrObj):
        instr = instrObj.instr
        imm_10_1 = (instr >> 21) & 0x000003ff
        imm_11 = (instr >> 10) & 0x00000400
        imm_19_12 = (instr & 0x000ff000) >> 1
        imm_20 = (instr >> 31) << 19
        imm = imm_20 + imm_19_12 + imm_11 + imm_10_1
        imm = self.twos_comp(imm, 20)
        rd = ((instr & self.RD_MASK) >> 7, 'x')
        instrObj.imm = imm
        instrObj.rd = rd
        instrObj.instr_name = "jal"
        return instrObj

    def jalr(self, instrObj):
        instr = instrObj.instr
        rd = ((instr & self.RD_MASK) >> 7, 'x')
        rs1 = ((instr & self.RS1_MASK) >> 15, 'x')
        imm_11_0 = instr >> 20
        imm = self.twos_comp(imm_11_0, 12)
        instrObj.rd = rd
        instrObj.rs1 = rs1
        instrObj.imm = imm
        instrObj.instr_name = "jalr"
        return instrObj

    def branch_ops(self, instrObj):
        instr = instrObj.instr
        funct3 = (instr & self.FUNCT3_MASK) >> 12
        rs1 = ((instr & self.RS1_MASK) >> 15, 'x')
        rs2 = ((instr & self.RS2_MASK) >> 20, 'x')
        imm_4_1 = (instr >> 8) & 0x0000000F
        imm_10_5 = (instr >> 21) & 0x000003f0
        imm_11 = (instr << 3) & 0x00000400
        imm_12 = (instr & 0x80000000) >> 20
        imm = imm_4_1 + imm_10_5 + imm_11 + imm_12
        imm = self.twos_comp(imm, 12)
        instrObj.rs1 = rs1
        instrObj.rs2 = rs2
        instrObj.imm = imm

        if funct3 == 0b000:
            instrObj.instr_name = 'beq'
        if funct3 == 0b001:
            instrObj.instr_name = 'bne'
        if funct3 == 0b100:
            instrObj.instr_name = 'blt'
        if funct3 == 0b101:
            instrObj.instr_name = 'bge'
        if funct3 == 0b110:
            instrObj.instr_name = 'bltu'
        if funct3 == 0b111:
            instrObj.instr_name = 'bgeu'

        return instrObj

    def load_ops(self, instrObj):
        instr = instrObj.instr
        funct3 = (instr & self.FUNCT3_MASK) >> 12
        rd = ((instr & self.RD_MASK) >> 7, 'x')
        rs1 = ((instr & self.RS1_MASK) >> 15, 'x')
        imm = self.twos_comp(instr >> 20, 12)

        instrObj.rd = rd
        instrObj.rs1 = rs1
        instrObj.imm = imm

        if funct3 == 0b000:
            instrObj.instr_name = 'lb'
        if funct3 == 0b001:
            instrObj.instr_name = 'lh'
        if funct3 == 0b010:
            instrObj.instr_name = 'lw'
        if funct3 == 0b100:
            instrObj.instr_name = 'lbu'
        if funct3 == 0b101:
            instrObj.instr_name = 'lhu'
        if funct3 == 0b110:
            instrObj.instr_name = 'lwu'
        if funct3 == 0b011:
            instrObj.instr_name = 'ld'

        return instrObj

    def store_ops(self, instrObj):
        instr = instrObj.instr
        funct3 = (instr & self.FUNCT3_MASK) >> 12
        rs1 = ((instr & self.RS1_MASK) >> 15, 'x')
        rs2 = ((instr & self.RS2_MASK) >> 20, 'x')
        imm_4_0 = (instr >> 7) & 0x0000001f
        imm_11_5 = (instr >> 20) & 0x00000fe0
        imm = self.twos_comp(imm_4_0 + imm_11_5, 12)

        instrObj.rs1 = rs1
        instrObj.rs2 = rs2
        instrObj.imm = imm

        if funct3 == 0b000:
            instrObj.instr_name = 'sb'
        if funct3 == 0b001:
            instrObj.instr_name = 'sh'
        if funct3 == 0b010:
            instrObj.instr_name = 'sw'
        if funct3 == 0b011:
            instrObj.instr_name = 'sd'

        return instrObj

    def arithi_ops(self, instrObj):

        instr = instrObj.instr

        funct3 = (instr & self.FUNCT3_MASK) >> 12
        funct4 = (instr & self.FUNCT4_MASK) >> 25
        funct6 = (instr & self.FUNCT6_MASK) >> 26
        funct7 = (instr >> 25)
        rd = ((instr & self.RD_MASK) >> 7, 'x')

        if funct3 == 0b110:
            if rd[0] == 0:
                return self.prefetch_ops(instrObj)

        rs1 = ((instr & self.RS1_MASK) >> 15, 'x')
        rs2 = ((instr & self.RS2_MASK) >> 20, 'x')
        rs3 = ((instr & self.RS3_MASK) >> 27, 'x')
        imm = (instr >> 20)
        imm_val = self.twos_comp(imm, 12)
        bs = (instr & self.BS_MASK) >> 30
        if self.arch  == 'rv32':
            sbi = (instr & 0xf8000000) >> 25
            shamt = (instr & 0x1f00000) >> 20
        elif self.arch == 'rv64':
            sbi = (instr & 0xfc000000) >> 26
            shamt = (instr & 0x3f00000) >> 20

        instrObj.rd = rd
        instrObj.rs1 = rs1
        instrObj.imm = imm_val

        if funct3 == 0b000:
            instrObj.instr_name = 'addi'
        if funct3 == 0b010:
            instrObj.instr_name = 'slti'
        if funct3 == 0b011:
            instrObj.instr_name = 'sltiu'
            instrObj.imm = imm
        if funct3 == 0b100:
            instrObj.instr_name = 'xori'
        if funct3 == 0b110:
            instrObj.instr_name = 'ori'
        if funct3 == 0b111:
            instrObj.instr_name = 'andi'

        if funct3 == 0b001:
            if funct7 == 0b0000100:
                if self.arch == 'rv32':
                   instrObj.instr_name = 'zip'
                   instrObj.rs1= rs1
                   instrObj.rd = rd
            elif sbi == 0b0100100 or  sbi == 0b010010:
                instrObj.rs1 = rs1
                instrObj.rd = rd
                instrObj.shamt = shamt
                instrObj.instr_name = 'bclri'
            elif sbi == 0b0110100 or  sbi == 0b011010:
                instrObj.rs1 = rs1
                instrObj.rd = rd
                instrObj.shamt = shamt
                instrObj.instr_name = 'binvi'
            elif sbi == 0b0010100 or  sbi == 0b001010:
                instrObj.rs1 = rs1
                instrObj.rd = rd
                instrObj.shamt = shamt
                instrObj.instr_name = 'bseti'
            elif funct6 == 0b000010:
                imm = (instr & 0x03F00000)>>20
                instrObj.rs1 = rs1
                instrObj.rd = rd
                instrObj.imm = imm
                instrObj.instr_name = 'shfli'
            elif funct4 == 0b01000:
                if rs2[0] == 0b01000:
                    instrObj.instr_name = 'sm3p0'
                    instrObj.rs1 = rs1
                    instrObj.rd = rd
                    instrObj.imm = bs
                elif rs2[0] == 0b01001:
                    instrObj.instr_name = 'sm3p1'
                    instrObj.rs1 = rs1
                    instrObj.rd = rd
                    instrObj.imm = bs
                elif rs2[0] == 0b00000:
                    instrObj.instr_name = 'sha256sum0'
                    instrObj.rs1 = rs1
                    instrObj.rd = rd
                    instrObj.imm = bs
                elif rs2[0] == 0b00001:
                    instrObj.instr_name = 'sha256sum1'
                    instrObj.rs1 = rs1
                    instrObj.rd = rd
                    instrObj.imm = bs
                elif rs2[0] == 0b00010:
                    instrObj.instr_name = 'sha256sig0'
                    instrObj.rs1 = rs1
                    instrObj.rd = rd
                    instrObj.imm = bs
                elif rs2[0] == 0b00011:
                    instrObj.instr_name = 'sha256sig1'
                    instrObj.rs1 = rs1
                    instrObj.rd = rd
                    instrObj.imm = bs
                elif rs2[0] == 0b00100:
                    instrObj.instr_name = 'sha512sum0'
                    instrObj.rs1 = rs1
                    instrObj.rd = rd
                    instrObj.imm = bs
                elif rs2[0] == 0b00101:
                    instrObj.instr_name = 'sha512sum1'
                    instrObj.rs1 = rs1
                    instrObj.rd = rd
                    instrObj.imm = bs
                elif rs2[0] == 0b00110:
                    instrObj.instr_name = 'sha512sig0'
                    instrObj.rs1 = rs1
                    instrObj.rd = rd
                    instrObj.imm = bs
                elif rs2[0] == 0b00111:
                    instrObj.instr_name = 'sha512sig1'
                    instrObj.rs1 = rs1
                    instrObj.rd = rd
                    instrObj.imm = bs
            elif funct4 == 0b11000:
                rs2_bit24 = (instr & 0x01000000) >> 24
                if rs2_bit24 == 0b1:
                    imm = (instr & 0x00f00000) >> 20
                    instrObj.instr_name = 'aes64ks1i'
                    instrObj.rs1 = rs1
                    instrObj.rd = rd
                    instrObj.imm = imm
                else:
                    instrObj.instr_name = 'aes64im'
                    instrObj.rs1 = rs1
                    instrObj.rd = rd
                    instrObj.imm = bs
            elif funct4 == 0b10000:
                if rs2[0] == 0b00000:
                    instrObj.instr_name = 'clz'
                    instrObj.rs1 = rs1
                    instrObj.rd = rd
                elif rs2[0] == 0b00010:
                    instrObj.instr_name = 'cpop'
                    instrObj.rs1 = rs1
                    instrObj.rd = rd
                elif rs2[0] == 0b00001:
                    instrObj.instr_name = 'ctz'
                    instrObj.rs1 = rs1
                    instrObj.rd = rd
                elif rs2[0] == 0b00100:
                    instrObj.instr_name = 'sext.b'
                    instrObj.rs1 = rs1
                    instrObj.rd = rd
                elif rs2[0] == 0b00101:
                    instrObj.instr_name = 'sext.h'
                    instrObj.rs1 = rs1
                    instrObj.rd = rd

            else:
                instrObj.instr_name = 'slli'
                instrObj.imm = None
                if self.arch == 'rv32':
                        shamt = imm & 0x01f
                elif self.arch == 'rv64':
                        shamt = imm & 0x03f
                instrObj.shamt = shamt

        if funct3 == 0b101:
            if funct7 == 0b0000100:
                if self.arch == 'rv32':
                    instrObj.instr_name = 'unzip'
                    instrObj.rs1= rs1
                    instrObj.rd = rd
            elif (instr >> 20) == 0x6B8 or (instr >> 20) == 0x698 :
                instrObj.instr_name = 'rev8'
                instrObj.rs1 = rs1
                instrObj.rd = rd
            elif (instr >> 20) == 0x687:
                instrObj.instr_name = 'brev8'
                instrObj.rs1 = rs1
                instrObj.rd = rd
            elif (instr >> 20) == 0x287:
                instrObj.instr_name = 'orc.b'
                instrObj.rs1 = rs1
                instrObj.rd = rd
            elif sbi == 0b0100100 or  sbi == 0b010010:
                instrObj.rs1 = rs1
                instrObj.rd = rd
                instrObj.shamt = shamt
                instrObj.instr_name = 'bexti'
            elif funct6 == 0b000010:
                imm = (instr & 0x03F00000)>>20
                instrObj.rs1 = rs1
                instrObj.rd = rd
                instrObj.imm = imm
                instrObj.instr_name = 'unshfli'
            elif self.arch == 'rv32' and (imm>>5) == 0b0110000:
                instrObj.imm = imm & 0x1f
                instrObj.shamt = imm & 0x1f
                instrObj.instr_name = 'rori'
                instrObj.rs1 = rs1
                instrObj.rd = rd
            elif self.arch == 'rv64' and (imm>>6) == 0b011000:
                instrObj.imm = imm & 0x3f
                instrObj.shamt = imm & 0x3f
                instrObj.instr_name = 'rori'
                instrObj.rs1 = rs1
                instrObj.rd = rd
            elif rs3[0] == 0b01101:
                imm = ((instr & 0x07f00000) >> 20)
                instrObj.instr_name = 'grevi'
                instrObj.rs1 = rs1
                instrObj.rd = rd
                instrObj.imm = imm
            else:
                instrObj.imm = None
                if self.arch == 'rv32':
                    shamt = imm & 0x01f
                elif self.arch == 'rv64':
                    shamt = imm & 0x03f
                instrObj.shamt = shamt
                rtype_bit = (imm >> 10) & 0x1
                if rtype_bit == 1:
                    instrObj.instr_name = 'srai'
                if rtype_bit == 0:
                    instrObj.instr_name = 'srli'

        return instrObj

    # Put the following function in internaldecoder.py
    def rvp_ops(self, instrObj):

        instr = instrObj.instr
        func3 = (instr & self.FUNCT3_MASK) >> 12
        instrObj.is_rvp = True
        if func3 == 0x0:
            self.rvp_func3_0x0_ops(instrObj)
        elif func3 == 0x1:
            self.rvp_func3_0x1_ops(instrObj)
        elif func3 == 0x2:
            self.rvp_func3_0x2_ops(instrObj)
        elif func3 == 0x3:
            self.rvp_func3_0x3_ops(instrObj)

        if self.arch == 'rv32':
            if instrObj.instr_name in self.rvp_rs1_is_64bit_set:
                instrObj.rs1_nregs = 2
            if instrObj.instr_name in self.rvp_rs2_is_64bit_set:
                instrObj.rs2_nregs = 2
            if instrObj.instr_name in self.rvp_rd_is_64bit_set:
                instrObj.rd_nregs = 2

        return instrObj


    def rvp_func3_0x0_ops(self, instrObj):
        '''
        Decoder for
        mask = 0b11111111111100000111000001111111:
               clrs8 clrs16 clrs32 clo8 clo16 clo32 clz8 clz16 clz32 kabs8 kabs16 kabsw sunpkd810 sunpkd820 sunpkd830 sunpkd831 sunpkd832 swap8 zunpkd810 zunpkd820 zunpkd830 zunpkd831 zunpkd832 kabs32
        mask = 0b11111110000000000111000001111111:
               add8 add16 ave bitrev cmpeq8 cmpeq16 cras16 crsa16 kadd8 kadd16 kcras16 kcrsa16 khm8 khmx8 khm16 khmx16 ksll8 ksll16 kslra8 kslra8.u kslra16 kslra16.u ksub8 ksub16 maxw minw pbsad pbsada radd8 radd16 rcras16 rcrsa16 rsub8 rsub16 scmple8 scmple16 scmplt8 scmplt16 sll8 sll16 smaqa smaqa.su smax8 smax16 smin8 smin16 smul8 smulx8 smul16 smulx16 sra8 sra8.u sra16 sra16.u srl8 srl8.u srl16 srl16.u sub8 sub16 ucmple8 ucmple16 ucmplt8 ucmplt16 ukadd8 ukadd16 ukcras16 ukcrsa16 uksub8 uksub16 umaqa umax8 umax16 umin8 umin16 umul8 umulx8 umul16 umulx16 uradd8 uradd16 urcras16 urcrsa16 ursub8 ursub16 wext
        mask = 0b11111111100000000111000001111111:
               insb kslli8 sclip8 slli8 srai8 srai8.u srli8 srli8.u uclip8
        mask = 0b11111111000000000111000001111111:
               kslli16 sclip16 slli16 srai16 srai16.u srli16 srli16.u uclip16
        mask = 0b11111110000000000111000001111111:
               sclip32 uclip32 wexti
        mask = 0b11111100000000000111000001111111:
               bitrevi
        '''

        instr = instrObj.instr
        # mask = 0b11111111111100000111000001111111
        # rvp_op  rd, rs1
        func = (instr & 0xfff0707f)
        if func in self.rvp_dict_0:
            instrObj.instr_name = self.rvp_dict_0[func]
            instrObj.rd = ((instr & self.RD_MASK) >> 7, 'x')
            instrObj.rs1 = ((instr & self.RS1_MASK) >> 15, 'x')
            return instrObj

        # mask = 0b11111110000000000111000001111111
        # rvp_op  rd, rs1, rs2
        func = (instr & 0xfe00707f)
        if func in self.rvp_dict_1:
            instrObj.instr_name = self.rvp_dict_1[func]
            instrObj.rd = ((instr & self.RD_MASK) >> 7, 'x')
            instrObj.rs1 = ((instr & self.RS1_MASK) >> 15, 'x')
            instrObj.rs2 = ((instr & self.RS2_MASK) >> 20, 'x')
            return instrObj

        # mask = 0b11111111100000000111000001111111
        # rvp_op  rd, rs1, imm3u
        func = (instr & 0xff80707f)
        if func in self.rvp_dict_2:
            instrObj.instr_name = self.rvp_dict_2[func]
            instrObj.rd = ((instr & self.RD_MASK) >> 7, 'x')
            instrObj.rs1 = ((instr & self.RS1_MASK) >> 15, 'x')
            instrObj.imm = (instr >> 20) & 0x7
            return instrObj

        # mask = 0b11111111000000000111000001111111
        # rvp_op  rd, rs1, imm4u
        func = (instr & 0xff00707f)
        if func in self.rvp_dict_3:
            instrObj.instr_name = self.rvp_dict_3[func]
            instrObj.rd = ((instr & self.RD_MASK) >> 7, 'x')
            instrObj.rs1 = ((instr & self.RS1_MASK) >> 15, 'x')
            instrObj.imm = (instr >> 20) & 0xf
            return instrObj

        # mask = 0b11111110000000000111000001111111
        # rvp_op  rd, rs1, imm5u
        func = (instr & 0xfe00707f)
        if func in self.rvp_dict_4:
            instrObj.instr_name = self.rvp_dict_4[func]
            instrObj.rd = ((instr & self.RD_MASK) >> 7, 'x')
            instrObj.rs1 = ((instr & self.RS1_MASK) >> 15, 'x')
            instrObj.imm = (instr >> 20) & 0x1f
            return instrObj

        # mask = 0b11111100000000000111000001111111
        # rvp_op  rd, rs1, imm6u
        func = (instr & 0xfc00707f)
        if func in self.rvp_dict_5:
            instrObj.instr_name = self.rvp_dict_5[func]
            instrObj.rd = ((instr & self.RD_MASK) >> 7, 'x')
            instrObj.rs1 = ((instr & self.RS1_MASK) >> 15, 'x')
            instrObj.imm = (instr >> 20) & 0x3f
            return instrObj

        return instrObj

    def rvp_func3_0x1_ops(self, instrObj):
        '''
        Decoder for
        mask = 0b11111110000000000111000001111111:
               add64 kadd64 kaddh kaddw kdmbb kdmbt kdmtt kdmabb kdmabt kdmatt khmbb khmbt khmtt kmabb kmabt kmatt kmada kmaxda kmads kmadrs kmaxds kmar64 kmda kmxda kmmac kmmac.u kmmawb kmmawb.u kmmawb2 kmmawb2.u kmmawt kmmawt.u kmmawt2 kmmawt2.u kmmsb kmmsb.u kmmwb2 kmmwb2.u kmmwt2 kmmwt2.u kmsda kmsxda kmsr64 ksllw kslraw kslraw.u ksub64 ksubh ksubw kwmmul kwmmul.u maddr32 msubr32 mulr64 mulsr64 pkbb16 pkbt16 pktt16 pktb16 radd64 raddw rsub64 rsubw smal smalbb smalbt smaltt smalda smalxda smalds smaldrs smalxds smar64 smbb16 smbt16 smtt16 smds smdrs smxds smmul smmul.u smmwb smmwb.u smmwt smmwt.u smslda smslxda smsr64 sra.u sub64 ukadd64 ukaddh ukaddw ukmar64 ukmsr64 uksub64 uksubh uksubw umar64 umsr64 uradd64 uraddw ursub64 ursubw kdmbb16 kdmbt16 kdmtt16 kdmabb16 kdmabt16 kdmatt16 khmbb16 khmbt16 khmtt16
        mask = 0b11111110000000000111000001111111:
               kslliw sraiw.u
        mask = 0b11111100000000000111000001111111:
               srai.u
        '''

        instr = instrObj.instr
        # mask = 0b11111110000000000111000001111111
        # rvp_op  rd, rs1, rs2
        func = (instr & 0xfe00707f)
        if func in self.rvp_dict_6:
            instrObj.instr_name = self.rvp_dict_6[func]
            instrObj.rd = ((instr & self.RD_MASK) >> 7, 'x')
            instrObj.rs1 = ((instr & self.RS1_MASK) >> 15, 'x')
            instrObj.rs2 = ((instr & self.RS2_MASK) >> 20, 'x')
            return instrObj

        # mask = 0b11111110000000000111000001111111
        # rvp_op  rd, rs1, imm5u
        func = (instr & 0xfe00707f)
        if func in self.rvp_dict_7:
            instrObj.instr_name = self.rvp_dict_7[func]
            instrObj.rd = ((instr & self.RD_MASK) >> 7, 'x')
            instrObj.rs1 = ((instr & self.RS1_MASK) >> 15, 'x')
            instrObj.imm = (instr >> 20) & 0x1f
            return instrObj

        # mask = 0b11111100000000000111000001111111
        # rvp_op  rd, rs1, imm6u
        func = (instr & 0xfc00707f)
        if func in self.rvp_dict_8:
            instrObj.instr_name = self.rvp_dict_8[func]
            instrObj.rd = ((instr & self.RD_MASK) >> 7, 'x')
            instrObj.rs1 = ((instr & self.RS1_MASK) >> 15, 'x')
            instrObj.imm = (instr >> 20) & 0x3f
            return instrObj

        return instrObj

    def rvp_func3_0x2_ops(self, instrObj):
        '''
        Decoder for
        mask = 0b11111110000000000111000001111111:
               kstas16 kstsa16 rstas16 rstsa16 stas16 stsa16 ukstas16 ukstsa16 urstas16 urstsa16 add32 cras32 crsa32 kadd32 kcras32 kcrsa32 kmabb32 kmabt32 kmatt32 kmaxda32 kmda32 kmxda32 kmads32 kmadrs32 kmaxds32 kmsda32 kmsxda32 ksll32 kslra32 kslra32.u kstas32 kstsa32 ksub32 pkbb32 pkbt32 pktt32 pktb32 radd32 rcras32 rcrsa32 rstas32 rstsa32 rsub32 sll32 smax32 smbt32 smtt32 smds32 smdrs32 smxds32 smin32 sra32 sra32.u srl32 srl32.u stas32 stsa32 sub32 ukadd32 ukcras32 ukcrsa32 ukstas32 ukstsa32 uksub32 umax32 umin32 uradd32 urcras32 urcrsa32 urstas32 urstsa32 ursub32
        mask = 0b11111110000000000111000001111111:
               kslli32 slli32 srai32 srai32.u srli32 srli32.u
        '''

        instr = instrObj.instr
        # mask = 0b11111110000000000111000001111111
        # rvp_op  rd, rs1, rs2
        func = (instr & 0xfe00707f)
        if func in self.rvp_dict_9:
            instrObj.instr_name = self.rvp_dict_9[func]
            instrObj.rd = ((instr & self.RD_MASK) >> 7, 'x')
            instrObj.rs1 = ((instr & self.RS1_MASK) >> 15, 'x')
            instrObj.rs2 = ((instr & self.RS2_MASK) >> 20, 'x')
            return instrObj

        # mask = 0b11111110000000000111000001111111
        # rvp_op  rd, rs1, imm5
        func = (instr & 0xfe00707f)
        if func in self.rvp_dict_10:
            instrObj.instr_name = self.rvp_dict_10[func]
            instrObj.rd = ((instr & self.RD_MASK) >> 7, 'x')
            instrObj.rs1 = ((instr & self.RS1_MASK) >> 15, 'x')
            instrObj.imm = (instr >> 20) & 0x1f
            return instrObj

        return instrObj

    def rvp_func3_0x3_ops(self, instrObj):
        '''
        Decoder for
        mask = 0b00000110000000000111000001111111:
               bpick
        '''

        instr = instrObj.instr
        # mask = 0b00000110000000000111000001111111
        # rvp_op  rd, rs1, rs2, rs3
        func = (instr & 0x0600707f)
        if func in self.rvp_dict_11:
            instrObj.instr_name = self.rvp_dict_11[func]
            instrObj.rd = ((instr & self.RD_MASK) >> 7, 'x')
            instrObj.rs1 = ((instr & self.RS1_MASK) >> 15, 'x')
            instrObj.rs2 = ((instr & self.RS2_MASK) >> 20, 'x')
            instrObj.rs3 = ((instr & self.RS3_MASK) >> 27, 'x')
            return instrObj

        return instrObj

    def arithm_ops(self, instrObj):
        instr = instrObj.instr
        funct3 = (instr & self.FUNCT3_MASK) >> 12
        rd = ((instr & self.RD_MASK) >> 7, 'x')
        rs1 = ((instr & self.RS1_MASK) >> 15, 'x')
        rs2 = ((instr & self.RS2_MASK) >> 20, 'x')

        instrObj.rd = rd
        instrObj.rs1 = rs1
        instrObj.rs2 = rs2

        if funct3 == 0b000:
            instrObj.instr_name = 'mul'
        if funct3 == 0b001:
            instrObj.instr_name = 'mulh'
        if funct3 == 0b010:
            instrObj.instr_name = 'mulhsu'
        if funct3 == 0b011:
            instrObj.instr_name = 'mulhu'
        if funct3 == 0b100:
            instrObj.instr_name = 'div'
        if funct3 == 0b101:
            instrObj.instr_name = 'divu'
        if funct3 == 0b110:
            instrObj.instr_name = 'rem'
        if funct3 == 0b111:
            instrObj.instr_name = 'remu'

        return instrObj

    def arith_ops(self, instrObj):

        instr = instrObj.instr
            # Test for RV32M ops
        funct7 = (instr >> 25)
        if funct7 == 0b0000001:
            return self.arithm_ops(instrObj)

        # Test for RV32I ops
        funct3 = (instr & self.FUNCT3_MASK) >> 12
        funct4 = (instr & self.FUNCT4_MASK) >> 25
        rd = ((instr & self.RD_MASK) >> 7, 'x')
        rs1 = ((instr & self.RS1_MASK) >> 15, 'x')
        rs2 = ((instr & self.RS2_MASK) >> 20, 'x')
        bs = (instr & self.BS_MASK) >> 30

        instrObj.rd = rd
        instrObj.rs1 = rs1
        instrObj.rs2 = rs2

        if funct3 == 0b000:
            if funct7 == 0b0000000:
                instrObj.instr_name = 'add'
            if funct7 == 0b0100000:
                instrObj.instr_name = 'sub'
            if funct4 == 0b01000:
                instrObj.instr_name = 'sha512sum0r'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
                instrObj.imm = bs
            elif funct4 == 0b01001:
                instrObj.instr_name = 'sha512sum1r'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
                instrObj.imm = bs
            elif funct4 == 0b01010:
                instrObj.instr_name = 'sha512sig0l'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
                instrObj.imm = bs
            elif funct4 == 0b01110:
                instrObj.instr_name = 'sha512sig0h'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
                instrObj.imm = bs
            elif funct4 == 0b01011:
                instrObj.instr_name = 'sha512sig1l'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
                instrObj.imm = bs
            elif funct4 == 0b01111:
                instrObj.instr_name = 'sha512sig1h'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
                instrObj.imm = bs
            elif funct4 == 0b11000:
                instrObj.instr_name = 'sm4ed'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
                instrObj.imm = bs
            elif funct4 == 0b11010:
                instrObj.instr_name = 'sm4ks'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
                instrObj.imm = bs
            elif funct4 == 0b10011:
                instrObj.instr_name = 'aes32esmi'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
                instrObj.imm = bs
            elif funct4 == 0b11011:
                instrObj.instr_name = 'aes64esm'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
                instrObj.imm = bs
            elif funct4 == 0b10001:
                instrObj.instr_name = 'aes32esi'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
                instrObj.imm = bs
            elif funct4 == 0b11001:
                instrObj.instr_name = 'aes64es'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
                instrObj.imm = bs
            elif funct4 == 0b10111:
                instrObj.instr_name = 'aes32dsmi'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
                instrObj.imm = bs
            elif funct4 == 0b11111:
                    if bs == 0b00:
                        instrObj.instr_name = 'aes64dsm'
                        instrObj.rs1 = rs1
                        instrObj.rs2 = rs2
                        instrObj.rd = rd
                        instrObj.imm = bs
                    elif bs == 0b01:
                        instrObj.instr_name = 'aes64ks2'
                        instrObj.rs1 = rs1
                        instrObj.rs2 = rs2
                        instrObj.rd = rd
                        instrObj.imm = bs
            elif funct4 == 0b10101:
                instrObj.instr_name = 'aes32dsi'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
                instrObj.imm = bs
            elif funct4 == 0b11101:
                instrObj.instr_name = 'aes64ds'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
                instrObj.imm = bs

        if funct3 == 0b001:
            if funct7 == 0b0110000:
                instrObj.instr_name = 'rol'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
            elif funct7 == 0b0000101:
                instrObj.instr_name = 'clmul'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
            elif funct7 == 0b0100100:
                instrObj.instr_name = 'bclr'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
            elif funct7 == 0b0110100:
                instrObj.instr_name = 'binv'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
            elif funct7 == 0b0010100:
                instrObj.instr_name = 'bset'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
            else:
                instrObj.instr_name = 'sll'

        if funct3 == 0b010:
            if funct7 == 0b0010100:
                instrObj.instr_name = 'xperm.n'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
            if funct7 == 0b0010000:
                instrObj.instr_name = 'sh1add'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
            elif funct7 == 0b0000101:
                instrObj.instr_name = 'clmulr'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
            elif funct7 == 0b0010100:
                instrObj.instr_name = 'xperm4'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
            else:
                instrObj.instr_name = 'slt'

        if funct3 == 0b011:
            if funct7 == 0b0000101:
                instrObj.instr_name = 'clmulh'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
            else:
                instrObj.instr_name = 'sltu'

        if funct3 == 0b100:
            if funct7 == 0b0100000:
                instrObj.instr_name = 'xnor'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
            elif funct7 == 0b0000100:
                instrObj.instr_name = 'pack'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
            elif funct7 == 0b0000101:
                instrObj.instr_name = 'min'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
            elif funct7 == 0b0010000:
                instrObj.instr_name = 'sh2add'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
            elif funct7 == 0b0010100:
                instrObj.instr_name = 'xperm8'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd

            # elif funct7 == 0b0100100:
            #     instrObj.instr_name = 'packu'
            #     instrObj.rs1 = rs1
            #     instrObj.rs2 = rs2
            #     instrObj.rd = rd
            elif funct7 == 0b0010100:
                instrObj.instr_name = 'xperm.b'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
            else:
                instrObj.instr_name = 'xor'

        if funct3 == 0b101:
            if funct7 == 0b0000000:
                instrObj.instr_name = 'srl'
            elif funct7 == 0b0100000:
                instrObj.instr_name = 'sra'
            elif funct7 == 0b0110000:
                instrObj.instr_name = 'ror'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
            elif funct7 == 0b0000101:
                instrObj.instr_name = 'minu'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
            elif funct7 == 0b0100100:
                instrObj.instr_name = 'bext'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
            elif funct7 == 0b0000111:
                instrObj.instr_name = 'czero.eqz'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd

        if funct3 == 0b110:
            if funct7 == 0b0100000:
                instrObj.instr_name = 'orn'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
            elif funct7 == 0b0010000:
                instrObj.instr_name = 'sh3add'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
            elif funct7 == 0b0000101:
                instrObj.instr_name = 'max'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
            else:
                instrObj.instr_name = 'or'

        if funct3 == 0b111:
            if funct7 == 0b0100000:
                instrObj.instr_name = 'andn'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
            elif funct7 == 0b0000100:
                instrObj.instr_name = 'packh'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
            elif funct7 == 0b0000101:
                instrObj.instr_name = 'maxu'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
            elif funct7 == 0b0000111:
                instrObj.instr_name = 'czero.nez'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
            else:
                instrObj.instr_name = 'and'

        return instrObj

    def mem_ops(self, instrObj):
        instr = instrObj.instr
        func3 = (instr & self.FUNCT3_MASK) >> 12
        if func3 == 0b000 or func3 == 0b001:
            return self.fence_ops(instrObj)
        elif func3 == 0b010 :
            return self.cbo_ops(instrObj)

    def fence_ops(self, instrObj):
        instr = instrObj.instr
        funct3 = (instr & self.FUNCT3_MASK) >> 12

        pred = (instr >> 20) & 0x0000000f
        succ = (instr >> 24) & 0x0000000f

        if funct3 == 0b000:
            instrObj.succ = succ
            instrObj.pred = pred
            instrObj.instr_name = 'fence'
        if funct3 == 0b001:
            instrObj.instr_name = 'fence.i'

        return instrObj

    def cbo_ops(self, instrObj):
        instr = instrObj.instr
        func = (instr) >> 20
        instrObj.rs1 = ((instr & self.RS1_MASK) >> 15, 'x')
        instrObj.imm = 0
        if func == 0b1:
            instrObj.instr_name = "cbo.clean"
        elif func == 0b10:
            instrObj.instr_name = "cbo.flush"
        elif func == 0b0:
            instrObj.instr_name = "cbo.inval"
        elif func == 0b100:
            instrObj.instr_name = "cbo.zero"
        return instrObj

    def prefetch_ops(self, instrObj):
        instr = instrObj.instr
        func = (instr & self.RS2_MASK) >> 20
        instrObj.rs1 = ((instr & self.RS1_MASK) >> 15, 'x')

        imm_11_5 = (instr & 0xfe000000) >> 20
        instrObj.imm = self.twos_comp(imm_11_5, 12)

        if func == 0b0:
            instrObj.instr_name = "prefetch.i"
        elif func == 0b1:
            instrObj.instr_name = "prefetch.r"
        elif func == 0b11:
            instrObj.instr_name = "prefetch.w"
        return instrObj

    def priviledged_ops(self, instrObj):
        instr = instrObj.instr
        funct3 = (instr & self.FUNCT3_MASK) >> 12
        rs1 = ((instr & self.RS1_MASK) >> 15, 'x')
        rs2 = ((instr & self.RS2_MASK) >> 20, 'x')

        # Test for ecall, ebreak and sfence.vma ops
        if funct3 == 0b000:
            etype = (instr >> 20) & 0x0fff
            funct7 = (instr >> 25) & 0x7f
            if etype == 0b0:
                instrObj.instr_name = 'ecall'
                return instrObj
            if etype == 0b1:
                instrObj.instr_name = 'ebreak'
                return instrObj
            if funct7 == 0b0001001:
                instrObj.instr_name = 'sfence.vma'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                return instrObj
            

        MOP_R_MASK = 0xB3C00000
        MOP_RR_MASK = 0xB2000000
        mop_r_n = ((instr & 0x40000000) >> 26) + ((instr & 0xC000000) >> 24) + ((instr & 0x300000) >> 20)
        mop_rr_n = ((instr & 0x40000000) >> 28) + ((instr & 0xC000000) >> 26)

        # Test for csr ops
        rd = ((instr & self.RD_MASK) >> 7, 'x')
        rs1 = ((instr & self.RS1_MASK) >> 15, 'x')
        rs2 = ((instr & self.RS2_MASK) >> 20, 'x')
        csr = (instr >> 20)

        instrObj.rd = rd
        instrObj.rs1 = rs1
        instrObj.csr = csr

        if funct3 == 0b001:
            instrObj.instr_name = 'csrrw'
        if funct3 == 0b010:
            instrObj.instr_name = 'csrrs'
        if funct3 == 0b011:
            instrObj.instr_name = 'csrrc'
        if funct3 == 0b100:
            if (instr & MOP_R_MASK == 0x81C00000):
                for n in range(32):
                    if (mop_r_n == n):
                        instrObj.instr_name = 'mop.r.' + str(n)
                        instrObj.csr = None
                        break     
            elif (instr & MOP_RR_MASK == 0x82000000):
                for n in range(8):
                    if (mop_rr_n == n):
                        instrObj.instr_name = 'mop.rr.' + str(n)
                        instrObj.rs2 = rs2
                        instrObj.csr = None
                        break
        if funct3 == 0b101:
            instrObj.instr_name = 'csrrwi'
            instrObj.rs1 = None
            instrObj.zimm = rs1[0]
        if funct3 == 0b110:
            instrObj.instr_name = 'csrrsi'
            instrObj.rs1 = None
            instrObj.zimm = rs1[0]
        if funct3 == 0b111:
            instrObj.instr_name = 'csrrci'
            instrObj.rs1 = None
            instrObj.zimm = rs1[0]

        return instrObj

    def rv64i_arithi_ops(self, instrObj):

        instr = instrObj.instr

        funct3 = (instr & self.FUNCT3_MASK) >> 12
        funct7 = (instr >> 25)
        funct7a = (instr >> 26) # for slli.uw
        rd = ((instr & self.RD_MASK) >> 7, 'x')
        rs1 = ((instr & self.RS1_MASK) >> 15, 'x')
        imm = ((instr & self.RS2_MASK) >> 20)

        instrObj.rd = rd
        instrObj.rs1 = rs1

        if funct3 == 0b000:
            imm = self.twos_comp((instr >> 20) & 0x00000FFF, 12)
            instrObj.imm = imm
            instrObj.instr_name = 'addiw'
            return instrObj

        shamt = (instr >> 20) & 0x0000001f
        instrObj.shamt = shamt

        if funct3 == 0b001:
            if funct7a == 0b000010:
                print("instr is slli.uw")
                instrObj.instr_name = 'slli.uw'
                instrObj.rs1 = rs1
                instrObj.rd = rd
                instrObj.shamt = imm
            elif funct7 == 0b0110000:
                if imm == 0b00000:
                    instrObj.instr_name = 'clzw'
                    instrObj.rs1 = rs1
                    instrObj.rd = rd
                elif imm == 0b00001:
                    instrObj.instr_name = 'ctzw'
                    instrObj.rs1 = rs1
                    instrObj.rd = rd
                elif imm == 0b00010:
                    instrObj.instr_name = 'cpopw'
                    instrObj.rs1 = rs1
                    instrObj.rd = rd
            else:
                instrObj.instr_name = 'slliw'
        elif funct3 == 0b101:
            if funct7 == 0b0110000:
                instrObj.instr_name = 'roriw'
                instrObj.rs1 = rs1
                instrObj.rd = rd
                instrObj.imm = imm
            else:
                rtype_bit = (instr >> 30) & 0x01
                if rtype_bit == 0:
                    instrObj.instr_name = 'srliw'
                if rtype_bit == 1:
                    instrObj.instr_name = 'sraiw'

        return instrObj

    def rv64m_arithm_ops(self, instrObj):
        instr = instrObj.instr
        funct3 = (instr & self.FUNCT3_MASK) >> 12
        rd = ((instr & self.RD_MASK) >> 7, 'x')
        rs1 = ((instr & self.RS1_MASK) >> 15, 'x')
        rs2 = ((instr & self.RS2_MASK) >> 20, 'x')

        instrObj.rd = rd
        instrObj.rs1 = rs1
        instrObj.rs2 = rs2

        if funct3 == 0b000:
            instrObj.instr_name = 'mulw'
        if funct3 == 0b100:
            instrObj.instr_name = 'divw'
        if funct3 == 0b101:
            instrObj.instr_name = 'divuw'
        if funct3 == 0b110:
            instrObj.instr_name = 'remw'
        if funct3 == 0b111:
            instrObj.instr_name = 'remuw'

        return instrObj

    def rv64i_arith_ops(self, instrObj):

        instr = instrObj.instr

        # Test for rv64m ops
        funct7 = (instr >> 25)
        if funct7 == 0b0000001:
            return self.rv64m_arithm_ops(instrObj)

        # Test for RV64I ops
        funct3 = (instr & self.FUNCT3_MASK) >> 12
        rd = ((instr & self.RD_MASK) >> 7, 'x')
        rs1 = ((instr & self.RS1_MASK) >> 15, 'x')
        rs2 = ((instr & self.RS2_MASK) >> 20, 'x')

        instrObj.rd = rd
        instrObj.rs1 = rs1
        instrObj.rs2 = rs2

        if funct3 == 0b000:
            if funct7 == 0b0000000:
                instrObj.instr_name = 'addw'
            if funct7 == 0b0000100:
                instrObj.instr_name = 'add.uw'
            if funct7 == 0b0100000:
                instrObj.instr_name = 'subw'

        if funct3 == 0b001:
            if funct7 == 0b0110000:
                instrObj.instr_name = 'rolw'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
            else:
                instrObj.instr_name = 'sllw'

        if funct3 == 0b010:
            if funct7 == 0b0010000:
                instrObj.instr_name = 'sh1add.uw'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd

        if funct3 == 0b100:
            if funct7 == 0b0000100:
# packw and zext.h have same opcode, func3, funct7 only diffrence is in rs2 value
# for zext.h rs2 is always 0, if packw instruction is used with x0 as rs2
# then cannot distinguish from each other, hence using isa to differentiate.
# zext.h is part of Zbb, packw is part of Zbkb
                instrObj.instr_name = 'packw'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
            elif funct7 == 0b0010000:
                instrObj.instr_name = 'sh2add.uw'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd
            # elif funct7 == 0b0100100:
            #     instrObj.instr_name = 'packuw'
            #     instrObj.rs1 = rs1
            #     instrObj.rs2 = rs2
            #     instrObj.rd = rd

        if funct3 == 0b101:
            if funct7 == 0b0000000:
                instrObj.instr_name = 'srlw'
            elif funct7 == 0b0100000:
                instrObj.instr_name = 'sraw'
            elif funct7 == 0b0110000:
                instrObj.instr_name = 'rorw'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd

        if funct3 == 0b110:
            if funct7 == 0b0010000:
                instrObj.instr_name = 'sh3add.uw'
                instrObj.rs1 = rs1
                instrObj.rs2 = rs2
                instrObj.rd = rd


        return instrObj

    rv32a_instr_names = {
            0b00010: 'lr.w',
            0b00011: 'sc.w',
            0b00001: 'amoswap.w',
            0b00000: 'amoadd.w',
            0b00100: 'amoxor.w',
            0b01100: 'amoand.w',
            0b01000: 'amoor.w',
            0b10000: 'amomin.w',
            0b10100: 'amomax.w',
            0b11000: 'amominu.w',
            0b11100: 'amomaxu.w'
    }

    rv64a_instr_names = {
            0b00010: 'lr.d',
            0b00011: 'sc.d',
            0b00001: 'amoswap.d',
            0b00000: 'amoadd.d',
            0b00100: 'amoxor.d',
            0b01100: 'amoand.d',
            0b01000: 'amoor.d',
            0b10000: 'amomin.d',
            0b10100: 'amomax.d',
            0b11000: 'amominu.d',
            0b11100: 'amomaxu.d'
    }

    zacas_instr_names = {
            0b010: 'zacas.w',
            0b011: 'zacas.d',
            0b100: 'zacas.q',
    }

    def rv64_rv32_atomic_ops(self, instrObj):

        instr = instrObj.instr
        funct5 = (instr >> 27) & 0x0000001f
        funct3 = (instr & self.FUNCT3_MASK) >> 12
        rd = ((instr & self.RD_MASK) >> 7, 'x')
        rs1 = ((instr & self.RS1_MASK) >> 15, 'x')
        rs2 = ((instr & self.RS2_MASK) >> 20, 'x')
        rl = (instr >> 25) & 0x00000001
        aq = (instr >> 26) & 0x00000001

        instrObj.rd = rd
        instrObj.rs1 = rs1
        instrObj.rs2 = rs2

        instrObj.rl = rl
        instrObj.aq = aq

        if funct5 == 0b00101:
            instrObj.instr_name = self.zacas_instr_names[funct3]
        else:
            #RV32A instructions
            if funct3 == 0b010:
                if funct5 == 0b00010:
                    instrObj.rs2 = None
                    instrObj.instr_name = self.rv32a_instr_names[funct5]
                else:
                    instrObj.instr_name = self.rv32a_instr_names[funct5]

                return instrObj

            #RV64A instructions
            if funct3 == 0b011:
                if funct5 == 0b00010:
                    instrObj.rs2 = None
                    instrObj.instr_name = self.rv64a_instr_names[funct5]
                else:
                    instrObj.instr_name = self.rv64a_instr_names[funct5]

        return instrObj

    def flw_fld(self, instrObj):
        instr = instrObj.instr
        rd = ((instr & self.RD_MASK) >> 7, 'f')
        rs1 = ((instr & self.RS1_MASK) >> 15, 'x')
        funct3 = (instr & self.FUNCT3_MASK) >> 12
        imm = self.twos_comp((instr >> 20), 12)

        instrObj.rd = rd
        instrObj.rs1 = rs1
        instrObj.imm = imm

        if funct3 == 0b010:
            instrObj.instr_name = 'flw'
        elif funct3 == 0b011:
            instrObj.instr_name = 'fld'

        return instrObj

    def fsw_fsd(self, instrObj):
        instr = instrObj.instr
        imm_4_0 = (instr & self.RD_MASK) >> 7
        imm_11_5 = (instr >> 25) << 5
        imm = self.twos_comp(imm_4_0 + imm_11_5, 12)
        rs1 = ((instr & self.RS1_MASK) >> 15, 'x')
        rs2 = ((instr & self.RS2_MASK) >> 20, 'f')

        funct3 = (instr & self.FUNCT3_MASK) >> 12

        instrObj.rs1 = rs1
        instrObj.rs2 = rs2
        instrObj.imm = imm

        if funct3 == 0b010:
            instrObj.instr_name = 'fsw'
        elif funct3 == 0b011:
            instrObj.instr_name = 'fsd'

        return instrObj

    def fmadd(self, instrObj):
        instr = instrObj.instr
        rd = ((instr & self.RD_MASK) >> 7, 'f')
        rm = (instr >> 12) & 0x00000007
        rs1 = ((instr & self.RS1_MASK) >> 15, 'f')
        rs2 = ((instr & self.RS2_MASK) >> 20, 'f')
        rs3 = ((instr >> 27), 'f')
        size_bit = (instr >> 25) & 0x00000001

        instrObj.rs1 = rs1
        instrObj.rs2 = rs2
        instrObj.rd = rd

        instrObj.rm = rm
        instrObj.rs3 = rs3

        if size_bit == 0b0:
            instrObj.instr_name = 'fmadd.s'
        elif size_bit == 0b1:
            instrObj.instr_name = 'fmadd.d'

        return instrObj

    def fmsub(self, instrObj):
        instr = instrObj.instr
        rd = ((instr & self.RD_MASK) >> 7, 'f')
        rm = (instr >> 12) & 0x00000007
        rs1 = ((instr & self.RS1_MASK) >> 15, 'f')
        rs2 = ((instr & self.RS2_MASK) >> 20, 'f')
        rs3 = ((instr >> 27), 'f')
        size_bit = (instr >> 25) & 0x00000001

        instrObj.rs1 = rs1
        instrObj.rs2 = rs2
        instrObj.rd = rd

        instrObj.rm = rm
        instrObj.rs3 = rs3

        if size_bit == 0b0:
            instrObj.instr_name = 'fmsub.s'
        elif size_bit == 0b1:
            instrObj.instr_name = 'fmsub.d'

        return instrObj

    def fnmsub(self, instrObj):
        instr = instrObj.instr
        rd = ((instr & self.RD_MASK) >> 7, 'f')
        rm = (instr >> 12) & 0x00000007
        rs1 = ((instr & self.RS1_MASK) >> 15, 'f')
        rs2 = ((instr & self.RS2_MASK) >> 20, 'f')
        rs3 = ((instr >> 27), 'f')
        size_bit = (instr >> 25) & 0x00000001

        instrObj.rs1 = rs1
        instrObj.rs2 = rs2
        instrObj.rd = rd

        instrObj.rm = rm
        instrObj.rs3 = rs3

        if size_bit == 0b0:
            instrObj.instr_name = 'fnmsub.s'
        elif size_bit == 0b1:
            instrObj.instr_name = 'fnmsub.d'

        return instrObj

    def fnmadd(self, instrObj):
        instr = instrObj.instr
        rd = ((instr & self.RD_MASK) >> 7, 'f')
        rm = (instr >> 12) & 0x00000007
        rs1 = ((instr & self.RS1_MASK) >> 15, 'f')
        rs2 = ((instr & self.RS2_MASK) >> 20, 'f')
        rs3 = ((instr >> 27), 'f')
        size_bit = (instr >> 25) & 0x00000001

        instrObj.rs1 = rs1
        instrObj.rs2 = rs2
        instrObj.rd = rd
        instrObj.rm = rm
        instrObj.rs3 = rs3

        if size_bit == 0b0:
            instrObj.instr_name = 'fnmadd.s'
        elif size_bit == 0b1:
            instrObj.instr_name = 'fnmadd.d'

        return instrObj

    def rv32_rv64_float_ops(self, instrObj):
        instr = instrObj.instr
        rd = ((instr & self.RD_MASK) >> 7, 'f')
        rm = (instr >> 12) & 0x00000007
        rs1 = ((instr & self.RS1_MASK) >> 15, 'f')
        rs2 = ((instr & self.RS2_MASK) >> 20, 'f')
        funct7 = (instr >> 25)

        instrObj.rs1 = rs1
        instrObj.rs2 = rs2
        instrObj.rd = rd
        instrObj.rm = rm

        # fadd, fsub, fmul, fdiv
        if funct7 == 0b0000000:
            instrObj.instr_name = 'fadd.s'
        elif funct7 == 0b0000100:
            instrObj.instr_name = 'fsub.s'
        elif funct7 == 0b0001000:
            instrObj.instr_name = 'fmul.s'
        elif funct7 == 0b0001100:
            instrObj.instr_name = 'fdiv.s'
        elif funct7 == 0b0000001:
            instrObj.instr_name = 'fadd.d'
        elif funct7 == 0b0000101:
            instrObj.instr_name = 'fsub.d'
        elif funct7 == 0b0001001:
            instrObj.instr_name = 'fmul.d'
        elif funct7 == 0b0001101:
            instrObj.instr_name = 'fdiv.d'

        # fsqrt
        if funct7 == 0b0101100:
            instrObj.instr_name = 'fsqrt.s'
            instrObj.rs2 = None
            return instrObj
        elif funct7 == 0b0101101:
            instrObj.instr_name = 'fsqrt.d'
            instrObj.rs2 = None
            return instrObj

        # fsgnj, fsgnjn, fsgnjx
        if funct7 == 0b0010000:
            if rm == 0b000:
                instrObj.instr_name = 'fsgnj.s'
                return instrObj
            elif rm == 0b001:
                instrObj.instr_name = 'fsgnjn.s'
                return instrObj
            elif rm == 0b010:
                instrObj.instr_name = 'fsgnjx.s'
                return instrObj
        elif funct7 == 0b0010001:
            if rm == 0b000:
                instrObj.instr_name = 'fsgnj.d'
                return instrObj
            elif rm == 0b001:
                instrObj.instr_name = 'fsgnjn.d'
                return instrObj
            elif rm == 0b010:
                instrObj.instr_name = 'fsgnjx.d'
                return instrObj

        # fmin, fmax, fminm, fmaxm
        if funct7 == 0b0010100:
            if rm == 0b000:
                instrObj.instr_name = 'fmin.s'
                return instrObj
            elif rm == 0b001:
                instrObj.instr_name = 'fmax.s'
                return instrObj
            elif rm == 0b010:
                instrObj.instr_name = 'fminm.s'
                return instrObj
            elif rm == 0b011:
                instrObj.instr_name = 'fmaxm.s'
                return instrObj
        elif funct7 == 0b0010101:
            if rm == 0b000:
                instrObj.instr_name = 'fmin.d'
                return instrObj
            elif rm == 0b001:
                instrObj.instr_name = 'fmax.d'
                return instrObj
            elif rm == 0b010:
                instrObj.instr_name = 'fminm.d'
                return instrObj
            elif rm == 0b011:
                instrObj.instr_name = 'fmaxm.d'
                return instrObj

        # fcvt.w, fcvt.wu, fcvt.l, fcvt.lu
        if funct7 == 0b1100000:
            mode = rs2[0]
            instrObj.rd = (rd[0], 'x')
            instrObj.rs2 = None

            if mode == 0b00000:
                instrObj.instr_name = 'fcvt.w.s'
                return instrObj
            elif mode == 0b00001:
                instrObj.instr_name = 'fcvt.wu.s'
                return instrObj
            elif mode == 0b00010:
                instrObj.instr_name = 'fcvt.l.s'
                return instrObj
            elif mode == 0b00011:
                instrObj.instr_name = 'fcvt.lu.s'
                return instrObj

        # fcvt.s.d, fround.s, froundnx.s, fcvt.d.s, fround.d, froundnx.d
        if funct7 == 0b0100000:
            if rs2[0] == 0b00001:
                instrObj.instr_name = 'fcvt.s.d'
                instrObj.rs2 = None
                return instrObj
            elif rs2[0] == 0b00100:
                instrObj.instr_name = 'fround.s'
                instrObj.rs2 = None
                return instrObj
            elif rs2[0] == 0b00101:
                instrObj.instr_name = 'froundnx.s'
                instrObj.rs2 = None
                return instrObj
        if funct7 == 0b0100001:
            if rs2[0] == 0b00000:
                instrObj.instr_name = 'fcvt.d.s'
                instrObj.rs2 = None
                return instrObj
            elif rs2[0] == 0b00100:
                instrObj.instr_name = 'fround.d'
                instrObj.rs2 = None
                return instrObj
            elif rs2[0] == 0b00101:
                instrObj.instr_name = 'froundnx.d'
                instrObj.rs2 = None
                return instrObj

        # fmv.x.w, fclass.s
        if funct7 == 0b1110000:
            if rm == 0b000:
                instrObj.instr_name = 'fmv.x.w'
                instrObj.rd = (rd[0], 'x')
                instrObj.rs2 = None
                instrObj.rm = None
                return instrObj
            elif rm == 0b001:
                instrObj.instr_name = 'fclass.s'
                instrObj.rd = (rd[0], 'x')
                instrObj.rs2 = None
                instrObj.rm = None
                return instrObj

        # feq, flt, fle, fltq, fleq
        if funct7 == 0b1010000:
            instrObj.rd = (rd[0], 'x')
            if rm == 0b010:
                instrObj.instr_name = 'feq.s'
                return instrObj
            elif rm == 0b001:
                instrObj.instr_name = 'flt.s'
                return instrObj
            elif rm == 0b000:
                instrObj.instr_name = 'fle.s'
                return instrObj
            elif rm == 0b101:
                instrObj.instr_name = 'fltq.s'
                instrObj.rd = (rd[0], 'x')
                return instrObj
            elif rm == 0b100:
                instrObj.instr_name = 'fleq.s'
                instrObj.rd = (rd[0], 'x')
                return instrObj

        if funct7 == 0b1010001:
            instrObj.rd = (rd[0], 'x')
            if rm == 0b010:
                instrObj.instr_name = 'feq.d'
                return instrObj
            elif rm == 0b001:
                instrObj.instr_name = 'flt.d'
                return instrObj
            elif rm == 0b000:
                instrObj.instr_name = 'fle.d'
                return instrObj
            elif rm == 0b101:
                instrObj.instr_name = 'fltq.d'
                instrObj.rd = (rd[0], 'x')
                return instrObj
            elif rm == 0b100:
                instrObj.instr_name = 'fleq.d'
                instrObj.rd = (rd[0], 'x')
                return instrObj

        # fcvt.s.w, fcvt.s.wu, fcvt.s.l, fcvt.s.lu
        if funct7 == 0b1101000:
            mode = rs2[0]
            instrObj.rs1 = (rs1[0], 'x')
            instrObj.rs2 = None
            if mode == 0b00000:
                instrObj.instr_name = 'fcvt.s.w'
                return instrObj
            elif mode == 0b00001:
                instrObj.instr_name = 'fcvt.s.wu'
                return instrObj
            elif mode == 0b00010:
                instrObj.instr_name = 'fcvt.s.l'
                return instrObj
            elif mode == 0b00011:
                instrObj.instr_name = 'fcvt.s.lu'
                return instrObj

        # fmv.w.x, fli.s
        if funct7 == 0b1111000:
            if rs2[0] == 0:
                instrObj.instr_name = 'fmv.w.x'
                instrObj.rs1 = (rs1[0], 'x')
                instrObj.rs2 = None
                return instrObj
            elif rs2[0] == 1:
                instrObj.instr_name = 'fli.s'
                instrObj.rs1 = (rs1[0], 'x')
                instrObj.rs2 = None
                return instrObj

        # fclass.d, fmv.x.d, fmvh.x.d
        if funct7 == 0b1110001:
            if rm == 0b001:
                instrObj.instr_name = 'fclass.d'
                instrObj.rd = (rd[0], 'x')
                instrObj.rs2 = None
                return instrObj
            elif rm == 0b000:
                if rs2[0] == 0:
                    instrObj.instr_name = 'fmv.x.d'
                    instrObj.rd = (rd[0], 'x')
                    instrObj.rs2 = None
                    return instrObj
                elif rs2[0] == 1:
                    instrObj.instr_name = 'fmvh.x.d'
                    instrObj.rd = (rd[0], 'x')
                    instrObj.rs2 = None
                    return instrObj
                
        # fmvp.d.x
        if funct7 == 0b1011001:
            instrObj.instr_name = 'fmvp.d.x'
            instrObj.rs1 = (rs1[0], 'x')
            instrObj.rs2 = (rs2[0], 'x')
            return instrObj

        # fcvt.w.d, fcvt.wu.d, fcvt.d.w, fcvt.d.wu, fcvt.l.d, fcvt.lu.d, fcvtmod.w.d
        if funct7 == 0b1100001:
            mode = rs2[0]
            instrObj.rs2 = None
            instrObj.rd = (rd[0], 'x')
            if mode == 0b00000:
                instrObj.instr_name = 'fcvt.w.d'
                instrObj.rs2 = None
                return instrObj
            elif mode == 0b00001:
                instrObj.instr_name = 'fcvt.wu.d'
                instrObj.rs2 = None
                return instrObj
            elif mode == 0b00010:
                instrObj.instr_name = 'fcvt.l.d'
                instrObj.rs2 = None
                return instrObj
            elif mode == 0b00011:
                instrObj.instr_name = 'fcvt.lu.d'
                instrObj.rs2 = None
                return instrObj
            elif mode == 0b01000:
                instrObj.instr_name = 'fcvtmod.w.d'
                instrObj.rd = (rd[0], 'x')
                instrObj.rs2 = None
                return instrObj
            

        if funct7 == 0b1101001:
            mode = rs2[0]
            instrObj.rs2 = None
            instrObj.rs1 = (rs1[0], 'x')
            if mode == 0b00000:
                instrObj.instr_name = 'fcvt.d.w'
                instrObj.rs2 = None
                return instrObj
            elif mode == 0b00001:
                instrObj.instr_name = 'fcvt.d.wu'
                instrObj.rs2 = None
                return instrObj
            elif mode == 0b00010:
                instrObj.instr_name = 'fcvt.d.l'
                instrObj.rs2 = None
                return instrObj
            elif mode == 0b00011:
                instrObj.instr_name = 'fcvt.d.lu'
                instrObj.rs2 = None
                return instrObj

        if funct7 == 0b1111001:
            if rs2[0] == 0:
                instrObj.instr_name = 'fmv.d.x'
                instrObj.rs1 = (rs1[0], 'x')
                instrObj.rs2 = None
                return instrObj
            elif rs2[0] == 1:
                instrObj.instr_name = 'fli.d'
                instrObj.rs1 = (rs1[0], 'x')
                instrObj.rs2 = None
                return instrObj

        if instrObj.instr_name != 'None':
            return instrObj

    ''' Compressed Instruction Parsing Functions '''
    C_FUNCT3_MASK = 0xe000
    C0_OP2_MASK = 0x0003
    C0_RDPRIME_MASK = 0x001C
    C0_RS2PRIME_MASK = 0x001C
    C0_RS1PRIME_MASK = 0x0380
    C0_UIMM_5_3_MASK = 0x1C00
    C0_UIMM_7_6_MASK = 0x0060
    C0_UIMM_6_MASK = 0x0020
    C0_UIMM_2_MASK = 0x0040

    C1_RD_MASK = 0x0F80
    C1_RDPRIME_MASK = 0x0380
    C1_RS1PRIME_MASK = 0x0380
    C1_RS2PRIME_MASK = 0x001C
    C1_IMM_5_MASK = 0x1000
    C1_IMM_4_0_MASK = 0x007c
    C1_IMM_17_MASK = 0x1000
    C1_IMM_16_12_MASK = 0x007c
    C1_MINOR_OP_MASK = 0x0C00
    C1_MINOR_OP2_MASK = 0x0060
    C1_ZCMOP_MASK = 0x18FC

    def get_bit(self, val, pos):
        return (val & (1 << pos)) >> pos

    def quad0(self, instrObj):
        '''Parse instructions from Quad0 of the Compressed extension in the RISCV-ISA-Standard'''
        instr = instrObj.instr
        funct3 = (self.C_FUNCT3_MASK & instr) >> 13

        # UIMM 7:6:5:3
        uimm_5_3 = (self.C0_UIMM_5_3_MASK & instr) >> 7
        uimm_7_6 = (self.C0_UIMM_7_6_MASK & instr) << 1
        uimm_7_6_5_3 = uimm_5_3 + uimm_7_6

        # UIMM 6:5:3:2
        uimm_2 = (self.C0_UIMM_2_MASK & instr) >> 4
        uimm_6 = (self.C0_UIMM_6_MASK & instr) << 1
        uimm_6_5_3_2 = uimm_6 + uimm_5_3 + uimm_2

        # Registers
        rdprime = (self.C0_RDPRIME_MASK & instr) >> 2
        rs1prime = (self.C0_RS1PRIME_MASK & instr) >> 7
        rs2prime = (self.C0_RS2PRIME_MASK & instr) >> 2

        if funct3 == 0b000:
            nzuimm_3 = self.get_bit(instr, 5)
            nzuimm_2 = self.get_bit(instr, 6)
            nzuimm_9_6 = self.get_bit(instr, 7) + (self.get_bit(instr,8) << 1) + (self.get_bit(instr,9) << 2) + (self.get_bit(instr,10)<<3)
            nzuimm_5_4 = self.get_bit(instr, 11) + (self.get_bit(instr, 12) << 1)
            nzuimm = (nzuimm_2 << 2) + (nzuimm_3 << 3) + (nzuimm_9_6 << 6) + (nzuimm_5_4 << 4)
            if nzuimm == 0 and rdprime == 0:
                instrObj.instr_name = 'c.illegal'
                instrObj.rd = (rdprime, 'x')
            else:
                instrObj.instr_name = 'c.addi4spn'
                instrObj.rd = (8 + rdprime, 'x')
            instrObj.imm = nzuimm
            return instrObj

        elif funct3 == 0b001:
            instrObj.instr_name = 'c.fld'
            instrObj.rd = (8 + rdprime, 'f')
            instrObj.rs1 = (8 + rs1prime, 'x')
            instrObj.imm = uimm_7_6_5_3

        elif funct3 == 0b010:
            instrObj.instr_name = 'c.lw'
            instrObj.rd = (8 + rdprime, 'x')
            instrObj.rs1 = (8 + rs1prime, 'x')
            instrObj.imm = uimm_6_5_3_2

        elif funct3 == 0b011:
            if self.arch == 'rv32':
                instrObj.instr_name = 'c.flw'
                instrObj.rd = (8 + rdprime, 'f')
                instrObj.rs1 = (8 + rs1prime, 'x')
                instrObj.imm = uimm_6_5_3_2
            elif self.arch == 'rv64':
                instrObj.instr_name = 'c.ld'
                instrObj.rd = (8 + rdprime, 'x')
                instrObj.rs1 = (8 + rs1prime, 'x')
                instrObj.imm = uimm_7_6_5_3

        elif funct3 == 0b100:
            if uimm_5_3 == 0:
                instrObj.instr_name = 'c.lbu'
                instrObj.rd = (8 + rdprime, 'x')
                instrObj.rs1 = (8 + rs1prime, 'x')
                instrObj.imm = uimm_7_6 >> 6
            elif uimm_5_3 == 8 and uimm_2 == 4:
                instrObj.instr_name = 'c.lh'
                instrObj.rd = (8 + rdprime, 'x')
                instrObj.rs1 = (8 + rs1prime, 'x')
                instrObj.imm = uimm_6 >> 5
            elif uimm_5_3 == 8 and uimm_2 == 0:
                instrObj.instr_name = 'c.lhu'
                instrObj.rd = (8 + rdprime, 'x')
                instrObj.rs1 = (8 + rs1prime, 'x')
                instrObj.imm = uimm_6 >> 5
            elif uimm_5_3 == 16:
                instrObj.instr_name = 'c.sb'
                instrObj.rs2 = (8 + rs2prime, 'x')
                instrObj.rs1 = (8 + rs1prime, 'x')
                instrObj.imm = uimm_7_6 >> 6
            elif uimm_5_3 == 24 and uimm_2 == 0:
                instrObj.instr_name = 'c.sh'
                instrObj.rs2 = (8 + rs2prime, 'x')
                instrObj.rs1 = (8 + rs1prime, 'x')
                instrObj.imm = uimm_6 >> 5
               
        elif funct3 == 0b101:
            instrObj.instr_name = 'c.fsd'
            instrObj.rs1 = (8 + rs1prime, 'x')
            instrObj.rs2 = (8 + rs2prime, 'f')
            instrObj.imm = uimm_7_6_5_3

        elif funct3 == 0b110:
            instrObj.instr_name = 'c.sw'
            instrObj.rs1 = (8 + rs1prime, 'x')
            instrObj.rs2 = (8 + rs2prime, 'x')
            instrObj.imm = uimm_6_5_3_2

        elif funct3 == 0b111:
            if self.arch == 'rv32':
                instrObj.instr_name = 'c.fsw'
                instrObj.rs1 = (8 + rs1prime, 'x')
                instrObj.rs2 = (8 + rs2prime, 'f')
                instrObj.imm = uimm_6_5_3_2
            elif self.arch == 'rv64':
                instrObj.instr_name = 'c.sd'
                instrObj.rs1 = (8 + rs1prime, 'x')
                instrObj.rs2 = (8 + rs2prime, 'x')
                instrObj.imm = uimm_7_6_5_3

        return instrObj

    def quad1(self, instrObj):
        '''Parse instructions from Quad1 of the Compressed extension in the RISCV-ISA-Standard'''
        instr = instrObj.instr
        funct3 = (self.C_FUNCT3_MASK & instr) >> 13

        # Registers
        rdprime = (self.C1_RDPRIME_MASK & instr) >> 7
        rs1prime = (self.C1_RS1PRIME_MASK & instr) >> 7
        rs2prime = (self.C1_RS2PRIME_MASK & instr) >> 2
        rd = (self.C1_RD_MASK & instr) >> 7
        rs1 = (self.C1_RD_MASK & instr) >> 7

        imm_5 = (self.C1_IMM_5_MASK & instr) >> 7
        imm_4_0 = (self.C1_IMM_4_0_MASK & instr) >> 2
        imm = imm_5 + imm_4_0

        imm_lui = ((self.C1_IMM_17_MASK & instr) >> 12) + ((self.C1_IMM_16_12_MASK & instr)>>2)
        imm_j_5 = self.get_bit(instr, 2) << 5
        imm_j_3_1 = self.get_bit(instr,3) + (self.get_bit(instr, 4) << 1) + (self.get_bit(instr,5) << 2)
        imm_j_7 = self.get_bit(instr,6) << 7
        imm_j_6 = self.get_bit(instr,7) << 6
        imm_j_10 = self.get_bit(instr, 8) << 10
        imm_j_9_8 = self.get_bit(instr, 9) + (self.get_bit(instr,10)<< 1)
        imm_j_4 = self.get_bit(instr,11) << 4
        imm_j_11 = self.get_bit(instr, 12) << 11
        imm_j = imm_j_5 + (imm_j_3_1 << 1) + imm_j_7 + imm_j_6 + imm_j_10 + (imm_j_9_8 << 8) + imm_j_4 + imm_j_11

        imm_b_5 = self.get_bit(instr, 2) << 5
        imm_b_2_1 = self.get_bit(instr, 3) + (self.get_bit(instr,4) << 1)
        imm_b_7_6 = self.get_bit(instr, 5) + (self.get_bit(instr,6) << 1)
        imm_b_4_3 = self.get_bit(instr, 10) + (self.get_bit(instr,11) << 1)
        imm_b_8 = self.get_bit(instr, 12) << 8
        imm_b = imm_b_5 + (imm_b_2_1 << 1) + (imm_b_7_6 << 6) + (imm_b_4_3 << 3) + imm_b_8

        imm_addi_5 = self.get_bit(instr, 2) << 5
        imm_addi_8_7 = (self.get_bit(instr, 3) + (self.get_bit(instr, 4)<< 1) ) << 7
        imm_addi_6 = self.get_bit(instr, 5) << 6
        imm_addi_4 = self.get_bit(instr, 6) << 4
        imm_addi_9 = self.get_bit(instr, 12) << 9
        imm_addi = imm_addi_5 + imm_addi_8_7 + imm_addi_6 + imm_addi_4 + imm_addi_9

        zcmop_n = (instr & 0x0700) >> 8

        op = (self.C1_MINOR_OP_MASK & instr) >> 10
        op2 = (self.C1_MINOR_OP2_MASK & instr) >> 5

        if funct3 == 0:
            instrObj.rs1 = (rs1, 'x')
            instrObj.rd = (rd, 'x')
            instrObj.imm = self.twos_comp(imm, 6)
            if rd == 0:
                instrObj.instr_name = 'c.nop'
            else:
                instrObj.instr_name = 'c.addi'
        elif funct3 == 1:
            if self.arch == 'rv32':
                instrObj.instr_name = 'c.jal'
                instrObj.imm = self.twos_comp(imm_j, 12)
                instrObj.rd = (1, 'x')
            elif rd !=0 :
                instrObj.instr_name = 'c.addiw'
                instrObj.imm = self.twos_comp(imm, 6)
                instrObj.rs1 = (rs1, 'x')
                instrObj.rd = (rd, 'x')
        elif funct3 == 2:
            instrObj.instr_name = 'c.li'
            instrObj.imm = self.twos_comp(imm, 6)
            instrObj.rd = (rd, 'x')
        elif funct3 == 3:
            if rd == 2 and imm_addi != 0:
                instrObj.instr_name = 'c.addi16sp'
                instrObj.rs1 = (2, 'x')
                instrObj.rd = (2, 'x')
                instrObj.imm = self.twos_comp(imm_addi, 10)
            elif rd != 2 and imm_lui !=0:
                instrObj.instr_name = 'c.lui'
                instrObj.imm = imm
                instrObj.rs1 = (rd, 'x')
                instrObj.rd = (rd, 'x')
            elif (instr & self.C1_ZCMOP_MASK == 0x0080):
                if (zcmop_n == 0):
                    instrObj.instr_name = 'c.mop.1'
                elif (zcmop_n == 1):
                    instrObj.instr_name = 'c.mop.3'
                elif (zcmop_n == 2):
                    instrObj.instr_name = 'c.mop.5'
                elif (zcmop_n == 3):
                    instrObj.instr_name = 'c.mop.7'
                elif (zcmop_n == 4):
                    instrObj.instr_name = 'c.mop.9'
                elif (zcmop_n == 5):
                    instrObj.instr_name = 'c.mop.11'
                elif (zcmop_n == 6):
                    instrObj.instr_name = 'c.mop.13'
                elif (zcmop_n == 7):
                    instrObj.instr_name = 'c.mop.15'
        elif funct3 == 4:
            if op == 0 and imm != 0:
                instrObj.instr_name = 'c.srli'
                instrObj.rs1 = (8 + rs1prime, 'x')
                instrObj.rd = (8 + rdprime, 'x')
                instrObj.imm = imm
            elif op == 1 and imm !=0:
                instrObj.instr_name = 'c.srai'
                instrObj.rs1 = (8 + rs1prime, 'x')
                instrObj.rd = (8 + rdprime, 'x')
                instrObj.imm = imm
            elif op == 2:
                instrObj.instr_name = 'c.andi'
                instrObj.rs1 = (8 + rs1prime, 'x')
                instrObj.rd = (8 + rdprime, 'x')
                instrObj.imm = self.twos_comp(imm, 6)
            elif op == 3 and op2 == 0 and imm_5 == 0:
                instrObj.instr_name = 'c.sub'
                instrObj.rs1 = (8 + rs1prime, 'x')
                instrObj.rd = (8 + rdprime, 'x')
                instrObj.rs2 = (8 + rs2prime, 'x')
            elif op == 3 and op2 == 1 and imm_5 == 0:
                instrObj.instr_name = 'c.xor'
                instrObj.rs1 = (8 + rs1prime, 'x')
                instrObj.rd = (8 + rdprime, 'x')
                instrObj.rs2 = (8 + rs2prime, 'x')
            elif op == 3 and op2 == 2 and imm_5 == 0:
                instrObj.instr_name = 'c.or'
                instrObj.rs1 = (8 + rs1prime, 'x')
                instrObj.rd = (8 + rdprime, 'x')
                instrObj.rs2 = (8 + rs2prime, 'x')
            elif op == 3 and op2 == 3 and imm_5 == 0:
                instrObj.instr_name = 'c.and'
                instrObj.rs1 = (8 + rs1prime, 'x')
                instrObj.rd = (8 + rdprime, 'x')
                instrObj.rs2 = (8 + rs2prime, 'x')
            elif op == 3 and op2 == 0 and imm_5 != 0 and self.arch == 'rv64':
                instrObj.instr_name = 'c.subw'
                instrObj.rs1 = (8 + rs1prime, 'x')
                instrObj.rd = (8 + rdprime, 'x')
                instrObj.rs2 = (8 + rs2prime, 'x')
            elif op == 3 and op2 == 1 and imm_5 != 0 and self.arch == 'rv64':
                instrObj.instr_name = 'c.addw'
                instrObj.rs1 = (8 + rs1prime, 'x')
                instrObj.rd = (8 + rdprime, 'x')
                instrObj.rs2 = (8 + rs2prime, 'x')
            elif op == 3 and imm_4_0 == 24 and imm_5 == 32:
                instrObj.instr_name = 'c.zext.b'
                instrObj.rs1 = (8 + rs1prime, 'x')
                instrObj.rd = (8 + rdprime, 'x')
            elif op == 3 and imm_4_0 == 25 and imm_5 == 32:
                instrObj.instr_name = 'c.sext.b'
                instrObj.rs1 = (8 + rs1prime, 'x')
                instrObj.rd = (8 + rdprime, 'x')
            elif op == 3 and imm_4_0 == 26 and imm_5 == 32:
                instrObj.instr_name = 'c.zext.h'
                instrObj.rs1 = (8 + rs1prime, 'x')
                instrObj.rd = (8 + rdprime, 'x')
            elif op == 3 and imm_4_0 == 27 and imm_5 == 32:
                instrObj.instr_name = 'c.sext.h'
                instrObj.rs1 = (8 + rs1prime, 'x')
                instrObj.rd = (8 + rdprime, 'x')
            elif op == 3 and imm_4_0 == 29 and imm_5 == 32:
                instrObj.instr_name = 'c.not'
                instrObj.rs1 = (8 + rs1prime, 'x')
                instrObj.rd = (8 + rdprime, 'x')
            elif op == 3 and op2 == 2 and imm_5 == 32:
                instrObj.instr_name = 'c.mul'
                instrObj.rs1 = (8 + rs1prime, 'x')
                instrObj.rd = (8 + rdprime, 'x')
                instrObj.rs2 = (8 + rs2prime, 'x')
            elif op == 3 and imm_4_0 == 28 and imm_5 == 32 and self.arch == 'rv64':
                instrObj.instr_name = 'c.zext.w'
                instrObj.rs1 = (8 + rs1prime, 'x')
                instrObj.rd = (8 + rdprime, 'x')
        elif funct3 == 5:
            instrObj.instr_name = 'c.j'
            instrObj.rd = (0, 'x')
            instrObj.imm = self.twos_comp(imm_j, 12)
        elif funct3 == 6:
            instrObj.instr_name = 'c.beqz'
            instrObj.rs1 = (8 + rs1prime, 'x')
            instrObj.rs2 = (0 , 'x')
            instrObj.imm = self.twos_comp(imm_b, 9)
        elif funct3 == 7:
            instrObj.instr_name = 'c.bnez'
            instrObj.rs1 = (8 + rs1prime, 'x')
            instrObj.rs2 = (0, 'x')
            instrObj.imm = self.twos_comp(imm_b, 9)
        return instrObj

    C2_RS2_MASK = 0x007C
    C2_RD_MASK = 0x0F80


    def quad2(self, instrObj):
        '''Parse instructions from Quad2 of the Compressed extension in the RISCV-ISA-Standard'''
        instr = instrObj.instr
        funct3 = (self.C_FUNCT3_MASK & instr) >> 13

        imm_5 = self.get_bit(instr, 12) << 5
        imm_4_0 = (instr & 0x007c) >> 2
        imm_4_3 = (instr & 0x0060) >> 2
        imm_4 = self.get_bit(instr, 6) << 4
        imm_4_2 = (instr & 0x0070) >> 2
        imm_8_6 = (instr & 0x001C) << 5
        imm_9_6 = (instr & 0x003C) << 5
        imm_7_6 = (instr & 0x000C) << 4
        imm_8_6 = (instr & 0x001C) << 4

        imm_5_3 = (instr & 0x1c00) >> 7
        imm_s_8_6 = (instr & 0x0380) >> 1
        imm_5_2 = (instr & 0x1E00) >> 7
        imm_s_7_6 = (instr & 0x0180) >> 1

        rd = (self.C2_RD_MASK & instr) >> 7
        rs1 = (self.C2_RD_MASK & instr) >> 7
        rs2 = (self.C2_RS2_MASK & instr) >> 2

        imm_slli = imm_5 + imm_4_0
        imm_fldsp = imm_5 + imm_4_3 + imm_8_6
        imm_lwsp = imm_5 + imm_4_2 + imm_7_6
        imm_ldsp = imm_5 + imm_4_3 + imm_8_6
        imm_fsdsp = imm_5_3 + imm_s_8_6
        imm_swsp = imm_5_2 + imm_s_7_6

        if funct3 == 0 and imm_slli !=0 and rd !=0:
            instrObj.instr_name = 'c.slli'
            instrObj.rd = (rd, 'x')
            instrObj.rs1 = (rs1, 'x')
            instrObj.imm = imm_slli
        elif funct3 == 1:
            instrObj.instr_name = 'c.fldsp'
            instrObj.rd = (rd, 'f')
            instrObj.imm = imm_fldsp
            instrObj.rs1 = (2, 'x')
        elif funct3 == 2 and rd != 0:
            instrObj.instr_name = 'c.lwsp'
            instrObj.rs1 = (2, 'x')
            instrObj.rd = (rd, 'x')
            instrObj.imm = imm_lwsp
        elif funct3 == 3 and self.arch == 'rv32':
            instrObj.instr_name = 'c.flwsp'
            instrObj.rd = (rd, 'f')
            instrObj.rs1 = (2, 'x')
            instrObj.imm = imm_lwsp
        elif funct3 == 3 and self.arch == 'rv64':
            instrObj.instr_name = 'c.ldsp'
            instrObj.rd = (rd, 'x')
            instrObj.rs1 = (2, 'x')
            instrObj.imm = imm_ldsp
        elif funct3 == 4 and rs1 != 0 and imm_5 == 0 and rs2 == 0:
            instrObj.instr_name = 'c.jr'
            instrObj.rs1 = (rs1, 'x')
            instrObj.imm = 0
        elif funct3 == 4 and rs2!=0 and imm_5 == 0:
            instrObj.instr_name = 'c.mv'
            instrObj.rs2 = (rs2, 'x')
            instrObj.rd = (rd, 'x')
        elif funct3 == 4 and rd ==0 and rs2 == 0 and imm_5 == 32:
            instrObj.instr_name = 'c.ebreak'
        elif funct3 == 4 and imm_5 == 32 and rs1 !=0 and rs2 == 0:
            instrObj.instr_name = 'c.jalr'
            instrObj.rs1 = (rs1, 'x')
            instrObj.rd = (1, 'x')
        elif funct3 == 4 and imm_5 == 32 and rs2 !=0 :
            instrObj.instr_name = 'c.add'
            instrObj.rs1 = (rs1, 'x')
            instrObj.rs2 = (rs2, 'x')
            instrObj.rd = (rd, 'x')
        elif funct3 == 5:
            instrObj.instr_name = 'c.fsdsp'
            instrObj.rs2 = (rs2, 'f')
            instrObj.imm = imm_fsdsp
            instrObj.rs1 = (2 , 'x')
        elif funct3 == 6:
            instrObj.instr_name = 'c.swsp'
            instrObj.rs2 = (rs2, 'x')
            instrObj.imm = imm_swsp
            instrObj.rs1 = (2 , 'x')
        elif funct3 == 7 and self.arch == 'rv32':
            instrObj.instr_name = 'c.fswsp'
            instrObj.rs2 = (rs2, 'f')
            instrObj.rs1 = (2, 'x')
            instrObj.imm = imm_swsp
        elif funct3 == 7 and self.arch == 'rv64':
            instrObj.instr_name = 'c.sdsp'
            instrObj.rs2 = (rs2, 'x')
            instrObj.imm = imm_fsdsp
            instrObj.rs1 = (2 , 'x')
        return instrObj



    def parseCompressedInstruction(self, instrObj_temp):
        ''' Parse a compressed instruction
            Args: instrObj_temp that contains partially filled data
            Returns: (instr_obj) with all fields filled
        '''
        instr = instrObj_temp.instr
        opcode = self.FIRST2_MASK & instr
        try:
            instrObj = self.C_OPCODES[opcode](instrObj_temp)
        except KeyError as e:
            print("Instruction not found", hex(instr))
            return None

        return instrObj

    def parseStandardInstruction(self, instrObj_temp):
        ''' Parse an input line and decode the instruction
            Args: instrObj_temp that contains partially filled data
            Returns: (instr_obj) with all fields filled
        '''
        instr = instrObj_temp.instr
        opcode = self.extractOpcode(instr)
        try:
            instrObj = self.OPCODES[opcode](instrObj_temp)
        except KeyError as e:
            print("Instruction not found", hex(instr))
            return None

        return instrObj

    @plugins.decoderHookImpl
    def decode(self, instrObj_temp):
        ''' Decodes the type of instruction
            Returns: instruction object
        '''
        instr = instrObj_temp.instr
        first_two_bits = self.FIRST2_MASK & instr
        if first_two_bits == 0b11:
            instrObj = self.parseStandardInstruction(instrObj_temp)
            return instrObj

        else:
            instrObj = self.parseCompressedInstruction(instrObj_temp)
            return instrObj







