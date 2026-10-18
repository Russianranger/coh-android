#include "fresh_character_owner.h"
#include "../../session/coh_session_crypto.h"
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

/* This is an expected fixture comparison, never a substitute for Auth data. */
enum { FC_UID = 900001, FC_TOTAL_MS = 30000, FC_CONNECT_MS = 3000, FC_REPLY_MS = 10000 };
struct CohFreshCharacterOwner {
    CohFreshCharacterConfig settings;
    CohFreshCharacterDiagnostics result;
    CohLogin *login;
    CohDbSession *database;
    uint64_t started_at, last_tick;
    uint32_t authorized_uid;
    unsigned in_call, shard_chosen;
    uint8_t new_name[64];
    size_t name_bytes;
};

static int intersect(const void *left, size_t left_size, const void *right, size_t right_size) {
    uintptr_t a = (uintptr_t)left, b = (uintptr_t)right;
    if(left_size > UINTPTR_MAX - a || right_size > UINTPTR_MAX - b) return 1;
    return a < b + right_size && b < a + left_size;
}
static int external_storage(const CohFreshCharacterOwner *owner, const void *p, size_t n) {
    return p && !intersect(owner, sizeof(*owner), p, n) &&
        !intersect(owner->settings.crypto, sizeof(*owner->settings.crypto), p, n);
}
static int localhost(CohNetEndpoint endpoint) {
    return endpoint.address[0] == 127 && endpoint.address[1] == 0 &&
        endpoint.address[2] == 0 && endpoint.address[3] == 1;
}
static int in_progress(const CohFreshCharacterOwner *owner) {
    return owner->result.phase == COH_FRESH_CHARACTER_AUTHENTICATING ||
        owner->result.phase == COH_FRESH_CHARACTER_WAIT_LIST ||
        owner->result.phase == COH_FRESH_CHARACTER_WAIT_OFFER;
}
static int stop_requested(CohCancel cancellation) {
    return cancellation.poll && cancellation.poll(cancellation.context);
}
static void erase_name(CohFreshCharacterOwner *owner) {
    coh_auth_wipe(owner->new_name, sizeof(owner->new_name));
    owner->name_bytes = 0;
    owner->result.private_name_wiped = 1;
}
static void release_components(CohFreshCharacterOwner *owner) {
    /* Only final phases are sampled here. Preserve the real pre-cleanup phase. */
    if(owner->database) {
        coh_db_session_cancel(owner->database);
        owner->result.cleanup_cancel_close_used = 1;
        owner->result.final_db_phase = coh_db_session_phase(owner->database);
        coh_db_session_destroy(owner->database);
        owner->database = NULL;
    }
    if(owner->login) {
        CohLoginDiagnostics last = {0};
        coh_login_close(owner->login);
        coh_login_diagnostics(owner->login, &last);
        owner->result.final_auth_phase = last.state;
        coh_login_destroy(owner->login);
        owner->login = NULL;
    }
    erase_name(owner);
    owner->authorized_uid = 0;
    owner->result.controllers_destroyed = 1;
}
static CohStatus terminal(CohFreshCharacterOwner *owner, CohFreshCharacterPhase phase,
    CohFreshCharacterFailure failure, CohStatus status) {
    release_components(owner);
    owner->result.phase = phase;
    owner->result.failure = failure;
    owner->result.status = status;
    return status;
}
static CohStatus refused(CohFreshCharacterOwner *owner, CohFreshCharacterFailure failure, CohStatus status) {
    return terminal(owner, COH_FRESH_CHARACTER_FAILED, failure, status);
}
static CohStatus cancelled(CohFreshCharacterOwner *owner) {
    return terminal(owner, COH_FRESH_CHARACTER_CANCELLED, COH_FRESH_CHARACTER_FAILURE_CANCEL, COH_CANCELLED);
}
static int shard_is_expected(const CohAuthShard *shard) {
    CohNetEndpoint endpoint = {{0}, 0};
    memcpy(endpoint.address, shard->ipv4, sizeof(endpoint.address));
    return shard->id == 1 && shard->status == 1 && shard->port == 7000 && localhost(endpoint);
}
static int clean_auth(const CohLoginDiagnostics *d, CohLoginState state, uint64_t frames) {
    return d->state == state && d->protocol == COH_AUTH_OUROBOROS2 && d->received_frames == frames &&
        !d->pending_send_bytes && !d->buffered_receive_bytes && !d->password_retained &&
        !d->remote_failure_command && !d->remote_failure_reason && !d->last_system_error;
}
CohFreshCharacterOwner *coh_fresh_character_create(const CohFreshCharacterConfig *settings) {
    if(!settings || !localhost(settings->auth_endpoint) || settings->auth_endpoint.port < 20000 ||
       settings->auth_endpoint.port > 59999 || !settings->connect_id || settings->owned_map_id != 1 ||
       !localhost(settings->owned_map_endpoint) || settings->owned_map_endpoint.port != 7001 ||
       !settings->crypto || !settings->crypto->keypair || !settings->crypto->shared ||
       !settings->crypto->md5 || !settings->crypto->sha512 || !settings->crypto->rsa_oaep_sha1 ||
       intersect(settings, sizeof(*settings), settings->crypto, sizeof(*settings->crypto))) return NULL;
    CohFreshCharacterOwner *owner = calloc(1, sizeof(*owner));
    if(!owner) return NULL;
    owner->settings = *settings;
    owner->result.provisional_development_policy = 1;
    owner->result.development_skip_requested = 1;
    owner->result.private_name_wiped = 1;
    owner->result.bridge_temporaries_wiped = 1;
    owner->result.controllers_destroyed = 1;
    return owner;
}
CohStatus coh_fresh_character_begin(CohFreshCharacterOwner *owner, const char *account,
    const char *password, CohBytes name, uint64_t now) {
    if(!owner) return COH_INVALID;
    if(owner->in_call || owner->result.begin_attempted || owner->result.phase != COH_FRESH_CHARACTER_IDLE)
        return COH_STATE;
    owner->in_call = 1;
    owner->result.begin_attempted = 1;
    owner->result.phase = COH_FRESH_CHARACTER_AUTHENTICATING;
    owner->started_at = owner->last_tick = now;
    CohStatus status = COH_INVALID;
    if(!external_storage(owner, account, 15) || !external_storage(owner, password, 17) ||
       !name.size || name.size > 63 || !external_storage(owner, name.data, name.size)) goto bad_input;
    for(size_t i = 0; i < name.size; ++i)
        if(name.data[i] < 32 || name.data[i] > 126) goto bad_input;
    memcpy(owner->new_name, name.data, name.size);
    owner->name_bytes = name.size;
    owner->result.private_name_wiped = 0;
    CohLoginConfig config = coh_login_default_config(owner->settings.crypto);
    config.connect_timeout_ms = FC_CONNECT_MS;
    config.reply_timeout_ms = FC_REPLY_MS;
    config.receive_budget = 4;
    owner->login = coh_login_create(&config);
    if(!owner->login) {
        status = refused(owner, COH_FRESH_CHARACTER_FAILURE_AUTH, COH_LIMIT);
    } else {
        owner->result.controllers_destroyed = 0;
        status = coh_login_begin(owner->login, owner->settings.auth_endpoint, account, password, 0, 0, now);
        CohLoginDiagnostics observation = {0};
        coh_login_diagnostics(owner->login, &observation);
        owner->result.observed_auth_phase = observation.state;
        if(status != COH_OK) status = refused(owner, COH_FRESH_CHARACTER_FAILURE_INPUT, status);
    }
    owner->in_call = 0;
    return status;
bad_input:
    status = refused(owner, COH_FRESH_CHARACTER_FAILURE_INPUT, status);
    owner->in_call = 0;
    return status;
}
static CohStatus select_registered_shard(CohFreshCharacterOwner *owner, uint64_t now,
    const CohLoginDiagnostics *observation, CohCancel cancellation) {
    if(owner->result.shard_attempted) return refused(owner, COH_FRESH_CHARACTER_FAILURE_SHARD, COH_STATE);
    owner->result.shard_attempted = 1;
    CohAuthShards offered = {0};
    CohStatus status = coh_login_shards(owner->login, &offered);
    if(status == COH_OK && (!clean_auth(observation, COH_LOGIN_SHARDS_READY, 3) ||
       offered.count != 1 || !shard_is_expected(&offered.shards[0]))) status = COH_STATE;
    if(status == COH_OK && stop_requested(cancellation)) status = COH_CANCELLED;
    if(status == COH_OK) status = coh_login_choose(owner->login, 1, now);
    coh_auth_wipe(&offered, sizeof(offered));
    if(status == COH_CANCELLED) return cancelled(owner);
    if(status != COH_OK) return refused(owner, COH_FRESH_CHARACTER_FAILURE_SHARD, status);
    owner->shard_chosen = 1;
    return COH_OK;
}
static CohDbSessionConfig database_config(const CohFreshCharacterOwner *owner) {
    CohDbSessionConfig config = {0};
    config.transport.link = coh_net_default_config();
    config.transport.link.connect_timeout_ms = FC_CONNECT_MS;
    config.transport.link.idle_timeout_ms = FC_REPLY_MS;
    config.transport.link.fragment_timeout_ms = FC_REPLY_MS;
    config.transport.local = (CohNetEndpoint){{127, 0, 0, 1}, 0};
    config.transport.peer = (CohNetEndpoint){{127, 0, 0, 1}, 7000};
    config.transport.receive_budget = 4;
    config.transport.key_exchange = coh_session_key_exchange;
    config.transport.key_context = (void *)(uintptr_t)owner->settings.crypto;
    config.transport.encryption_required = 1;
    config.request_timeout_ms = FC_REPLY_MS;
    return config;
}
static CohStatus transfer_actual_authorization(CohFreshCharacterOwner *owner, uint64_t now,
    const CohLoginDiagnostics *observation, CohCancel cancellation) {
    if(owner->result.bridge_attempted) return refused(owner, COH_FRESH_CHARACTER_FAILURE_GRANT, COH_STATE);
    owner->result.bridge_attempted = 1;
    owner->result.bridge_temporaries_wiped = 0;
    CohLoginAuthorization authorization = {0};
    CohDbLogin login = {0};
    CohDbAuthReceipt receipt = {0};
    CohStatus status = coh_login_authorization(owner->login, &authorization);
    CohFreshCharacterFailure failure = COH_FRESH_CHARACTER_FAILURE_GRANT;
    if(status == COH_OK && (!owner->shard_chosen || !clean_auth(observation, COH_LOGIN_AUTHORIZED, 4) ||
       authorization.protocol != COH_AUTH_OUROBOROS2 || authorization.play.shard_id != 1 ||
       authorization.play.user_id != FC_UID || !authorization.play.game_key ||
       !shard_is_expected(&authorization.shard) || !authorization.account_name[0] ||
       !memchr(authorization.account_name, 0, sizeof(authorization.account_name)))) status = COH_STATE;
    if(status == COH_OK) {
        owner->result.actual_grant_verified = 1;
        owner->authorized_uid = authorization.play.user_id;
        memcpy(login.account, authorization.account_name, sizeof(login.account));
        login.user_id = authorization.play.user_id;
        login.cookie = authorization.play.game_key;
        login.protocol_version = COH_DB_PROTOCOL_VERSION;
        login.no_version_check = 1;
        static const char development_label[] = "dev:owned-fresh-character";
        memcpy(login.patch_version, development_label, sizeof(development_label));
        memcpy(login.executable_checksum, owner->settings.executable_checksum, sizeof(login.executable_checksum));
        memcpy(receipt.account, authorization.account_name, sizeof(receipt.account));
        receipt.user_id = authorization.play.user_id;
        receipt.game_cookie = authorization.play.game_key;
        receipt.generation = 1;
        receipt.verified = 1;
        if(stop_requested(cancellation)) status = COH_CANCELLED;
        if(status == COH_OK) {
            failure = COH_FRESH_CHARACTER_FAILURE_DB_BEGIN;
            CohDbSessionConfig config = database_config(owner);
            owner->database = coh_db_session_create(&config);
            status = owner->database ? coh_db_session_begin(owner->database, &login, &receipt,
                owner->settings.connect_id, now) : COH_LIMIT;
            if(status == COH_OK) {
                CohDbSessionDiagnostics d = {0};
                coh_db_session_diagnostics(owner->database, &d);
                owner->result.observed_db_phase = d.phase;
                if(d.generation != 1 || d.local_development_auth || !d.server_identity_bound)
                    status = COH_STATE;
                else {
                    owner->result.session_generation = d.generation;
                    owner->result.receipt_generation = receipt.generation;
                }
            }
        }
    }
    coh_auth_wipe(&authorization, sizeof(authorization));
    coh_db_wipe(&login, sizeof(login));
    coh_db_wipe(&receipt, sizeof(receipt));
    owner->result.bridge_temporaries_wiped = 1;
    if(status == COH_CANCELLED) return cancelled(owner);
    if(status != COH_OK) return refused(owner, failure, status);
    owner->result.phase = COH_FRESH_CHARACTER_WAIT_LIST;
    return COH_OK;
}
static int database_identity_ok(const CohFreshCharacterOwner *owner, const CohDbSessionDiagnostics *d) {
    return d->generation == owner->result.session_generation && d->generation == 1 &&
        !d->local_development_auth && d->server_identity_bound == 1 &&
        !d->queue_updates && !d->unsupported && d->login_requests <= 1 && d->player_lists <= 1;
}
static int empty_slot_from_list(const CohDbPlayers *players, uint32_t uid, uint32_t *slot) {
    if(!uid || players->user_id != uid || !players->max_slots || players->max_slots > COH_DB_SLOTS_MAX ||
       !players->base_slots || players->base_slots > players->max_slots || players->selectable_count) return 0;
    unsigned found = 0;
    for(uint32_t i = 0; i < players->max_slots; ++i) {
        const CohDbPlayer *candidate = &players->players[i];
        if(candidate->wire_slot != i || candidate->empty != 1 || candidate->slot_lock ||
           candidate->visitor || candidate->invalid) return 0;
        if(!found) { *slot = i; found = 1; }
    }
    return found == 1;
}
static CohStatus request_empty_slot(CohFreshCharacterOwner *owner, uint64_t now,
    const CohDbSessionDiagnostics *d, CohCancel cancellation) {
    CohDbPlayers players = {0};
    uint32_t selected = 0;
    CohStatus status = coh_db_session_players(owner->database, &players);
    if(status == COH_OK && (d->login_requests != 1 || d->player_lists != 1 ||
       !empty_slot_from_list(&players, owner->authorized_uid, &selected))) status = COH_STATE;
    coh_db_wipe(&players, sizeof(players));
    if(status != COH_OK) return refused(owner, COH_FRESH_CHARACTER_FAILURE_LIST, status);
    owner->result.matching_empty_list_verified = 1;
    if(owner->result.creation_attempted) return refused(owner, COH_FRESH_CHARACTER_FAILURE_CREATE, COH_STATE);
    owner->result.creation_attempted = 1;
    CohDbEmptyCreationRequest request = {0};
    request.wire_slot = selected;
    request.name = (CohBytes){owner->new_name, owner->name_bytes};
    request.location = COH_DB_CREATE_PRIMAL_HERO;
    request.expected_session_generation = d->generation;
    request.expected_receipt_generation = owner->result.receipt_generation;
    request.expected_list_generation = d->player_lists;
    if(stop_requested(cancellation)) status = COH_CANCELLED;
    if(status == COH_OK) status = coh_db_session_create_empty(owner->database, &request, now);
    coh_db_wipe(&request, sizeof(request));
    erase_name(owner);
    if(status == COH_CANCELLED) return cancelled(owner);
    if(status != COH_OK) return refused(owner, COH_FRESH_CHARACTER_FAILURE_CREATE, status);
    owner->result.creation_request_queued = 1;
    owner->result.persistent_allocation_possible = 1;
    CohDbSessionDiagnostics after = {0};
    coh_db_session_diagnostics(owner->database, &after);
    owner->result.observed_db_phase = after.phase;
    if(!database_identity_ok(owner, &after) || after.phase != COH_DB_WAIT_MAP || after.choices != 1 ||
       after.handoffs || after.selection_generation != 1)
        return refused(owner, COH_FRESH_CHARACTER_FAILURE_CREATE, COH_STATE);
    owner->result.selection_generation = after.selection_generation;
    owner->result.phase = COH_FRESH_CHARACTER_WAIT_OFFER;
    return COH_OK;
}
static CohStatus retire_allocation_offer(CohFreshCharacterOwner *owner, CohCancel cancellation) {
    if(owner->result.retirement_attempted) return refused(owner, COH_FRESH_CHARACTER_FAILURE_RETIRE, COH_STATE);
    owner->result.retirement_attempted = 1;
    CohDbCreatedOfferPolicy policy = {0};
    CohDbCreatedOfferSummary summary = {0};
    policy.expected_session_generation = owner->result.session_generation;
    policy.expected_receipt_generation = owner->result.receipt_generation;
    policy.expected_selection_generation = owner->result.selection_generation;
    policy.owned_map_id = owner->settings.owned_map_id;
    policy.owned_map_endpoint = owner->settings.owned_map_endpoint;
    CohStatus status = stop_requested(cancellation) ? COH_CANCELLED :
        coh_db_session_retire_created_offer(owner->database, &policy, &summary);
    if(status == COH_OK && (summary.server_allocated_offer_observed != 1 || summary.private_offer_retired != 1 ||
       summary.container_uninitialized != 1 || summary.persistent_rollback_claimed ||
       summary.session_generation != owner->result.session_generation ||
       summary.receipt_generation != owner->result.receipt_generation ||
       summary.selection_generation != owner->result.selection_generation ||
       coh_db_session_phase(owner->database) != COH_DB_CANCELLED)) status = COH_STATE;
    coh_db_wipe(&policy, sizeof(policy));
    coh_db_wipe(&summary, sizeof(summary));
    if(status == COH_CANCELLED) return cancelled(owner);
    if(status != COH_OK) return refused(owner, COH_FRESH_CHARACTER_FAILURE_RETIRE, status);
    owner->result.allocated_offer_observed = 1;
    owner->result.private_offer_retired = 1;
    owner->result.container_uninitialized = 1;
    release_components(owner);
    if(stop_requested(cancellation)) return cancelled(owner);
    return terminal(owner, COH_FRESH_CHARACTER_COMPLETE, COH_FRESH_CHARACTER_FAILURE_NONE, COH_OK);
}
static CohStatus advance_database(CohFreshCharacterOwner *owner, uint64_t now, CohCancel cancellation) {
    CohStatus status = coh_db_session_service(owner->database, now, cancellation);
    CohDbSessionDiagnostics d = {0};
    coh_db_session_diagnostics(owner->database, &d);
    owner->result.observed_db_phase = d.phase;
    if(status == COH_CANCELLED) return cancelled(owner);
    if(status != COH_OK) return refused(owner, COH_FRESH_CHARACTER_FAILURE_DB, status);
    if(!database_identity_ok(owner, &d))
        return refused(owner, COH_FRESH_CHARACTER_FAILURE_DB, d.unsupported ? COH_UNSUPPORTED : COH_STATE);
    if(owner->result.phase == COH_FRESH_CHARACTER_WAIT_LIST) {
        if(d.selection_generation || d.choices || d.handoffs)
            return refused(owner, COH_FRESH_CHARACTER_FAILURE_LIST, COH_STATE);
        if(d.phase == COH_DB_CHARACTERS) return request_empty_slot(owner, now, &d, cancellation);
        if(d.phase == COH_DB_CONNECTING || d.phase == COH_DB_WAIT_PLAYERS) return COH_OK;
        return refused(owner, COH_FRESH_CHARACTER_FAILURE_LIST, COH_STATE);
    }
    if(d.login_requests != 1 || d.player_lists != 1 || d.choices != 1 || d.handoffs > 1 ||
       d.selection_generation != owner->result.selection_generation)
        return refused(owner, COH_FRESH_CHARACTER_FAILURE_OFFER, COH_STATE);
    if(d.phase == COH_DB_WAIT_MAP && !d.handoffs) return COH_OK;
    if(d.phase == COH_DB_HANDOFF_READY && d.handoffs == 1) return retire_allocation_offer(owner, cancellation);
    return refused(owner, COH_FRESH_CHARACTER_FAILURE_OFFER, COH_STATE);
}
CohStatus coh_fresh_character_service(CohFreshCharacterOwner *owner, uint64_t now, CohCancel cancellation) {
    if(!owner) return COH_INVALID;
    if(owner->in_call || !in_progress(owner)) return COH_STATE;
    owner->in_call = 1;
    CohStatus status;
    if(now < owner->last_tick) status = refused(owner, COH_FRESH_CHARACTER_FAILURE_INPUT, COH_INVALID);
    else if(now - owner->started_at >= FC_TOTAL_MS)
        status = refused(owner, COH_FRESH_CHARACTER_FAILURE_TIMEOUT, COH_STATE);
    else if(stop_requested(cancellation)) status = cancelled(owner);
    else {
        owner->last_tick = now;
        if(owner->result.phase != COH_FRESH_CHARACTER_AUTHENTICATING)
            status = advance_database(owner, now, cancellation);
        else {
            status = coh_login_service(owner->login, now, cancellation);
            CohLoginDiagnostics d = {0};
            coh_login_diagnostics(owner->login, &d);
            owner->result.observed_auth_phase = d.state;
            if(status == COH_CANCELLED) status = cancelled(owner);
            else if(status != COH_OK) status = refused(owner, COH_FRESH_CHARACTER_FAILURE_AUTH, status);
            else if(d.state == COH_LOGIN_SHARDS_READY) status = select_registered_shard(owner, now, &d, cancellation);
            else if(d.state == COH_LOGIN_AUTHORIZED) status = transfer_actual_authorization(owner, now, &d, cancellation);
            else if(d.state < COH_LOGIN_CONNECTING || d.state > COH_LOGIN_WAIT_PLAY)
                status = refused(owner, COH_FRESH_CHARACTER_FAILURE_AUTH, COH_STATE);
        }
    }
    owner->in_call = 0;
    return status;
}
CohStatus coh_fresh_character_timeout(CohFreshCharacterOwner *owner) {
    if(!owner) return COH_INVALID;
    if(owner->in_call || !in_progress(owner)) return COH_STATE;
    owner->in_call = 1;
    CohStatus status = refused(owner, COH_FRESH_CHARACTER_FAILURE_TIMEOUT, COH_STATE);
    owner->in_call = 0;
    return status;
}
CohStatus coh_fresh_character_cancel(CohFreshCharacterOwner *owner) {
    if(!owner) return COH_INVALID;
    if(owner->in_call || !in_progress(owner)) return COH_STATE;
    owner->in_call = 1;
    CohStatus status = cancelled(owner);
    owner->in_call = 0;
    return status;
}
CohStatus coh_fresh_character_close(CohFreshCharacterOwner *owner) {
    if(!owner) return COH_INVALID;
    if(owner->in_call) return COH_STATE;
    owner->in_call = 1;
    if(owner->result.phase == COH_FRESH_CHARACTER_IDLE || in_progress(owner))
        (void)terminal(owner, COH_FRESH_CHARACTER_CLOSED, COH_FRESH_CHARACTER_FAILURE_CLOSE, COH_STATE);
    owner->in_call = 0;
    return COH_OK;
}
CohStatus coh_fresh_character_destroy(CohFreshCharacterOwner **slot) {
    if(!slot) return COH_INVALID;
    CohFreshCharacterOwner *owner = *slot;
    if(!owner) return COH_OK;
    if(owner->in_call) return COH_STATE;
    if(!external_storage(owner, slot, sizeof(*slot))) return COH_INVALID;
    (void)coh_fresh_character_close(owner);
    coh_auth_wipe(owner, sizeof(*owner));
    free(owner);
    *slot = NULL;
    return COH_OK;
}
CohStatus coh_fresh_character_diagnostics(const CohFreshCharacterOwner *owner, CohFreshCharacterDiagnostics *out) {
    if(!owner || !out) return COH_INVALID;
    if(owner->in_call) return COH_STATE;
    if(!external_storage(owner, out, sizeof(*out))) return COH_INVALID;
    *out = owner->result;
    return COH_OK;
}
