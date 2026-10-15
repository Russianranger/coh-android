"""Read selected authentic definition blocks, preserving values and source hashes.
Only a test corpus importer; runtime consumes parsed data through its public API.
"""
import hashlib,json,re,shlex

def sha(p):return hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
def block(text,start):
 opening=text.index('{',start);depth=1;i=opening+1
 while depth:
  if text[i]=='{':depth+=1
  elif text[i]=='}':depth-=1
  i+=1
 return text[opening+1:i-1]
def fields(text):
 out={}
 for line in text.splitlines():
  line=line.split('//')[0].strip()
  if not line or line.startswith(('#','{','}')):continue
  words=shlex.split(line.replace(',',' '))
  if len(words)>1:out[words[0].lower()]=words[1:]
 return out

def load(root):
 data=root/'upstream/i24/data';source=root/'upstream/ouroboros'
 bones=(source/'Common/seq/bones.h').read_text();bones=bones[bones.index('typedef enum BoneId'):]
 names=re.findall(r'\bBONEID_([A-Z0-9_]+)\s*,',bones);names=names[:names.index('COUNT')];ids={name:i for i,name in enumerate(names)}
 bp=data/'defs/ui/bodyparts.bp';text=bp.read_text();definitions=[]
 for match in re.finditer(r'(?m)^BodyPart\s*$',text):
  end=text.index('\nEnd',match.end());record=fields(text[match.end():end]);count=int(record['bonecount'][0]);name=record['geoname'][0]
  sockets=[ids.get((name+suffix).upper(),-1) for suffix in (['R','L'] if count==2 else [''])]
  sockets=[i if i>=0 else 0xffffffff for i in sockets]
  definitions.append({'name':record['name'][0],'geometry_name':name,'texture_name':record['texname'][0],'base_name':record['basename'][0],'sockets':sockets})
 lookup={d['name'].lower():i for i,d in enumerate(definitions)}
 choices=[('defs/npc/contacts_atlas.nd','Model_Aaron_Thiery_NoRing',0),('defs/villaincostume/i23_unique_costumes.nd','Model_Nightward_BurningBody_Talon',1),('defs/v_villain_costumes/v_arachnos_henchmen.nd','Arachnos_Archetype_03',4),('defs/v_villain_costumes/v_arachnos_henchmen.nd','Arachnos_Wretch',4)]
 costumes=[];paths=[bp,source/'Common/seq/bones.h',source/'Common/entity/costume.h',source/'Common/entity/costume.c',source/'Game/src/entity/costume_client.c',source/'Common/seq/anim.c']
 for relative,name,body in choices:
  path=data/relative;raw=path.read_text();match=re.search(r'NPC\s+"'+re.escape(name)+r'"\s*\{',raw);assert match,name
  npc=block(raw,match.start());costume=block(npc,re.search(r'\bCostume\s*\{',npc).start());f=fields(costume[:costume.find('CostumePart')]);parts=[]
  for m in re.finditer(r'CostumePart\s+([^\s{]+)\s*\{',costume):
   part=fields(block(costume,m.start()));pname=m[1].strip('"');cols=[]
   for i in range(4):
    col=[int(x) for x in part.get('color'+str(i+1),['0','0','0'])];cols.append(col+[255])
   parts.append({'definition':lookup[pname.lower()],'geometry':part.get('geometry',[None])[0],'textures':[part.get('texture1',['None'])[0],part.get('texture2',['None'])[0]],'colors':cols})
  costumes.append({'name':name,'body':body,'ent_type':f.get('enttypefile',[None])[0],'prefix':f.get('costumefileprefix',[None])[0],'skin':[int(x) for x in f.get('skincolor',['0','0','0'])]+[255],'parts':parts,'source':str(path.relative_to(root)),'source_sha256_lf':sha(path)})
  paths.append(path)
 return {'definitions':definitions,'costumes':costumes,'source_pins':{str(p.relative_to(root)):sha(p) for p in paths}}
