
#include <cstdio>
#include <vector>
#include <cstdlib>
static unsigned checks,cases,queries,sleeps,results;static long now_ms,advance_ms;
static std::vector<int> answers;static bool last_empty;
static void check(bool ok){++checks;if(!ok)std::abort();}
struct Refusal{int code;};
struct Milliseconds{long start;operator long()const{return now_ms-start;}};
struct Watch{Milliseconds ElapsedMilliseconds;};
struct StopwatchFactory{Watch StartNew(){Watch w={{now_ms}};return w;}} Stopwatch;
struct ThreadFactory{void Sleep(int value){check(value==20);++sleeps;now_ms+=advance_ms;}} Thread;
struct CauseFactory{int JOB;} Cause={7};
static void Need(bool ok,int code){if(!ok)throw Refusal{code};}
static bool JobIsEmpty(){
 unsigned at=queries++;int value=answers[at<answers.size()?at:answers.size()-1];
 if(value<0){throw Refusal{99};}last_empty=value!=0;return last_empty;
}
struct ResultFactory{void Same(){check(last_empty);++results;}} resultPin;
static void candidate(){
   Watch drain=Stopwatch.StartNew();bool drained=false;
   do {drained=JobIsEmpty();if(drained)break;Thread.Sleep(20);}
   while(drain.ElapsedMilliseconds<10000);
   Need(drained,Cause.JOB);
   resultPin.Same();
}
static void scenario(std::vector<int> input,int expected,unsigned q,unsigned nap,unsigned result,long step=20){
 ++cases;answers=input;queries=sleeps=results=0;now_ms=0;advance_ms=step;last_empty=false;int actual=0;
 try{candidate();}catch(Refusal refusal){actual=refusal.code;}
 check(actual==expected);check(queries==q);check(sleeps==nap);check(results==result);
}
int main(){
 scenario({1},0,1,0,1);scenario({0,0,1},0,3,2,1);scenario({0},7,500,500,0);
 scenario({-1},99,1,0,0);scenario({0,-1},99,2,1,0);scenario({0,1},7,1,1,0,10000);
 std::printf("{\"passed\":true,\"scenarios\":%u,\"checks\":%u,\"Windows_API\":false,\"original_owner_or_probe\":false}\n",cases,checks);return 0;
}
