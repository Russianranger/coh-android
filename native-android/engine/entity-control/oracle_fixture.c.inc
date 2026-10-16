static void fixture_setup(ClientLink *client,Entity *e,Character *character,MotionState *motion,
                          ServerControlState *server,FuturePush *pushes,int scenario){
 memset(client,0,sizeof(*client));memset(e,0,sizeof(*e));memset(character,0,sizeof(*character));
 memset(motion,0,sizeof(*motion));memset(server,0,sizeof(*server));memset(pushes,0,40*sizeof(*pushes));
 e->client=client;e->pchar=character;e->motion=motion;
 client->controls.phys.latest.net_id=-1;server->id=37;client->controls.sent_update_id=37;
 if(scenario==0)return;
 for(int i=0;i<3;i++){
  e->pos[i]=(float)(100+i*10);motion->vel[i]=i==1?0:(float)(i-2);
  client->controls.pyr.cur[i]=(float)(i+1)*0.25f;
  client->controls.phys.latest.pos[i]=(float)(-40+i*13);
  client->controls.phys.latest.vel[i]=i==1?0:(float)(i+2)*-0.5f;
  server->speed[i]=(float)(i+1)*3.25f;
 }
 server->speed_back=1.5f;server->jump_height=12.0f;
 float *surfaces=(float *)server->surf_mods;for(int i=0;i<10;i++)surfaces[i]=(float)(i+1)*0.125f;
 server->fly=1;server->stun=0;server->jumppack=1;server->glide=1;server->ninja_run=0;
 server->walk=1;server->beast_run=1;server->steam_jump=0;server->hover_board=1;
 server->magic_carpet=1;server->parkour_run=0;server->no_physics=1;server->hit_stumble=1;
 server->controls_input_ignored=0;server->shell_disabled=1;server->no_ent_collision=1;server->no_jump_repeat=1;
 character->attrCur.fStunned=scenario==4?2.0f:0.0f;
 client->controls.queued_server_states.tail=server;
 client->controls.phys.latest.net_id=65535;
 client->controls.server_pos_id=17;motion->falling=1;
 unsigned count=scenario==2?32u:(scenario==6?33u:3u);
 if(scenario==3){client->controls.queued_server_states.tail=NULL;client->controls.phys.latest.net_id=-1;count=0;}
 if(scenario==4){client->controls.server_pos_id=0;count=0;}
 if(scenario==5){client->controls.record_motion=1;count=0;}
 for(unsigned i=0;i<count;i++){
  pushes[i].controls_next=i+1<count?&pushes[i+1]:NULL;
  pushes[i].net_id_start=(U16)(65535u-i);pushes[i].phys_tick_wait=(U16)(i?i:65535u);
  pushes[i].abs_time=0xfedcba00u+i;pushes[i].do_knockback_anim=i&1;
  pushes[i].add_vel[0]=(float)i;pushes[i].add_vel[1]=-2.5f;pushes[i].add_vel[2]=0.125f;
 }
 if(count)client->controls.future_push_list=pushes;
 if(scenario==7){pushes[1].was_sent=1;}
 if(scenario==8){pushes[0].net_id_used=1;pushes[2].net_id_used=1;}
}
void original_send(int scenario,int aligned,int prefix,U8 *out,U32 *bits){
 U32 storage[8192]={0};Packet p={0};ClientLink client;Entity e;Character character;MotionState motion;ServerControlState server;FuturePush pushes[40];NetLink link={0};
 fixture_setup(&client,&e,&character,&motion,&server,pushes,scenario);link.userData=&client;
 initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,aligned,0);
 if(prefix)bsWriteBits(&p.stream,prefix,0);
 svrPlayerSendControlState(&p,&e,&link,scenario==4);
 *bits=p.stream.bitLength;memcpy(out,storage,(*bits+7)/8);
}
/* Original TEST_CLIENT consumer executes complete control composition, with
 * no pending local prediction history, recording data, or ACK creation. */
void original_receive(const U8 *input,U32 bits,int aligned,int prefix,U32 packet,U32 prior,
                      CohControlState *out,CohControlUpdate *events,U32 *cursor){
 U32 storage[8192]={0};Packet p={0};MotionState motion={0};
 memset(&control_state,0,sizeof(control_state));memset(&fixture_server,0,sizeof(fixture_server));
 memset(&fixture_entity,0,sizeof(fixture_entity));memset(received_pushes,0,sizeof(received_pushes));
 memset(&server_visible_state,0,sizeof(server_visible_state));memset(&cam_info,0,sizeof(cam_info));
 memset(glob_pos,0,sizeof(glob_pos));memset(glob_vel,0,sizeof(glob_vel));
 glob_client_pos_id=glob_falling=glob_plrstate_valid=0;received_count=0;
 fixture_entity.motion=&motion;control_state.server_state=&fixture_server;
 control_state.server_state_pkt_id=control_state.forced_move_pkt_id=control_state.server_pos_pkt_id=prior;
 initBitStream(&p.stream,(U8*)storage,sizeof(storage),Read,aligned,0);memcpy(storage,input,(bits+7)/8);
 p.stream.bitLength=bits;p.id=packet;if(prefix)bsReadBits(&p.stream,prefix);
 playerReceiveControlState(&p);
 memset(out,0,sizeof(*out));memset(events,0,sizeof(*events));out->generation=1;
 out->server_packet=control_state.server_state_pkt_id;out->forced_packet=control_state.forced_move_pkt_id;
 out->physics_position_packet=control_state.server_pos_pkt_id;
 out->server_valid=out->server_packet!=0;out->forced_valid=out->forced_packet!=0;out->physics_valid=out->physics_position_packet!=0;
 out->server.update_id=control_state.received_update_id;
 memcpy(&out->server.speed,fixture_server.speed,12);out->server.speed_back=fixture_server.speed_back;out->server.jump_height=fixture_server.jump_height;
 memcpy(out->server.surface_le,fixture_server.surf_mods,40);
 unsigned flags[]={fixture_server.fly,fixture_server.stun,fixture_server.jumppack,fixture_server.glide,fixture_server.ninja_run,
 fixture_server.walk,fixture_server.beast_run,fixture_server.steam_jump,fixture_server.hover_board,fixture_server.magic_carpet,
 fixture_server.parkour_run,fixture_server.no_physics,fixture_server.hit_stumble,fixture_server.controls_input_ignored,
 fixture_server.shell_disabled,fixture_server.no_ent_collision,fixture_server.no_jump_repeat};
 for(unsigned i=0;i<17;i++)out->server.flags|=flags[i]<<i;
 out->forced.position_id=(U32)glob_client_pos_id;out->forced.falling=(U32)glob_falling;
 memcpy(&out->forced.position,glob_pos,12);memcpy(&out->forced.velocity,glob_vel,12);
 memcpy(&out->forced.pyr,control_state.pyr.cur,12);
 if(control_state.svr_phys.end){
  PhysStep *s=&control_state.svr_phys.step[control_state.svr_phys.end-1];
  out->physics.net_id=(U32)s->net_id;out->physics.has_id=out->physics.position_changed=1;
  memcpy(&out->physics.position,s->pos,12);memcpy(&out->physics.velocity,s->vel,12);
 }
 events->push_count=received_count;
 for(unsigned i=0;i<received_count;i++){
  CohControlPush *to=&events->pushes[i];FuturePush *from=&received_pushes[i];
  to->net_id_start=from->net_id_start;to->physics_ticks=from->phys_tick_remaining;to->abs_time=from->abs_time;
  to->knockback_animation=from->do_knockback_anim;memcpy(&to->velocity,from->add_vel,12);
 }
 *cursor=bsGetCursorBitPosition(&p.stream);
}
