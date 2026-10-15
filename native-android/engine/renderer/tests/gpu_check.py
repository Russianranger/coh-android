"""Real surfaceless Mesa GLES qualification through the concrete C backend.
This is host software-GPU evidence, never Android/Adreno/Thor acceptance.
"""
import ctypes as C,hashlib,json,math,struct
from pathlib import Path
from bindings import *
from oracle import fragment,vertex,clamp
class EGL:
    def __init__(self):
        self.e=C.CDLL('libEGL.so.1');self.g=C.CDLL('libGL.so.1')
        self.ef('eglGetProcAddress',C.c_void_p,[C.c_char_p]);p=self.e.eglGetProcAddress(b'eglGetPlatformDisplayEXT');assert p
        self.display=C.CFUNCTYPE(C.c_void_p,U,C.c_void_p,C.POINTER(C.c_int))(p)(0x31dd,None,None);assert self.display
        self.ef('eglInitialize',U,[C.c_void_p,C.POINTER(C.c_int),C.POINTER(C.c_int)]);a=C.c_int();b=C.c_int();assert self.e.eglInitialize(self.display,C.byref(a),C.byref(b));self.version=[a.value,b.value]
        self.ef('eglBindAPI',U,[U]);assert self.e.eglBindAPI(0x30a0)
        self.ef('eglChooseConfig',U,[C.c_void_p,C.POINTER(C.c_int),C.POINTER(C.c_void_p),C.c_int,C.POINTER(C.c_int)])
        cfg=C.c_void_p();n=C.c_int();attrs=(C.c_int*15)(0x3033,1,0x3040,0x40,0x3024,8,0x3023,8,0x3022,8,0x3021,8,0x3038,0,0);assert self.e.eglChooseConfig(self.display,attrs,C.byref(cfg),1,C.byref(n)) and n.value
        self.config=cfg
        self.ef('eglCreateContext',C.c_void_p,[C.c_void_p,C.c_void_p,C.c_void_p,C.POINTER(C.c_int)]);self.context=self.e.eglCreateContext(self.display,cfg,None,(C.c_int*3)(0x3098,3,0x3038));assert self.context
        self.ef('eglMakeCurrent',U,[C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p]);assert self.e.eglMakeCurrent(self.display,None,None,self.context)
        self.ef('eglDestroyContext',U,[C.c_void_p,C.c_void_p]);self.ef('eglTerminate',U,[C.c_void_p])
        self.gf('glGetString',C.c_char_p,[U]);self.identity={k:self.g.glGetString(v).decode() for k,v in [('vendor',0x1f00),('renderer',0x1f01),('version',0x1f02),('glsl',0x8b8c)]}
        self.gf('glGetError',U,[])
        for name in ('glGenTextures','glGenFramebuffers','glGenBuffers','glGenVertexArrays','glGenTransformFeedbacks'):self.gf(name,None,[C.c_int,C.POINTER(U)])
        for name in ('glDeleteTextures','glDeleteFramebuffers','glDeleteBuffers','glDeleteVertexArrays','glDeleteTransformFeedbacks'):self.gf(name,None,[C.c_int,C.POINTER(U)])
        for name in ('glBindTexture','glBindFramebuffer','glBindBuffer','glBindTransformFeedback'):self.gf(name,None,[U,U])
        self.gf('glTexImage2D',None,[U,C.c_int,C.c_int,C.c_int,C.c_int,C.c_int,U,U,C.c_void_p]);self.gf('glTexParameteri',None,[U,U,C.c_int]);self.gf('glFramebufferTexture2D',None,[U,U,U,U,C.c_int]);self.gf('glCheckFramebufferStatus',U,[U]);self.gf('glViewport',None,[C.c_int,C.c_int,C.c_int,C.c_int]);self.gf('glClearColor',None,[F,F,F,F]);self.gf('glClear',None,[U]);self.gf('glReadPixels',None,[C.c_int,C.c_int,C.c_int,C.c_int,U,U,C.c_void_p]);self.gf('glDepthMask',None,[C.c_uint8])
        self.gf('glCreateShader',U,[U]);self.gf('glShaderSource',None,[U,C.c_int,C.POINTER(C.c_char_p),C.POINTER(C.c_int)]);self.gf('glCompileShader',None,[U]);self.gf('glGetShaderiv',None,[U,U,C.POINTER(C.c_int)]);self.gf('glGetShaderInfoLog',None,[U,C.c_int,C.POINTER(C.c_int),C.c_void_p]);self.gf('glCreateProgram',U,[]);self.gf('glAttachShader',None,[U,U]);self.gf('glTransformFeedbackVaryings',None,[U,C.c_int,C.POINTER(C.c_char_p),U]);self.gf('glLinkProgram',None,[U]);self.gf('glGetProgramiv',None,[U,U,C.POINTER(C.c_int)]);self.gf('glGetProgramInfoLog',None,[U,C.c_int,C.POINTER(C.c_int),C.c_void_p]);self.gf('glDeleteProgram',None,[U]);self.gf('glDeleteShader',None,[U]);self.gf('glUseProgram',None,[U]);self.gf('glGetUniformLocation',C.c_int,[U,C.c_char_p]);self.gf('glUniformMatrix4fv',None,[C.c_int,C.c_int,C.c_uint8,C.POINTER(F)]);self.gf('glUniform1i',None,[C.c_int,C.c_int]);self.gf('glUniform1f',None,[C.c_int,F]);self.gf('glUniform3fv',None,[C.c_int,C.c_int,C.POINTER(F)]);self.gf('glUniform4fv',None,[C.c_int,C.c_int,C.POINTER(F)]);self.gf('glBindVertexArray',None,[U]);self.gf('glBufferData',None,[U,C.c_ssize_t,C.c_void_p,U]);self.gf('glVertexAttribPointer',None,[U,C.c_int,U,C.c_uint8,C.c_int,C.c_void_p]);self.gf('glEnableVertexAttribArray',None,[U]);self.gf('glBindBufferBase',None,[U,U,U]);self.gf('glBeginTransformFeedback',None,[U]);self.gf('glEndTransformFeedback',None,[]);self.gf('glEnable',None,[U]);self.gf('glDisable',None,[U]);self.gf('glDrawArrays',None,[U,C.c_int,C.c_int]);self.gf('glMapBufferRange',C.c_void_p,[U,C.c_ssize_t,C.c_ssize_t,U]);self.gf('glUnmapBuffer',C.c_uint8,[U])
    def ef(self,n,r,a):f=getattr(self.e,n);f.restype=r;f.argtypes=a;return f
    def gf(self,n,r,a):f=getattr(self.g,n);f.restype=r;f.argtypes=a;return f
    def recreate_context(self):
        assert self.e.eglMakeCurrent(self.display,None,None,None)
        assert self.e.eglDestroyContext(self.display,self.context)
        self.context=self.e.eglCreateContext(self.display,self.config,None,(C.c_int*3)(0x3098,3,0x3038));assert self.context
        assert self.e.eglMakeCurrent(self.display,None,None,self.context)
    def close(self):self.e.eglMakeCurrent(self.display,None,None,None);self.e.eglDestroyContext(self.display,self.context);self.e.eglTerminate(self.display)
    def texture(self,w,h,data=None):
        name=U();self.g.glGenTextures(1,C.byref(name));self.g.glBindTexture(0xde1,name);buf=C.create_string_buffer(data) if data is not None else None;self.g.glTexImage2D(0xde1,0,0x8058,w,h,0,0x1908,0x1401,buf)
        for param,value in [(0x2801,0x2600),(0x2800,0x2600),(0x2802,0x812f),(0x2803,0x812f)]:self.g.glTexParameteri(0xde1,param,value)
        return name
    def shader(self,kind,text):
        s=self.g.glCreateShader(kind);a=C.c_char_p(text);self.g.glShaderSource(s,1,C.byref(a),None);self.g.glCompileShader(s);ok=C.c_int();self.g.glGetShaderiv(s,0x8b81,C.byref(ok));log=C.create_string_buffer(4096);self.g.glGetShaderInfoLog(s,4096,None,log);assert ok.value,log.value;return s
    def tf_program(self,v,f):
        vs=self.shader(0x8b31,v);fs=self.shader(0x8b30,f);p=self.g.glCreateProgram();self.g.glAttachShader(p,vs);self.g.glAttachShader(p,fs);names=(C.c_char_p*5)(b'gl_Position',b'vViewPosition',b'vNormal',b'vLit',b'vFog');self.g.glTransformFeedbackVaryings(p,5,names,0x8c8c);self.g.glLinkProgram(p);ok=C.c_int();self.g.glGetProgramiv(p,0x8b82,C.byref(ok));log=C.create_string_buffer(4096);self.g.glGetProgramInfoLog(p,4096,None,log);assert ok.value,log.value;self.g.glDeleteShader(vs);self.g.glDeleteShader(fs);return p

def parse_corpus(p):
    meta=json.loads((p/'world-fixture.json').read_text());b=(p/'world.bin').read_bytes();ref=(p/'material-reference.bin').read_bytes()
    for name in ('world.bin','material-reference.bin'):
        data=(p/name).read_bytes();pin=meta['assets'][name];assert len(data)==pin['bytes'] and hashlib.sha256(data).hexdigest()==pin['sha256']
    assert b[:8]==b'COHWOR09';parts=[];textures=[]
    for i in range(struct.unpack_from('<I',b,16)[0]):
        r=128+i*96;off,size,node,base,dual,flags=struct.unpack_from('<6I',b,r);mesh=b[off:off+size];assert hashlib.sha256(mesh).hexdigest()==meta['parts'][i]['canonical_sha256'];assert mesh[:8]==b'COHMESH1'
        # canonical mesh header: version,header,vertices,indices,bones,offsets
        _,_,nv,ni,nb,stride,vo,io,bo=struct.unpack_from('<9I',mesh,8);assert stride==48
        vertices=(Vertex*nv)()
        for k in range(nv):
            raw=struct.unpack_from('<10f2I',mesh,vo+k*48);vertices[k]=Vertex(V3(*raw[:3]),V3(*raw[3:6]),(F*2)(*raw[6:8]),(F*2)(*raw[6:8]),V4(.25,.25,.25,1))
        indices=(U*ni)(*struct.unpack_from('<'+str(ni)+'I',mesh,io));parts.append({'vertices':vertices,'indices':indices,'mode':struct.unpack_from('<I',b,r+68)[0],'base':base,'dual':dual})
    to=struct.unpack_from('<I',b,40)[0]
    for i in range(struct.unpack_from('<I',b,20)[0]):
        off,size,w,h=struct.unpack_from('<4I',b,to+i*32);raw=b[off:off+size];assert hashlib.sha256(raw).hexdigest()==meta['textures'][i]['rgba_sha256'];textures.append((w,h,raw))
    return parts,textures,ref,{'world_sha256':hashlib.sha256(b).hexdigest(),'material_reference_sha256':hashlib.sha256(ref).hexdigest(),'vertices':sum(len(x['vertices']) for x in parts),'indices':sum(len(x['indices']) for x in parts),'textures':len(textures)}

def tf_check(e,lib,parts,precise=False):
    lib.coh_renderer_vertex_shader.restype=C.c_char_p;lib.coh_renderer_fragment_shader.argtypes=[C.c_int];lib.coh_renderer_fragment_shader.restype=C.c_char_p
    lib.coh_renderer_vertex_shader_precise.restype=C.c_char_p;lib.coh_renderer_fragment_shader_precise.argtypes=[C.c_int];lib.coh_renderer_fragment_shader_precise.restype=C.c_char_p
    p=e.tf_program(lib.coh_renderer_vertex_shader_precise() if precise else lib.coh_renderer_vertex_shader(),lib.coh_renderer_fragment_shader_precise(0) if precise else lib.coh_renderer_fragment_shader(0));g=e.g;g.glUseProgram(p);vao=U();vbo=U();tf=U();tbo=U();g.glGenVertexArrays(1,C.byref(vao));g.glGenBuffers(1,C.byref(vbo));g.glGenBuffers(1,C.byref(tbo));g.glGenTransformFeedbacks(1,C.byref(tf));g.glBindVertexArray(vao);g.glBindBuffer(0x8892,vbo)
    for loc,count,offset in [(0,3,0),(1,3,12),(2,2,24),(3,2,32),(4,4,40)]:g.glVertexAttribPointer(loc,count,0x1406,0,C.sizeof(Vertex),C.c_void_p(offset));g.glEnableVertexAttribArray(loc)
    max_error=0;components=0
    try:
        for lighting in range(3):
            for part in parts:
                verts=part['vertices'];d=Draw();d.material=lib.coh_renderer_default_material(0);d.material.lighting=lighting;d.material.light=V3(.2,.1,.97);d.material.diffuse=V4(.5,.7,1,1);d.material.ambient=V4(.1,.2,.3,1);d.material.specular=V3(.1,.3,.5);d.material.shininess=8;d.model_view=identity();d.model_view[0]=.8;d.model_view[5]=1.3;d.model_view[10]=1.1;d.model_view[12]=2;d.model_view[13]=-3;d.model_view[14]=-9;d.projection=identity();d.projection[0]=.02;d.projection[5]=.02;d.projection[10]=-.01
                for name,mat in [(b'uModelView',d.model_view),(b'uProjection',d.projection)]:g.glUniformMatrix4fv(g.glGetUniformLocation(p,name),1,0,mat)
                m=d.material;g.glUniform1i(g.glGetUniformLocation(p,b'uLighting'),lighting);g.glUniform3fv(g.glGetUniformLocation(p,b'uLight'),1,m.light);g.glUniform3fv(g.glGetUniformLocation(p,b'uSpecular'),1,m.specular);g.glUniform4fv(g.glGetUniformLocation(p,b'uDiffuse'),1,m.diffuse);g.glUniform4fv(g.glGetUniformLocation(p,b'uAmbient'),1,m.ambient);g.glUniform1f(g.glGetUniformLocation(p,b'uShininess'),m.shininess)
                g.glBindBuffer(0x8892,vbo);g.glBufferData(0x8892,C.sizeof(verts),verts,0x88e8);g.glBindTransformFeedback(0x8e22,tf);g.glBindBuffer(0x8c8e,tbo);g.glBufferData(0x8c8e,len(verts)*15*4,None,0x88e8);g.glBindBufferBase(0x8c8e,0,tbo);g.glEnable(0x8c89);g.glBeginTransformFeedback(0);g.glDrawArrays(0,0,len(verts));g.glEndTransformFeedback();g.glDisable(0x8c89);pointer=g.glMapBufferRange(0x8c8e,0,len(verts)*15*4,1);assert pointer;got=C.cast(pointer,C.POINTER(F));values=[got[i] for i in range(len(verts)*15)];assert g.glUnmapBuffer(0x8c8e)
                for i,v in enumerate(verts):
                    clip,n,lit,fog=vertex(d,v);view=[sum(d.model_view[k+4*j]*v.position[j] for j in range(3))+d.model_view[k+12] for k in range(3)];expected=[*clip,*view,*n,*lit,fog];actual=values[i*15:(i+1)*15];err=max(abs(a-b) for a,b in zip(actual,expected));max_error=max(max_error,err);assert err<1e-4,(lighting,i,err,actual,expected);components+=15
        assert g.glGetError()==0
    finally:g.glBindTransformFeedback(0x8e22,0);g.glDeleteProgram(p);g.glDeleteBuffers(1,C.byref(vbo));g.glDeleteBuffers(1,C.byref(tbo));g.glDeleteVertexArrays(1,C.byref(vao));g.glDeleteTransformFeedbacks(1,C.byref(tf))
    return {'passed':True,'components':components,'max_error':max_error,'tolerance':1e-4,'source_geometry':True,'lighting_modes':3,'shader_profile':'ESSL3.20 core precise' if precise else 'ESSL3.00 explicit source order'}

def gpu_check(library,corpus):
    e=EGL();g=e.g;lib=load(library,gles=True);driver=C.c_void_p();backend=Backend();renderer=C.c_void_p();textures=[];fbo=U();target=U()
    try:
        assert lib.coh_renderer_gles_create(65536,196608,C.byref(driver),C.byref(backend))==0
        cfg=Config(32,65536,196608,3);assert lib.coh_renderer_create(C.byref(cfg),C.byref(backend),C.byref(renderer))==0
        parts,tex,refs,pins=parse_corpus(corpus) if corpus else ([],[(1,1,bytes([76,127,178,128])),(1,1,bytes([51,153,230,128]))],None,{})
        for w,h,data in tex:textures.append(e.texture(w,h,data))
        control=e.texture(1,1,bytes([51,153,230,128]));textures.append(control)
        mask=e.texture(1,1,bytes([0,0,0,255]));textures.append(mask)
        target=e.texture(64,64);g.glGenFramebuffers(1,C.byref(fbo));g.glBindFramebuffer(0x8d40,fbo);g.glFramebufferTexture2D(0x8d40,0x8ce0,0xde1,target,0);assert g.glCheckFramebufferStatus(0x8d40)==0x8cd5;g.glViewport(0,0,64,64)
        verts=(Vertex*4)(*[Vertex(V3(x,y,0),V3(0,0,1),(F*2)(u,v),(F*2)(u,v),V4(.25,.25,.25,1)) for x,y,u,v in [(-1,-1,0,0),(1,-1,1,0),(1,1,1,1),(-1,1,0,1)]]);indices=(U*6)(0,1,2,0,2,3);d=Draw(Geometry(verts,4,indices,6,1,1),lib.coh_renderer_default_material(0),identity(),identity(),0)
        pixels=(C.c_uint8*(64*64*4))();cases=0;real_cases=0;max_error=0;compared=0
        def render(m,clear):
            d.material=m;g.glClearColor(*clear);g.glDepthMask(1);g.glClear(0x4000);assert lib.coh_renderer_begin(renderer,0)==0;assert lib.coh_renderer_submit(renderer,C.byref(d))==0;status=lib.coh_renderer_flush(renderer,Cancel());assert status==0,(status,lib.coh_renderer_gles_shader_log(driver));g.glReadPixels(0,0,64,64,0x1908,0x1401,pixels);assert g.glGetError()==0;return bytes(pixels)
        if refs:
            count=struct.unpack_from('<I',refs,24)[0]
            for i in range(count):
                r=64+i*16512;vals=struct.unpack_from('<26f4I',refs,r);flags=vals[26];part=parts[vals[27]];m=lib.coh_renderer_default_material(part['mode']);m.depth_test=m.depth_write=m.cull_back=0;m.const0=V4(*vals[:4]);m.const1=V4(*vals[4:8]);m.fog_params=V4(*vals[12:16]);m.fog_params[2]=m.fog_params[2]-vals[24]+math.sqrt(2);m.fog_color=V4(*vals[16:20]);m.alpha_ref=vals[25];m.blend=1 if flags&1 else 0
                for v in verts:v.color=V4(*vals[8:12])
                m.textures[0]=Texture(textures[part['base']].value,1,1,0,0);m.textures[1]=Texture(control.value if flags&2 else textures[part['dual']].value,1,1,0,0)
                got=render(m,vals[20:24]);expected=refs[r+128:r+128+16384];error=max(abs(a-b) for a,b in zip(got,expected));assert error<=2,(i,error);max_error=max(max_error,error);compared+=len(got);cases+=1;real_cases+=not bool(flags&2)
        # All three shader families, including ADDGLOW mask source branches,
        # with authentic texture pairs used as controlled semantic inputs.
        btex=tex[0];dtex=tex[min(2,len(tex)-1)];glowtex=textures[min(2,len(tex)-1)]
        for family in range(3):
            for glow in (0,1):
                m=lib.coh_renderer_default_material(family);m.depth_test=m.depth_write=m.cull_back=0;m.const0=V4(.2,.7,.4,.5);m.const1=V4(.8,.1,.6,1);m.fog_params=V4(0,0,100,1);m.glow_params=V4(glow,0,0,0);m.textures[0]=Texture(textures[0].value,1,1,0,0);m.textures[1]=Texture(glowtex.value,1,1,0,0);m.textures[2]=Texture(mask.value,1,1,0,0)
                for v in verts:v.color=V4(.25,.25,.25,1)
                got=render(m,(0,0,0,0));expected=bytearray()
                for y in range(64):
                    for x in range(64):
                        def sample(t):
                            w,h,data=t;xx=min(w-1,((2*x+1)*w)//128);yy=min(h-1,((2*y+1)*h)//128);return [c/255 for c in data[(yy*w+xx)*4:(yy*w+xx)*4+4]]
                        color,discard=fragment(m,sample(btex),sample(dtex),0,(.25,.25,.25,1),math.sqrt(2));expected.extend(0 if discard else int(math.floor(clamp(v)*255+.5)) for v in color)
                err=max(abs(a-b) for a,b in zip(got,expected));assert err<=2,(family,glow,err);max_error=max(max_error,err);compared+=len(got);cases+=1
        # Generic authentic meshes run through exact public submission boundary.
        for part in parts:
            d.geometry=Geometry(part['vertices'],len(part['vertices']),part['indices'],len(part['indices']),7,1);d.model_view=identity();d.projection=identity();d.projection[0]=d.projection[5]=d.projection[10]=.001;m=lib.coh_renderer_default_material(part['mode']);m.cull_back=m.depth_test=m.depth_write=0;m.textures[0]=Texture(textures[part['base']].value,1,1,0,0);m.textures[1]=Texture(textures[part['dual']].value,1,1,0,0);render(m,(0,0,0,0))
        result={'passed':True,'identity':e.identity,'egl':e.version,'driver':'concrete C GLES3 backend','material_cases':cases,'authentic_declared_material_cases':real_cases,'controlled_semantic_cases':cases-real_cases,'rgba_components_compared':compared,'max_byte_error':max_error,'tolerance':2,'authentic_input':pins,'stats':{name:getattr(lib.coh_renderer_stats(renderer),name) for name,_ in Stats._fields_},'android_execution':False,'physical_thor':False}
        if parts:result['transform_feedback']=[tf_check(e,lib,parts,False),tf_check(e,lib,parts,True)]
        # Surface recreation resets GL resources and lazily recompiles shaders.
        lib.coh_renderer_surface_lost(renderer,1,1);assert lib.coh_renderer_gles_recreate(driver,1)==0;assert lib.coh_renderer_begin(renderer,0)==7;assert lib.coh_renderer_begin(renderer,1)==0;assert lib.coh_renderer_submit(renderer,C.byref(d))==0;assert lib.coh_renderer_flush(renderer,Cancel())==0;result['surface_recreate_passed']=True
        # Destroy the actual EGL context. Old GPU names are deliberately not
        # deleted in the replacement context; caller reuploads borrowed textures.
        lib.coh_renderer_surface_lost(renderer,2,0);e.recreate_context();textures=[];target=U();fbo=U();assert lib.coh_renderer_gles_recreate(driver,0)==0
        for w,h,data in tex[:2]:textures.append(e.texture(w,h,data))
        target=e.texture(64,64);g.glGenFramebuffers(1,C.byref(fbo));g.glBindFramebuffer(0x8d40,fbo);g.glFramebufferTexture2D(0x8d40,0x8ce0,0xde1,target,0);assert g.glCheckFramebufferStatus(0x8d40)==0x8cd5;g.glViewport(0,0,64,64)
        d.material=lib.coh_renderer_default_material(1);d.material.cull_back=d.material.depth_test=d.material.depth_write=0;d.material.textures[0]=Texture(textures[0].value,1,1,0,0);d.material.textures[1]=Texture(textures[1].value,1,1,0,0)
        assert lib.coh_renderer_begin(renderer,1)==7;assert lib.coh_renderer_begin(renderer,2)==0;assert lib.coh_renderer_submit(renderer,C.byref(d))==0;assert lib.coh_renderer_flush(renderer,Cancel())==0;g.glReadPixels(0,0,64,64,0x1908,0x1401,pixels);assert g.glGetError()==0;result['egl_context_loss_recreate_passed']=True
        return result
    finally:
        if renderer:lib.coh_renderer_destroy(renderer)
        if driver:lib.coh_renderer_gles_destroy(driver,1)
        for t in textures:g.glDeleteTextures(1,C.byref(t))
        if target:g.glDeleteTextures(1,C.byref(target))
        if fbo:g.glDeleteFramebuffers(1,C.byref(fbo))
        e.close()
