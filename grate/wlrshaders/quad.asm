/*
 * wlroots quad.frag sem blend: gl_FragColor = color.
 * u0 = (b, g), u1 = (r, a) em fx10.
 */
pseq_to_dw_exec_nb = 1	// the number of 'EXEC' block where DW happens
alu_buffer_size = 1	// number of .rgba regs carried through pipeline

.uniforms
	[0].l = "color_b";
	[0].h = "color_g";
	[1].l = "color_r";
	[1].h = "color_a";

.asm

EXEC
	ALU:
		ALU0:	MAD  r2.l, u0.l, #1, #0
		ALU1:	MAD  r2.h, u0.h, #1, #0
		ALU2:	MAD  r3.l, u1.l, #1, #0
		ALU3:	MAD  r3.h, u1.h, #1, #0

	DW:	store rt1, r2, r3
;
