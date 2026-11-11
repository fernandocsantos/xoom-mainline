#!/usr/bin/env python3
# at.py PORTA CMD [CMD...]: manda comandos AT e imprime a resposta (timeout curto)
import os, sys, termios, time, select
fd = os.open(sys.argv[1], os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
a = termios.tcgetattr(fd)
a[0] = 0; a[1] = 0; a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL; a[3] = 0
a[4] = a[5] = termios.B115200
termios.tcsetattr(fd, termios.TCSANOW, a)
termios.tcflush(fd, termios.TCIOFLUSH)
for cmd in sys.argv[2:]:
    os.write(fd, (cmd + "\r").encode())
    out = b""; end = time.time() + float(os.environ.get("T", "2"))
    while time.time() < end:
        r, _, _ = select.select([fd], [], [], 0.2)
        if r:
            try: out += os.read(fd, 4096)
            except BlockingIOError: pass
            if b"OK\r" in out or b"ERROR" in out: break
    print(f"[{cmd}] {out!r}")
os.close(fd)
