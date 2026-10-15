#!/usr/bin/env python3
"""Qualify production APK provenance without Android or JSON dependencies.

Independent Python SHA-256 expectations and a heap smaller than the largest
admitted fixture exercise exact streaming identity. This is host evidence only.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
JAVA = ROOT / 'combined-client/app/src/main/java/org/coh/nativecombined/ApkReportIdentity.java'
MAXIMUM = 25 * 1024 * 1024

HARNESS = r'''
package org.coh.nativecombined;
import java.io.File;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.math.BigDecimal;
import java.math.BigInteger;
import java.util.concurrent.atomic.AtomicInteger;
public final class ApkIdentityTest {
 static int checks;
 static final String PACKAGE="org.coh.nativecombined";
 static void need(boolean ok) { checks++; if(!ok)throw new AssertionError("Identity check "+checks); }
 static void rejected(File file) throws Exception {
  try { ApkReportIdentity.capture(file);throw new AssertionError("Unexpected identity acceptance"); }
  catch(IOException expected) {
   need(expected.getMessage().equals("APK identity unavailable"));
   need(expected.getCause()==null);
  }
 }
 static void versions() {
  need(ApkReportIdentity.sameAppReport(PACKAGE,4,PACKAGE,Integer.valueOf(4)));
  need(ApkReportIdentity.sameAppReport(PACKAGE,4,PACKAGE,Long.valueOf(4)));
  need(ApkReportIdentity.sameAppReport(PACKAGE,Long.MAX_VALUE,PACKAGE,Long.valueOf(Long.MAX_VALUE)));
  Object[] invalid={null,"4","04",Boolean.TRUE,Boolean.FALSE,Double.valueOf(4),Float.valueOf(4),
   Double.NaN,Double.POSITIVE_INFINITY,new BigInteger("4"),new BigDecimal("4"),
   new AtomicInteger(4),Byte.valueOf((byte)4),Short.valueOf((short)4),
   Integer.valueOf(0),Long.valueOf(0),Integer.valueOf(-4),Long.valueOf(Long.MIN_VALUE),
   Integer.valueOf(3),Long.valueOf(5),Long.valueOf(Long.MAX_VALUE)};
  for(Object version:invalid)need(!ApkReportIdentity.sameAppReport(PACKAGE,4,PACKAGE,version));
  Object[] packages={null,"",PACKAGE+" ",PACKAGE.toUpperCase(),new StringBuilder(PACKAGE),Integer.valueOf(4),"org.coh.nativecombined\u0000"};
  for(Object name:packages)need(!ApkReportIdentity.sameAppReport(PACKAGE,4,name,Integer.valueOf(4)));
  need(!ApkReportIdentity.sameAppReport(null,4,PACKAGE,Integer.valueOf(4)));
  need(!ApkReportIdentity.sameAppReport("",4,"",Integer.valueOf(4)));
  need(!ApkReportIdentity.sameAppReport(PACKAGE,0,PACKAGE,Integer.valueOf(0)));
  need(!ApkReportIdentity.sameAppReport(PACKAGE,-1,PACKAGE,Long.valueOf(-1)));
  need(!ApkReportIdentity.sameAppReport(PACKAGE,Long.MIN_VALUE,PACKAGE,Long.valueOf(Long.MIN_VALUE)));
 }
 public static void main(String[] args) throws Exception {
  File directory=new File(args[0]);
  versions();
  for(int i=1;i<args.length;i+=3) {
   File file=new File(directory,args[i]);long bytes=Long.parseLong(args[i+1]);String hash=args[i+2];
   ApkReportIdentity.Snapshot snapshot=ApkReportIdentity.capture(file);
   need(snapshot.bytes==bytes);need(snapshot.sha256.equals(hash));
   need(snapshot.sha256.matches("[a-f0-9]{64}"));
  }
  File abc=new File(directory,"abc");
  need(ApkReportIdentity.capture(abc).sha256.equals("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"));
  rejected(null);rejected(directory);rejected(new File(directory,"missing"));
  rejected(new File(directory,"empty"));rejected(new File(directory,"oversize"));
  rejected(new File(directory,"abc") {
   int calls;
   @Override public long lastModified(){return super.lastModified()+(calls++==0?0:1);}
  });
  rejected(new File(directory,"abc") {
   @Override public long length(){return super.length()+1;}
  });
  rejected(new File(directory,"abc") {
   @Override public boolean isFile(){throw new SecurityException("secret path");}
  });
  ApkReportIdentity.Snapshot before=ApkReportIdentity.capture(abc);
  try(RandomAccessFile writer=new RandomAccessFile(abc,"rw")){writer.seek(1);writer.write('d');}
  ApkReportIdentity.Snapshot after=ApkReportIdentity.capture(abc);
  need(before.bytes==after.bytes);need(!before.sha256.equals(after.sha256));
  need(before.sha256.equals("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"));
  System.out.println(checks);
 }
}
'''


def main():
    sizes = [1, 2, 31, 255, 65535, 65536, 65537, 1024 * 1024 + 37, MAXIMUM]
    block = bytes((i * 19 + 7) & 255 for i in range(65536))
    with tempfile.TemporaryDirectory(prefix='coh-apk-identity-') as directory:
        tmp = Path(directory)
        arguments = []
        for size in sizes:
            name = 'size-' + str(size)
            digest = hashlib.sha256()
            remaining = size
            with (tmp / name).open('wb') as output:
                while remaining:
                    chunk = block[:min(len(block), remaining)]
                    output.write(chunk)
                    digest.update(chunk)
                    remaining -= len(chunk)
            arguments.extend([name, str(size), digest.hexdigest()])
        (tmp / 'abc').write_bytes(b'abc')
        (tmp / 'empty').touch()
        # A sparse oversized fixture proves size admission without retaining a
        # byte array proportional to the declared file size.
        with (tmp / 'oversize').open('wb') as output:
            output.truncate(MAXIMUM + 1)
        harness = tmp / 'ApkIdentityTest.java'
        harness.write_text(HARNESS)
        subprocess.run(['java', 'com.sun.tools.javac.Main', '-Xlint:all', '-Werror',
                        '-d', str(tmp), str(JAVA), str(harness)],
                       check=True, capture_output=True, text=True)
        completed = subprocess.run(['java', '-Xmx16m', '-cp', str(tmp),
                                    'org.coh.nativecombined.ApkIdentityTest', str(tmp), *arguments],
                                   check=True, capture_output=True, text=True, timeout=30)
        checks = int(completed.stdout.strip())
        if checks < 80:
            raise AssertionError('Identity harness did not complete its assertions')
    print(json.dumps({'schema':'coh-apk-report-identity-host-v1', 'passed':True,
                      'checks':checks, 'independent_sha256_file_cases':len(sizes),
                      'maximum_admitted_bytes':MAXIMUM, 'java_heap_limit_bytes':16*1024*1024,
                      'streaming_large_file_verified':True,
                      'observable_mutation_rejected':True, 'path_free_errors_verified':True,
                      'strict_package_version_types_verified':True,
                      'production_sha256':hashlib.sha256(JAVA.read_bytes()).hexdigest(),
                      'scope':'Host pure Java provenance policy only; Android owner caching and report integration are separate',
                      'android_built':False, 'emulator_qualified':False, 'physical_thor_accepted':False}))


if __name__ == '__main__':
    main()
