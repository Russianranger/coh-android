#!/usr/bin/env python3
"""Exercise endpoint lease trust boundaries on the actual production Java rule."""
from pathlib import Path
import argparse,json,subprocess,tempfile
HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'app/src/main/java/org/coh/nativecombined/LeaseRules.java'
HARNESS=r'''
package org.coh.nativecombined;
public final class LeaseTest {
 static int checks;static final String s="0123456789abcdef0123456789abcdef",g="generation-"+s;
 static void check(boolean v){checks++;if(!v)throw new AssertionError("lease test "+checks);}
 static boolean ok(boolean alive,String actual,String generation,String ip,int port,long observed,long file,long now,long mono){return LeaseRules.accept(alive,s,actual,g,generation,ip,port,now,observed,file,mono);}
 public static void main(String[] args){
  check(ok(true,s,g,"127.0.0.1",7000,100000,100000,100000,3));
  check(ok(true,s,g,"127.0.0.1",7000,85000,85000,100000,3));
  check(!ok(false,s,g,"127.0.0.1",7000,100000,100000,100000,3));
  check(!ok(true,"a"+s.substring(1),g,"127.0.0.1",7000,100000,100000,100000,3));
  check(!ok(true,s,"generation-ffffffffffffffffffffffffffffffff","127.0.0.1",7000,100000,100000,100000,3));
  for(String ip:new String[]{"127.0.0.2","192.168.1.1","0.0.0.0","localhost","",null})check(!ok(true,s,g,ip,7000,100000,100000,100000,3));
  for(int p:new int[]{0,6997,7001,-1,65536})check(!ok(true,s,g,"127.0.0.1",p,100000,100000,100000,3));
  check(!ok(true,s,g,"127.0.0.1",7000,84999,100000,100000,3));
  check(!ok(true,s,g,"127.0.0.1",7000,100000,84999,100000,3));
  check(!ok(true,s,g,"127.0.0.1",7000,100001,100000,100000,3));
  check(!ok(true,s,g,"127.0.0.1",7000,100000,100001,100000,3));
  check(!ok(true,s,g,"127.0.0.1",7000,0,100000,100000,3));
  check(!ok(true,s,g,"127.0.0.1",7000,100000,100000,100000,-1));
  check(!LeaseRules.accept(true,null,s,g,g,"127.0.0.1",7000,100000,100000,100000,3));
  check(!LeaseRules.accept(true,s,s,"bad",g,"127.0.0.1",7000,100000,100000,100000,3));
  System.out.println("{\"passed\":true,\"checks\":"+checks+",\"actual_server\":false}");
 }
}
'''
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args()
 with tempfile.TemporaryDirectory(prefix='coh-lease-') as tmp:
  root=Path(tmp);test=root/'LeaseTest.java';test.write_text(HARNESS)
  subprocess.run(['java','com.sun.tools.javac.Main','-d',str(root),str(SOURCE),str(test)],check=True,capture_output=True,text=True)
  r=subprocess.run(['java','-cp',str(root),'org.coh.nativecombined.LeaseTest'],check=True,capture_output=True,text=True);q=json.loads(r.stdout)
 if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(q,indent=2)+'\n')
 print(json.dumps(q))
if __name__=='__main__':main()
