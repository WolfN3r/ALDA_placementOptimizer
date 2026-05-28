* ============================================================
* Circuit : sc_dc_dc_converter
* Source  : ALIGN analog layout examples
* File    : sc_dc_dc_converter\sc_dc_dc_converter.sp
* ============================================================
* Stats:
*   Subcircuits  : 1
*   Devices (M)  : 7
*   Device types : nmos_rvt
*   Passives     : 0 resistors, 2 capacitors
* Note: Converted from FinFET-style to CMOS-style netlist.
*       Device sizes are placeholders — optimizer generates new sizes.
* ============================================================

* --- DEVICE PARAMETERS ---
.param m8_L=20e-9 m8_Nf=832
.param m7_L=20e-9 m7_Nf=832
.param m6_L=20e-9 m6_Nf=832
.param m5_L=20e-9 m5_Nf=832
.param m4_L=20e-9 m4_Nf=832
.param m3_L=20e-9 m3_Nf=832
.param m0_L=20e-9 m0_Nf=832


* --- CIRCUIT DEFINITION ---
.subckt sc_dc_dc_converter phi1 phi2 vout vin VSSA
m8 vout phi1 net7 VSSA nmos_rvt L={m8_L} W 12 Nf={m8_Nf}
m7 net7 phi2 VSSA VSSA nmos_rvt L={m7_L} W 12 Nf={m7_Nf}
m6 vout phi2 net8 VSSA nmos_rvt L={m6_L} W 12 Nf={m6_Nf}
m5 net9 phi1 net8 VSSA nmos_rvt L={m5_L} W 12 Nf={m5_Nf}
m4 net9 phi2 VSSA VSSA nmos_rvt L={m4_L} W 12 Nf={m4_Nf}
m3 vout phi2 net10 VSSA nmos_rvt L={m3_L} W 12 Nf={m3_Nf}
m0 net10 phi1 vin VSSA nmos_rvt L={m0_L} W 12 Nf={m0_Nf}
c1 net8 net7 1e-12
c0 net10 net9 1e-12
.ends sc_dc_dc_converter
