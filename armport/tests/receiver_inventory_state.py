#!/usr/bin/env python3
"""Exercise the actual generic-inventory snapshot writer under sanitizers."""
import json
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    source = (Path(__file__).resolve().parents[1] / 'replay/state.c').read_text()
    formatting = source[source.index('static void out('):source.index('void armportReplayStateInit(')]
    inventory = source[source.index('static void inventory_item('):source.index('static unsigned deletes;')]
    fixture = r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#define CAPACITY 65536
#define check(x) do { if (!(x)) exit(3); } while (0)
static char buffer[CAPACITY]; static size_t used;
typedef struct { int salId; const char *pchName; } SalvageItem;
typedef struct { const SalvageItem *salvage; unsigned amount; } SalvageInventoryItem;
typedef struct { int id; const char *pchName; } Detail, DetailRecipe;
typedef struct { const Detail *item; unsigned amount; } DetailInventoryItem;
typedef struct { const DetailRecipe *recipe; unsigned amount; } RecipeInventoryItem;
typedef struct { int id; const char *name; } ConceptDef;
typedef struct { const ConceptDef *def; float afVars[4]; } ConceptItem;
typedef struct { const ConceptItem *concept; unsigned amount; } ConceptInventoryItem;
typedef struct {
    int salvageInvTotalSlots, storedSalvageInvTotalSlots, recipeInvTotalSlots, auctionInvTotalSlots;
    SalvageInventoryItem **salvageInv, **storedSalvageInv;
    RecipeInventoryItem **recipeInv; DetailInventoryItem **detailInv;
    ConceptInventoryItem **conceptInv;
} Character;
static int eaSize(const void *address) {
    void *items; memcpy(&items, address, sizeof(items));
    return items ? (int)((size_t *)items)[-1] : 0;
}
''' + formatting + inventory + r'''
int main(int argc, char **argv) {
    int mode = argc > 1 ? atoi(argv[1]) : 0;
    unsigned vars[] = {0x80000000U, 0x7fc01234U, 1U, 0x7f800000U};
    SalvageItem salvage = {42, "Salvage"};
    SalvageInventoryItem s = {&salvage, 0xffffffffU}, empty = {NULL, 9};
    Detail detail = {77, "Detail"}; DetailInventoryItem di = {&detail, 3};
    DetailRecipe recipe = {88, "Recipe"}; RecipeInventoryItem ri = {&recipe, 4};
    ConceptDef def = {99, "Concept"}; ConceptItem concept = {&def, {0}};
    ConceptInventoryItem ci = {&concept, 5}, empty_concept = {NULL, 6};
    struct { size_t n; SalvageInventoryItem *v[3]; } sa = {3, {NULL, &empty, &s}};
    struct { size_t n; DetailInventoryItem *v[1]; } da = {1, {&di}};
    struct { size_t n; RecipeInventoryItem *v[1]; } ra = {1, {&ri}};
    struct { size_t n; ConceptInventoryItem *v[3]; } ca = {3, {&ci, NULL, &empty_concept}};
    Character p = {10, 20, 30, 40, sa.v, sa.v, ra.v, da.v, ca.v};
    memcpy(concept.afVars, vars, sizeof(vars));
    if (mode == 1) ri.amount = 8;
    if (mode == 2) sa.n = 8193;
    if (mode == 3) { p.salvageInv = p.storedSalvageInv = NULL;
        p.recipeInv = NULL; p.detailInv = NULL; p.conceptInv = NULL; }
    generic_inventories(&p);
    check(s.amount == 0xffffffffU && empty.amount == 9 && concept.def == &def);
    puts(buffer); return 0;
}
'''
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        (root / 'fixture.c').write_text(fixture)
        subprocess.run([os.environ.get('CC', 'cc'), '-std=c99', '-O1', '-g',
                        '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                        str(root / 'fixture.c'), '-o', str(root / 'fixture')], check=True)
        results = [subprocess.run([str(root / 'fixture'), str(i)], capture_output=True,
                                  text=True, timeout=15) for i in (0, 1, 2, 3, 0)]
        assert [r.returncode for r in results] == [0, 0, 3, 0, 0], [(r.returncode, r.stderr) for r in results]
        assert results[0].stdout == results[4].stdout
        d = json.loads(results[0].stdout)
        assert d['salvage_total'] == 10 and d['stored_salvage_total'] == 20
        assert d['recipe_total'] == 30 and d['auction_total'] == 40
        assert d['salvageInv'] == [None, dict(id=0, name=None, amount=9),
                                   dict(id=42, name='Salvage', amount=0xffffffff)]
        assert d['storedSalvageInv'] == d['salvageInv']
        assert d['recipeInv'] == [dict(id=88, name='Recipe', amount=4)]
        assert d['detailInv'] == [dict(id=77, name='Detail', amount=3)]
        assert d['conceptInv'][0] == dict(amount=5, concept=dict(id=99, name='Concept',
                                        vars_f32_bits=[0x80000000, 0x7fc01234, 1, 0x7f800000]))
        assert d['conceptInv'][1:] == [None, dict(amount=6, concept=None)]
        changed = json.loads(results[1].stdout)
        changed['recipeInv'][0]['amount'] = 4
        assert changed == d
        empty = json.loads(results[3].stdout)
        assert all(empty[k] == [] for k in ('salvageInv', 'storedSalvageInv', 'recipeInv', 'detailInv', 'conceptInv'))
    print('inventory serializer: five typed arrays, null slots/definitions, unsigned amounts, concept F32 bits, capacity fields, mutation sensitivity and bounds pass; ASan/UBSan enabled')


if __name__ == '__main__':
    main()
