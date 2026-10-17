"""Mechanical source-table projection; all original aliases/order retained in pin."""
import re,hashlib
TABLES=[('Common/entity/classes.h','ParseCharacterClasses'),('Common/entity/classes.h','ParseCharacterClass'),('Common/entity/character_attribs.h','ParseCharacterAttributes'),('Common/entity/character_attribs.h','ParseCharacterAttributesTable'),('Common/entity/classes.h','ParseNamedTable')]
TYPES={'STRING':1,'STRINGARRAY':2,'INTARRAY':3,'F32':4,'AUTOINT':4,'BOOL':4,'BOOLFLAG':4,'STRUCT':5,'F32ARRAY':3,'POINTER':6}
def schema(texts):
 tables=[];pins={}
 for path,name in TABLES:
  body=re.search(r'TokenizerParseInfo '+name+r'\[\]\s*=.*?\n};',texts[path],re.S).group();pins[name]=hashlib.sha256(body.encode()).hexdigest();entries=[]
  for key,value in re.findall(r'\{\s*"([^"]*)",\s*(.*?)\s*\}',body,re.S):
   if not key or 'TOK_REDUNDANTNAME'in value:continue
   m=re.search(r'\bTOK_(\w+)',value)
   if not m:raise ValueError((name,key,value))
   typ=m.group(1)
   if typ in('START','END'):continue
   sub=0
   if typ=='STRUCT':
    target=re.search(r',\s*(Parse\w+)\s*\)',value).group(1);sub=next(i for i,(_,n)in enumerate(TABLES)if n==target)
   entries.append({'name':key,'kind':TYPES[typ],'sub':sub,'source_token':typ})
  tables.append(entries)
 code='/* Generated from complete pinned original tables; no layout offsets. */\n'
 for i,entries in enumerate(tables):code+='static const Field schema_'+str(i)+'[]={'+','.join('{'+str(e['kind'])+','+str(e['sub'])+'}'for e in entries)+'};\n'
 code+='static const Schema schemas[]={'+','.join('{schema_'+str(i)+',sizeof(schema_'+str(i)+')/sizeof(schema_'+str(i)+'[0])}'for i in range(len(tables)))+'};\n'
 return tables,pins,code
