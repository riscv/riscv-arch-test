# See LICENSE.incore for details

import os

root = os.path.abspath(os.path.dirname(__file__))

cwd = os.getcwd()

dpr_template = '''
# Data Propagation Report

- **STAT1** : Number of instructions that hit unique coverpoints and update the signature
- **STAT2** : Number of instructions that hit covepoints which are not unique but still update the signature (completely or partially)
- **STAT3** : Number of instructions that hit a unique coverpoint but do not update the signature completely
- **STAT4** : Number of multiple signature updates for the same coverpoint
- **STAT5** : Number of times the signature was overwritten

| Param                     | Value    |
|---------------------------|----------|
| XLEN                      | {0}      |
| TEST_REGION               | {1}      |
| SIG_REGION                | {2}      |
| COV_LABELS                | {3}      |
| TEST_NAME                 | {4}.S    |
| Total Number of coverpoints| {5}     |
| Total Coverpoints Hit     | {7}      |
| Total Signature Updates   | {6}      |
| STAT1                     | {8}      |
| STAT2                     | {9}      |
| STAT3                     | {10}     |
| STAT4                     | {11}     |
| STAT5                     | {12}     |

## Details for STAT2:

```
{13}

```

## Details of STAT3

```
{14}

```

## Details of STAT4:

```
{15}
```

## Details of STAT5:

{16}

## Details of STAT1:

- The first column indicates the signature address(es) and the data at that location in hexadecimal in the following format:
  ```
  [Address1]
  Data1

  [Address2]
  Data2

  ...
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

'''
