import sys, wave, array, math
w = wave.open(sys.argv[1]); ch = w.getnchannels(); r = w.getframerate()
a = array.array('h', w.readframes(w.getnframes()))
print(f"{ch} canais, {r} Hz, {len(a)//ch} quadros")
for c in range(ch):
    x = a[c::ch]
    n = len(x); m = sum(x)/n
    rms = math.sqrt(sum((v-m)**2 for v in x)/n)
    print(f" canal {c}: min {min(x)} max {max(x)} média {m:.1f} rms {rms:.1f}  zeros {x.count(0)}  primeiros {list(x[r:r+8])}")
    # rms por 0,5 s
    seg = r//2
    print("   rms/0.5s:", [round(math.sqrt(sum((v-m)**2 for v in x[i:i+seg])/seg)) for i in range(0, n-seg+1, seg)])
