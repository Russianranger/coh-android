"""Verify overlay provenance and execute its real C mode/selection/packet guards."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

import prepare_resume_client_source as resume


class ResumeSourceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.source = Path(self.temporary.name) / 'source'
        self.source.mkdir()
        self.expected = resume.expected_resume_receipt()
        pg = self.expected['postgresql_build_input']
        for name in (*resume.RESUME_FILES, *pg['patched_sha256']):
            target = self.source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(resume.ROOT / 'upstream/ouroboros' / name, target)
        resume.apply_patch(self.source, (resume.ROOT / 'patches/postgresql/0001-dbserver-postgresql.patch')
                           .read_bytes().replace(b'\r\n', b'\n'))
        for name in pg['overlay_sha256']:
            target = self.source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(resume.ROOT / 'database/postgresql/overlay' / name, target)
        self.pg_path = self.source / 'postgresql-build-input.json'
        self.pg_path.write_text(json.dumps(pg))

    def test_real_overlay_preserves_source_and_pg_base(self):
        receipt = resume.apply_resume_overlay(self.source)
        self.assertEqual(receipt, self.expected)
        self.assertEqual(json.loads((self.source / resume.RECEIPT).read_text()), receipt)
        for name, digest in receipt['patched_sha256'].items():
            self.assertEqual(resume.sha256(self.source / name), digest)
            self.assertEqual(resume.sha256(resume.ROOT / 'upstream/ouroboros' / name),
                             receipt['source_sha256'][name])
        self.assertEqual(json.loads(self.pg_path.read_text()), receipt['postgresql_build_input'])
        self.assertEqual(receipt['runtime_validation'], 'unverified')

    def test_dirty_input_and_pg_base_fail_before_patch(self):
        for name in (resume.RESUME_FILES[0], *list(self.expected['postgresql_build_input']['patched_sha256'])[:1],
                     *list(self.expected['postgresql_build_input']['overlay_sha256'])[:1]):
            with self.subTest(name=name):
                path = self.source / name
                original = path.read_bytes()
                path.write_bytes(original + b'\n// dirty\n')
                with self.assertRaisesRegex(ValueError, 'Staged source SHA-256 mismatch'):
                    resume.apply_resume_overlay(self.source)
                path.write_bytes(original)
        self.assertFalse((self.source / resume.RECEIPT).exists())

    def test_stale_pg_receipt_rejected(self):
        pg = json.loads(self.pg_path.read_text())
        pg['source_commit'] = 'f' * 40
        self.pg_path.write_text(json.dumps(pg))
        with self.assertRaisesRegex(ValueError, 'PostgreSQL build receipt mismatch'):
            resume.apply_resume_overlay(self.source)

    def test_known_crlf_overlay_profile_preserves_actual_receipt(self):
        pg = json.loads(self.pg_path.read_text())
        for name in pg['overlay_sha256']:
            target = self.source / name
            target.write_bytes(target.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
            pg['overlay_sha256'][name] = resume.sha256(target)
        self.pg_path.write_text(json.dumps(pg))
        receipt = resume.apply_resume_overlay(self.source)
        self.assertEqual(receipt, resume.expected_resume_receipt(postgresql_build_input=pg))
        self.assertEqual(receipt['postgresql_build_input'], pg)

    def test_repeat_or_upstream_application_and_existing_output_rejected(self):
        with self.assertRaisesRegex(ValueError, 'new directory'):
            resume.prepare(self.source)
        resume.apply_resume_overlay(self.source)
        with self.assertRaisesRegex(ValueError, 'already exists'):
            resume.apply_resume_overlay(self.source)
        with self.assertRaisesRegex(ValueError, 'immutable snapshots'):
            resume.apply_resume_overlay(resume.ROOT / 'upstream/ouroboros')


@unittest.skipUnless(shutil.which('cc'), 'Narrow C behavior probe requires a C compiler')
class ResumeBehaviorTests(unittest.TestCase):
    """Compile actual changed C blocks; this is not an engine/network simulation."""
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        root = Path(cls.temporary.name)
        target = root / resume.RESUME_FILES[0]
        target.parent.mkdir(parents=True)
        shutil.copy2(resume.ROOT / 'upstream/ouroboros' / resume.RESUME_FILES[0], target)
        resume.apply_patch(root, resume.patch_bytes(resume.ROOT))
        source = target.read_text()
        helpers = source.split('static void validateResumeOnlyArgs(', 1)[1].split('#define CMDEQ(s)', 1)[0]
        helpers = 'static void validateResumeOnlyArgs(' + helpers
        selection = source.split('            gPlayerNumber = 0;\n', 1)[1].split('            if (!(g_testMode & TEST_CREATE_CHAR)', 1)[0]
        predicate = re.search(r'if \((!err && \(resume_only \|\| firstEmptySlot[^\n]+)\) \{', source).group(1)
        packet = source.split('        commSendInput();\n', 1)[1].split('        calcNetworkStats();', 1)[0]
        enum = (resume.ROOT / 'upstream/ouroboros/Utilities/TestClient/src/testClientInclude.h').read_text().split('extern TestMode g_testMode;', 1)[0]
        probe = root / 'probe.c'
        probe.write_text(r'''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#define stricmp strcasecmp
''' + enum + r'''
static int resume_only, resume_only_update_seen;
static char resume_only_name[64], character_name[256];
static int ask_user, gPlayerNumber, err;
static TestMode g_testMode = TEST_RESUME_CHAR | TEST_CREATE_CHAR | TEST_STAY_CONNECTED | TEST_LEVELUP;
static TestMode2 g_testMode2 = TEST2_LEAGUE_ACCEPT;
static MissionServerTestMode g_testModeMission = TEST_MISSIONSEARCH;
static AccountServerTestMode g_testModeAccount = TEST_ACCOUNTSERVER;
typedef struct { char name[64]; int db_id; } PlayerSlot;
// receivePlayersCommon calloc leaves db_id zero and player_count counts only
// occupied slots, whereas max_slots gives the allocated array length.
static PlayerSlot slots[] = {{"empty",0}, {"empty",0}, {"TESTHero",0}};
static struct { PlayerSlot *players; int player_count, max_slots; } db_info = { slots, 1, 3 };
typedef struct { char name[64]; int db_id; } Entity;
static Entity entity = { "TESTHero",42 };
static Entity *playerPtr(void) { return &entity; }
static void statusUpdate(const char *s) { printf("STATUS:%s\n",s); }
static void dbDisconnect(void) { printf("DB_DISCONNECT\n"); }
#define SERVER_UPDATE 71
static int simulated_packet_result;
static int commCheck(int command) { printf("COMM_CHECK:%d\n",command); return command ? simulated_packet_result : 0; }
static void entNetUpdate(void) {}
static void entClientProcess(void) {}
static void fixUpEntities(void) {}
''' + helpers + r'''
int main(int argc, char **argv) {
    int i, firstEmptySlot = 0, resume_update_result = 0;
    validateResumeOnlyArgs(argc,argv);
    for(i=1;i<argc;i++) {
        if(strcmp(argv[i],"-justlogin")==0) g_testMode=TEST_LOGIN;
        if(strcmp(argv[i],"-CREATE_CHAR")==0) g_testMode |= TEST_CREATE_CHAR;
        if(strcmp(argv[i],"-disconnect")==0) g_testMode &= ~TEST_STAY_CONNECTED;
        if(strcmp(argv[i],"-askuser")==0) ask_user=1;
        if(strcmp(argv[i],"-character")==0 && i+1<argc) strcpy(character_name,argv[++i]);
        if(strcmp(argv[i],"-no-slots")==0) { db_info.players=NULL; db_info.player_count=0; db_info.max_slots=0; }
        if(strcmp(argv[i],"-packet")==0 && i+1<argc) simulated_packet_result=atoi(argv[++i]);
        if(strcmp(argv[i],"-wrong-entity")==0) strcpy(entity.name,"OtherHero");
        if(strcmp(argv[i],"-entity-id")==0 && i+1<argc) entity.db_id=atoi(argv[++i]);
    }
    finalizeResumeOnlyMode();
    printf("MODES:%d,%d,%d,%d\n",g_testMode,g_testMode2,g_testModeMission,g_testModeAccount);
''' + selection + '\nif (' + predicate + r''') printf("RESUME_BRANCH\n");
''' + packet + r'''
    printf("DONE\n");
    return 0;
}
''')
        cls.executable = root / 'probe'
        subprocess.run([shutil.which('cc'), '-std=c99', '-Wall', '-Werror', str(probe),
                        '-o', str(cls.executable)], check=True, capture_output=True)

    def run_probe(self, *args):
        return subprocess.run([str(self.executable), *args], capture_output=True, text=True)

    def test_existing_name_after_empty_slots_with_zero_list_id_preserves_connection(self):
        for flags in (('-resumeonly', '-character', 'TESTHero', '-justlogin', '-CREATE_CHAR', '-disconnect'),
                      ('-disconnect', '-justlogin', '-character', 'TESTHero', '-resumeonly')):
            with self.subTest(flags=flags):
                result = self.run_probe(*flags)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('MODES:5,0,0,0', result.stdout)
                self.assertIn('COH_RESUME_ONLY_SELECTED slot=2 name=TESTHero', result.stdout)
                self.assertIn('RESUME_BRANCH', result.stdout)

    def test_missing_or_wrong_case_name_exits_before_scene_or_creation(self):
        for name, flags in (('Absent', ()), ('testhero', ()), ('TESTHero', ('-no-slots',))):
            with self.subTest(name=name, flags=flags):
                result = self.run_probe('-resumeonly', '-character', name, *flags)
                self.assertEqual(result.returncode, 3)
                self.assertIn('COH_RESUME_ONLY_MISSING name=' + name, result.stdout)
                self.assertIn('DB_DISCONNECT', result.stdout)
                self.assertNotIn('SELECTED', result.stdout)
                self.assertNotIn('RESUME_BRANCH', result.stdout)
                self.assertNotIn('COMM_CHECK', result.stdout)
                self.assertNotIn('DONE', result.stdout)

    def test_invalid_arguments_fail_before_legacy_parser(self):
        for flags in (('-resumeonly',), ('-resumeonly', '-character'),
                      ('-character', '-resumeonly'), ('-resumeonly','-character',''),
                      ('-resumeonly','-character','empty'), ('-resumeonly','-character','a'*64),
                      ('-resumeonly','-character','bad\nname'),
                      ('-resumeonly','-character','TESTHero','-character','Second'),
                      ('-resumeonly','-character','TESTHero','-askuser')):
            with self.subTest(flags=flags):
                result = self.run_probe(*flags)
                self.assertEqual(result.returncode, 2)
                self.assertIn('COH_RESUME_ONLY_INVALID_ARGUMENTS', result.stdout)
                self.assertNotIn('COMM_CHECK', result.stdout)

    def test_nonpositive_received_entity_id_is_rejected(self):
        for dbid in ('0', '-7'):
            with self.subTest(dbid=dbid):
                result = self.run_probe('-resumeonly','-character','TESTHero',
                                        '-packet','1','-entity-id',dbid)
                self.assertEqual(result.returncode, 4)
                self.assertIn('COH_RESUME_ONLY_IDENTITY_MISMATCH', result.stdout)
                self.assertNotIn('COH_RESUME_ONLY_SERVER_UPDATE', result.stdout)

    def test_actual_received_positive_id_is_reported_for_independent_sql_binding(self):
        result = self.run_probe('-resumeonly','-character','TESTHero','-packet','1','-entity-id','987')
        self.assertEqual(result.returncode, 0)
        self.assertIn('COH_RESUME_ONLY_SERVER_UPDATE id=987 name=TESTHero', result.stdout)

    def test_only_successfully_processed_update_emits_actual_entity_identity(self):
        for packet_result in (1, 0, -1):
            with self.subTest(packet_result=packet_result):
                result = self.run_probe('-resumeonly','-character','TESTHero','-packet',str(packet_result))
                self.assertEqual(result.returncode, 0)
                self.assertIn('COMM_CHECK:71\nCOMM_CHECK:0', result.stdout)
                marker = 'COH_RESUME_ONLY_SERVER_UPDATE id=42 name=TESTHero'
                self.assertEqual(marker in result.stdout, packet_result == 1)
        wrong = self.run_probe('-resumeonly','-character','TESTHero','-packet','1','-wrong-entity')
        self.assertEqual(wrong.returncode, 4)
        self.assertIn('COH_RESUME_ONLY_IDENTITY_MISMATCH', wrong.stdout)
        self.assertNotIn('COH_RESUME_ONLY_SERVER_UPDATE', wrong.stdout)

    def test_without_option_defaults_and_packet_drain_remain_unchanged(self):
        result = self.run_probe('-packet','1')
        self.assertEqual(result.returncode, 0)
        self.assertIn('MODES:8199,1,1,1', result.stdout)
        self.assertIn('COMM_CHECK:0', result.stdout)
        self.assertNotIn('COMM_CHECK:71', result.stdout)
        self.assertNotIn('COH_RESUME_ONLY', result.stdout)


if __name__ == '__main__':
    unittest.main()
