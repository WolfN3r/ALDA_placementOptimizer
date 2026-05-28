* ============================================================
* Circuit : five_transistor_ota
* Source  : ALIGN analog layout examples
* File    : five_transistor_ota\five_transistor_ota.sp
* ============================================================
* Stats:
*   Subcircuits  : 1
*   Devices (M)  : 5
*   Device types : nmos_rvt pmos_rvt
*   Passives     : 0 resistors, 0 capacitors
* Note: Converted from FinFET-style to CMOS-style netlist.
*       Device sizes are placeholders — optimizer generates new sizes.
* ============================================================

* --- DEVICE PARAMETERS ---
.param mn1_L=20e-9 mn1_W=4 mn1_Nf=2 mn1_M=8
.param mn2_L=20e-9 mn2_W=4 mn2_Nf=2 mn2_M=16
.param mn3_L=20e-9 mn3_W=4 mn3_Nf=2 mn3_M=16
.param mp4_L=20e-9 mp4_W=4 mp4_Nf=2 mp4_M=4
.param mp5_L=20e-9 mp5_W=4 mp5_Nf=2 mp5_M=4


* --- CIRCUIT DEFINITION ---
.subckt five_transistor_ota vbias VSSA VDDA von vin vip
mn1 tail vbias VSSA VSSA nmos_rvt L={mn1_L} W={mn1_W} Nf={mn1_Nf} M={mn1_M}
mn2 von vin tail VSSA nmos_rvt L={mn2_L} W={mn2_W} Nf={mn2_Nf} M={mn2_M}
mn3 vop vip tail VSSA nmos_rvt L={mn3_L} W={mn3_W} Nf={mn3_Nf} M={mn3_M}
mp4 von vop VDDA VDDA pmos_rvt L={mp4_L} W={mp4_W} Nf={mp4_Nf} M={mp4_M}
mp5 vop vop VDDA VDDA pmos_rvt L={mp5_L} W={mp5_W} Nf={mp5_Nf} M={mp5_M}
.ends five_transistor_ota
