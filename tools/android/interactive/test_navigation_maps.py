"""The navigation map pack: only passed map jobs, checked as the guest checks them, in the asset pack's volume format.

Owner, 2026-11-09: a navigation map for every zone, reaching the phone as a separate
pack to import, like the asset pack. The volume is imported here by the shipped Java
AssetPackArchive, as the app does.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import unittest.mock
import zipfile
import package_navigation_maps as pack
import test_zone_beacons as fixtures

MAP_ID, NAMES, HEAD = fixtures.MAP_ID, fixtures.NAMES, 'a' * 40
ROOT = Path(__file__).resolve().parents[3]
ARCHIVE_SOURCE = ROOT / 'android/app/src/main/java/io/github/russianranger/cohdiagnostic/AssetPackArchive.java'
def run_folder(root, run_id, *, conclusion='success', graph=b'complete native graph fixture', workflow=pack.WORKFLOW):
    folder = Path(root) / str(run_id); artifact = folder / ('coh-zone-beacons-%d' % MAP_ID)
    artifact.mkdir(parents=True)
    fixtures.complete_package(artifact, graph=graph)
    (folder / 'run.json').write_text(json.dumps({'id': run_id, 'path': workflow, 'status': 'completed',
                                                 'conclusion': 'failure', 'head_sha': HEAD}))
    (folder / 'jobs.json').write_text(json.dumps({'jobs': [
        {'id': 1, 'name': 'plan', 'conclusion': 'success'}, {'id': 2, 'name': 'generator', 'conclusion': 'success'},
        {'id': run_id * 10, 'name': 'beacons (%d)' % MAP_ID, 'conclusion': conclusion},
        {'id': run_id * 10 + 1, 'name': 'beacons (72)', 'conclusion': 'failure'}]}))
    return folder


class NavigationMapPackTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name); self.runs = self.root / 'runs'

    def build(self, order, version='1.0.0'):
        output = self.root / ('out-' + '-'.join(map(str, order)) + '-' + version)
        return pack.build(self.runs, order, output, version), output

    def test_a_passed_map_becomes_one_verified_volume(self):
        run_folder(self.runs, 1001)
        report, output = self.build([1001])
        descriptor = json.loads((output / pack.DESCRIPTOR).read_bytes())
        archive, manifest = 'runtime/' + NAMES['archive'], 'runtime/' + NAMES['manifest']
        self.assertEqual((descriptor['id'], descriptor['version'], sorted(descriptor['files'])),
                         ('coh-navigation-maps', '1.0.0', sorted([archive, manifest])))
        self.assertEqual(descriptor['volumes'], {'maps': sorted([archive, manifest])})
        volume = output / 'COH-Navigation-Maps-1.0.0.zip'
        pack.verify_volume(volume, descriptor, 'maps')
        self.assertEqual(report['volumes']['COH-Navigation-Maps-1.0.0.zip']['sha256'],
                         hashlib.sha256(volume.read_bytes()).hexdigest())
        self.assertEqual((output / 'COH-Navigation-Maps-1.0.0.zip.sha256').read_text().split()[0],
                         report['volumes']['COH-Navigation-Maps-1.0.0.zip']['sha256'])
        self.assertEqual((report['map_count'], report['maps']['71']['run_id'], report['maps']['71']['job_id']), (1, 1001, 10010))
        self.assertEqual(len(report['maps_without_graph']), 63)
        self.assertNotIn(71, report['maps_without_graph'])
        with zipfile.ZipFile(volume) as archive_zip:
            self.assertEqual(archive_zip.namelist(), [pack.MANIFEST] + ['payloads/' + n for n in sorted([archive, manifest])])
            self.assertEqual(archive_zip.read('payloads/' + archive), (self.runs / '1001/coh-zone-beacons-71' / NAMES['archive']).read_bytes())

    def test_a_failed_map_job_is_never_packed(self):
        run_folder(self.runs, 1001, conclusion='failure')
        with self.assertRaisesRegex(ValueError, 'No passed map'):
            self.build([1001])

    def test_a_later_run_replaces_an_earlier_map(self):
        run_folder(self.runs, 1001); run_folder(self.runs, 1002, graph=b'regenerated native graph fixture')
        report, output = self.build([1001, 1002])
        self.assertEqual(report['maps']['71']['run_id'], 1002)
        report, output = self.build([1002, 1001], version='1.0.1')
        self.assertEqual(report['maps']['71']['run_id'], 1001)

    def test_tampered_or_foreign_artifacts_are_refused(self):
        folder = run_folder(self.runs, 1001)
        artifact = folder / 'coh-zone-beacons-71'
        (artifact / 'extra.txt').write_text('x')
        with self.assertRaisesRegex(ValueError, 'Incomplete or extra'):
            self.build([1001])
        (artifact / 'extra.txt').unlink()
        with zipfile.ZipFile(artifact / NAMES['archive'], 'a') as archive:
            archive.writestr('extra.bcn', b'x')
        with self.assertRaises(ValueError):
            self.build([1001])
        shutil.rmtree(self.runs); run_folder(self.runs, 1001, workflow='.github/workflows/other.yml')
        with self.assertRaisesRegex(ValueError, 'not a completed zone graph run'):
            self.build([1001])
        shutil.rmtree(self.runs); folder = run_folder(self.runs, 1001)
        run = json.loads((folder / 'run.json').read_bytes()); run['head_sha'] = 'b' * 40
        (folder / 'run.json').write_text(json.dumps(run))
        with self.assertRaisesRegex(ValueError, 'does not match its own generation job'):
            self.build([1001])

    def test_large_packs_split_into_numbered_parts(self):
        files = {'runtime/zone-beacons-%d.zip' % m: {'bytes': 700, 'sha256': '0' * 64} for m in (3, 4, 6)}
        with unittest.mock.patch.object(pack, 'VOLUME_BUDGET', 1500):
            volumes = pack.plan_volumes(files)
        self.assertEqual(sorted(volumes), ['maps-1', 'maps-2'])
        self.assertEqual(sum(len(v) for v in volumes.values()), 3)
        self.assertEqual(pack.volume_filename('1.0.0', 'maps-2'), 'COH-Navigation-Maps-1.0.0-Part-2.zip')
        self.assertEqual(pack.volume_filename('1.0.0', 'maps'), 'COH-Navigation-Maps-1.0.0.zip')

    def test_descriptor_names_only_zone_graph_files(self):
        good = {'format': 1, 'id': 'coh-navigation-maps', 'version': '1.0.0',
                'files': {'runtime/' + NAMES['archive']: {'bytes': 1, 'sha256': '0' * 64},
                          'runtime/' + NAMES['manifest']: {'bytes': 1, 'sha256': '1' * 64}},
                'volumes': {'maps': sorted(['runtime/' + NAMES['archive'], 'runtime/' + NAMES['manifest']])}}
        pack.validate_descriptor(good)
        for change in (lambda v: v.update(id='coh-assets'),
                       lambda v: v['files'].update({'runtime/client-caches.zip': {'bytes': 1, 'sha256': '2' * 64}}),
                       lambda v: v['files'].pop('runtime/' + NAMES['manifest']),
                       lambda v: v.update(volumes={'base': v['volumes']['maps']})):
            value = json.loads(json.dumps(good)); change(value)
            if 'runtime/' + NAMES['manifest'] not in value['files']:
                value['volumes'] = {'maps': ['runtime/' + NAMES['archive']]}
            with self.subTest(value=value), self.assertRaises(ValueError):
                pack.validate_descriptor(value)

    @unittest.skipUnless(shutil.which('javac') and shutil.which('java'), 'A JDK runs the shipped Java importer')
    def test_the_apps_own_importer_accepts_the_volume(self):
        run_folder(self.runs, 1001)
        report, output = self.build([1001])
        descriptor = json.loads((output / pack.DESCRIPTOR).read_bytes())
        work = self.root / 'java'; (work / 'src').mkdir(parents=True)
        host = (work / 'src/NavigationPackHost.java')
        host.write_text(r'''
package io.github.russianranger.cohdiagnostic;
import java.io.*;
import java.nio.file.*;
import java.util.*;
public final class NavigationPackHost {
    public static void main(String[] args)throws Exception {
        File root=new File(args[0]);
        Map<String,AssetPackArchive.Pin> pins=new TreeMap<>();Map<String,Set<String>> volumes=new TreeMap<>();
        for(String row:Files.readAllLines(new File(root,"pins.tsv").toPath())) {
            String[] f=row.split("\t");pins.put(f[0],new AssetPackArchive.Pin(Long.parseLong(f[1]),f[2]));
            volumes.computeIfAbsent(f[3],k->new TreeSet<>()).add(f[0]);
        }
        AssetPackArchive.Io io=new AssetPackArchive.Io(){public void before(){}public void read(long n){}
            public void written(long n,AssetPackArchive.Sync s)throws IOException{s.sync();}public void synced(){}};
        AssetPackArchive archive=new AssetPackArchive(new File(root,"store"),Files.readAllBytes(new File(args[1]).toPath()),
            pins,volumes,()->{},io,(p,d,t)->{},f->100L<<30);
        if(archive.isAccepted())throw new AssertionError("accepted before import");
        String volume=archive.importVolume(new FileInputStream(args[2]));
        System.out.println(volume+" "+archive.isAccepted()+" "+archive.missingVolumes()+" "+archive.resolve(args[3]).length());
    }
}
''')
        (work / 'pins.tsv').write_text(''.join('%s\t%d\t%s\t%s\n' % (name, row['bytes'], row['sha256'],
                                       next(v for v, members in descriptor['volumes'].items() if name in members))
                                       for name, row in descriptor['files'].items()))
        classes = work / 'classes'; classes.mkdir()
        subprocess.run(['javac', '-d', str(classes), str(ARCHIVE_SOURCE), str(host)], check=True, capture_output=True)
        archive_name = 'runtime/' + NAMES['archive']
        result = subprocess.run(['java', '-cp', str(classes), 'io.github.russianranger.cohdiagnostic.NavigationPackHost',
                                 str(work), str(output / pack.DESCRIPTOR), str(output / 'COH-Navigation-Maps-1.0.0.zip'),
                                 archive_name], check=True, capture_output=True, text=True)
        self.assertEqual(result.stdout.split(), ['maps', 'true', '[]', str(descriptor['files'][archive_name]['bytes'])])


if __name__ == '__main__':
    unittest.main()
