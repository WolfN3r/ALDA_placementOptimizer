* ============================================================
* Circuit : comparator1
* Source  : ALIGN analog layout examples
* File    : comparator1\comparator1.sp
* ============================================================
* Stats:
*   Subcircuits  : 6
*   Devices (M)  : 19
*   Device types : nmos_rvt pmos_rvt
*   Passives     : 0 resistors, 0 capacitors
* Note: Converted from FinFET-style to CMOS-style netlist.
*       Device sizes are placeholders — optimizer generates new sizes.
* ============================================================

* --- DEVICE PARAMETERS ---
.param INVERTER_1_m0_M=1 INVERTER_1_m0_L=14n INVERTER_1_m0_W=2
.param INVERTER_1_m1_M=1 INVERTER_1_m1_L=14n INVERTER_1_m1_W=3
.param INVERTER_2_m0_M=1 INVERTER_2_m0_L=14n INVERTER_2_m0_W=4
.param INVERTER_2_m1_M=1 INVERTER_2_m1_L=14n INVERTER_2_m1_W=6
.param NAND_1_m1_M=1 NAND_1_m1_L=14n NAND_1_m1_W=4
.param NAND_1_m3_M=1 NAND_1_m3_L=14n NAND_1_m3_W=4
.param NAND_1_m4_M=1 NAND_1_m4_L=14n NAND_1_m4_W=6
.param comparator_m0_M=1 comparator_m0_L=14n comparator_m0_W=4
.param comparator_m1_M=1 comparator_m1_L=14n comparator_m1_W=4
.param comparator_m2_M=1 comparator_m2_L=14n comparator_m2_W=4
.param comparator_m3_M=1 comparator_m3_L=14n comparator_m3_W=4
.param comparator_m4_M=1 comparator_m4_L=14n comparator_m4_W=4
.param comparator_m5_M=1 comparator_m5_L=14n comparator_m5_W=4
.param comparator_m6_M=1 comparator_m6_L=14n comparator_m6_W=4
.param comparator_m7_M=1 comparator_m7_L=14n comparator_m7_W=4
.param comparator_m8_M=1 comparator_m8_L=14n comparator_m8_W=6
.param comparator_m9_M=1 comparator_m9_L=14n comparator_m9_W=6
.param comparator_m10_M=1 comparator_m10_L=14n comparator_m10_W=6
.param comparator_m11_M=1 comparator_m11_L=14n comparator_m11_W=6


* --- CIRCUIT DEFINITION ---
.param fck1=2 fck2=2 finnn=2 fninv=4 fpinv=4 fprst=4 fttt=4 fout1=1 fout2=2 frdynand=2 fckbuf1_seq=2 frstbuf1_compckgen=1 fpinn_latch_M=4 fpinn_latch_L=2 bit_M_Latch=2 bit_L_Latch=4
.param fs=1G vos=100u VCM=400m VDD=0.8

.subckt INVERTER_1 A VDDA VSSA Z
.param _par0=1 _par1=1
    m0 Z A VSSA VSSA nmos_rvt M={INVERTER_1_m0_M} L={INVERTER_1_m0_L} W={INVERTER_1_m0_W} Nf=_par0
    m1 Z A VDDA VDDA pmos_rvt M={INVERTER_1_m1_M} L={INVERTER_1_m1_L} W={INVERTER_1_m1_W} Nf=_par1
.ends INVERTER_1

.subckt INVERTER_2 A VDDA VSSA Z
.param _par0=1 _par1=1
    m0 Z A VSSA VSSA nmos_rvt M={INVERTER_2_m0_M} L={INVERTER_2_m0_L} W={INVERTER_2_m0_W} Nf=_par0
    m1 Z A VDDA VDDA pmos_rvt M={INVERTER_2_m1_M} L={INVERTER_2_m1_L} W={INVERTER_2_m1_W} Nf=_par1
.ends INVERTER_2
* End of subcircuit definition.

.subckt NAND_1 A B Z VDDA VSSA
.param fingern=1 fppp=1
    m1 Z A net47 VSSA nmos_rvt M={NAND_1_m1_M} L={NAND_1_m1_L} W={NAND_1_m1_W} Nf=fingern
    m3 net47 B VSSA VSSA nmos_rvt M={NAND_1_m3_M} L={NAND_1_m3_L} W={NAND_1_m3_W} Nf=fingern
    m4 Z B VDDA VDDA pmos_rvt M={NAND_1_m4_M} L={NAND_1_m4_L} W={NAND_1_m4_W} Nf=fppp
.ends NAND_1

.subckt NAND A B VDDA VSSA Z
.param fingern=1 fppp=1
xI0 A B Z VDDA VSSA NAND_1 fingern=fingern fppp=fppp
xI1 B A Z VDDA VSSA NAND_1 fingern=fingern fppp=fppp
.ends NAND

.subckt comparator AN AP BN BP CKi ON OP RDY VDDA VSSA oCK
.param _par0=2 _par1=2 _par2=2 _par3=2 _par4=2 _par5=2 _par6=2 _par7=2
    m0 OP ON net65 VSSA nmos_rvt M={comparator_m0_M} L={comparator_m0_L} W={comparator_m0_W} Nf=_par0
    m1 ON OP net61 VSSA nmos_rvt M={comparator_m1_M} L={comparator_m1_L} W={comparator_m1_W} Nf=_par0
    m2 net65 BN net67 VSSA nmos_rvt M={comparator_m2_M} L={comparator_m2_L} W={comparator_m2_W} Nf=_par1
    m3 net67 oCK VSSA VSSA nmos_rvt M={comparator_m3_M} L={comparator_m3_L} W={comparator_m3_W} Nf _par2
    m4 net61 BP net67 VSSA nmos_rvt M={comparator_m4_M} L={comparator_m4_L} W={comparator_m4_W} Nf _par1
    m5 net65 AN net60 VSSA nmos_rvt M={comparator_m5_M} L={comparator_m5_L} W={comparator_m5_W} Nf _par1
    m6 net60 oCK VSSA VSSA nmos_rvt M={comparator_m6_M} L={comparator_m6_L} W={comparator_m6_W} Nf _par2
    m7 net61 AP net60 VSSA nmos_rvt M={comparator_m7_M} L={comparator_m7_L} W={comparator_m7_W} Nf _par1
    m8 OP oCK VDDA VDDA pmos_rvt M={comparator_m8_M} L={comparator_m8_L} W={comparator_m8_W} Nf _par3
    m9 ON oCK VDDA VDDA pmos_rvt M={comparator_m9_M} L={comparator_m9_L} W={comparator_m9_W} Nf _par3
    m10 OP ON VDDA VDDA pmos_rvt M={comparator_m10_M} L={comparator_m10_L} W={comparator_m10_W} Nf _par4
    m11 ON OP VDDA VDDA pmos_rvt M={comparator_m11_M} L={comparator_m11_L} W={comparator_m11_W} Nf _par4
    xI5 CKi VDDA VSSA net019 INVERTER_1 _par0=_par5 _par1=_par5
    xI4 net019 VDDA VSSA oCK INVERTER_2 _par0=_par6 _par1=_par6
    xI2 OP ON VDDA VSSA RDY NAND fingern=_par7 fppp=_par7
.ends comparator
* End of subcircuit definition.

.subckt comparator1 AN AP BN BP CKi ON OP RDY VDDA VSSA oCK
xI1 AN AP BN BP CKi ON OP RDY VDDA VSSA oCK comparator _par0=fninv _par1=finnn _par2=fttt _par3=fprst _par4=fpinv _par5=fck1 _par6=fck2 _par7=frdynand
.ends comparator1
