#!/bin/sh
# teste-dvfs.sh [SEG] : fixa cada frequência da CPU por SEG segundos (padrão 180)
# com 2 laços de gzip -> gunzip conferindo o sha256; depois volta ao ondemand.
# Log em /root/teste-dvfs.log. Rodar: setsid sh teste-dvfs.sh 180 </dev/null >/dev/null 2>&1 &
P=/sys/devices/system/cpu/cpufreq/policy0
V=$(for d in /sys/class/regulator/*; do [ "$(cat $d/name)" = vdd_cpu ] && echo $d; done)
SEG=${1:-180}
LOG=/root/teste-dvfs.log
F=/tmp/dvfs.bin
T=$(for h in /sys/class/hwmon/hwmon*; do grep -q nct1008 $h/name 2>/dev/null && echo $h/temp2_input; done)
head -c 16777216 /usr/lib/libLLVM.so.22.1 > $F
REF=$(gzip -1 -c $F | gzip -dc | sha256sum | cut -c1-16)
echo "inicio $(date) ref=$REF" > $LOG
laco() { # $1 = fim (segundos desde epoch)
	n=0; e=0
	while [ $(date +%s) -lt $1 ]; do
		h=$(gzip -1 -c $F | gzip -dc | sha256sum | cut -c1-16)
		n=$((n+1)); [ "$h" = "$REF" ] || e=$((e+1))
	done
	echo "$n $e"
}
echo userspace > $P/scaling_governor
for f in $(cat $P/scaling_available_frequencies); do
	echo $f > $P/scaling_setspeed
	fim=$(( $(date +%s) + SEG ))
	laco $fim > /tmp/dvfs.a &
	laco $fim > /tmp/dvfs.b
	wait
	echo "$f kHz $(cat $V/microvolts) uV cur=$(cat $P/cpuinfo_cur_freq) temp=$(cat $T 2>/dev/null) a=[$(cat /tmp/dvfs.a)] b=[$(cat /tmp/dvfs.b)] (rodadas erros)" >> $LOG
done
echo ondemand > $P/scaling_governor
echo "fim $(date)" >> $LOG
