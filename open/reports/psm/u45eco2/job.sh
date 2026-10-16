#!/bin/bash
#SBATCH -A <USER> -q standby -p cpu -n 4 --mem=16G -t 00:30:00 -o <SCRATCH>/open-ir-v2/u45eco2/job-%j.out
cd <SCRATCH>/open-ir-v2/u45eco2
IMG=<WORK>/openroad-fix/session-20261008-1838/image-018/librelane_3.0.14-openroad-fix-s3-018.sif
run(){ mkdir -p $1; cd $1; APPTAINERENV_CASE=$1 APPTAINERENV_LP=<SCRATCH>/open-ir-v2/u45eco2/$2 APPTAINERENV_LG=<SCRATCH>/open-ir-v2/u45eco2/$3 APPTAINERENV_TLEF=$4 apptainer exec --cleanenv --bind <DEPOT> --bind <SCRATCH> $IMG openroad -no_splash -exit <SCRATCH>/open-ir-v2/u45eco2/run.tcl 2>&1 | grep "^CASE\|Net  \|Worstcase IR\|Average IR\|Total power\|ERROR\|PSM-00[0-9][0-9]\]"; cd ..; }
T=<DEPOT>
echo IMAGE-SHA $(sha256sum $IMG)
run eco_all_pins P4.loc G4.loc $T
run eco_single P1.loc G1.loc $T
run eco_Rx3 P4.loc G4.loc <SCRATCH>/open-ir-v2/u45eco2/nom_x3.tlef
run eco_Rx25 P4.loc G4.loc <SCRATCH>/open-ir-v2/u45eco2/nom_x25.tlef
python3 - <<PY
import csv,glob
for d in sorted(glob.glob("eco_*")):
    for net,p in (("vpwr",1),("vgnd",0)):
        v=[float(r["Voltage"]) for r in csv.DictReader(open(d+"/"+d+"_"+net+".csv"))]
        print(d,net.upper(),"worst_mV=%.4f"%(((1.6-min(v)) if p else max(v))*1e3),"avg_mV=%.3f"%(1e3*((1.6-sum(v)/len(v)) if p else sum(v)/len(v))),"rows",len(v))
PY
