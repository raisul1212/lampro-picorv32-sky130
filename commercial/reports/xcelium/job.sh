#!/bin/bash
#SBATCH -A <USER> -p cpu -N 1 -n 1 --mem=8G -t 01:30:00 -J xcel -o <WORK>/pico_t1_diag/xcel_825/job_%j.out
export PATH=/apps/eda/cadence/XCELIUM2403/tools/bin/64bit:/apps/eda/cadence/XCELIUM2403/tools/bin:/apps/eda/cadence/XCELIUM2403/bin:$PATH
D=<WORK>/pico_t1_diag/xcel_825; cd $D
M=<DEPOT>
sha256sum picorv32.sdf picorv32.powered.v tb_picorv32_golden.v
for p in 8.25 10 4; do
  xrun -64bit -sv -timescale 1ns/1ps -define USE_POWER_PINS -access +r -neg_tchk -sdf_verbose \
       tb_picorv32_golden.v picorv32.powered.v $M/primitives.v $M/sky130_fd_sc_hd.v -top tb \
       -xmlibdirname xcelium.d_$p -l xrun_$p.log +period=$p > xrun_$p.out 2>&1
  echo "== $p rc=$? verdict: $(grep -h -m1 VERDICT xrun_$p.log) result: $(grep -h -m1 RESULT xrun_$p.log)"
  echo "   timing-check violations: $(grep -ciE 'timing violation|\$setuphold|\$setup|\$hold|\$recrem|\$width' xrun_$p.log)"
  grep -iE "\*E|annotat.*(complete|summary)|SDFA|Annotation" xrun_$p.log | sort | uniq -c | sort -rn | head -6
done
echo DONE
