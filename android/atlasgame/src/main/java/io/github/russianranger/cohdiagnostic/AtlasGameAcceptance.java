package io.github.russianranger.cohdiagnostic;

import java.util.Arrays;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** The Android result requires the complete device sequence, not a guest pass flag alone. */
final class AtlasGameAcceptance {
    private static final String GAME_ACK="COH_GAME_LOOPBACK_ONLY=1 active: IPv4 loopback binding policy";
    private static final String DB_ACK="COH_WINE_DB_LOOPBACK_ONLY=1 active: IPv4 listener binds restricted to loopback; endpoint verification required";
    private static final String FIXED_ACK="COH_WINE_DB_FIXED_INPUTS=1 active: directory monitoring disabled; initial reads and lookup mode preserved";
    private static final String[] STAGES={"game_private_runtime","assets_and_architecture","initialize_owned_cluster","postgres_first_start",
        "restricted_fixture_database","wine_prefix_and_driver","win32_odbc_driver","win32_runtime_dll","game_services_first",
        "atlas_ready_observation","game_create_and_connect","game_live_currency","game_protocol_logout_first","game_restart",
        "postgres_game_restart","game_services_restart","game_resume_exact_name","game_protocol_logout_second"};
    private static final String[] DIGEST_KEYS={"game_package_sha256","game_data_manifest_sha256","schema_manifest_sha256"};
    private static final String[] DIGESTS={"ebfdbbab3984627f7c39220f42a9c3e67b78ffe555aa742621a7a1450731fb2a",
        "b367cc35d3f3826d9988ffa5dadb0a240ffc0967f0d248586e54d8ac545615f4","b89136892e69ceb39db640613d3f8a34abf2ef8e75e947f4034728b935938b92"};

    static boolean cleanupSafe(Object value) {
        Map<?,?> report=object(value),execution=object(report.get("cleanup_execution"));
        if(!yes(report.get("cleanup_complete"))||!(report.get("processes") instanceof List)
                ||!(execution.get("diagnostic_initialized") instanceof Boolean)||!(execution.get("wine_started") instanceof Boolean)
                ||!(execution.get("postgres_started") instanceof Boolean))return false;
        List<?> processes=list(report.get("processes"));
        if(!number(execution.get("owned_child_count"),processes.size()))return false;
        for(Object valueProcess:processes){Map<?,?> process=object(valueProcess);
            if(!integer(process.get("exit_code"))||!all(process,"input_closed","output_capture_closed"))return false;}
        if(no(execution.get("diagnostic_initialized")))return processes.isEmpty()&&no(execution.get("wine_started"))&&no(execution.get("postgres_started"));
        Map<?,?> cleanup=object(report.get("cleanup"));
        return yes(cleanup.get("owned_processes_reaped"))
            &&(no(execution.get("postgres_started"))||yes(cleanup.get("postgres_graceful")))
            &&(no(execution.get("wine_started"))||(yes(cleanup.get("wine_prefix_stopped"))&&owned(report.get("wine_process_cleanup"))));
    }

    static boolean accepts(Object value,String runtimeHash,Object imported) {
        Map<?,?> report=object(value),expectedImport=object(imported);
        if(!yes(report.get("passed"))||!"passed".equals(report.get("status"))||!empty(report.get("failures"))
                ||!"atlas_character_persistence".equals(report.get("diagnostic_mode"))
                ||!"android".equals(report.get("execution_platform_requested"))||!"device".equals(report.get("listener_policy"))
                ||!yes(report.get("cleanup_complete")))return false;
        for(String key:new String[]{"android_execution_validated","gameplay_validated","android_surface_validated",
                "hardware_acceleration_validated","interactive_rendering_validated"})if(!no(report.get(key)))return false;
        Map<?,?> inputs=object(report.get("inputs"));
        if(!digest(runtimeHash)||!runtimeHash.equals(inputs.get("runtime_manifest_sha256"))
                ||!"ac4c1f7978be444a893f65f5177641191861d42f".equals(inputs.get("repository_commit"))
                ||!"0b75ade0c801735e10c5798f641948a45cc50488".equals(inputs.get("source_commit"))
                ||!"d51533ec8e6a9cf726b9214968077a05fdcf19f3".equals(inputs.get("data_commit")))return false;
        for(int i=0;i<DIGEST_KEYS.length;i++)if(!DIGESTS[i].equals(inputs.get(DIGEST_KEYS[i])))return false;
        Map<?,?> actualImport=object(report.get("imported_content"));
        if(expectedImport.isEmpty()||!yes(actualImport.get("private_copy_verified"))||!yes(actualImport.get("source_generation_unchanged")))return false;
        for(String key:new String[]{"generation","contract_sha256","receipt_sha256"})
            if(!expectedImport.containsKey(key)||!expectedImport.get(key).equals(actualImport.get(key)))return false;
        if(!number(actualImport.get("file_count"),173011)||!number(actualImport.get("total_bytes"),2977730517L))return false;
        Map<?,?> cleanup=object(report.get("cleanup"));
        if(!all(cleanup,"postgres_graceful","wine_prefix_stopped","owned_processes_reaped")||!owned(report.get("wine_process_cleanup")))return false;
        List<?> stages=list(report.get("stages"));if(stages.size()!=STAGES.length)return false;
        for(int i=0;i<STAGES.length;i++)if(!STAGES[i].equals(object(stages.get(i)).get("stage"))||!"passed".equals(object(stages.get(i)).get("status")))return false;
        Map<?,?> first=object(stages.get(0));
        if(!number(first.get("input_files"),173011)||!number(first.get("input_bytes"),2977730517L)
                ||!number(first.get("accepted_schema_overlay_files"),62)||!no(object(stages.get(2)).get("cluster_reused")))return false;
        List<?> processes=list(report.get("processes"));if(processes.isEmpty()||processes.size()>240)return false;
        List<String> labels=new ArrayList<>();
        for(Object item:processes){Map<?,?> process=object(item);Object label=process.get("label");
            if(!(label instanceof String)||!integer(process.get("exit_code"))
                ||!all(process,"input_closed","output_capture_closed"))return false;
            labels.add((String)label);
            if(((String)label).startsWith("bridge-")&&!number(process.get("exit_code"),0))return false;}
        if(!labels.containsAll(Arrays.asList("first-dbserver","first-atlas","restart-dbserver","restart-atlas","bridge-create","bridge-resume",
                "postgres_first_start","postgres_game_restart")))return false;
        for(String label:new String[]{"first-dbserver","first-atlas","restart-dbserver","restart-atlas","bridge-create","bridge-resume",
                "postgres_first_start","postgres_game_restart"})if(Collections.frequency(labels,label)!=1)return false;
        Map<?,?> game=object(report.get("game"));
        if(!"passed".equals(game.get("status"))||!all(game,"created_connected","attributes_unchanged")
                ||!"loopback".equals(game.get("dbserver_profile"))||!"loopback".equals(game.get("game_listener_profile")))return false;
        List<?> phases=list(game.get("phases"));if(phases.size()!=2)return false;
        Object catalog=null;
        for(int i=0;i<2;i++) {
            Map<?,?> phase=object(phases.get(i)),schema=object(phase.get("schema")),fixed=object(phase.get("fixed_inputs"));
            if(!(i==0?"first_services_ready":"restart_services_ready").equals(phase.get("phase"))||!"passed".equals(phase.get("status"))
                    ||!yes(phase.get("baseline_not_started"))||!mapReady(phase.get("map"))||!dbListeners(phase.get("loopback_only"))
                    ||!gameListeners(phase.get("game_listeners"),false)||!yes(fixed.get("requested"))||!FIXED_ACK.equals(fixed.get("startup_acknowledgement"))
                    ||!number(schema.get("table_count"),99)||!number(schema.get("column_count"),5935)
                    ||!"0f35891b50f957d331c2407bdf5145bf36648e415c62445109c0431d9f32e36e".equals(schema.get("ordered_columns_sha256")))return false;
            Map<?,?> current=object(schema.get("catalog_sha256"));if(current.size()!=3||!digest(current.get("columns"))||!digest(current.get("indexes"))||!digest(current.get("constraints")))return false;
            if(catalog!=null&&!catalog.equals(current))return false;catalog=current;
        }
        Map<?,?> fixed=object(game.get("fixed_inputs")),baseline=object(fixed.get("baseline"));
        if(!yes(fixed.get("requested"))||!number(fixed.get("schema_file_count"),62)||!digest(baseline.get("inventory_sha256")))return false;
        List<?> checks=list(fixed.get("checks"));String[] order={"before-first","after-first-save","before-restart","after-second-save"};
        if(checks.size()!=4)return false;
        for(int i=0;i<order.length;i++){Map<?,?> check=object(checks.get(i));if(!order[i].equals(check.get("phase"))||!yes(check.get("unchanged"))
                ||!baseline.get("inventory_sha256").equals(check.get("inventory_sha256")))return false;}
        Map<?,?> observation=object(game.get("atlas_observation"));
        if(!all(observation,"db_confirmed_ready","current_heartbeats")||!atLeast(observation.get("seconds"),30))return false;
        List<?> samples=list(observation.get("samples"));if(samples.size()<2)return false;
        double previous=0;for(Object sample:samples){Object time=object(sample).get("monotonic");if(!mapReady(sample)||!atLeast(time,previous)||((Number)time).doubleValue()==previous)return false;previous=((Number)time).doubleValue();}
        Map<?,?> character=object(game.get("character")),currency=object(game.get("live_currency"));
        Object name=character.get("name"),account=character.get("account"),id=character.get("container_id");
        if(!(name instanceof String)||((String)name).isEmpty()||((String)name).length()>128||!(account instanceof String)
                ||!((String)account).matches("CohA[0-9a-f]{10}")||!account.equals(game.get("account"))||!integer(id)||!atLeast(id,1)
                ||!name.equals(currency.get("player"))||!account.equals(currency.get("account"))||!number(currency.get("influence"),12345))return false;
        Map<?,?> firstSave=object(game.get("first_save")),secondSave=object(game.get("second_save"));
        if(!save(firstSave,1)||!save(secondSave,2)||!firstSave.get("row_counts").equals(secondSave.get("row_counts")))return false;
        Map<?,?> restart=object(game.get("restart"));
        if(!all(restart,"same_cluster","same_database","no_reseed_or_restore","identity_unchanged","selected_rows_unchanged")
                ||!all(object(restart.get("wine_shutdown")),"prefix_lock_free","server_socket_inactive")||!owned(restart.get("owned_cleanup"))
                ||!firstSave.get("snapshot_sha256").equals(restart.get("snapshot_sha256"))||!number(restart.get("login_count_after"),1))return false;
        Map<?,?> comparison=object(secondSave.get("comparison")),resume=object(game.get("resume"));
        if(!all(comparison,"identity_unchanged","selected_rows_unchanged")||!number(comparison.get("login_count_before"),1)
                ||!number(comparison.get("login_count_after"),2)||!firstSave.get("row_counts").equals(comparison.get("row_counts"))
                ||!name.equals(resume.get("exact_name"))||!sameNumber(id,resume.get("database_id"))
                ||!all(resume,"creation_disabled","connected_on_atlas","processed_server_update","scene_exchange_observed","processed_server_update_for_original_player")
                ||!no(resume.get("active_gameplay_confirmed")))return false;
        Map<?,?> sessions=object(game.get("sessions")),live=object(game.get("client_listener_observations"));
        if(sessions.size()!=2||live.size()!=2)return false;
        for(String label:new String[]{"first","second"}) {
            Map<?,?> session=object(sessions.get(label));if(!session(session)||!gameListeners(live.get(label),true)||!gameListeners(session.get("game_listeners"),true))return false;
            List<?> earlier=list(object(live.get(label)).get("endpoints")),later=list(object(session.get("game_listeners")).get("endpoints"));
            if(later.size()<earlier.size()||!later.subList(0,earlier.size()).equals(earlier))return false;
        }
        Map<?,?> captures=object(game.get("capture_files")),service=object(game.get("service_capture_files"));
        for(String label:new String[]{"first","second"})for(String suffix:new String[]{"ready.json","result.json","events.jsonl","console.txt","snapshot.json"})
            if(!pin(captures.get(label+"-"+suffix)))return false;
        if(!pin(captures.get("restart-snapshot.json")))return false;
        for(String label:new String[]{"first-dbserver","first-atlas","restart-dbserver","restart-atlas"})if(!pin(service.get(label+"-stdout.txt")))return false;
        return pin(service.get("manifest.json"));
    }
    private static boolean save(Map<?,?> proof,int count) {
        Map<?,?> rows=object(proof.get("row_counts"));
        return all(proof,"protocol_quit","disconnected_before_sql","independent_committed_sql")&&no(proof.get("quitnow_is_save_ack"))
            &&no(proof.get("forced_stop_before_save"))&&number(proof.get("login_count"),count)&&number(proof.get("influence"),12345)
            &&digest(proof.get("snapshot_sha256"))&&rows.size()==4&&number(rows.get("ents"),1)&&number(rows.get("ents2"),1)
            &&atLeast(rows.get("powers"),1)&&atLeast(rows.get("costumeparts"),1);
    }
    private static boolean session(Map<?,?> session) {
        Map<?,?> ready=object(session.get("ready")),result=object(session.get("result"));Object pid=ready.get("child_pid"),exit=result.get("child_exit_code");
        return yes(session.get("proof_completed_before_stop"))&&number(ready.get("format"),1)&&number(result.get("format"),1)
            &&integer(pid)&&atLeast(pid,1)&&sameNumber(pid,ready.get("transport_pid"))&&sameNumber(pid,result.get("child_pid"))
            &&all(ready,"console_attached","pipe_pid_verified","protocol_pid_verified","initial_snapshot")
            &&all(result,"final_snapshot","pipe_framing_complete","pipe_disconnected")
            &&(result.get("error")==null||"null".equals(String.valueOf(result.get("error"))))
            &&integer(exit)&&atLeast(exit,0)&&!number(exit,259)&&atLeast(result.get("console_snapshots"),2)
            &&digest(session.get("console_sha256"))&&digest(session.get("events_sha256"));
    }
    private static boolean mapReady(Object value) {
        Map<?,?> map=object(value);return yes(map.get("ready"))&&number(map.get("map_id"),1)&&"127.0.0.1".equals(map.get("address"))
            &&number(map.get("port"),7001)&&range(map.get("network_age_seconds"),0,20)&&range(map.get("stats_age_seconds"),0,20);
    }
    private static boolean dbListeners(Object value) {
        Map<?,?> record=object(value);if(!yes(record.get("requested"))||!DB_ACK.equals(record.get("startup_acknowledgement")))return false;
        Set<String> required=new HashSet<>(Arrays.asList("tcp:6971","tcp:6974","tcp:6976","tcp:6977","tcp:6979","tcp:6980","tcp:6982",
            "tcp:6984","tcp:6989","tcp:6996","tcp:6997","tcp:6998","udp:7000"));
        Set<String> actual=new HashSet<>();for(Object entry:list(record.get("endpoints"))){String key=endpoint(entry);if(key==null||(!required.contains(key)&&!"tcp:6992".equals(key))||!actual.add(key))return false;}
        return actual.containsAll(required);
    }
    private static boolean gameListeners(Object value,boolean client) {
        Map<?,?> record=object(value);List<?> endpoints=list(record.get("endpoints"));
        if(!yes(record.get("requested"))||!GAME_ACK.equals(record.get("startup_acknowledgement"))||endpoints.size()<(client?2:1)||endpoints.size()>128)return false;
        if(!client)return endpoints.size()==1&&"udp:7001".equals(endpoint(endpoints.get(0)));
        for(Object entry:endpoints){String key=endpoint(entry);if(key==null||!key.startsWith("udp:"))return false;}return true;
    }
    private static String endpoint(Object value){Map<?,?> e=object(value);Object protocol=e.get("protocol"),port=e.get("port");
        if(!"127.0.0.1".equals(e.get("address"))||!("tcp".equals(protocol)||"udp".equals(protocol))||!range(port,1,65535))return null;
        return protocol+":"+((Number)port).intValue();}
    private static boolean owned(Object value){Map<?,?> v=object(value);return yes(v.get("complete"))&&number(v.get("remaining"),0)&&number(v.get("inspection_failures"),0);}
    private static boolean pin(Object value){Map<?,?> p=object(value);return integer(p.get("bytes"))&&atLeast(p.get("bytes"),0)&&digest(p.get("sha256"));}
    private static boolean all(Map<?,?> value,String...keys){for(String key:keys)if(!yes(value.get(key)))return false;return true;}
    private static boolean sameNumber(Object a,Object b){return integer(a)&&integer(b)&&((Number)a).doubleValue()==((Number)b).doubleValue();}
    private static boolean integer(Object n){return n instanceof Number&&Double.isFinite(((Number)n).doubleValue())&&((Number)n).doubleValue()==((Number)n).longValue();}
    private static boolean number(Object n,long expected){return integer(n)&&((Number)n).longValue()==expected;}
    private static boolean atLeast(Object n,double expected){return n instanceof Number&&Double.isFinite(((Number)n).doubleValue())&&((Number)n).doubleValue()>=expected;}
    private static boolean range(Object n,long min,long max){return integer(n)&&((Number)n).longValue()>=min&&((Number)n).longValue()<=max;}
    private static boolean digest(Object v){return v instanceof String&&((String)v).matches("[0-9a-f]{64}");}
    private static boolean yes(Object v){return Boolean.TRUE.equals(v);}
    private static boolean no(Object v){return Boolean.FALSE.equals(v);}
    private static boolean empty(Object v){return v instanceof List&&((List<?>)v).isEmpty();}
    private static Map<?,?> object(Object v){return v instanceof Map?(Map<?,?>)v:Collections.emptyMap();}
    private static List<?> list(Object v){return v instanceof List?(List<?>)v:Collections.emptyList();}
    private AtlasGameAcceptance(){}
}
