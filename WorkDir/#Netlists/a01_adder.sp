* ============================================================
* Circuit : adder
* Source  : ALIGN analog layout examples
* File    : adder\adder.sp
* ============================================================
* Stats:
*   Subcircuits  : 3
*   Devices (M)  : 4
*   Device types : nmos_rvt pmos_rvt
*   Passives     : 3 resistors, 2 capacitors
* Note: Converted from FinFET-style to CMOS-style netlist.
*       Device sizes are placeholders — optimizer generates new sizes.
* ============================================================

* --- DEVICE PARAMETERS ---
.param nfet2x_MN0_L=0.014u nfet2x_MN0_W=12
.param nfet2x_MN1_L=0.014u nfet2x_MN1_W=12
.param pfet2x_MP0_L=0.014u pfet2x_MP0_W=12
.param pfet2x_MP1_L=0.014u pfet2x_MP1_W=12


* --- CIRCUIT DEFINITION ---

.subckt nfet2x d g s b
.param p1=2
    MN0 d g n1 b nmos_rvt L={nfet2x_MN0_L} W={nfet2x_MN0_W} Nf=p1
    MN1 n1 g s b nmos_rvt L={nfet2x_MN1_L} W={nfet2x_MN1_W} Nf=p1
.ends nfet2x

.subckt pfet2x d g s b
.param p1=2
    MP0 d g n1 b pmos_rvt L={pfet2x_MP0_L} W={pfet2x_MP0_W} Nf=p1
    MP1 n1 g s b pmos_rvt L={pfet2x_MP1_L} W={pfet2x_MP1_W} Nf=p1
.ends pfet2x

.subckt adder n1 n2 vin vout VDDA VSSA
.param cc=48f nfpf=4 rb=20K rl=500

    xI0 vout vbn1 VSSA VSSA nfet2x p1=nfpf
    xI1 vout vbp1 VDDA VDDA pfet2x p1=nfpf
    R0 vbn1 n1 rb
    C0 vin vbn1 cc
    R1 vbp1 n2 rb
    C1 vin vbp1 cc
    R2 VDDA vout rl
.ends adder
