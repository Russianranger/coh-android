"""Bounded independent Parse6 attribute schema decoder, original slot order."""
import struct
class Reader:
 def __init__(self,data):self.data=data;self.at=0
 def take(self,n):
  if n<0 or n>len(self.data)-self.at:raise ValueError('truncated')
  out=self.data[self.at:self.at+n];self.at+=n;return out
 def word(self):return struct.unpack('<I',self.take(4))[0]
 def segment(self):
  n=self.word()
  if n>len(self.data)-self.at:raise ValueError('segment')
  return self.at+n
 def text(self):
  n=struct.unpack('<H',self.take(2))[0]
  if n>=260:raise ValueError('text limit')
  out=self.take(n)
  if b'\0'in out:raise ValueError('embedded NUL')
  self.take((-n-2)%4);return out.decode('ascii')
 def end(self,end):
  if self.at!=end:raise ValueError('wrong segment end')
def decode(data):
 if not data or len(data)>65536:raise ValueError('input bound')
 r=Reader(data)
 if r.take(8)!=b'CrypticS':raise ValueError('magic')
 crc=r.word()
 if crc!=0x315acdb1:raise ValueError('crc')
 if (r.text(),r.text())!=('Parse6','Files1'):raise ValueError('signature')
 end=r.segment();count=r.word()
 if count>64:raise ValueError('dependency bound')
 dependencies=[(r.text(),r.word())for _ in range(count)];r.end(end)
 root=r.segment()
 if root!=len(data):raise ValueError('root')
 count=r.word()
 if count>32:raise ValueError('category bound')
 rows=[]
 for cat in range(count):
  catend=r.segment();catname=r.text();n=r.word()
  if n>256-len(rows):raise ValueError('row bound')
  for j in range(n):
   rowend=r.segment();name=r.text();display=r.text();tooltip=r.text();type_,style,key,offset,show=[r.word()for _ in range(5)];r.end(rowend)
   rows.append({'category':cat,'row':j,'type':type_,'style':style,'key':key,'offset':offset,'show_base_word':show,'category_rows':n,'category_name':catname,'name':name,'display_name':display,'tooltip':tooltip,'lookup_key':(460*type_+offset)&0xffffffff})
  r.end(catend)
 r.end(root)
 return {'schema_crc':crc,'category_count':count,'row_count':len(rows),'dependencies':dependencies,'ordered_sender_rows':list(reversed(rows))}
