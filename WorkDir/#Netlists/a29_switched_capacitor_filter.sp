* ============================================================
* Circuit : switched_capacitor_filter
* Source  : ALIGN analog layout examples
* File    : switched_capacitor_filter\switched_capacitor_filter.sp
* ============================================================
* Stats:
*   Subcircuits  : 2
*   Devices (M)  : 22
*   Device types : nmos_rvt pmos_rvt
*   Passives     : 0 resistors, 10 capacitors
* Note: Converted from FinFET-style to CMOS-style netlist.
*       Device sizes are placeholders — optimizer generates new sizes.
* ============================================================

* --- DEVICE PARAMETERS ---
.param telescopic_ota_m9_L=20e-9 telescopic_ota_m9_W=9 telescopic_ota_m9_Nf=4
.param telescopic_ota_m8_L=20e-9 telescopic_ota_m8_W=9 telescopic_ota_m8_Nf=4
.param telescopic_ota_m5_L=20e-9 telescopic_ota_m5_W=6 telescopic_ota_m5_Nf=4
.param telescopic_ota_m4_L=20e-9 telescopic_ota_m4_W=6 telescopic_ota_m4_Nf=6
.param telescopic_ota_m3_L=20e-9 telescopic_ota_m3_W=12 telescopic_ota_m3_Nf=6
.param telescopic_ota_m0_L=20e-9 telescopic_ota_m0_W=12 telescopic_ota_m0_Nf=6
.param telescopic_ota_m7_L=20e-9 telescopic_ota_m7_W=12 telescopic_ota_m7_Nf=2
.param telescopic_ota_m6_L=20e-9 telescopic_ota_m6_W=12 telescopic_ota_m6_Nf=2
.param telescopic_ota_m2_L=20e-9 telescopic_ota_m2_W=6 telescopic_ota_m2_Nf=2
.param telescopic_ota_m1_L=20e-9 telescopic_ota_m1_W=6 telescopic_ota_m1_Nf=2
.param switched_capacitor_filter_m0_L=20e-9 switched_capacitor_filter_m0_W=6 switched_capacitor_filter_m0_Nf=2
.param switched_capacitor_filter_m7_L=20e-9 switched_capacitor_filter_m7_W=6 switched_capacitor_filter_m7_Nf=2
.param switched_capacitor_filter_m6_L=20e-9 switched_capacitor_filter_m6_W=6 switched_capacitor_filter_m6_Nf=2
.param switched_capacitor_filter_m3_L=20e-9 switched_capacitor_filter_m3_W=6 switched_capacitor_filter_m3_Nf=2
.param switched_capacitor_filter_m5_L=20e-9 switched_capacitor_filter_m5_W=6 switched_capacitor_filter_m5_Nf=2
.param switched_capacitor_filter_m4_L=20e-9 switched_capacitor_filter_m4_W=6 switched_capacitor_filter_m4_Nf=2
.param switched_capacitor_filter_m8_L=20e-9 switched_capacitor_filter_m8_W=6 switched_capacitor_filter_m8_Nf=2
.param switched_capacitor_filter_m11_L=20e-9 switched_capacitor_filter_m11_W=6 switched_capacitor_filter_m11_Nf=2
.param switched_capacitor_filter_m9_L=20e-9 switched_capacitor_filter_m9_W=6 switched_capacitor_filter_m9_Nf=2
.param switched_capacitor_filter_m10_L=20e-9 switched_capacitor_filter_m10_W=6 switched_capacitor_filter_m10_Nf=2
.param switched_capacitor_filter_m12_L=20e-9 switched_capacitor_filter_m12_W=6 switched_capacitor_filter_m12_Nf=2
.param switched_capacitor_filter_m14_L=20e-9 switched_capacitor_filter_m14_W=6 switched_capacitor_filter_m14_Nf=2


* --- CIRCUIT DEFINITION ---
** Generated for: hspiceD
** Generated on: Jun 19 10:29:58 2019
** Design library name: ALIGN_circuits_ASAP7nm
** Design cell name: switched_capacitor_filter_spice
** Design view name: schematic


.TEMP 25.0
.OPTION INGOLD=2 ARTIST=2 PSF=2 MEASOUT=1 PARHIER=LOCAL PROBE=0 MARCH=2 ACCURACY=1 POST
** Library name: ALIGN_circuits_ASAP7nm
** Cell name: telescopic_ota
** View name: schematic
.subckt telescopic_ota d1 VDDA vinn vinp VSSA vbiasn vbiasp1 vbiasp2 voutn voutp
m9 voutn vbiasn net8 VSSA nmos_rvt L={telescopic_ota_m9_L} W={telescopic_ota_m9_W} Nf={telescopic_ota_m9_Nf}
m8 voutp vbiasn net014 VSSA nmos_rvt L={telescopic_ota_m8_L} W={telescopic_ota_m8_W} Nf={telescopic_ota_m8_Nf}
m5 d1 d1 VSSA VSSA nmos_rvt L={telescopic_ota_m5_L} W={telescopic_ota_m5_W} Nf={telescopic_ota_m5_Nf}
m4 net10 d1 VSSA VSSA nmos_rvt L={telescopic_ota_m4_L} W={telescopic_ota_m4_W} Nf={telescopic_ota_m4_Nf}
m3 net014 vinn net10 VSSA nmos_rvt L={telescopic_ota_m3_L} W={telescopic_ota_m3_W} Nf={telescopic_ota_m3_Nf}
m0 net8 vinp net10 VSSA nmos_rvt L={telescopic_ota_m0_L} W={telescopic_ota_m0_W} Nf={telescopic_ota_m0_Nf}
m7 voutp vbiasp2 net012 net012 pmos_rvt L={telescopic_ota_m7_L} W={telescopic_ota_m7_W} Nf={telescopic_ota_m7_Nf}
m6 voutn vbiasp2 net06 net06 pmos_rvt L={telescopic_ota_m6_L} W={telescopic_ota_m6_W} Nf={telescopic_ota_m6_Nf}
m2 net012 vbiasp1 VDDA VDDA pmos_rvt L={telescopic_ota_m2_L} W={telescopic_ota_m2_W} Nf={telescopic_ota_m2_Nf}
m1 net06 vbiasp1 VDDA VDDA pmos_rvt L={telescopic_ota_m1_L} W={telescopic_ota_m1_W} Nf={telescopic_ota_m1_Nf}
.ends telescopic_ota
** End of subcircuit definition.

** Library name: ALIGN_circuits_ASAP7nm
** Cell name: switched_capacitor_filter_spice
** View name: schematic

.subckt switched_capacitor_filter voutn voutp vinp vinn id agnd VSSA VDDA
m0 voutn phi1 net67 VSSA nmos_rvt L={switched_capacitor_filter_m0_L} W={switched_capacitor_filter_m0_W} Nf={switched_capacitor_filter_m0_Nf}
m7 net66 phi1 net63 VSSA nmos_rvt L={switched_capacitor_filter_m7_L} W={switched_capacitor_filter_m7_W} Nf={switched_capacitor_filter_m7_Nf}
m6 net72 phi1 vinn VSSA nmos_rvt L={switched_capacitor_filter_m6_L} W={switched_capacitor_filter_m6_W} Nf={switched_capacitor_filter_m6_Nf}
m3 agnd phi2 net67 VSSA nmos_rvt L={switched_capacitor_filter_m3_L} W={switched_capacitor_filter_m3_W} Nf={switched_capacitor_filter_m3_Nf}
m5 agnd phi2 net63 VSSA nmos_rvt L={switched_capacitor_filter_m5_L} W={switched_capacitor_filter_m5_W} Nf={switched_capacitor_filter_m5_Nf}
m4 net72 phi2 agnd VSSA nmos_rvt L={switched_capacitor_filter_m4_L} W={switched_capacitor_filter_m4_W} Nf={switched_capacitor_filter_m4_Nf}
m8 net60 phi2 agnd VSSA nmos_rvt L={switched_capacitor_filter_m8_L} W={switched_capacitor_filter_m8_W} Nf={switched_capacitor_filter_m8_Nf}
m11 agnd phi2 net68 VSSA nmos_rvt L={switched_capacitor_filter_m11_L} W={switched_capacitor_filter_m11_W} Nf={switched_capacitor_filter_m11_Nf}
m9 agnd phi2 net62 VSSA nmos_rvt L={switched_capacitor_filter_m9_L} W={switched_capacitor_filter_m9_W} Nf={switched_capacitor_filter_m9_Nf}
m10 net64 phi1 net62 VSSA nmos_rvt L={switched_capacitor_filter_m10_L} W={switched_capacitor_filter_m10_W} Nf={switched_capacitor_filter_m10_Nf}
m12 net60 phi1 vinp VSSA nmos_rvt L={switched_capacitor_filter_m12_L} W={switched_capacitor_filter_m12_W} Nf={switched_capacitor_filter_m12_Nf}
m14 voutp phi1 net68 VSSA nmos_rvt L={switched_capacitor_filter_m14_L} W={switched_capacitor_filter_m14_W} Nf={switched_capacitor_filter_m14_Nf}
xi0 id VDDA net64 net66 VSSA vbiasn vbiasp1 vbiasp2 voutn voutp telescopic_ota
c9 voutp VSSA 60e-15
c8 voutn VSSA 60e-15
c7 net62 net68 30e-15
c6 net64 voutp 60e-15
c5 vinn net64 30e-15
c4 net60 net62 60e-15
c3 net66 voutn 60e-15
c2 vinp net66 30e-15
c1 net63 net67 30e-15
c0 net72 net63 60e-15
.ends switched_capacitor_filter
