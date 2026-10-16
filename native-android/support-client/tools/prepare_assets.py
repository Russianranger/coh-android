#!/usr/bin/env python3
"""Prepare the isolated offline Support Client from authenticated external inputs.

No binary inputs belong in Git. The accepted APK and its seven native assets are
immutable; optional new authentic animations/font/audio are separately identified.
Whole archive SHA values are provenance: bounded member acquisition verifies each
selected size/SHA/ZIP CRC and does not claim to hash an entire release archive.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile

APK_SHA = '75ff158c3e1387671ff2a47f0aa6a126b9c93389fd16685d78a9fcf4ed164639'
ACCEPTED = {
 'character.bin': (4261100, '59dae233f6a6b980f134be71b1ef6d7d112fca46f49b01468f932787fbe33ea7'),
 'locomotion.bin': (147103, '8c42bd6c72223ec0d32519143fe90fa23f9528006ed914659ae44f78592b63d7'),
 'map.bin': (161654, '1b7141f49387d7f37fecda62f7241363aea150e021cfba9bf66a996a3dd22a7f'),
 'morph.bin': (3028, 'ceba092c4e80fa9945cecb08fc438e28e69786253c4638512549baf7af021e02'),
 'rig.bin': (11642, '2b1e862dc61744d51d568f05f54ee1a0ce723ba7529c55adb7e373d2c42b8dd5'),
 'walkable.bin': (605048, 'e69fe7339d3207208627f612c2c1b6d742515c5d8b48db46a6c1b88f99f53357'),
 'world.bin': (102176, '7289eb3a4478648dcefce682121ccd0448aee6a21a7c4977ffd6415dd11ece6f'),
}
CLIPS = [('1_2punch', 'punch.bin'), ('jump_n_smash', 'jump.bin'), ('fallout', 'fall.bin')]
AUDIO = {'atlasplaza.ogg': ('music.ogg', 256209, '1a9f7ee21bc425508eb2e4a17c6ac66c04059ee6f0b0e4d0517ba3e1095c7bf7'),
         'steam1.ogg': ('ambient.ogg', 42318, '176bfd08df6a17af558157ad1934d23c92aaaa81d7428e2e04d1250cfa0c6821')}


def require(value, message):
 if not value:
  raise ValueError(message)


def digest(data):
 return hashlib.sha256(data).hexdigest()


def checked(data, size, expected, label):
 require(len(data) == size and digest(data) == expected, label + ' size/SHA256 differs')
 return data


def load_module(name, path):
 spec = importlib.util.spec_from_file_location(name, path)
 result = importlib.util.module_from_spec(spec)
 spec.loader.exec_module(result)
 return result


def read_local(directory, virtual):
 if directory is None:
  return None
 path = Path(virtual)
 for candidate in [directory / path, directory / path.name,
                   directory / path.parent.name / path.name]:
  if candidate.is_file():
   return candidate.read_bytes()
 return None


def canonical(prep, raw, expected_base, expected_clip):
 """Validate every prebuilt rig byte, including both original raw source spans."""
 require(len(raw) >= 128 and raw[:8] == b'COHRIG01', 'Prebuilt family rig signature differs')
 bo, bn, mo, mn = struct.unpack_from('<4I', raw, 16)
 require(bo == 128 and mo == bo + bn and bo + bn <= len(raw) and mo + mn <= len(raw), 'Prebuilt raw spans differ')
 base = checked(raw[bo:bo+bn], expected_base['size'], expected_base['sha256'], 'Huge base')
 motion = checked(raw[mo:mo+mn], expected_clip['bytes'], expected_clip['sha256'], 'Huge motion')
 result, _ = make_rig(prep, base, motion)
 require(raw == result, 'Prebuilt rig canonical metadata differs')
 return raw


def make_rig(prep, base, motion):
 base_meta, _ = prep.inspect_animation(base)
 clip_meta, _ = prep.inspect_animation(motion)
 require(base_meta['name'].casefold() == 'huge/skel_ready', 'Unexpected base source identity')
 require(clip_meta['base_anim_name'].casefold() == 'huge/skel_ready', 'Motion references a different rig')
 result = bytearray(prep.make_rig(base, motion, [0], 0))
 struct.pack_into('<3f', result, 48, 1.0, clip_meta['length_frames'], 30.0)
 return bytes(result), clip_meta


class Reference:
 """One bounded original Reference ZIP reader, opened only for missing inputs."""
 def __init__(self, ranges, pins):
  self.ranges = ranges
  self.pins = pins
  self.reader = None
  self.inner = None
  self.archive = None

 def read(self, name, size):
  if self.reader is None:
   self.reader = self.ranges.HTTPRange(self.pins['outer_asset_url'], self.pins['outer_expected_bytes'], 16 << 20)
   with zipfile.ZipFile(self.reader) as outer:
    self.inner = self.ranges.subzip(self.reader, outer.getinfo(self.pins['inner_member']))
   require(self.inner.size == self.pins['inner_expected_bytes'], 'Reference inner ZIP size differs')
   self.archive = zipfile.ZipFile(self.inner)
  entry = self.archive.getinfo(name)
  require(not entry.flag_bits & 1 and entry.compress_type in (0, 8) and entry.file_size == size and size <= 8 << 20,
          'Unsafe or mismatched Reference member ' + name)
  # Python ZipExtFile validates the central/local identity, deflate and CRC.
  data = self.archive.read(entry)
  require(len(data) == size, 'Truncated Reference member')
  return data

 def report(self):
  return {'bytes_transferred': self.reader.total if self.reader else 0,
          'ranges': self.reader.requests if self.reader else [],
          'etag': self.reader.etag if self.reader else None,
          'whole_outer_hash_verified': False, 'whole_inner_hash_verified': False,
          'strict_http206': True, 'member_crc_verified_when_acquired': True}

 def close(self):
  if self.archive is not None:
   self.archive.close()


def main():
 parser = argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--source-root', type=Path, default=Path('.'))
 parser.add_argument('--accepted-apk', type=Path, required=True)
 parser.add_argument('--output', type=Path, default=Path('native-android/support-client/assets'))
 parser.add_argument('--evidence-output', type=Path, default=Path('results/support-client'))
 parser.add_argument('--generated', type=Path)
 parser.add_argument('--extra-corpus', type=Path)
 parser.add_argument('--family-dir', type=Path)
 parser.add_argument('--audio-dir', type=Path)
 parser.add_argument('--font-ttf', type=Path)
 parser.add_argument('--appearance-package',type=Path,help='Optional exact pinned prebuilt neutral Male fixture')
 args = parser.parse_args()
 root = args.source_root.resolve()
 native = root / 'native-android'
 output = args.output.resolve()
 evidence = args.evidence_output.resolve()
 generated = args.generated.resolve() if args.generated else output.parent / 'generated'
 apk_raw = args.accepted_apk.read_bytes()
 require(digest(apk_raw) == APK_SHA, 'Accepted 0.3.0 APK SHA256 differs; no files prepared')
 payload = {}
 with zipfile.ZipFile(args.accepted_apk) as apk:
  manifest_raw = apk.read('assets/asset-manifest.json')
  manifest = json.loads(manifest_raw)
  require(manifest.get('schema') == 1 and set(manifest['assets']) == set(ACCEPTED), 'Accepted manifest schema/asset set differs')
  for name, (size, sha) in ACCEPTED.items():
   require(manifest['assets'][name] == {'bytes': size, 'sha256': sha}, 'Accepted manifest pin differs: ' + name)
   payload[name] = checked(apk.read('assets/' + name), size, sha, 'Accepted ' + name)
  payload['asset-manifest.json'] = manifest_raw
 reference_pins = json.loads((native / 'tools/animation_fixture/pins.json').read_text())
 original_base = next(r for r in reference_pins['records'] if r['name'].endswith('/huge/skel_ready.anim'))
 extra_pins = json.loads((native / 'engine/sequencer/continuation/extra-asset-pins.json').read_text())
 font_pins = json.loads((native / 'engine/ui/gameplay/docs/font-provenance.json').read_text())
 original_font = next(r for r in font_pins['records'] if r['name'] == 'assets/fonts/mont_hvbold.ttf')
 require(font_pins['outer_asset_url'] == reference_pins['outer_asset_url'], 'Font/animation source releases differ')
 ranges = load_module('support_ranges', native / 'tools/animation_fixture/acquire.py')
 prep = load_module('support_prepare_rig', native / 'tools/animation_fixture/prepare.py')
 atlas = load_module('support_make_atlas', native / 'engine/ui/gameplay/make_atlas.py')
 reference = Reference(ranges, reference_pins)
 evidence.mkdir(parents=True, exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='coh-support-prepare-') as temporary:
  temp = Path(temporary)
  clips = []
  try:
   base = None
   for clip, destination in CLIPS:
    pin = extra_pins['huge/' + clip]
    prebuilt = read_local(args.family_dir, 'huge-' + clip + '.bin')
    if prebuilt is not None:
     raw = canonical(prep, prebuilt, original_base, pin)
    else:
     if base is None:
      base = read_local(args.extra_corpus, original_base['name'])
      if base is None:
       base = reference.read(original_base['name'], original_base['size'])
      base = checked(base, original_base['size'], original_base['sha256'], 'Huge base')
     name = 'assets/player_library/animations/huge/' + clip + '.anim'
     motion = read_local(args.extra_corpus, name)
     if motion is None:
      motion = reference.read(name, pin['bytes'])
     motion = checked(motion, pin['bytes'], pin['sha256'], name)
     raw, metadata = make_rig(prep, base, motion)
    payload[destination] = raw
    clips.append({'asset': 'huge/' + clip, 'output': destination, 'bytes': len(raw), 'sha256': digest(raw),
                  'canonical': 'COHRIG01', 'source_raw_sha256': pin['sha256'], 'prebuilt_verified': prebuilt is not None})
   font = args.font_ttf.read_bytes() if args.font_ttf else read_local(args.extra_corpus, original_font['name'])
   if font is None:
    font = reference.read(original_font['name'], original_font['size'])
   checked(font, original_font['size'], original_font['sha256'], 'Original mont_hvbold.ttf')
   font_path = temp / 'mont_hvbold.ttf'
   font_path.write_bytes(font)
   atlas_dir = temp / 'font'
   font_report = atlas.build(font_path, atlas_dir, size=16, resource=7, font_id=1, prefix='coh_hud_font', nohint=True)
   audio_dir = args.audio_dir
   audio_acquisition = None
   if audio_dir is None or not all((audio_dir / name).is_file() for name in AUDIO):
    audio_dir = temp / 'audio'
    command = [sys.executable, str(native / 'engine/audio/android-integration/acquire.py'), '--output', str(audio_dir)]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    audio_acquisition = json.loads((audio_dir / 'corpus.json').read_text())
   for name, (destination, size, sha) in AUDIO.items():
    payload[destination] = checked((audio_dir / name).read_bytes(), size, sha, 'Original ' + name)
   appearance_package=args.appearance_package
   appearance_provenance={'scope':'Exact pinned complete neutral Male package; source provenance in appearance actor manifest.'}
   if appearance_package is not None and (appearance_package.parent/'actor.json').is_file():
    appearance_provenance=json.loads((appearance_package.parent/'actor.json').read_text())
   if appearance_package is None:
    appearance_dir=temp/'appearance'
    subprocess.run([sys.executable,str(native/'engine/appearance/prepare_actor.py'),'--source-root',str(root),'--output',str(appearance_dir)],check=True,capture_output=True,text=True)
    appearance_package=appearance_dir/'appearance-male.bin'
    appearance_provenance=json.loads((appearance_dir/'actor.json').read_text())
   appearance_raw=checked(appearance_package.read_bytes(),1673302,'bda4a9f1098281d3ddc32842aeda792e83cebb0be3185d9458e3402032f77df9','Complete neutral Male fixture')
   payload['appearance-male.bin']=appearance_raw
   prepared = {'schema': 'coh-native-support-assets-v1', 'accepted_apk_sha256': APK_SHA,
               'assets': {name: {'bytes': len(raw), 'sha256': digest(raw)} for name, raw in sorted(payload.items())},
               'scope': 'Accepted offline assets plus authentic neutral Male costume, raw Huge clip diagnostics and original-font/audio preparation; no new gate/device acceptance.'}
   # Publish only after every input and derived output has been admitted.
   output.mkdir(parents=True, exist_ok=True)
   generated.mkdir(parents=True, exist_ok=True)
   for name, raw in payload.items():
    stage = output / (name + '.preparing')
    stage.write_bytes(raw)
    os.replace(stage, output / name)
   (output / 'support-asset-manifest.json').write_text(json.dumps(prepared, indent=2) + '\n')
   shutil.copyfile(atlas_dir / 'atlas.h', generated / 'support_font.h')
   font_evidence = evidence / 'font'
   font_evidence.mkdir(parents=True, exist_ok=True)
   for name in ['atlas.png', 'atlas.alpha', 'atlas.json']:
    shutil.copyfile(atlas_dir / name, font_evidence / name)
   result = {'schema': 'coh-native-support-preparation-v1', 'passed': True, 'source_root': str(root),
             'accepted_apk': str(args.accepted_apk.resolve()), 'accepted_apk_sha256': APK_SHA,
             'accepted_asset_pins_verified': 7, 'output': str(output), 'generated': str(generated),
             'assets': prepared['assets'], 'clips': clips, 'reference_acquisition': reference.report(),
             'font': font_report, 'font_header_sha256': digest((generated / 'support_font.h').read_bytes()),
             'audio_acquisition': audio_acquisition, 'appearance':appearance_provenance,
             'appearance_package_sha256':digest(appearance_raw),'physical_qualification': False,
             'limitations': ['Preparation validates identity and canonical envelopes; runtime, GPU, audio and Thor acceptance are separate.',
                             'Font rasterization uses host FreeType with source NOHINT policy; host FreeType versions may change generated mask bytes.',
                             'No whole Reference or Audio archive SHA was computed from partial ranges.']}
   (evidence / 'preparation.json').write_text(json.dumps(result, indent=2) + '\n')
   print(json.dumps({'passed': True, 'accepted_assets': 7, 'new_rigs': 3, 'audio_assets': 2,
                     'font_header': str(generated / 'support_font.h'), 'reference_network_bytes': reference.report()['bytes_transferred'],
                     'evidence': str(evidence / 'preparation.json')}))
  finally:
   reference.close()


if __name__ == '__main__':
 main()
