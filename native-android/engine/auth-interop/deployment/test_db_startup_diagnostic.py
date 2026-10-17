import json
import unittest
from unittest import mock

import db_startup_diagnostic as stage


class DbStartupDiagnosticTests(unittest.TestCase):
    def test_exact_owned_numeric_query_and_cardinalities(self):
        sql=stage.sql_query('cohdb_ci_'+'a'*24,2596)
        self.assertIn("s.program_name='DBSERVER' AND s.host_process_id=2596",sql)
        self.assertIn('sys.dm_exec_requests',sql)
        self.assertNotIn('sql_text',sql)
        self.assertNotIn('user_auth',sql)
        row=stage.admit_sql('0|0|65|65|0|0|0|0|0|0|0|0|0')
        self.assertEqual(row['user_tables'],0);self.assertEqual(row['dbserver_sessions'],65)
        row=stage.admit_sql('99|3|65|62|3|3|1|1|1|1|0|0|0')
        self.assertEqual(row['waiting_requests'],3)
        for bad in ('0|0|65|65|0|0|0|0|0|0|0|0|0|secret','true','0|0|1|1|2|0|0|0|0|0|0|0|0',
                    '99|4|65|65|0|0|0|0|0|0|0|0|0','0|0|65|65|0|0|0|1|0|0|0|0|0'):
            with self.assertRaises(ValueError):stage.admit_sql(bad)
        with self.assertRaises(ValueError):stage.sql_query('external',2596)
        with self.assertRaises(ValueError):stage.sql_query('cohdb_ci_'+'a'*24,True)

    def test_real_shaped_process_output_is_only_fixed_enum_counts(self):
        value={'pid':2596,'cpu_ms':105,'threads':[{'state':2,'wait_reason':-1},
            {'state':5,'wait_reason':6},{'state':5,'wait_reason':6}]}
        with mock.patch.object(stage.prior,'capture',return_value=json.dumps(value)) as command:
            result=stage.observe_process(2596)
        self.assertIn('Get-Process -Id 2596',command.call_args.args[0][-1])
        self.assertEqual(result['thread_count'],3)
        self.assertEqual(result['thread_state_enum_counts']['5'],2)
        self.assertEqual(result['wait_reason_enum_counts']['6'],2)
        self.assertNotIn('threads',result)
        for key,changed in (('pid',True),('pid',2597),('cpu_ms',True),('threads',[]),
            ('threads',[{'state':True,'wait_reason':-1}]),('threads',[{'state':2,'wait_reason':6}]),
            ('threads',[{'state':5,'wait_reason':14}]),('threads',[{'state':5,'wait_reason':6,'stack':'private'}])):
            bad=dict(value);bad[key]=changed
            with self.subTest(key=key),self.assertRaises(ValueError):stage.admit_process(bad,2596)


if __name__=='__main__':unittest.main()
