#ifndef _RENDERPARTICLES_H
#define _RENDERPARTICLES_H

#include "graphics/FX/particle.h"  

#include "graphics/FX/fxfluid.h"

#include "render/thread/rt_particles.h"

int modelDrawParticleSys(ParticleSystem * system, F32 alpha, int VBOBuffer, Mat4 systemMatCamSpace  );
#ifdef NOVODEX_FLUIDS
void drawFluid(FxFluidEmitter* emitter);
#endif
void rdrCleanUpAfterRenderingParticleSystems();
void rdrPrepareToRenderParticleSystems();

#endif
