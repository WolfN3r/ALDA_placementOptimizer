* ============================================================
* Circuit : five_transistor_ota_Bulk
* Source  : ALIGN analog layout examples
* File    : five_transistor_ota_Bulk\five_transistor_ota_Bulk.sp
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
.param mn1_W=400e-9 mn1_L=60e-9 mn1_Nf=2 mn1_M=24
.param mn2_W=400e-9 mn2_L=60e-9 mn2_Nf=2 mn2_M=16
.param mn3_W=400e-9 mn3_L=60e-9 mn3_Nf=2 mn3_M=16
.param mp4_W=400e-9 mp4_L=60e-9 mp4_Nf=2 mp4_M=4
.param mp5_W=400e-9 mp5_L=60e-9 mp5_Nf=2 mp5_M=4


* --- CIRCUIT DEFINITION ---
.subckt five_transistor_ota_Bulk vbias VSSA VDDA von vin vip
mn1 tail vbias VSSA VSSA nmos_rvt W={mn1_W} L={mn1_L} Nf={mn1_Nf} M={mn1_M}
mn2 von vin tail VSSA nmos_rvt W={mn2_W} L={mn2_L} Nf={mn2_Nf} M={mn2_M}
mn3 vop vip tail VSSA nmos_rvt W={mn3_W} L={mn3_L} Nf={mn3_Nf} M={mn3_M}
mp4 von vop VDDA VDDA pmos_rvt W={mp4_W} L={mp4_L} Nf={mp4_Nf} M={mp4_M}
mp5 vop vop VDDA VDDA pmos_rvt W={mp5_W} L={mp5_L} Nf={mp5_Nf} M={mp5_M}
.ends five_transistor_ota_Bulk
