#!/usr/bin/env python3
"""Offline screenshot bounds for the fixed neutral Male inspection mode.

Checks actual raster pixels, masking only the known top status/target HUD.
Original-client material/visual parity still requires human inspection.
"""
from pathlib import Path
import argparse,hashlib,json,math
from PIL import Image

def verify_preview_image(image_path,report):
 area=report['input_area'];preview=report['native']['appearance_preview']
 if report['support']['presentation']['visible']:raise ValueError('Presentation panel must be closed for costume image qualification')
 if not (preview['available'] and preview['active'] and preview['body']=='Male' and preview['parts']==8):
  raise ValueError('Screenshot is not an active complete Male preview report')
 x,y,w,h=(area[k] for k in ('left','top','width','height'))
 if any(type(v) is not int for v in (x,y,w,h)) or min(x,y)<0 or min(w,h)<128:raise ValueError('Invalid reported scene rectangle')
 with Image.open(image_path) as original:
  if x+w>original.width or y+h>original.height:raise ValueError('Scene rectangle exceeds screenshot')
  screenshot_size=list(original.size);scene=original.convert('RGB').crop((x,y,x+w,y+h))
 colors=scene.getcolors(w*h)
 if not colors:raise ValueError('Scene colors exceed finite raster bound')
 background=max(colors,key=lambda pair:pair[0])[1]
 scale=min(w/1024,h/768);ox=(w-1024*scale)/2;oy=(h-768*scale)/2
 exclusions=[]
 for bx,by,bw,bh in [(12,12,310,102),(656,12,356,90)]:
  exclusions.append((math.floor(ox+bx*scale)-3,math.floor(oy+by*scale)-3,math.ceil(ox+(bx+bw)*scale)+3,math.ceil(oy+(by+bh)*scale)+3))
 pixels=scene.load();lowx=w;lowy=h;highx=highy=-1;count=0
 for py in range(h):
  for px in range(w):
   if any(a<=px<b and c<=py<d for a,c,b,d in exclusions):continue
   color=pixels[px,py]
   if sum(abs(color[k]-background[k]) for k in range(3))<=20:continue
   lowx=min(lowx,px);highx=max(highx,px);lowy=min(lowy,py);highy=max(highy,py);count+=1
 if not count:raise ValueError('Male screenshot has no visible silhouette')
 bounds=[lowx/w,lowy/h,(highx+1)/w,(highy+1)/h];extent=[bounds[2]-bounds[0],bounds[3]-bounds[1]];fraction=count/(w*h)
 errors=[]
 if min(bounds[0],bounds[1],1-bounds[2],1-bounds[3])<.08:errors.append('silhouette touches reserved outer margin/cropped body or HUD obstruction')
 if extent[0]<.08 or extent[1]<.35:errors.append('insufficient full-body silhouette extent')
 if abs((bounds[0]+bounds[2])/2-.5)>.07 or abs((bounds[1]+bounds[3])/2-.5)>.10:errors.append('silhouette is not centered in the inspection viewport')
 if not .008<=fraction<=.40:errors.append('silhouette visible-pixel fraction outside bounded preview range')
 return {'schema':'coh-support-neutral-preview-image-v1','passed':not errors,'image':Path(image_path).name,'image_sha256':hashlib.sha256(Path(image_path).read_bytes()).hexdigest(),'screenshot_size':screenshot_size,'scene_rectangle':[x,y,w,h],'background_rgb':list(background),'excluded_top_hud_rectangles':exclusions,'visible_pixels':count,'visible_fraction':fraction,'bounds_normalized':bounds,'extent_normalized':extent,'required_minimum_margin':.08,'errors':errors,'scope':'Actual screenshot silhouette/framing check with only two top HUD exclusions; not original-client pixel equivalence or physical acceptance.'}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--image',type=Path,required=True);p.add_argument('--report',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 result=verify_preview_image(a.image,json.loads(a.report.read_text()));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
