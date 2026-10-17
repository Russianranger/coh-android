"""Bounded streaming field decoder, independent of original TokenStore storage.

Uses the initialized original schema descriptors, with no duplicated hand-built
costume tables. Retains the input and O(depth + schema) objects only.
"""
import hashlib,struct
class Refused(ValueError):pass
def decode(raw,begin,schemas):
 if len(raw)>32*1024*1024 or begin<0 or begin>=len(raw):raise Refused('input')
 at=begin;count=[0]*8;h=hashlib.sha256()
 def word(n):h.update(struct.pack('<I',n))
 def take(n):
  nonlocal at
  if n<0 or n>len(raw)-at:raise Refused('short field')
  start=at;at+=n;return raw[start:at]
 def number(n):return int.from_bytes(take(n),'little')
 def node(table,depth):
  if depth>32 or table>=len(schemas):raise Refused('depth/table')
  size=number(4);end=at+size
  if end>len(raw):raise Refused('segment')
  count[0]+=1
  if count[0]>1000000:raise Refused('node cap')
  count[7]=max(count[7],depth);word(table)
  for col,(flags,param,child) in enumerate(schemas[table]):
   base=flags&255
   if flags&256 or base==2:continue
   n=number(4)if flags&(1<<20)else param if flags&(1<<21)else 1
   if n>65536:raise Refused('array cap')
   count[1]+=1
   if count[1]>4000000:raise Refused('field cap')
   word(col);word(flags);word(n)
   if flags&(1<<20):count[6]+=n
   for i in range(n):
    if base==29:node(child,depth+1)
    elif base in(9,13):
     length=number(2)
     if length>=12000:raise Refused('string cap')
     text=take(length);padding=take((-(length+2))%4)
     if 0 in text or any(padding):raise Refused('noncanonical text')
     absent=not length and not flags&(1<<20)
     word(0xffffffff if absent else length)
     if not absent:h.update(text)
     count[2]+=1;count[3]+=int(absent);count[4]+=int(not absent and not length)
    elif base in(5,7,20):
     word(number(1 if base==20 else 4));count[5]+=1
    else:raise Refused('unsupported actual type')
  if at!=end:raise Refused('segment equality')
 # Source table order is obtained from initialized original ParseCostumeSet.
 root=next(i for i,s in enumerate(schemas)if len(s)==1 and s[0][0]&255==29)
 node(root,0)
 if at!=len(raw):raise Refused('trailing bytes')
 return {'projection_sha256':h.hexdigest(),'counts':count,'consumed':at}
