* ============================================================
* Circuit : double_tail_sense_amplifier
* Source  : ALIGN analog layout examples
* File    : double_tail_sense_amplifier\double_tail_sense_amplifier.sp
* ============================================================
* Stats:
*   Subcircuits  : 1
*   Devices (M)  : 14
*   Device types : nmos_rvt pmos_rvt
*   Passives     : 0 resistors, 0 capacitors
* Note: Converted from FinFET-style to CMOS-style netlist.
*       Device sizes are placeholders — optimizer generates new sizes.
* ============================================================

* --- DEVICE PARAMETERS ---
.param MTAIL_P_1_W=2 MTAIL_P_1_L=60e-9 MTAIL_P_1_Nf=12
.param MTAIL_P_2_W=2 MTAIL_P_2_L=60e-9 MTAIL_P_2_Nf=12
.param MINV_P_P_W=2 MINV_P_P_L=60e-9 MINV_P_P_Nf=12
.param MINV_P_N_W=2 MINV_P_N_L=60e-9 MINV_P_N_Nf=12
.param MLOAD_P_W=2 MLOAD_P_L=60e-9 MLOAD_P_Nf=16
.param MLOAD_N_W=2 MLOAD_N_L=60e-9 MLOAD_N_Nf=16
.param MRESET_P_W=2 MRESET_P_L=60e-9 MRESET_P_Nf=8
.param MRESET_N_W=2 MRESET_N_L=60e-9 MRESET_N_Nf=8
.param MINV_N_P_W=2 MINV_N_P_L=60e-9 MINV_N_P_Nf=8
.param MINV_N_N_W=2 MINV_N_N_L=60e-9 MINV_N_N_Nf=8
.param MIN_P_W=2 MIN_P_L=60e-9 MIN_P_Nf=12
.param MIN_N_W=2 MIN_N_L=60e-9 MIN_N_Nf=12
.param MTAIL_2_W=2 MTAIL_2_L=60e-9 MTAIL_2_Nf=8
.param MTAIL_1_W=2 MTAIL_1_L=60e-9 MTAIL_1_Nf=8


* --- CIRCUIT DEFINITION ---
.subckt double_tail_sense_amplifier CLK CLK_B DIN DIP VDDA VIN VIP VON VOP VSSA
MTAIL_P_1 REGEN_SOURCE CLK_B VDDA VDDA pmos_rvt W={MTAIL_P_1_W} L={MTAIL_P_1_L} Nf={MTAIL_P_1_Nf}
MTAIL_P_2 REGEN_SOURCE CLK_B VDDA VDDA pmos_rvt W={MTAIL_P_2_W} L={MTAIL_P_2_L} Nf={MTAIL_P_2_Nf}
MINV_P_P VOP VON REGEN_SOURCE VDDA pmos_rvt W={MINV_P_P_W} L={MINV_P_P_L} Nf={MINV_P_P_Nf}
MINV_P_N VON VOP REGEN_SOURCE VDDA pmos_rvt W={MINV_P_N_W} L={MINV_P_N_L} Nf={MINV_P_N_Nf}
MLOAD_P DIN CLK VDDA VDDA pmos_rvt W={MLOAD_P_W} L={MLOAD_P_L} Nf={MLOAD_P_Nf}
MLOAD_N DIP CLK VDDA VDDA pmos_rvt W={MLOAD_N_W} L={MLOAD_N_L} Nf={MLOAD_N_Nf}
MRESET_P VOP DIN VSSA VSSA nmos_rvt W={MRESET_P_W} L={MRESET_P_L} Nf={MRESET_P_Nf}
MRESET_N VON DIP VSSA VSSA nmos_rvt W={MRESET_N_W} L={MRESET_N_L} Nf={MRESET_N_Nf}
MINV_N_P VOP VON VSSA VSSA nmos_rvt W={MINV_N_P_W} L={MINV_N_P_L} Nf={MINV_N_P_Nf}
MINV_N_N VON VOP VSSA VSSA nmos_rvt W={MINV_N_N_W} L={MINV_N_N_L} Nf={MINV_N_N_Nf}
MIN_P DIN VIP PRE_AMP_SOURCE VSSA nmos_rvt W={MIN_P_W} L={MIN_P_L} Nf={MIN_P_Nf}
MIN_N DIP VIN PRE_AMP_SOURCE VSSA nmos_rvt W={MIN_N_W} L={MIN_N_L} Nf={MIN_N_Nf}
MTAIL_2 PRE_AMP_SOURCE CLK VSSA VSSA nmos_rvt W={MTAIL_2_W} L={MTAIL_2_L} Nf={MTAIL_2_Nf}
MTAIL_1 PRE_AMP_SOURCE CLK VSSA VSSA nmos_rvt W={MTAIL_1_W} L={MTAIL_1_L} Nf={MTAIL_1_Nf}
.ends double_tail_sense_amplifier
