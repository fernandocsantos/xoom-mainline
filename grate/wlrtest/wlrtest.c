/*
 * wlrtest: exercita no Mesa do grate exatamente os shaders e o estado GL do
 * renderizador GLES2 do wlroots 0.20.2 e confere os pixels.
 *
 * Render target: BO GBM XRGB8888 importado como EGLImage num renderbuffer
 * (como o wlroots faz). Leitura: mmap do dma-buf.
 *
 *   wlrtest            roda todos os testes
 *   wlrtest -c         só compila/linka os programas (útil com GRATE_DEBUG=tgsi)
 */
#define _GNU_SOURCE
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES2/gl2.h>
#include <GLES2/gl2ext.h>
#include <drm_fourcc.h>
#include <fcntl.h>
#include <gbm.h>
#include <math.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

#define W 64
#define H 64

/* Shaders do wlroots 0.20.2 (render/gles2/shaders), sem alterações. */
static const char common_vert[] =
	"uniform mat3 proj;\n"
	"uniform mat3 tex_proj;\n"
	"attribute vec2 pos;\n"
	"varying vec2 v_texcoord;\n"
	"\n"
	"void main() {\n"
	"	vec3 pos3 = vec3(pos, 1.0);\n"
	"	gl_Position = vec4(pos3 * proj, 1.0);\n"
	"	v_texcoord = (pos3 * tex_proj).xy;\n"
	"}\n";

#define FRAG_PRECISION \
	"#ifdef GL_FRAGMENT_PRECISION_HIGH\n" \
	"precision highp float;\n" \
	"#else\n" \
	"precision mediump float;\n" \
	"#endif\n" \
	"\n"

static const char quad_frag[] = FRAG_PRECISION
	"varying vec4 v_color;\n"
	"varying vec2 v_texcoord;\n"
	"uniform vec4 color;\n"
	"\n"
	"void main() {\n"
	"	gl_FragColor = color;\n"
	"}\n";

static const char tex_rgba_frag[] = FRAG_PRECISION
	"varying vec2 v_texcoord;\n"
	"uniform sampler2D tex;\n"
	"uniform float alpha;\n"
	"\n"
	"void main() {\n"
	"	gl_FragColor = texture2D(tex, v_texcoord) * alpha;\n"
	"}\n";

static const char tex_rgbx_frag[] = FRAG_PRECISION
	"varying vec2 v_texcoord;\n"
	"uniform sampler2D tex;\n"
	"uniform float alpha;\n"
	"\n"
	"void main() {\n"
	"	gl_FragColor = vec4(texture2D(tex, v_texcoord).rgb, 1.0) * alpha;\n"
	"}\n";

/* Controle: shaders que o grate compila sozinho (FS só com MOV), como o kmscube. */
static const char ctrl_vert[] =
	"uniform mat3 proj;\n"
	"attribute vec2 pos;\n"
	"varying vec4 v_color;\n"
	"void main() {\n"
	"	gl_Position = vec4(vec3(pos, 1.0) * proj, 1.0);\n"
	"	v_color = vec4(1.0, 0.0, 1.0, 1.0);\n"
	"}\n";

static const char ctrl_frag[] = FRAG_PRECISION
	"varying vec4 v_color;\n"
	"void main() {\n"
	"	gl_FragColor = v_color;\n"
	"}\n";

static const char *vert_src = common_vert;

struct prog {
	const char *name;
	GLuint id;
	GLint proj, tex_proj, tex, alpha, color, pos;
};

static PFNGLEGLIMAGETARGETRENDERBUFFERSTORAGEOESPROC image_target_rb;
static PFNEGLCREATEIMAGEKHRPROC create_image;
static uint32_t *pixels;
static int falhas;

static GLuint compile(GLenum type, const char *src, const char *name)
{
	GLuint s = glCreateShader(type);
	glShaderSource(s, 1, &src, NULL);
	glCompileShader(s);
	GLint ok;
	glGetShaderiv(s, GL_COMPILE_STATUS, &ok);
	if (!ok) {
		char log[1024];
		glGetShaderInfoLog(s, sizeof(log), NULL, log);
		fprintf(stderr, "%s: compilação falhou: %s\n", name, log);
		exit(1);
	}
	return s;
}

static void link_prog(struct prog *p, const char *frag)
{
	GLuint vs = compile(GL_VERTEX_SHADER, vert_src, p->name);
	GLuint fs = compile(GL_FRAGMENT_SHADER, frag, p->name);
	p->id = glCreateProgram();
	glAttachShader(p->id, vs);
	glAttachShader(p->id, fs);
	glLinkProgram(p->id);
	GLint ok;
	glGetProgramiv(p->id, GL_LINK_STATUS, &ok);
	if (!ok) {
		fprintf(stderr, "%s: link falhou\n", p->name);
		exit(1);
	}
	p->proj = glGetUniformLocation(p->id, "proj");
	p->tex_proj = glGetUniformLocation(p->id, "tex_proj");
	p->tex = glGetUniformLocation(p->id, "tex");
	p->alpha = glGetUniformLocation(p->id, "alpha");
	p->color = glGetUniformLocation(p->id, "color");
	p->pos = glGetAttribLocation(p->id, "pos");
}

/* Desenha o quadrado unitário mapeado para o retângulo (x, y, w, h) em pixels. */
static void draw_rect(struct prog *p, int x, int y, int w, int h)
{
	/* Mesma convenção do wlroots: matriz row-major, GL_FALSE, pos3 * proj. */
	float proj[9] = {
		2.0f * w / W, 0, 2.0f * x / W - 1,
		0, 2.0f * h / H, 2.0f * y / H - 1,
		0, 0, 1,
	};
	float tex_proj[9] = { 1, 0, 0, 0, 1, 0, 0, 0, 1 };
	static const GLfloat verts[] = {
		0, 0, 1, 0, 0, 1,
		1, 0, 1, 1, 0, 1,
	};

	glUniformMatrix3fv(p->proj, 1, GL_FALSE, proj);
	if (p->tex_proj >= 0)
		glUniformMatrix3fv(p->tex_proj, 1, GL_FALSE, tex_proj);
	glEnableVertexAttribArray(p->pos);
	glVertexAttribPointer(p->pos, 2, GL_FLOAT, GL_FALSE, 0, verts);
	glDrawArrays(GL_TRIANGLES, 0, 6);
	glDisableVertexAttribArray(p->pos);
}

/* Pixel (x, y) do GL: num FBO a linha 0 da memória é y = 0. */
static uint32_t px(int x, int y)
{
	return pixels[y * W + x] & 0x00ffffff;
}

static int canal(uint32_t c, int s)
{
	return (c >> s) & 0xff;
}

static void confere(const char *teste, int x, int y, uint32_t esperado)
{
	glFinish();
	uint32_t v = px(x, y);
	int ok = 1;
	for (int s = 0; s < 24; s += 8)
		if (abs(canal(v, s) - canal(esperado, s)) > 3)
			ok = 0;
	printf("%-34s (%2d,%2d) = %06x esperado %06x  %s\n", teste, x, y, v,
	       esperado, ok ? "ok" : "FALHOU");
	if (!ok) {
		falhas++;
		/* mapa 8x8 (y = 0 embaixo), amostrando o centro de cada bloco */
		for (int by = 7; by >= 0; by--) {
			printf("    ");
			for (int bx = 0; bx < 8; bx++)
				printf(" %06x", px(bx * 8 + 4, by * 8 + 4));
			printf("\n");
		}
	}
}

int main(int argc, char **argv)
{
	bool so_compilar = argc > 1 && !strcmp(argv[1], "-c");

	int fd = open("/dev/dri/renderD128", O_RDWR | O_CLOEXEC);
	struct gbm_device *gbm = gbm_create_device(fd);
	PFNEGLGETPLATFORMDISPLAYEXTPROC get_dpy = (void *)
		eglGetProcAddress("eglGetPlatformDisplayEXT");
	EGLDisplay dpy = get_dpy(EGL_PLATFORM_GBM_KHR, gbm, NULL);
	if (!eglInitialize(dpy, NULL, NULL)) {
		fprintf(stderr, "eglInitialize falhou\n");
		return 1;
	}
	eglBindAPI(EGL_OPENGL_ES_API);
	static const EGLint ctx_attr[] = { EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE };
	EGLContext ctx = eglCreateContext(dpy, EGL_NO_CONFIG_KHR, EGL_NO_CONTEXT, ctx_attr);
	eglMakeCurrent(dpy, EGL_NO_SURFACE, EGL_NO_SURFACE, ctx);
	printf("GL_RENDERER: %s\n", glGetString(GL_RENDERER));

	struct prog quad = { "quad" }, rgba = { "tex_rgba" }, rgbx = { "tex_rgbx" };
	struct prog ctrl = { "controle" };
	vert_src = ctrl_vert;
	link_prog(&ctrl, ctrl_frag);
	vert_src = common_vert;
	link_prog(&quad, quad_frag);
	link_prog(&rgba, tex_rgba_frag);
	link_prog(&rgbx, tex_rgbx_frag);
	if (so_compilar) {
		printf("programas linkados\n");
		return 0;
	}

	/* Render target como o wlroots: BO GBM -> dma-buf -> EGLImage -> renderbuffer. */
	struct gbm_bo *bo = gbm_bo_create(gbm, W, H, GBM_FORMAT_XRGB8888,
					  GBM_BO_USE_RENDERING | GBM_BO_USE_LINEAR);
	int dmabuf = gbm_bo_get_fd(bo);
	uint32_t stride = gbm_bo_get_stride(bo);
	if (stride != W * 4) {
		fprintf(stderr, "stride %u inesperado\n", stride);
		return 1;
	}
	create_image = (void *)eglGetProcAddress("eglCreateImageKHR");
	image_target_rb = (void *)eglGetProcAddress("glEGLImageTargetRenderbufferStorageOES");
	EGLint img_attr[] = {
		EGL_WIDTH, W, EGL_HEIGHT, H,
		EGL_LINUX_DRM_FOURCC_EXT, DRM_FORMAT_XRGB8888,
		EGL_DMA_BUF_PLANE0_FD_EXT, dmabuf,
		EGL_DMA_BUF_PLANE0_OFFSET_EXT, 0,
		EGL_DMA_BUF_PLANE0_PITCH_EXT, (EGLint)stride,
		EGL_NONE,
	};
	EGLImageKHR img = create_image(dpy, EGL_NO_CONTEXT, EGL_LINUX_DMA_BUF_EXT, NULL, img_attr);
	if (img == EGL_NO_IMAGE_KHR) {
		fprintf(stderr, "eglCreateImageKHR falhou: 0x%x\n", eglGetError());
		return 1;
	}
	GLuint rb, fb;
	glGenRenderbuffers(1, &rb);
	glBindRenderbuffer(GL_RENDERBUFFER, rb);
	image_target_rb(GL_RENDERBUFFER, img);
	glGenFramebuffers(1, &fb);
	glBindFramebuffer(GL_FRAMEBUFFER, fb);
	glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_RENDERBUFFER, rb);
	GLenum st = glCheckFramebufferStatus(GL_FRAMEBUFFER);
	if (st != GL_FRAMEBUFFER_COMPLETE) {
		fprintf(stderr, "FBO incompleto: 0x%x\n", st);
		return 1;
	}
	pixels = mmap(NULL, stride * H, PROT_READ, MAP_SHARED, dmabuf, 0);
	if (pixels == MAP_FAILED) {
		perror("mmap do dma-buf");
		return 1;
	}

	/* Estado por passada do wlroots (pass.c). */
	glViewport(0, 0, W, H);
	glBlendFunc(GL_ONE, GL_ONE_MINUS_SRC_ALPHA);
	glDisable(GL_SCISSOR_TEST);

	/* 1. clear */
	glClearColor(0, 0, 1, 1);
	glClear(GL_COLOR_BUFFER_BIT);
	confere("clear azul", 2, 2, 0x0000ff);

	/* 1b. controle: FS compilado pelo grate */
	glUseProgram(ctrl.id);
	glDisable(GL_BLEND);
	draw_rect(&ctrl, 0, 48, 16, 16);
	confere("controle (MOV do grate) magenta", 8, 56, 0xff00ff);

	/* 2. quad sem blend */
	glUseProgram(quad.id);
	glDisable(GL_BLEND);
	glUniform4f(quad.color, 1, 0, 0, 1);
	draw_rect(&quad, 8, 8, 16, 16);
	confere("quad vermelho sem blend", 16, 16, 0xff0000);
	confere("fora do quad continua azul", 40, 40, 0x0000ff);

	/* 3. quad com blend premultiplicado: (0, .5, 0, .5) sobre azul */
	glEnable(GL_BLEND);
	glUniform4f(quad.color, 0, 0.5f, 0, 0.5f);
	draw_rect(&quad, 32, 32, 16, 16);
	confere("quad verde 50% sobre azul", 40, 40, 0x008080);

	/* Textura 2x2 ARGB8888 em memória (BGRA): vermelho, verde / azul, branco 50% premult. */
	static const uint32_t texels[4] = {
		0xffff0000, 0xff00ff00,
		0xff0000ff, 0x80808080,
	};
	GLuint tex;
	glGenTextures(1, &tex);
	glBindTexture(GL_TEXTURE_2D, tex);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
	glTexImage2D(GL_TEXTURE_2D, 0, GL_BGRA_EXT, 2, 2, 0, GL_BGRA_EXT,
		     GL_UNSIGNED_BYTE, texels);

	/* 4. tex_rgba sem blend, alpha 1; texel (0,0) fica embaixo à esquerda */
	glClear(GL_COLOR_BUFFER_BIT);
	confere("clear apaga o quad (36,36)", 36, 36, 0x0000ff);
	confere("clear apaga o quad (44,44)", 44, 44, 0x0000ff);
	confere("clear apaga o quad vermelho", 12, 12, 0x0000ff);
	glUseProgram(rgba.id);
	glUniform1i(rgba.tex, 0);
	glDisable(GL_BLEND);
	glUniform1f(rgba.alpha, 1.0f);
	draw_rect(&rgba, 0, 0, 32, 32);
	confere("tex_rgba texel vermelho", 8, 8, 0xff0000);
	confere("tex_rgba texel verde", 24, 8, 0x00ff00);
	confere("tex_rgba texel azul", 8, 24, 0x0000ff);
	confere("tex_rgba texel branco 50%", 24, 24, 0x808080);

	/* 5. tex_rgba com blend e alpha .5 sobre o fundo azul */
	glEnable(GL_BLEND);
	glUniform1f(rgba.alpha, 0.5f);
	draw_rect(&rgba, 32, 32, 32, 32);
	confere("tex_rgba 50% vermelho sobre azul", 40, 40, 0x800080);
	confere("tex_rgba 25% branco sobre azul", 56, 56, 0x4040ff);

	/* 6. tex_rgbx: ignora o alpha da textura */
	glDisable(GL_BLEND);
	glUseProgram(rgbx.id);
	glUniform1i(rgbx.tex, 0);
	glUniform1f(rgbx.alpha, 1.0f);
	draw_rect(&rgbx, 32, 0, 32, 32);
	confere("tex_rgbx texel branco 50% opaco", 56, 24, 0x808080);

	/* 7. filtro linear: meio da textura deve misturar os quatro texels */
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
	glUseProgram(rgba.id);
	glUniform1f(rgba.alpha, 1.0f);
	draw_rect(&rgba, 0, 32, 32, 32);
	/*
	 * O centro do pixel (16.5, 48.5) não cai no meio exato dos texels:
	 * pesos 0,469/0,531 dão (92, 100, 100).
	 */
	confere("tex_rgba linear centro", 16, 48, 0x5c6464);

	/* nada desenhou de novo em (36,36) depois do tex_rgba com blend */
	confere("estado final (36,36)", 36, 36, 0x800080);

	printf("%s: %d falha(s)\n", falhas ? "FALHOU" : "OK", falhas);
	return falhas ? 1 : 0;
}
