#!/bin/sh
# gravar-boot.sh IMG N : envia, confere sha256, grava na p7, confere, reinicia e espera "#N "
set -e
IMG=$1; N=$2
SSHO="${XOOM_SSHO:-} -o ConnectTimeout=5"
L=$(sha256sum $IMG | cut -d' ' -f1); TAM=$(stat -c %s $IMG)
R=$(ssh $SSHO ${XOOM_HOST:-root@172.16.42.1} "cat > /root/boot-new.img && sha256sum /root/boot-new.img" < $IMG | cut -d' ' -f1)
[ "$L" = "$R" ] || { echo "sha diferente no envio"; exit 1; }
P=$(ssh $SSHO ${XOOM_HOST:-root@172.16.42.1} "dd if=/root/boot-new.img of=/dev/mmcblk0p7 bs=1M conv=fsync 2>/dev/null; head -c $TAM /dev/mmcblk0p7 | sha256sum" | cut -d' ' -f1)
[ "$L" = "$P" ] || { echo "sha diferente na p7!"; exit 1; }
echo "gravado ok $L"
ssh $SSHO ${XOOM_HOST:-root@172.16.42.1} 'sync; reboot' || true
sleep 25
for i in $(seq 1 50); do
  v=$(ssh $SSHO ${XOOM_HOST:-root@172.16.42.1} 'uname -v' 2>/dev/null) && case "$v" in "#$N "*) echo "voltou: $v"; exit 0;; esac
  sleep 5
done
echo "não voltou"; exit 1
