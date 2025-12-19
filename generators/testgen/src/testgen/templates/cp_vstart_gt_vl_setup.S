///////////////////////////////////////////
// cp_vstart_gt_vl_setup.S
//
// Set up function of vstart and vl for cp_vstart_gt_vl_setup in ExceptionsV
// Goal: generate vl and vstart where VLMAX > vstart > vl > 0
///////////////////////////////////////////

j    end_cp_vstart_gt_vl_setup       # jump past the function when not called

cp_vstart_gt_vl_setup:
    vsetvli x8, x0, SEWSIZE, m4, tu, mu  # x8 = VLMAX
    remu a0, a0, x8                      # ensure that a0 < VLMAX by a0 % VLMAX
    remu a1, a1, x8                      # ensure that a1 < VLMAX by a1 % VLMAX

    zero_check:  # ensure that both vstart and vl are greater than 0
    beqz a0, add_a0                      # add to a0 if a0 == 0
    remu a0, a0, x8                      # ensure that a0 < VLMAX by a0 % VLMAX
    beqz a1, add_a1                      # add to a1 if a1 == 0
    remu a1, a1, x8                      # ensure that a1 < VLMAX by a1 % VLMAX
    j    compare

add_a0:      # add to a0 to make a0 > 0
    addi a0, a0, 1
    j    zero_check                      # jump back to zero_check to ensure that both a0, a1 > 0

add_a1:      # add to a1 to make a1 > 0
    addi a1, a1, 1
    j    zero_check                      # jump back to zero_check to ensure that both a0, a1 > 0

compare:     # compare place holder values to assign CSRs accordingly
    blt  a1, a0, a0a1_swap               # if a1 < a0, jump to assign vl = a1 and vstart = a0
    beq  a1, a0, a0a1_equal              # if a1 = a0, jump to modify one of the placeholder values
    j    a0a1_keep                       # if a1 > a0, jump to assign vstart = a1 and vl = a0

a0a1_equal:  # VLMAX > a1 = a0, modify one of the placeholder values
    addi a1, a1, 1                       # add to a1 (vstart place holder) to create a1 > a0
    remu a1, a1, x8                      # ensure that a1 < VLMAX by a1 % VLMAX
    j    zero_check                      # compare again in case a1 = 0 after the rem operation

a0a1_keep:   # VLMAX > a1 > a0, assign CSRs such that VLMAX > vstart > vl
    vsetvli x8, a0, SEWSIZE, m4, tu, mu  # set vl = a0
    csrw vstart, a1                      # set vstart = v4
    ret                                  # return to cp_vstart_gt_vl test after set up

a0a1_swap:   # VLMAX > a0 > a1, assign CSRs such that VLMAX > vstart > vl
    vsetvli x8, a1, SEWSIZE, m4, tu, mu  # set vl = a1
    csrw vstart, a0                      # set vstart = a0
    ret                                  # return to cp_vstart_gt_vl test after set up

end_cp_vstart_gt_vl_setup:
