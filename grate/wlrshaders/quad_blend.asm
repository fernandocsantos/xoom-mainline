/*
 * wlroots quad.frag com glBlendFunc(GL_ONE, GL_ONE_MINUS_SRC_ALPHA):
 * dst = color + (1 - color.a) * dst. u0 = (b, g), u1 = (r, a) em fx10.
 */
pseq_to_dw_exec_nb = 3	// the number of 'EXEC' block where DW happens
alu_buffer_size = 2	// number of .rgba regs carried through pipeline

.uniforms
	[0].l = "color_b";
	[0].h = "color_g";
	[1].l = "color_r";
	[1].h = "color_a";

.asm

EXEC
	ALU:
		ALU0:	MAD  r0.l, u0.l, #1, #0
		ALU1:	MAD  r0.h, u0.h, #1, #0
		ALU2:	MAD  r1.l, u1.l, #1, #0
		ALU3:	MAD  r1.h, u1.h, #1, #0
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
