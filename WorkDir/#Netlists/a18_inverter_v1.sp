* ============================================================
* Circuit : inverter_v1
* Source  : ALIGN analog layout examples
* File    : inverter_v1\inverter_v1.sp
* ============================================================
* Stats:
*   Subcircuits  : 1
*   Devices (M)  : 2
*   Device types : nmos_rvt pmos_rvt
*   Passives     : 0 resistors, 0 capacitors
* Note: Converted from FinFET-style to CMOS-style netlist.
*       Device sizes are placeholders — optimizer generates new sizes.
* ============================================================

* --- DEVICE PARAMETERS ---
.param mp1_L=20e-9 mp1_W=6 mp1_Nf=2
.param mn1_L=20e-9 mn1_W=6 mn1_Nf=2


* --- CIRCUIT DEFINITION ---
.subckt inverter_v1 vin vout VDDA VSSA
mp1 vout vin VDDA VDDA pmos_rvt L={mp1_L} W={mp1_W} Nf={mp1_Nf}
mn1 vout vin VSSA VSSA nmos_rvt L={mn1_L} W={mn1_W} Nf={mn1_Nf}
.ends inverter_v1
