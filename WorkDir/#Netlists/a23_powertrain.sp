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
* SIZES CONVERTED 2026-07-10 scale=7.14286 source_L_ref=0.014um
*       Device/passive sizes are scaled from the real source-netlist values
*       (see marker above) -- not random placeholders.
* ============================================================

* --- DEVICE PARAMETERS ---
.param mmp0_L=0.3 mmp0_W=28.55 mmp0_Nf=8 mmp0_M=20


* --- CIRCUIT DEFINITION ---
.subckt powertrain VDDA vg vout
mmp0 vout vg VDDA VDDA pmos_lvt L={mmp0_L} W={mmp0_W} Nf={mmp0_Nf} M={mmp0_M}
.ends powertrain
