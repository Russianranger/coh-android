"""Install the existing reviewed Atlas supplement before private servers start.

The base game-data inventory and schema validation remain unchanged. This is
the same immutable archive used by the client, not new assets or server code.
"""
from pathlib import Path
import shutil
import tempfile

import stage_atlas_supplement as atlas
import smoke_run


def copy_inputs(source, tools):
    """Freeze the two pinned inputs in this run's tools directory."""
    atlas.verify_inputs(source)
    target = tools / 'atlas-supplement'
    target.mkdir()
    for name in atlas.PINS:
        shutil.copyfile(source / name, target / name)
    reviewed = tools / 'atlas-world-supplement-manifest.json'
    shutil.copyfile(atlas.REVIEWED_MANIFEST, reviewed)
    atlas.verify_inputs(target, reviewed)


def stage(source, data, reviewed_manifest):
    """Verify all bytes before a case-aware, collision-rejecting merge."""
    data = Path(data)
    atlas.require(data.is_dir() and not data.is_symlink(), 'Private server data required')
    with tempfile.TemporaryDirectory(prefix='armport-atlas-', dir=data.parent) as temp:
        incoming = Path(temp) / 'data'
        result = atlas.stage(source, incoming, reviewed_manifest)
        # Both trees are private: incoming was just extracted with no symlinks,
        # and the original guest has verified/copied the complete base inventory.
        result['matching_collisions'] = smoke_run.merge_tree(incoming, data, strict=True, copy_files=True)
        result['merged_tree'] = smoke_run.audit_runtime_tree(data)
    result.update(scope='reviewed_atlas_supplement_for_private_server',
                  server_binaries_changed=False, rendered_world_verified=False)
    return result
