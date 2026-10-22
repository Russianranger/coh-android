/* ArmPort: PhysX (NovodeX) is compiled out on ARM64, and NwRagdoll.cpp with it.
 * entrecv.c still calls these two client functions unconditionally. Without
 * physics no ragdoll is created: server-driven ragdoll poses are not shown,
 * and deletion has nothing to release. Signatures follow NovodeX/NwRagdoll.h.
 */
typedef struct Ragdoll Ragdoll;
typedef struct Entity Entity;

Ragdoll *nwCreateRagdollNoPhysics(Entity *e)
{
	(void)e;
	return 0;
}

void nwDeleteRagdoll(Ragdoll *parentRagdoll)
{
	(void)parentRagdoll;
}
