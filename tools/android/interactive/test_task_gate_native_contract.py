"""Pin the stock command/task/save contracts used by the bounded Atlas task gate.

These tests qualify observations of existing native behavior. They add no
native command, quest definition, reward override, or mutation to game state.
"""
import hashlib
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import task_gate_evidence as evidence

EXTRA_NATIVE = (
    'MapServer/src/storyarc/clue.c',
    'MapServer/src/Reward.c',
    'Common/dbserver/servercfg.c',
    'DBServer/src/dbdispatch.c',
    'MapServer/src/dbcomm/dbcomm.c',
    'libs/UtilitiesLib/include/utilitieslib/utils/log.h',
    'libs/UtilitiesLib/src/utils/log.c',
)
EXTRA_DATA = (
    'data/texts/english/contacts/atlas_park/tasks/sl1_matthewhabashy.ms',
    'data/texts/english/contacts/atlas_park/atlaspark.def.ms',
)


class TaskGateNativeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.texts = {}
        for prefix, manifest_path, paths in (
            ('upstream/ouroboros', 'docs/source-manifest.json',
             evidence.NATIVE_CONTRACT_FILES + EXTRA_NATIVE),
            ('upstream/i24', 'docs/data-manifest.json',
             evidence.DATA_CONTRACT_FILES + EXTRA_DATA),
        ):
            manifest = json.loads((ROOT / manifest_path).read_text())
            pins = {entry['path']: entry for entry in manifest['entries']}
            for path in dict.fromkeys(paths):
                raw = (ROOT / prefix / path).read_bytes()
                pin = pins[path]
                if len(raw) != pin['size'] or hashlib.sha256(raw).hexdigest() != pin['sha256']:
                    raise AssertionError('Native/authored task contract differs from preserved source pin: ' + path)
                cls.texts[path] = raw.decode()

    def text(self, path):
        return self.texts[path]

    def test_stock_opener_does_not_depend_on_a_rendered_npc(self):
        commands = self.text('MapServer/src/cmdparse/cmdserver.c')
        self.assertRegex(commands, r'\{\s*9,\s*"contactdialog",\s*SCMD_CONTACT_INTERACT')
        self.assertIn('ContactDebugInteract(client, tmp_str, 0)', commands)
        interaction = self.text('MapServer/src/storyarc/contactInteraction.c')
        opener = interaction.split('void ContactDebugInteract(', 1)[1].split('// Make sure the server', 1)[0]
        self.assertIn('contact = ContactGetHandleLoose(contactfile)', opener)
        self.assertIn('interactEntityRef = 0', opener)
        self.assertIn('interactPosLimited = 0', opener)
        self.assertIn('ContactGeneralInteract(client->entity, contact, CONTACTLINK_HELLO)', opener)
        self.assertIn('"ContactInteract:Debug Initiating interaction with contact %d"', opener)
        self.assertNotIn('TaskAdd(', opener)

    def test_acceptance_remains_a_normal_manual_dialogue_response(self):
        dialog = self.text('MapServer/src/storyarc/contactDialog.c')
        accept = dialog.split('void ContactInteractionAcceptTask(', 1)[1].split('// wrap up a task', 1)[0]
        self.assertIn('ContactPickTask(player, info, contactInfo, taskLength, &pickInfo, false)', accept)
        self.assertIn('TaskAdd(player, &pickInfo.sahandle, seed, limitLevel, villainGroup)', accept)
        self.assertIn('case CONTACTLINK_ACCEPTSHORT:', dialog)
        self.assertIn('ContactInteractionAcceptTask(&context, TASK_SHORT)', dialog)
        authored = self.text('data/scripts.loc/contacts/atlas_park/tasks/sl1_matthewhabashy.storyarc')
        first = authored.split('// Task Mission1', 1)[1].split('// Episode "one" Reward', 1)[0]
        self.assertIn('TaskDef taskKillX taskShort taskRequired', first)
        self.assertNotIn('taskAutoIssue', first)
        self.assertNotIn('taskDontReturntoContact', first)

    def test_stock_completion_is_zero_based_and_uses_normal_completion(self):
        commands = self.text('MapServer/src/cmdparse/cmdserver.c')
        self.assertRegex(commands, r'\{\s*2,\s*"completetask",\s*SCMD_TASK_COMPLETE')
        self.assertIn('TaskDebugComplete(client->entity, tmp_int, cmd->num == SCMD_TASK_COMPLETE)', commands)
        task = self.text('MapServer/src/storyarc/task.c')
        debug = task.split('void TaskDebugComplete(Entity* player, int index, int succeeded)', 1)[1].split('// calls TaskForceGet()', 1)[0]
        self.assertIn('index < eaSize(&info->tasks)', debug)
        self.assertIn('taskinfo = info->tasks[index]', debug)
        self.assertIn('TaskDebugCompleteByTask(player, taskinfo, succeeded)', debug)
        by_task = task.split('void TaskDebugCompleteByTask(', 1)[1].split('void TaskDebugComplete(Entity*', 1)[0]
        self.assertIn('TaskSetComplete(player, &taskinfo->sahandle, 1, succeeded)', by_task)
        self.assertIn('TaskStatusSendUpdate(player)', by_task)
        self.assertNotIn('TaskDebugClearAllTasks', debug + by_task)

    def test_native_logs_cover_assignment_command_and_real_success(self):
        task = self.text('MapServer/src/storyarc/task.c')
        self.assertIn('"Task:Add %s", task->def->logicalname', task)
        self.assertIn('"Task:ForceComplete Auth: %s Task: %s"', task)
        self.assertIn('"Task:ForceComplete Context: %d Subhandle: %d"', task)
        self.assertIn('"Task:ForceComplete Task Name: %s, File: %s"', task)
        completion = task.split('void TaskComplete(Entity*', 1)[1].split('/* Function TaskRewardCompletion()', 1)[0]
        self.assertIn('task->state = TASK_SUCCEEDED', completion)
        self.assertIn('strcpy(buf, "Task:Success")', completion)
        self.assertIn('"%s Name: %s, Type: %s", buf, task->def->logicalname, typeStr', completion)
        self.assertIn('if (success && !taskAlreadyComplete)', completion)
        self.assertIn('StoryRewardApply(task->def->taskSuccess[0]', completion)
        self.assertLess(completion.index('"%s Name:'), completion.index('StoryRewardApply(task->def->taskSuccess[0]'))

    def test_sql_state_four_is_completed_before_return_to_contact(self):
        header = self.text('MapServer/src/storyarc/storyarcprivate.h')
        enum_body = header.split('typedef enum TaskState', 1)[1].split('} TaskState;', 1)[0]
        values = re.findall(r'\bTASK_[A-Z_]+\b', enum_body)
        self.assertEqual(values, ['TASK_NONE', 'TASK_ASSIGNED', 'TASK_MARKED_SUCCESS',
                                  'TASK_MARKED_FAILURE', 'TASK_SUCCEEDED', 'TASK_FAILED'])
        self.assertEqual(values.index('TASK_ASSIGNED'), 1)
        self.assertEqual(values.index('TASK_SUCCEEDED'), 4)
        task = self.text('MapServer/src/storyarc/task.c')
        self.assertIn('if (TASK_IS_NORETURN(task->def))', task)
        self.assertIn('TaskRewardCompletion(player, task, contactInfo, response)', task)
        dialog = self.text('MapServer/src/storyarc/contactDialog.c')
        turn_in = dialog.split('int ContactInteractionTaskCompletion(', 1)[1].split('// show busy text', 1)[0]
        self.assertIn('TaskCompletedAndIncremented(task)', turn_in)
        self.assertIn('TaskRewardCompletion(player, task, contactInfo, response)', turn_in)
        self.assertIn('TaskClose(player, contactInfo, task, response)', turn_in)

    def test_sql_task_context_is_an_authored_path_not_the_runtime_handle(self):
        descriptor = self.text('MapServer/src/container/containerloadsave.c')
        self.assertIn('INOUT(TaskGetHandle, TaskFileName)', descriptor)
        self.assertIn('INOUT(ContactGetHandle, ContactFileName)', descriptor)
        self.assertIn('INOUT(StoryArcContextFromFileName, StoryArcFileName)', descriptor)
        definitions = self.text('MapServer/src/storyarc/taskdef.c')
        self.assertIn('if (context<0)', definitions)
        self.assertIn('return StoryArcFileName(context)', definitions)
        self.assertIn('return ContactFileName(context)', definitions)
        arc = self.text('MapServer/src/storyarc/storyarc.c')
        self.assertIn('"Storyarc:Add Handle %d", sahandle.context', arc)
        self.assertIn('sahandle->subhandle = StoryIndexToHandle(index)', arc)
        header = self.text('MapServer/src/storyarc/storyarcprivate.h')
        self.assertIn('StoryIndexToHandle(int index) { return index + 1; }', header)
        self.assertEqual(evidence.CONTEXT_PATH.casefold(), evidence.TASK_FILE.casefold())
        self.assertEqual(evidence.TASKS['Mission1']['subhandle'], 1)

    def test_authored_first_task_is_one_simple_eligible_atlas_task(self):
        contact = self.text('data/scripts.loc/contacts/atlas_park/matthew_habashy.contact')
        self.assertRegex(contact, r'\bAlliance\s+Hero\b')
        self.assertRegex(contact, r'\bMinPlayerLevel\s+1\b')
        self.assertRegex(contact, r'\bMaxPlayerLevel\s+10\b')
        self.assertNotIn('InteractionRequires', contact)
        self.assertNotIn('TaskInclude', contact)
        self.assertIn('StoryArc scripts.loc\\Contacts\\Atlas_Park\\tasks\\SL1_MatthewHabashy.storyarc', contact)
        authored = self.text('data/scripts.loc/contacts/atlas_park/tasks/sl1_matthewhabashy.storyarc')
        first = authored.split('Episode // one', 1)[1].split('// Episode "one" Reward', 1)[0]
        self.assertEqual(re.findall(r'\bTaskDef\s+([^\r\n]+)', first), ['taskKillX taskShort taskRequired'])
        self.assertRegex(first, r'\bName\s+Mission1\b')
        self.assertRegex(first, r'\bVillainType\s+Hellions\b')
        self.assertRegex(first, r'\bVillainCount\s+5\b')
        self.assertRegex(first, r'\bLocationMap\s+City_01_01\b')
        self.assertEqual(evidence.TASKS['Mission1']['type'], 'taskKillX')
        definitions = self.text('MapServer/src/storyarc/taskdef.c')
        self.assertRegex(definitions, r'"taskKillX",\s*TASK_KILLX')

    def test_success_rewards_are_authored_and_native_credit_can_be_scaled(self):
        authored = self.text('data/scripts.loc/contacts/atlas_park/tasks/sl1_matthewhabashy.storyarc')
        first = authored.split('// Task Mission1', 1)[1].split('// Episode "one" Reward', 1)[0]
        success = first.split('TaskSuccess\n', 1)[1].split('// ReturnSuccessFlashback', 1)[0]
        self.assertRegex(success, r'\bContactPoints\s+10\b')
        self.assertRegex(success, r'Chance\s+100\s+Always')
        self.assertRegex(success, r'\bExperience\s+25\b')
        self.assertNotIn('PrimaryReward', success)
        self.assertNotIn('Influence', success)
        self.assertEqual(evidence.TASKS['Mission1']['task_success_experience'], 25)
        self.assertEqual(evidence.TASKS['Mission1']['task_success_contact_points'], 10)
        reward = self.text('MapServer/src/Reward.c')
        self.assertIn('fXPScale += e->pchar->attrCur.fExperienceGain', reward)
        self.assertIn('iXPReceived = reward->experience*fXPScale', reward)
        self.assertIn('"[Tbl]:Rcv:Points XP: %d, Debt: %d, Inf: %d, Pres: %d (SGMode off (%d))"', reward)
        clue = self.text('MapServer/src/storyarc/clue.c')
        self.assertIn('StoryRewardContactPoints(contactInfo, info, reward->contactPoints)', clue)
        self.assertIn('rewardApplyLogWrapper(accumulator, player, true, false, REWARDSOURCE_STORY)', clue)

    def test_profile_can_enable_old_arc_context_logs_without_native_changes(self):
        config = self.text('Common/dbserver/servercfg.c')
        self.assertIn('stricmp(s, "SetLogLevel") == 0', config)
        self.assertIn('logSetLevel( logGetTypeFromName(s2), atoi(args[2]) )', config)
        levels = self.text('libs/UtilitiesLib/include/utilitieslib/utils/log.h')
        enum_body = levels.split('typedef enum LogLevel', 1)[1].split('}LogLevel;', 1)[0]
        self.assertLess(enum_body.index('LOG_LEVEL_IMPORTANT'), enum_body.index('LOG_LEVEL_VERBOSE'))
        self.assertLess(enum_body.index('LOG_LEVEL_VERBOSE'), enum_body.index('LOG_LEVEL_DEPRECATED'))
        self.assertIn('LOG_LEVEL_ALERT = -1', enum_body)
        self.assertIn('LOG_LEVEL_DEPRECATED', self.text('MapServer/src/dbcomm/logcomm.h'))
        db = self.text('DBServer/src/dbdispatch.c')
        self.assertIn('logLevel(i)', db)
        self.assertIn('sendLogLevels(link, DBSERVER_UPDATE_LOG_LEVELS)', db)
        receiver = self.text('MapServer/src/dbcomm/dbcomm.c')
        self.assertIn('xcase DBSERVER_UPDATE_LOG_LEVELS:', receiver)
        self.assertIn('logSetLevel(i,log_level)', receiver)
        defaults = self.text('libs/UtilitiesLib/src/utils/log.c')
        self.assertRegex(defaults, r'\{\s*"rewards",\s*LOG_LEVEL_IMPORTANT\s*\}')
        self.assertRegex(defaults, r'\{\s*"Admin",\s*LOG_LEVEL_IMPORTANT\s*\}')

    def test_selected_sql_columns_exist_in_the_preserved_descriptors(self):
        descriptor = self.text('MapServer/src/container/containerloadsave.c')
        groups = {
            'tasks': descriptor.split('LineDesc task_line_desc[]', 1)[1].split('StructDesc task_desc[]', 1)[0],
            'contacts': descriptor.split('LineDesc contact_line_desc[]', 1)[1].split('StructDesc contact_desc[]', 1)[0],
            'storyarcs': descriptor.split('LineDesc storyarc_line_desc[]', 1)[1].split('StructDesc storyarc_desc[]', 1)[0],
            'ents': descriptor,
        }
        for table, fields in evidence.SELECTED.items():
            names = {name.casefold() for name in re.findall(r'"([A-Za-z][A-Za-z0-9_]*)"', groups[table])}
            for field in set(fields) - {'containerid', 'subid'}:
                self.assertIn(field, names, table + '.' + field)

    def test_instructions_can_name_the_exact_task_without_english_guessing(self):
        texts = self.text('data/texts/english/contacts/atlas_park/tasks/sl1_matthewhabashy.ms')
        self.assertIn('"P585749243" "<color deepskyblue>What Was Lost</color>"', texts)
        self.assertIn('"P3073403113" "<color deepskyblue>Part One: Demons and Gangsters</color>"', texts)
        self.assertIn('"P718894000" "Just tell me where to go and I\'ll help those people."', texts)
        contact = self.text('data/texts/english/contacts/atlas_park/atlaspark.def.ms')
        self.assertIn('"P469111239" "Matthew Habashy"', contact)


if __name__ == '__main__':
    unittest.main()
