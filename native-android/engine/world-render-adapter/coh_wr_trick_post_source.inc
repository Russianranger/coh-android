/* Exact original numeric prefix and independent group-tray statements only. */
static void source_numeric_prefix(TrickInfo *trick, bool shared_memory)
{
    TrickInfo    *dup_trick;
    U8            *c;

    trick->tnode.info = trick;

    c = trick->tnode.trick_rgba;
    if (!(c[0]|c[1]|c[2]))
        memset(trick->tnode.trick_rgba,255,4);
    c = trick->tnode.trick_rgba2;
    if (!(c[0]|c[1]|c[2]))
        memset(trick->tnode.trick_rgba2,255,4);
    trick->alpha_ref = trick->alpha_ref_parser / 255.f;
    if (trick->tex_bias)
        trick->tnode.flags2 |= TRICK2_TEXBIAS;
    if (trick->alpha_ref)
        trick->tnode.flags2 |= TRICK2_ALPHAREF;
    if (trick->shadow_dist)
        trick->tnode.flags2 |= TRICK2_CASTSHADOW;
    if (trick->nightglow_times[0] || trick->nightglow_times[1])
        trick->tnode.flags2 |= TRICK2_NIGHTGLOW;
    if (trick->sway[0] || trick->sway_pitch[0] || trick->sway_roll[0])
        trick->tnode.flags2 |= TRICK2_HAS_SWAY;


    if (trick->texScrollAmt[0][0] || trick->texScrollAmt[0][1])
        trick->tnode.flags2 |= TRICK2_STSCROLL0;
    if (trick->texScrollAmt[1][0] || trick->texScrollAmt[1][1])
        trick->tnode.flags2 |= TRICK2_STSCROLL1;

}
static void source_group_projection(TrickInfo *trick) {
    if (trick->group_flags & GROUP_VIS_TRAY)
        trick->model_flags |= OBJ_FORCEOPAQUE|OBJ_ALLOW_MULTISPLIT;
}
