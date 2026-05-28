* ============================================================
* Circuit : telescopic_ota_multi_connection
* Source  : ALIGN analog layout examples
* File    : telescopic_ota_multi_connection\telescopic_ota_multi_connection.sp
* ============================================================
* Stats:
*   Subcircuits  : 1
*   Devices (M)  : 10
*   Device types : nmos_rvt pmos_rvt
*   Passives     : 0 resistors, 0 capacitors
* Note: Converted from FinFET-style to CMOS-style netlist.
*       Device sizes are placeholders — optimizer generates new sizes.
* ============================================================

* --- DEVICE PARAMETERS ---
.param m9_L=20e-9 m9_W=9 m9_Nf=4
.param m8_L=20e-9 m8_W=9 m8_Nf=4
.param m5_L=20e-9 m5_W=9 m5_Nf=2
.param m4_L=20e-9 m4_W=9 m4_Nf=4
.param m3_L=20e-9 m3_W=9 m3_Nf=12
.param m0_L=20e-9 m0_W=9 m0_Nf=12
.param m7_L=20e-9 m7_W=12 m7_Nf=2
.param m6_L=20e-9 m6_W=12 m6_Nf=2
.param m2_L=20e-9 m2_W=6 m2_Nf=2
.param m1_L=20e-9 m1_W=6 m1_Nf=2


* --- CIRCUIT DEFINITION ---
.subckt telescopic_ota_multi_connection d1 VDDA vinn vinp VSSA vbiasn vbiasp1 vbiasp2 voutn voutp
m9 voutn vbiasn net8 VSSA nmos_rvt L={m9_L} W={m9_W} Nf={m9_Nf}
m8 voutp vbiasn net014 VSSA nmos_rvt L={m8_L} W={m8_W} Nf={m8_Nf}
m5 d1 d1 VSSA VSSA nmos_rvt L={m5_L} W={m5_W} Nf={m5_Nf}
m4 net10 d1 VSSA VSSA nmos_rvt L={m4_L} W={m4_W} Nf={m4_Nf}
m3 net014 vinn net10 VSSA nmos_rvt L={m3_L} W={m3_W} Nf={m3_Nf}
m0 net8 vinp net10 VSSA nmos_rvt L={m0_L} W={m0_W} Nf={m0_Nf}
m7 voutp vbiasp2 net06 VDDA pmos_rvt L={m7_L} W={m7_W} Nf={m7_Nf}
m6 voutn vbiasp2 net06 VDDA pmos_rvt L={m6_L} W={m6_W} Nf={m6_Nf}
m2 net06 vbiasp1 VDDA VDDA pmos_rvt L={m2_L} W={m2_W} Nf={m2_Nf}
m1 net06 vbiasp1 VDDA VDDA pmos_rvt L={m1_L} W={m1_W} Nf={m1_Nf}
.ends telescopic_ota_multi_connection
