* ============================================================
* Circuit : inverter_v3
* Source  : ALIGN analog layout examples
* File    : inverter_v3\inverter_v3.sp
* ============================================================
* Stats:
*   Subcircuits  : 1
*   Devices (M)  : 3
*   Device types : nmos_rvt pmos_rvt
*   Passives     : 0 resistors, 0 capacitors
* Note: Converted from FinFET-style to CMOS-style netlist.
* SIZES CONVERTED 2026-07-10 scale=7.14286 source_L_ref=0.014um
*       Device/passive sizes are scaled from the real source-netlist values
*       (see marker above) -- not random placeholders.
* ============================================================

* --- DEVICE PARAMETERS ---
.param mp1_L=0.15 mp1_W=42.85 mp1_Nf=2
.param mn1_L=0.15 mn1_W=42.85 mn1_Nf=2
.param mn2_L=0.15 mn2_W=42.85 mn2_Nf=2


* --- CIRCUIT DEFINITION ---
.subckt inverter_v3 vin vout VDDA VSSA
mp1 vout vin VDDA VDDA pmos_rvt L={mp1_L} W={mp1_W} Nf={mp1_Nf}
mn1 vout vin VSSA VSSA nmos_rvt L={mn1_L} W={mn1_W} Nf={mn1_Nf}
mn2 vout VSSA VSSA VSSA nmos_rvt L={mn2_L} W={mn2_W} Nf={mn2_Nf}
.ends inverter_v3
