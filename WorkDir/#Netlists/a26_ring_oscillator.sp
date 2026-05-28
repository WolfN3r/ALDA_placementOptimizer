* ============================================================
* Circuit : ring_oscillator
* Source  : ALIGN analog layout examples
* File    : ring_oscillator\ring_oscillator.sp
* ============================================================
* Stats:
*   Subcircuits  : 2
*   Devices (M)  : 2
*   Device types : nmos_rvt pmos_rvt
*   Passives     : 0 resistors, 0 capacitors
* Note: Converted from FinFET-style to CMOS-style netlist.
*       Device sizes are placeholders — optimizer generates new sizes.
* ============================================================

* --- DEVICE PARAMETERS ---
.param ring_oscillator_stage_mp0_W=2 ring_oscillator_stage_mp0_L=40n ring_oscillator_stage_mp0_M=1 ring_oscillator_stage_mp0_Nf=4
.param ring_oscillator_stage_mn0_W=2 ring_oscillator_stage_mn0_L=40n ring_oscillator_stage_mn0_M=1 ring_oscillator_stage_mn0_Nf=4


* --- CIRCUIT DEFINITION ---
.subckt ring_oscillator_stage vi vo VSSA VDDA vctl
mp0 vo vi vctl VDDA pmos_rvt W={ring_oscillator_stage_mp0_W} L={ring_oscillator_stage_mp0_L} M={ring_oscillator_stage_mp0_M} Nf={ring_oscillator_stage_mp0_Nf}
mn0 vo vi VSSA VSSA nmos_rvt W={ring_oscillator_stage_mn0_W} L={ring_oscillator_stage_mn0_L} M={ring_oscillator_stage_mn0_M} Nf={ring_oscillator_stage_mn0_Nf}
.ends ring_oscillator_stage

.subckt ring_oscillator vctl vo VDDA VSSA
xi0 vo n1 VSSA VDDA vctl ring_oscillator_stage
xi1 n1 n2 VSSA VDDA vctl ring_oscillator_stage
xi2 n2 n3 VSSA VDDA vctl ring_oscillator_stage
xi3 n3 n4 VSSA VDDA vctl ring_oscillator_stage
xi4 n4 vo VSSA VDDA vctl ring_oscillator_stage
.ends ring_oscillator
