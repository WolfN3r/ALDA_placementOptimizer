* ============================================================
* Circuit : powertrain
* Source  : ALIGN analog layout examples
* File    : powertrain\powertrain.sp
* ============================================================
* Stats:
*   Subcircuits  : 1
*   Devices (M)  : 1
*   Device types : pmos_lvt
*   Passives     : 0 resistors, 0 capacitors
* Note: Converted from FinFET-style to CMOS-style netlist.
*       Device sizes are placeholders — optimizer generates new sizes.
* ============================================================

* --- DEVICE PARAMETERS ---
.param mmp0_L=40n mmp0_W=4 mmp0_Nf=8 mmp0_M=20


* --- CIRCUIT DEFINITION ---
.subckt powertrain VDDA vg vout
mmp0 vout vg VDDA VDDA pmos_lvt L={mmp0_L} W={mmp0_W} Nf={mmp0_Nf} M={mmp0_M}
.ends powertrain
