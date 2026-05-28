* ============================================================
* Circuit : inverter_current_starved
* Source  : ALIGN analog layout examples
* File    : inverter_current_starved\inverter_current_starved.sp
* ============================================================
* Stats:
*   Subcircuits  : 1
*   Devices (M)  : 7
*   Device types : nmos_rvt pmos_rvt
*   Passives     : 0 resistors, 0 capacitors
* Note: Converted from FinFET-style to CMOS-style netlist.
*       Device sizes are placeholders — optimizer generates new sizes.
* ============================================================

* --- DEVICE PARAMETERS ---
.param mmp0_L=40n mmp0_W=4 mmp0_Nf=2 mmp0_M=4
.param mmn0_L=40n mmn0_W=4 mmn0_Nf=2 mmn0_M=4
.param mmp1_L=40n mmp1_W=4 mmp1_Nf=2 mmp1_M=4
.param mmn1_L=40n mmn1_W=4 mmn1_Nf=2 mmn1_M=4
.param mmp2_L=40n mmp2_W=4 mmp2_Nf=2 mmp2_M=8
.param mmn2_L=40n mmn2_W=4 mmn2_Nf=2 mmn2_M=8
.param mmp3_L=40n mmp3_W=4 mmp3_Nf=2 mmp3_M=8


* --- CIRCUIT DEFINITION ---
.subckt inverter_current_starved VDDA vin vip von vop VSSA
mmp0 vop vin VDDA VDDA pmos_rvt L={mmp0_L} W={mmp0_W} Nf={mmp0_Nf} M={mmp0_M}
mmn0 vop vin VSSA VSSA nmos_rvt L={mmn0_L} W={mmn0_W} Nf={mmn0_Nf} M={mmn0_M}
mmp1 von vip vxx VDDA pmos_rvt L={mmp1_L} W={mmp1_W} Nf={mmp1_Nf} M={mmp1_M}
mmn1 von vip VSSA VSSA nmos_rvt L={mmn1_L} W={mmn1_W} Nf={mmn1_Nf} M={mmn1_M}
mmp2 von vip vxx VDDA pmos_rvt L={mmp2_L} W={mmp2_W} Nf={mmp2_Nf} M={mmp2_M}
mmn2 von vip VSSA VSSA nmos_rvt L={mmn2_L} W={mmn2_W} Nf={mmn2_Nf} M={mmn2_M}
mmp3 vxx clk VDDA VDDA pmos_rvt L={mmp3_L} W={mmp3_W} Nf={mmp3_Nf} M={mmp3_M}
.ends inverter_current_starved
