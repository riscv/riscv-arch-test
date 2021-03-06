
# Data Propagation Report

- **STAT1** : Number of instructions that hit unique coverpoints and update the signature.
- **STAT2** : Number of instructions that hit covepoints which are not unique but still update the signature
- **STAT3** : Number of instructions that hit a unique coverpoint but do not update signature
- **STAT4** : Number of multiple signature updates for the same coverpoint
- **STAT5** : Number of times the signature was overwritten

| Param                     | Value    |
|---------------------------|----------|
| XLEN                      | 32      |
| TEST_REGION               | [('0x800000f8', '0x80000890')]      |
| SIG_REGION                | [('0x80002010', '0x80002220', '132 words')]      |
| COV_LABELS                | rev.b      |
| TEST_NAME                 | /scratch/git-repo/incoresemi/temp/riscof_work/rev.b-01.S/ref.S    |
| Total Number of coverpoints| 202     |
| Total Coverpoints Hit     | 197      |
| Total Signature Updates   | 132      |
| STAT1                     | 131      |
| STAT2                     | 1      |
| STAT3                     | 0     |
| STAT4                     | 0     |
| STAT5                     | 0     |

## Details for STAT2:

```
Op without unique coverpoint updates Signature
 -- Code Sequence:
      [0x80000878]:grevi
      [0x8000087c]:sw
 -- Signature Address: 0x80002218 Data: 0xb38f0500
 -- Redundant Coverpoints hit by the op
      - opcode : grevi
      - rs1 : x10
      - rd : x11
      - rs1 != rd
      - rs1_val == 0xCDF1A000 #nosat






```

## Details of STAT3

```


```

## Details of STAT4:

```

```

## Details of STAT5:



## Details of STAT1:

- The first column indicates the signature address and the data at that location in hexadecimal in the following format: 
  ```
  [Address]
  Data
  ```

- The second column captures all the coverpoints which have been captured by that particular signature location

- The third column captures all the insrtuctions since the time a coverpoint was
  hit to the point when a store to the signature was performed. Each line has
  the following format:
  ```
  [PC of instruction] : mnemonic
  ```
- The order in the table is based on the order of signatures occuring in the
  test. These need not necessarily be in increasing or decreasing order of the
  address in the signature region.

|s.no|        signature         |                                              coverpoints                                              |                   code                    |
|---:|--------------------------|-------------------------------------------------------------------------------------------------------|-------------------------------------------|
|   1|[0x80002010]<br>0xffffffff|- opcode : grevi<br> - rs1 : x16<br> - rd : x10<br> - rs1 != rd<br> - rs1_val == 0xFFFFFFFF #nosat<br> |[0x80000104]:grevi<br> [0x80000108]:sw<br> |
|   2|[0x80002014]<br>0x00000000|- rs1 : x23<br> - rd : x23<br> - rs1 == rd<br> - rs1_val == 0x00000000 #nosat<br>                      |[0x80000110]:grevi<br> [0x80000114]:sw<br> |
|   3|[0x80002018]<br>0x01000000|- rs1 : x20<br> - rd : x22<br> - rs1_val == 0x80000000 #nosat<br>                                      |[0x8000011c]:grevi<br> [0x80000120]:sw<br> |
|   4|[0x8000201c]<br>0x02000000|- rs1 : x11<br> - rd : x15<br> - rs1_val == 0x40000000 #nosat<br>                                      |[0x80000128]:grevi<br> [0x8000012c]:sw<br> |
|   5|[0x80002020]<br>0x05000000|- rs1 : x19<br> - rd : x11<br> - rs1_val == 0xA0000000 #nosat<br>                                      |[0x80000134]:grevi<br> [0x80000138]:sw<br> |
|   6|[0x80002024]<br>0x09000000|- rs1 : x28<br> - rd : x30<br> - rs1_val == 0x90000000 #nosat<br>                                      |[0x80000140]:grevi<br> [0x80000144]:sw<br> |
|   7|[0x80002028]<br>0x13000000|- rs1 : x8<br> - rd : x4<br> - rs1_val == 0xC8000000 #nosat<br>                                        |[0x8000014c]:grevi<br> [0x80000150]:sw<br> |
|   8|[0x8000202c]<br>0x34000000|- rs1 : x4<br> - rd : x6<br> - rs1_val == 0x2C000000 #nosat<br>                                        |[0x80000158]:grevi<br> [0x8000015c]:sw<br> |
|   9|[0x80002030]<br>0x75000000|- rs1 : x13<br> - rd : x27<br> - rs1_val == 0xAE000000 #nosat<br>                                      |[0x80000164]:grevi<br> [0x80000168]:sw<br> |
|  10|[0x80002034]<br>0xc2000000|- rs1 : x25<br> - rd : x29<br> - rs1_val == 0x43000000 #nosat<br>                                      |[0x80000170]:grevi<br> [0x80000174]:sw<br> |
|  11|[0x80002038]<br>0x8f010000|- rs1 : x9<br> - rd : x12<br> - rs1_val == 0xF1800000 #nosat<br>                                       |[0x8000017c]:grevi<br> [0x80000180]:sw<br> |
|  12|[0x8000203c]<br>0x75030000|- rs1 : x2<br> - rd : x3<br> - rs1_val == 0xAEC00000 #nosat<br>                                        |[0x80000188]:grevi<br> [0x8000018c]:sw<br> |
|  13|[0x80002040]<br>0x99040000|- rs1 : x30<br> - rd : x17<br> - rs1_val == 0x99200000 #nosat<br>                                      |[0x80000194]:grevi<br> [0x80000198]:sw<br> |
|  14|[0x80002044]<br>0x0d0e0000|- rs1 : x26<br> - rd : x16<br> - rs1_val == 0xB0700000 #nosat<br>                                      |[0x800001a0]:grevi<br> [0x800001a4]:sw<br> |
|  15|[0x80002048]<br>0xac110000|- rs1 : x21<br> - rd : x24<br> - rs1_val == 0x35880000 #nosat<br>                                      |[0x800001ac]:grevi<br> [0x800001b0]:sw<br> |
|  16|[0x8000204c]<br>0x5a330000|- rs1 : x10<br> - rd : x14<br> - rs1_val == 0x5ACC0000 #nosat<br>                                      |[0x800001b8]:grevi<br> [0x800001bc]:sw<br> |
|  17|[0x80002050]<br>0x7a5c0000|- rs1 : x27<br> - rd : x13<br> - rs1_val == 0x5E3A0000 #nosat<br>                                      |[0x800001c4]:grevi<br> [0x800001c8]:sw<br> |
|  18|[0x80002054]<br>0x75b80000|- rs1 : x18<br> - rd : x25<br> - rs1_val == 0xAE1D0000 #nosat<br>                                      |[0x800001d0]:grevi<br> [0x800001d4]:sw<br> |
|  19|[0x80002058]<br>0x76cd0100|- rs1 : x14<br> - rd : x20<br> - rs1_val == 0x6EB38000 #nosat<br>                                      |[0x800001dc]:grevi<br> [0x800001e0]:sw<br> |
|  20|[0x8000205c]<br>0x7d680200|- rs1 : x31<br> - rd : x2<br> - rs1_val == 0xBE164000 #nosat<br>                                       |[0x800001e8]:grevi<br> [0x800001ec]:sw<br> |
|  21|[0x80002060]<br>0x00000000|- rs1 : x5<br> - rd : x0<br> - rs1_val == 0xCDF1A000 #nosat<br>                                        |[0x800001fc]:grevi<br> [0x80000200]:sw<br> |
|  22|[0x80002064]<br>0x01b20b00|- rs1 : x6<br> - rd : x9<br> - rs1_val == 0x804DD000 #nosat<br>                                        |[0x80000208]:grevi<br> [0x8000020c]:sw<br> |
|  23|[0x80002068]<br>0xbcf21800|- rs1 : x7<br> - rd : x26<br> - rs1_val == 0x3D4F1800 #nosat<br>                                       |[0x80000218]:grevi<br> [0x8000021c]:sw<br> |
|  24|[0x8000206c]<br>0x00000000|- rs1 : x0<br> - rd : x19<br>                                                                          |[0x80000224]:grevi<br> [0x80000228]:sw<br> |
|  25|[0x80002070]<br>0xa2225f00|- rs1 : x3<br> - rd : x28<br> - rs1_val == 0x4544FA00 #nosat<br>                                       |[0x80000234]:grevi<br> [0x80000238]:sw<br> |
|  26|[0x80002074]<br>0xe3fdcf00|- rs1 : x24<br> - rd : x1<br> - rs1_val == 0xC7BFF300 #nosat<br>                                       |[0x80000244]:grevi<br> [0x80000248]:sw<br> |
|  27|[0x80002078]<br>0x9bb90001|- rs1 : x22<br> - rd : x31<br> - rs1_val == 0xD99D0080 #nosat<br>                                      |[0x80000254]:grevi<br> [0x80000258]:sw<br> |
|  28|[0x8000207c]<br>0x04ba9c03|- rs1 : x15<br> - rd : x5<br> - rs1_val == 0x205D39C0 #nosat<br>                                       |[0x80000264]:grevi<br> [0x80000268]:sw<br> |
|  29|[0x80002080]<br>0x8c8ed805|- rs1 : x12<br> - rd : x21<br> - rs1_val == 0x31711BA0 #nosat<br>                                      |[0x80000274]:grevi<br> [0x80000278]:sw<br> |
|  30|[0x80002084]<br>0x9579e00d|- rs1 : x29<br> - rd : x18<br> - rs1_val == 0xA99E07B0 #nosat<br>                                      |[0x80000284]:grevi<br> [0x80000288]:sw<br> |
|  31|[0x80002088]<br>0xdc155716|- rs1 : x1<br> - rd : x7<br> - rs1_val == 0x3BA8EA68 #nosat<br>                                        |[0x80000294]:grevi<br> [0x80000298]:sw<br> |
|  32|[0x8000208c]<br>0x85021e2d|- rs1 : x17<br> - rd : x8<br> - rs1_val == 0xA14078B4 #nosat<br>                                       |[0x800002a4]:grevi<br> [0x800002a8]:sw<br> |
|  33|[0x80002090]<br>0x919d2d6b|- rs1_val == 0x89B9B4D6 #nosat<br>                                                                     |[0x800002b4]:grevi<br> [0x800002b8]:sw<br> |
|  34|[0x80002094]<br>0x9ebe6efb|- rs1_val == 0x797D76DF #nosat<br>                                                                     |[0x800002c4]:grevi<br> [0x800002c8]:sw<br> |
|  35|[0x80002098]<br>0xc08deb32|- rs1_val == 0x03B1D74C #nosat<br>                                                                     |[0x800002d4]:grevi<br> [0x800002d8]:sw<br> |
|  36|[0x8000209c]<br>0xffbe7a83|- rs1_val == 0xFF7D5EC1 #nosat<br>                                                                     |[0x800002e4]:grevi<br> [0x800002e8]:sw<br> |
|  37|[0x800020a0]<br>0xd9037cc4|- rs1_val == 0x9BC03E23 #nosat<br>                                                                     |[0x800002f4]:grevi<br> [0x800002f8]:sw<br> |
|  38|[0x800020a4]<br>0xf5a494e3|- rs1_val == 0xAF2529C7 #nosat<br>                                                                     |[0x80000304]:grevi<br> [0x80000308]:sw<br> |
|  39|[0x800020a8]<br>0x6b0e15f4|- rs1_val == 0xD670A82F #nosat<br>                                                                     |[0x80000314]:grevi<br> [0x80000318]:sw<br> |
|  40|[0x800020ac]<br>0x042a5ff9|- rs1_val == 0x2054FA9F #nosat<br>                                                                     |[0x80000324]:grevi<br> [0x80000328]:sw<br> |
|  41|[0x800020b0]<br>0x763e30fc|- rs1_val == 0x6E7C0C3F #nosat<br>                                                                     |[0x80000334]:grevi<br> [0x80000338]:sw<br> |
|  42|[0x800020b4]<br>0xe035fafe|- rs1_val == 0x07AC5F7F #nosat<br>                                                                     |[0x80000344]:grevi<br> [0x80000348]:sw<br> |
|  43|[0x800020b8]<br>0xd27605ff|- rs1_val == 0x4B6EA0FF #nosat<br>                                                                     |[0x80000354]:grevi<br> [0x80000358]:sw<br> |
|  44|[0x800020bc]<br>0x7d25a4ff|- rs1_val == 0xBEA425FF #nosat<br>                                                                     |[0x80000364]:grevi<br> [0x80000368]:sw<br> |
|  45|[0x800020c0]<br>0x6c43c5ff|- rs1_val == 0x36C2A3FF #nosat<br>                                                                     |[0x80000374]:grevi<br> [0x80000378]:sw<br> |
|  46|[0x800020c4]<br>0x1ba1edff|- rs1_val == 0xD885B7FF #nosat<br>                                                                     |[0x80000384]:grevi<br> [0x80000388]:sw<br> |
|  47|[0x800020c8]<br>0x1120f4ff|- rs1_val == 0x88042FFF #nosat<br>                                                                     |[0x80000394]:grevi<br> [0x80000398]:sw<br> |
|  48|[0x800020cc]<br>0x4884f9ff|- rs1_val == 0x12219FFF #nosat<br>                                                                     |[0x800003a4]:grevi<br> [0x800003a8]:sw<br> |
|  49|[0x800020d0]<br>0x84aafdff|- rs1_val == 0x2155BFFF #nosat<br>                                                                     |[0x800003b4]:grevi<br> [0x800003b8]:sw<br> |
|  50|[0x800020d4]<br>0xf4effeff|- rs1_val == 0x2FF77FFF #nosat<br>                                                                     |[0x800003c4]:grevi<br> [0x800003c8]:sw<br> |
|  51|[0x800020d8]<br>0xdd17ffff|- rs1_val == 0xBBE8FFFF #nosat<br>                                                                     |[0x800003d4]:grevi<br> [0x800003d8]:sw<br> |
|  52|[0x800020dc]<br>0x25a8ffff|- rs1_val == 0xA415FFFF #nosat<br>                                                                     |[0x800003e4]:grevi<br> [0x800003e8]:sw<br> |
|  53|[0x800020e0]<br>0x9cc5ffff|- rs1_val == 0x39A3FFFF #nosat<br>                                                                     |[0x800003f4]:grevi<br> [0x800003f8]:sw<br> |
|  54|[0x800020e4]<br>0x7be1ffff|- rs1_val == 0xDE87FFFF #nosat<br>                                                                     |[0x80000404]:grevi<br> [0x80000408]:sw<br> |
|  55|[0x800020e8]<br>0xa4f5ffff|- rs1_val == 0x25AFFFFF #nosat<br>                                                                     |[0x80000414]:grevi<br> [0x80000418]:sw<br> |
|  56|[0x800020ec]<br>0x55f9ffff|- rs1_val == 0xAA9FFFFF #nosat<br>                                                                     |[0x80000424]:grevi<br> [0x80000428]:sw<br> |
|  57|[0x800020f0]<br>0xdcfcffff|- rs1_val == 0x3B3FFFFF #nosat<br>                                                                     |[0x80000434]:grevi<br> [0x80000438]:sw<br> |
|  58|[0x800020f4]<br>0x65feffff|- rs1_val == 0xA67FFFFF #nosat<br>                                                                     |[0x80000444]:grevi<br> [0x80000448]:sw<br> |
|  59|[0x800020f8]<br>0x74ffffff|- rs1_val == 0x2EFFFFFF #nosat<br>                                                                     |[0x80000454]:grevi<br> [0x80000458]:sw<br> |
|  60|[0x800020fc]<br>0x87ffffff|- rs1_val == 0xE1FFFFFF #nosat<br>                                                                     |[0x80000464]:grevi<br> [0x80000468]:sw<br> |
|  61|[0x80002100]<br>0xdbffffff|- rs1_val == 0xDBFFFFFF #nosat<br>                                                                     |[0x80000474]:grevi<br> [0x80000478]:sw<br> |
|  62|[0x80002104]<br>0xe3ffffff|- rs1_val == 0xC7FFFFFF #nosat<br>                                                                     |[0x80000484]:grevi<br> [0x80000488]:sw<br> |
|  63|[0x80002108]<br>0xf5ffffff|- rs1_val == 0xAFFFFFFF #nosat<br>                                                                     |[0x80000494]:grevi<br> [0x80000498]:sw<br> |
|  64|[0x8000210c]<br>0xfbffffff|- rs1_val == 0xDFFFFFFF #nosat<br>                                                                     |[0x800004a4]:grevi<br> [0x800004a8]:sw<br> |
|  65|[0x80002110]<br>0xfdffffff|- rs1_val == 0xBFFFFFFF #nosat<br>                                                                     |[0x800004b4]:grevi<br> [0x800004b8]:sw<br> |
|  66|[0x80002114]<br>0xfeffffff|- rs1_val == 0x7FFFFFFF #nosat<br>                                                                     |[0x800004c4]:grevi<br> [0x800004c8]:sw<br> |
|  67|[0x80002118]<br>0xdf8ee0ac|- rs1_val == 0xFB710735 #nosat<br>                                                                     |[0x800004d4]:grevi<br> [0x800004d8]:sw<br> |
|  68|[0x8000211c]<br>0x1a766133|- rs1_val == 0x586E86CC #nosat<br>                                                                     |[0x800004e4]:grevi<br> [0x800004e8]:sw<br> |
|  69|[0x80002120]<br>0x541dd516|- rs1_val == 0x2AB8AB68 #nosat<br>                                                                     |[0x800004f4]:grevi<br> [0x800004f8]:sw<br> |
|  70|[0x80002124]<br>0x48d6fec6|- rs1_val == 0x126B7F63 #nosat<br>                                                                     |[0x80000504]:grevi<br> [0x80000508]:sw<br> |
|  71|[0x80002128]<br>0x90a1f414|- rs1_val == 0x09852F28 #nosat<br>                                                                     |[0x80000514]:grevi<br> [0x80000518]:sw<br> |
|  72|[0x8000212c]<br>0xe0f79f83|- rs1_val == 0x07EFF9C1 #nosat<br>                                                                     |[0x80000524]:grevi<br> [0x80000528]:sw<br> |
|  73|[0x80002130]<br>0xc022bb02|- rs1_val == 0x0344DD40 #nosat<br>                                                                     |[0x80000534]:grevi<br> [0x80000538]:sw<br> |
|  74|[0x80002134]<br>0x80e78b06|- rs1_val == 0x01E7D160 #nosat<br>                                                                     |[0x80000544]:grevi<br> [0x80000548]:sw<br> |
|  75|[0x80002138]<br>0x006df464|- rs1_val == 0x00B62F26 #nosat<br>                                                                     |[0x80000554]:grevi<br> [0x80000558]:sw<br> |
|  76|[0x8000213c]<br>0x0032f5b9|- rs1_val == 0x004CAF9D #nosat<br>                                                                     |[0x80000564]:grevi<br> [0x80000568]:sw<br> |
|  77|[0x80002140]<br>0x00d42d41|- rs1_val == 0x002BB482 #nosat<br>                                                                     |[0x80000574]:grevi<br> [0x80000578]:sw<br> |
|  78|[0x80002144]<br>0x00c8b7e3|- rs1_val == 0x0013EDC7 #nosat<br>                                                                     |[0x80000584]:grevi<br> [0x80000588]:sw<br> |
|  79|[0x80002148]<br>0x00109e29|- rs1_val == 0x00087994 #nosat<br>                                                                     |[0x80000594]:grevi<br> [0x80000598]:sw<br> |
|  80|[0x8000214c]<br>0x00a02864|- rs1_val == 0x00051426 #nosat<br>                                                                     |[0x800005a4]:grevi<br> [0x800005a8]:sw<br> |
|  81|[0x80002150]<br>0x0040112a|- rs1_val == 0x00028854 #nosat<br>                                                                     |[0x800005b4]:grevi<br> [0x800005b8]:sw<br> |
|  82|[0x80002154]<br>0x0080e677|- rs1_val == 0x000167EE #nosat<br>                                                                     |[0x800005c4]:grevi<br> [0x800005c8]:sw<br> |
|  83|[0x80002158]<br>0x00007f5e|- rs1_val == 0x0000FE7A #nosat<br>                                                                     |[0x800005d4]:grevi<br> [0x800005d8]:sw<br> |
|  84|[0x8000215c]<br>0x00007ae1|- rs1_val == 0x00005E87 #nosat<br>                                                                     |[0x800005e4]:grevi<br> [0x800005e8]:sw<br> |
|  85|[0x80002160]<br>0x00008cc3|- rs1_val == 0x000031C3 #nosat<br>                                                                     |[0x800005f4]:grevi<br> [0x800005f8]:sw<br> |
|  86|[0x80002164]<br>0x00009854|- rs1_val == 0x0000192A #nosat<br>                                                                     |[0x80000604]:grevi<br> [0x80000608]:sw<br> |
|  87|[0x80002168]<br>0x0000709e|- rs1_val == 0x00000E79 #nosat<br>                                                                     |[0x80000614]:grevi<br> [0x80000618]:sw<br> |
|  88|[0x8000216c]<br>0x0000e05e|- rs1_val == 0x0000077A #nosat<br>                                                                     |[0x80000620]:grevi<br> [0x80000624]:sw<br> |
|  89|[0x80002170]<br>0x000040cc|- rs1_val == 0x00000233 #nosat<br>                                                                     |[0x8000062c]:grevi<br> [0x80000630]:sw<br> |
|  90|[0x80002174]<br>0x0000808a|- rs1_val == 0x00000151 #nosat<br>                                                                     |[0x80000638]:grevi<br> [0x8000063c]:sw<br> |
|  91|[0x80002178]<br>0x0000007d|- rs1_val == 0x000000BE #nosat<br>                                                                     |[0x80000644]:grevi<br> [0x80000648]:sw<br> |
|  92|[0x8000217c]<br>0x000000ee|- rs1_val == 0x00000077 #nosat<br>                                                                     |[0x80000650]:grevi<br> [0x80000654]:sw<br> |
|  93|[0x80002180]<br>0x00000044|- rs1_val == 0x00000022 #nosat<br>                                                                     |[0x8000065c]:grevi<br> [0x80000660]:sw<br> |
|  94|[0x80002184]<br>0x00000068|- rs1_val == 0x00000016 #nosat<br>                                                                     |[0x80000668]:grevi<br> [0x8000066c]:sw<br> |
|  95|[0x80002188]<br>0x00000070|- rs1_val == 0x0000000E #nosat<br>                                                                     |[0x80000674]:grevi<br> [0x80000678]:sw<br> |
|  96|[0x8000218c]<br>0x00000020|- rs1_val == 0x00000004 #nosat<br>                                                                     |[0x80000680]:grevi<br> [0x80000684]:sw<br> |
|  97|[0x80002190]<br>0x00000040|- rs1_val == 0x00000002 #nosat<br>                                                                     |[0x8000068c]:grevi<br> [0x80000690]:sw<br> |
|  98|[0x80002194]<br>0x00000080|- rs1_val == 0x00000001 #nosat<br>                                                                     |[0x80000698]:grevi<br> [0x8000069c]:sw<br> |
|  99|[0x80002198]<br>0x860d7750|- rs1_val == 0x61B0EE0A #nosat<br>                                                                     |[0x800006a8]:grevi<br> [0x800006ac]:sw<br> |
| 100|[0x8000219c]<br>0x59674594|- rs1_val == 0x9AE6A229 #nosat<br>                                                                     |[0x800006b8]:grevi<br> [0x800006bc]:sw<br> |
| 101|[0x800021a0]<br>0x5b56cd54|- rs1_val == 0xDA6AB32A #nosat<br>                                                                     |[0x800006c8]:grevi<br> [0x800006cc]:sw<br> |
| 102|[0x800021a4]<br>0xc781c467|- rs1_val == 0xE38123E6 #nosat<br>                                                                     |[0x800006d8]:grevi<br> [0x800006dc]:sw<br> |
| 103|[0x800021a8]<br>0x2fccc121|- rs1_val == 0xF4338384 #nosat<br>                                                                     |[0x800006e8]:grevi<br> [0x800006ec]:sw<br> |
| 104|[0x800021ac]<br>0xdff9a8a3|- rs1_val == 0xFB9F15C5 #nosat<br>                                                                     |[0x800006f8]:grevi<br> [0x800006fc]:sw<br> |
| 105|[0x800021b0]<br>0xbf1630b8|- rs1_val == 0xFD680C1D #nosat<br>                                                                     |[0x80000708]:grevi<br> [0x8000070c]:sw<br> |
| 106|[0x800021b4]<br>0x7f2e27fa|- rs1_val == 0xFE74E45F #nosat<br>                                                                     |[0x80000718]:grevi<br> [0x8000071c]:sw<br> |
| 107|[0x800021b8]<br>0xff78da0f|- rs1_val == 0xFF1E5BF0 #nosat<br>                                                                     |[0x80000728]:grevi<br> [0x8000072c]:sw<br> |
| 108|[0x800021bc]<br>0xff39a4e7|- rs1_val == 0xFF9C25E7 #nosat<br>                                                                     |[0x80000738]:grevi<br> [0x8000073c]:sw<br> |
| 109|[0x800021c0]<br>0xffd3f3c8|- rs1_val == 0xFFCBCF13 #nosat<br>                                                                     |[0x80000748]:grevi<br> [0x8000074c]:sw<br> |
| 110|[0x800021c4]<br>0xff07f6e1|- rs1_val == 0xFFE06F87 #nosat<br>                                                                     |[0x80000758]:grevi<br> [0x8000075c]:sw<br> |
| 111|[0x800021c8]<br>0xffef138c|- rs1_val == 0xFFF7C831 #nosat<br>                                                                     |[0x80000768]:grevi<br> [0x8000076c]:sw<br> |
| 112|[0x800021cc]<br>0xff5fe91e|- rs1_val == 0xFFFA9778 #nosat<br>                                                                     |[0x80000778]:grevi<br> [0x8000077c]:sw<br> |
| 113|[0x800021d0]<br>0xff3fd722|- rs1_val == 0xFFFCEB44 #nosat<br>                                                                     |[0x80000788]:grevi<br> [0x8000078c]:sw<br> |
| 114|[0x800021d4]<br>0xff7ffc5d|- rs1_val == 0xFFFE3FBA #nosat<br>                                                                     |[0x80000798]:grevi<br> [0x8000079c]:sw<br> |
| 115|[0x800021d8]<br>0xffff681a|- rs1_val == 0xFFFF1658 #nosat<br>                                                                     |[0x800007a8]:grevi<br> [0x800007ac]:sw<br> |
| 116|[0x800021dc]<br>0xffff355c|- rs1_val == 0xFFFFAC3A #nosat<br>                                                                     |[0x800007b8]:grevi<br> [0x800007bc]:sw<br> |
| 117|[0x800021e0]<br>0xffffb30f|- rs1_val == 0xFFFFCDF0 #nosat<br>                                                                     |[0x800007c8]:grevi<br> [0x800007cc]:sw<br> |
| 118|[0x800021e4]<br>0xffff6721|- rs1_val == 0xFFFFE684 #nosat<br>                                                                     |[0x800007d8]:grevi<br> [0x800007dc]:sw<br> |
| 119|[0x800021e8]<br>0xffff8f63|- rs1_val == 0xFFFFF1C6 #nosat<br>                                                                     |[0x800007e8]:grevi<br> [0x800007ec]:sw<br> |
| 120|[0x800021ec]<br>0xffff1f60|- rs1_val == 0xFFFFF806 #nosat<br>                                                                     |[0x800007f4]:grevi<br> [0x800007f8]:sw<br> |
| 121|[0x800021f0]<br>0xffff3f1e|- rs1_val == 0xFFFFFC78 #nosat<br>                                                                     |[0x80000800]:grevi<br> [0x80000804]:sw<br> |
| 122|[0x800021f4]<br>0xffff7fdc|- rs1_val == 0xFFFFFE3B #nosat<br>                                                                     |[0x8000080c]:grevi<br> [0x80000810]:sw<br> |
| 123|[0x800021f8]<br>0xffffff5a|- rs1_val == 0xFFFFFF5A #nosat<br>                                                                     |[0x80000818]:grevi<br> [0x8000081c]:sw<br> |
| 124|[0x800021fc]<br>0xffffff11|- rs1_val == 0xFFFFFF88 #nosat<br>                                                                     |[0x80000824]:grevi<br> [0x80000828]:sw<br> |
| 125|[0x80002200]<br>0xffffff83|- rs1_val == 0xFFFFFFC1 #nosat<br>                                                                     |[0x80000830]:grevi<br> [0x80000834]:sw<br> |
| 126|[0x80002204]<br>0xffffff17|- rs1_val == 0xFFFFFFE8 #nosat<br>                                                                     |[0x8000083c]:grevi<br> [0x80000840]:sw<br> |
| 127|[0x80002208]<br>0xffffff8f|- rs1_val == 0xFFFFFFF1 #nosat<br>                                                                     |[0x80000848]:grevi<br> [0x8000084c]:sw<br> |
| 128|[0x8000220c]<br>0xffffff9f|- rs1_val == 0xFFFFFFF9 #nosat<br>                                                                     |[0x80000854]:grevi<br> [0x80000858]:sw<br> |
| 129|[0x80002210]<br>0xffffffbf|- rs1_val == 0xFFFFFFFD #nosat<br>                                                                     |[0x80000860]:grevi<br> [0x80000864]:sw<br> |
| 130|[0x80002214]<br>0xffffff7f|- rs1_val == 0xFFFFFFFE #nosat<br>                                                                     |[0x8000086c]:grevi<br> [0x80000870]:sw<br> |
| 131|[0x8000221c]<br>0xfd253200|- rs1_val == 0xBFA44C00 #nosat<br>                                                                     |[0x80000888]:grevi<br> [0x8000088c]:sw<br> |
