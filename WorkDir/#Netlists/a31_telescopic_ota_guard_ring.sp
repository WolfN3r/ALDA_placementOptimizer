* ============================================================
* Circuit : telescopic_ota_guard_ring
* Source  : ALIGN analog layout examples
* File    : telescopic_ota_guard_ring\telescopic_ota_guard_ring.sp
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
.param m1_L=20e-9 m1_W=8 m1_Nf=4
.param m2_L=20e-9 m2_W=8 m2_Nf=4
.param m5_L=20e-9 m5_Nf=2
.param m6_L=20e-9 m6_Nf=2
.param m8_L=20e-9 m8_W=8 m8_Nf=2
.param m7_L=20e-9 m7_W=8 m7_Nf=2
.param m10_L=20e-9 m10_W=8 m10_Nf=4
.param m9_L=20e-9 m9_W=8 m9_Nf=4
.param m4_L=20e-9 m4_W=12 m4_Nf=6
.param m3_L=20e-9 m3_W=12 m3_Nf=6


* --- CIRCUIT DEFINITION ---
.subckt telescopic_ota_guard_ring vbiasn vbiasp1 vbiasp2 vinn vinp voutn voutp VDDA VSSA
.param no_of_fin = 5
m1 id id VSSA VSSA nmos_rvt L={m1_L} W={m1_W} Nf={m1_Nf}
m2 net10 id VSSA VSSA nmos_rvt L={m2_L} W={m2_W} Nf={m2_Nf}
m5 voutn vbiasn net8 0 nmos_rvt L={m5_L} W=no_of_fin Nf={m5_Nf}
m6 voutp vbiasn net014 0 nmos_rvt L={m6_L} W=no_of_fin Nf={m6_Nf}
m8 voutp vbiasp1 net012 VDDA pmos_rvt L={m8_L} W={m8_W} Nf={m8_Nf}
m7 voutn vbiasp1 net06 VDDA pmos_rvt L={m7_L} W={m7_W} Nf={m7_Nf}
m10 net012 vbiasp2 VDDA VDDA pmos_rvt L={m10_L} W={m10_W} Nf={m10_Nf}
m9 net06 vbiasp2 VDDA VDDA pmos_rvt L={m9_L} W={m9_W} Nf={m9_Nf}
m4 net014 vinn net10 0 nmos_rvt L={m4_L} W={m4_W} Nf={m4_Nf}
m3 net8 vinp net10 0 nmos_rvt L={m3_L} W={m3_W} Nf={m3_Nf}
.ends telescopic_ota_guard_ring
** End of subcircuit definition.
