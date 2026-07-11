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
* SIZES CONVERTED 2026-07-10 scale=7.14286 source_L_ref=0.014um
*       Device/passive sizes are scaled from the real source-netlist values
*       (see marker above) -- not random placeholders.
* ============================================================

* --- DEVICE PARAMETERS ---
.param MTAIL_P_1_W=14.3 MTAIL_P_1_L=0.45 MTAIL_P_1_Nf=12
.param MTAIL_P_2_W=14.3 MTAIL_P_2_L=0.45 MTAIL_P_2_Nf=12
.param MINV_P_P_W=14.3 MINV_P_P_L=0.45 MINV_P_P_Nf=12
.param MINV_P_N_W=14.3 MINV_P_N_L=0.45 MINV_P_N_Nf=12
.param MLOAD_P_W=14.3 MLOAD_P_L=0.45 MLOAD_P_Nf=16
.param MLOAD_N_W=14.3 MLOAD_N_L=0.45 MLOAD_N_Nf=16
.param MRESET_P_W=14.3 MRESET_P_L=0.45 MRESET_P_Nf=8
.param MRESET_N_W=14.3 MRESET_N_L=0.45 MRESET_N_Nf=8
.param MINV_N_P_W=14.3 MINV_N_P_L=0.45 MINV_N_P_Nf=8
.param MINV_N_N_W=14.3 MINV_N_N_L=0.45 MINV_N_N_Nf=8
.param MIN_P_W=14.3 MIN_P_L=0.45 MIN_P_Nf=12
.param MIN_N_W=14.3 MIN_N_L=0.45 MIN_N_Nf=12
.param MTAIL_2_W=14.3 MTAIL_2_L=0.45 MTAIL_2_Nf=8
.param MTAIL_1_W=14.3 MTAIL_1_L=0.45 MTAIL_1_Nf=8


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
