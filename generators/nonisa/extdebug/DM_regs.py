##################################
# DM_regs.py
#
# Debug Module register bitfield definitions
#
# David Harris (David_Harris@hmc.edu) with Claude, 8 November 2026
# SPDX-License-Identifier: Apache-2.0
##################################

# Debug Module registers and bitfields (RISC-V Debug Spec, xml/dm_registers.xml)
# Each register name is its DMI address.
# Field names are unprefixed (unique across registers), except HAWINDOWSEL_HAWINDOWSEL.
# Single-bit fields are the bit number; multi-bit fields are (msb, lsb).

DMSTATUS                = 0x11
NDMRESETPENDING         = 24
STICKYUNAVAIL           = 23
IMPEBREAK               = 22
ALLHAVERESET            = 19
ANYHAVERESET            = 18
ALLRESUMEACK            = 17
ANYRESUMEACK            = 16
ALLNONEXISTENT          = 15
ANYNONEXISTENT          = 14
ALLUNAVAIL              = 13
ANYUNAVAIL              = 12
ALLRUNNING              = 11
ANYRUNNING              = 10
ALLHALTED               = 9
ANYHALTED               = 8
AUTHENTICATED           = 7
AUTHBUSY                = 6
HASRESETHALTREQ         = 5
CONFSTRPTRVALID         = 4
VERSION                 = (3, 0)

DMCONTROL               = 0x10
HALTREQ                 = 31
RESUMEREQ               = 30
HARTRESET               = 29
ACKHAVERESET            = 28
ACKUNAVAIL              = 27
HASEL                   = 26
HARTSELLO               = (25, 16)
HARTSELHI               = (15, 6)
HARTSEL                 = (25, 6)
SETKEEPALIVE            = 5
CLRKEEPALIVE            = 4
SETRESETHALTREQ         = 3
CLRRESETHALTREQ         = 2
NDMRESET                = 1
DMACTIVE                = 0

HARTINFO                = 0x12
NSCRATCH                = (23, 20)
DATAACCESS              = 16
DATASIZE                = (15, 12)
DATAADDR                = (11, 0)

HAWINDOWSEL             = 0x14
HAWINDOWSEL_HAWINDOWSEL = (14, 0)

ABSTRACTCS              = 0x16
PROGBUFSIZE             = (28, 24)
BUSY                    = 12
RELAXEDPRIV             = 11
CMDERR                  = (10, 8)
DATACOUNT               = (3, 0)

COMMAND                 = 0x17
CMDTYPE                 = (31, 24)
CONTROL                 = (23, 0)

ABSTRACTAUTO            = 0x18
AUTOEXECPROGBUF         = (31, 16)
AUTOEXECDATA            = (11, 0)

DMCS2                   = 0x32
GROUPTYPE               = 11
DMEXTTRIGGER            = (10, 7)
GROUP                   = (6, 2)
HGWRITE                 = 1
HGSELECT                = 0

SBCS                    = 0x38
SBVERSION               = (31, 29)
SBBUSYERROR             = 22
SBBUSY                  = 21
SBREADONADDR            = 20
SBACCESS                = (19, 17)
SBAUTOINCREMENT         = 16
SBREADONDATA            = 15
SBERROR                 = (14, 12)
SBASIZE                 = (11, 5)
SBACCESS128             = 4
SBACCESS64              = 3
SBACCESS32              = 2
SBACCESS16              = 1
SBACCESS8               = 0

# Registers without fields, by address
DATA0                   = 0x04
DATA1                   = 0x05
DATA2                   = 0x06
DATA3                   = 0x07
DATA4                   = 0x08
DATA5                   = 0x09
DATA6                   = 0x0a
DATA7                   = 0x0b
DATA8                   = 0x0c
DATA9                   = 0x0d
DATA10                  = 0x0e
DATA11                  = 0x0f
HALTSUM1                = 0x13
HAWINDOW                = 0x15
CONFSTRPTR0             = 0x19
CONFSTRPTR1             = 0x1a
CONFSTRPTR2             = 0x1b
CONFSTRPTR3             = 0x1c
NEXTDM                  = 0x1d
PROGBUF0                = 0x20
PROGBUF1                = 0x21
PROGBUF2                = 0x22
PROGBUF3                = 0x23
PROGBUF4                = 0x24
PROGBUF5                = 0x25
PROGBUF6                = 0x26
PROGBUF7                = 0x27
PROGBUF8                = 0x28
PROGBUF9                = 0x29
PROGBUF10               = 0x2a
PROGBUF11               = 0x2b
PROGBUF12               = 0x2c
PROGBUF13               = 0x2d
PROGBUF14               = 0x2e
PROGBUF15               = 0x2f
AUTHDATA                = 0x30
HALTSUM2                = 0x34
HALTSUM3                = 0x35
SBADDRESS3              = 0x37
SBADDRESS0              = 0x39
SBADDRESS1              = 0x3a
SBADDRESS2              = 0x3b
SBDATA0                 = 0x3c
SBDATA1                 = 0x3d
SBDATA2                 = 0x3e
SBDATA3                 = 0x3f
HALTSUM0                = 0x40
