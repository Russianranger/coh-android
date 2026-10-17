#ifndef COH_CHARACTER_TAIL_H
#define COH_CHARACTER_TAIL_H
#include "../replication/coh_replication.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_CHARACTER_TAIL_TOKENS_MAX 256u
#define COH_CHARACTER_TAIL_FRIENDS_MAX 25u
#define COH_CHARACTER_TAIL_TEXT_MAX (640u*1024u)
#define COH_CHARACTER_TAIL_RAM_MAX (8u*1024u*1024u)
#define COH_CHARACTER_TAIL_STACK_RESERVE 8192u
typedef struct {uint32_t offset,bytes;} CohCharacterTailString;
typedef struct {CohCharacterTailString name;uint32_t value,timer;} CohCharacterRewardToken;
typedef struct {uint32_t selected_top,selected_bottom,tab_bits,divider_word;} CohCharacterChatWindow;
typedef struct {char name[19];uint32_t system_channels[2],user_bits,options,default_channel,default_type;} CohCharacterChatTab;
typedef struct {char name[22];uint32_t options,colors[2];} CohCharacterChatChannel;
typedef struct {CohCharacterTailString command;uint32_t key,modifier;} CohCharacterKeybind;
typedef struct {uint32_t present,dbid,online,class_index,origin_index,map_id;char name[32],map_name[256];} CohCharacterFriend;
typedef struct {uint32_t key_present,key,order_present,order;} CohCharacterCombatMonitor;
typedef struct {
 uint32_t reward_count,active_reward_count;
 CohCharacterRewardToken rewards[COH_CHARACTER_TAIL_TOKENS_MAX],active_rewards[COH_CHARACTER_TAIL_TOKENS_MAX];
 uint32_t lfg,hidden,supergroup_mode,hide_emblem,skills_unlocked,team_buff_display,dock_mode,inspiration_mode,new_features;
 uint32_t help_chat_added,chat_send_channel,user_send_channel,chat_options,primary_chat_minimized;
 CohCharacterChatWindow chat_windows[5];CohCharacterChatTab chat_tabs[20];CohCharacterChatChannel chat_channels[15];
 uint32_t title_the,title_colors[2],title_badge;
 char title_the_text[10],title_common[32],title_origin[32],title_special[128],description[1024],motto[128],comment[128],key_profile[32];
 CohCharacterKeybind keybinds[256];
 uint32_t options_saved,option_words[114],mouse_invert,mouse_speed_word,turn_speed_word;
 uint32_t dividers[8],control_first,control_no_collision,friends_full_update,friend_count;
 CohCharacterFriend friends[COH_CHARACTER_TAIL_FRIENDS_MAX];
 CohCharacterCombatMonitor monitors[10];uint32_t rename;
 uint32_t text_bytes;char text[COH_CHARACTER_TAIL_TEXT_MAX];
 size_t begin_bit,rewards_end_bit,chat_end_bit,keybinds_end_bit,options_end_bit,end_bit;
} CohCharacterTail;
typedef struct {CohCharacterTail candidate;} CohCharacterTailWorkspace;
/* Complete outer character groups5..6 from reward-token count through rename.
 * Raw ordered events only. No rewards, commands, friends, UI/options, dictionaries,
 * entitlement/state application or actor/ACK. Fixed source counts and enum-ordered
 * option widths pinned by source oracle. Chat system arrays byte-align using
 * original bit-array rules. Duplicate/unknown named tokens and sentinel dictionary
 * indices remain explicit. Local token count256 and name1024 limits refuse rather
 * than truncate. Original fixed receiver strings likewise refuse overflow.
 * All floats must be finite. All spans pairwise disjoint; no allocation/retained
 * input. Output/workspace on caller heap/arena. Budget charges input+bothPODs+
 * stackreserve+retained ownership. Failure preserves reader/output atomically.
 * Success is full outer-character raw grammar, NOT enclosing ALLENTS exact end. */
CohStatus coh_character_tail_read(CohRepReader *,CohCharacterTail *,
 CohCharacterTailWorkspace *,size_t budget,size_t retained_bytes);
#ifdef __cplusplus
}
#endif
#endif
