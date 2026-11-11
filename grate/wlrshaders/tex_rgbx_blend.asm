/*
 * wlroots tex_rgbx.frag com glBlendFunc(GL_ONE, GL_ONE_MINUS_SRC_ALPHA):
 * gl_FragColor = vec4(texture2D(tex, v_texcoord).rgb, 1.0) * alpha. u0.l = alpha em fx10.
 */
pseq_to_dw_exec_nb = 3	// the number of 'EXEC' block where DW happens
alu_buffer_size = 2	// number of .rgba regs carried through pipeline

.uniforms
	[0].l = "alpha";

.asm

EXEC
	MFU:	sfu:  rcp r4
		mul0: bar, sfu, bar0
		mul1: bar, sfu, bar1
		ipl:  t0.fp20, t0.fp20, NOP, NOP

	// sample tex0
	TEX:	tex r0, r1, tex0, r0, r1, r2

	// src *= alpha
	ALU:
		ALU0:	MAD  r0.l, r0.l, u0.l, #0
		ALU1:	MAD  r0.h, r0.h, u0.l, #0
		ALU2:	MAD  r1.l, r1.l, u0.l, #0
		ALU3:	MAD  r1.h, u0.l, #1, #0
;

EXEC
;

EXEC
	// fetch dst pixel to r2,r3
	PSEQ:	0x0081000A

	// tmp = 1 - src.a
	ALU:
		ALU0:	MAD  lp.lh, -r1.h, #1, #1

	// r0,r1 = (1 - src.a) * dst.bgra + src.bgra
	ALU:
		ALU0:	MAD  r0.l, alu0, r2.l, r0.l (sat)
		ALU1:	MAD  r0.h, alu0, r2.h, r0.h (sat)
		ALU2:	MAD  r1.l, alu0, r3.l, r1.l (sat)
		ALU3:	MAD  r1.h, alu0, r3.h, r1.h (sat)

	DW:	store rt1, r0, r1
;

EXEC
;
