# Diário técnico: Linux mainline no Motorola Xoom

Cópia pública do diário que guiou o port (14 a 19/10/2026), com dados do aparelho
(MAC, senha, posição) e notas de outro projeto removidos. Os caminhos citados
(`grate/`, `emc/`, `kernel-hw/`...) são da pasta de trabalho do autor; o código está
nos forks e nos repositórios xoom-*. Os números de kernel (#13, #26...) contam as
imagens gravadas; o mapa para os commits está no README.

## Aparelho

- Motorola Xoom 3G (MZ600/MZ601, CyanogenMod "everest"), placa "stingray",
  Tegra 2 (T20), revisão de hardware P3, bootloader 1049, desbloqueado.
- Painel AUO 1280x800 LVDS.
- CPU sem NEON (vfpv3d16). 1 GB RAM. eMMC 32 GB.

## Partições (estado atual)

| Partição | Conteúdo |
|---|---|
| boot (mmcblk0p7, 8 MB) | `boot-mainline-boot-pg3pulso.img` (kernel #26 = #24 + **reboot sem carregador corrigido** (pulso do PG3/SYS_RESTART_B antes do reset + bit SOFT_RESET do VAL1, no driver cpcap-reboot-mode) + DTB `emc/tegra20-motorola-stingray.dts.26-pg3-pulso` (sem o hog do PG3); sha256 00ad715a…564a; gravado em 2026-10-19 ~00:48; ver "Reboot travado sem carregador"). **Kernels ≤ #25 travam o reboot na bateria: para gravar/voltar a um deles, ligar o cabo USB no PC antes do reboot.** Antes: `boot-mainline-boot-softreset.img` (#25 = #24 + só o bit SOFT_RESET; sha256 ed8fe1c4…e19a; não resolveu). Antes: `boot-mainline-boot-i2crec.img` (kernel #24 = #23 + **recuperação do i2c-0 por GPIO** (patch no i2c-tegra) + DTB `emc/tegra20-motorola-stingray.dts.25-i2c-recuperacao` (inclui UARTE do GPS); sha256 8985f5cc…8dfa; gravado em 2026-10-18 ~22:50; ver "Recuperação do i2c-0"). Antes: `boot-mainline-boot-gps.img` (#23 + DTB do GPS, sha256 ffc110d5…8320). Antes: `boot-mainline-boot-bt2.img` (kernel #23 = #21 + **Bluetooth** (firmware no initramfs) + **sensor de luz**; sha256 bff9144e…0328; gravado em 2026-10-18 ~00:25; ver "Bluetooth e sensor de luz"). Antes: `boot-mainline-boot-modem.img` (kernel #21 = #20/750 mV + **USB3 do modem 3G** + drivers seriais/QMI/PPP como módulos; sha256 11c65a77…d6c0; gravado em 2026-10-18 ~00:10; ver "Modem 3G"). Antes: `boot-mainline-boot-750.img` (kernel #20 + vdd_cpu mínimo 750 mV; sha256 03099167…36f4; gravado em 2026-10-18). Antes: `boot-mainline-boot-pm.img` (kernel #20 = #19 + **runtime PM por job na UAPI antiga** (grate/0010); sha256 c97963e9…fc7e; core cai para 1,1 V em repouso). Antes: `boot-mainline-boot-core.img` (kernel #19 = #18 + **acoplamento vdd_core/aon/cpu**; sha256 5a1ea25c…3494). Antes: `boot-mainline-boot-hw2.img` (kernel #18: correções do PMC, reboot-bootloader, áudio HDMI, LP1, PG3 alto; sha256 da989de1…332e; gravado em 2026-10-17 ~22:40, ver "Hardware restante"). Antes: `boot-mainline-boot-emc2.img` (kernel #17: DVFS da CPU + thermal + **DVFS da RAM** + correção da banda do display; sha256 a9630fad…2cd9; gravado em 2026-10-17). Volta segura: `boot-mainline-boot-emc.img` (#16, sha256 6e6809d1…82b8), depois `boot-mainline-boot-thermal.img` (#15, sha256 8083…4283); antes dele `boot-mainline-boot-cpufreq.img` (#14, sem lm90 embutido: ver Thermal) |
| recovery (p6, 12 MB) | `boot-mainline.img`: mainline com módulos (resgate) |
| userdata (p10, 29 GB) | Alpine 3.24 (Sxmo) |
| system (p8) | CyanogenMod antigo, sem uso |
| p1–p5 | do bootloader: NUNCA gravar (backup em `stock/particoes/`) |

Backups do original: `stock/boot-mmcblk0p7.img` (CM/ElementalX),
`stock/recovery-mmcblk0p6.img` (TWRP), `stock/params.txt` (offsets e histórico).
Segurar Volume − no boot = modo de resgate do initramfs (telnet, diagnóstico).

## Kernel

- Árvore: `linux/` (mainline 7.3.0-rc7), build em `out-stingray/`,
  toolchain `toolchain/gcc-16.2.0-nolibc/arm-linux-gnueabi/bin/arm-linux-gnueabi-`.
- Config: `tegra_defconfig` + `stingray.config`. Compilar:
  `cd linux && make ARCH=arm CROSS_COMPILE=... O=../out-stingray -j16 zImage dtbs modules`
- Imagem boot: `cat zImage + dtb > zImage-dtb-boot` e mkbootimg com
  `--base 0x10000000 --kernel_offset 0x8000 --ramdisk_offset 0x04000000
  --second_offset 0xf00000 --tags_offset 0x100 --pagesize 2048 --header_version 0
  --cmdline "console=tty0 ignore_loglevel panic=5"` (mkbootimg.py em
  `~/android/lineage/system/tools/mkbootimg/`). Limite da boot: 8388608 bytes.
- Módulos vão para o Alpine (modules_install com INSTALL_MOD_STRIP=1 em
  `out-stingray/modstage`, depois tar por ssh para /lib/modules).
- Patch completo: `0001-ARM-tegra-add-Motorola-Xoom-stingray.patch` (DTS, debug DTS,
  binding tegra.yaml, driver novo `drivers/w1/masters/tegra-owr.c` + binding,
  correção de nome no `ds2781_battery`). Validado com dtbs_check (11 avisos conhecidos).
- dt-schema: venv em scratchpad (recriar com `pip install dtschema` se sumir).

### Funciona
PMIC CPCAP e reguladores, eMMC (GPT do Tegra), microSD, vídeo Tegra DRM via LVDS
(BGR ok), backlight LP8550, touch mXT1386 (com wake-gpios PJ2), teclas, sensores
(gyro, accel, magnetômetro, barômetro, NCT1008), Wi-Fi BCM4329 (brcmfmac, firmware do
linux-firmware + NVRAM do próprio tablet), bateria DS2781 via 1-Wire (driver novo),
carregador bq24617 (gpio-charger), USB gadget, sensor de luz MAX9635, Bluetooth BCM4329
(BR/EDR, sem LE), modem 3G no USB3 (só AT por enquanto).

### Lições aprendidas (não repetir os erros)
- Sem `core-supply` no PMC, nada no domínio pd_core probea (USB, eMMC, display).
- LP8550: dev-ctrl precisa do bit 0 (0x05), senão backlight desligado.
- Pinmux: grupos sem registrador de pull (LCD, hdint, pmc, sdb) não podem ter
  nvidia,pull; um erro descarta o pinmux inteiro. Conversor corrigido:
  `tegra20-pinmux-android2dts.py`.
- O bootloader carrega o kernel em 0x10008000; ramdisk em 0x11000000 é sobrescrito.
  Usamos initramfs embutido.
- O reboot só volta sozinho na bateria se o kernel pulsar o PG3 (`sys_restart_b` do CPCAP)
  antes do reset pelo PMC, como o Android (driver cpcap-reboot-mode, #26). Com cabo USB
  ligado ao PC ele sempre voltava, o que confundiu os testes (o hog do PG3 do #18 não era a
  correção). Ver "Reboot travado sem carregador".

### Pendências do kernel
(Lista completa e atualizada em "PENDÊNCIAS", no fim deste arquivo.)
- Câmeras, modem, vídeo HDMI com cabo (ver "Hardware restante"). Oops do powergate,
  reboot-bootloader, áudio HDMI e suspend LP1: resolvidos no #18; reboot travado: no #26.

## DVFS da CPU (2026-10-16): FUNCIONA (cpufreq-dt, ondemand, 216 MHz–1 GHz)

- Antes: sem `operating-points-v2`/`cpu-supply` no DTS, o tegra20-cpufreq saía com
  -ENODEV e a CPU ficava fixa em 1 GHz (pll_x do bootloader), sem /sys/.../cpufreq.
- vdd_cpu = MAX8649 em 0x60 no DVC (i2c-3), modo VID 1 nas placas P1+ (Android:
  board-stingray-power.c, 0,77–1,1 V, rampa 32 mV/us). O bootloader deixa MODE1 =
  0x97 (980 mV + PWM forçado). MODE0/2 = 0x3f e MODE3 = 0x21 não são usados.
- Chip: A03p, SKU 8 → soc speedo 1, CPU process 1 (`hardware version 0x2 0x2`).
  OPPs mainline (tegra20-cpu-opp*.dtsi): 216/312 @750, 456 @800, 608 @850,
  760 @875, 816/912 @950, 1000 MHz @1000 mV.
- `grate/0006-regulator-max8649-add-device-tree-support.patch` (candidato a upstream):
  compatible `maxim,max8649`, `maxim,vid-mode` obrigatório, init_data pelo DT,
  `regulator-ramp-delay` pelo registrador RAMP (regulator_set_ramp_delay_regmap);
  binding `regulator/maxim,max8649.yaml` (dt_binding_check ok). CONFIG_REGULATOR_MAX8649=y
  no stingray.config.
- DTS (no 0001): `vdd_cpu: regulator@60` com 800–1080 mV, cpu0/cpu1 com cpu-supply +
  operating-points-v2 + #cooling-cells. Mínimo era 800 mV (hoje 750, ver abaixo) = folga nas OPPs de 750 (216/312
  rodam a 800). Máximo 1,08 V porque vdd_core está fixo em 1,2 V e a CPU tem de ficar
  ≥120 mV abaixo do core. SEM acoplamento (regulator-coupled-with): o core/RTC continuam
  fixos em 1,2 V, então o acoplador tegra20 não entra.
- Conferido no MAX8649 (i2cget -f -y 3 0x60 1): 0x85 = 800 mV em 216–456 MHz,
  0x8a = 850 em 608, 0x99 = 1000 mV em 1 GHz (760 → 880, passo de 10 mV).
- Teste `cpufreq/teste-dvfs.sh` (/root no tablet): cada frequência fixa por 3 min, 2
  laços gzip→gunzip de 16 MB conferindo sha256: 0 erros nas 8 frequências, 35→42 °C
  (NCT1008). Ondemand com carga intermitente por 3 min: 127 trocas de frequência,
  101 rodadas, 0 erros. Uso normal da interface durante o teste, sem queda.
- vdd_core NÃO dá para escalar ainda (analisado 2026-10-16): o EMC roda a 600 MHz
  (pll_m) e o tegra20-peripherals-opp.dtsi exige core 1,2 V para EMC 600/666 MHz; o
  Android limitava SW2/SW4 a 1,0–1,2 V, então o piso = teto. Sem timings de memória no DT
  ("device-tree doesn't have memory timings") o EMC não muda de frequência e NÃO vota no
  genpd (pm_genpd_summary: memory-controller "unsupported"). Ligar o acoplamento
  core/RTC/CPU (regulator-coupled-with + nvidia,tegra-*-regulator, como no Acer A500)
  agora seria PERIGOSO: depois do sync_state o core desceria até ~1,1 V (votos de
  host1x/USB) com a RAM a 600 MHz. Pré-requisito: DVFS do EMC (timings da Elpida LPDDR2
  do Android em nvidia,tegra20-emc-table) — só então o core pode cair em repouso.
- Mínimo de 750 mV feito em 2026-10-18 (ver "DVFS da RAM / EMC"). O WARN
  `tegra_pmc_enter_suspend_mode` (pmc.c:4999) no boot é antigo (já em 14/10).

### Thermal zones (2026-10-16, kernel #15): freio da CPU por temperatura FUNCIONA

- DTS (no 0001): label `nct1008` no sensor @4c e `thermal-zones` iguais às do Acer A500:
  `skin-thermal` (sensor 0, interno/placa) freia a 60 °C e desliga a 70 °C;
  `cpu-thermal` (sensor 1, diodo da CPU) freia a 85 °C e desliga a 90 °C. Freio =
  cpufreq de cpu0/cpu1 (cooling_device0 "cpufreq-cpu0", 8 estados), governor step_wise.
- `CONFIG_SENSORS_LM90=y` (era =m) para as zonas não dependerem do módulo. No tablet
  o `lm90.ko` saiu de /lib/modules (guardado em /root/lm90.ko.antes-thermal) e o
  `modules.builtin` foi atualizado + depmod. **Se voltar ao #14, devolver o lm90.ko**
  (senão some o hwmon do NCT1008).
- Testado baixando o trip passivo da cpu-thermal para 39 °C pelo sysfs
  (`/sys/class/thermal/thermal_zone1/trip_point_0_temp`, gravável) com 2 laços de gzip:
  a CPU caiu para 912/816/760 MHz, a temperatura ficou em 39–40 °C e voltou a 1 GHz
  sem carga. Trip devolvido a 85 °C (sysfs não persiste). Ver estado:
  `grep . /sys/class/thermal/thermal_zone*/temp /sys/class/thermal/cooling_device0/cur_state`.
- Em uso normal: placa ~33 °C, CPU ~35–37 °C; 1 GHz sob carga contínua chega a ~42 °C.

### DVFS da RAM / EMC (2026-10-16/18): FUNCIONA 50–600 MHz; core acoplado e escalando 1,1–1,2 V (#20)

- DTS (no patch 0001 desde 2026-10-17): `memory-controller@7000f400` com `emc-tables@0`
  = tabela "Elpida 40nm" do board-stingray-memory.c do Android (que tinha
  CONFIG_TEGRA_EMC_SCALING_ENABLE=y), escolhida pelo nó lpddr2 (rev <1 0>, 2048 Mbit,
  x16; RAM code do strap = 0 em todos os Xoom). 43 dos 46 registradores que o bootloader
  deixa a 600 MHz batem com a entrada da tabela (só os do DLL leem diferente). Também
  `opp-table-emc` sem as OPPs de 666/760 MHz (sem timings; acabou o aviso
  `out of range: 760000000 600000000`). dtbs_check: nenhum aviso novo.
  Arquivos em `emc/`: fontes do Android, `tabelas-android2dts.py`, json das tabelas
  (Elpida 40/50 nm, Samsung), `ler-emc.py`, `teste-emc.sh`, `teste-emc-baixo.sh`,
  `memtester-longo.sh`, `gravar-boot.sh IMG N` (espera `uname -v` = #N).
- No boot: "got 5 timings for RAM code 0 (min 50MHz max 600MHz)". O devfreq
  (simple_ondemand) escolhe a frequência; o memory-controller vota no genpd (1,2 V a 600).
  Com a tela ligada o display pede ~199 MHz pelo interconnect → só 300/600.
- **Bug do mainline corrigido (kernel #17)**: com a tela apagada o display continuava
  pedindo 245 MB/s e o EMC não descia de 300 MHz. A sway/wlopm solta os planos no mesmo
  commit que desliga o CRTC, e `tegra_crtc_update_memory_bandwidth` (dc.c) só percorria
  os planos do estado NOVO (vazio). Agora usa o `plane_mask` do estado antigo:
  `grate/0007-drm-tegra-dc-release-icc-bw-of-detached-planes.patch` (candidato a upstream).
  Conferido: tela apagada → banda 0 → EMC a 50 MHz.
- Testes (memtester + gzip/sha256 + teste de GPU):
  - tela ligada, 3 min/freq (#16): 300 MHz gzip 19/0, GPU 65/0; 600 MHz gzip 24/0, GPU
    89/0; memtester 64 MB 1 passada/0 erros em cada.
  - memtester 300 MB, 20 min em 300 e 20 min em 600 MHz: nenhuma passada completa (uma
    passada leva > 20 min); a 600 MHz Stuck Address, Random, Compare*, Seq. Increment,
    Solid Bits e Block Sequential deram ok, sem FAILURE. A saída de 300 foi perdida (script
    corrigido para guardar a parcial).
  - tela apagada (Sxmo screenoff), 2 min/freq (#17): memtester 4 MB e gzip de 2 MB sem
    erros: 50 MHz mt 1/0 gz 32/0; 100 MHz 1/0, 61/0; 150 MHz 2/0, 81/0.
    **teste de GPU falhou** (50: 23/41, 100: 52/89, 150: 79/125): faltam os últimos blocos da
    "malha grande" (desenho incompleto, não dados trocados).
- **GPU dessincronizada depois do teste a 50 MHz (até o próximo reboot)**: syncpoints do
  GR2D (id 1) e GR3D (id 2) com o hardware 1 à frente do máximo do kernel
  (`/sys/kernel/debug/tegra-host1x/status`: `min 3329 max 3328`; dmesg cheio de
  `syncpt_load failed`). Toda espera termina um job antes → teste de GPU falha mesmo a 600 MHz
  (10/10), com GRATE_BATCH=1 e com o driver da sway. Causa provável: o grate submete todo
  job com `timeout = 1000` ms (`drivers/grate/drm/uapi_v1/job.c:156`); a 50 MHz um job
  passou de 1 s, o host1x completou o syncpoint pela CPU (cdma_timeout_cpu_incr) e a GPU
  incrementou de novo ao terminar (o dmesg rodou e não sobrou o log do timeout).
  Em uso normal o EMC só fica abaixo de 300 MHz com a tela apagada, mas um job pesado
  nesse momento pode causar o mesmo. **Reiniciar limpa**; pode haver falhas de desenho
  na sway até lá.
  **Correção (2026-10-17)**: timeout do SUBMIT 1000 → 10000 ms (o kernel aceita até
  10000, drivers/gpu/drm/tegra/drm.c) e espera do fence em grate_stream.c 1000 → 10000 ms
  (com 1 s ela desistia e os BOs do job eram soltos com a GPU ainda usando). Instalado nos
  dois drivers; ver "TIMEOUT DE 10 s" na seção do grate. **Testado (2026-10-17, após
  reboot)**: `sh /root/teste-emc-baixo.sh 120 "50000000"` (o script não tem +x) →
  50 MHz mt=[1 0] gz=[29 0] **gpu=[42 0]** (antes 41/23); GR2D/GR3D com min = max depois
  (44/44, 518/518) e teste de GPU 23/23 a 300 MHz com os dois drivers. Os únicos
  `syncpt_load failed` são do **id=26** (min=11 max=0), que não pertence a nenhum cliente
  (não aparece no status): já surge no boot (~31 s) e em transições da tela; inofensivo,
  provavelmente resto do bootloader recarregado quando o host1x volta do runtime PM.
  O reboot travou de novo com tela preta (sem rede); subiu depois de religar no Power.
- O 1º teste de tela apagada (sway `power off` + EMC travado em 50 MHz) deixou a tela
  "fora de sincronia": o Sxmo foi para `lock` por inatividade e acendeu a luz de fundo
  com a saída desligada (painel aceso sem sinal). Por isso o `teste-emc-baixo.sh` usa o
  estado screenoff do Sxmo (ambiente da sessão + WAYLAND_DISPLAY, por causa do wlopm) e
  destrava o EMC se a banda do display ou a luz de fundo voltarem. O `dpms` do sysfs fica
  "On" mesmo com a saída desligada: usar a banda do interconnect.
- O reboot para o #17 travou com tela preta (sem rede, sem USB, pstore vazio); subiu
  normal depois de desligar e religar no Power. Já tinha acontecido antes do DVFS da RAM.
- **Passo 3: acoplamento vdd_core/aon/cpu FUNCIONA (kernel #19, 2026-10-18)**:
  `boot-mainline-boot-core.img` (= #18 de "Hardware restante", com a correção do
  PMC, + acoplamento; sha256 5a1ea25c…3494). DTS em `emc/...dts.19-hw-acoplamento`, já no
  patch 0001 (o patch isolado continua em `emc/acoplamento-vdd-core.patch`). vdd_core
  (SW2) e vdd_aon (SW4) 1,0–1,2 V com regulator-coupled-with/max-spread <170000 550000> e
  nvidia,tegra-core/rtc-regulator; vdd_cpu com <550000 550000> e nvidia,tegra-cpu-regulator.
  dtbs_check: 3 avisos novos (nvidia,tegra-*-regulator não estão nos schemas YAML do
  MAX8649/CPCAP; o binding do acoplamento ainda é .txt no mainline).
  - Boot: "core voltage initialized to 1200000uV" e "**voltage state synced**" (só aparece
    com a correção do PMC, que faz `tegra_pmc_core_domain_state_synced()` ler a flag certa).
  - Teste `teste-dvfs.sh 120` (8 frequências da CPU, 2 laços gzip/sha256) com
    `emc/amostrar-tensoes.sh` (a cada 0,5 s): **0 erros**; 697 amostras, **0 violações**
    (CPU+120 mV ≤ core e aon; |core−aon| ≤ 170 mV). vdd_aon segue a CPU: 1,0375 V (436
    amostras), 1,075 (198), 1,125 (63). Dmesg sem avisos do acoplador.
  - No #19 o core NÃO descia de 1,2 V com a sway GLES2 aberta: o GR2D votava 1,2 V
    (300 MHz). O grate usa a UAPI antiga do tegra-drm, que fazia `pm_runtime_resume_and_get`
    ao abrir o canal e só soltava ao fechar (drm.c), então GR2D e GR3D ficavam ligados no
    clock máximo o tempo todo.
- **Kernel #20 (2026-10-18): runtime PM por job na UAPI antiga** —
  `grate/0010-drm-tegra-legacy-uapi-runtime-pm-per-job.patch` (candidato a upstream): o
  `tegra_drm_submit` liga o motor antes do `host1x_job_submit` e solta no `job->release`
  (`pm_runtime_put_autosuspend`, 500 ms), como a UAPI nova (submit.c); o open/close do
  canal não segura mais o PM. Boot `boot-mainline-boot-pm.img` (sha256 c97963e9…fc7e).
  - Em repouso GR2D/GR3D ficam `suspended` e o **core cai para 1,1 V** (1,125 V com a CPU
    a 1 GHz: CPU + 125 mV). O piso de 1,1 V agora é o host1x (150 MHz, ativo enquanto o
    display estiver ligado); o dc vota 0,95 V. Sob carga de GPU o core sobe a 1,2 V e volta.
  - Testes: teste de GPU 5/5 e wlrtest OK; 60 testes de GPU com 0,7 s de pausa (GR3D desligado e
    religado entre 54 deles): 0 falhas, syncpoints min = max; `teste de GPU -b 20` 45,8 ms
    (antes 42–49). Interface do Sxmo normal.
  - `syncpt_load failed: id=26, min=10, max=0` aparece só ao ler
    /sys/kernel/debug/tegra-host1x/status: syncpoint alocado com valor antigo; inofensivo.
- **vdd_cpu mínimo 750 mV (2026-10-18)**: `boot-mainline-boot-750.img` (zImage #20 + DTB com
  regulator-min-microvolt = 750000; sha256 03099167…36f4). As OPPs de 216/312 MHz deste chip
  pedem 750 mV (o Android usava no mínimo 770). MAX8649 = 0x80 (750 mV) a 216 MHz.
  `teste-dvfs.sh 120` (8 frequências, gzip/sha256): **0 erros**; 216/312 MHz a 750 mV,
  456 @800, 608 @850, 760 @880, 816/912 @950, 1000 @1000 mV; 32→38 °C.
  Amostrador: core 1,1 V em 670 de 708 amostras, aon 1,0–1,125 V. As 4 "violações" que ele
  marcou eram leituras no meio de uma descida (lê core e depois aon; a amostra seguinte já
  mostra os dois descidos) — o acoplador confere as regras antes de cada mudança e não
  imprimiu nenhum "voltage constraint violated".

## Hardware restante (2026-10-17, kernel #18): oops, WARN, reboot-bootloader, HDMI, LP1

Notas completas: `kernel-hw/NOTAS.md` (inclui o levantamento de câmeras e modem). Build
do #18 em `kernel-hw/out-teste` (árvore `kernel-hw/linux-teste` = hardlinks da `linux/`);
tudo já integrado na `linux/` + `stingray.config` (CONFIG_CPCAP_REBOOT_MODE=y) + 0001.
DTS do #18: `emc/tegra20-motorola-stingray.dts.18-hw`. Imagens: `boot-mainline-boot-hw.img`
(#18 sem o hog do PG3) e `boot-mainline-boot-hw2.img` (gravada).

- **Oops do debugfs powergate e WARN pmc.c:4999 (bugs do mainline 7.3)**:
  `grate/0008-soc-tegra-pmc-fix-early-pmc-state-and-powergate-debugfs.patch`. O probe do
  PMC passou a usar uma struct própria, mas o cpuidle, o suspend e o acoplador do core
  leem o `early_pmc`: `rate` ficava 0 (o WARN; LP2 com tempos de 100 MHz),
  `core_domain_state_synced` ficava false (o acoplador tegra20 nunca deixaria o vdd_core
  descer: importante para o passo 3 do DVFS) e o probe adiado não devolvia o
  `suspend_mode` a NOT_READY (cpuidle em LP2 antes do probe). O `powergate_show` usava o
  argumento `data` (= SEQ_START_TOKEN, 1) em vez de `s->private` → leitura em 0x19.
  linux-next só copia o `rate`. Conferido no #18: `cat /sys/kernel/debug/powergate` lista
  os domínios e não há WARNING no boot. Candidato a upstream.
- **reboot-bootloader FUNCIONA**: `grate/0009-power-reset-add-cpcap-reboot-mode-driver.patch`
  (driver `cpcap-reboot-mode`, célula nova no motorola-cpcap, binding yaml com
  dt_binding_check ok). O bootloader da Motorola lê o VAL1 do CPCAP (0x0428):
  BOOT_MODE 0x800 = fastboot, FOTA_MODE 0x4 = recovery (Android: board-stingray-power.c);
  o bit 30 do PMC scratch0 que o mainline grava é ignorado. Nó `reboot-mode` no pmic@0.
  O driver limpa os bits no probe; o bootloader também limpa (VAL1 = 0 depois de sair do
  fastboot). Userspace: `/usr/local/sbin/reboot-bootloader [recovery]` grava
  /run/reboot-param e chama o reboot do busybox; a última linha `::shutdown:` do
  /etc/inittab roda `/usr/local/sbin/reboot-param --from-inittab` (compilado no tablet de
  `kernel-hw/userspace/reboot-param.c`), que faz reboot(RESTART2, arg) depois do
  `openrc shutdown`. Cópias em `alpine/config/` (o montar-rootfs.sh precisa compilar o
  reboot-param.c no alvo: só o fonte está em usr/local/src). Testado: parou sozinho no
  fastboot; saída com `fastboot reboot` (cabo USB) ou pelo menu (Volume).
- ~~Reboot travado com tela preta CORRIGIDO (PG3)~~ **(conclusão errada: ver "Reboot travado
  sem carregador", 2026-10-19; os reboots "ok" do hog foram todos com cabo USB no PC)**: o Android mantém o PG3
  (`sys_restart_b` do CPCAP) em saída alta desde o boot e o pulsa 0 → 1 antes do reset;
  no mainline o pino ficava na função "ide" do grupo atc, lendo 0. Hoje 3 de 3 `reboot`
  travaram assim; com o PG3 alto (sysfs, depois hog `sys-restart-b-hog` no DTS) foram
  3 reboots ok + o reboot-bootloader. O `gpio-restart` não serve: termina o pulso com o
  pino ativo e só então passa ao PMC.
- **Áudio HDMI**: `spdif@70002400` okay + `nvidia,fixed-parent-rate` (igual A500). Agora há
  a placa ALSA 1 "NVIDIA Tegra20 HDMI" e nada em devices_deferred. **Vídeo HDMI sem teste**
  (falta cabo micro-HDMI): DTS já tinha hdmi@54280000 (5 V em PC4, VCSI, DDC i2c@7000c400,
  HPD PN7); o conector card0-HDMI-A-1 existe e o HPD lê 0 sem cabo.
- **Suspend LP1 FUNCIONA**: `nvidia,suspend-mode = <1>`. O mainline do Tegra 20 não tem LP0
  (sem warmboot; `tegra_pm_validate_suspend_mode` limita a LP1), então o `PWRREQ_OE`
  (bit 9) que o Android ligava para o LP0 não é necessário: **não ligar** (só faz sentido
  com a macro 14 do CPCAP derrubando o vdd_core). Testado: `rtcwake -d rtc1 -m mem -s 20`
  ("Entering suspend state LP1", voltou em 21 s, tela, toque, Wi-Fi e sway ok) e
  acordar pelo Power (2º teste, acordou em 85 s pelo botão). suspend_stats: 2 ok, 0 falhas.
  Consumo suspenso ~105 mA (2,5 mAh em 85 s, medidor grosso) contra ~360 mA acordado com
  a tela acesa. O Sxmo NÃO suspende sozinho (sxmo_autosuspend não roda): para usar,
  ligar o autosuspend do Sxmo e conferir os wakeups (Power, RTC, carregador, Wi-Fi).
- Câmeras: só levantamento (ver PENDÊNCIAS e `kernel-hw/NOTAS.md`). Modem: ver "Modem 3G".

## Reboot travado sem carregador (2026-10-19, kernel #26): CORRIGIDO

- Sintoma: `reboot` (ssh ou gravar-boot.sh) deixava o tablet morto: sem luz de fundo, sem logo,
  sem rede e sem USB, até segurar o Power. Ligar o cabo no PC com ele travado **não** muda nada:
  nem RCM (0955:7820), nem fastboot, nem o carregador religa. Ou seja, o CPCAP não desligou e a
  boot ROM não caiu em RCM: o SoC fica parado logo no reset/início do bootloader. O pstore volta
  vazio porque segurar o Power corta a RAM.
- **Depende do cabo USB**: no journal do PC (eventos USB do gadget "Motorola Xoom (mainline)" em
  1-5.4.4) e no /var/log/messages do tablet (gap entre `syslogd exiting` e o boot seguinte):
  com o cabo ligado ao PC, ~15 reboots de 15 a 18/10 voltaram em ~27 s (inclusive os do #18 que
  "provaram" o hog do PG3); só na bateria, todos os vistos travaram (os 3 do #17 em 17/10, 4 de 4
  no #23/#24 em 18–19/10: gaps de 4,6 h, 7,5, 7 e 11,5 min). O hog do PG3 não tinha nada a ver.
- Android (`kernel-hw/android/board-stingray.c`, `board-stingray-power.c`): `stingray_reset()`
  põe o PG3 (sys_restart_b do CPCAP, "stop the uC") em 0 por 100 ms, 1 por 100 ms e só então
  `tegra_assert_system_reset()`; e o `cpcap_validity` liga o bit SOFT_RESET (0x10) do VAL1 no
  probe e só o limpa no power off (também ligava PGC SYS_RST_MODE + macro 15, não feito).
- **#25** (`boot-mainline-boot-softreset.img`): só o bit SOFT_RESET no VAL1 (lido 0x0010): **0 de 1**
  na bateria. Hipótese do VAL1 sozinha descartada.
- **#26** (`boot-mainline-boot-pg3pulso.img`, sha256 00ad715a…564a): driver cpcap-reboot-mode com
  `sys-restart-gpios` (PG3, GPIO_ACTIVE_LOW; pino em alto desde o probe, substitui o hog) e
  handler de restart com prioridade SYS_OFF_PRIO_DEFAULT (antes do PMC, que é LOW): 0 → 100 ms →
  1 → 100 ms → PMC. Mantém o SOFT_RESET do #25. **Série de 10 reboots seguidos só na bateria:
  10 de 10**, cada um voltou em 61–64 s até o ssh (bateria 38 %, EMC 300 MHz, CPU 608–1000 MHz).
  Conferir no tablet: `grep sys-restart /sys/kernel/debug/gpio` → `gpio-51 … out hi ACTIVE LOW`;
  VAL1 em `/sys/kernel/debug/regmap/spi0.0/registers` linha `0428: 0010`.
- Causa provável: o PMC reseta só o T20; sem o pulso, o microcontrolador do CPCAP (macros do
  bootloader) continua no estado de "sistema rodando" e o SoC não volta. Com VBUS presente o
  CPCAP segue outro caminho (detecção do carregador) e o boot acontecia. Não conferido por dentro
  (o firmware do uC do CPCAP é fechado).
- Arquivos: `reboot/` (fontes antes/depois do driver, `serie-reboot.sh N [espera]` = N reboots
  pelo ssh contando sucessos, para no 1º que não voltar; logs `serie-*.log`, builds). Patch
  `grate/0011-power-reset-cpcap-reboot-mode-soft-reset-and-sys-restart-pulse.patch` (driver +
  binding, por cima do 0009; dt_binding_check ok, dtbs_check sem avisos novos). DTS no 0001
  regerado (backup `reboot/0001.antes-reboot.patch`).
- O `gpio-restart` padrão não serve: com GPIO_ACTIVE_LOW termina o pulso com o pino em 0, e com
  ACTIVE_HIGH + open-source deixa o pino solto (entrada) durante o uso.

## Modem 3G (2026-10-18, kernel #21): MDM6600 UMTS ENUMERA no USB3 e responde AT

- **O tablet é o MZ605 (3G UMTS/HSPA)**, segundo o adesivo da traseira. O bootloader passa
  `androidboot.modelno=MZ600 product_type=cw` (CDMA), o que está **errado** (firmware do
  MZ600 em algum momento?). O CM do tablet era o `cm_everest` = Xoom 3G UMTS (no CM:
  stingray = MZ600 Verizon, wingray = Wi-Fi), e a boot.img dele forçava `product_type=uw`.
- Android (board-stingray*.c, igual no ElementalX): com "u" e sem "c", o kernel NÃO controla
  a energia do modem (o mdm6600_ctrl e o wrigley são só do CDMA) e sempre registra o ehci3.
  O modem sobe sozinho. RIL do CM everest (system.prop): `libmoto_ril.so`, mux 27.010 em
  `/dev/ttyUSB2` (8 canais), tcmd em ttyUSB3, modem em ttyUSB4, dados por pppd.
- DTS (#21, no 0001; = `emc/tegra20-motorola-stingray.dts.22-modem`): `usb@c5008000` okay
  (host) + `usb-phy@c5008000` com hssync-start-delay 0 e xcvr-setup 8 (utmi_phy_config[1]).
  stingray.config: USB_SERIAL, USB_SERIAL_WWAN/OPTION/QUALCOMM, USB_NET_QMI_WWAN, N_GSM, PPP,
  PPP_ASYNC/DEFLATE/BSDCOMP como **módulos** (nada embutido mudou). Módulos instalados no
  tablet (backup da pasta anterior: /lib/modules/7.3.0-rc7-g0fcb05b72344-dirty.antes-modem).
- Resultado: `22b8:2a70` "Motorola, Incorporated / Flash MDM6600" (mesmo ID do Droid 4),
  5 interfaces vendor → `option` → ttyUSB0..4. Só a **ttyUSB4 responde AT**: Qualcomm,
  firmware `M6600A-SCAUTSZ-1.5.6505T`, `+GCAP: +CGSM`. O ModemManager (generic, porta
  ttyUSB4) o vê como **gsm-umts**, estado failed/sim-missing (sem chip agora). Com
  `AT+CFUN=1` sem chip: "SIM failure", e CSQ/CREG/COPS dão ERROR (rádio devolvido a CFUN=0).
  ttyUSB3 ecoa lixo (tcmd binário); ttyUSB0/1/2 calados (ttyUSB2 = mux 27.010).
- Teste AT: `python3 /root/at.py /dev/ttyUSB4 ATI "AT+CPIN?"` (`kernel-hw/userspace/at.py`;
  T=segundos de espera). Não deixar o ModemManager e o at.py na mesma porta ao mesmo tempo.
- Próximos passos (com chip): ver se o MM registra pela ttyUSB4 sozinho; se os comandos
  de rede só existirem no mux, testar `ldattach GSM0710` (n_gsm) na ttyUSB2 (o Motorola
  usava um 27.010 próprio, ts27010mux); dados por PPP (ATD*99#) na ttyUSB4; medir o consumo
  do modem ligado (ele sempre ligou no boot, mesmo antes do USB3 no DTS).

## Bluetooth e sensor de luz (2026-10-18, kernel #23): FUNCIONAM

- **Sensor de luz MAX9635** (i2c-0 0x4b, IRQ PV1): `light-sensor@4b` com compatible
  `maxim,max44009` (mesmo mapa de registradores), `CONFIG_MAX44009=m` (carrega sozinho).
  Leitura: o iio:device cujo `name` = max44009 → `in_illuminance_input` (0,9–1,9 lux no
  quarto escuro). O índice do iio:device muda entre boots: procurar pelo nome. Falta ligar
  ao brilho automático do Sxmo.
- **Bluetooth BCM4329** na UARTC (`serial@70006200` = ttyTHS1, `nvidia,tegra20-hsuart`,
  nó `bluetooth` `brcm,bcm4329-bt` igual ao do Acer A500: shutdown PU0, device-wakeup
  PU1, host-wakeup PU6, 3,375 Mbaud; alimentação pelo PU4 do pwrseq do Wi-Fi). PI7
  (BT_SHUTDOWN do Android, sempre 0) = hog em nível baixo. **O serial-tegra exige o alias
  `serial1 = &uartc`** ("failed to get alias id" sem ele).
- Firmware: `bcm4329.hcd` do system do CM ("BCM4329B1 Generic FMRX 38.4 MHz"), guardado em
  `kernel-hw/firmware/BCM4329B1.hcd` (sha256 fe8c49c4…b91e) e **embutido no initramfs**
  (`initramfs/initramfs.list` → /lib/firmware/brcm/BCM4329B1.hcd): o hci_bcm o pede aos
  ~1,6 s, antes do rootfs. Cópia também em /lib/firmware/brcm/ do Alpine.
  - A p8 (system do CM) não monta direto: o ext4 diz 1 GB e a partição tem 256 MB ("bad
    geometry"). Ler com loop só leitura: `losetup -r -o $((122880*512)) /dev/loop0
    /dev/mmcblk0; mount -t ext4 -o ro,noload /dev/loop0 /mnt/p8`.
- Endereço: o bootloader o passava por ATAG (o mainline não lê). Está na partição PDS
  (mmcblk0p2, offset 0xe0000, cópia em 0x104000): `XX:XX:XX:XX:XX:XX`, um abaixo do MAC do
  Wi-Fi (0x140000). O `local-bd-address` do DT não serve (o btbcm não marca o endereço do
  BCM4329 como inválido). Serviço OpenRC `/etc/init.d/bt-addr` (before bluetooth) lê o PDS e
  faz `btmgmt public-addr`. Cópias em `alpine/config/etc/init.d/` e `kernel-hw/userspace/`.
- Alpine: `bluez bluez-btmgmt` (+ bluez-btmon instalado à mão), serviços `bt-addr` e
  `bluetooth` no runlevel default (também no montar-rootfs.sh).
- Testado: hci0 com firmware e endereço certos sozinho no boot, bluetoothd powered; o
  celular encontra o tablet ("Xoom", `bluetoothctl system-alias Xoom` +
  `discoverable on`). Um mouse BT não apareceu na busca: o BCM4329 é **BT 2.1+EDR, sem LE**,
  e o inquiry clássico roda certo (btmon: Inquiry → Complete, 0 resultados), então o
  mouse deve ser só LE. Falta parear algo (teclado/fone clássico) e o áudio A2DP/SCO.

## GPS BCM4750 (2026-10-18): FUNCIONA como serviço (xoom-gps → gpsd e GeoClue), pelo HAL do Android via libhybris (musl)

- **Resultado**: perto da janela, com `-job Periodic`, cold start sem assistência: 6 satélites
  fortes + 3 fracos e **fix 3D** (`$GPGGA … ,1,08,1.0,848.0,M`: 8 satélites, HDOP 1,0) em
  ~10 min. Os logs em /data/location/com.broadcom.gps/logs/ contêm a posição (apagar se
  quiser). O NMEA "MOT_NMEA" do formatador da Motorola sai com a latitude errada; o
  "GL_NMEA" da Broadcom está certo. A data sai em 2007 (rollover da semana GPS: +1024 semanas
  = data real); a hora do dia está certa.
- p7: `boot-mainline-boot-gps.img` (zImage #23 + DTB com UARTE e I2C sem DMA; sha256
  ffc110d5…8320; DTS = `emc/tegra20-motorola-stingray.dts.24-gps-uarte`, no 0001). Volta:
  `boot-mainline-boot-bt2.img`. Os dois reboots de hoje travaram de novo com tela escura
  (mesmo com o PG3 alto): **o hog do PG3 não resolveu todos os casos**.
- Kernel/DTS: `uarte: serial@70006400` (`nvidia,tegra20-hsuart`, alias serial2 →
  /dev/ttyTHS2). **Faltavam canais de DMA**: o APB DMA tem 16 e 15 estavam ocupados
  (SPI, 4 I2C, 2 I2S, SPDIF, UARTC); sem DMA o serial-tegra dá EIO no TCGETS ("DMA channel
  alloc failed: -19"). Tirei `dmas` dos I2C 7000c400 (DDC do HDMI) e 7000d000 (DVC), que
  passam a PIO. Ver uso: /sys/kernel/debug/dmaengine/summary.
- Hardware: BCM4750A1 ("Barracuda", TCXO 26 MHz, firmware/patch 2.17.1 do motor), UARTE
  115200 com RTS/CTS, nReset = PH0 (gpio56), nStandby = PH1 (gpio57). Protocolo fechado:
  a posição é calculada no host pelo `brcm_guci_drv` (motor GLL da Broadcom), que conversa
  pelo /data/location/GpsIpc* com o daemon `location` da Motorola; o HAL
  `gps.stingray.so` (68 KB) só fala com o `location` por socket.
- Userspace (tudo em `kernel-hw/hybris/`):
  - blobs do cm-10.2 everest (TheMuppets) em `blobs-cm102/` (`brcm_guci_drv`, `location`,
    `gps.stingray.so`, `gpsconfig.xml`, `location.cfg`, `gps.conf`). As libs da p8 estão
    corrompidas (o ext4 do CM passa dos 256 MB da partição; ler a p8 com loop só leitura
    em offset 122880*512).
  - bionic do **TWRP** (Android 4.0.4, wingray) em `bionic-ics/`: linker, libc, libm,
    liblog, libcutils, libstdc++ cobrem todos os símbolos; `libutils.so` de mentira só com
    android::elapsedRealtime() (`src/libutils-stub.c`).
  - `libgpsshim.so` (`src/gps-gpio-shim.c`, LD_PRELOAD): emula o /dev/gps_brcm4750 do
    kernel Android: RESET/STANDBY (ponteiro p/ int) → sysfs gpio56/57; START_TIMER (ms
    **por valor**: ler como ponteiro dava o SIGSEGV) / STOP_TIMER → timerfd; poll()
    consome a expiração uma vez.
  - No tablet: `/system -> /opt/android/system`, `/data -> /opt/android/data`, config
    `/system/etc/gpsconfig-xoom.xml` (= gpsconfig.xml + `acNmeaOutName`). Rodar:
    `/root/gps-rodar.sh [segundos] [job]` (cópia em `kernel-hw/userspace/` e
    alpine/config/usr/local/sbin/): links/GPIOs, sobe o `location` (sem ele o motor trava
    10 s mandando a versão e declara "ASIC is DEAD") e o motor com o job (Periodic =
    posição contínua; sem job ele para logo depois da consulta inicial).
  - **`/data/location/nmea_out.txt` é um FIFO**: precisa de um leitor (`cat` dele), senão o
    NMEA se perde e um `grep` nele bloqueia.
- **Caminho do HAL pela libhybris FUNCIONA (2026-10-18)**: `hybris-gps-test` (musl) carrega o
  `gps.stingray.so` da Motorola com `hw_get_module("gps")`, chama init/set_position_mode/start
  e recebe os callbacks: em 10 min, 329 posições (`location_cb`, flags 0x13, precisão ~28 m,
 ) e status de satélites (até 9; efemérides de vários). `used_in_fix_mask`
  vem sempre 0 neste HAL.
  - libhybris master (7079712) compilada **no tablet** só com include/common/properties/hardware
    (`./autogen.sh --prefix=/opt/hybris --enable-arch=arm
    --with-android-headers=/usr/src/hybris/android-headers-5.1
    --with-default-hybris-ld-library-path=/system/lib --enable-debug`, depois `make -C <dir>` e
    `make -C <dir> install`). Fontes em /usr/src/hybris (libhybris, Halium android-headers
    halium-5.1). Linker `jb` (o bionic é 4.0.4). Instalada em /opt/hybris (lib, linker).
  - **Port para musl**: `kernel-hw/hybris/src/libhybris-musl/libhybris-musl.patch` (+
    `musl-compat.h`): mutex recursivo sem inicializador estático; aliases *64; fpos_t
    (`__lldata`); `TEMP_FAILURE_RETRY`, wmempcpy, pvalloc, mallinfo, *_np, clockwait,
    stackaddr, scandirat; `_GNU_SOURCE` antes de tudo; strerror_r XSI; `__v*printf_chk`.
    **time_t**: o bionic de 32 bits usa time_t de 32 bits e a musl de 64 → os hooks de espera
    com timeout (mutex/cond/rwlock) convertem o timespec, e localtime/localtime_r/gmtime
    ganharam wrappers (timer_settime ficou sem conversão; já não funcionaria: timer_t difere).
  - `/system/lib/libhardware.so` de mentira (`src/libhardware-stub.c`): o hw_get_module da
    libhybris delega à libhardware do Android, que não veio no TWRP; esta faz dlopen de
    /system/lib/hw/<id>.stingray.so e devolve o HMI. `/system/build.prop` mínimo (sdk 15).
  - O `location` precisa dos sockets que o init criava (`socket gpshal_socket/location_shim/
    gps_tcmd stream` no init.stingray.rc): `android-socket-exec.py` cria em /dev/socket e passa
    ANDROID_SOCKET_<nome>. Sem eles o HAL dá init = -1 (ECONNREFUSED/ENOENT).
  - Rodar: `/root/gps-rodar.sh 600 -` (sem job: quem pede posição é o HAL) e
    `/usr/src/hybris/teste/hybris-gps-test 560` (fonte `kernel-hw/hybris/src/hybris-gps-test.c`
    + `src/ics/hardware/gps.h` do 4.0.4). Scripts também em alpine/config/usr/local/sbin/.
  - Armadilhas: `pkill -f`/`pgrep -f` com nome que aparece na própria linha do ssh mata o ssh
    (usar killall/pidof); recopiar scripts por tar tira o +x; um brcm_guci_drv antigo vivo
    impede o novo (gps_driver.pid).
### Serviço do GPS (2026-10-18): `xoom-gps` + gpsd + GeoClue, GPS liga sob demanda

- **Caminho de dados: pelo HAL**. O FIFO `acNmeaOutName` só recebe o **MOT_NMEA** (lat/lon
  com 6/7 dígitos inteiros: formato errado); o GL_NMEA certo só sai no log do motor
  (~2 MB/min, com a posição). O `location_cb` do HAL dá lat/lon certos e o **timestamp já
  em 2026** (o `location` corrige o rollover; `location.cfg` tem `abs_gps_week_at_bld_time =
  1602`). O HAL não chama `nmea_cb` e deixa `used_in_fix_mask` em 0.
- **`xoom-gps-ponte`** (`kernel-hw/hybris/src/xoom-gps-ponte.c`, compilado no tablet em
  /usr/src/hybris/ponte, instalado em /usr/local/sbin): carrega o `gps.stingray.so` pela
  libhybris e gera $GPRMC/$GPGGA/$GPGSA/$GPGSV/$GPGST/$GPZDA. Saídas: um **pty**
  (`/dev/gps-xoom` → /dev/pts/N, grupo dialout) para o gpsd e o **socket**
  `/run/xoom-gps/nmea.sock` para o GeoClue. **GPS só liga com leitor** (pty aberto do outro
  lado, detectado pelo POLLHUP do mestre, ou cliente no socket); sem leitor por 10 s →
  `gps->stop()`. Data: se o timestamp vier com ano < 2019, soma 1024 semanas. Satélite
  "usado" = com efeméride e SNR > 0. O HAL não dá DOP: HDOP = precisão/30 (o gpsd faz eph ≈
  HDOP × 67 m). Altitude do HAL é sobre o elipsoide: vai no GGA com separação 0 (altMSL do gpsd
  fica uns metros errada).
- **`/etc/init.d/xoom-gps`** (alpine/config): GPIOs 56/57 baixos, link ttyHS4 → ttyTHS2,
  sockets do init (android-socket-exec.py), `location`, motor **sem job** com
  `/system/etc/gpsconfig-servico.xml` (cópia em `kernel-hw/hybris/`: sem FIFO, **logs
  desligados**) e a ponte. Logs em /var/log/xoom-gps/. `stop` mata na ordem inversa (o
  `location` ignora SIGTERM: precisa de KILL) e deixa gpio56/57 = 0 (chip em reset).
  Com o serviço ocioso o motor deixa gpio56=1, gpio57=0 (standby); ligado, 1/1.
  Habilitado no runlevel default junto com o `gpsd` (`/etc/conf.d/gpsd`:
  `DEVICES="/dev/gps-xoom"`, sem -n: o gpsd só abre o pty com cliente e solta ~60 s depois).
  Não rodar `gps-rodar.sh` com o serviço de pé (dois motores/location brigam).
- **GeoClue**: `/etc/geoclue/conf.d/90-xoom-gps.conf` (`[network-nmea] nmea-socket=`). O
  GeoClue conecta no socket só enquanto um app pede localização e desconecta depois (o GPS
  desliga). Precisa de um agente para o usuário: o Sxmo não sobe nenhum sozinho; liga-se com
  `superctl start geoclue-agent` (ou o menu de contexto do GNOME Maps, "Toggle Geoclue").
  Com ele, `where-am-i -a 8` deu "GPS GGA+RMC", data de 2026.
- **Resultado**: depois de um reboot (que travou com tela escura de novo e precisou do Power)
  o `xoom-gps` subiu sozinho; `gpspipe -w` → TPV `mode:3`, `"time":"2026-10-19T00:50:06Z"`,
  altHAE 844 m, eph 28,5 m, fix em ~60 s (efemérides no gpsdata.nvs), 3–4 satélites usados,
  perto da janela. `rc-service xoom-gps stop` deixa nada rodando, gpio56/57 = 0, sem pty/socket.
- **Consumo** (`ds2781-battery-2/current_now`, médias de 2 min, tela apagada (bl_power 4), sem
  carregador, Wi-Fi ligado): serviço parado **209 / 211 mA**; serviço de pé, GPS ocioso
  **205 mA** (sem diferença mensurável); **GPS ligado com fix 242 mA → ≈ +33 mA** (~0,12 W);
  CPU do sistema 15–17 % nos três casos. (A medição "ocioso de novo", 223 mA, pegou 40 s com o
  GPS ainda ligado, porque o gpsd solta o pty ~60 s depois do último cliente.)
- montar-rootfs.sh: pacotes python3, gpsd, gpsd-openrc, gpsd-clients, geoclue e serviços
  xoom-gps e gpsd. O /opt/android (blobs + bionic) e o /opt/hybris continuam fora do script.

## Recuperação do i2c-0 por GPIO (2026-10-18, kernel #24): FUNCIONA

- Por que só o DTS não bastava: o i2c-tegra só registra `bus_recovery_info` nos chips com
  bus clear (T114+); no T20 `i2c_recover_bus()` devolvia -EBUSY (o `-16` do dmesg) e o
  núcleo nem olha `scl-gpios`. E a recuperação genérica do núcleo seguraria os GPIOs desde o
  probe: no Tegra um GPIO requisitado (bit CNF) tira o pino do controlador → i2c morto.
  Estado pinctrl "gpio" não serve para nada no T20 (o pinmux não decide GPIO × função).
- Patch `emc/i2c-tegra-recuperacao-gpio.patch` (drivers/i2c/busses/i2c-tegra.c): sem bus
  clear e com `scl-gpios`+`sda-gpios` no DT, o adaptador ganha um `recover_bus` próprio que
  pega os dois GPIOs (open-drain) só durante a recuperação, chama
  `i2c_generic_scl_recovery()` (até 9 clocks + STOP), solta os GPIOs, reinicia o
  controlador e devolve -EAGAIN (o núcleo repete a transferência). Dispara na perda de
  arbitragem (single master). Não roda em transferência atômica.
- DTS (`emc/…dts.25-i2c-recuperacao`): no `i2c@7000c000`,
  `scl-gpios = <&gpio TEGRA_GPIO(K, 5) (GPIO_ACTIVE_HIGH | GPIO_OPEN_DRAIN)>` e
  `sda-gpios = … TEGRA_GPIO(K, 6) …`.
- No boot: `tegra-i2c 7000c000.i2c: using GPIOs for bus recovery`. A cada recuperação:
  `recovering bus by GPIO: SCL=1 SDA=0`; falha seria `GPIO bus recovery failed`. Os GPIOs
  PK5/PK6 não aparecem em /sys/kernel/debug/gpio (só ficam presos durante a recuperação):
  o registro é a mensagem do dmesg.
- Teste provocado: `/usr/local/sbin/i2c0-travar` (cópia em alpine/config) faz pelo GPIO
  START + 0x2c (LP8550) leitura + ACK e para com o escravo pondo 0 no SDA → barramento
  travado (SDA=0, SCL=1). A próxima transferência (`i2cget -f -y 0 0x2c 0x00`) recuperou
  sozinha e leu certo, 4 vezes seguidas; touch (0x5b), backlight (brilho 60/128) e ALS
  seguem funcionando, nenhum `transfer failed`.
- O DTS com scl-gpios/sda-gpios já entrou no 0001 (regerado em 2026-10-19); o patch do
  i2c-tegra continua separado em `emc/`.
- Obs.: no travamento real do #23 vieram também -110 (timeout) entre os -16; o timeout não
  dispara recuperação, mas o -16 seguinte dispara.
- O reboot para o #24 travou com tela escura de novo (religado no Power).

## Áudio (2026-10-16): alto-falantes FUNCIONAM (44,1 e 48 kHz, PipeWire)

- Hardware (do board-stingray.c / drivers/mfd/tegra-cpcap-audio.c do kernel AOSP
  `kernel/tegra` branch android-tegra-moto-2.6.39; cópia em scratchpad):
  DAC estéreo do CPCAP no I2S1 (DAC1->DAP1, padrão do DAS), CPCAP mestre do clock,
  I2S 16 bits. Alto-falante = LINEOUT do CPCAP + amplificador externo ligado por PR3.
  Fone = HSL/HSR (detecção pelo CPCAP, já aparece como input "Headphones").
  I2S2 = codec de voz (mics) / Bluetooth, ainda não usado. PD4 = spdif_enable.
  MCLK: pino cdev1 com função osc = clk_m = 26 MHz (o Xoom tem cristal de 26 MHz).
- Mainline já tem a máquina `nvidia,tegra-audio-cpcap` (série do Svyatoslav Ryhel,
  2026, para Atrix/Droid X2). DTS: i2s@70002800 okay, `cpcap_audio: audio-codec`
  (#sound-dai-cells, irqs hs=9/mb2=10, VAUDIO-supply), nó `sound`
  ("motorola,tegra-audio-cpcap-stingray") com routing Headphones<-HSL/HSR,
  Int Spk<-LINEL/LINER e `nvidia,spkr-en-gpios = PR3`. Config: SND_SOC_TEGRA_CPCAP=y,
  SND_SOC_CPCAP=y (no stingray.config). Tudo dentro do patch 0001 regenerado.
- Bug do mainline corrigido: `tegra_machine_mclk_rate_cpcap` usava 256*fs para a
  família 48 kHz (12,288 MHz), que o CPCAP recusa ("unsupported freq") — ele só aceita
  CLK_IN de 15,36 a 38,4 MHz e gera o BCLK num PLL próprio. Agora sempre 26 MHz:
  `grate/0003-ASoC-tegra-cpcap-mclk-26mhz.patch`. (Candidato a enviar ao upstream.)
- Mixer: `Lineout Left/Right = HiFi` (alto-falante), `Headset Left/Right = HiFi`
  (fone), `HiFi` = volume (0..15). Estado salvo em /var/lib/alsa/asound.state e
  serviço `alsa` no runlevel default (também em alpine/config e montar-rootfs.sh).
- Kernel na boot: `boot-mainline-boot-audio.img` (#12; inclui o patch 0002 do gem.c);
  substituído pelo #13 (`boot-mainline-boot-mic.img`, ver Microfones).
- Script que envia, confere sha256, grava a p7, reinicia e espera: `audio/gravar-boot.sh IMG`.
- Gravar a boot pelo ssh: enviar o arquivo, conferir sha256, `dd`, conferir de novo e
  só depois `reboot` — SEM `&` no comando remoto (o `&` deixa o stdin vazio: na 1ª vez
  gravou um arquivo de 0 bytes e nada foi para a p7). Esperar o boot novo pela versão
  (`uname -v | grep "^#N "`), não pelo uptime.
- Falta: testar o fone (saída e troca automática pelo UCM); volume pelo Sxmo.

## Microfones (2026-10-16): mic interno FUNCIONA (ALSA hw:0,1 e PipeWire)

- Hardware: codec de voz do CPCAP no I2S2 (DAC2 -> DAP2), CPCAP mestre, modo
  DSP/network (4 slots) 16 bits. Mic interno = MIC1 (MICR no mainline, bias
  MB_ON1R; "handset" no Android). Mic do fone = HSMIC (também no MIC1). MIC2/MICL
  não tem nada ligado. Slot 0 = MIC2 (sempre zero), slot 1 = MIC1.
- Kernel (#13, `boot-mainline-boot-mic.img`):
  - `grate/0004-ASoC-tegra-cpcap-voice-capture.patch` (aplicar depois do 0003):
    segundo dai_link na máquina CPCAP ("CPCAP Voice", DAI `cpcap-voice`,
    DSP_A + NB_NF + CPCAP mestre, só captura), ligado à 2ª entrada de
    `nvidia,i2s-controller`; hw_params próprio que só põe o sysclk de 26 MHz (não
    mexe no pll_a, para não atrapalhar a reprodução em andamento). O DAS passa a
    ligar DAP2<->DAC2. Binding aceita 2 I2S. dtbs_check sem avisos novos.
  - `grate/0005-ARM-dts-tegra20-fix-i2s2-dma-request.patch`: **bug do mainline**: o
    tegra20.dtsi usava o request 1 do APB DMA para o I2S2 (é do I2S1); o certo é 7
    (TEGRA_DMA_REQ_SEL_I2S2_1, devices.c do Android). Sintoma: arecord dá "I/O
    error" em ~0,57 s (1,1 × buffer), DMA com residue parado e STATUS do I2S2 com
    FIFO2_ERR (overflow = os bits chegam). Candidato a upstream (junto com o 0003).
  - DTS: `i2s@70002a00` okay; no `sound`: `nvidia,i2s-controller = <&tegra_i2s1>,
    <&tegra_i2s2>` e routing `MICR <- Int Mic`, `HSMIC <- Headset Mic`.
- ALSA: `hw:0,1` só aceita 2 canais (I2S Tegra). `arecord -D plughw:0,1 -r 16000
  -f S16_LE` funciona (mono = média dos 2 slots, −6 dB). Mixer: `Right Capture
  Route = Mic 1` (ou `Headset Mic`), `Mic1 Capture Volume` 0..31 dB (uso 20).
- Testado: tom de 1 kHz no alto-falante gravado com RMS ~7700 vs ~15 em silêncio,
  frequência medida = 1000 Hz (taxa certa); gravação tocada de volta pelos
  alto-falantes. Analisador: `audio/analisar-wav.py arquivo.wav` (rms por 0,5 s).
- PipeWire: o perfil automático do ACP só testa captura no device 0, por isso não
  havia fonte. Agora há **UCM do Xoom** (em `alpine/config/usr/share/alsa/ucm2/`:
  `conf.d/tegra/Motorola Xoom (MZ600) CPCAP.conf` + `Tegra/cpcap/Motorola-Xoom-HiFi.conf`):
  dispositivos Speaker (Lineout = HiFi + Int Spk), Headphones (Headset = HiFi,
  JackControl "Headphones Jack"), Mic e Headset (SplitPCM: só o slot 1, mono).
  A PipeWire cria a fonte `alsa_input.platform-sound.HiFi__Mic__source` (padrão)
  e o sink "Built-in Audio Speaker" com volume em hardware (HiFi). Testado com
  `parecord --rate=16000 --channels=1` + `paplay`: tom gravado com RMS ~4500 vs ~90.
  Recarregar depois de mexer no UCM: `superctl restart wireplumber` (como xoom).
  Testar o UCM: `alsaucm -c hw:0 set _verb HiFi list _devices` (`-c CPCAP` não acha).
- Pendências: transiente forte no início de toda gravação (degrau até −32768 e
  decaimento de ~300 ms: bias do mic ligando junto com o stream + passa-alta; o
  Android esperava 39 ms após o bias); mic do fone e troca automática não testados
  (sem fone com mic); Bluetooth SCO pela DAP4 não feito; captura em 1 canal nativo
  no I2S (o Android usava FIFO 16_LSB) evitaria o slot vazio.

## Alpine + Sxmo

- Script reprodutível: `alpine/montar-rootfs.sh` (apk.static + fakeroot, sem root/qemu;
  verifica assinaturas), configs em `alpine/config/`. Atualizado com tudo, mas a
  reconstrução completa ainda NÃO foi testada (primeiro boot roda `apk fix --reinstall`).
- Sessão alternativa: Phosh (ver "Phosh"; `trocar-sessao phosh|sxmo`).
- Udev (eudev) no lugar de mdev; seatd; D-Bus; NetworkManager (usb0 unmanaged,
  `auth-polkit=false`, dhcpcd removido); Sxmo/sway com `WLR_RENDERER=pixman`;
  login automático do `xoom` no tty1; perfil `sxmo_deviceprofile_motorola,stingray.sh`.
- `util-linux-misc` é necessário (setsid -f para os gestos). `bonsaid` não existe em armv7.
- Tablet tem internet pelo Wi-Fi: `apk add` funciona direto. Sistema atualizado.
- llvmpipe do Mesa do sistema dá "Illegal instruction" (sem NEON): sem grate não há GL.

## Aceleração 3D (grate) — EM ANDAMENTO

- Fontes no tablet: `/usr/src/grate/libdrm` (branch grate-2.4.109) e
  `/usr/src/grate/mesa` (branch 22.2.4); instalados em `/opt/grate` (Mesa do sistema
  intocado). Patches em `grate/`: `libdrm-grate-2.4.109.patch` (#ifdef→#if VALGRIND),
  `mesa-grate-22.2.4.patch` (distutils→packaging; correção do RT_PTR),
  `corrigir-rt-ptr.py`.
- O kernel mainline tem a UAPI staging que o grate usa (estruturas idênticas).
- Bug corrigido no driver: emit_render_targets relocava o RT 0 (profundidade) com BO
  nulo → EINVAL; e o firewall do host1x proíbe escrever RT_PTR sem relocação. Agora só
  escreve RT_PTR dos RTs com BO.
- Rodar o teste (troca para o tty2 e volta):
  ```
  chvt 2; LD_LIBRARY_PATH=/opt/grate/lib LIBGL_DRIVERS_PATH=/opt/grate/lib/dri \
    GBM_BACKENDS_PATH=/opt/grate/lib/gbm kmscube; chvt 1
  ```
- ESTADO ATUAL (2026-10-16): **kmscube a 65 fps** (limitado pelo vsync), modo legacy.
  - O "travamento" era falso: o kmscube legacy sai ao ver o stdin legível
    ("user interrupted!"), e pelo ssh o stdin está em EOF. Rodar com
    `tail -f /dev/null | kmscube -c 300`.
  - Tela preta ao voltar para o tty1 = Sxmo em screenoff (swayidle disparou durante o
    teste no tty2; `swaymsg -t get_outputs` mostra power=false). Apertar Power.
    `fb_set_par error -16` a cada troca de VT: fbcon, inofensivo.
  - `kmscube -A` falha: "no eglDupNativeFenceFDANDROID" (grate sem
    EGL_ANDROID_native_fence_sync).
- CORRIGIDO: era 12,5 fps porque cada TEGRA_SUBMIT levava ~11 ms no kernel. Medido com
  tracepoints (raw_syscalls id==54 + dma:dma_map_sg; não precisa de ftrace de função):
  ~8,6 ms no dma_map_sg do RT de 4 MB e ~2,1 ms no BO de 1 MB (manutenção de cache,
  ~2,1 ms/MB). Patch `grate/0002-drm-tegra-skip-cpu-sync-wc-bo.patch`:
  DMA_ATTR_SKIP_CPU_SYNC no tegra_bo_pin/unpin para BOs de dma_alloc_wc (sem pages).
  SUBMIT agora 0,08 ms (mediana). Traces em `grate/trace-submit*.txt`.
- Ainda há 7 SUBMIT + SYNCPT_WAIT por quadro (um por draw); juntar no Mesa ajudaria
  cenas maiores. Gravar a boot pelo próprio tablet funciona:
  `dd of=/dev/mmcblk0p7 bs=1M conv=fsync` + reboot (conferir sha256 antes/depois).
  Na 1ª tentativa o tablet não voltou sozinho após o reboot (sem log; foi desligado
  e religado e subiu normal). Ficar de olho em reboots.
- **SXMO/SWAY COM GLES2 NO TEGRA FUNCIONA (2026-10-16, caminho B)** — ver bloco
  "CAMINHO B" abaixo. Histórico do bloqueio (resolvido):
- SWAY COM GLES2 (2026-10-16): bloqueado: o grate 22.2.4 não implementa texturas
  (`set_sampler_views` = unimplemented, sem `create_sampler_view`, FP sem TEX; só os
  registradores em tgr_3d.xml.h). A sway cai com SIGSEGV (pc=0) em
  `st_get_texture_sampler_view_from_stobj` ao desenhar o 1º cliente (log em
  `grate/sway-gles2-gdb.log`). Obstáculos já resolvidos no caminho:
  - libdrm do grate (2.4.109) não tem símbolos que o wlroots 0.20 usa → 
    `/opt/grate/lib-sway` = links do grate SEM libdrm.so* (usa a 2.4.134 do sistema;
    conferido que o Mesa do grate não precisa de nada além dela).
  - `/usr/bin/sway` tem `cap_sys_nice=ep` → o musl IGNORA LD_LIBRARY_PATH (por isso o
    erro "DRI2: failed to create screen" vinha do Mesa 26 do sistema procurando nouveau).
    Wrapper `/opt/grate/bin/sway` chama `/lib/ld-musl-armhf.so.1 --library-path ...`.
  - O wlroots exige render node (renderD128) e dma-buf. O Mesa do grate EMBUTE sua
    própria cópia da libdrm_tegra (`drivers/grate/drm/tegra.c`, estática). Patch
    `grate/mesa-grate-dmabuf.patch`: WINSYS_HANDLE_TYPE_FD em get/from_handle, e
    from_dmabuf usava lseek SEEK_CUR (dma-buf só aceita END/SET → EINVAL).
    Na libdrm do grate em /usr/src também exportei to/from_dmabuf (inofensivo, não usado).
  - Backup das libs antes disso: `/opt/grate/lib.antes-dmabuf`.
  - Com isso a sway headless sobe com "GL renderer: Tegra" e sem erros (sem clientes).
- Ligar o teste de novo: `touch ~/.config/sxmo-gles2` (e `~/.config/sxmo-gles2-debug`
  para log -d em ~/.cache/sway-gles2-debug.log). O `.profile` volta sozinho para pixman
  se a sway GLES2 morrer em < 20 s (grava ~/.cache/sxmo-gles2-falhou).
  **Hoje: LIGADO** (`~/.config/sxmo-gles2` existe). Desligar: apagar esse arquivo.
- TEXTURAS NO GRATE (pesquisa 2026-10-16): **nenhuma branch nem PR do grate-driver/mesa
  tem texturas** (19.2…22.2.4, grate, master; grep create_sampler_view/TEX). O driver
  Mesa é um esqueleto: compilador FP só faz MOV (`fp/tgsi.c`; "TODO: TEX" no fpir.h);
  VP faz MOV ADD MUL DP3 DP4 SLT MAX MAD RSQ; unimplemented(): set_sampler_views,
  bind_blend_state, scissor, fence_finish, flush, etc.
  - O Tegra 2 NÃO tem unidade de blend: o blend é feito no FP (PSEQ lê o pixel de
    destino p/ registradores, ALU faz MAD, DW grava). Scissor existe (0x350/0x351).
  - Referências que FUNCIONAM com texturas: `grate-driver/grate` (libgrate:
    grate-3d.c TEXTURE_POINTER/DESC1/DESC2, assembler fragment_asm.y com TEX, testes
    cube-textured/texture-filter) e `grate-driver/xf86-video-opentegra` (EXA composite
    com gr3d; shaders asm por operação Porter-Duff, ex. shaders/blend_over/*/fragment.asm).
  - Caminhos: (A) compilador FP de verdade no Mesa (TEX, ALU, escalonamento, blend
    no shader) = semanas/meses; (B) no driver grate, reconhecer os poucos shaders fixos
    do wlroots (quad, tex_rgba, tex_rgbx) + blend premultiplicado e trocar por asm
    escrito à mão (montado com o libgrate, partindo do blend_over do opentegra) +
    sampler views/states + scissor + uniform = dias/poucas semanas, frágil por versão
    do wlroots; (C) Sxmo com dwm (X11) + xf86-video-opentegra (EXA acelerado já
    existe; compilar contra o xorg-server do Alpine); (D) só conferir se o pixman do
    Alpine usa o caminho arm-simd (ARMv6, sem NEON).
- (D) pixman: o arm-simd JÁ está ativo (OVER 1280x800: 20 ms; sem arm-simd 45 ms).
- CAMINHO B (feito): patch completo do Mesa em `grate/mesa-grate-wlroots.patch`
  (git diff de /usr/src/grate/mesa: inclui os patches anteriores de RT_PTR e dma-buf).
  - Shaders asm: `grate/wlrshaders/*.asm` (quad, tex_rgba, tex_rgbx, com e sem blend),
    montados com o `gen_shader_bin` do xf86-video-opentegra (compilar no PC: flex/bison
    dos .l/.y de src/gpu/gr3d-asm + gcc exa/gen_shader_bin.c) e convertidos por
    `grate/wlrshaders/gerar-header.py` em `grate_wlr_shaders.h` (vai para
    src/gallium/drivers/grate/).
  - Driver: reconhece o TGSI exato dos FS do wlroots 0.20.2 (tgsi_dump_str sem espaços)
    e troca pelo blob; escolhe a variante com blend conforme o blend state; uniforms do
    FP em fx10 (cor (b,g)/(r,a); alpha); sampler views/states; TEXTURE_DESC1/2/POINTER.
  - 4 bugs do grate achados e corrigidos no caminho:
    1. **Imediatos do VS nunca eram enviados** (vp/tgsi.c usava uniform 1023-i sem
       upload): todo VS com constante literal (o do wlroots usa 1.0 em w) não desenhava
       nada. Agora ficam em 255-i e vão no blob do VS. (O kmscube escapava por não ter.)
    2. Pitch das texturas: o amostrador não tem registrador de pitch; precisa 16 bytes
       (POT) ou 64 (NPOT). O grate alinhava a 32.
    3. **FDC_CONTROL sem INVALIDATE** (0xe00 → 0xe01, como opentegra/libgrate): sem isso a
       leitura do destino no blend às vezes vinha de um job anterior (3/10 rodadas).
    4. O compilador FP só faz MOV e o shader `quad` (sem entradas) corrompia memória.
    5. **Imagem de cabeça para baixo na tela** (o grim mostrava certo): o grate criava
       todo BO de RT/scanout com DRM_TEGRA_GEM_CREATE_BOTTOM_UP, e o tegra-drm mainline
       transforma isso em DRM_MODE_REFLECT_Y no scanout (dc.c, tegra_plane_atomic_check).
       Flag removida; confirmado na tela em 2026-10-16.
  - Vista 1 vez (antes da correção 5): a sway GLES2 caiu num `swaymsg output power on`
    depois do screenoff. Não reproduziu depois (5 ciclos off/on + acordar pelo Power sob
    gdb). Se voltar: `ln -sf sway-gdb /opt/grate/bin/sway`, reiniciar a sessão, e o
    backtrace fica em ~/.cache/sway-gles2-gdb.log (voltar com `ln -sf sway.normal ...`).
    Era o bug do `lookup_bo` (reimport de dma-buf) — corrigido, ver "CORRIGIDO" acima.
  - Teste: `grate/wlrtest/wlrtest.c` (no tablet em /root/wlrtest): mesmos shaders/estado
    do wlroots, RT = BO GBM via EGLImage, confere pixels por mmap do dma-buf. 20/20 OK.
    `GRATE_DEBUG=tgsi` mostra o TGSI e qual blob foi usado; `GRATE_DUMP_STREAM=1` imprime
    o command stream (decodificar com `grate/wlrtest/decodificar-stream.py`).
  - Captura de tela pelo grim (saída real do GR3D): `grate/tela-gles2.png`.
  - Sessão: wrapper `/opt/grate/bin/sway` -> `sway.normal` (sempre exec). O .profile NÃO exporta mais
    LD_LIBRARY_PATH/LIBGL_DRIVERS_PATH (não vaza para os apps). Reiniciar a sessão: kill
    no PID de `pgrep -f '^/lib/ld-musl-armhf.so.1 --library-path /opt/grate/lib-sway'`
    (`pkill -x sway` não acha; `pkill -f /usr/bin/sway` mata o próprio ssh).
  - Limites: só os shaders do wlroots 0.20.2 são acelerados (outra versão do wlroots =
    TGSI diferente → cai no compilador MOV); só blend GL_ONE/ONE_MINUS_SRC_ALPHA;
    tex_external sem teste; texturas R8G8B8A8 (shm ABGR) não mapeadas (só B8G8R8A8/X8);
    apps GL do Mesa do sistema usam llvmpipe (com o shim d16).
- **Mais do driver (2026-10-16/17)**, também nos commits do fork do Mesa:
  - **VP com DIV e RCP**: o VP não tem divisão; DIV vira um RCP escalar por componente
    distinta do divisor num temporário (r31) e um MUL.
  - **Scissor implementado** (era unimplemented). Mesmas coordenadas das linhas do RT, MAX
    exclusivo.
  - **Índices**: o GR3D não tem índices de 32 bits e INDEX_COUNT tem 12 bits (o assert
    antigo de < 2048 sumia no release e truncava). Agora as listas de triângulos vão em
    blocos de 4095, cada bloco convertido para u16 a partir do menor vértice (ATTRIB_PTR
    deslocado). Os índices são lidos de uma cópia na CPU (`shadow` dos index buffers,
    preenchida em buffer_subdata): ler o BO write-combined custava caro.
  - **Formatos de textura**: is_format_supported recusa SAMPLER_VIEW fora de
    grate_pixel_format → o Mesa converte RGBA8 para BGRA8 no upload e não expõe sRGB.
    Antes RGBA8 virava formato -1.
  - **lookup_bo**: BOs importados (dma-buf, flink) nasciam com as listas não
    inicializadas; reimportar o mesmo dma-buf (o wlroots faz ao religar a saída) gravava
    em 0x4 e derrubava a sway. Ver "Botão Power" e o commit no fork.
  - **Draws em lote**: o job do GR3D fica aberto entre draws (`grate_init_state` só no
    início do job; cada draw reemite o próprio estado). Flush (submit + espera) em
    pipe->flush (era unimplemented; flush síncrono, sem fence), antes de fill/clear/blit
    no 2D, em transfer_map (não UNSYNCHRONIZED) de recurso usado pelo job pendente, em
    flush_resource, no destroy do contexto e com 1024 draws ou 4096 relocs no job.
    - **O pushbuf não segurava referência dos BOs relocados** (só dos BOs de comando):
      agora o grate_stream guarda um set dos BOs do job e solta depois da espera. Sem
      isso um VBO liberado voltava ao cache e era reusado com o job apontando para ele.
    - glBufferData do mesmo tamanho (DISCARD_WHOLE_RESOURCE) num buffer em uso pelo job:
      o recurso ganha armazenamento novo em vez de dar flush.
    - **Subalocação**: buffers ≤ 64 KB saem de arenas de 1 MB. Sem isso, depois de ~3 s
      parado o cache de BOs descartava os buffers pequenos e o quadro seguinte pagava
      dezenas de GEM_CREATE (alocação CMA). Uso pela GPU rastreado por recurso
      (`resource->batch`), não por BO.
    - libdrm embutida: `drm_tegra_job_add_reloc` crescia o vetor de relocs de 1 em 1.
    - Variáveis: `GRATE_BATCH=1` = um submit por draw, como antes; `GRATE_BATCH_REINIT=1`
      = grate_init_state em todo draw; `GRATE_BATCH_LOG=1` imprime por job: tempo
      montando, draws, relocs, BOs, submit e espera.
    - Limitação: renderizar numa textura e amostrá-la no MESMO job não invalida o cache
      de textura entre os draws (usar GRATE_BATCH_REINIT=1).
  - **Timeout de 10 s (2026-10-17)**: `args.timeout = 1000` → `10000` no SUBMIT
    (drivers/grate/drm/uapi_v1/job.c) e na espera da fence (grate_stream.c). Com o EMC a
    50 MHz um job passou de 1 s, o host1x completou o syncpoint pela CPU e a GPU
    incrementou de novo → syncpoints dessincronizados até o reboot (ver "DVFS da RAM").
- PRÓXIMOS PASSOS: medir fps/latência do Sxmo GLES2 vs pixman; testar clientes dma-buf
  (tex_external) e shm ABGR; levar o driver em lote para a sway (/opt/grate/lib/dri)
  depois de testar; reinstalar wlroots exato
  (fixar versão 0.20.2 no apk ou tolerar variações de TGSI).
- Para compilar o Mesa no tablet: `cd /usr/src/grate/mesa && ninja -C build -j2 &&
  ninja -C build install` (completo ~1 h; incremental poucos minutos).

## Botão Power não reacendia a tela (2026-10-16) — CORRIGIDO
- Sintoma: Power apagava a tela, mas não acendia mais. O evento chegava, a sway
  executava o bind e o sxmo.state ia para unlock, mas a LVDS-1 ficava com `power: false`
  e bl_power=4. No log da sway: `[ERROR] Backend commit failed`, sem erro do DRM. Era sempre o
  1º `output power on` depois de um `power off`; um 2º `power on` funcionava.
- Causa (wlroots 0.20.2, não o Mesa do grate): ao desligar a saída, wlr_scene marca
  `gamma_lut_changed` ("reaplicar gamma ao religar"). Ao religar,
  `scene_output_state_attempt_gamma()` põe COLOR_TRANSFORM=NULL (resetar a gamma) na
  commit. O teste passa, porque `wlr_output_test_state` tira campos "inalterados", mas
  a commit real chama `drm_legacy_crtc_set_gamma(size 0)`. O CRTC da Tegra não tem
  GAMMA_LUT nem gamma legada (tamanho 0), então a função retorna false SEM log e a
  ioctl ATOMIC real nem é enviada (confirmado com ftrace raw_syscalls: 2 ATOMIC
  TEST_ONLY, CREATEPROPBLOB, e nada mais). A 2ª tentativa passa porque o flag já foi limpo.
  Não está corrigido no wlroots master. Com pixman deve acontecer o mesmo (é
  independente do renderer); a sway pixman usa a lib de /usr/lib, sem a correção.
- Correção: patch de 4 bytes numa CÓPIA da lib do Alpine (0.20.2-r0, sha256 cae415…)
  instalada em `/opt/grate/lib-sway/libwlroots-0.20.so` (só a sway GLES2 carrega, via
  --library-path do wrapper). Em 0x4597a: `mov r4,r0; cbz r0,→return false` virou
  `movs r4,r0; beq →0x45a40` (`movs r0,#1`), ou seja, resetar gamma num CRTC sem gamma
  conta como sucesso. Arquivos: o fork do wlroots (patch-wlroots-gamma.py confere o
  sha256 e os bytes; wlroots-0.20.2-gamma-reset.patch = mesma mudança no fonte;
  libwlroots-0.20.so.gamma = binário). Se o apk atualizar o wlroots, refazer o patch
  (o script recusa uma lib diferente) ou remover a cópia de lib-sway.
- Testado: 3 ciclos `swaymsg output LVDS-1 power off/on` + 4 ciclos pelo botão
  (screenoff → lock/unlock), todos com "Commit of 1 outputs succeeded" e bl_power 4→0.
- Gestos "pararam" logo depois (13:40): não era defeito. (1) A partir de screenoff, um
  toque no Power leva a `lock` (tela acesa, mas o Sxmo ignora gestos; uns 8 s depois o
  idle volta para screenoff). Para chegar a `unlock` é preciso um 2º toque (o ciclo do
  `click` é screenoff → lock → unlock → screenoff). (2) Havia um 2º lisgd órfão, de uma
  sway que caiu às 04:34 (SWAYSOCK morto, ppid 1): cada gesto disparava o
  inputhandler 2 vezes, e ações de alternar (menu, teclado) se desfaziam. Matei o órfão.
  Quando a sway cair ou reiniciar, conferir: `ps | grep "lisgd -d"` deve mostrar só 1
  (o de SWAYSOCK atual em /proc/PID/environ). Teste: gesto em unlock abre o bemenu.
- Diagnóstico útil: `echo 0x16 > /sys/module/drm/parameters/debug` (atomic no dmesg);
  a sway roda sob gdb, então não dá para usar strace, mas o ftrace com
  `events/raw_syscalls` filtrado por `common_pid` e `id == 54` (ioctl) funciona.

## Phosh (2026-10-19): FUNCIONA pelos pacotes do Alpine, como sessão alternativa ao Sxmo

- Pacotes: `apk add phosh squeekboard phosh-mobile-settings polkit-elogind` (180 pacotes,
  ~1,3 GB no total do sistema). O phosh exige `polkit-elogind`, que conflita com o `polkit` +
  `polkit-noelogind-libs` fixados no world: tirei os dois do world (backup
  `/root/world.antes-phosh`); o Sxmo aceita o polkit-elogind. Nada foi atualizado.
  Versões: phosh 0.55.0, **phoc 0.55.1 com wlroots 0.19 embutido** (estático, não usa o
  wlroots0.20 do sistema nem a cópia com o patch da gamma), gnome-session 48 (sobe sem
  systemd: "Falling back to non-systemd startup"), GTK4 4.22.4, libadwaita 1.9.2,
  squeekboard 1.43.1. **O elogind NÃO foi instalado** (só a libelogind): o elogind
  apagaria o tablet no Power (HandlePowerKey=poweroff) também no Sxmo, e o login do tty1
  é o do busybox (sem PAM, não registraria sessão).
- Renderização (1ª versão; hoje o phoc vai pela GPU, ver abaixo): `WLR_RENDERER=pixman` no phoc, `GSK_RENDERER=cairo GDK_DISABLE=gl,vulkan` no GTK4 (o llvmpipe do
  sistema dá SIGILL sem o shim d16). O phosh e o squeekboard são GTK3 (cairo).
  `/etc/phosh/phoc.ini` (cópia em alpine/config): `xwayland=false`, LVDS-1 escala 1.
- **Testado no aparelho**: Power apaga e acende (o phoc não tem o bug da gamma do
  wlroots 0.20.2: só avisa "Failed to set gamma for LVDS-1"), desbloqueio com PIN, apps
  abrem (Foot, Mobile Settings), squeekboard aparece sozinho no Foot. **No NetSurf o
  teclado não aparece** (os campos da página não usam o IM do GTK; abrir o teclado pela
  barra de baixo do Phosh).
- PIN: o xoom tinha senha travada (`!`) e a tela de bloqueio do Phosh autentica pelo PAM
  (serviço "phosh" → /usr/lib/pam.d/other → pam_unix). **Defini uma senha para o xoom** (trocar com
  `passwd xoom`; backup do shadow em /root/shadow.antes-phosh). Não muda o login automático
  nem o ssh (só chave). O `doas` (permit persist :wheel) passa a aceitar essa senha.
- Consumo: sessão ociosa ~99% idle; ~145–160 MB "used" e ~760–800 MB disponíveis. PSS:
  phosh 46 MB, phoc 24, wireplumber 20, goa-daemon 14, evolution-* ~27, squeekboard 9.
  O libinput avisa "event processing lagging behind by 80–156 ms" no toque às vezes.
- Sem logind os avisos esperados: "Failed to inhibit power button/suspend" (o Power
  funciona assim mesmo), agente polkit sem sessão ("No session for pid": pedidos de senha
  do polkit não aparecem), gsd-rfkill sem /dev/rfkill, sem papel de parede (falta
  /usr/share/backgrounds/gnome/blobs-d.svg; fundo preto).
- **Alternar** (`/usr/local/bin/trocar-sessao phosh|sxmo`, cópia em alpine/config): grava ou
  apaga `~/.config/sessao-phosh` e mata o phoc/a sway; o login automático do tty1 relê o
  `~/.profile` e sobe a outra sessão.
  - No Phosh: app **"Voltar ao Sxmo"** (`~/.local/share/applications/voltar-sxmo.desktop`).
  - No Sxmo: item **"Trocar para o Phosh"** no menu de apps (hook sxmo_hook_apps.sh).
  - Pelo ssh: `su xoom -s /bin/sh -c "trocar-sessao sxmo"` (ou só `rm
    /home/xoom/.config/sessao-phosh` e matar o phoc).
  - **Volta automática**: se o `phosh-session` terminar em menos de 60 s, o `.profile`
    copia `~/.phosh.log` para `~/.cache/phosh-falhou` e sobe o Sxmo na mesma hora; enquanto
    esse arquivo existir, o Phosh não é tentado (o `trocar-sessao phosh` o apaga). Testado
    sem querer na 1ª tentativa (faltava o XDG_RUNTIME_DIR: o phoc não acha o /run/user/1000
    sozinho como o Sxmo; agora o .profile exporta).
  - **Ida e volta testadas (2026-10-19)**: `trocar-sessao sxmo` → Sxmo GLES2 em ~40 s (um
    só `lisgd -d`, nenhum processo do Phosh sobrando); `trocar-sessao phosh` → Phosh na tela
    de bloqueio, sem sway/lisgd/swayidle órfãos. O atalho e o item do menu chamam
    `/usr/local/bin/trocar-sessao` pelo caminho absoluto (o `su xoom` sem -l não tem
    /usr/local/bin no PATH; a sessão do Phosh tem).
  - Log da sessão: `~/.phosh.log`. Backup do .profile anterior: `~/.profile.antes-phosh`.
- **phoc NA GPU (grate) FUNCIONA (2026-10-19)**: o wlroots 0.19 embutido no phoc gera
  exatamente o mesmo TGSI do 0.20.2 (quad, tex_rgba, tex_rgbx; o tex_external cai em
  tex_rgba), então o driver do grate (`/opt/grate/lib/dri`, o mesmo da sway) reconhece tudo
  sem mudança nenhuma (`GRATE_DEBUG=tgsi`: "wlroots shader -> quad / tex_rgba / tex_rgbx").
  - Teste headless: phoc com foot, grim em gles2 × pixman: **0 pixels diferentes**
    (scripts no tablet: /tmp/phoc-cmp.sh e /tmp/phoc-cliente.sh; não guardados).
  - Lançador `/usr/local/bin/phosh-sessao gles2|pixman` (cópia em alpine/config): faz o que o
    /usr/bin/phosh-session faz (dbus-run-session, `phoc -v -S -C /etc/phosh/phoc.ini -E
    "gnome-session --session=phosh"`), com o phoc chamado pelo loader do musl com
    `--library-path /opt/grate/lib-sway` no modo gles2. Só o phoc recebe o Mesa do grate; os
    apps continuam com cairo. Sai com 1 se a sessão durou < 60 s.
  - Liga com `~/.config/phosh-gles2` (**LIGADO**). O .profile tenta gles2; se cair em < 60 s
    grava `~/.cache/phosh-gles2-falhou` e sobe na hora com pixman; se esse cair também, grava
    `~/.cache/phosh-falhou` e vai para o Sxmo. `trocar-sessao phosh` apaga os dois.
    Desligar a GPU: `rm ~/.config/phosh-gles2` e reiniciar a sessão.
  - **Testado no aparelho**: imagem certa, desbloqueio, app, squeekboard, Power apaga e
    acende (sem "commit failed": o caminho da gamma do 0.19 não trava), e "ficou mais rápido".
    Memória: phoc PSS 24 → 32 MB; ~750 MB disponíveis. O libinput ainda avisa de 20–107 ms de
    atraso no toque às vezes (os clientes continuam desenhando na CPU).
- **Bluetooth no Phosh (2026-10-19)**: o Phosh não mostrava o Bluetooth porque o
  gsd-rfkill não abria o `/dev/rfkill` (root:root 664; a regra
  61-gnome-settings-daemon-rfkill.rules usa `uaccess`, que precisa do logind). Regra nova
  `/etc/udev/rules.d/70-rfkill-netdev.rules` (cópia em alpine/config): GROUP="netdev",
  MODE="0664" (o xoom está no netdev). Aplicada com `udevadm trigger` + kill do gsd-rfkill
  (o gnome-session o reinicia: X-GNOME-AutoRestart). Conferido no aparelho: o botão
  aparece e liga/desliga. Áudio por Bluetooth ainda não: falta o plugin bluez da PipeWire
  (pacote `pipewire-spa-bluez`).
- **Animações desligadas** (2026-10-19): `gsettings set org.gnome.desktop.interface
  enable-animations false` (como xoom, com o DBUS_SESSION_BUS_ADDRESS da sessão do phosh,
  tirado de /proc/$(pidof phosh)/environ); fica no dconf do xoom. O phoc escuta a chave ao
  vivo (`changed::enable-animations`); GTK3/GTK4/libadwaita seguem pelo
  gtk-enable-animations. Religar: mesmo comando com `true`. Os apps continuam em cairo
  (CPU); o phoc já compõe pela GPU (bloco acima).
- Teste sem mexer na tela (headless, outro XDG_RUNTIME_DIR): `WLR_BACKENDS=headless
  WLR_RENDERER=pixman XDG_RUNTIME_DIR=/tmp/phosh-teste … timeout 90 phosh-session` como xoom.
- Pendências: tirar do autostart do Phosh o que não se usa (evolution-alarm-notify,
  vvmd, mmsd, goa) com `Hidden=true` em ~/.config/autostart; papel de parede
  (phosh-wallpapers); sensor de luz/rotação (iio-sensor-proxy); suspender (sem logind o
  gsd-power não suspende).

## PENDÊNCIAS (consolidado em 2026-10-17)

**Em andamento: DVFS da RAM** (ver "DVFS da RAM / EMC")
- vdd_core: piso de 1,1 V com o display ligado (host1x a 150 MHz); conferir o core com a
  tela apagada (dc e host1x suspensos → 1,0 V?).
- memtester completo (uma passada de 300 MB leva > 20 min: deixar uma noite).

**Kernel e hardware**
- Resolvidos no #18 (ver "Hardware restante"): oops do powergate, WARN do pmc.c:4999,
  reboot-bootloader, áudio HDMI, suspend LP1; PWRREQ_OE não é necessário (só LP0, que o
  mainline não tem).
- ~~Reboot travado com tela escura~~: **resolvido no #26** (pulso do PG3 antes do reset; ver
  "Reboot travado sem carregador"). Constava aqui por engano como resolvido no #18 (hog do
  PG3). Falta: conferir o reboot-bootloader no #26 (o pulso também roda nele); se quiser
  isolar, testar o pulso sem o bit SOFT_RESET.
- ~~i2c-0 travado por escravo segurando o SDA~~: **resolvido no #24** (recuperação por
  GPIO, ver "Recuperação do i2c-0"). Histórico:
  **i2c-0 travou (2x) (2026-10-19, kernel #23, ~35 min após o boot, ao apagar a tela)**:
  um escravo ficou segurando o SDA (PK6 em 0, PK5/SCL em 1); toda transferência perdia
  arbitragem → dmesg inundado de `atmel_mxt_ts 0-005b: … i2c transfer failed (-16)`, touch
  morto e **backlight que não apaga** (o lp855x ignora `bl_power`; quem apaga é o painel no
  DPMS off, escrevendo brilho 0 pelo I2C, e essa escrita falhou). O T20 não tem bus clear e
  o DT não tem recuperação por GPIO, então o kernel desiste (-EBUSY). Destravado à mão com
  `/usr/local/sbin/i2c0-destravar` (alpine/config): 18 clocks no SCL pelo GPIO + STOP;
  o escravo dava ACK a cada 9 clocks (estava recebendo). Causa e escravo não identificados.
  Corrigido com patch no i2c-tegra + `scl-gpios`/`sda-gpios` no DTS (o estado pinctrl
  "gpio" não se aplica ao T20). Falta: achar o escravo/causa; regerar o 0001 com o patch.
- Vídeo HDMI: testar com cabo micro-HDMI e monitor (EDID, modo, áudio pela placa 1).
- Bluetooth (funciona, ver "Bluetooth e sensor de luz"): parear um aparelho clássico
  (BR/EDR; o chip não tem LE), testar A2DP pela PipeWire e o SCO pela DAP4.
- Sensor de luz (funciona): ligar ao brilho automático do Sxmo.
- Suspend: medir o consumo com mais precisão (suspensão longa) e ligar o autosuspend do
  Sxmo; conferir que o Wi-Fi e o carregador acordam o tablet como esperado.
- Câmeras (só levantamento): traseira OV5650 5 MP Bayer RAW (0x36) + foco DW9714L
  (0x0c) + flash LM3559 (0x53); frontal Aptina SOC2030 2 MP YUV (0x3c); CSI do Tegra 20
  (staging tegra-video tem CSI/Bayer, nenhuma placa T20 usa no DT). Faltam drivers
  mainline de OV5650, SOC2030 e LM3559 (DW9714 existe). Estimativa: semanas (dois
  drivers de sensor portados do Android, DT do VI/CSI nunca testado no T20 e, para a
  traseira, debayer/ISP em software no userspace).
- Modem 3G UMTS (MZ605): enumera e responde AT (ver "Modem 3G"). Falta: testar com chip
  (registro, sinal, SMS), dados (PPP na ttyUSB4 ou pelo ModemManager), o mux 27.010 da
  ttyUSB2 (canal de comandos do RIL da Motorola) e o consumo do modem.

**Áudio**
- Testar o fone (saída e troca automática pelo UCM) e o volume pelo Sxmo.
- Mic: transiente de ~300 ms no início das gravações; mic do fone sem teste; Bluetooth
  SCO (DAP4); captura em 1 canal nativo.

**GPU (grate) e sway**
- Levar o driver com draws em lote para a sway (/opt/grate/lib/dri).
- Medir a interface GLES2 contra pixman; testar tex_external (dma-buf) e shm ABGR.
- **Fixar o wlroots 0.20.2**: os shaders reconhecidos e o patch binário da gamma
  (correção do Power) dependem dessa versão; um `apk upgrade` quebra os dois.
- A sway roda sob o gdb (`/opt/grate/bin/sway -> sway-gdb`); voltar para `sway.normal`
  depois de uns dias sem queda.
- Limitação: renderizar numa textura e amostrá-la no mesmo job (GRATE_BATCH_REINIT=1).

**Sistema e apps**
- Reconstrução completa pelo `alpine/montar-rootfs.sh` nunca testada.
- Se a sway cair/reiniciar: conferir que não ficou `lisgd` órfão (gestos duplicados).

**Candidatos a upstream**
- Kernel: `grate/0011` (pulso do SYS_RESTART_B + SOFT_RESET no cpcap-reboot-mode, junto com o
  0009), `grate/0008` (early_pmc e debugfs do powergate no pmc.c), `grate/0009`
  (cpcap-reboot-mode, também serve para os mapphone/Droid 4), `grate/0007` (banda do display com a tela apagada), `grate/0003` (MCLK do CPCAP), `grate/0005` (DMA do I2S2), `grate/0006`
  (DT do MAX8649), talvez `grate/0002` (cache no tegra_bo_pin).
- wlroots: reset de gamma num CRTC sem gamma (o fork do wlroots).
- Mesa: `-d32` no llvmpipe para CPUs vfpv3d16 (`llvmpipe-d16/`).

## Diagnóstico e logs úteis
- `resultado-*/`: diagnósticos de cada boot; `teste-*.log`: gravações e boots.
- `initramfs/`: /init, xoom-check, busybox, `montar-extras.sh`.

