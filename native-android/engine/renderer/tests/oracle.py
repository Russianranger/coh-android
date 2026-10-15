"""Binary64 scalar expressions transcribed from pinned original Cg sources.
No C implementation or generated GLSL is evaluated here. Includes original
specular behavior: no NdotL condition, no specular output clamp.
"""
import math

def clamp(x):return max(0,min(1,x))
def mix(a,b,t):return a+(b-a)*t
def fragment(m,base,dual,mask,lit,fog):
    rgb=[]
    for i in range(3):
        if m.family==0:r=base[i]*dual[i]*(8*lit[i])
        elif m.family==1:r=mix(mix(m.const1[i],m.const0[i],dual[i]),1,base[3])*base[i]*(4*lit[i])
        else:r=mix(m.const0[i],base[i],base[3])*(4*lit[i])+(dual[i] if mask<m.glow_params[0] else 0)
        rgb.append(mix(m.fog_color[i],r,clamp(m.fog_params[3]*(m.fog_params[2]-fog))))
    alpha=m.const0[3]*(base[3]*dual[3] if m.family==0 else (dual[3] if m.family==1 else 1))
    return (*rgb,alpha),not alpha>m.alpha_ref

def normalize(v):
    length=math.sqrt(sum(x*x for x in v));assert length>0
    return [x/length for x in v]
def vertex(d,v):
    def mul(m,v,w,n):return [sum(m[i+4*j]*v[j] for j in range(3))+m[i+12]*w for i in range(n)]
    m=d.material;p=mul(d.model_view,v.position,1,3);n=normalize(mul(d.model_view,v.normal,0,3));clip=mul(d.projection,p,1,4);fog=math.sqrt(sum(x*x for x in p)+1e-16);ndl=sum(n[i]*m.light[i] for i in range(3))
    if m.lighting==0:lit=list(v.color)
    elif m.lighting==1:lit=[clamp(ndl)*m.diffuse[i]+m.ambient[i] for i in range(4)]
    else:
        view=normalize([-x for x in p]);half=normalize([m.light[i]+view[i] for i in range(3)]);spec=clamp(sum(n[i]*half[i] for i in range(3)))**m.shininess
        lit=[(clamp(ndl*m.diffuse[i])+m.ambient[i])*v.color[i]+spec*m.specular[i] for i in range(3)]+[v.color[3]]
    return clip,n,lit,fog
