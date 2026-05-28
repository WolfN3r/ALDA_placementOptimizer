* ============================================================
* Circuit : common_source
* Source  : ALIGN analog layout examples
* File    : common_source\common_source.sp
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
.param mp0_W=4 mp0_Nf=2 mp0_M=4
.param mn0_W=4 mn0_Nf=2 mn0_M=4


* --- CIRCUIT DEFINITION ---
.subckt common_source vin vop VDDA VSSA
mp0 vop vop VDDA VDDA pmos_rvt W={mp0_W} Nf={mp0_Nf} M={mp0_M}
mn0 vop vin VSSA VSSA nmos_rvt W={mn0_W} Nf={mn0_Nf} M={mn0_M}
.ends common_source
