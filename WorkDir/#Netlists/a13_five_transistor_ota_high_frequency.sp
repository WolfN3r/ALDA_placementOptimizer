* ============================================================
* Circuit : five_transistor_ota_high_frequency
* Source  : ALIGN analog layout examples
* File    : five_transistor_ota_high_frequency\five_transistor_ota_high_frequency.sp
* ============================================================
* Stats:
*   Subcircuits  : 1
*   Devices (M)  : 6
*   Device types : nmos_rvt pmos_rvt
*   Passives     : 0 resistors, 0 capacitors
* Note: Converted from FinFET-style to CMOS-style netlist.
*       Device sizes are placeholders — optimizer generates new sizes.
* ============================================================

* --- DEVICE PARAMETERS ---
.param m5_M=1 m5_L=14e-9 m5_W=12 m5_Nf=2
.param m4_L=14e-9 m4_W=12 m4_Nf=2
.param m3_M=1 m3_L=14e-9 m3_W=12 m3_Nf=2
.param m2_M=1 m2_L=14e-9 m2_W=12 m2_Nf=16
.param m1_M=1 m1_L=14e-9 m1_W=12 m1_Nf=40
.param m0_M=1 m0_L=14e-9 m0_W=12 m0_Nf=40


* --- CIRCUIT DEFINITION ---
.subckt five_transistor_ota_high_frequency vinn_ota vinp_ota vout_ota id_ota VDDA VSSA
m5 vout_ota net19 VDDA VDDA pmos_rvt M={m5_M} L={m5_L} W={m5_W} Nf={m5_Nf}
m4 net19 net19 VDDA VDDA pmos_rvt L={m4_L} W={m4_W} Nf={m4_Nf}
m3 id_ota id_ota VSSA VSSA nmos_rvt M={m3_M} L={m3_L} W={m3_W} Nf={m3_Nf}
m2 net017 id_ota VSSA VSSA nmos_rvt M={m2_M} L={m2_L} W={m2_W} Nf={m2_Nf}
m1 vout_ota vinn_ota net017 VSSA nmos_rvt M={m1_M} L={m1_L} W={m1_W} Nf={m1_Nf}
m0 net19 vinp_ota net017 VSSA nmos_rvt M={m0_M} L={m0_L} W={m0_W} Nf={m0_Nf}
.ends five_transistor_ota_high_frequency
