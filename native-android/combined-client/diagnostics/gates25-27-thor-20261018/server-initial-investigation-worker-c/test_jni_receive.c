/* Reuse doubles as source only. Do not call the old qualifier's main. */
#define main retained_adapter_controls_not_executed
#include "../../interop-adapter-20261018/test_interop_adapter.c"
#undef main
int main(void){
 fixture();start();CohNetUdpDiagnostics*u=&capture.d.local.map_protocol.udp;
 u->datagrams_received=45;u->malformed=20;u->link.received=25;u->link.rx_pending=4;u->link.fragment_groups=2;
 u->link.decode.failure_kind=COH_NET_DECODE_BUDGET;u->link.decode.compressed_bytes=16000;u->link.decode.declared_raw_bytes=70000;u->link.decode.output_budget=4194304;
 CHECK(JNI(service)(&env,NULL,current,101)==COH_OK);CHECK(strstr(report(),"coh-initial-receive-counters-v1")&&strstr(report_text,"\"udp_malformed\":20")&&strstr(report_text,"\"link_received\":25"));
 strcpy(sample_report,report_text);JNI(suspend)(&env,NULL,current);CHECK(strstr(report(),"\"observation_retired\":true"));JNI(disconnect)(&env,NULL,current);CHECK(strstr(report(),"\"udp_datagrams_received\":45"));finish();
 fixture();start();capture.d.local.map_protocol.udp.datagrams_received=1000001;CHECK(JNI(service)(&env,NULL,current,101)==COH_OK);CHECK(strstr(report(),"\"refusal\":\"LIMIT\""));finish();
 CHECK(freed==wiped&&!live);
 printf("{\"passed\":true,\"checks\":%u,\"scenarios\":%u,\"new_receive_controls_only\":true,\"JNI_controller_and_witness_explicit_doubles\":true,\"actual_Android_or_original_server\":false,\"sample_report\":%s}\n",checks,scenarios,sample_report);return 0;
}
