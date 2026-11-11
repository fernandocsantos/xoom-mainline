#!/bin/sh
# amostrar-tensoes.sh SEG : a cada 0,5 s grava core/aon/cpu (uV), EMC e CPU (MHz)
# em /root/tensoes.log e conta violações (CPU+120 mV > core ou aon; |core-aon| > 170 mV)
R=/sys/class/regulator
for d in $R/*; do case $(cat $d/name) in vdd_core) C=$d;; vdd_aon) A=$d;; vdd_cpu) P=$d;; esac; done
fim=$(( $(date +%s) + $1 )); : > /root/tensoes.log
while [ $(date +%s) -lt $fim ]; do
	echo "$(cat $C/microvolts) $(cat $A/microvolts) $(cat $P/microvolts) $(( $(cat /sys/kernel/debug/clk/emc/clk_rate)/1000000 )) $(( $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq)/1000 ))" >> /root/tensoes.log
	sleep 0.5
done
awk '{n++; if($3+120000>$1)vc++; if($3+120000>$2)va++; d=$1-$2; if(d<0)d=-d; if(d>170000)vs++; c[$1]++; a[$2]++}
END{printf "amostras=%d viol_cpu_core=%d viol_cpu_aon=%d viol_core_aon=%d\n",n,vc,va,vs;
for(k in c)printf "core %d: %d\n",k,c[k]; for(k in a)printf "aon %d: %d\n",k,a[k]}' /root/tensoes.log
