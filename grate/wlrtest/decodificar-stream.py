#!/usr/bin/env python3
"""Decodifica um dump GRATE_DUMP_STREAM (palavras host1x) em escritas de registrador.

Uso: decodificar-stream.py dump.txt  -> imprime "reg valor" na ordem, uma escrita por linha.
RELOC: o firewall troca o valor pelo endereço do BO; aqui aparece o handle/offset cru.
"""
import re
import sys

words = [int(w, 16) for w in re.findall(r"\b[0-9a-f]{8}\b", open(sys.argv[1]).read())]
i = 0
out = []
while i < len(words):
    w = words[i]
    op = w >> 28
    i += 1
    if op == 0:  # SETCLASS
        out.append(("class", (w >> 6) & 0x3ff))
    elif op == 1:  # INCR
        off, cnt = (w >> 16) & 0xfff, w & 0xffff
        for k in range(cnt):
            out.append((off + k, words[i + k]))
        i += cnt
    elif op == 2:  # NONINCR
        off, cnt = (w >> 16) & 0xfff, w & 0xffff
        for k in range(cnt):
            out.append((off, words[i + k]))
        i += cnt
    elif op == 3:  # MASK
        off, mask = (w >> 16) & 0xfff, w & 0xffff
        k = 0
        for b in range(16):
            if mask & (1 << b):
                out.append((off + b, words[i + k]))
                k += 1
        i += k
    elif op == 4:  # IMM
        out.append(((w >> 16) & 0xfff, w & 0xffff))
    else:
        out.append(("op%d" % op, w))
for r, v in out:
    print(("%03x" % r if isinstance(r, int) else r), "%08x" % v)
