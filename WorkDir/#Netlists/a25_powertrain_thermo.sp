* ============================================================
* Circuit : powertrain_thermo
* Source  : ALIGN analog layout examples
* File    : powertrain_thermo\powertrain_thermo.sp
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

.subckt powertrain_thermo on_d[15] on_d[14] on_d[13] on_d[12] on_d[11] on_d[10] on_d[9] on_d[8] on_d[7] on_d[6] on_d[5] on_d[4] on_d[3] on_d[2] on_d[1] on_d[0] VDDA vout
xu_pmos_title[15] on_d[15] VDDA vout powertrain_cell
xu_pmos_title[14] on_d[14] VDDA vout powertrain_cell
xu_pmos_title[13] on_d[13] VDDA vout powertrain_cell
xu_pmos_title[12] on_d[12] VDDA vout powertrain_cell
xu_pmos_title[11] on_d[11] VDDA vout powertrain_cell
xu_pmos_title[10] on_d[10] VDDA vout powertrain_cell
xu_pmos_title[9] on_d[9] VDDA vout powertrain_cell
xu_pmos_title[8] on_d[8] VDDA vout powertrain_cell
xu_pmos_title[7] on_d[7] VDDA vout powertrain_cell
xu_pmos_title[6] on_d[6] VDDA vout powertrain_cell
xu_pmos_title[5] on_d[5] VDDA vout powertrain_cell
xu_pmos_title[4] on_d[4] VDDA vout powertrain_cell
xu_pmos_title[3] on_d[3] VDDA vout powertrain_cell
xu_pmos_title[2] on_d[2] VDDA vout powertrain_cell
xu_pmos_title[1] on_d[1] VDDA vout powertrain_cell
xu_pmos_title[0] on_d[0] VDDA vout powertrain_cell
.ends powertrain_thermo
