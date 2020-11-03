
# Data Propagation Report

STAT1 : Number of unique coverpoint hits that have updated the signature

STAT2 : Number of covepoints hits which are not unique but still update the signature

STAT3 : Number of instructions that contribute to a unique coverpoint but do not update signature

STAT4 : Number of Multiple signature updates for the same coverpoint

STAT5 : Number of times the signature was overwritten

| Param                     | Value    |
|---------------------------|----------|
| XLEN                      | 64      |
| TEST_REGION               | [('0x8000039c', '0x80000480')]      |
| SIG_REGION                | [('0x80003204', '0x80003448', '72 dwords')]      |
| COV_LABELS                | misalign-sd      |
| TEST_NAME                 | /scratch/git-repo/incoresemi/riscof/riscof_work/misalign-sd-01.S/misalign-sd-01.S    |
| Total Number of coverpoints| 8     |
| Total Signature Updates   | 35      |
| Total Coverpoints Covered | 8      |
| STAT1                     | 7      |
| STAT2                     | 0      |
| STAT3                     | 0     |
| STAT4                     | 28     |
| STAT5                     | 0     |

## Details for STAT2:

```


```

## Details of STAT3

```


```

## Details of STAT4:

```
Last Coverpoint : ['opcode : sd', 'ea_align == 1']
Last Code Sequence : 
	-[0x800003bc]:sd a1, 2(a0)
Current Store : [0x80000720] : sd t2, 0(t1) -- Store: [0x80003248]:0x000000000000010F




Last Coverpoint : ['opcode : sd', 'ea_align == 1']
Last Code Sequence : 
	-[0x800003bc]:sd a1, 2(a0)
Current Store : [0x80000728] : sd t2, 8(t1) -- Store: [0x80003250]:0x0000000000000006




Last Coverpoint : ['opcode : sd', 'ea_align == 1']
Last Code Sequence : 
	-[0x800003bc]:sd a1, 2(a0)
Current Store : [0x80000740] : sd t4, 16(t1) -- Store: [0x80003258]:0x00000000000003B0




Last Coverpoint : ['opcode : sd', 'ea_align == 1']
Last Code Sequence : 
	-[0x800003bc]:sd a1, 2(a0)
Current Store : [0x800007cc] : sd t2, 24(t1) -- Store: [0x80003260]:0x0000000000003205




Last Coverpoint : ['ea_align == 2']
Last Code Sequence : 
	-[0x800003e0]:sd a1, 3583(a0)
Current Store : [0x80000720] : sd t2, 0(t1) -- Store: [0x80003268]:0x000000000000010F




Last Coverpoint : ['ea_align == 2']
Last Code Sequence : 
	-[0x800003e0]:sd a1, 3583(a0)
Current Store : [0x80000728] : sd t2, 8(t1) -- Store: [0x80003270]:0x0000000000000006




Last Coverpoint : ['ea_align == 2']
Last Code Sequence : 
	-[0x800003e0]:sd a1, 3583(a0)
Current Store : [0x80000740] : sd t4, 16(t1) -- Store: [0x80003278]:0x00000000000003D4




Last Coverpoint : ['ea_align == 2']
Last Code Sequence : 
	-[0x800003e0]:sd a1, 3583(a0)
Current Store : [0x800007cc] : sd t2, 24(t1) -- Store: [0x80003280]:0x000000000000320E




Last Coverpoint : ['ea_align == 3']
Last Code Sequence : 
	-[0x800003fc]:sd a1, 1024(a0)
Current Store : [0x80000720] : sd t2, 0(t1) -- Store: [0x80003288]:0x000000000000010F




Last Coverpoint : ['ea_align == 3']
Last Code Sequence : 
	-[0x800003fc]:sd a1, 1024(a0)
Current Store : [0x80000728] : sd t2, 8(t1) -- Store: [0x80003290]:0x0000000000000006




Last Coverpoint : ['ea_align == 3']
Last Code Sequence : 
	-[0x800003fc]:sd a1, 1024(a0)
Current Store : [0x80000740] : sd t4, 16(t1) -- Store: [0x80003298]:0x00000000000003F0




Last Coverpoint : ['ea_align == 3']
Last Code Sequence : 
	-[0x800003fc]:sd a1, 1024(a0)
Current Store : [0x800007cc] : sd t2, 24(t1) -- Store: [0x800032a0]:0x0000000000003217




Last Coverpoint : ['ea_align == 4']
Last Code Sequence : 
	-[0x8000041c]:sd a1, 6(a0)
Current Store : [0x80000720] : sd t2, 0(t1) -- Store: [0x800032a8]:0x000000000000010F




Last Coverpoint : ['ea_align == 4']
Last Code Sequence : 
	-[0x8000041c]:sd a1, 6(a0)
Current Store : [0x80000728] : sd t2, 8(t1) -- Store: [0x800032b0]:0x0000000000000006




Last Coverpoint : ['ea_align == 4']
Last Code Sequence : 
	-[0x8000041c]:sd a1, 6(a0)
Current Store : [0x80000740] : sd t4, 16(t1) -- Store: [0x800032b8]:0x0000000000000410




Last Coverpoint : ['ea_align == 4']
Last Code Sequence : 
	-[0x8000041c]:sd a1, 6(a0)
Current Store : [0x800007cc] : sd t2, 24(t1) -- Store: [0x800032c0]:0x0000000000003220




Last Coverpoint : ['ea_align == 5']
Last Code Sequence : 
	-[0x80000438]:sd a1, 16(a0)
Current Store : [0x80000720] : sd t2, 0(t1) -- Store: [0x800032c8]:0x000000000000010F




Last Coverpoint : ['ea_align == 5']
Last Code Sequence : 
	-[0x80000438]:sd a1, 16(a0)
Current Store : [0x80000728] : sd t2, 8(t1) -- Store: [0x800032d0]:0x0000000000000006




Last Coverpoint : ['ea_align == 5']
Last Code Sequence : 
	-[0x80000438]:sd a1, 16(a0)
Current Store : [0x80000740] : sd t4, 16(t1) -- Store: [0x800032d8]:0x000000000000042C




Last Coverpoint : ['ea_align == 5']
Last Code Sequence : 
	-[0x80000438]:sd a1, 16(a0)
Current Store : [0x800007cc] : sd t2, 24(t1) -- Store: [0x800032e0]:0x0000000000003229




Last Coverpoint : ['ea_align == 6']
Last Code Sequence : 
	-[0x80000454]:sd a1, 16(a0)
Current Store : [0x80000720] : sd t2, 0(t1) -- Store: [0x800032e8]:0x000000000000010F




Last Coverpoint : ['ea_align == 6']
Last Code Sequence : 
	-[0x80000454]:sd a1, 16(a0)
Current Store : [0x80000728] : sd t2, 8(t1) -- Store: [0x800032f0]:0x0000000000000006




Last Coverpoint : ['ea_align == 6']
Last Code Sequence : 
	-[0x80000454]:sd a1, 16(a0)
Current Store : [0x80000740] : sd t4, 16(t1) -- Store: [0x800032f8]:0x0000000000000448




Last Coverpoint : ['ea_align == 6']
Last Code Sequence : 
	-[0x80000454]:sd a1, 16(a0)
Current Store : [0x800007cc] : sd t2, 24(t1) -- Store: [0x80003300]:0x0000000000003232




Last Coverpoint : ['ea_align == 7']
Last Code Sequence : 
	-[0x80000474]:sd a1, 5(a0)
Current Store : [0x80000720] : sd t2, 0(t1) -- Store: [0x80003308]:0x000000000000010F




Last Coverpoint : ['ea_align == 7']
Last Code Sequence : 
	-[0x80000474]:sd a1, 5(a0)
Current Store : [0x80000728] : sd t2, 8(t1) -- Store: [0x80003310]:0x0000000000000006




Last Coverpoint : ['ea_align == 7']
Last Code Sequence : 
	-[0x80000474]:sd a1, 5(a0)
Current Store : [0x80000740] : sd t4, 16(t1) -- Store: [0x80003318]:0x0000000000000468




Last Coverpoint : ['ea_align == 7']
Last Code Sequence : 
	-[0x80000474]:sd a1, 5(a0)
Current Store : [0x800007cc] : sd t2, 24(t1) -- Store: [0x80003320]:0x000000000000323B





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

|s.no|            signature             |             coverpoints              |              code               |
|---:|----------------------------------|--------------------------------------|---------------------------------|
|   1|[0x80003211]<br>0xFFFF7FFFFFFFFFFF|- opcode : sd<br> - ea_align == 1<br> |[0x800003bc]:sd a1, 2(a0)<br>    |
|   2|[0x8000321a]<br>0xF7FFFFFFFFFFFFFF|- ea_align == 2<br>                   |[0x800003e0]:sd a1, 3583(a0)<br> |
|   3|[0x80003223]<br>0xFFFFFFFFFFFFFFFD|- ea_align == 3<br>                   |[0x800003fc]:sd a1, 1024(a0)<br> |
|   4|[0x8000322c]<br>0x0000000080000000|- ea_align == 4<br>                   |[0x8000041c]:sd a1, 6(a0)<br>    |
|   5|[0x80003235]<br>0x0000000000400000|- ea_align == 5<br>                   |[0x80000438]:sd a1, 16(a0)<br>   |
|   6|[0x8000323e]<br>0xFFFFFFFFFFFFFFFD|- ea_align == 6<br>                   |[0x80000454]:sd a1, 16(a0)<br>   |
|   7|[0x80003247]<br>0x0000080000000000|- ea_align == 7<br>                   |[0x80000474]:sd a1, 5(a0)<br>    |