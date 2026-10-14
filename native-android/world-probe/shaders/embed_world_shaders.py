"""Embed reviewed source once; strict variants alter only the shader prologue."""
import pathlib,sys
root,out=map(pathlib.Path,sys.argv[1:])
lines=['/* Generated directly from source-reviewed world shaders. */']
def emit(symbol,raw):
 lines.append('static const char '+symbol+'[] =')
 for off in range(0,len(raw),64):lines.append('"'+''.join('\\%03o'%b for b in raw[off:off+64])+'"')
 lines.append(';')
for symbol,name in [('kWorldVertex','world.vert'),('kWorldReferenceVertex','reference.vert'),('kWorldFragment','world.frag')]:emit(symbol,(root/name).read_bytes())
vertex=(root/'world.vert').read_bytes().split(b'\n',1)[1]
fragment=(root/'world.frag').read_bytes().split(b'\n',1)[1]
for suffix,version,extension in [('Core320',320,None),('Ext310',310,'GL_EXT_gpu_shader5'),('Oes310',310,'GL_OES_gpu_shader5')]:
 prologue=('#version %d es\n'%version).encode()
 if extension:prologue+=('#extension %s : require\n'%extension).encode()
 emit('kWorldVertex'+suffix,prologue+b'#define COH_SOURCE_PRECISE precise\n'+vertex)
 emit('kWorldFragment'+suffix,('#version %d es\n'%version).encode()+fragment)
out.write_text('\n'.join(lines)+'\n')
