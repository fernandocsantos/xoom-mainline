# Linux mainline no Motorola Xoom (Tegra 2)

*English below.*

Linux mainline (7.3-rc7) e Alpine Linux, com Sxmo e Phosh, num Motorola Xoom 3G (MZ605,
placa "stingray", NVIDIA Tegra 20) de 2011, com aceleração 3D pelo Mesa do projeto
grate. O port começou em 14/10/2026, com o primeiro boot mostrando o Tux de bico azul, e
o tablet está em uso desde então.

Este repositório reúne as ferramentas, o initramfs e os testes. As mudanças nos
softwares de terceiros estão nos forks:

| Fork | Branch | O que tem |
|---|---|---|
| [linux](https://github.com/fernandocsantos/linux/tree/xoom-stingray) | `xoom-stingray` | 36 commits, um por marco: DTS, driver 1-Wire novo, correções no tegra-drm, ASoC, PMC, i2c-tegra, MAX8649, reboot do CPCAP. `arch/arm/configs/stingray.config` |
| [mesa](https://github.com/fernandocsantos/mesa/tree/xoom-tegra20) (grate) | `xoom-tegra20` | texturas e shaders do wlroots escritos à mão em assembly do Tegra, blend no shader, dma-buf, scissor, índices de 32 bits, draws em lote e correções |
| [libdrm](https://github.com/fernandocsantos/libdrm/tree/xoom-tegra20) (grate) | `xoom-tegra20` | build sem valgrind, exportação do dma-buf |
| [wlroots](https://github.com/fernandocsantos/wlroots/tree/xoom-tegra20) | `xoom-tegra20` | o botão Power não reacendia a tela (reset de gamma num CRTC sem gamma) |
| [libhybris](https://github.com/fernandocsantos/libhybris/tree/xoom-musl) | `xoom-musl` | port para musl, para rodar o HAL do GPS do Android |

Repositórios irmãos: [xoom-alpine](https://github.com/fernandocsantos/xoom-alpine)
(rootfs e configuração) e [xoom-gps](https://github.com/fernandocsantos/xoom-gps)
(GPS pelo HAL do Android).

## O que funciona

Vídeo pelo Tegra DRM (LVDS, painel 1280x800) e luz de fundo; toque mXT1386, teclas e
sensores (giroscópio, acelerômetro, magnetômetro, barômetro, temperatura, luz); Wi-Fi
BCM4329; Bluetooth (sem LE); bateria (DS2781 por 1-Wire) e carregador; alto-falante,
microfone e PipeWire; GPU (GR3D) compondo a sway e o phoc; frequência da CPU (216 MHz a
1 GHz) e da RAM (50 a 600 MHz), com o vdd_core descendo a 1,1 V em repouso; thermal
zones; USB gadget (rede e serial pelo cabo); modem 3G respondendo AT; GPS; reboot e
"reboot bootloader", também só na bateria.

**Ainda não:** vídeo HDMI (sem cabo para testar), câmeras, registro e dados do modem (sem
chip), áudio por Bluetooth com som ruim, fone de ouvido sem teste, o tablet não suspende
sozinho, reconstrução do rootfs pelo script nunca testada do zero.

## Conteúdo

| Pasta | O que é |
|---|---|
| `ferramentas/tegra20-pinmux-android2dts.py` | converte a tabela de pinmux de uma placa Tegra 2 do kernel Android (board-*-pinmux.c) em nós pinctrl do DT, validando contra o driver do mainline |
| `initramfs/` | `/init` próprio (busybox): monta o Alpine e faz switch_root; com Volume − no boot, modo de resgate com rede USB (NCM), serial (ACM), telnet e pstore. `xoom-check` faz um diagnóstico. `*.list.in`: listas do gen_init_cpio (troque `@XOOM@` pela pasta de trabalho) |
| `boot/gravar-boot.sh` | envia uma boot.img pelo ssh, confere sha256, grava, confere de novo e espera o kernel novo voltar |
| `emc/` | tabelas de timing da RAM tiradas do Android (`board-stingray-memory.c`, GPL-2.0) e convertidas para o DT (`tabelas-android2dts.py`), leitura dos registradores da EMC, testes |
| `testes/` | DVFS da CPU, série de reboots, análise de gravações do microfone |
| `userspace/` | reboot com parâmetro (fastboot/recovery), AT do modem, endereço do Bluetooth |
| `grate/wlrshaders/` | os shaders do wlroots em assembly do Tegra (com e sem blend) e o gerador do `grate_wlr_shaders.h` do fork do Mesa. Montados com o `gen_shader_bin` do xf86-video-opentegra |
| `grate/wlrtest/` | teste dos shaders e do estado do wlroots no GR3D, conferindo pixels |
| `docs/diario-tecnico.md` | o diário técnico do port (14 a 19/10/2026): cada problema, a causa e a correção, com os números |

## Montar e gravar

Toolchain usada: gcc 16.2 nolibc (`arm-linux-gnueabi-`). No fork do kernel:

```
make ARCH=arm tegra_defconfig
scripts/config --set-str INITRAMFS_SOURCE "<pasta>/initramfs/initramfs.list"
make ARCH=arm stingray.config          # depois do INITRAMFS_SOURCE (senão o XZ do initramfs se perde)
make ARCH=arm -j16 zImage dtbs modules
cat arch/arm/boot/zImage arch/arm/boot/dts/nvidia/tegra20-motorola-stingray.dtb > zImage-dtb
mkbootimg --kernel zImage-dtb --base 0x10000000 --kernel_offset 0x8000 \
  --ramdisk_offset 0x04000000 --second_offset 0xf00000 --tags_offset 0x100 \
  --pagesize 2048 --header_version 0 --cmdline "console=tty0 ignore_loglevel panic=5" -o boot.img
```

O bootloader de consumidor recusa `fastboot boot`: grava-se `fastboot flash recovery` (12 MB)
ou `boot` (8 MB, por isso XZ). O DTB vai anexado ao zImage e o initramfs embutido (o
bootloader sobrescreve um ramdisk separado).

**Cuidado:** nunca gravar mmcblk0p1 a p5 (bootloader). Faça backup de boot e recovery antes.
Kernels sem o último commit da série travam o reboot quando o tablet está só na bateria:
deixe o cabo USB ligado.

## Licenças

Scripts e ferramentas: MIT (`LICENSE`). `initramfs/` e os fragmentos de DT: GPL-2.0
(`LICENSE.GPL-2.0`). `emc/board-stingray-memory.c` e `emc/tegra2_emc.c` vêm do kernel
Android (Google, GPL-2.0, cabeçalho original). Os shaders partem do `blend_over` do
xf86-video-opentegra (MIT).

Nada de firmware, NVRAM, backups de partição ou binários do Android está aqui: cada um
tira os seus do próprio aparelho.

---

# Mainline Linux on the Motorola Xoom (Tegra 2)

Mainline Linux (7.3-rc7) and Alpine Linux, with Sxmo and Phosh, on a 2011 Motorola Xoom 3G
(MZ605, "stingray" board, NVIDIA Tegra 20), with 3D acceleration through the grate Mesa
driver. The port started on 2026-10-14 (first boot: Tux with a blue beak, red and blue
swapped) and the tablet has been in daily use since.

This repository holds the tools, the initramfs, the tests and the technical diary of the port
(`docs/diario-tecnico.md`, in Portuguese); changes to third-party
software live in the forks listed in the table above (kernel, grate Mesa and libdrm,
wlroots, libhybris). Sister repositories: xoom-alpine (root filesystem and configuration)
and xoom-gps (GPS through the Android HAL).

**Works:** display (Tegra DRM over LVDS) and backlight, touchscreen, keys and sensors,
Wi-Fi, Bluetooth (no LE), battery and charger, speaker, microphone and PipeWire, GPU
compositing for sway and phoc, CPU (216 MHz-1 GHz) and RAM (50-600 MHz) frequency
scaling, thermal zones, USB gadget, 3G modem (AT only), GPS, reboot on battery.
**Not yet:** HDMI video, cameras, modem registration/data, Bluetooth audio quality,
headset, automatic suspend.

Build and flashing instructions are in the Portuguese section above (the commands are the
same). Never write mmcblk0p1-p5 (bootloader partitions). Scripts and tools are MIT;
`initramfs/` and device tree fragments are GPL-2.0; the two Android EMC files keep their
GPL-2.0 headers. No firmware, NVRAM, partition backups or Android binaries are included.
