* ============================================================
* Circuit : powertrain_binary
* Source  : ALIGN analog layout examples
* File    : powertrain_binary\powertrain_binary.sp
* ============================================================
* Stats:
*   Subcircuits  : 2
*   Devices (M)  : 1
*   Device types : pmos_rvt
*   Passives     : 0 resistors, 0 capacitors
* Note: Converted from FinFET-style to CMOS-style netlist.
*       Device sizes are placeholders — optimizer generates new sizes.
* ============================================================

* --- DEVICE PARAMETERS ---
.param powertrain_cell_mmp0_L=40n powertrain_cell_mmp0_W=4 powertrain_cell_mmp0_Nf=8 powertrain_cell_mmp0_M=4


* --- CIRCUIT DEFINITION ---
.subckt powertrain_cell ond VDDA vout
mmp0 vout ond VDDA VDDA pmos_rvt L={powertrain_cell_mmp0_L} W={powertrain_cell_mmp0_W} Nf={powertrain_cell_mmp0_Nf} M={powertrain_cell_mmp0_M}
.ends powertrain_cell

.subckt powertrain_binary on_d[5] on_d[4] on_d[3] on_d[2] on_d[1] on_d[0] VDDA vout
xu_pmos_1[2] on_d[1] VDDA vout powertrain_cell
xu_pmos_1[1] on_d[1] VDDA vout powertrain_cell
xu_pmos_5[32] on_d[5] VDDA vout powertrain_cell
xu_pmos_5[31] on_d[5] VDDA vout powertrain_cell
xu_pmos_5[30] on_d[5] VDDA vout powertrain_cell
xu_pmos_5[29] on_d[5] VDDA vout powertrain_cell
xu_pmos_5[28] on_d[5] VDDA vout powertrain_cell
xu_pmos_5[27] on_d[5] VDDA vout powertrain_cell
xu_pmos_5[26] on_d[5] VDDA vout powertrain_cell
xu_pmos_5[25] on_d[5] VDDA vout powertrain_cell
xu_pmos_5[24] on_d[5] VDDA vout powertrain_cell
xu_pmos_5[23] on_d[5] VDDA vout powertrain_cell
xu_pmos_5[22] on_d[5] VDDA vout powertrain_cell
xu_pmos_5[21] on_d[5] VDDA vout powertrain_cell
xu_pmos_5[20] on_d[5] VDDA vout powertrain_cell
xu_pmos_5[19] on_d[5] VDDA vout powertrain_cell
xu_pmos_5[18] on_d[5] VDDA vout powertrain_cell
xu_pmos_5[17] on_d[5] VDDA vout powertrain_cell
xu_pmos_5[16] on_d[5] VDDA vout powertrain_cell
xu_pmos_5[15] on_d[5] VDDA vout powertrain_cell
xu_pmos_5[14] on_d[5] VDDA vout powertrain_cell
xu_pmos_5[13] on_d[5] VDDA vout powertrain_cell
xu_pmos_5[12] on_d[5] VDDA vout powertrain_cell
xu_pmos_5[11] on_d[5] VDDA vout powertrain_cell
xu_pmos_5[10] on_d[5] VDDA vout powertrain_cell
xu_pmos_5[9] on_d[5] VDDA vout powertrain_cell
xu_pmos_5[8] on_d[5] VDDA vout powertrain_cell
xu_pmos_5[7] on_d[5] VDDA vout powertrain_cell
xu_pmos_5[6] on_d[5] VDDA vout powertrain_cell
xu_pmos_5[5] on_d[5] VDDA vout powertrain_cell
xu_pmos_5[4] on_d[5] VDDA vout powertrain_cell
xu_pmos_5[3] on_d[5] VDDA vout powertrain_cell
xu_pmos_5[2] on_d[5] VDDA vout powertrain_cell
xu_pmos_5[1] on_d[5] VDDA vout powertrain_cell
xu_pmos_4[16] on_d[4] VDDA vout powertrain_cell
xu_pmos_4[15] on_d[4] VDDA vout powertrain_cell
xu_pmos_4[14] on_d[4] VDDA vout powertrain_cell
xu_pmos_4[13] on_d[4] VDDA vout powertrain_cell
xu_pmos_4[12] on_d[4] VDDA vout powertrain_cell
xu_pmos_4[11] on_d[4] VDDA vout powertrain_cell
xu_pmos_4[10] on_d[4] VDDA vout powertrain_cell
xu_pmos_4[9] on_d[4] VDDA vout powertrain_cell
xu_pmos_4[8] on_d[4] VDDA vout powertrain_cell
xu_pmos_4[7] on_d[4] VDDA vout powertrain_cell
xu_pmos_4[6] on_d[4] VDDA vout powertrain_cell
xu_pmos_4[5] on_d[4] VDDA vout powertrain_cell
xu_pmos_4[4] on_d[4] VDDA vout powertrain_cell
xu_pmos_4[3] on_d[4] VDDA vout powertrain_cell
xu_pmos_4[2] on_d[4] VDDA vout powertrain_cell
xu_pmos_4[1] on_d[4] VDDA vout powertrain_cell
xu_pmos_3[8] on_d[3] VDDA vout powertrain_cell
xu_pmos_3[7] on_d[3] VDDA vout powertrain_cell
xu_pmos_3[6] on_d[3] VDDA vout powertrain_cell
xu_pmos_3[5] on_d[3] VDDA vout powertrain_cell
xu_pmos_3[4] on_d[3] VDDA vout powertrain_cell
xu_pmos_3[3] on_d[3] VDDA vout powertrain_cell
xu_pmos_3[2] on_d[3] VDDA vout powertrain_cell
xu_pmos_3[1] on_d[3] VDDA vout powertrain_cell
xu_pmos_2[4] on_d[2] VDDA vout powertrain_cell
xu_pmos_2[3] on_d[2] VDDA vout powertrain_cell
xu_pmos_2[2] on_d[2] VDDA vout powertrain_cell
xu_pmos_2[1] on_d[2] VDDA vout powertrain_cell
xu_pmos_0 on_d[0] VDDA vout powertrain_cell
.ends powertrain_binary
