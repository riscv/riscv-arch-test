# c.hint.S
# custom tests for compressed hints

cp_chint_nop:
    .half 0x0005        # c.nop with imm = 1
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_1")
    .half 0x0009        # c.nop with imm = 2
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_2")
    .half 0x000D        # c.nop with imm = 3
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_3")
    .half 0x0011        # c.nop with imm = 4
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_4")
    .half 0x0015        # c.nop with imm = 5
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_5")
    .half 0x0019        # c.nop with imm = 6
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_6")
    .half 0x001D        # c.nop with imm = 7
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_7")
    .half 0x0021        # c.nop with imm = 8
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_8")
    .half 0x0025        # c.nop with imm = 9
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_9")
    .half 0x0029        # c.nop with imm = 10
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_10")
    .half 0x002D        # c.nop with imm = 11
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_11")
    .half 0x0031        # c.nop with imm = 12
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_12")
    .half 0x0035        # c.nop with imm = 13
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_13")
    .half 0x0039        # c.nop with imm = 14
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_14")
    .half 0x003D        # c.nop with imm = 15
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_15")
    .half 0x0041        # c.nop with imm = 16
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_16")
    .half 0x0045        # c.nop with imm = 17
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_17")
    .half 0x0049        # c.nop with imm = 18
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_18")
    .half 0x004D        # c.nop with imm = 19
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_19")
    .half 0x0051        # c.nop with imm = 20
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_20")
    .half 0x0055        # c.nop with imm = 21
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_21")
    .half 0x0059        # c.nop with imm = 22
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_22")
    .half 0x005D        # c.nop with imm = 23
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_23")
    .half 0x0061        # c.nop with imm = 24
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_24")
    .half 0x0065        # c.nop with imm = 25
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_25")
    .half 0x0069        # c.nop with imm = 26
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_26")
    .half 0x006D        # c.nop with imm = 27
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_27")
    .half 0x0071        # c.nop with imm = 28
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_28")
    .half 0x0075        # c.nop with imm = 29
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_29")
    .half 0x0079        # c.nop with imm = 30
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_30")
    .half 0x007D        # c.nop with imm = 31
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_31")
    .half 0x1001        # c.nop with imm = 32
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_32")
    .half 0x1005        # c.nop with imm = 33
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_33")
    .half 0x1009        # c.nop with imm = 34
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_34")
    .half 0x100D        # c.nop with imm = 35
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_35")
    .half 0x1011        # c.nop with imm = 36
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_36")
    .half 0x1015        # c.nop with imm = 37
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_37")
    .half 0x1019        # c.nop with imm = 38
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_38")
    .half 0x101D        # c.nop with imm = 39
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_39")
    .half 0x1021        # c.nop with imm = 40
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_40")
    .half 0x1025        # c.nop with imm = 41
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_41")
    .half 0x1029        # c.nop with imm = 42
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_42")
    .half 0x102D        # c.nop with imm = 43
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_43")
    .half 0x1031        # c.nop with imm = 44
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_44")
    .half 0x1035        # c.nop with imm = 45
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_45")
    .half 0x1039        # c.nop with imm = 46
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_46")
    .half 0x103D        # c.nop with imm = 47
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_47")
    .half 0x1041        # c.nop with imm = 48
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_48")
    .half 0x1045        # c.nop with imm = 49
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_49")
    .half 0x1049        # c.nop with imm = 50
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_50")
    .half 0x104D        # c.nop with imm = 51
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_51")
    .half 0x1051        # c.nop with imm = 52
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_52")
    .half 0x1055        # c.nop with imm = 53
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_53")
    .half 0x1059        # c.nop with imm = 54
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_54")
    .half 0x105D        # c.nop with imm = 55
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_55")
    .half 0x1061        # c.nop with imm = 56
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_56")
    .half 0x1065        # c.nop with imm = 57
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_57")
    .half 0x1069        # c.nop with imm = 58
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_58")
    .half 0x106D        # c.nop with imm = 59
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_59")
    .half 0x1071        # c.nop with imm = 60
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_60")
    .half 0x1075        # c.nop with imm = 61
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_61")
    .half 0x1079        # c.nop with imm = 62
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_62")
    .half 0x107D        # c.nop with imm = 63
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_nop_63")

cp_chint_addi:
    .half 0x0081        # c.addi x1, 0
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_addi_1")
    .half 0x0101        # c.addi x2, 0
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_addi_2")
    .half 0x0181        # c.addi x3, 0
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_addi_3")
    .half 0x0201        # c.addi x4, 0
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_addi_4")
    .half 0x0281        # c.addi x5, 0
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_addi_5")
    .half 0x0301        # c.addi x6, 0
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_addi_6")
    .half 0x0381        # c.addi x7, 0
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_addi_7")
    .half 0x0401        # c.addi x8, 0
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_addi_8")
    .half 0x0481        # c.addi x9, 0
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_addi_9")
    .half 0x0501        # c.addi x10, 0
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_addi_10")
    .half 0x0581        # c.addi x11, 0
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_addi_11")
    .half 0x0601        # c.addi x12, 0
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_addi_12")
    .half 0x0681        # c.addi x13, 0
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_addi_13")
    .half 0x0701        # c.addi x14, 0
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_addi_14")
    .half 0x0781        # c.addi x15, 0
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_addi_15")
    .half 0x0801        # c.addi x16, 0
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_addi_16")
    .half 0x0881        # c.addi x17, 0
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_addi_17")
    .half 0x0901        # c.addi x18, 0
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_addi_18")
    .half 0x0981        # c.addi x19, 0
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_addi_19")
    .half 0x0A01        # c.addi x20, 0
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_addi_20")
    .half 0x0A81        # c.addi x21, 0
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_addi_21")
    .half 0x0B01        # c.addi x22, 0
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_addi_22")
    .half 0x0B81        # c.addi x23, 0
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_addi_23")
    .half 0x0C01        # c.addi x24, 0
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_addi_24")
    .half 0x0C81        # c.addi x25, 0
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_addi_25")
    .half 0x0D01        # c.addi x26, 0
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_addi_26")
    .half 0x0D81        # c.addi x27, 0
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_addi_27")
    .half 0x0E01        # c.addi x28, 0
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_addi_28")
    .half 0x0E81        # c.addi x29, 0
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_addi_29")
    .half 0x0F01        # c.addi x30, 0
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_addi_30")
    .half 0x0F81        # c.addi x31, 0
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_addi_31")

cp_chint_li:
    .half 0x4001        # c.li x0, 0
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_0")
    .half 0x4005        # c.li x0, 1
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_1")
    .half 0x4009        # c.li x0, 2
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_2")
    .half 0x400D        # c.li x0, 3
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_3")
    .half 0x4011        # c.li x0, 4
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_4")
    .half 0x4015        # c.li x0, 5
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_5")
    .half 0x4019        # c.li x0, 6
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_6")
    .half 0x401D        # c.li x0, 7
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_7")
    .half 0x4021        # c.li x0, 8
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_8")
    .half 0x4025        # c.li x0, 9
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_9")
    .half 0x4029        # c.li x0, 10
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_10")
    .half 0x402D        # c.li x0, 11
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_11")
    .half 0x4031        # c.li x0, 12
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_12")
    .half 0x4035        # c.li x0, 13
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_13")
    .half 0x4039        # c.li x0, 14
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_14")
    .half 0x403D        # c.li x0, 15
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_15")
    .half 0x4041        # c.li x0, 16
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_16")
    .half 0x4045        # c.li x0, 17
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_17")
    .half 0x4049        # c.li x0, 18
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_18")
    .half 0x404D        # c.li x0, 19
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_19")
    .half 0x4051        # c.li x0, 20
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_20")
    .half 0x4055        # c.li x0, 21
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_21")
    .half 0x4059        # c.li x0, 22
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_22")
    .half 0x405D        # c.li x0, 23
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_23")
    .half 0x4061        # c.li x0, 24
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_24")
    .half 0x4065        # c.li x0, 25
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_25")
    .half 0x4069        # c.li x0, 26
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_26")
    .half 0x406D        # c.li x0, 27
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_27")
    .half 0x4071        # c.li x0, 28
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_28")
    .half 0x4075        # c.li x0, 29
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_29")
    .half 0x4079        # c.li x0, 30
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_30")
    .half 0x407D        # c.li x0, 31
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_31")
    .half 0x5001        # c.li x0, 32
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_32")
    .half 0x5005        # c.li x0, 33
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_33")
    .half 0x5009        # c.li x0, 34
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_34")
    .half 0x500D        # c.li x0, 35
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_35")
    .half 0x5011        # c.li x0, 36
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_36")
    .half 0x5015        # c.li x0, 37
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_37")
    .half 0x5019        # c.li x0, 38
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_38")
    .half 0x501D        # c.li x0, 39
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_39")
    .half 0x5021        # c.li x0, 40
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_40")
    .half 0x5025        # c.li x0, 41
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_41")
    .half 0x5029        # c.li x0, 42
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_42")
    .half 0x502D        # c.li x0, 43
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_43")
    .half 0x5031        # c.li x0, 44
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_44")
    .half 0x5035        # c.li x0, 45
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_45")
    .half 0x5039        # c.li x0, 46
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_46")
    .half 0x503D        # c.li x0, 47
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_47")
    .half 0x5041        # c.li x0, 48
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_48")
    .half 0x5045        # c.li x0, 49
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_49")
    .half 0x5049        # c.li x0, 50
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_50")
    .half 0x504D        # c.li x0, 51
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_51")
    .half 0x5051        # c.li x0, 52
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_52")
    .half 0x5055        # c.li x0, 53
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_53")
    .half 0x5059        # c.li x0, 54
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_54")
    .half 0x505D        # c.li x0, 55
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_55")
    .half 0x5061        # c.li x0, 56
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_56")
    .half 0x5065        # c.li x0, 57
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_57")
    .half 0x5069        # c.li x0, 58
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_58")
    .half 0x506D        # c.li x0, 59
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_59")
    .half 0x5071        # c.li x0, 60
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_60")
    .half 0x5075        # c.li x0, 61
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_61")
    .half 0x5079        # c.li x0, 62
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_62")
    .half 0x507D        # c.li x0, 63
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_li_63")

cp_chint_lui:
    .half 0x6005        # c.lui x0, 1
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_1")
    .half 0x6009        # c.lui x0, 2
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_2")
    .half 0x600D        # c.lui x0, 3
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_3")
    .half 0x6011        # c.lui x0, 4
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_4")
    .half 0x6015        # c.lui x0, 5
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_5")
    .half 0x6019        # c.lui x0, 6
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_6")
    .half 0x601D        # c.lui x0, 7
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_7")
    .half 0x6021        # c.lui x0, 8
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_8")
    .half 0x6025        # c.lui x0, 9
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_9")
    .half 0x6029        # c.lui x0, 10
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_10")
    .half 0x602D        # c.lui x0, 11
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_11")
    .half 0x6031        # c.lui x0, 12
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_12")
    .half 0x6035        # c.lui x0, 13
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_13")
    .half 0x6039        # c.lui x0, 14
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_14")
    .half 0x603D        # c.lui x0, 15
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_15")
    .half 0x6041        # c.lui x0, 16
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_16")
    .half 0x6045        # c.lui x0, 17
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_17")
    .half 0x6049        # c.lui x0, 18
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_18")
    .half 0x604D        # c.lui x0, 19
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_19")
    .half 0x6051        # c.lui x0, 20
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_20")
    .half 0x6055        # c.lui x0, 21
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_21")
    .half 0x6059        # c.lui x0, 22
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_22")
    .half 0x605D        # c.lui x0, 23
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_23")
    .half 0x6061        # c.lui x0, 24
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_24")
    .half 0x6065        # c.lui x0, 25
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_25")
    .half 0x6069        # c.lui x0, 26
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_26")
    .half 0x606D        # c.lui x0, 27
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_27")
    .half 0x6071        # c.lui x0, 28
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_28")
    .half 0x6075        # c.lui x0, 29
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_29")
    .half 0x6079        # c.lui x0, 30
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_30")
    .half 0x607D        # c.lui x0, 31
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_31")
    .half 0x7001        # c.lui x0, 32
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_32")
    .half 0x7005        # c.lui x0, 33
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_33")
    .half 0x7009        # c.lui x0, 34
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_34")
    .half 0x700D        # c.lui x0, 35
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_35")
    .half 0x7011        # c.lui x0, 36
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_36")
    .half 0x7015        # c.lui x0, 37
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_37")
    .half 0x7019        # c.lui x0, 38
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_38")
    .half 0x701D        # c.lui x0, 39
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_39")
    .half 0x7021        # c.lui x0, 40
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_40")
    .half 0x7025        # c.lui x0, 41
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_41")
    .half 0x7029        # c.lui x0, 42
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_42")
    .half 0x702D        # c.lui x0, 43
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_43")
    .half 0x7031        # c.lui x0, 44
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_44")
    .half 0x7035        # c.lui x0, 45
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_45")
    .half 0x7039        # c.lui x0, 46
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_46")
    .half 0x703D        # c.lui x0, 47
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_47")
    .half 0x7041        # c.lui x0, 48
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_48")
    .half 0x7045        # c.lui x0, 49
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_49")
    .half 0x7049        # c.lui x0, 50
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_50")
    .half 0x704D        # c.lui x0, 51
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_51")
    .half 0x7051        # c.lui x0, 52
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_52")
    .half 0x7055        # c.lui x0, 53
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_53")
    .half 0x7059        # c.lui x0, 54
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_54")
    .half 0x705D        # c.lui x0, 55
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_55")
    .half 0x7061        # c.lui x0, 56
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_56")
    .half 0x7065        # c.lui x0, 57
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_57")
    .half 0x7069        # c.lui x0, 58
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_58")
    .half 0x706D        # c.lui x0, 59
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_59")
    .half 0x7071        # c.lui x0, 60
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_60")
    .half 0x7075        # c.lui x0, 61
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_61")
    .half 0x7079        # c.lui x0, 62
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_62")
    .half 0x707D        # c.lui x0, 63
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_lui_63")

cp_chint_mv:
    .half 0x8006        # c.mv x0, x1
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_mv_1")
    .half 0x800A        # c.mv x0, x2
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_mv_2")
    .half 0x800E        # c.mv x0, x3
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_mv_3")
    .half 0x8012        # c.mv x0, x4
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_mv_4")
    .half 0x8016        # c.mv x0, x5
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_mv_5")
    .half 0x801A        # c.mv x0, x6
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_mv_6")
    .half 0x801E        # c.mv x0, x7
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_mv_7")
    .half 0x8022        # c.mv x0, x8
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_mv_8")
    .half 0x8026        # c.mv x0, x9
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_mv_9")
    .half 0x802A        # c.mv x0, x10
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_mv_10")
    .half 0x802E        # c.mv x0, x11
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_mv_11")
    .half 0x8032        # c.mv x0, x12
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_mv_12")
    .half 0x8036        # c.mv x0, x13
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_mv_13")
    .half 0x803A        # c.mv x0, x14
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_mv_14")
    .half 0x803E        # c.mv x0, x15
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_mv_15")
    .half 0x8042        # c.mv x0, x16
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_mv_16")
    .half 0x8046        # c.mv x0, x17
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_mv_17")
    .half 0x804A        # c.mv x0, x18
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_mv_18")
    .half 0x804E        # c.mv x0, x19
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_mv_19")
    .half 0x8052        # c.mv x0, x20
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_mv_20")
    .half 0x8056        # c.mv x0, x21
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_mv_21")
    .half 0x805A        # c.mv x0, x22
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_mv_22")
    .half 0x805E        # c.mv x0, x23
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_mv_23")
    .half 0x8062        # c.mv x0, x24
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_mv_24")
    .half 0x8066        # c.mv x0, x25
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_mv_25")
    .half 0x806A        # c.mv x0, x26
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_mv_26")
    .half 0x806E        # c.mv x0, x27
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_mv_27")
    .half 0x8072        # c.mv x0, x28
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_mv_28")
    .half 0x8076        # c.mv x0, x29
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_mv_29")
    .half 0x807A        # c.mv x0, x30
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_mv_30")
    .half 0x807E        # c.mv x0, x31
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_mv_31")

cp_chint_add:
    .half 0x9006        # c.add x0, x1
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_add_1")
    .half 0x900A        # c.add x0, x2 (c.ntl.p1)
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_add_2")
    .half 0x900E        # c.add x0, x3 (c.ntl.pall)
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_add_3")
    .half 0x9012        # c.add x0, x4 (c.ntl.s1)
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_add_4")
    .half 0x9016        # c.add x0, x5 (c.ntl.all)
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_add_5")
    .half 0x901A        # c.add x0, x6
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_add_6")
    .half 0x901E        # c.add x0, x7
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_add_7")
    .half 0x9022        # c.add x0, x8
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_add_8")
    .half 0x9026        # c.add x0, x9
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_add_9")
    .half 0x902A        # c.add x0, x10
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_add_10")
    .half 0x902E        # c.add x0, x11
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_add_11")
    .half 0x9032        # c.add x0, x12
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_add_12")
    .half 0x9036        # c.add x0, x13
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_add_13")
    .half 0x903A        # c.add x0, x14
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_add_14")
    .half 0x903E        # c.add x0, x15
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_add_15")
    .half 0x9042        # c.add x0, x16
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_add_16")
    .half 0x9046        # c.add x0, x17
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_add_17")
    .half 0x904A        # c.add x0, x18
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_add_18")
    .half 0x904E        # c.add x0, x19
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_add_19")
    .half 0x9052        # c.add x0, x20
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_add_20")
    .half 0x9056        # c.add x0, x21
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_add_21")
    .half 0x905A        # c.add x0, x22
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_add_22")
    .half 0x905E        # c.add x0, x23
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_add_23")
    .half 0x9062        # c.add x0, x24
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_add_24")
    .half 0x9066        # c.add x0, x25
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_add_25")
    .half 0x906A        # c.add x0, x26
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_add_26")
    .half 0x906E        # c.add x0, x27
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_add_27")
    .half 0x9072        # c.add x0, x28
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_add_28")
    .half 0x9076        # c.add x0, x29
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_add_29")
    .half 0x907A        # c.add x0, x30
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_add_30")
    .half 0x907E        # c.add x0, x31
    RVTEST_SIGUPD(x3, x4, x5, x0, "test_1") # RVTEST_SIGUPD(x3, x4, x5, x0, "test_cp_chint_add_31")
