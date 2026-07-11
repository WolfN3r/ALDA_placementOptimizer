* ============================================================
* Circuit : telescopic_ota_with_bias
* Source  : ALIGN analog layout examples
* File    : telescopic_ota_with_bias\telescopic_ota_with_bias.sp
* ============================================================
* Stats:
*   Subcircuits  : 1
*   Devices (M)  : 36
*   Device types : nmos_rvt pmos_rvt
*   Passives     : 0 resistors, 0 capacitors
* Note: Converted from FinFET-style to CMOS-style netlist.
* SIZES CONVERTED 2026-07-10 scale=7.14286 source_L_ref=0.014um
*       Device/passive sizes are scaled from the real source-netlist values
*       (see marker above) -- not random placeholders.
* ============================================================

* --- DEVICE PARAMETERS ---
.param m9_L=0.15 m9_W=85.7 m9_Nf=6
.param m9s_L=0.15 m9s_W=85.7 m9s_Nf=6
.param m8_L=0.15 m8_W=85.7 m8_Nf=6
.param m8s_L=0.15 m8s_W=85.7 m8s_Nf=6
.param m5_L=0.15 m5_W=35.7 m5_Nf=4
.param m5s_L=0.15 m5s_W=35.7 m5s_Nf=4
.param m4_L=0.15 m4_W=35.7 m4_Nf=20
.param m4s_L=0.15 m4s_W=35.7 m4s_Nf=20
.param m3_L=0.15 m3_W=71.45 m3_Nf=14
.param m3s_L=0.15 m3s_W=71.45 m3s_Nf=14
.param m0_L=0.15 m0_W=71.45 m0_Nf=14
.param m0s_L=0.15 m0s_W=71.45 m0s_Nf=14
.param m7_L=0.15 m7_W=57.15 m7_Nf=12
.param m7s_L=0.15 m7s_W=57.15 m7s_Nf=12
.param m6_L=0.15 m6_W=57.15 m6_Nf=12
.param m6s_L=0.15 m6s_W=57.15 m6s_Nf=12
.param m2_L=0.15 m2_W=85.7 m2_Nf=4
.param m2s_L=0.15 m2s_W=85.7 m2s_Nf=4
.param m1_L=0.15 m1_W=85.7 m1_Nf=4
.param m1s_L=0.15 m1s_W=85.7 m1s_Nf=4
.param m10_L=0.15 m10_W=21.45 m10_Nf=2
.param m10s_L=0.15 m10s_W=21.45 m10s_Nf=2
.param m11_L=0.15 m11_W=35.7 m11_Nf=2
.param m11s_L=0.15 m11s_W=35.7 m11s_Nf=2
.param m15_L=0.15 m15_W=35.7 m15_Nf=2
.param m15s_L=0.15 m15s_W=35.7 m15s_Nf=2
.param m16_L=0.15 m16_W=35.7 m16_Nf=2
.param m16s_L=0.15 m16s_W=35.7 m16s_Nf=2
.param m17_L=0.15 m17_W=35.7 m17_Nf=2
.param m17s_L=0.15 m17s_W=35.7 m17s_Nf=2
.param m12_L=0.15 m12_W=35.7 m12_Nf=2
.param m12s_L=0.15 m12s_W=35.7 m12s_Nf=2
.param m13_L=0.15 m13_W=21.45 m13_Nf=2
.param m13s_L=0.15 m13s_W=21.45 m13s_Nf=2
.param m14_L=0.15 m14_W=35.7 m14_Nf=2
.param m14s_L=0.15 m14s_W=35.7 m14s_Nf=2


* --- CIRCUIT DEFINITION ---
** Generated for: hspiceD
** Generated on: Jun 19 10:29:58 2019
** Design library name: ALIGN_circuits_ASAP7nm
** Design cell name: switched_capacitor_filter_spice
** Design view name: schematic

** Library name: ALIGN_circuits_ASAP7nm
** Cell name: telescopic_ota
** View name: schematic
.subckt telescopic_ota_with_bias d1 VDDA vinn vinp VSSA vout
m9 vpgate vbiasn net8s VSSA nmos_rvt L={m9_L} W={m9_W} Nf={m9_Nf}
m9s net8s vbiasn net8 VSSA nmos_rvt L={m9s_L} W={m9s_W} Nf={m9s_Nf}
m8 vout vbiasn net014s VSSA nmos_rvt L={m8_L} W={m8_W} Nf={m8_Nf}
m8s net014s vbiasn net014 VSSA nmos_rvt L={m8s_L} W={m8s_W} Nf={m8s_Nf}
m5 D1 D1 netm5s VSSA nmos_rvt L={m5_L} W={m5_W} Nf={m5_Nf}
m5s netm5s D1 VSSA VSSA nmos_rvt L={m5s_L} W={m5s_W} Nf={m5s_Nf}
m4 net10 D1 netm4s VSSA nmos_rvt L={m4_L} W={m4_W} Nf={m4_Nf}
m4s netm4s D1 VSSA VSSA nmos_rvt L={m4s_L} W={m4s_W} Nf={m4s_Nf}
m3 net014 vinn netm3s VSSA nmos_rvt L={m3_L} W={m3_W} Nf={m3_Nf}
m3s netm3s vinn net10 VSSA nmos_rvt L={m3s_L} W={m3s_W} Nf={m3s_Nf}
m0 net8 vinp netm0s VSSA nmos_rvt L={m0_L} W={m0_W} Nf={m0_Nf}
m0s netm0s vinp net10 VSSA nmos_rvt L={m0s_L} W={m0s_W} Nf={m0s_Nf}
m7 vout vbiasp net012s VDDA pmos_rvt L={m7_L} W={m7_W} Nf={m7_Nf}
m7s net012s vbiasp net012 VDDA pmos_rvt L={m7s_L} W={m7s_W} Nf={m7s_Nf}
m6 vpgate vbiasp net06s VDDA pmos_rvt L={m6_L} W={m6_W} Nf={m6_Nf}
m6s net06s vbiasp net06 VDDA pmos_rvt L={m6s_L} W={m6s_W} Nf={m6s_Nf}
m2 net012 vpgate netm2s VDDA pmos_rvt L={m2_L} W={m2_W} Nf={m2_Nf}
m2s netm2s vpgate VDDA VDDA pmos_rvt L={m2s_L} W={m2s_W} Nf={m2s_Nf}
m1 net06 vpgate netm1s VDDA pmos_rvt L={m1_L} W={m1_W} Nf={m1_Nf}
m1s netm1s vpgate VDDA VDDA pmos_rvt L={m1s_L} W={m1s_W} Nf={m1s_Nf}
m10 vbiasn vbiasn net5s VSSA nmos_rvt L={m10_L} W={m10_W} Nf={m10_Nf}
m10s net5s vbiasn net5 VSSA nmos_rvt L={m10s_L} W={m10s_W} Nf={m10s_Nf}
m11 net5 vbiasn netm11s VSSA nmos_rvt L={m11_L} W={m11_W} Nf={m11_Nf}
m11s netm11s vbiasn net10 VSSA nmos_rvt L={m11s_L} W={m11s_W} Nf={m11s_Nf}
m15 net9 d1 netm15s VSSA nmos_rvt L={m15_L} W={m15_W} Nf={m15_Nf}
m15s netm15s d1 VSSA VSSA nmos_rvt L={m15s_L} W={m15s_W} Nf={m15s_Nf}
m16 net9 net9 netm16s VDDA pmos_rvt L={m16_L} W={m16_W} Nf={m16_Nf}
m16s netm16s net9 VDDA VDDA pmos_rvt L={m16s_L} W={m16s_W} Nf={m16s_Nf}
m17 vbiasn net9 netm17s VDDA pmos_rvt L={m17_L} W={m17_W} Nf={m17_Nf}
m17s netm17s net9 VDDA VDDA pmos_rvt L={m17s_L} W={m17s_W} Nf={m17s_Nf}
m12 vbiasp d1 netm12s VSSA nmos_rvt L={m12_L} W={m12_W} Nf={m12_Nf}
m12s netm12s d1 VSSA VSSA nmos_rvt L={m12s_L} W={m12s_W} Nf={m12s_Nf}
m13 vbiasp vbiasp netm13s VDDA pmos_rvt L={m13_L} W={m13_W} Nf={m13_Nf}
m13s netm13s vbiasp net7 VDDA pmos_rvt L={m13s_L} W={m13s_W} Nf={m13s_Nf}
m14 net7 vbiasp netm14s VDDA pmos_rvt L={m14_L} W={m14_W} Nf={m14_Nf}
m14s netm14s vbiasp VDDA VDDA pmos_rvt L={m14s_L} W={m14s_W} Nf={m14s_Nf}
.ends telescopic_ota_with_bias
** End of subcircuit definition.

.ends
