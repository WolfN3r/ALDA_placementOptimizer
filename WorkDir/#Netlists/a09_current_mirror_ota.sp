* ============================================================
* Circuit : current_mirror_ota
* Source  : ALIGN analog layout examples
* File    : current_mirror_ota\current_mirror_ota.sp
* ============================================================
* Stats:
*   Subcircuits  : 1
*   Devices (M)  : 12
*   Device types : nmos_rvt pmos_rvt
*   Passives     : 0 resistors, 0 capacitors
* Note: Converted from FinFET-style to CMOS-style netlist.
* SIZES CONVERTED 2026-07-10 scale=7.14286 source_L_ref=0.014um
*       Device/passive sizes are scaled from the real source-netlist values
*       (see marker above) -- not random placeholders.
* ============================================================

* --- DEVICE PARAMETERS ---
.param m17_L=0.15 m17_W=50 m17_Nf=4
.param m16_L=0.15 m16_W=35.7 m16_Nf=2
.param m15_L=0.15 m15_W=50 m15_Nf=4
.param m14_L=0.15 m14_W=35.7 m14_Nf=2
.param m11_L=0.15 m11_W=85.7 m11_Nf=2
.param m10_L=0.15 m10_W=85.7 m10_Nf=2
.param m21_L=0.15 m21_W=71.45 m21_Nf=6
.param m20_L=0.15 m20_W=71.45 m20_Nf=24
.param m20s_L=0.15 m20s_W=71.45 m20s_Nf=24
.param m19_L=0.15 m19_W=71.45 m19_Nf=6
.param m18_L=0.15 m18_W=71.45 m18_Nf=24
.param m18s_L=0.15 m18s_W=71.45 m18s_Nf=24


* --- CIRCUIT DEFINITION ---
.subckt current_mirror_ota id vinn vinp VSSA VDDA voutp vbiasnd
m17 net16 vinn net24 VSSA nmos_rvt L={m17_L} W={m17_W} Nf={m17_Nf}
m16 net24 id VSSA VSSA nmos_rvt L={m16_L} W={m16_W} Nf={m16_Nf}
m15 net27 vinp net24 VSSA nmos_rvt L={m15_L} W={m15_W} Nf={m15_Nf}
m14 id id VSSA VSSA nmos_rvt L={m14_L} W={m14_W} Nf={m14_Nf}
m11 vbiasnd vbiasnd VSSA VSSA nmos_rvt L={m11_L} W={m11_W} Nf={m11_Nf}
m10 voutp vbiasnd VSSA VSSA nmos_rvt L={m10_L} W={m10_W} Nf={m10_Nf}
m21 net16 net16 VDDA VDDA pmos_rvt L={m21_L} W={m21_W} Nf={m21_Nf}
m20 m20stack net16 VDDA VDDA pmos_rvt L={m20_L} W={m20_W} Nf={m20_Nf}
m20s vbiasnd net16 m20stack VDDA pmos_rvt L={m20s_L} W={m20s_W} Nf={m20s_Nf}
m19 net27 net27 VDDA VDDA pmos_rvt L={m19_L} W={m19_W} Nf={m19_Nf}
m18 m18stack net27 VDDA VDDA pmos_rvt L={m18_L} W={m18_W} Nf={m18_Nf}
m18s voutp net27 m18stack VDDA pmos_rvt L={m18s_L} W={m18s_W} Nf={m18s_Nf}
.ends current_mirror_ota
