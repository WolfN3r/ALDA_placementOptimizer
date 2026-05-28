* ============================================================
* Circuit : buffer
* Source  : ALIGN analog layout examples
* File    : buffer\buffer.sp
* ============================================================
* Stats:
*   Subcircuits  : 1
*   Devices (M)  : 4
*   Device types : nmos_rvt pmos_rvt
*   Passives     : 0 resistors, 0 capacitors
* Note: Converted from FinFET-style to CMOS-style netlist.
*       Device sizes are placeholders — optimizer generates new sizes.
* ============================================================

* --- DEVICE PARAMETERS ---
.param mp1_L=20e-9 mp1_W=6 mp1_Nf=2
.param mn1_L=20e-9 mn1_W=6 mn1_Nf=2
.param mp2_L=20e-9 mp2_W=12 mp2_Nf=2
.param mn2_L=20e-9 mn2_W=12 mn2_Nf=4


* --- CIRCUIT DEFINITION ---
.subckt buffer vin vout VDDA VSSA
mp1 vxx vin VDDA VDDA pmos_rvt L={mp1_L} W={mp1_W} Nf={mp1_Nf}
mn1 vxx vin VSSA VSSA nmos_rvt L={mn1_L} W={mn1_W} Nf={mn1_Nf}
mp2 vout vxx VDDA VDDA pmos_rvt L={mp2_L} W={mp2_W} Nf={mp2_Nf}
mn2 vout vxx VSSA VSSA nmos_rvt L={mn2_L} W={mn2_W} Nf={mn2_Nf}
.ends buffer
