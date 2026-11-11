#!/bin/sh
# serie-reboot.sh N [espera] : N reboots seguidos pelo ssh, contando sucessos.
# Antes de cada um registra kernel, VAL1 do CPCAP, carregador e bateria.
# Para no primeiro que não voltar em <espera> s (padrão 120): o tablet travou
# e precisa do Power. Log em reboot/serie-AAAAMMDD-HHMM.log.
N=${1:-10}; ESPERA=${2:-120}
SSHO="${XOOM_SSHO:-} -o ConnectTimeout=5 -o BatchMode=yes"
X="ssh $SSHO ${XOOM_HOST:-root@172.16.42.1}"
LOG=reboot/serie-$(date +%Y%m%d-%H%M).log
ok=0
estado() {
	$X 'printf "%s up=%s boot=%s " "$(uname -v | cut -d" " -f1)" "$(cut -d" " -f1 /proc/uptime)" "$(cut -c1-8 /proc/sys/kernel/random/boot_id)"
	printf "VAL1=%s " "$(grep "^0428:" /sys/kernel/debug/regmap/spi0.0/registers | cut -d" " -f2)"
	for p in /sys/class/power_supply/*; do printf "%s=%s " "${p##*/}" "$(cat $p/online 2>/dev/null || cat $p/capacity 2>/dev/null)"; done
	printf "emc=%s cpu=%s\n" "$(cat /sys/kernel/debug/clk/emc/clk_rate 2>/dev/null)" "$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null)"'
}
for i in $(seq 1 $N); do
	antes=$(estado) || { echo "sem ssh antes do reboot $i" | tee -a $LOG; exit 1; }
	b0=$(echo "$antes" | sed 's/.*boot=\([^ ]*\).*/\1/')
	echo "$(date +%T) [$i/$N] antes: $antes" | tee -a $LOG
	$X 'sync; reboot' </dev/null >/dev/null 2>&1
	t0=$(date +%s); volta=
	sleep 15
	while [ $(( $(date +%s) - t0 )) -lt $ESPERA ]; do
		b=$($X 'cut -c1-8 /proc/sys/kernel/random/boot_id' 2>/dev/null) && [ -n "$b" ] && [ "$b" != "$b0" ] && { volta=$(( $(date +%s) - t0 )); break; }
		sleep 3
	done
	if [ -n "$volta" ]; then
		ok=$((ok + 1))
		echo "$(date +%T) [$i/$N] VOLTOU em ${volta} s" | tee -a $LOG
		sleep 20	# deixa o boot terminar (serviços, Wi-Fi)
	else
		echo "$(date +%T) [$i/$N] NÃO VOLTOU em $ESPERA s: travou? ($ok de $i ok)" | tee -a $LOG
		exit 1
	fi
done
echo "$(date +%T) RESULTADO: $ok de $N" | tee -a $LOG
