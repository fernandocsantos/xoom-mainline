#!/bin/sh
# Monta módulos e firmware extras do initramfs e gera modules.list para o
# CONFIG_INITRAMFS_SOURCE. Rode depois de:
#   make O=../out-stingray INSTALL_MOD_PATH=../out-stingray/modstage \
#        INSTALL_MOD_STRIP=1 modules_install
set -eu

X=$(cd "$(dirname "$0")/.." && pwd)
STAGE=$X/out-stingray/modstage/lib/modules
KV=$(ls "$STAGE" | head -n 1)
M=$STAGE/$KV
OUT=$X/initramfs/extras
CAL=${CAL:-$(ls -t "$X"/resultado-*-wifi/bcm4329.cal | head -n 1)}
# MAC do Wi-Fi do seu tablet (etiqueta ou PDS); o .cal traz um MAC de exemplo
MAC=${MAC:?defina MAC=xx:xx:xx:xx:xx:xx}

MODULES="bmp280-i2c kxcjk-1013 ak8975 st_gyro_i2c lm90
         brcmfmac brcmfmac-wcc brcmfmac-cyw brcmfmac-bca"

rm -rf "$OUT"
mkdir -p "$OUT/lib/modules/$KV" "$OUT/lib/firmware/brcm"

# Módulos pedidos + dependências, segundo o modules.dep do build
for m in $MODULES; do
	line=$(grep -E "/$m\.ko:" "$M/modules.dep") || { echo "módulo $m não encontrado" >&2; exit 1; }
	for f in $(echo "$line" | tr -d ':'); do
		mkdir -p "$OUT/lib/modules/$KV/$(dirname "$f")"
		cp "$M/$f" "$OUT/lib/modules/$KV/$f"
	done
done
cp "$M/modules.order" "$M/modules.builtin" "$M/modules.builtin.modinfo" "$OUT/lib/modules/$KV/"
depmod -b "$OUT" "$KV"

# Firmware do BCM4329 (linux-firmware do PC, comprimido em zstd)
zstd -q -dc /lib/firmware/brcm/brcmfmac4329-sdio.bin.zst > "$OUT/lib/firmware/brcm/brcmfmac4329-sdio.bin"

# NVRAM (calibração de rádio do próprio tablet) com o MAC real. O brcmfmac
# procura primeiro o nome com o compatible da placa.
sed "s/^macaddr=.*/macaddr=$MAC/" "$CAL" > "$OUT/lib/firmware/brcm/brcmfmac4329-sdio.motorola,stingray.txt"

# Lista no formato do usr/gen_init_cpio
cd "$OUT"
{
	find lib -type d | sort | sed 's|^\(.*\)$|dir /\1 755 0 0|'
	find lib -type f | sort | while read -r f; do echo "file /$f $OUT/$f 644 0 0"; done
} > "$X/initramfs/modules.list"

echo "kernel $KV: $(find lib -name '*.ko' | wc -l) módulos, $(du -sh "$OUT" | cut -f1) em $OUT"
grep -n "^macaddr" "$OUT/lib/firmware/brcm/"*.txt
