* ============================================================
* Circuit : high_speed_comparator_charge_flow
* Source  : ALIGN analog layout examples
* File    : high_speed_comparator_charge_flow\high_speed_comparator_charge_flow.sp
* ============================================================
* Stats:
*   Subcircuits  : 1
*   Devices (M)  : 15
*   Device types : nmos_rvt pmos_rvt
*   Passives     : 0 resistors, 0 capacitors
* Note: Converted from FinFET-style to CMOS-style netlist.
*       Device sizes are placeholders — optimizer generates new sizes.
* ============================================================

* --- DEVICE PARAMETERS ---
.param mn0_W=6 mn0_Nf=2 mn0_L=14e-9 mn0_M=8
.param mn1_W=6 mn1_Nf=2 mn1_L=14e-9 mn1_M=16
.param mn2_W=6 mn2_Nf=2 mn2_L=14e-9 mn2_M=16
.param mn3_W=6 mn3_Nf=2 mn3_L=14e-9 mn3_M=8
.param mn4_W=6 mn4_Nf=2 mn4_L=14e-9 mn4_M=8
.param mp5_W=6 mp5_Nf=2 mp5_L=14e-9 mp5_M=4
.param mp6_W=6 mp6_Nf=2 mp6_L=14e-9 mp6_M=4
.param mp7_W=6 mp7_Nf=2 mp7_L=14e-9 mp7_M=1
.param mp8_W=6 mp8_Nf=2 mp8_L=14e-9 mp8_M=1
.param mp9_W=6 mp9_Nf=2 mp9_L=14e-9 mp9_M=1
.param mp10_W=6 mp10_Nf=2 mp10_L=14e-9 mp10_M=1
.param mp11_W=6 mp11_Nf=2 mp11_L=14e-9 mp11_M=1
.param mn13_W=6 mn13_Nf=2 mn13_L=14e-9 mn13_M=1
.param mp12_W=6 mp12_Nf=2 mp12_L=14e-9 mp12_M=1
.param mn14_W=6 mn14_Nf=2 mn14_L=14e-9 mn14_M=1


* --- CIRCUIT DEFINITION ---
.subckt high_speed_comparator_charge_flow clk VDDA vin vip von vop VSSA

mn0 vcom clk VSSA VSSA nmos_rvt W={mn0_W} Nf={mn0_Nf} L={mn0_L} M={mn0_M}

mn1 vin_d vin vcom VSSA nmos_rvt W={mn1_W} Nf={mn1_Nf} L={mn1_L} M={mn1_M}
mn2 vip_d vip vcom VSSA nmos_rvt W={mn2_W} Nf={mn2_Nf} L={mn2_L} M={mn2_M}

mn3 vin_o vip_o vin_d VSSA nmos_rvt W={mn3_W} Nf={mn3_Nf} L={mn3_L} M={mn3_M}
mn4 vip_o vin_o vip_d VSSA nmos_rvt W={mn4_W} Nf={mn4_Nf} L={mn4_L} M={mn4_M}

mp5 vin_o vip_o VDDA VDDA pmos_rvt W={mp5_W} Nf={mp5_Nf} L={mp5_L} M={mp5_M}
mp6 vip_o vin_o VDDA VDDA pmos_rvt W={mp6_W} Nf={mp6_Nf} L={mp6_L} M={mp6_M}

mp7 vin_d clk VDDA VDDA pmos_rvt W={mp7_W} Nf={mp7_Nf} L={mp7_L} M={mp7_M}
mp8 vip_d clk VDDA VDDA pmos_rvt W={mp8_W} Nf={mp8_Nf} L={mp8_L} M={mp8_M}

mp9 vin_o clk VDDA VDDA pmos_rvt W={mp9_W} Nf={mp9_Nf} L={mp9_L} M={mp9_M}
mp10 vip_o clk VDDA VDDA pmos_rvt W={mp10_W} Nf={mp10_Nf} L={mp10_L} M={mp10_M}

mp11 vop vip_o VDDA VDDA pmos_rvt W={mp11_W} Nf={mp11_Nf} L={mp11_L} M={mp11_M}
mn13 vop vip_o VSSA VSSA nmos_rvt W={mn13_W} Nf={mn13_Nf} L={mn13_L} M={mn13_M}

mp12 von vin_o VDDA VDDA pmos_rvt W={mp12_W} Nf={mp12_Nf} L={mp12_L} M={mp12_M}
mn14 von vin_o VSSA VSSA nmos_rvt W={mn14_W} Nf={mn14_Nf} L={mn14_L} M={mn14_M}

.ends high_speed_comparator_charge_flow
