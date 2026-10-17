"""Bounded independent format projection; no native layout or gameplay values."""
import struct
def decode(raw,tables):
 at=0;texts=[];entries=[];mods=[];scalar=0;array=0
 def word():
  nonlocal at
  assert at+4<=len(raw);v=struct.unpack_from('<I',raw,at)[0];at+=4;return v
 def string():
  nonlocal at
  assert at+2<=len(raw);n=struct.unpack_from('<H',raw,at)[0];at+=2;assert n<260 and at+n<=len(raw);s=raw[at:at+n];assert b'\0'not in s;at+=n;at+=(4-(n+2)%4)%4;return s
 def record(table,owner,row,depth):
  nonlocal at,scalar,array
  assert depth<=3;begin=at;end=at+4+struct.unpack_from('<I',raw,at)[0];word();assert end<=len(raw);mod=None
  if table==1:
   assert owner==len(entries);entries.append({'record':[begin,end],'fields':[],'name_text':0})
  if table==4:mod={'record':[begin,end],'owner':owner,'row':row,'name_text':0};mods.append(mod)
  for f,field in enumerate(tables[table]):
   start=at;k=field['kind'];n=1
   if k in(2,3,5,6):n=word()
   if k in(1,2):
    for element in range(n):
     s=string();ti=len(texts);texts.append({'owner':owner,'table':table,'row':row,'field':f,'element':element,'text':s.decode('ascii')})
     if table==1 and f==0:entries[owner]['name_text']=ti
     if mod is not None and f==0:mod['name_text']=ti
   elif k==3:
    assert n<=4096
    for _ in range(n):word();array+=1
   elif k==4:word();scalar+=1
   elif k==5:
    assert n<=(64 if field['sub']==1 else 4096 if field['sub']==4 else 128)
    for i in range(n):record(field['sub'],i if field['sub']==1 else owner,i,depth+1)
   elif k==6:assert at+n<=len(raw);at+=n
   else:assert False
   if table==1:entries[owner]['fields'].append([start,at])
   assert at<=end
  assert at==end
 assert raw[:8]==b'CrypticS';at=8;crc=word();assert string()==b'Parse6'and string()==b'Files1';files_end=at+4+struct.unpack_from('<I',raw,at)[0];word();deps=word()
 for _ in range(deps):string();word()
 assert at==files_end;begin=at;record(0,0,0,0);assert at==len(raw)
 return {'begin':begin,'header_crc':crc,'dependencies':deps,'scalar_words':scalar,'array_words':array,'entries':entries,'texts':texts,'modtables':mods}
def serialize(d):
 out=bytearray()
 def words(*v):out.extend(struct.pack('<'+'I'*len(v),*v))
 words(len(d['entries']),len(d['texts']),len(d['modtables']),d['dependencies']);out.extend(struct.pack('<QQ',d['scalar_words'],d['array_words']))
 for e in d['entries']:
  words(*e['record'],e['name_text'])
  for field in e['fields']:words(*field)
 for t in d['texts']:
  b=t['text'].encode();words(t['owner'],t['table'],t['row'],t['field'],t['element'],len(b));out.extend(b)
 for m in d['modtables']:words(*m['record'],m['owner'],m['row'],m['name_text'])
 return bytes(out)
