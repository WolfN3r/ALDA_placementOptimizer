#!/bin/bash
# Generate the case schematics (make_sch.py), netlist them (connectivity check) and draw
# each to <name>.png, like 06_ota1_magical/export.sh. Runs in the container:
#     ./export.sh
cd "$(dirname "$0")"
RC="$PDK_ROOT/$PDK/libs.tech/xschem/xschemrc"
python3 make_sch.py || exit 1
for c in ota1_c1 ota1_c2 ota1_c3; do
    xschem --rcfile "$RC" --preinit "set top_is_subckt 1; set lvs_netlist 0" -q -x -n -s \
        -o "$PWD" -N $c.spice $c.sch > $c.log 2>&1
    grep -q "^\.subckt $c " $c.spice || { echo "export.sh: no '.subckt $c' in $c.spice" >&2; exit 1; }
    # the picture needs an X display (the VNC desktop is :1)
    DISPLAY=${DISPLAY:-:1} timeout 60 xschem --rcfile "$RC" -q --command "wm geometry . 2400x1400; update; \
        xschem zoom_full; update; xschem print png $PWD/$c.png 2600 1500; xschem exit closewindow force" \
        $c.sch > /dev/null 2>&1
    [ -s $c.png ] && echo "wrote $c.spice and $c.png" || echo "export.sh: no $c.png" >&2
done
