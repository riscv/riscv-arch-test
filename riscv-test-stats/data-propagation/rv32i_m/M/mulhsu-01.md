
# Data Propagation Report

STAT1 : Number of unique coverpoint hits that have updated the signature

STAT2 : Number of covepoints hits which are not unique but still update the signature

STAT3 : Number of instructions that contribute to a unique coverpoint but do not update signature

STAT4 : Number of Multiple signature updates for the same coverpoint

STAT5 : Number of times the signature was overwritten

| Param                     | Value    |
|---------------------------|----------|
| XLEN                      | 32      |
| TEST_REGION               | [('0x800000f8', '0x80000800')]      |
| SIG_REGION                | [('0x80003204', '0x80003390', '99 words')]      |
| COV_LABELS                | mulhsu      |
| TEST_NAME                 | /scratch/git-repo/incoresemi/riscof/riscof_work/mulhsu-01.S/mulhsu-01.S    |
| Total Number of coverpoints| 246     |
| Total Signature Updates   | 96      |
| Total Coverpoints Covered | 246      |
| STAT1                     | 93      |
| STAT2                     | 3      |
| STAT3                     | 0     |
| STAT4                     | 0     |
| STAT5                     | 0     |

## Details for STAT2:

```
Op without unique coverpoint updates Signature
 -- Code Sequence:
      [0x800007c0]:mulhsu a2, a0, a1
      [0x800007c4]:sw a2, 296(gp)
 -- Signature Address: 0x80003380 Data: 0xFFFFFFFF
 -- Redundant Coverpoints hit by the op
      - opcode : mulhsu
      - rs1 : x10
      - rs2 : x11
      - rd : x12
      - rs1 != rs2  and rs1 != rd and rs2 != rd
      - rs1_val < 0 and rs2_val > 0
      - rs1_val != rs2_val
      - rs2_val == 1
      - rs1_val == (-2**(xlen-1))
      - rs1_val == -2147483648




Op without unique coverpoint updates Signature
 -- Code Sequence:
      [0x800007e8]:mulhsu a2, a0, a1
      [0x800007ec]:sw a2, 304(gp)
 -- Signature Address: 0x80003388 Data: 0x00000000
 -- Redundant Coverpoints hit by the op
      - opcode : mulhsu
      - rs1 : x10
      - rs2 : x11
      - rd : x12
      - rs1 != rs2  and rs1 != rd and rs2 != rd
      - rs1_val != rs2_val
      - rs2_val == 0
      - rs1_val == -32769




Op without unique coverpoint updates Signature
 -- Code Sequence:
      [0x800007f8]:mulhsu a2, a0, a1
      [0x800007fc]:sw a2, 308(gp)
 -- Signature Address: 0x8000338c Data: 0x00000000
 -- Redundant Coverpoints hit by the op
      - opcode : mulhsu
      - rs1 : x10
      - rs2 : x11
      - rd : x12
      - rs1 != rs2  and rs1 != rd and rs2 != rd
      - rs1_val > 0 and rs2_val > 0
      - rs1_val != rs2_val
      - rs2_val == 1024
      - rs1_val == 256






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

|s.no|        signature         |                                                                                                           coverpoints                                                                                                            |                                 code                                  |
|---:|--------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------|
|   1|[0x80003210]<br>0x00000000|- opcode : mulhsu<br> - rs1 : x8<br> - rs2 : x8<br> - rd : x8<br> - rs1 == rs2 == rd<br> - rs1_val > 0 and rs2_val > 0<br> - rs1_val == rs2_val<br> - rs2_val == 1<br> - rs1_val == 1<br>                                         |[0x80000108]:mulhsu fp, fp, fp<br> [0x8000010c]:sw fp, 0(a0)<br>       |
|   2|[0x80003214]<br>0x00000000|- rs1 : x19<br> - rs2 : x1<br> - rd : x1<br> - rs2 == rd != rs1<br> - rs1_val != rs2_val<br> - rs1_val == 0<br> - rs2_val == -67108865<br>                                                                                        |[0x8000011c]:mulhsu ra, s3, ra<br> [0x80000120]:sw ra, 4(a0)<br>       |
|   3|[0x80003218]<br>0x03FFFFFF|- rs1 : x20<br> - rs2 : x5<br> - rd : x20<br> - rs1 == rd != rs2<br> - rs1_val == (2**(xlen-1)-1)<br> - rs2_val == 134217728<br> - rs1_val == 2147483647<br>                                                                      |[0x80000130]:mulhsu s4, s4, t0<br> [0x80000134]:sw s4, 8(a0)<br>       |
|   4|[0x8000321c]<br>0x00000000|- rs1 : x0<br> - rs2 : x25<br> - rd : x6<br> - rs1 != rs2  and rs1 != rd and rs2 != rd<br> - rs2_val == -513<br>                                                                                                                  |[0x80000140]:mulhsu t1, zero, s9<br> [0x80000144]:sw t1, 12(a0)<br>    |
|   5|[0x80003220]<br>0xC0000000|- rs1 : x18<br> - rs2 : x18<br> - rd : x19<br> - rs1 == rs2 != rd<br> - rs1_val < 0 and rs2_val < 0<br> - rs2_val == (-2**(xlen-1))<br> - rs1_val == (-2**(xlen-1))<br> - rs2_val == -2147483648<br> - rs1_val == -2147483648<br> |[0x80000154]:mulhsu s3, s2, s2<br> [0x80000158]:sw s3, 16(a0)<br>      |
|   6|[0x80003224]<br>0x00000000|- rs1 : x27<br> - rs2 : x12<br> - rd : x0<br> - rs2_val == 0<br> - rs1_val == -32769<br>                                                                                                                                          |[0x80000168]:mulhsu zero, s11, a2<br> [0x8000016c]:sw zero, 20(a0)<br> |
|   7|[0x80003228]<br>0x00001FFF|- rs1 : x23<br> - rs2 : x31<br> - rd : x2<br> - rs2_val == (2**(xlen-1)-1)<br> - rs2_val == 2147483647<br> - rs1_val == 16384<br>                                                                                                 |[0x8000017c]:mulhsu sp, s7, t6<br> [0x80000180]:sw sp, 24(a0)<br>      |
|   8|[0x8000322c]<br>0xFFFFFEFF|- rs1 : x29<br> - rs2 : x30<br> - rd : x31<br> - rs2_val == -257<br> - rs1_val == -257<br>                                                                                                                                        |[0x8000018c]:mulhsu t6, t4, t5<br> [0x80000190]:sw t6, 28(a0)<br>      |
|   9|[0x80003230]<br>0x00000001|- rs1 : x6<br> - rs2 : x11<br> - rd : x4<br> - rs1_val > 0 and rs2_val < 0<br> - rs2_val == -1431655766<br> - rs1_val == 2<br>                                                                                                    |[0x800001a0]:mulhsu tp, t1, a1<br> [0x800001a4]:sw tp, 32(a0)<br>      |
|  10|[0x80003234]<br>0x00000003|- rs1 : x11<br> - rs2 : x3<br> - rd : x7<br> - rs2_val == -4194305<br> - rs1_val == 4<br>                                                                                                                                         |[0x800001b4]:mulhsu t2, a1, gp<br> [0x800001b8]:sw t2, 36(a0)<br>      |
|  11|[0x80003238]<br>0x00000007|- rs1 : x28<br> - rs2 : x15<br> - rd : x13<br> - rs2_val == -8193<br> - rs1_val == 8<br>                                                                                                                                          |[0x800001c8]:mulhsu a3, t3, a5<br> [0x800001cc]:sw a3, 40(a0)<br>      |
|  12|[0x8000323c]<br>0x0000000F|- rs1 : x13<br> - rs2 : x9<br> - rd : x3<br> - rs1_val == 16<br>                                                                                                                                                                  |[0x800001dc]:mulhsu gp, a3, s1<br> [0x800001e0]:sw gp, 44(a0)<br>      |
|  13|[0x80003240]<br>0x0000001B|- rs1 : x14<br> - rs2 : x24<br> - rd : x26<br> - rs2_val == -536870913<br> - rs1_val == 32<br>                                                                                                                                    |[0x800001f0]:mulhsu s10, a4, s8<br> [0x800001f4]:sw s10, 48(a0)<br>    |
|  14|[0x80003244]<br>0x0000003F|- rs1 : x15<br> - rs2 : x6<br> - rd : x22<br> - rs2_val == -129<br> - rs1_val == 64<br>                                                                                                                                           |[0x80000200]:mulhsu s6, a5, t1<br> [0x80000204]:sw s6, 52(a0)<br>      |
|  15|[0x80003248]<br>0x00000000|- rs1 : x3<br> - rs2 : x23<br> - rd : x29<br> - rs2_val == 16777216<br> - rs1_val == 128<br>                                                                                                                                      |[0x80000210]:mulhsu t4, gp, s7<br> [0x80000214]:sw t4, 56(a0)<br>      |
|  16|[0x8000324c]<br>0x00000000|- rs1 : x22<br> - rs2 : x0<br> - rd : x14<br> - rs1_val == 256<br>                                                                                                                                                                |[0x80000220]:mulhsu a4, s6, zero<br> [0x80000224]:sw a4, 60(a0)<br>    |
|  17|[0x80003250]<br>0x000001FF|- rs1 : x31<br> - rs2 : x19<br> - rd : x25<br> - rs2_val == -65<br> - rs1_val == 512<br>                                                                                                                                          |[0x80000230]:mulhsu s9, t6, s3<br> [0x80000234]:sw s9, 64(a0)<br>      |
|  18|[0x80003254]<br>0x000003FF|- rs1 : x30<br> - rs2 : x16<br> - rd : x27<br> - rs1_val == 1024<br>                                                                                                                                                              |[0x80000240]:mulhsu s11, t5, a6<br> [0x80000244]:sw s11, 68(a0)<br>    |
|  19|[0x80003258]<br>0x00000080|- rs1 : x7<br> - rs2 : x17<br> - rd : x11<br> - rs2_val == 268435456<br> - rs1_val == 2048<br>                                                                                                                                    |[0x8000025c]:mulhsu a1, t2, a7<br> [0x80000260]:sw a1, 0(gp)<br>       |
|  20|[0x8000325c]<br>0x00000FFD|- rs1 : x10<br> - rs2 : x29<br> - rd : x28<br> - rs2_val == -2097153<br> - rs1_val == 4096<br>                                                                                                                                    |[0x80000270]:mulhsu t3, a0, t4<br> [0x80000274]:sw t3, 4(gp)<br>       |
|  21|[0x80003260]<br>0x00001BFF|- rs1 : x1<br> - rs2 : x10<br> - rd : x16<br> - rs1_val == 8192<br>                                                                                                                                                               |[0x80000284]:mulhsu a6, ra, a0<br> [0x80000288]:sw a6, 8(gp)<br>       |
|  22|[0x80003264]<br>0x00007FEF|- rs1 : x24<br> - rs2 : x4<br> - rd : x21<br> - rs1_val == 32768<br>                                                                                                                                                              |[0x80000298]:mulhsu s5, s8, tp<br> [0x8000029c]:sw s5, 12(gp)<br>      |
|  23|[0x80003268]<br>0x0000FFFF|- rs1 : x2<br> - rs2 : x20<br> - rd : x10<br> - rs1_val == 65536<br>                                                                                                                                                              |[0x800002a8]:mulhsu a0, sp, s4<br> [0x800002ac]:sw a0, 16(gp)<br>      |
|  24|[0x8000326c]<br>0x00000100|- rs1 : x9<br> - rs2 : x22<br> - rd : x24<br> - rs2_val == 8388608<br> - rs1_val == 131072<br>                                                                                                                                    |[0x800002b8]:mulhsu s8, s1, s6<br> [0x800002bc]:sw s8, 20(gp)<br>      |
|  25|[0x80003270]<br>0x00000000|- rs1 : x5<br> - rs2 : x28<br> - rd : x15<br> - rs2_val == 8192<br> - rs1_val == 262144<br>                                                                                                                                       |[0x800002c8]:mulhsu a5, t0, t3<br> [0x800002cc]:sw a5, 24(gp)<br>      |
|  26|[0x80003274]<br>0x00000000|- rs1 : x16<br> - rs2 : x26<br> - rd : x23<br> - rs2_val == 32<br> - rs1_val == 524288<br>                                                                                                                                        |[0x800002d8]:mulhsu s7, a6, s10<br> [0x800002dc]:sw s7, 28(gp)<br>     |
|  27|[0x80003278]<br>0x000FFFFF|- rs1 : x25<br> - rs2 : x21<br> - rd : x9<br> - rs2_val == -1025<br> - rs1_val == 1048576<br>                                                                                                                                     |[0x800002e8]:mulhsu s1, s9, s5<br> [0x800002ec]:sw s1, 32(gp)<br>      |
|  28|[0x8000327c]<br>0x00000000|- rs1 : x21<br> - rs2 : x7<br> - rd : x30<br> - rs1_val == 2097152<br>                                                                                                                                                            |[0x800002f8]:mulhsu t5, s5, t2<br> [0x800002fc]:sw t5, 36(gp)<br>      |
|  29|[0x80003280]<br>0x0037FFFF|- rs1 : x26<br> - rs2 : x2<br> - rd : x12<br> - rs1_val == 4194304<br>                                                                                                                                                            |[0x8000030c]:mulhsu a2, s10, sp<br> [0x80000310]:sw a2, 40(gp)<br>     |
|  30|[0x80003284]<br>0x007FFFFF|- rs1 : x4<br> - rs2 : x13<br> - rd : x17<br> - rs1_val == 8388608<br>                                                                                                                                                            |[0x8000031c]:mulhsu a7, tp, a3<br> [0x80000320]:sw a7, 44(gp)<br>      |
|  31|[0x80003288]<br>0x00040000|- rs1 : x17<br> - rs2 : x14<br> - rd : x5<br> - rs2_val == 67108864<br> - rs1_val == 16777216<br>                                                                                                                                 |[0x8000032c]:mulhsu t0, a7, a4<br> [0x80000330]:sw t0, 48(gp)<br>      |
|  32|[0x8000328c]<br>0x01FFFFEF|- rs1 : x12<br> - rs2 : x27<br> - rd : x18<br> - rs2_val == -2049<br> - rs1_val == 33554432<br>                                                                                                                                   |[0x80000340]:mulhsu s2, a2, s11<br> [0x80000344]:sw s2, 52(gp)<br>     |
|  33|[0x80003290]<br>0x00001000|- rs2_val == 262144<br> - rs1_val == 67108864<br>                                                                                                                                                                                 |[0x80000350]:mulhsu a2, a0, a1<br> [0x80000354]:sw a2, 56(gp)<br>      |
|  34|[0x80003294]<br>0x07FBFFFF|- rs2_val == -8388609<br> - rs1_val == 134217728<br>                                                                                                                                                                              |[0x80000364]:mulhsu a2, a0, a1<br> [0x80000368]:sw a2, 60(gp)<br>      |
|  35|[0x80003298]<br>0x0FFFFFEF|- rs1_val == 268435456<br>                                                                                                                                                                                                        |[0x80000374]:mulhsu a2, a0, a1<br> [0x80000378]:sw a2, 64(gp)<br>      |
|  36|[0x8000329c]<br>0x1FFFFFFE|- rs1_val == 536870912<br>                                                                                                                                                                                                        |[0x80000384]:mulhsu a2, a0, a1<br> [0x80000388]:sw a2, 68(gp)<br>      |
|  37|[0x800032a0]<br>0x00000000|- rs1_val == 1073741824<br>                                                                                                                                                                                                       |[0x80000394]:mulhsu a2, a0, a1<br> [0x80000398]:sw a2, 72(gp)<br>      |
|  38|[0x800032a4]<br>0xFFFFFFFF|- rs1_val < 0 and rs2_val > 0<br> - rs2_val == 8<br> - rs1_val == -2<br>                                                                                                                                                          |[0x800003a4]:mulhsu a2, a0, a1<br> [0x800003a8]:sw a2, 76(gp)<br>      |
|  39|[0x800032a8]<br>0xFFFFFFFF|- rs1_val == -3<br>                                                                                                                                                                                                               |[0x800003b4]:mulhsu a2, a0, a1<br> [0x800003b8]:sw a2, 80(gp)<br>      |
|  40|[0x800032ac]<br>0xFFFFFFFB|- rs2_val == -2<br> - rs1_val == -5<br>                                                                                                                                                                                           |[0x800003c4]:mulhsu a2, a0, a1<br> [0x800003c8]:sw a2, 84(gp)<br>      |
|  41|[0x800032b0]<br>0xFFFFFFF7|- rs2_val == -65537<br> - rs1_val == -9<br>                                                                                                                                                                                       |[0x800003d8]:mulhsu a2, a0, a1<br> [0x800003dc]:sw a2, 88(gp)<br>      |
|  42|[0x800032b4]<br>0xFFFFFFEF|- rs2_val == -524289<br> - rs1_val == -17<br>                                                                                                                                                                                     |[0x800003ec]:mulhsu a2, a0, a1<br> [0x800003f0]:sw a2, 92(gp)<br>      |
|  43|[0x800032b8]<br>0xFF8001FF|- rs2_val == -262145<br> - rs1_val == -8388609<br>                                                                                                                                                                                |[0x80000404]:mulhsu a2, a0, a1<br> [0x80000408]:sw a2, 96(gp)<br>      |
|  44|[0x800032bc]<br>0x00000000|- rs2_val == -1048577<br>                                                                                                                                                                                                         |[0x80000418]:mulhsu a2, a0, a1<br> [0x8000041c]:sw a2, 100(gp)<br>     |
|  45|[0x800032c0]<br>0xFFFFFF7F|- rs2_val == -16777217<br> - rs1_val == -129<br>                                                                                                                                                                                  |[0x8000042c]:mulhsu a2, a0, a1<br> [0x80000430]:sw a2, 104(gp)<br>     |
|  46|[0x800032c4]<br>0xFFF80FFF|- rs2_val == -33554433<br> - rs1_val == -524289<br>                                                                                                                                                                               |[0x80000444]:mulhsu a2, a0, a1<br> [0x80000448]:sw a2, 108(gp)<br>     |
|  47|[0x800032c8]<br>0xFFFFFE0F|- rs2_val == -134217729<br> - rs1_val == -513<br>                                                                                                                                                                                 |[0x80000458]:mulhsu a2, a0, a1<br> [0x8000045c]:sw a2, 112(gp)<br>     |
|  48|[0x800032cc]<br>0xFFFFFFF6|- rs2_val == -268435457<br>                                                                                                                                                                                                       |[0x8000046c]:mulhsu a2, a0, a1<br> [0x80000470]:sw a2, 116(gp)<br>     |
|  49|[0x800032d0]<br>0x02FFFFFF|- rs2_val == -1073741825<br>                                                                                                                                                                                                      |[0x80000480]:mulhsu a2, a0, a1<br> [0x80000484]:sw a2, 120(gp)<br>     |
|  50|[0x800032d4]<br>0xFFFFFD55|- rs2_val == 1431655765<br> - rs1_val == -2049<br>                                                                                                                                                                                |[0x80000498]:mulhsu a2, a0, a1<br> [0x8000049c]:sw a2, 124(gp)<br>     |
|  51|[0x800032d8]<br>0xFFFFFFFF|- rs1_val == -33<br>                                                                                                                                                                                                              |[0x800004a8]:mulhsu a2, a0, a1<br> [0x800004ac]:sw a2, 128(gp)<br>     |
|  52|[0x800032dc]<br>0xFFFFFFC0|- rs1_val == -65<br>                                                                                                                                                                                                              |[0x800004bc]:mulhsu a2, a0, a1<br> [0x800004c0]:sw a2, 132(gp)<br>     |
|  53|[0x800032e0]<br>0xFFFFFBFF|- rs1_val == -1025<br>                                                                                                                                                                                                            |[0x800004cc]:mulhsu a2, a0, a1<br> [0x800004d0]:sw a2, 136(gp)<br>     |
|  54|[0x800032e4]<br>0xFFFFF07F|- rs1_val == -4097<br>                                                                                                                                                                                                            |[0x800004e4]:mulhsu a2, a0, a1<br> [0x800004e8]:sw a2, 140(gp)<br>     |
|  55|[0x800032e8]<br>0xFFFFBFFF|- rs2_val == -33<br> - rs1_val == -16385<br>                                                                                                                                                                                      |[0x800004f8]:mulhsu a2, a0, a1<br> [0x800004fc]:sw a2, 144(gp)<br>     |
|  56|[0x800032ec]<br>0xFFFFFFBF|- rs2_val == 4194304<br> - rs1_val == -65537<br>                                                                                                                                                                                  |[0x8000050c]:mulhsu a2, a0, a1<br> [0x80000510]:sw a2, 148(gp)<br>     |
|  57|[0x800032f0]<br>0xFFFFFFFF|- rs1_val == -131073<br>                                                                                                                                                                                                          |[0x80000520]:mulhsu a2, a0, a1<br> [0x80000524]:sw a2, 152(gp)<br>     |
|  58|[0x800032f4]<br>0xFFFFFFFF|- rs1_val == -262145<br>                                                                                                                                                                                                          |[0x80000534]:mulhsu a2, a0, a1<br> [0x80000538]:sw a2, 156(gp)<br>     |
|  59|[0x800032f8]<br>0xFFFFFFFF|- rs2_val == 1024<br> - rs1_val == -1048577<br>                                                                                                                                                                                   |[0x80000548]:mulhsu a2, a0, a1<br> [0x8000054c]:sw a2, 160(gp)<br>     |
|  60|[0x800032fc]<br>0xFFFFFFFF|- rs1_val == -2097153<br>                                                                                                                                                                                                         |[0x8000055c]:mulhsu a2, a0, a1<br> [0x80000560]:sw a2, 164(gp)<br>     |
|  61|[0x80003300]<br>0xFFFFFFFD|- rs2_val == 2048<br> - rs1_val == -4194305<br>                                                                                                                                                                                   |[0x80000574]:mulhsu a2, a0, a1<br> [0x80000578]:sw a2, 168(gp)<br>     |
|  62|[0x80003304]<br>0xFF00001F|- rs1_val == -16777217<br>                                                                                                                                                                                                        |[0x8000058c]:mulhsu a2, a0, a1<br> [0x80000590]:sw a2, 172(gp)<br>     |
|  63|[0x80003308]<br>0xFDFFFFFF|- rs2_val == -17<br> - rs1_val == -33554433<br>                                                                                                                                                                                   |[0x800005a0]:mulhsu a2, a0, a1<br> [0x800005a4]:sw a2, 176(gp)<br>     |
|  64|[0x8000330c]<br>0xFEFFFFFF|- rs1_val == -67108865<br>                                                                                                                                                                                                        |[0x800005b8]:mulhsu a2, a0, a1<br> [0x800005bc]:sw a2, 180(gp)<br>     |
|  65|[0x80003310]<br>0xF80007FF|- rs1_val == -134217729<br>                                                                                                                                                                                                       |[0x800005d0]:mulhsu a2, a0, a1<br> [0x800005d4]:sw a2, 184(gp)<br>     |
|  66|[0x80003314]<br>0xFFFFFFFF|- rs1_val == -268435457<br>                                                                                                                                                                                                       |[0x800005e4]:mulhsu a2, a0, a1<br> [0x800005e8]:sw a2, 188(gp)<br>     |
|  67|[0x80003318]<br>0xFFBFFFFF|- rs2_val == 33554432<br> - rs1_val == -536870913<br>                                                                                                                                                                             |[0x800005f8]:mulhsu a2, a0, a1<br> [0x800005fc]:sw a2, 192(gp)<br>     |
|  68|[0x8000331c]<br>0xC0000000|- rs2_val == -5<br> - rs1_val == -1073741825<br>                                                                                                                                                                                  |[0x8000060c]:mulhsu a2, a0, a1<br> [0x80000610]:sw a2, 196(gp)<br>     |
|  69|[0x80003320]<br>0x02AAAAAA|- rs1_val == 1431655765<br>                                                                                                                                                                                                       |[0x80000620]:mulhsu a2, a0, a1<br> [0x80000624]:sw a2, 200(gp)<br>     |
|  70|[0x80003324]<br>0xFFFFEAAA|- rs2_val == 16384<br> - rs1_val == -1431655766<br>                                                                                                                                                                               |[0x80000634]:mulhsu a2, a0, a1<br> [0x80000638]:sw a2, 204(gp)<br>     |
|  71|[0x80003328]<br>0xFFFFFFFF|- rs2_val == 2<br>                                                                                                                                                                                                                |[0x80000648]:mulhsu a2, a0, a1<br> [0x8000064c]:sw a2, 208(gp)<br>     |
|  72|[0x8000332c]<br>0xFFFFFFFF|- rs2_val == 4<br>                                                                                                                                                                                                                |[0x80000658]:mulhsu a2, a0, a1<br> [0x8000065c]:sw a2, 212(gp)<br>     |
|  73|[0x80003330]<br>0x00000002|- rs2_val == 16<br>                                                                                                                                                                                                               |[0x80000668]:mulhsu a2, a0, a1<br> [0x8000066c]:sw a2, 216(gp)<br>     |
|  74|[0x80003334]<br>0x00000000|- rs2_val == 64<br>                                                                                                                                                                                                               |[0x80000678]:mulhsu a2, a0, a1<br> [0x8000067c]:sw a2, 220(gp)<br>     |
|  75|[0x80003338]<br>0xFFFFFFFF|- rs2_val == 128<br>                                                                                                                                                                                                              |[0x80000688]:mulhsu a2, a0, a1<br> [0x8000068c]:sw a2, 224(gp)<br>     |
|  76|[0x8000333c]<br>0x00000040|- rs2_val == 256<br>                                                                                                                                                                                                              |[0x80000698]:mulhsu a2, a0, a1<br> [0x8000069c]:sw a2, 228(gp)<br>     |
|  77|[0x80003340]<br>0x000000FF|- rs2_val == 512<br>                                                                                                                                                                                                              |[0x800006ac]:mulhsu a2, a0, a1<br> [0x800006b0]:sw a2, 232(gp)<br>     |
|  78|[0x80003344]<br>0xFFFFFFFF|- rs2_val == 524288<br>                                                                                                                                                                                                           |[0x800006bc]:mulhsu a2, a0, a1<br> [0x800006c0]:sw a2, 236(gp)<br>     |
|  79|[0x80003348]<br>0xFFFFFFFF|- rs2_val == 1048576<br>                                                                                                                                                                                                          |[0x800006cc]:mulhsu a2, a0, a1<br> [0x800006d0]:sw a2, 240(gp)<br>     |
|  80|[0x8000334c]<br>0x00000000|- rs2_val == 2097152<br>                                                                                                                                                                                                          |[0x800006dc]:mulhsu a2, a0, a1<br> [0x800006e0]:sw a2, 244(gp)<br>     |
|  81|[0x80003350]<br>0x00000400|- rs2_val == 4096<br>                                                                                                                                                                                                             |[0x800006ec]:mulhsu a2, a0, a1<br> [0x800006f0]:sw a2, 248(gp)<br>     |
|  82|[0x80003354]<br>0xFFFFFFF7|- rs2_val == 536870912<br>                                                                                                                                                                                                        |[0x800006fc]:mulhsu a2, a0, a1<br> [0x80000700]:sw a2, 252(gp)<br>     |
|  83|[0x80003358]<br>0x00000000|- rs2_val == 1073741824<br>                                                                                                                                                                                                       |[0x8000070c]:mulhsu a2, a0, a1<br> [0x80000710]:sw a2, 256(gp)<br>     |
|  84|[0x8000335c]<br>0x001FFFBF|- rs2_val == -131073<br>                                                                                                                                                                                                          |[0x80000720]:mulhsu a2, a0, a1<br> [0x80000724]:sw a2, 260(gp)<br>     |
|  85|[0x80003360]<br>0xFFFFEFFF|- rs2_val == -3<br>                                                                                                                                                                                                               |[0x80000734]:mulhsu a2, a0, a1<br> [0x80000738]:sw a2, 264(gp)<br>     |
|  86|[0x80003364]<br>0x00000002|- rs2_val == -9<br>                                                                                                                                                                                                               |[0x80000744]:mulhsu a2, a0, a1<br> [0x80000748]:sw a2, 268(gp)<br>     |
|  87|[0x80003368]<br>0xFFFFFFFF|- rs2_val == 32768<br>                                                                                                                                                                                                            |[0x80000754]:mulhsu a2, a0, a1<br> [0x80000758]:sw a2, 272(gp)<br>     |
|  88|[0x8000336c]<br>0xC0000400|- rs2_val == -4097<br>                                                                                                                                                                                                            |[0x80000768]:mulhsu a2, a0, a1<br> [0x8000076c]:sw a2, 276(gp)<br>     |
|  89|[0x80003370]<br>0x001FFFF7|- rs2_val == -16385<br>                                                                                                                                                                                                           |[0x8000077c]:mulhsu a2, a0, a1<br> [0x80000780]:sw a2, 280(gp)<br>     |
|  90|[0x80003374]<br>0x00003FFF|- rs2_val == -32769<br>                                                                                                                                                                                                           |[0x80000790]:mulhsu a2, a0, a1<br> [0x80000794]:sw a2, 284(gp)<br>     |
|  91|[0x80003378]<br>0xFFFFFFFF|- rs2_val == 65536<br>                                                                                                                                                                                                            |[0x800007a0]:mulhsu a2, a0, a1<br> [0x800007a4]:sw a2, 288(gp)<br>     |
|  92|[0x8000337c]<br>0x00000000|- rs2_val == 131072<br>                                                                                                                                                                                                           |[0x800007b0]:mulhsu a2, a0, a1<br> [0x800007b4]:sw a2, 292(gp)<br>     |
|  93|[0x80003384]<br>0xFFFFEFFF|- rs1_val == -8193<br>                                                                                                                                                                                                            |[0x800007d4]:mulhsu a2, a0, a1<br> [0x800007d8]:sw a2, 300(gp)<br>     |