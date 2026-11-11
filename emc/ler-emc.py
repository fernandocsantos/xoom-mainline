#!/usr/bin/env python3
# Lê os registradores de timing do EMC (0x7000f400) e o strap do RAM code.
import mmap, os, struct, sys
OFF = dict(RC=0x2c,RFC=0x30,RAS=0x34,RP=0x38,R2W=0x3c,W2R=0x40,R2P=0x44,W2P=0x48,
 RD_RCD=0x4c,WR_RCD=0x50,RRD=0x54,REXT=0x58,WDV=0x5c,QUSE=0x60,QRST=0x64,QSAFE=0x68,
 RDV=0x6c,REFRESH=0x70,BURST_REFRESH_NUM=0x74,PDEX2WR=0x78,PDEX2RD=0x7c,PCHG2PDEN=0x80,
 ACT2PDEN=0x84,AR2PDEN=0x88,RW2PDEN=0x8c,TXSR=0x90,TCKE=0x94,TFAW=0x98,TRPAB=0x9c,
 TCLKSTABLE=0xa0,TCLKSTOP=0xa4,TREFBW=0xa8,QUSE_EXTRA=0xac,FBIO_CFG6=0x114,ODT_WRITE=0xb0,
 ODT_READ=0xb4,FBIO_CFG5=0x104,CFG_DIG_DLL=0x2bc,DLL_XFORM_DQS=0x2c0,DLL_XFORM_QUSE=0x2c4,
 ZCAL_REF_CNT=0x2e0,ZCAL_WAIT_CNT=0x2e4,AUTO_CAL_INTERVAL=0x2a8,CFG_CLKTRIM_0=0x2d0,
 CFG_CLKTRIM_1=0x2d4,CFG_CLKTRIM_2=0x2d8)
fd = os.open("/dev/mem", os.O_RDONLY | os.O_SYNC)
def rd(base, off):
    m = mmap.mmap(fd, 0x1000, mmap.MAP_SHARED, mmap.PROT_READ, offset=base)
    v = struct.unpack_from("<I", m, off)[0]; m.close(); return v
s = rd(0x70000000, 0x8)
print("STRAPPING_OPT_A 0x%08x ram_code %d" % (s, (s >> 4) & 3))
for n, o in OFF.items():
    print("%s 0x%08x" % (n, rd(0x7000f000, 0x400 + o)))
