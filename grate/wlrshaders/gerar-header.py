#!/usr/bin/env python3
"""Gera grate_wlr_shaders.h a partir das saídas .bin.h do gen_shader_bin.

Uso: gerar-header.py SAIDA.h quad.bin.h quad_blend.bin.h tex_rgba.bin.h ...

Só as palavras do Tegra20 (fs_<nome>_words) e os parâmetros do FS entram; o
vertex shader e o linker continuam vindo do compilador TGSI do grate.
"""
import re
import sys


def opcode(m):
    kind, offset, arg = m.group(1), int(m.group(2), 0), int(m.group(3), 0)
    code = {"INCR": 1, "NONINCR": 2, "IMM": 4}[kind]
    return "0x%08x" % ((code << 28) | (offset << 16) | arg)


def parse(path):
    text = open(path).read()
    name = re.search(r"static const uint32_t fs_(\w+?)_words\[\]", text).group(1)
    body = re.search(r"fs_%s_words\[\] = \{(.*?)\};" % name, text, re.S).group(1)
    words = []
    tok_re = r"HOST1X_OPCODE_(INCR|NONINCR|IMM)\((\w+),\s*(\w+)\)|(0x[0-9A-Fa-f]+)"
    for m in re.finditer(tok_re, body):
        words.append(opcode(m) if m.group(1) else "0x%08x" % int(m.group(4), 16))

    def field(f):
        return int(re.search(r"\.%s = (\d+)," % f, text).group(1))

    return name, words, {
        "alu_buf_size": field("fs_alu_buf_size"),
        "pseq_to_dw": field("fs_pseq_to_dw"),
        "pseq_inst_nb": field("fs_pseq_inst_nb"),
        "used_tram_rows_nb": field("used_tram_rows_nb"),
    }


def main():
    out, inputs = sys.argv[1], sys.argv[2:]
    lines = [
        "/* Gerado por grate/wlrshaders/gerar-header.py: não editar. */",
        "/* Fontes: os .asm de grate/wlrshaders no repositório xoom-mainline (montados com o gen_shader_bin do opentegra). */",
        "",
        "#ifndef GRATE_WLR_SHADERS_H",
        "#define GRATE_WLR_SHADERS_H",
        "",
        "#include <stdint.h>",
        "",
        "struct grate_wlr_fs_bin {",
        "   const char *name;",
        "   const uint32_t *words;",
        "   unsigned num_words;",
        "   unsigned alu_buf_size;",
        "   unsigned pseq_to_dw;",
        "   unsigned pseq_inst_nb;",
        "   unsigned used_tram_rows_nb;",
        "};",
        "",
    ]
    for path in inputs:
        name, words, p = parse(path)
        lines.append("static const uint32_t grate_wlr_%s_words[] = {" % name)
        for i in range(0, len(words), 6):
            lines.append("   " + ", ".join(words[i:i + 6]) + ",")
        lines.append("};")
        lines.append("")
        lines.append("static const struct grate_wlr_fs_bin grate_wlr_%s = {" % name)
        lines.append('   .name = "%s",' % name)
        lines.append("   .words = grate_wlr_%s_words," % name)
        lines.append("   .num_words = %d," % len(words))
        for k, v in p.items():
            lines.append("   .%s = %d," % (k, v))
        lines.append("};")
        lines.append("")
    lines.append("#endif")
    open(out, "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
