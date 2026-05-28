* ============================================================
* Circuit : block_spacing_bug
* Source  : ALIGN analog layout examples
* File    : block_spacing_bug\block_spacing_bug.sp
* ============================================================
* Stats:
*   Subcircuits  : 1
*   Devices (M)  : 3
*   Device types : nmos_rvt
*   Passives     : 0 resistors, 0 capacitors
* Note: Converted from FinFET-style to CMOS-style netlist.
*       Device sizes are placeholders — optimizer generates new sizes.
* ============================================================

* --- DEVICE PARAMETERS ---
.param mn1_L=20e-9 mn1_W=4 mn1_Nf=2 mn1_M=16
.param mn2_L=20e-9 mn2_W=4 mn2_Nf=2 mn2_M=16
.param mn3_L=20e-9 mn3_W=4 mn3_Nf=2 mn3_M=16


* --- CIRCUIT DEFINITION ---
.subckt block_spacing_bug VSSA vin vip vin1 tail
mn1 von vin tail VSSA nmos_rvt L={mn1_L} W={mn1_W} Nf={mn1_Nf} M={mn1_M}
mn2 vop vip tail VSSA nmos_rvt L={mn2_L} W={mn2_W} Nf={mn2_Nf} M={mn2_M}
mn3 tail vin1 VSSA VSSA nmos_rvt L={mn3_L} W={mn3_W} Nf={mn3_Nf} M={mn3_M}
.ends block_spacing_bug
