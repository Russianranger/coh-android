import pathlib,sys
root,out=map(pathlib.Path,sys.argv[1:])
lines=['/* Generated directly from source-reviewed world shaders. */']
for symbol,name in [('kWorldVertex','world.vert'),('kWorldReferenceVertex','reference.vert'),('kWorldFragment','world.frag')]:
 raw=(root/name).read_bytes();lines.append('static const char '+symbol+'[] =')
 for off in range(0,len(raw),64):lines.append('"'+''.join('\\%03o'%b for b in raw[off:off+64])+'"')
 lines.append(';')
out.write_text('\n'.join(lines)+'\n')
