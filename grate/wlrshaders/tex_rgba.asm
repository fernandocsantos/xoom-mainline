/*
 * wlroots tex_rgba.frag sem blend:
 * gl_FragColor = texture2D(tex, v_texcoord) * alpha. u0.l = alpha em fx10.
 */
pseq_to_dw_exec_nb = 1	// the number of 'EXEC' block where DW happens
alu_buffer_size = 1	// number of .rgba regs carried through pipeline

.uniforms
	[0].l = "alpha";

.asm

EXEC
	MFU:	sfu:  rcp r4
		mul0: bar, sfu, bar0
		mul1: bar, sfu, bar1
		ipl:  t0.fp20, t0.fp20, NOP, NOP

	// sample tex0
	TEX:	tex r2, r3, tex0, r0, r1, r2

	// src *= alpha
	ALU:
		ALU0:	MAD  r2.l, r2.l, u0.l, #0
		ALU1:	MAD  r2.h, r2.h, u0.l, #0
		ALU2:	MAD  r3.l, r3.l, u0.l, #0
		ALU3:	MAD  r3.h, r3.h, u0.l, #0

	DW:	store rt1, r2, r3
;
