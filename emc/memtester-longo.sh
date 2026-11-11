#!/bin/sh
# memtester-longo.sh MB SEG : memtester de MB megabytes por SEG s em 300 e depois 600 MHz
E=/sys/kernel/debug/emc; LOG=/root/memtester-longo.log
echo "inicio $(date)" > $LOG
for r in 300000000 600000000; do
	echo 600000000 > $E/max_rate; echo $r > $E/min_rate; echo $r > $E/max_rate
	fim=$(( $(date +%s) + $2 )); n=0; e=0
	while [ $(date +%s) -lt $fim ]; do
		timeout $(( fim - $(date +%s) + 1 )) memtester ${1}M 1 > /tmp/mt.out 2>&1; rc=$?
		grep -q FAILURE /tmp/mt.out && { e=$((e+1)); cp /tmp/mt.out /root/mt-falha-$(date +%H%M%S).txt; }
		[ $rc = 124 ] && { cp /tmp/mt.out /root/mt-parcial-$r.txt; break; }  # cortado no fim do tempo
		n=$((n+1)); [ $rc != 0 ] && ! grep -q FAILURE /tmp/mt.out && e=$((e+1))
	done
	echo "$r clk=$(cat /sys/kernel/debug/clk/emc/clk_rate) passadas=$n erros=$e $(date +%T)" >> $LOG
done
echo 600000000 > $E/max_rate; echo 50000000 > $E/min_rate
echo "fim $(date)" >> $LOG
