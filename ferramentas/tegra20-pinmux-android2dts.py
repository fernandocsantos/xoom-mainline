#!/usr/bin/env python3
"""
Converte uma tabela de pinmux de placa Tegra 2 (kernel Android 2.6.3x,
board-*-pinmux.c) em nós pinctrl de device tree para o kernel mainline.

Lê as tabelas tegra_pingroup_config e tegra_drive_pingroup_config do
arquivo da placa e valida cada função contra o driver pinctrl-tegra20.c
do mainline. TEGRA_MUX_SAFE é trocado pela func_safe de cada grupo,
definida em pinmux-t2-tables.c do mesmo kernel Android.

Os grupos da memória DDR (xm2*, memcomp) são ignorados de propósito:
o bootloader já os configura junto com a EMC.

Exemplos:
  # baixa as tabelas de referência automaticamente
  ./tegra20-pinmux-android2dts.py board-stingray-pinmux.c > pinmux.dtsi

  # nó pinmux@70000014 completo, pronto para colar no DTS
  ./tegra20-pinmux-android2dts.py --full board-olympus-pinmux.c

  # tudo local, sem rede
  ./tegra20-pinmux-android2dts.py --tables pinmux-t2-tables.c \\
      --pinctrl linux/drivers/pinctrl/tegra/pinctrl-tegra20.c board-x-pinmux.c
"""
import argparse
import base64
import re
import sys
import urllib.request
from collections import OrderedDict

ANDROID_TABLES_URL = (
    "https://android.googlesource.com/kernel/tegra/+/refs/heads/{branch}/"
    "arch/arm/mach-tegra/pinmux-t2-tables.c?format=TEXT"
)
PINCTRL_URL = (
    "https://raw.githubusercontent.com/torvalds/linux/master/"
    "drivers/pinctrl/tegra/pinctrl-tegra20.c"
)

PUPD = {"NORMAL": "TEGRA_PIN_PULL_NONE", "PULL_UP": "TEGRA_PIN_PULL_UP",
        "PULL_DOWN": "TEGRA_PIN_PULL_DOWN"}
TRI = {"NORMAL": "TEGRA_PIN_DISABLE", "TRISTATE": "TEGRA_PIN_ENABLE"}

MUX_RE = re.compile(r"\{\s*TEGRA_PINGROUP_(\w+),\s*TEGRA_MUX_(\w+),\s*"
                    r"TEGRA_PUPD_(\w+),\s*TEGRA_TRI_(\w+)\s*\}")
# Ordem dos campos em tegra_drive_pingroup_config: pingroup, hsm, schmitt,
# drive, pull_down, pull_up, slew_rising, slew_falling
DRIVE_RE = re.compile(r"\{\s*TEGRA_DRIVE_PINGROUP_(\w+),\s*TEGRA_HSM_(\w+),\s*"
                      r"TEGRA_SCHMITT_(\w+),\s*TEGRA_DRIVE_(DIV_\d),\s*"
                      r"TEGRA_PULL_(\d+),\s*TEGRA_PULL_(\d+),\s*"
                      r"TEGRA_SLEW_(\w+),\s*TEGRA_SLEW_(\w+)\s*\}")


def read_or_fetch(path, url, gitiles=False):
    if path:
        with open(path) as f:
            return f.read()
    print(f"baixando {url}", file=sys.stderr)
    with urllib.request.urlopen(url, timeout=60) as r:
        data = r.read()
    return (base64.b64decode(data) if gitiles else data).decode()


def is_memory_group(pg):
    return pg.startswith("xm2") or pg == "memcomp"


def convert(board, tables, pinctrl):
    safe = {m.group(1).lower(): m.group(2).lower() for m in re.finditer(
        r"PINGROUP\((\w+),\s*\w+,\s*\w+,\s*\w+,\s*\w+,\s*\w+,\s*(\w+),", tables)}

    # Funções válidas por grupo no mainline, e se o grupo tem registrador
    # de tristate e de pull (-1 = não tem; ex.: pinos do LCD sem pull).
    # MUX_PG(nome, f0, f1, f2, f3, tri_r, tri_b, mux_r, mux_b, pupd_r, pupd_b)
    groups, has_tri, has_pull = {}, set(), set()
    for m in re.finditer(r"MUX_PG\((\w+),\s*(\w+),\s*(\w+),\s*(\w+),\s*(\w+),"
                         r"\s*(-?\w+),\s*-?\w+,\s*-?\w+,\s*-?\w+,\s*(-?\w+),", pinctrl):
        groups[m.group(1)] = [f.lower() for f in m.group(2, 3, 4, 5)]
        if m.group(6) != "-1":
            has_tri.add(m.group(1))
        if m.group(7) != "-1":
            has_pull.add(m.group(1))
    pull_groups = set(re.findall(r"PULL_PG\((\w+),", pinctrl))
    drive_groups = set(re.findall(r"DRV_PG(?:_EXT)?\((\w+),", pinctrl))
    if not groups or not safe:
        sys.exit("erro: tabelas de referência vazias ou em formato inesperado")

    errors, skipped, safe_used, no_pull = [], [], [], []
    mux_nodes = OrderedDict()    # (função, pull, tristate) -> [grupos]
    pull_nodes = OrderedDict()   # pull -> [grupos]
    drive_nodes = OrderedDict()  # parâmetros -> [grupos]

    for m in MUX_RE.finditer(board):
        pg, mux, pupd, tri = m.group(1).lower(), m.group(2).lower(), m.group(3), m.group(4)
        if is_memory_group(pg):
            skipped.append(pg)
            continue
        if pg in groups:
            valid = groups[pg]
            if mux == "safe":
                # RSVDn é a posição n-1 na lista de funções do grupo
                s = safe.get(pg)
                if s is None:
                    errors.append(f"{pg}: sem func_safe em pinmux-t2-tables.c")
                    continue
                r = re.fullmatch(r"rsvd(\d)", s)
                mux = valid[int(r.group(1)) - 1] if r else s
                safe_used.append(f"{pg}={mux}")
            if mux == "i2c":
                func = next((f for f in ("i2c1", "i2cp") if f in valid), None)
                if func is None:
                    errors.append(f"{pg}: I2C sem equivalente em {valid}")
                    continue
            elif mux in valid:
                func = mux
            else:
                errors.append(f"{pg}: função {mux} não existe no mainline {valid}")
                continue
            # Um grupo sem o registrador faz o kernel abortar o pinmux inteiro
            pull = PUPD[pupd] if pg in has_pull else None
            if pull is None and pupd != "NORMAL":
                no_pull.append(pg)
            mux_nodes.setdefault((func, pull, TRI[tri] if pg in has_tri else None),
                                 []).append(pg)
        elif pg in pull_groups:
            # Grupos só de pull não têm mux nem tristate
            pull_nodes.setdefault(PUPD[pupd], []).append(pg)
        else:
            errors.append(f"{pg}: grupo desconhecido no mainline")

    for m in DRIVE_RE.finditer(board):
        pg = m.group(1).lower()
        if is_memory_group(pg):
            skipped.append("drive_" + pg)
            continue
        if pg not in drive_groups:
            errors.append(f"drive_{pg}: grupo desconhecido no mainline")
            continue
        key = (m.group(2), m.group(3), m.group(4), int(m.group(5)),
               int(m.group(6)), m.group(7), m.group(8))
        drive_nodes.setdefault(key, []).append("drive_" + pg)

    if errors:
        sys.exit("erros:\n  " + "\n  ".join(errors))
    if not (mux_nodes or drive_nodes):
        sys.exit("erro: nenhuma tabela de pinmux encontrada no arquivo da placa")

    pins = [p for ps in (*mux_nodes.values(), *pull_nodes.values(),
                         *drive_nodes.values()) for p in ps]
    dups = sorted({p for p in pins if pins.count(p) > 1})
    if dups:
        sys.exit(f"erro: grupos configurados mais de uma vez: {dups}")

    stats = (f"mux: {sum(map(len, mux_nodes.values()))} grupos em {len(mux_nodes)} nós; "
             f"pull: {sum(map(len, pull_nodes.values()))}; "
             f"drive: {sum(map(len, drive_nodes.values()))} em {len(drive_nodes)} nós")
    if no_pull:
        stats += f"\npull omitido (grupo sem registrador de pull): {', '.join(no_pull)}"
    return mux_nodes, pull_nodes, drive_nodes, skipped, safe_used, stats


def render(mux_nodes, pull_nodes, drive_nodes, indent):
    names = set()

    def uniq(n):
        base, i = n, 2
        while n in names:
            n, i = f"{base}-{i}", i + 1
        names.add(n)
        return n

    def pins_list(pins):
        lines = [", ".join(f'"{p}"' for p in pins[i:i + 5])
                 for i in range(0, len(pins), 5)]
        return (",\n" + indent + "\t\t").join(lines)

    def onoff(v):
        return "TEGRA_PIN_ENABLE" if v == "ENABLE" else "TEGRA_PIN_DISABLE"

    I, o = indent, []
    for (func, pull, tri), pins in mux_nodes.items():
        o += [f"{I}{uniq(pins[0])} {{",
              f"{I}\tnvidia,pins = {pins_list(pins)};",
              f'{I}\tnvidia,function = "{func}";']
        if pull:
            o.append(f"{I}\tnvidia,pull = <{pull}>;")
        if tri:
            o.append(f"{I}\tnvidia,tristate = <{tri}>;")
        o.append(f"{I}}};")
    for pull, pins in pull_nodes.items():
        o += [f"{I}{uniq('conf_' + pins[0])} {{",
              f"{I}\tnvidia,pins = {pins_list(pins)};",
              f"{I}\tnvidia,pull = <{pull}>;",
              f"{I}}};"]
    for (hsm, sch, div, pd, pu, rise, fall), pins in drive_nodes.items():
        o += [f"{I}{uniq(pins[0])} {{",
              f"{I}\tnvidia,pins = {pins_list(pins)};",
              f"{I}\tnvidia,high-speed-mode = <{onoff(hsm)}>;",
              f"{I}\tnvidia,schmitt = <{onoff(sch)}>;",
              f"{I}\tnvidia,low-power-mode = <TEGRA_PIN_LP_DRIVE_{div}>;",
              f"{I}\tnvidia,pull-down-strength = <{pd}>;",
              f"{I}\tnvidia,pull-up-strength = <{pu}>;",
              f"{I}\tnvidia,slew-rate-rising = <TEGRA_PIN_SLEW_RATE_{rise}>;",
              f"{I}\tnvidia,slew-rate-falling = <TEGRA_PIN_SLEW_RATE_{fall}>;",
              f"{I}}};"]
    return "\n".join(o) + "\n"


def main():
    ap = argparse.ArgumentParser(
        description="Converte pinmux de placa Tegra 2 (Android) em device tree.",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("board", help="board-*-pinmux.c do kernel Android")
    ap.add_argument("--tables", help="pinmux-t2-tables.c local (padrão: baixar)")
    ap.add_argument("--branch", default="android-tegra-moto-2.6.39-jb-mr0",
                    help="branch de kernel/tegra para baixar pinmux-t2-tables.c")
    ap.add_argument("--pinctrl", help="pinctrl-tegra20.c local (padrão: baixar do mainline)")
    ap.add_argument("--full", action="store_true",
                    help="gera o nó pinmux@70000014 completo, com pinctrl-0")
    ap.add_argument("-o", "--output", help="arquivo de saída (padrão: stdout)")
    args = ap.parse_args()

    with open(args.board) as f:
        board = f.read()
    tables = read_or_fetch(args.tables, ANDROID_TABLES_URL.format(branch=args.branch),
                           gitiles=True)
    pinctrl = read_or_fetch(args.pinctrl, PINCTRL_URL)

    mux, pull, drive, skipped, safe_used, stats = convert(board, tables, pinctrl)

    if args.full:
        body = render(mux, pull, drive, "\t\t\t")
        out = ("\tpinmux@70000014 {\n"
               '\t\tpinctrl-names = "default";\n'
               "\t\tpinctrl-0 = <&state_default>;\n\n"
               "\t\tstate_default: pinmux {\n" + body + "\t\t};\n\t};\n")
    else:
        out = render(mux, pull, drive, "\t\t\t")

    if args.output:
        with open(args.output, "w") as f:
            f.write(out)
    else:
        sys.stdout.write(out)

    print(stats, file=sys.stderr)
    if skipped:
        print("ignorados (memória):", ", ".join(skipped), file=sys.stderr)
    if safe_used:
        print("TEGRA_MUX_SAFE ->", ", ".join(safe_used), file=sys.stderr)
    # Configurações que a placa muda em código, fora da tabela
    extra = re.findall(r"tegra_pinmux_set_\w+\(\s*TEGRA_PINGROUP_(\w+)", board)
    if extra:
        print("atenção: o arquivo ajusta em código (por revisão/modelo):",
              ", ".join(sorted(set(p.lower() for p in extra))), file=sys.stderr)


if __name__ == "__main__":
    main()
