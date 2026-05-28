* ============================================================
* Circuit : cascode_current_mirror_ota
* Source  : ALIGN analog layout examples
* File    : cascode_current_mirror_ota\cascode_current_mirror_ota.sp
* ============================================================
* Stats:
*   Subcircuits  : 1
*   Devices (M)  : 20
*   Device types : nmos_rvt pmos_rvt
*   Passives     : 0 resistors, 0 capacitors
* Note: Converted from FinFET-style to CMOS-style netlist.
*       Device sizes are placeholders — optimizer generates new sizes.
* ============================================================

* --- DEVICE PARAMETERS ---
.param m25_L=20e-9 m25_W=12 m25_Nf=2
.param m24_L=20e-9 m24_W=12 m24_Nf=2
.param m17_L=20e-9 m17_W=8 m17_Nf=4
.param m16_L=20e-9 m16_W=8 m16_Nf=2
.param m15_L=20e-9 m15_W=8 m15_Nf=4
.param m14_L=20e-9 m14_W=8 m14_Nf=2
.param m11_L=20e-9 m11_W=8 m11_Nf=4
.param m10_L=20e-9 m10_W=8 m10_Nf=4
.param m1nup_L=20e-9 m1nup_W=2 m1nup_Nf=2
.param m1ndown_L=20e-9 m1ndown_W=3 m1ndown_Nf=2
.param m1pup_L=20e-9 m1pup_W=3 m1pup_Nf=2
.param m1pdown_L=20e-9 m1pdown_W=3 m1pdown_Nf=2
.param m27_L=20e-9 m27_W=10 m27_Nf=6
.param m26_L=20e-9 m26_W=10 m26_Nf=6
.param m23_L=20e-9 m23_W=12 m23_Nf=10
.param m22_L=20e-9 m22_W=12 m22_Nf=10
.param m21_L=20e-9 m21_W=3 m21_Nf=2
.param m20_L=20e-9 m20_W=5 m20_Nf=2
.param m19_L=20e-9 m19_W=3 m19_Nf=2
.param m18_L=20e-9 m18_W=5 m18_Nf=2


* --- CIRCUIT DEFINITION ---
.subckt cascode_current_mirror_ota id vbiasn vbiasnd vbiasp vinn vinp voutp VSSA VDDA
m25 voutp vbiasn net034 VSSA nmos_rvt L={m25_L} W={m25_W} Nf={m25_Nf}
m24 vbiasnd vbiasn net033 VSSA nmos_rvt L={m24_L} W={m24_W} Nf={m24_Nf}
m17 net16 vinn net24 VSSA nmos_rvt L={m17_L} W={m17_W} Nf={m17_Nf}
m16 net24 id VSSA VSSA nmos_rvt L={m16_L} W={m16_W} Nf={m16_Nf}
m15 net27 vinp net24 VSSA nmos_rvt L={m15_L} W={m15_W} Nf={m15_Nf}
m14 id id VSSA VSSA nmos_rvt L={m14_L} W={m14_W} Nf={m14_Nf}
m11 net033 vbiasnd VSSA VSSA nmos_rvt L={m11_L} W={m11_W} Nf={m11_Nf}
m10 net034 vbiasnd VSSA VSSA nmos_rvt L={m10_L} W={m10_W} Nf={m10_Nf}

m1nup vbiasn vbiasn net9b VSSA nmos_rvt L={m1nup_L} W={m1nup_W} Nf={m1nup_Nf}
m1ndown net9b net9b VSSA VSSA nmos_rvt L={m1ndown_L} W={m1ndown_W} Nf={m1ndown_Nf}

m1pup net8b net8b VDDA VDDA pmos_rvt L={m1pup_L} W={m1pup_W} Nf={m1pup_Nf}
m1pdown vbiasp vbiasp net8b VDDA pmos_rvt L={m1pdown_L} W={m1pdown_W} Nf={m1pdown_Nf}
m27 net27 vbiasp net021 VDDA pmos_rvt L={m27_L} W={m27_W} Nf={m27_Nf}
m26 net16 vbiasp net015 VDDA pmos_rvt L={m26_L} W={m26_W} Nf={m26_Nf}
m23 voutp vbiasp net024 VDDA pmos_rvt L={m23_L} W={m23_W} Nf={m23_Nf}
m22 vbiasnd vbiasp net06 VDDA pmos_rvt L={m22_L} W={m22_W} Nf={m22_Nf}
m21 net015 net16 VDDA VDDA pmos_rvt L={m21_L} W={m21_W} Nf={m21_Nf}
m20 net06 net16 VDDA VDDA pmos_rvt L={m20_L} W={m20_W} Nf={m20_Nf}
m19 net021 net27 VDDA VDDA pmos_rvt L={m19_L} W={m19_W} Nf={m19_Nf}
m18 net024 net27 VDDA VDDA pmos_rvt L={m18_L} W={m18_W} Nf={m18_Nf}
.ends cascode_current_mirror_ota
