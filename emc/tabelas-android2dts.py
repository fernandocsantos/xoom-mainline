#!/usr/bin/env python3
"""Converte uma tabela tegra_emc_table do board-stingray-memory.c (Android)
em nós nvidia,tegra20-emc-table do mainline (mesma ordem dos 46 registradores)."""
import re, sys, json

src, nome = sys.argv[1], sys.argv[2]  # ex.: elpida_40nm
txt = open(src).read()
m = re.search(r"stingray_emc_tables_%s\[\] = \{(.*?)\n\};" % nome, txt, re.S)
tabelas = []
for bloco in re.finditer(r"\.rate = (\d+),.*?\.regs = \{(.*?)\}", m.group(1), re.S):
    regs = re.findall(r"(0x[0-9a-fA-F]+),\s*/\*\s*(\w+)", bloco.group(2))
    assert len(regs) == 46, len(regs)
    tabelas.append((int(bloco.group(1)), regs))

if len(sys.argv) > 3 and sys.argv[3] == "json":
    print(json.dumps({r: [[n, v] for v, n in regs] for r, regs in tabelas}))
    sys.exit()

for rate, regs in tabelas:
    vals = [v.lower() for v, _ in regs]
    linhas = []
    for i in range(0, 46, 4):
        linhas.append(" ".join("0x%08x" % int(v, 16) for v in vals[i:i + 4]))
    print("\t\t\temc-table@%d {" % rate)
    print("\t\t\t\treg = <%d>;" % rate)
    print('\t\t\t\tcompatible = "nvidia,tegra20-emc-table";')
    print("\t\t\t\tclock-frequency = <%d>;" % rate)
    print("\t\t\t\tnvidia,emc-registers = <" + ("\n\t\t\t\t\t".join(linhas)) + ">;")
    print("\t\t\t};\n")
