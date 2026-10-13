"""Admission tests using captured inventories; no native execution is simulated."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
sys.path.insert(0, str(ROOT/'android/guest'))
import prepare_native_startup_reuse_fixture as fixture

# Exact inventory records extracted from the control in failed native capture
# 38350025346. This historical evidence is deliberately independent of the
# module's EXPECTED_DELTA and is available without downloading an artifact in CI.
CAPTURED_INVENTORIES = json.loads(r'''{
  "after":{
    "data/bin/BodyParts.bin":{
      "bytes":2584,
      "sha256":"b0955c46731ed0cb54ad01d96015b301e583bd0224f8d872f50cfefeb08f6beb"
    },
    "data/bin/Cards.bin":{
      "bytes":69268,
      "sha256":"000bf30499c3601238395f3abfe65dc0348377265ae475adea88fc9919ccc9fa"
    },
    "data/bin/CustomCritterRewardMods.bin":{
      "bytes":236,
      "sha256":"197e85b8715f14d464769489c9155969550288b727d88c48434e3b313eb9041d"
    },
    "data/bin/InvBaseDetail.bin":{
      "bytes":77652,
      "sha256":"80990b0300deab77613b2ab8a0abf56ecbe4e14840346a79fad17283d228e75d"
    },
    "data/bin/InvConcept.bin":{
      "bytes":18620,
      "sha256":"8ee9a606ecb4f341c7bceb7717c77da20caabe1a342606698fac98db726a01e0"
    },
    "data/bin/InvRecipe.bin":{
      "bytes":929768,
      "sha256":"f772a8556efe8119799c0691e2ed70b34f422406fb4bd1368110f3af960b028c"
    },
    "data/bin/InvSalvage.bin":{
      "bytes":11284,
      "sha256":"eb65b811238a17be8311d882c2b548b734da1e9f65f9af7ab882d468ff4b939c"
    },
    "data/bin/InvStoredSalvage.bin":{
      "bytes":11140,
      "sha256":"cc9cc4c7a81fadcf69abdaa2dcd275f2ae0b1f81fd4813785d8dd026d7675abd"
    },
    "data/bin/LoyaltyReward.bin":{
      "bytes":8140,
      "sha256":"3bf7e0a0915736660b693a12eff038934d6ab25710f36eb88364d601f3036819"
    },
    "data/bin/PC_Def_Animation.bin":{
      "bytes":7004,
      "sha256":"3629065439d2a0e0cff10bd8e2801078c95f87bd0e436b3c45d84d7b40877753"
    },
    "data/bin/PC_Def_Contacts.bin":{
      "bytes":29144,
      "sha256":"84feed47eaf155c90c07e90acc6be4e9eb6964e28ab6d9bf85ddbd5838d857ed"
    },
    "data/bin/PC_Def_DestructObject.bin":{
      "bytes":2024,
      "sha256":"df4bc54596dced71c94b33d9a869abb17996a5a32ce1fe4aaf2419c54f2ee315"
    },
    "data/bin/PC_Def_Entities.bin":{
      "bytes":91768,
      "sha256":"b6c46354cfcdaf85baaff72ea1dea8540c8675e0ca939fe3f31b611ef13dcaf7"
    },
    "data/bin/PC_Def_MapSets.bin":{
      "bytes":1484,
      "sha256":"2fc050c57a00f4ca13f23d311b5e1e35434bc9b1a839ffd7a7a35a260fef43b8"
    },
    "data/bin/PC_Def_MapUnique.bin":{
      "bytes":23432,
      "sha256":"cf2a2aee0709220098723e2f64691d3af2ec0ec108f30e4b903aca9bf7ccfbd7"
    },
    "data/bin/PC_Def_NonSelectable_Entities.bin":{
      "bytes":25952,
      "sha256":"6e9672bc0bac7c365bf23c2dc82cf2a276f644d8a94777a264454b2495c2a7bf"
    },
    "data/bin/PC_Def_Objects.bin":{
      "bytes":3952,
      "sha256":"d661cea6776964194af09c5f9f383d423cfef8208c06cc2c3d92b69fb0cff6d3"
    },
    "data/bin/PC_Def_Sequencer_Anims.bin":{
      "bytes":19912,
      "sha256":"17253148edec82d5e373883997972be2130657dc028dd1c71a39105497789fe3"
    },
    "data/bin/PC_Def_UI.bin":{
      "bytes":75552,
      "sha256":"d6c1ca0ca4c82243cca6ebb1ddd8b2db13427df26de9e3fd3bfd62dab24515ac"
    },
    "data/bin/PC_Def_Unlockable_Content.bin":{
      "bytes":22260,
      "sha256":"7e8c4ca2c579b314bf22f6433d7fbd72197278e1f2a9f086a56f76cdc5e18593"
    },
    "data/bin/PopHelp.bin":{
      "bytes":6632,
      "sha256":"8da203d500c8d518ea7a7c8305fa2ed1aa50dbc5628b7d8c51456f6fc0ada9e5"
    },
    "data/bin/Proficiencies.bin":{
      "bytes":2748,
      "sha256":"24837a0390efcc3f7be2696c49514998f74df0aca9c07de6ec5c24fd8f32188b"
    },
    "data/bin/ProficiencyIds.bin":{
      "bytes":704,
      "sha256":"6d3e893c0b7591935aad9c7422bc681e2f42af5c5850d79ae50d5b3b69c4002f"
    },
    "data/bin/Salvage.bin":{
      "bytes":70568,
      "sha256":"bb351fc475d654578d8f613c38a07d2fb8bb05424853114a80c1fccc68b054ee"
    },
    "data/bin/VillainCostume.bin":{
      "bytes":28743996,
      "sha256":"94f2d86ce15785d8a4d69e269f8b495bb1d1982b484b19853babbb559c209cca"
    },
    "data/bin/VillainDef.bin":{
      "bytes":16417580,
      "sha256":"0fbf7d87d17c7f682613753fc2ed4d1541b8ba4e95873da79003db37f0e159eb"
    },
    "data/bin/VillainGroups.bin":{
      "bytes":14464,
      "sha256":"c9f8f220be77ffcd71abf27340e71b148e6a83adce37f517c77ab2896dcab44b"
    },
    "data/bin/arenamaps.bin":{
      "bytes":1252,
      "sha256":"33deb39c44e96a85e2344df91e1b9f91203dd1f61d3bd00414279705b610ea4d"
    },
    "data/bin/attrib_descriptions.bin":{
      "bytes":5892,
      "sha256":"20f770f406e661050434284e4253f721699df2112ea4481de66b50146304c132"
    },
    "data/bin/attrib_names.bin":{
      "bytes":10592,
      "sha256":"92daf1ec706f21b9a2f1f57d1ba941be43d4ed16b3f48c4e5028ac7e79162345"
    },
    "data/bin/auctionconfig.bin":{
      "bytes":80,
      "sha256":"831cb9df5b09674453522e5d3f0d0fe10cfd7a3dbeed6fdd112809330a86a90b"
    },
    "data/bin/badges.bin":{
      "bytes":586324,
      "sha256":"c12387e003414c2f584469c29eb1b8f48c25d53749d77e6b63bbb0be908aabe9"
    },
    "data/bin/baserecipes.bin":{
      "bytes":12492600,
      "sha256":"065827aabf290427dbef231735ba4a9081be5e32cf4caf1a2815250f9ccfd386"
    },
    "data/bin/baseupkeep.bin":{
      "bytes":200,
      "sha256":"f8c82217241baa3e5e5031dcbbfb18f533748d3e195205fbef42bd44f2257c33"
    },
    "data/bin/behaviors.bin":{
      "bytes":4198644,
      "sha256":"d2e7eaf268bf4d5beeb60876b727d9738ef1b42494d1ab78b480d1e07f788056"
    },
    "data/bin/boost_effect_above.bin":{
      "bytes":96,
      "sha256":"04c0643936f30f0c445899564c8b99c65ae933a1a59eab71fd1be2ba7560ac02"
    },
    "data/bin/boost_effect_below.bin":{
      "bytes":96,
      "sha256":"f888e14a84b042ed6f498aa800ffcd9c089cc26441a2660aa07f53500b418f8e"
    },
    "data/bin/boost_effect_boosters.bin":{
      "bytes":104,
      "sha256":"cc295ce81cd8dbabcd658dafb7f5043bbb524d6f3694d2c14d33ca118a326c35"
    },
    "data/bin/boostsets.bin":{
      "bytes":2275580,
      "sha256":"7af712b44bcbb93c18c45d42d21cb12bd7946c57506858f2f42c1070bb818c6c"
    },
    "data/bin/capes.bin":{
      "bytes":97568,
      "sha256":"9d34b0a7a2c22c7f4e21080f9aa5b36f468b7d2e0c06ca4487488a95b36c9a62"
    },
    "data/bin/chestGeoLink.bin":{
      "bytes":1108,
      "sha256":"46606cfe37efee7e2da2ad6a008a5dfea9bd4c30cbbb5fcd6eb07923d626f0e8"
    },
    "data/bin/classes.bin":{
      "bytes":1219292,
      "sha256":"91af1ca0b304d77e56f356d54e1a880309b910c40f1729672cc0af1b83dd6733"
    },
    "data/bin/clothColInfo.bin":{
      "bytes":42792,
      "sha256":"adcc645aed172f088f35683be662e09ddddc88948dc7bb3664a627459d4445eb"
    },
    "data/bin/clothWindInfo.bin":{
      "bytes":1548,
      "sha256":"0e9e1b22c8b4acd8bf1549b63571a05aebc2a619d7fa9355a06575aca7fd1385"
    },
    "data/bin/combine_booster_chances.bin":{
      "bytes":104,
      "sha256":"1bdae93fe8a14f45e0f08e0eb4cf590616ff6676c8e7c8bdc356c14e09a5a1fd"
    },
    "data/bin/combine_chances.bin":{
      "bytes":160,
      "sha256":"041f1d89c637566b170ef267f990f41405b7b7e3931cc9d730df5ea8c022cfeb"
    },
    "data/bin/combine_same_set_chances.bin":{
      "bytes":168,
      "sha256":"dd6f943d9c40f55f2dc322acaf3ff8bc77330f360df2ebd0a6885000fbf120b3"
    },
    "data/bin/command.bin":{
      "bytes":5984,
      "sha256":"cb183ffbe69e17d513b2e8cd0f208de8d88b22ae4034be4134fea74d73647070"
    },
    "data/bin/conversionsets.bin":{
      "bytes":1304,
      "sha256":"f49989a4537a4b9395a9b77dbd7f69d69d8132dc134a12fbe7a06aef021a1888"
    },
    "data/bin/costume.bin":{
      "bytes":17691352,
      "sha256":"10ef7562156be60bd1ef3c437c3b46d10b36b6b265129c10f39d25c4a4df5a77"
    },
    "data/bin/costumeWeaponStances.bin":{
      "bytes":528,
      "sha256":"9980bb27731f81baa8a49d64cb26e538581e448cef878fd5d8f962cad617101e"
    },
    "data/bin/defaultBodyCfg.bin":{
      "bytes":972,
      "sha256":"e1ddc4c739df802d5498d3e70d6919c1b8f8ea2e2986c739c7a5603789f82202"
    },
    "data/bin/defnames.bin":{
      "bytes":3300312,
      "sha256":"cab5eb006413fdf355586b85765d7bfdecca082b687c1338e78b9eeb17b29fc7"
    },
    "data/bin/depts.bin":{
      "bytes":29420,
      "sha256":"eb60fe990086e4b86d60ddbd889a80e9254efc4586e4d1e6c52f7a862b5380c0"
    },
    "data/bin/detailcats.bin":{
      "bytes":1108,
      "sha256":"b3c0f24047dd138017ba7870d6652a5348f98535f807e8b54eabbebfceb4cbe4"
    },
    "data/bin/details.bin":{
      "bytes":401216,
      "sha256":"11e5104e0210fa5cbbc910932e5df461a34853e9a30d43f890d31510cdf2ce28"
    },
    "data/bin/dim_returns.bin":{
      "bytes":864,
      "sha256":"cf81588dc98b4264a5f4e27b86300d848363781834c81a8423f5ce6c74bd0c19"
    },
    "data/bin/ent_types.bin":{
      "bytes":1444116,
      "sha256":"4bb44025fda13d11c03d200362c55f51dec346d60e195ded4ecaed38026ebf67"
    },
    "data/bin/exemplar_handicaps.bin":{
      "bytes":892,
      "sha256":"626456e3797195e8d79ff56e2ce742e3a581b38d4399400affb43bb488f8cafb"
    },
    "data/bin/experience.bin":{
      "bytes":512,
      "sha256":"1295f7e7ad69f49aa9187bf7a97f8fa4335af78df0bd778dcbc28d776669a4d0"
    },
    "data/bin/fxinfo.bin":{
      "bytes":58505496,
      "sha256":"3b1af6d146db65aa2a00fa9dbe4502776409cdea15f94f717e5455a3cda5fe70"
    },
    "data/bin/items.bin":{
      "bytes":4542044,
      "sha256":"80e45680f9a22ac49ab1654a98c3389a5a2763f36bbd22d0470cd616c617e824"
    },
    "data/bin/kb.bin":{
      "bytes":12240,
      "sha256":"af3a2dfed7f4d1deb6cad00e8beae0c9b3a9ea8777f62961258bd7dc3a9c04bd"
    },
    "data/bin/kbkorea.bin":{
      "bytes":12252,
      "sha256":"e8bea925c9c4dbe77e8db6529c2a0dbd0dcfa86e460c9a92685f1dc1988edecc"
    },
    "data/bin/lods.bin":{
      "bytes":1059016,
      "sha256":"13800255781138248226340be316cd628e98800d9ba889fe1aecc902e483b66a"
    },
    "data/bin/map.bin":{
      "bytes":5600,
      "sha256":"5e64f9b0903a3bbfd163ef6ec62f40ad95e55be3c85c7a7742d53d788d336e49"
    },
    "data/bin/mapspecs.bin":{
      "bytes":164840,
      "sha256":"238b6876148ff6f19cc8f835ee36b8a9fe0b09a5d13601eb8adb5a3d858f077e"
    },
    "data/bin/mapstats.bin":{
      "bytes":1542744,
      "sha256":"b14c208848ef59529ceeb592a1c4a4e167d7a62683a13c9d1536b5166d0b44a8"
    },
    "data/bin/menuAnimations.bin":{
      "bytes":1804,
      "sha256":"a2dc887e6aeced481e4fc1bf556c50632b302e82f9e0fdfc7f2c49fee92e33d2"
    },
    "data/bin/minimap.bin":{
      "bytes":13945296,
      "sha256":"a9a2ba27bcf6c6e3ab7df66a8f1a96d74e6d3b7d9f2ccbe93395f65f2da259a2"
    },
    "data/bin/npcs_client.bin":{
      "bytes":546520,
      "sha256":"27c1eacc19f2b0774763ea7b01eaf912eb0d08e9a4b1d0c6130fa7c803c67035"
    },
    "data/bin/origins.bin":{
      "bytes":504,
      "sha256":"ec13f45bc83815bb6d2c440380360589217919c65cc637f94959e53c5410e033"
    },
    "data/bin/particles.bin":{
      "bytes":25770540,
      "sha256":"87898af40681f6c7c54a324be4d959e4dd592768f31fa2b2642e663af8f71241"
    },
    "data/bin/plots.bin":{
      "bytes":19260,
      "sha256":"f3568a21a3eda0a3e9120d2addd77b90d35d9e9124fbf30ff78300a888d2a25a"
    },
    "data/bin/powercats.bin":{
      "bytes":239304,
      "sha256":"67b46915b9bf4440de8f5cf8bf7dd4a9047daee7dc5cb96f2c2be3999f8fc5e7"
    },
    "data/bin/powercustomizationcost.bin":{
      "bytes":196,
      "sha256":"50b968d708261f4a9775e73bc0508e4b0f9c6925e73d665bc0a2ba2195d4041c"
    },
    "data/bin/powercustomizationmenu.bin":{
      "bytes":332,
      "sha256":"f71aa71d1f27eaeee31aa26eedf9366da9a2e45074228e33dc433fdcabcbd30a"
    },
    "data/bin/powers.bin":{
      "bytes":62047164,
      "sha256":"25641e747c60e066016fcc7d2ce0a2e72f57d7d3953f7b1ff4b18b69e2d49c6d"
    },
    "data/bin/powersets.bin":{
      "bytes":3179276,
      "sha256":"afadc5f3ae6fc9c9c413924cec75bb911ff5cd4ce37388c6737cdb5786d9d547"
    },
    "data/bin/product_catalog.bin":{
      "bytes":250576,
      "sha256":"14a5484ac342ba4d117001bcb1eb23d0e7bee693abcee09afaaf3b72843a008a"
    },
    "data/bin/replacepowernames.bin":{
      "bytes":2352,
      "sha256":"7da843a2f3119967050dc704c2a93f7a1062f057d00090f9c152bc0d151d8eb3"
    },
    "data/bin/roomcategories.bin":{
      "bytes":812,
      "sha256":"47298da5fbd1034f1bd338124c09f1df9939d3f8762fbeb09860df48c7b12e02"
    },
    "data/bin/roomtemplates.bin":{
      "bytes":25688,
      "sha256":"2fbd3f2fee1498a8c0dbb3eb21c278ff8734ea5d0013808cb1ac40b80408ffd3"
    },
    "data/bin/schedules.bin":{
      "bytes":520,
      "sha256":"a6b344b7f37b8bade2f5fbc28906d122690791ca08b381a10e6581664a348de6"
    },
    "data/bin/seqstatebits.bin":{
      "bytes":15380,
      "sha256":"9c4a5aab4c2bffb99eb2416e76a692449ee26927beed3cdd86dece02af2b2aac"
    },
    "data/bin/sequencers.bin":{
      "bytes":83739012,
      "sha256":"64362d2213da02a36e63235de7037eb0355b9cdfdc5982dce528d26a42783d53"
    },
    "data/bin/soundinfo.bin":{
      "bytes":34432,
      "sha256":"3d1fce1f3c5826be100c6dd77b016e6cec2346f51a3f2b5e5892382dc0120d37"
    },
    "data/bin/stores.bin":{
      "bytes":29912,
      "sha256":"68e8763476b39f3ac32a09a3fa578bb6876692a24829abcd0fe652ae583a00a2"
    },
    "data/bin/supergroupColors.bin":{
      "bytes":2664,
      "sha256":"e5676ebbccc380f9d69322ef6750332b0b7e7a46d915bdfb591322862d22cb75"
    },
    "data/bin/supergroupEmblems.bin":{
      "bytes":13764,
      "sha256":"9a8fb6ee86a46e9ff69bdc5e0de5f83ed137412eb1d33b489bb09a8d789284e0"
    },
    "data/bin/supergroup_badges.bin":{
      "bytes":13076,
      "sha256":"5f3fd9325ab157948197fa767244c2f7b40254d30531fdb080c3aee96a8caed3"
    },
    "data/bin/tailorcost.bin":{
      "bytes":272,
      "sha256":"aa70748cd9ab05239ffc811d579f8fa039d3bee4c5f0c1bda86cd8f5321266c9"
    },
    "data/bin/texWords.bin":{
      "bytes":694324,
      "sha256":"4a4eac7c3464febdf11d67a9afd0e349fb4e49f3f06ea33933e258a495739b11"
    },
    "data/bin/tricks.bin":{
      "bytes":13537052,
      "sha256":"cf9595e54bc65a40d2dddc3a5a13c475d7c2ce07a96420e6001b0e2312926bc1"
    },
    "data/bin/villain_classes.bin":{
      "bytes":4228088,
      "sha256":"bc0789f03941d845f9574f6df4dd1ad953ad35328a3d7323c07d02d92fdbd523"
    },
    "data/bin/villain_origins.bin":{
      "bytes":124,
      "sha256":"2432c9d535ef7021d2c86ab9ea2e7049148304721e88163af3a3a2611bbeba3a"
    },
    "data/bin/visionPhases.bin":{
      "bytes":328,
      "sha256":"4e1099f1b9234004b568c7e2899eecd8b63b6ed9a2c50c56b90ed6989f4a8d32"
    },
    "data/bin/visionPhasesExclusive.bin":{
      "bytes":916,
      "sha256":"60a6b76d7b7e481923eb87e1dd710dfe6dc3ab694999e061be2453514328ad15"
    },
    "data/server/bin/CustomCritterRewardMods.bin":{
      "bytes":236,
      "sha256":"197e85b8715f14d464769489c9155969550288b727d88c48434e3b313eb9041d"
    },
    "data/server/bin/DayJobs.bin":{
      "bytes":19936,
      "sha256":"f3d44c7af6913ded5eaf271a15a0d2e21e199ccfa4bbaf7069af78ca97814bc3"
    },
    "data/server/bin/DifficultyCost.bin":{
      "bytes":304,
      "sha256":"8f31c63143b9d0da3a9909af2df8512fdbc5d4e13ab733100f236617c8bb0b92"
    },
    "data/server/bin/InvBaseDetail.bin":{
      "bytes":77652,
      "sha256":"3e75bfca08ba979fd7bcb4083da01ab51bdfb640fb159663e982421c1effd7c2"
    },
    "data/server/bin/InvConcept.bin":{
      "bytes":18620,
      "sha256":"8ee9a606ecb4f341c7bceb7717c77da20caabe1a342606698fac98db726a01e0"
    },
    "data/server/bin/InvRecipe.bin":{
      "bytes":929768,
      "sha256":"95b8a09a4e3d5ea1981188d7521283663db0f6f4bd22b5403fb409792d9821c5"
    },
    "data/server/bin/InvSalvage.bin":{
      "bytes":11284,
      "sha256":"8eb0e6ca8a13684e82e1a15c6b2c92f1d4015518375ff9cfcd8a36047eb7a133"
    },
    "data/server/bin/InvStoredSalvage.bin":{
      "bytes":11140,
      "sha256":"534c31af966e27c6f40a8a1d24ddfc03fd1dd388eee115c8efdbc32483551bd4"
    },
    "data/server/bin/ItemSets.bin":{
      "bytes":2922748,
      "sha256":"badc5fbcd6bdf917a714c0ef1768886156874400aa0ad3bb2510bb612d7e3d8c"
    },
    "data/server/bin/LevelBonus.bin":{
      "bytes":484,
      "sha256":"b9819c0dd6d224e76f36ccdb51397725d4424f9ecf1c5083f35ab73f1d5ee46b"
    },
    "data/server/bin/MARTY_exp_mods.bin":{
      "bytes":20304,
      "sha256":"d3d5c44524f061899f39cf6f1bac3d9e05d9b1b2b1927f3cb7ba754d3679ef42"
    },
    "data/server/bin/MapObjectives.bin":{
      "bytes":25356,
      "sha256":"a8f0e8937278df81b1f894375ffbb97c200dd7b6b33296fac1db44f84815d59a"
    },
    "data/server/bin/NewFeatures.bin":{
      "bytes":240,
      "sha256":"d2b5550dc7677b314c74e9cd10763314dce09121b4454e1b0d6935d6dccbaf48"
    },
    "data/server/bin/NictusHunterOptions.bin":{
      "bytes":220,
      "sha256":"1599640b3383f3605beb7c3e14c81305d1a804007f5d6293b67cf751755fa5ef"
    },
    "data/server/bin/PC_Rewards.bin":{
      "bytes":676,
      "sha256":"fb6f4bcaddea4eb51d55fe9e0e101b07b7aa0d81b100127cdde0115185f5db2a"
    },
    "data/server/bin/PowersetConversion.bin":{
      "bytes":18628,
      "sha256":"d262596cf6281168633d2b06e3d8412a4b54924accd30472bbbaf325b188924a"
    },
    "data/server/bin/Proficiencies.bin":{
      "bytes":2748,
      "sha256":"24837a0390efcc3f7be2696c49514998f74df0aca9c07de6ec5c24fd8f32188b"
    },
    "data/server/bin/ProficiencyIds.bin":{
      "bytes":704,
      "sha256":"820fea54bde7c1e1a52d8b14ab8defa16a784ce321f61bef79bd2f9401758527"
    },
    "data/server/bin/RewardChoiceTables.bin":{
      "bytes":150264,
      "sha256":"93c1ead857d523b33062e25df2fc392fb8a0f72b981f87ac0682ad32a97f7a82"
    },
    "data/server/bin/RewardTables.bin":{
      "bytes":82178028,
      "sha256":"dc5d2f2f2161b977a9ddee34731e06765bbb3920fa2d7b27b3f8cf035976bd05"
    },
    "data/server/bin/Salvage.bin":{
      "bytes":70568,
      "sha256":"bb351fc475d654578d8f613c38a07d2fb8bb05424853114a80c1fccc68b054ee"
    },
    "data/server/bin/SouvenirClues.bin":{
      "bytes":86616,
      "sha256":"5d10de29c150446d9104859dd853ca5f37a3c84ff1d21d73666ac5a734282a20"
    },
    "data/server/bin/SupergroupMods.bin":{
      "bytes":488,
      "sha256":"8bc1c8d4b1e37febc4c6f0d7c17650ec750b0c1b72209d805d1426d24e0225f8"
    },
    "data/server/bin/TFTimeLimits.bin":{
      "bytes":484,
      "sha256":"d32f20cd0c1b4e7516ac0c9b21458ff3e1ac1961012631ece98e867416d34b64"
    },
    "data/server/bin/TeamReward.bin":{
      "bytes":680,
      "sha256":"dde272da2c4abcac0a398805e2443955cb44e31ed89c5e6fcff41294553c22ae"
    },
    "data/server/bin/TrackedSalvage.bin":{
      "bytes":332,
      "sha256":"70fa7b2d87e39a6c3640d676c03ffa5d6a2df47bcec26ceae22036c9aebfd6df"
    },
    "data/server/bin/VillainDef.bin":{
      "bytes":16417580,
      "sha256":"f529f6d0db231ecb3a26b23c3120e983aabea8999ae456268b2d4bb0ae195617"
    },
    "data/server/bin/VillainGroups.bin":{
      "bytes":14464,
      "sha256":"c9f8f220be77ffcd71abf27340e71b148e6a83adce37f517c77ab2896dcab44b"
    },
    "data/server/bin/attrib_names.bin":{
      "bytes":10592,
      "sha256":"92daf1ec706f21b9a2f1f57d1ba941be43d4ed16b3f48c4e5028ac7e79162345"
    },
    "data/server/bin/badges.bin":{
      "bytes":874324,
      "sha256":"9dc0a979d68fe01e72f8601d4eac190c45646f31af230794301db257c51eec2b"
    },
    "data/server/bin/baserecipes.bin":{
      "bytes":12547112,
      "sha256":"4f358ca92b88f46de77eb75ce833e76c880d0d56d486861e2b5bd9023420e829"
    },
    "data/server/bin/boost_effect_above.bin":{
      "bytes":96,
      "sha256":"04c0643936f30f0c445899564c8b99c65ae933a1a59eab71fd1be2ba7560ac02"
    },
    "data/server/bin/boost_effect_below.bin":{
      "bytes":96,
      "sha256":"f888e14a84b042ed6f498aa800ffcd9c089cc26441a2660aa07f53500b418f8e"
    },
    "data/server/bin/boost_effect_boosters.bin":{
      "bytes":104,
      "sha256":"cc295ce81cd8dbabcd658dafb7f5043bbb524d6f3694d2c14d33ca118a326c35"
    },
    "data/server/bin/boostsets.bin":{
      "bytes":2275580,
      "sha256":"7af712b44bcbb93c18c45d42d21cb12bd7946c57506858f2f42c1070bb818c6c"
    },
    "data/server/bin/classes.bin":{
      "bytes":1219292,
      "sha256":"91af1ca0b304d77e56f356d54e1a880309b910c40f1729672cc0af1b83dd6733"
    },
    "data/server/bin/combat_mods.bin":{
      "bytes":6852,
      "sha256":"33d0393f4908d6c0c6dd6a5aaf1a8968bf4943819e654a1264d0b17981a26688"
    },
    "data/server/bin/combat_mods_villain.bin":{
      "bytes":2256,
      "sha256":"f5153efb99bf23bde6cb5363d110f9d206deae9d845f7a29b43c36c30278acef"
    },
    "data/server/bin/combine_booster_chances.bin":{
      "bytes":104,
      "sha256":"1bdae93fe8a14f45e0f08e0eb4cf590616ff6676c8e7c8bdc356c14e09a5a1fd"
    },
    "data/server/bin/combine_chances.bin":{
      "bytes":160,
      "sha256":"041f1d89c637566b170ef267f990f41405b7b7e3931cc9d730df5ea8c022cfeb"
    },
    "data/server/bin/combine_same_set_chances.bin":{
      "bytes":168,
      "sha256":"dd6f943d9c40f55f2dc322acaf3ff8bc77330f360df2ebd0a6885000fbf120b3"
    },
    "data/server/bin/contacts.bin":{
      "bytes":1983168,
      "sha256":"93da4b8266e5db9650abd07378195fefa70b2ac43ea10ade8cf7431959650617"
    },
    "data/server/bin/conversionsets.bin":{
      "bytes":1304,
      "sha256":"f49989a4537a4b9395a9b77dbd7f69d69d8132dc134a12fbe7a06aef021a1888"
    },
    "data/server/bin/damagedecay.bin":{
      "bytes":88,
      "sha256":"288bcee933d4b2b43bc7a06ca559a1a3c2b8627ec13cc2ed2e88fec1a1c95c54"
    },
    "data/server/bin/designer_contact_tip_types.bin":{
      "bytes":304,
      "sha256":"a45c8bc79f2703083bade43181eca2f758c9007933ce747d22043741a0af1de2"
    },
    "data/server/bin/detailcats.bin":{
      "bytes":1108,
      "sha256":"b3c0f24047dd138017ba7870d6652a5348f98535f807e8b54eabbebfceb4cbe4"
    },
    "data/server/bin/details.bin":{
      "bytes":418868,
      "sha256":"d6e2c59a7ae3278e201ac6dc8c984f521d197345c0c0e0575cf9f3b189497f2a"
    },
    "data/server/bin/dialog.bin":{
      "bytes":1012364,
      "sha256":"c15afd70244fd610cd5b1c56b0c405085b24e84addb4a9b89208ea471ed45ed5"
    },
    "data/server/bin/dialogdefs.bin":{
      "bytes":3328,
      "sha256":"6cf5953eb5784ec95880671c0e6eb756d0e762581cd298bf861ba333a4dc6dd9"
    },
    "data/server/bin/dim_returns.bin":{
      "bytes":864,
      "sha256":"cf81588dc98b4264a5f4e27b86300d848363781834c81a8423f5ce6c74bd0c19"
    },
    "data/server/bin/emotes.bin":{
      "bytes":33140,
      "sha256":"57dd7ef923c5b61b21fcc40cf4bc1fad4d7e7f6df6e27212717c329b71671168"
    },
    "data/server/bin/exemplar_handicaps.bin":{
      "bytes":892,
      "sha256":"626456e3797195e8d79ff56e2ce742e3a581b38d4399400affb43bb488f8cafb"
    },
    "data/server/bin/experience.bin":{
      "bytes":512,
      "sha256":"1295f7e7ad69f49aa9187bf7a97f8fa4335af78df0bd778dcbc28d776669a4d0"
    },
    "data/server/bin/incarnate.bin":{
      "bytes":884,
      "sha256":"2ffee43e712fdc2b7502b9cf524f622eb85b6fea14b691eed3378614ddb9313f"
    },
    "data/server/bin/inventory_sizes.bin":{
      "bytes":1752,
      "sha256":"fec2eac9e09b23f4491c4b4e04fd63b15476de1ea10e696362b9d03a32f1b76d"
    },
    "data/server/bin/inventory_tier_bonus.bin":{
      "bytes":332,
      "sha256":"2be40f1058e99d97dc0a93f839bb61ef3885103bd7fc417e1c31181cfe6f55ff"
    },
    "data/server/bin/mapsspec.bin":{
      "bytes":66388,
      "sha256":"4d8af645a32eea00fcd2f3af1cb2cda7cc1131e3c9aff347c96196e2e8886ebb"
    },
    "data/server/bin/meritsRewards.bin":{
      "bytes":36376,
      "sha256":"56b365ce8249ff628496e75684c14cb90c25ca7d3814f73b5133a6fec6142880"
    },
    "data/server/bin/messages-en.bin":{
      "bytes":6933216,
      "sha256":"769d3419df025c3067aabb6f6c0bc97936c68f3ce2f6e660ee33adf1bb855f3f"
    },
    "data/server/bin/missionhostagespawns.bin":{
      "bytes":624,
      "sha256":"d493fb4cb08fdfe57c19b35002482365d5d41f1f15802c83916ac16d1fc1fd94"
    },
    "data/server/bin/missionspawns.bin":{
      "bytes":22284,
      "sha256":"ab47259759e1a47cfdf98f62f8f70b9dbecc5997b305a812be459a768d7074b3"
    },
    "data/server/bin/missionspecs.bin":{
      "bytes":355712,
      "sha256":"09fa2446df00c99a173fdd12f857aceaea286711a4bd2cd7abfddf883f822625"
    },
    "data/server/bin/monorails.bin":{
      "bytes":10496,
      "sha256":"c5f729c836618796654cfd07c6c1f2b352a4bc26e05e09e80c712e06e8fec233"
    },
    "data/server/bin/npcs_server.bin":{
      "bytes":530936,
      "sha256":"011b30bbe643133f7bcc9c6a087f6ec42b590d3af66e2bd7dbc0f668690ebf8e"
    },
    "data/server/bin/origins.bin":{
      "bytes":504,
      "sha256":"ec13f45bc83815bb6d2c440380360589217919c65cc637f94959e53c5410e033"
    },
    "data/server/bin/petBattleCreatureInfo.bin":{
      "bytes":6380,
      "sha256":"ee7ac2604a9db535fe21a9bf047be49f86e04e8262cfe1a0b73ca21a0b7c2766"
    },
    "data/server/bin/plots.bin":{
      "bytes":19260,
      "sha256":"f3568a21a3eda0a3e9120d2addd77b90d35d9e9124fbf30ff78300a888d2a25a"
    },
    "data/server/bin/powercats.bin":{
      "bytes":239304,
      "sha256":"e236f92e9bd0c3dc33058f7cc01795db21e7c6aa4d1b36d82be84c68035357ee"
    },
    "data/server/bin/powers.bin":{
      "bytes":62047164,
      "sha256":"3b563ea562eb7c96c95bdc4200ffdf8432638e5dceb8f792fca4e2e29f2047f9"
    },
    "data/server/bin/powersets.bin":{
      "bytes":3179276,
      "sha256":"5db7961a042540ad2675deea08a67905f0e596bb2997db9f2ec14e7d4babdebc"
    },
    "data/server/bin/pvptaskmodifiers.bin":{
      "bytes":216,
      "sha256":"395ae902328e24db1c9f61add366784a02b66729d301d59bfe8c1d76e2c58437"
    },
    "data/server/bin/randomgroupselection.bin":{
      "bytes":6620,
      "sha256":"54e4cb30a3d07c46a8b622e70ca252aaf199641326a3602ec5e0697537616467"
    },
    "data/server/bin/randommapselection.bin":{
      "bytes":424,
      "sha256":"c8190ad0104004dbc41b90b635a9c751aa93786e5a7714d295cbadae24231980"
    },
    "data/server/bin/roomcategories.bin":{
      "bytes":812,
      "sha256":"47298da5fbd1034f1bd338124c09f1df9939d3f8762fbeb09860df48c7b12e02"
    },
    "data/server/bin/roomtemplates.bin":{
      "bytes":25688,
      "sha256":"2fbd3f2fee1498a8c0dbb3eb21c278ff8734ea5d0013808cb1ac40b80408ffd3"
    },
    "data/server/bin/schedules.bin":{
      "bytes":520,
      "sha256":"a6b344b7f37b8bade2f5fbc28906d122690791ca08b381a10e6581664a348de6"
    },
    "data/server/bin/scriptdefs.bin":{
      "bytes":136408,
      "sha256":"c785a3ff7f2bad2612b39b1bd90b1fa8c58d3c2f405c59ffe7f10f37cd191d01"
    },
    "data/server/bin/seqstatebits.bin":{
      "bytes":15380,
      "sha256":"9c4a5aab4c2bffb99eb2416e76a692449ee26927beed3cdd86dece02af2b2aac"
    },
    "data/server/bin/spawndefs.bin":{
      "bytes":115084768,
      "sha256":"141fb3f67430c6d1cfad706cd9afd7664e63554462884b1b1dbfa6e5aa9ab81f"
    },
    "data/server/bin/staticmsg-en.bin":{
      "bytes":96413,
      "sha256":"7e52da7857144aeb06adfa5a3d574d6cfe3387f6cbd84c2dfc399dea1fef149d"
    },
    "data/server/bin/storyarc.bin":{
      "bytes":50639400,
      "sha256":"c0c667ae2e446e2dc959ae1f389588066469fb30e15de2d5a9568afe3e90b0e4"
    },
    "data/server/bin/storyarcmsg-en.bin":{
      "bytes":20926850,
      "sha256":"63035041f3505cb6ed14b8b79cb1648c1f6a75180a44dbb83c9670b2ad5823e5"
    },
    "data/server/bin/supergroup_badges.bin":{
      "bytes":20604,
      "sha256":"d1dc7826ef9143b09bad9fcac6ca58fbfb8ed42257825489ae0945316d0dc688"
    },
    "data/server/bin/tasksets.bin":{
      "bytes":36685476,
      "sha256":"d7f995419751844011b80ae5052317287a1e92fc8e797be6463126da2e95192f"
    },
    "data/server/bin/turnstile_server.bin":{
      "bytes":21028,
      "sha256":"229b31498370958d83b2776d9e59b637205a2f700bb419bf31070d83bff2056a"
    },
    "data/server/bin/tut_votekick.bin":{
      "bytes":84,
      "sha256":"6471eeaeb972a186860e417eb321b62c4a21bd904cb0a26a29f215686e44fd58"
    },
    "data/server/bin/villain_classes.bin":{
      "bytes":4228088,
      "sha256":"bc0789f03941d845f9574f6df4dd1ad953ad35328a3d7323c07d02d92fdbd523"
    },
    "data/server/bin/villain_origins.bin":{
      "bytes":124,
      "sha256":"2432c9d535ef7021d2c86ab9ea2e7049148304721e88163af3a3a2611bbeba3a"
    },
    "data/server/bin/villainrandomgroupselection.bin":{
      "bytes":5948,
      "sha256":"ac0874d1554c88b80e7874b36a4cf63b1cf71bb6e1ccc240db8caf704aebd3b8"
    },
    "data/server/bin/villainrandommapselection.bin":{
      "bytes":388,
      "sha256":"29107e77a21db08151a9b32b7917da6f24475d001ac1bfbe68e91a1614f5b229"
    },
    "data/server/bin/visionPhases.bin":{
      "bytes":328,
      "sha256":"4e1099f1b9234004b568c7e2899eecd8b63b6ed9a2c50c56b90ed6989f4a8d32"
    },
    "data/server/bin/visionPhasesExclusive.bin":{
      "bytes":916,
      "sha256":"60a6b76d7b7e481923eb87e1dd710dfe6dc3ab694999e061be2453514328ad15"
    },
    "data/server/bin/zone_event_karma.bin":{
      "bytes":224,
      "sha256":"3047b833eb5438a3a12a9b7eca57ae541d9e943dba509cae9e83ab4a61258b94"
    }
  },
  "before":{
    "data/bin/BodyParts.bin":{
      "bytes":2584,
      "sha256":"b0955c46731ed0cb54ad01d96015b301e583bd0224f8d872f50cfefeb08f6beb"
    },
    "data/bin/Cards.bin":{
      "bytes":69268,
      "sha256":"000bf30499c3601238395f3abfe65dc0348377265ae475adea88fc9919ccc9fa"
    },
    "data/bin/CustomCritterRewardMods.bin":{
      "bytes":236,
      "sha256":"197e85b8715f14d464769489c9155969550288b727d88c48434e3b313eb9041d"
    },
    "data/bin/InvBaseDetail.bin":{
      "bytes":77652,
      "sha256":"80990b0300deab77613b2ab8a0abf56ecbe4e14840346a79fad17283d228e75d"
    },
    "data/bin/InvConcept.bin":{
      "bytes":18620,
      "sha256":"8ee9a606ecb4f341c7bceb7717c77da20caabe1a342606698fac98db726a01e0"
    },
    "data/bin/InvRecipe.bin":{
      "bytes":929768,
      "sha256":"f772a8556efe8119799c0691e2ed70b34f422406fb4bd1368110f3af960b028c"
    },
    "data/bin/InvSalvage.bin":{
      "bytes":11284,
      "sha256":"eb65b811238a17be8311d882c2b548b734da1e9f65f9af7ab882d468ff4b939c"
    },
    "data/bin/InvStoredSalvage.bin":{
      "bytes":11140,
      "sha256":"cc9cc4c7a81fadcf69abdaa2dcd275f2ae0b1f81fd4813785d8dd026d7675abd"
    },
    "data/bin/LoyaltyReward.bin":{
      "bytes":8140,
      "sha256":"d0af635d12dae04cb422b8745e716586fac31a15dcee2e786c34a4d5f7abe66c"
    },
    "data/bin/PC_Def_Animation.bin":{
      "bytes":7008,
      "sha256":"87d5b32f2da9b625cb1ff201edc7b4a8325e36ecc269ead35f6c326fd54aaf6a"
    },
    "data/bin/PC_Def_Contacts.bin":{
      "bytes":29148,
      "sha256":"906499910d7c2ea9cc91ed9e81718829ae750d82fb8bc30f5398c3282602ce88"
    },
    "data/bin/PC_Def_DestructObject.bin":{
      "bytes":2028,
      "sha256":"2ef27b0ecf18dbec9bb003b29a8e5618e407cbf08058a4c0b49a4408b45f3f42"
    },
    "data/bin/PC_Def_Entities.bin":{
      "bytes":91772,
      "sha256":"5fd5a031f785db26649a9501638fffe9513005cf8cb98240e74899ec01519fbc"
    },
    "data/bin/PC_Def_MapSets.bin":{
      "bytes":1488,
      "sha256":"5b52cd5a75710a5a8ac828cb84979b4862bce89b04410bb4cd41982e9000d1ba"
    },
    "data/bin/PC_Def_MapUnique.bin":{
      "bytes":23436,
      "sha256":"4c5593f57e7242b527c28ae61bde40917bb13f752295c44683d43a9504d54e2d"
    },
    "data/bin/PC_Def_NonSelectable_Entities.bin":{
      "bytes":25956,
      "sha256":"93421fe594c1b5b3d74abd0f37c1c4ccfad054c549709f3a72c806ca4f9c08fc"
    },
    "data/bin/PC_Def_Objects.bin":{
      "bytes":3956,
      "sha256":"d93e6972cfcf022597ff545f1e65be50187da1a17e0e71157676cc5915cc3f41"
    },
    "data/bin/PC_Def_Sequencer_Anims.bin":{
      "bytes":19916,
      "sha256":"51f60f31c38dc9ff71ea5e2531c170cc69686216564da4ac87fec437769b931a"
    },
    "data/bin/PC_Def_UI.bin":{
      "bytes":75552,
      "sha256":"d6c1ca0ca4c82243cca6ebb1ddd8b2db13427df26de9e3fd3bfd62dab24515ac"
    },
    "data/bin/PC_Def_Unlockable_Content.bin":{
      "bytes":22264,
      "sha256":"e403d19e98fdd3ad0df643aad1295c40df2131a17e639ee76c3f7df082b53689"
    },
    "data/bin/PopHelp.bin":{
      "bytes":6632,
      "sha256":"8da203d500c8d518ea7a7c8305fa2ed1aa50dbc5628b7d8c51456f6fc0ada9e5"
    },
    "data/bin/Proficiencies.bin":{
      "bytes":2748,
      "sha256":"24837a0390efcc3f7be2696c49514998f74df0aca9c07de6ec5c24fd8f32188b"
    },
    "data/bin/ProficiencyIds.bin":{
      "bytes":704,
      "sha256":"6d3e893c0b7591935aad9c7422bc681e2f42af5c5850d79ae50d5b3b69c4002f"
    },
    "data/bin/Salvage.bin":{
      "bytes":70568,
      "sha256":"bb351fc475d654578d8f613c38a07d2fb8bb05424853114a80c1fccc68b054ee"
    },
    "data/bin/VillainCostume.bin":{
      "bytes":28743996,
      "sha256":"94f2d86ce15785d8a4d69e269f8b495bb1d1982b484b19853babbb559c209cca"
    },
    "data/bin/VillainDef.bin":{
      "bytes":16417580,
      "sha256":"0fbf7d87d17c7f682613753fc2ed4d1541b8ba4e95873da79003db37f0e159eb"
    },
    "data/bin/VillainGroups.bin":{
      "bytes":14464,
      "sha256":"c9f8f220be77ffcd71abf27340e71b148e6a83adce37f517c77ab2896dcab44b"
    },
    "data/bin/arenamaps.bin":{
      "bytes":1252,
      "sha256":"33deb39c44e96a85e2344df91e1b9f91203dd1f61d3bd00414279705b610ea4d"
    },
    "data/bin/attrib_descriptions.bin":{
      "bytes":5892,
      "sha256":"20f770f406e661050434284e4253f721699df2112ea4481de66b50146304c132"
    },
    "data/bin/attrib_names.bin":{
      "bytes":10592,
      "sha256":"92daf1ec706f21b9a2f1f57d1ba941be43d4ed16b3f48c4e5028ac7e79162345"
    },
    "data/bin/auctionconfig.bin":{
      "bytes":80,
      "sha256":"831cb9df5b09674453522e5d3f0d0fe10cfd7a3dbeed6fdd112809330a86a90b"
    },
    "data/bin/badges.bin":{
      "bytes":586324,
      "sha256":"c12387e003414c2f584469c29eb1b8f48c25d53749d77e6b63bbb0be908aabe9"
    },
    "data/bin/baserecipes.bin":{
      "bytes":12492600,
      "sha256":"065827aabf290427dbef231735ba4a9081be5e32cf4caf1a2815250f9ccfd386"
    },
    "data/bin/baseupkeep.bin":{
      "bytes":200,
      "sha256":"f8c82217241baa3e5e5031dcbbfb18f533748d3e195205fbef42bd44f2257c33"
    },
    "data/bin/behaviors.bin":{
      "bytes":4198644,
      "sha256":"d2e7eaf268bf4d5beeb60876b727d9738ef1b42494d1ab78b480d1e07f788056"
    },
    "data/bin/boost_effect_above.bin":{
      "bytes":96,
      "sha256":"04c0643936f30f0c445899564c8b99c65ae933a1a59eab71fd1be2ba7560ac02"
    },
    "data/bin/boost_effect_below.bin":{
      "bytes":96,
      "sha256":"f888e14a84b042ed6f498aa800ffcd9c089cc26441a2660aa07f53500b418f8e"
    },
    "data/bin/boost_effect_boosters.bin":{
      "bytes":104,
      "sha256":"cc295ce81cd8dbabcd658dafb7f5043bbb524d6f3694d2c14d33ca118a326c35"
    },
    "data/bin/boostsets.bin":{
      "bytes":2275580,
      "sha256":"7af712b44bcbb93c18c45d42d21cb12bd7946c57506858f2f42c1070bb818c6c"
    },
    "data/bin/capes.bin":{
      "bytes":97568,
      "sha256":"9d34b0a7a2c22c7f4e21080f9aa5b36f468b7d2e0c06ca4487488a95b36c9a62"
    },
    "data/bin/chestGeoLink.bin":{
      "bytes":1108,
      "sha256":"46606cfe37efee7e2da2ad6a008a5dfea9bd4c30cbbb5fcd6eb07923d626f0e8"
    },
    "data/bin/classes.bin":{
      "bytes":1219292,
      "sha256":"91af1ca0b304d77e56f356d54e1a880309b910c40f1729672cc0af1b83dd6733"
    },
    "data/bin/clothColInfo.bin":{
      "bytes":42792,
      "sha256":"adcc645aed172f088f35683be662e09ddddc88948dc7bb3664a627459d4445eb"
    },
    "data/bin/clothWindInfo.bin":{
      "bytes":1548,
      "sha256":"0e9e1b22c8b4acd8bf1549b63571a05aebc2a619d7fa9355a06575aca7fd1385"
    },
    "data/bin/combine_booster_chances.bin":{
      "bytes":104,
      "sha256":"1bdae93fe8a14f45e0f08e0eb4cf590616ff6676c8e7c8bdc356c14e09a5a1fd"
    },
    "data/bin/combine_chances.bin":{
      "bytes":160,
      "sha256":"041f1d89c637566b170ef267f990f41405b7b7e3931cc9d730df5ea8c022cfeb"
    },
    "data/bin/combine_same_set_chances.bin":{
      "bytes":168,
      "sha256":"dd6f943d9c40f55f2dc322acaf3ff8bc77330f360df2ebd0a6885000fbf120b3"
    },
    "data/bin/command.bin":{
      "bytes":5984,
      "sha256":"cb183ffbe69e17d513b2e8cd0f208de8d88b22ae4034be4134fea74d73647070"
    },
    "data/bin/conversionsets.bin":{
      "bytes":1304,
      "sha256":"f49989a4537a4b9395a9b77dbd7f69d69d8132dc134a12fbe7a06aef021a1888"
    },
    "data/bin/costume.bin":{
      "bytes":17691352,
      "sha256":"10ef7562156be60bd1ef3c437c3b46d10b36b6b265129c10f39d25c4a4df5a77"
    },
    "data/bin/costumeWeaponStances.bin":{
      "bytes":528,
      "sha256":"9980bb27731f81baa8a49d64cb26e538581e448cef878fd5d8f962cad617101e"
    },
    "data/bin/defaultBodyCfg.bin":{
      "bytes":972,
      "sha256":"e1ddc4c739df802d5498d3e70d6919c1b8f8ea2e2986c739c7a5603789f82202"
    },
    "data/bin/defnames.bin":{
      "bytes":3300312,
      "sha256":"cab5eb006413fdf355586b85765d7bfdecca082b687c1338e78b9eeb17b29fc7"
    },
    "data/bin/depts.bin":{
      "bytes":29420,
      "sha256":"eb60fe990086e4b86d60ddbd889a80e9254efc4586e4d1e6c52f7a862b5380c0"
    },
    "data/bin/detailcats.bin":{
      "bytes":1108,
      "sha256":"b3c0f24047dd138017ba7870d6652a5348f98535f807e8b54eabbebfceb4cbe4"
    },
    "data/bin/details.bin":{
      "bytes":401216,
      "sha256":"11e5104e0210fa5cbbc910932e5df461a34853e9a30d43f890d31510cdf2ce28"
    },
    "data/bin/dim_returns.bin":{
      "bytes":864,
      "sha256":"cf81588dc98b4264a5f4e27b86300d848363781834c81a8423f5ce6c74bd0c19"
    },
    "data/bin/ent_types.bin":{
      "bytes":1444116,
      "sha256":"4bb44025fda13d11c03d200362c55f51dec346d60e195ded4ecaed38026ebf67"
    },
    "data/bin/exemplar_handicaps.bin":{
      "bytes":892,
      "sha256":"626456e3797195e8d79ff56e2ce742e3a581b38d4399400affb43bb488f8cafb"
    },
    "data/bin/experience.bin":{
      "bytes":512,
      "sha256":"1295f7e7ad69f49aa9187bf7a97f8fa4335af78df0bd778dcbc28d776669a4d0"
    },
    "data/bin/fxinfo.bin":{
      "bytes":58505496,
      "sha256":"3b1af6d146db65aa2a00fa9dbe4502776409cdea15f94f717e5455a3cda5fe70"
    },
    "data/bin/items.bin":{
      "bytes":4542044,
      "sha256":"80e45680f9a22ac49ab1654a98c3389a5a2763f36bbd22d0470cd616c617e824"
    },
    "data/bin/kb.bin":{
      "bytes":12240,
      "sha256":"af3a2dfed7f4d1deb6cad00e8beae0c9b3a9ea8777f62961258bd7dc3a9c04bd"
    },
    "data/bin/kbkorea.bin":{
      "bytes":12252,
      "sha256":"e8bea925c9c4dbe77e8db6529c2a0dbd0dcfa86e460c9a92685f1dc1988edecc"
    },
    "data/bin/lods.bin":{
      "bytes":1059016,
      "sha256":"13800255781138248226340be316cd628e98800d9ba889fe1aecc902e483b66a"
    },
    "data/bin/map.bin":{
      "bytes":5600,
      "sha256":"5e64f9b0903a3bbfd163ef6ec62f40ad95e55be3c85c7a7742d53d788d336e49"
    },
    "data/bin/mapspecs.bin":{
      "bytes":164840,
      "sha256":"238b6876148ff6f19cc8f835ee36b8a9fe0b09a5d13601eb8adb5a3d858f077e"
    },
    "data/bin/mapstats.bin":{
      "bytes":1542744,
      "sha256":"b14c208848ef59529ceeb592a1c4a4e167d7a62683a13c9d1536b5166d0b44a8"
    },
    "data/bin/menuAnimations.bin":{
      "bytes":1804,
      "sha256":"a2dc887e6aeced481e4fc1bf556c50632b302e82f9e0fdfc7f2c49fee92e33d2"
    },
    "data/bin/minimap.bin":{
      "bytes":13945296,
      "sha256":"a9a2ba27bcf6c6e3ab7df66a8f1a96d74e6d3b7d9f2ccbe93395f65f2da259a2"
    },
    "data/bin/npcs_client.bin":{
      "bytes":546520,
      "sha256":"27c1eacc19f2b0774763ea7b01eaf912eb0d08e9a4b1d0c6130fa7c803c67035"
    },
    "data/bin/origins.bin":{
      "bytes":504,
      "sha256":"ec13f45bc83815bb6d2c440380360589217919c65cc637f94959e53c5410e033"
    },
    "data/bin/particles.bin":{
      "bytes":25770540,
      "sha256":"87898af40681f6c7c54a324be4d959e4dd592768f31fa2b2642e663af8f71241"
    },
    "data/bin/plots.bin":{
      "bytes":19260,
      "sha256":"f3568a21a3eda0a3e9120d2addd77b90d35d9e9124fbf30ff78300a888d2a25a"
    },
    "data/bin/powercats.bin":{
      "bytes":239304,
      "sha256":"67b46915b9bf4440de8f5cf8bf7dd4a9047daee7dc5cb96f2c2be3999f8fc5e7"
    },
    "data/bin/powercustomizationcost.bin":{
      "bytes":196,
      "sha256":"50b968d708261f4a9775e73bc0508e4b0f9c6925e73d665bc0a2ba2195d4041c"
    },
    "data/bin/powercustomizationmenu.bin":{
      "bytes":332,
      "sha256":"f71aa71d1f27eaeee31aa26eedf9366da9a2e45074228e33dc433fdcabcbd30a"
    },
    "data/bin/powers.bin":{
      "bytes":62047164,
      "sha256":"25641e747c60e066016fcc7d2ce0a2e72f57d7d3953f7b1ff4b18b69e2d49c6d"
    },
    "data/bin/powersets.bin":{
      "bytes":3179276,
      "sha256":"afadc5f3ae6fc9c9c413924cec75bb911ff5cd4ce37388c6737cdb5786d9d547"
    },
    "data/bin/product_catalog.bin":{
      "bytes":250576,
      "sha256":"79252c1e4967e046320201f0c8ff4e6387a7da5ed501de2d316aef50a9e5ccd5"
    },
    "data/bin/replacepowernames.bin":{
      "bytes":2352,
      "sha256":"7da843a2f3119967050dc704c2a93f7a1062f057d00090f9c152bc0d151d8eb3"
    },
    "data/bin/roomcategories.bin":{
      "bytes":812,
      "sha256":"47298da5fbd1034f1bd338124c09f1df9939d3f8762fbeb09860df48c7b12e02"
    },
    "data/bin/roomtemplates.bin":{
      "bytes":25688,
      "sha256":"2fbd3f2fee1498a8c0dbb3eb21c278ff8734ea5d0013808cb1ac40b80408ffd3"
    },
    "data/bin/schedules.bin":{
      "bytes":520,
      "sha256":"a6b344b7f37b8bade2f5fbc28906d122690791ca08b381a10e6581664a348de6"
    },
    "data/bin/seqstatebits.bin":{
      "bytes":15380,
      "sha256":"9c4a5aab4c2bffb99eb2416e76a692449ee26927beed3cdd86dece02af2b2aac"
    },
    "data/bin/sequencers.bin":{
      "bytes":83739012,
      "sha256":"64362d2213da02a36e63235de7037eb0355b9cdfdc5982dce528d26a42783d53"
    },
    "data/bin/soundinfo.bin":{
      "bytes":34432,
      "sha256":"3d1fce1f3c5826be100c6dd77b016e6cec2346f51a3f2b5e5892382dc0120d37"
    },
    "data/bin/stores.bin":{
      "bytes":29912,
      "sha256":"68e8763476b39f3ac32a09a3fa578bb6876692a24829abcd0fe652ae583a00a2"
    },
    "data/bin/supergroupColors.bin":{
      "bytes":2664,
      "sha256":"e5676ebbccc380f9d69322ef6750332b0b7e7a46d915bdfb591322862d22cb75"
    },
    "data/bin/supergroupEmblems.bin":{
      "bytes":13764,
      "sha256":"9a8fb6ee86a46e9ff69bdc5e0de5f83ed137412eb1d33b489bb09a8d789284e0"
    },
    "data/bin/supergroup_badges.bin":{
      "bytes":13076,
      "sha256":"5f3fd9325ab157948197fa767244c2f7b40254d30531fdb080c3aee96a8caed3"
    },
    "data/bin/tailorcost.bin":{
      "bytes":272,
      "sha256":"aa70748cd9ab05239ffc811d579f8fa039d3bee4c5f0c1bda86cd8f5321266c9"
    },
    "data/bin/texWords.bin":{
      "bytes":694324,
      "sha256":"4a4eac7c3464febdf11d67a9afd0e349fb4e49f3f06ea33933e258a495739b11"
    },
    "data/bin/tricks.bin":{
      "bytes":13537052,
      "sha256":"cf9595e54bc65a40d2dddc3a5a13c475d7c2ce07a96420e6001b0e2312926bc1"
    },
    "data/bin/villain_classes.bin":{
      "bytes":4228088,
      "sha256":"bc0789f03941d845f9574f6df4dd1ad953ad35328a3d7323c07d02d92fdbd523"
    },
    "data/bin/villain_origins.bin":{
      "bytes":124,
      "sha256":"2432c9d535ef7021d2c86ab9ea2e7049148304721e88163af3a3a2611bbeba3a"
    },
    "data/bin/visionPhases.bin":{
      "bytes":328,
      "sha256":"4e1099f1b9234004b568c7e2899eecd8b63b6ed9a2c50c56b90ed6989f4a8d32"
    },
    "data/bin/visionPhasesExclusive.bin":{
      "bytes":916,
      "sha256":"60a6b76d7b7e481923eb87e1dd710dfe6dc3ab694999e061be2453514328ad15"
    },
    "data/server/bin/CustomCritterRewardMods.bin":{
      "bytes":236,
      "sha256":"197e85b8715f14d464769489c9155969550288b727d88c48434e3b313eb9041d"
    },
    "data/server/bin/DayJobs.bin":{
      "bytes":19936,
      "sha256":"f3d44c7af6913ded5eaf271a15a0d2e21e199ccfa4bbaf7069af78ca97814bc3"
    },
    "data/server/bin/DifficultyCost.bin":{
      "bytes":304,
      "sha256":"8f31c63143b9d0da3a9909af2df8512fdbc5d4e13ab733100f236617c8bb0b92"
    },
    "data/server/bin/InvBaseDetail.bin":{
      "bytes":77652,
      "sha256":"80990b0300deab77613b2ab8a0abf56ecbe4e14840346a79fad17283d228e75d"
    },
    "data/server/bin/InvConcept.bin":{
      "bytes":18620,
      "sha256":"8ee9a606ecb4f341c7bceb7717c77da20caabe1a342606698fac98db726a01e0"
    },
    "data/server/bin/InvRecipe.bin":{
      "bytes":929768,
      "sha256":"f772a8556efe8119799c0691e2ed70b34f422406fb4bd1368110f3af960b028c"
    },
    "data/server/bin/InvSalvage.bin":{
      "bytes":11284,
      "sha256":"eb65b811238a17be8311d882c2b548b734da1e9f65f9af7ab882d468ff4b939c"
    },
    "data/server/bin/InvStoredSalvage.bin":{
      "bytes":11140,
      "sha256":"cc9cc4c7a81fadcf69abdaa2dcd275f2ae0b1f81fd4813785d8dd026d7675abd"
    },
    "data/server/bin/ItemSets.bin":{
      "bytes":2922748,
      "sha256":"badc5fbcd6bdf917a714c0ef1768886156874400aa0ad3bb2510bb612d7e3d8c"
    },
    "data/server/bin/LevelBonus.bin":{
      "bytes":484,
      "sha256":"b9819c0dd6d224e76f36ccdb51397725d4424f9ecf1c5083f35ab73f1d5ee46b"
    },
    "data/server/bin/MARTY_exp_mods.bin":{
      "bytes":20304,
      "sha256":"d3d5c44524f061899f39cf6f1bac3d9e05d9b1b2b1927f3cb7ba754d3679ef42"
    },
    "data/server/bin/MapObjectives.bin":{
      "bytes":25356,
      "sha256":"a8f0e8937278df81b1f894375ffbb97c200dd7b6b33296fac1db44f84815d59a"
    },
    "data/server/bin/NewFeatures.bin":{
      "bytes":240,
      "sha256":"d2b5550dc7677b314c74e9cd10763314dce09121b4454e1b0d6935d6dccbaf48"
    },
    "data/server/bin/NictusHunterOptions.bin":{
      "bytes":220,
      "sha256":"1599640b3383f3605beb7c3e14c81305d1a804007f5d6293b67cf751755fa5ef"
    },
    "data/server/bin/PC_Rewards.bin":{
      "bytes":680,
      "sha256":"11d0506a3704b703e683a99155b911b80189a7e87f97c988d3ae939507192c70"
    },
    "data/server/bin/PowersetConversion.bin":{
      "bytes":18628,
      "sha256":"d262596cf6281168633d2b06e3d8412a4b54924accd30472bbbaf325b188924a"
    },
    "data/server/bin/Proficiencies.bin":{
      "bytes":2748,
      "sha256":"24837a0390efcc3f7be2696c49514998f74df0aca9c07de6ec5c24fd8f32188b"
    },
    "data/server/bin/ProficiencyIds.bin":{
      "bytes":704,
      "sha256":"6d3e893c0b7591935aad9c7422bc681e2f42af5c5850d79ae50d5b3b69c4002f"
    },
    "data/server/bin/RewardChoiceTables.bin":{
      "bytes":150264,
      "sha256":"93c1ead857d523b33062e25df2fc392fb8a0f72b981f87ac0682ad32a97f7a82"
    },
    "data/server/bin/RewardTables.bin":{
      "bytes":82178028,
      "sha256":"dc5d2f2f2161b977a9ddee34731e06765bbb3920fa2d7b27b3f8cf035976bd05"
    },
    "data/server/bin/Salvage.bin":{
      "bytes":70568,
      "sha256":"bb351fc475d654578d8f613c38a07d2fb8bb05424853114a80c1fccc68b054ee"
    },
    "data/server/bin/SouvenirClues.bin":{
      "bytes":86616,
      "sha256":"5d10de29c150446d9104859dd853ca5f37a3c84ff1d21d73666ac5a734282a20"
    },
    "data/server/bin/SupergroupMods.bin":{
      "bytes":488,
      "sha256":"8bc1c8d4b1e37febc4c6f0d7c17650ec750b0c1b72209d805d1426d24e0225f8"
    },
    "data/server/bin/TFTimeLimits.bin":{
      "bytes":484,
      "sha256":"d32f20cd0c1b4e7516ac0c9b21458ff3e1ac1961012631ece98e867416d34b64"
    },
    "data/server/bin/TeamReward.bin":{
      "bytes":680,
      "sha256":"dde272da2c4abcac0a398805e2443955cb44e31ed89c5e6fcff41294553c22ae"
    },
    "data/server/bin/TrackedSalvage.bin":{
      "bytes":332,
      "sha256":"70fa7b2d87e39a6c3640d676c03ffa5d6a2df47bcec26ceae22036c9aebfd6df"
    },
    "data/server/bin/VillainDef.bin":{
      "bytes":16417580,
      "sha256":"f529f6d0db231ecb3a26b23c3120e983aabea8999ae456268b2d4bb0ae195617"
    },
    "data/server/bin/VillainGroups.bin":{
      "bytes":14464,
      "sha256":"c9f8f220be77ffcd71abf27340e71b148e6a83adce37f517c77ab2896dcab44b"
    },
    "data/server/bin/attrib_names.bin":{
      "bytes":10592,
      "sha256":"92daf1ec706f21b9a2f1f57d1ba941be43d4ed16b3f48c4e5028ac7e79162345"
    },
    "data/server/bin/badges.bin":{
      "bytes":874324,
      "sha256":"9dc0a979d68fe01e72f8601d4eac190c45646f31af230794301db257c51eec2b"
    },
    "data/server/bin/baserecipes.bin":{
      "bytes":12547112,
      "sha256":"4f358ca92b88f46de77eb75ce833e76c880d0d56d486861e2b5bd9023420e829"
    },
    "data/server/bin/boost_effect_above.bin":{
      "bytes":96,
      "sha256":"04c0643936f30f0c445899564c8b99c65ae933a1a59eab71fd1be2ba7560ac02"
    },
    "data/server/bin/boost_effect_below.bin":{
      "bytes":96,
      "sha256":"f888e14a84b042ed6f498aa800ffcd9c089cc26441a2660aa07f53500b418f8e"
    },
    "data/server/bin/boost_effect_boosters.bin":{
      "bytes":104,
      "sha256":"cc295ce81cd8dbabcd658dafb7f5043bbb524d6f3694d2c14d33ca118a326c35"
    },
    "data/server/bin/boostsets.bin":{
      "bytes":2275580,
      "sha256":"7af712b44bcbb93c18c45d42d21cb12bd7946c57506858f2f42c1070bb818c6c"
    },
    "data/server/bin/classes.bin":{
      "bytes":1219292,
      "sha256":"91af1ca0b304d77e56f356d54e1a880309b910c40f1729672cc0af1b83dd6733"
    },
    "data/server/bin/combat_mods.bin":{
      "bytes":6852,
      "sha256":"33d0393f4908d6c0c6dd6a5aaf1a8968bf4943819e654a1264d0b17981a26688"
    },
    "data/server/bin/combat_mods_villain.bin":{
      "bytes":2256,
      "sha256":"f5153efb99bf23bde6cb5363d110f9d206deae9d845f7a29b43c36c30278acef"
    },
    "data/server/bin/combine_booster_chances.bin":{
      "bytes":104,
      "sha256":"1bdae93fe8a14f45e0f08e0eb4cf590616ff6676c8e7c8bdc356c14e09a5a1fd"
    },
    "data/server/bin/combine_chances.bin":{
      "bytes":160,
      "sha256":"041f1d89c637566b170ef267f990f41405b7b7e3931cc9d730df5ea8c022cfeb"
    },
    "data/server/bin/combine_same_set_chances.bin":{
      "bytes":168,
      "sha256":"dd6f943d9c40f55f2dc322acaf3ff8bc77330f360df2ebd0a6885000fbf120b3"
    },
    "data/server/bin/contacts.bin":{
      "bytes":1983168,
      "sha256":"93da4b8266e5db9650abd07378195fefa70b2ac43ea10ade8cf7431959650617"
    },
    "data/server/bin/conversionsets.bin":{
      "bytes":1304,
      "sha256":"f49989a4537a4b9395a9b77dbd7f69d69d8132dc134a12fbe7a06aef021a1888"
    },
    "data/server/bin/damagedecay.bin":{
      "bytes":88,
      "sha256":"288bcee933d4b2b43bc7a06ca559a1a3c2b8627ec13cc2ed2e88fec1a1c95c54"
    },
    "data/server/bin/designer_contact_tip_types.bin":{
      "bytes":304,
      "sha256":"a45c8bc79f2703083bade43181eca2f758c9007933ce747d22043741a0af1de2"
    },
    "data/server/bin/detailcats.bin":{
      "bytes":1108,
      "sha256":"b3c0f24047dd138017ba7870d6652a5348f98535f807e8b54eabbebfceb4cbe4"
    },
    "data/server/bin/details.bin":{
      "bytes":418868,
      "sha256":"d6e2c59a7ae3278e201ac6dc8c984f521d197345c0c0e0575cf9f3b189497f2a"
    },
    "data/server/bin/dialog.bin":{
      "bytes":1012364,
      "sha256":"c15afd70244fd610cd5b1c56b0c405085b24e84addb4a9b89208ea471ed45ed5"
    },
    "data/server/bin/dialogdefs.bin":{
      "bytes":3328,
      "sha256":"6cf5953eb5784ec95880671c0e6eb756d0e762581cd298bf861ba333a4dc6dd9"
    },
    "data/server/bin/dim_returns.bin":{
      "bytes":864,
      "sha256":"cf81588dc98b4264a5f4e27b86300d848363781834c81a8423f5ce6c74bd0c19"
    },
    "data/server/bin/emotes.bin":{
      "bytes":33140,
      "sha256":"57dd7ef923c5b61b21fcc40cf4bc1fad4d7e7f6df6e27212717c329b71671168"
    },
    "data/server/bin/exemplar_handicaps.bin":{
      "bytes":892,
      "sha256":"626456e3797195e8d79ff56e2ce742e3a581b38d4399400affb43bb488f8cafb"
    },
    "data/server/bin/experience.bin":{
      "bytes":512,
      "sha256":"1295f7e7ad69f49aa9187bf7a97f8fa4335af78df0bd778dcbc28d776669a4d0"
    },
    "data/server/bin/incarnate.bin":{
      "bytes":884,
      "sha256":"2ffee43e712fdc2b7502b9cf524f622eb85b6fea14b691eed3378614ddb9313f"
    },
    "data/server/bin/inventory_sizes.bin":{
      "bytes":1752,
      "sha256":"fec2eac9e09b23f4491c4b4e04fd63b15476de1ea10e696362b9d03a32f1b76d"
    },
    "data/server/bin/inventory_tier_bonus.bin":{
      "bytes":332,
      "sha256":"2be40f1058e99d97dc0a93f839bb61ef3885103bd7fc417e1c31181cfe6f55ff"
    },
    "data/server/bin/mapsspec.bin":{
      "bytes":66388,
      "sha256":"4d8af645a32eea00fcd2f3af1cb2cda7cc1131e3c9aff347c96196e2e8886ebb"
    },
    "data/server/bin/meritsRewards.bin":{
      "bytes":36376,
      "sha256":"56b365ce8249ff628496e75684c14cb90c25ca7d3814f73b5133a6fec6142880"
    },
    "data/server/bin/messages-en.bin":{
      "bytes":6933216,
      "sha256":"769d3419df025c3067aabb6f6c0bc97936c68f3ce2f6e660ee33adf1bb855f3f"
    },
    "data/server/bin/missionhostagespawns.bin":{
      "bytes":624,
      "sha256":"d493fb4cb08fdfe57c19b35002482365d5d41f1f15802c83916ac16d1fc1fd94"
    },
    "data/server/bin/missionspawns.bin":{
      "bytes":22284,
      "sha256":"ab47259759e1a47cfdf98f62f8f70b9dbecc5997b305a812be459a768d7074b3"
    },
    "data/server/bin/missionspecs.bin":{
      "bytes":355712,
      "sha256":"09fa2446df00c99a173fdd12f857aceaea286711a4bd2cd7abfddf883f822625"
    },
    "data/server/bin/monorails.bin":{
      "bytes":10496,
      "sha256":"c5f729c836618796654cfd07c6c1f2b352a4bc26e05e09e80c712e06e8fec233"
    },
    "data/server/bin/npcs_server.bin":{
      "bytes":530936,
      "sha256":"011b30bbe643133f7bcc9c6a087f6ec42b590d3af66e2bd7dbc0f668690ebf8e"
    },
    "data/server/bin/origins.bin":{
      "bytes":504,
      "sha256":"ec13f45bc83815bb6d2c440380360589217919c65cc637f94959e53c5410e033"
    },
    "data/server/bin/petBattleCreatureInfo.bin":{
      "bytes":6380,
      "sha256":"ee7ac2604a9db535fe21a9bf047be49f86e04e8262cfe1a0b73ca21a0b7c2766"
    },
    "data/server/bin/plots.bin":{
      "bytes":19260,
      "sha256":"f3568a21a3eda0a3e9120d2addd77b90d35d9e9124fbf30ff78300a888d2a25a"
    },
    "data/server/bin/powercats.bin":{
      "bytes":239304,
      "sha256":"e236f92e9bd0c3dc33058f7cc01795db21e7c6aa4d1b36d82be84c68035357ee"
    },
    "data/server/bin/powers.bin":{
      "bytes":62047164,
      "sha256":"3b563ea562eb7c96c95bdc4200ffdf8432638e5dceb8f792fca4e2e29f2047f9"
    },
    "data/server/bin/powersets.bin":{
      "bytes":3179276,
      "sha256":"5db7961a042540ad2675deea08a67905f0e596bb2997db9f2ec14e7d4babdebc"
    },
    "data/server/bin/pvptaskmodifiers.bin":{
      "bytes":216,
      "sha256":"395ae902328e24db1c9f61add366784a02b66729d301d59bfe8c1d76e2c58437"
    },
    "data/server/bin/randomgroupselection.bin":{
      "bytes":6620,
      "sha256":"54e4cb30a3d07c46a8b622e70ca252aaf199641326a3602ec5e0697537616467"
    },
    "data/server/bin/randommapselection.bin":{
      "bytes":424,
      "sha256":"c8190ad0104004dbc41b90b635a9c751aa93786e5a7714d295cbadae24231980"
    },
    "data/server/bin/roomcategories.bin":{
      "bytes":812,
      "sha256":"47298da5fbd1034f1bd338124c09f1df9939d3f8762fbeb09860df48c7b12e02"
    },
    "data/server/bin/roomtemplates.bin":{
      "bytes":25688,
      "sha256":"2fbd3f2fee1498a8c0dbb3eb21c278ff8734ea5d0013808cb1ac40b80408ffd3"
    },
    "data/server/bin/schedules.bin":{
      "bytes":520,
      "sha256":"a6b344b7f37b8bade2f5fbc28906d122690791ca08b381a10e6581664a348de6"
    },
    "data/server/bin/scriptdefs.bin":{
      "bytes":136408,
      "sha256":"c785a3ff7f2bad2612b39b1bd90b1fa8c58d3c2f405c59ffe7f10f37cd191d01"
    },
    "data/server/bin/seqstatebits.bin":{
      "bytes":15380,
      "sha256":"9c4a5aab4c2bffb99eb2416e76a692449ee26927beed3cdd86dece02af2b2aac"
    },
    "data/server/bin/spawndefs.bin":{
      "bytes":115084768,
      "sha256":"141fb3f67430c6d1cfad706cd9afd7664e63554462884b1b1dbfa6e5aa9ab81f"
    },
    "data/server/bin/staticmsg-en.bin":{
      "bytes":96413,
      "sha256":"7e52da7857144aeb06adfa5a3d574d6cfe3387f6cbd84c2dfc399dea1fef149d"
    },
    "data/server/bin/storyarc.bin":{
      "bytes":50639400,
      "sha256":"c0c667ae2e446e2dc959ae1f389588066469fb30e15de2d5a9568afe3e90b0e4"
    },
    "data/server/bin/storyarcmsg-en.bin":{
      "bytes":20926850,
      "sha256":"63035041f3505cb6ed14b8b79cb1648c1f6a75180a44dbb83c9670b2ad5823e5"
    },
    "data/server/bin/supergroup_badges.bin":{
      "bytes":20604,
      "sha256":"d1dc7826ef9143b09bad9fcac6ca58fbfb8ed42257825489ae0945316d0dc688"
    },
    "data/server/bin/tasksets.bin":{
      "bytes":36685476,
      "sha256":"d7f995419751844011b80ae5052317287a1e92fc8e797be6463126da2e95192f"
    },
    "data/server/bin/turnstile_server.bin":{
      "bytes":21028,
      "sha256":"229b31498370958d83b2776d9e59b637205a2f700bb419bf31070d83bff2056a"
    },
    "data/server/bin/tut_votekick.bin":{
      "bytes":84,
      "sha256":"6471eeaeb972a186860e417eb321b62c4a21bd904cb0a26a29f215686e44fd58"
    },
    "data/server/bin/villain_classes.bin":{
      "bytes":4228088,
      "sha256":"bc0789f03941d845f9574f6df4dd1ad953ad35328a3d7323c07d02d92fdbd523"
    },
    "data/server/bin/villain_origins.bin":{
      "bytes":124,
      "sha256":"2432c9d535ef7021d2c86ab9ea2e7049148304721e88163af3a3a2611bbeba3a"
    },
    "data/server/bin/villainrandomgroupselection.bin":{
      "bytes":5948,
      "sha256":"ac0874d1554c88b80e7874b36a4cf63b1cf71bb6e1ccc240db8caf704aebd3b8"
    },
    "data/server/bin/villainrandommapselection.bin":{
      "bytes":388,
      "sha256":"29107e77a21db08151a9b32b7917da6f24475d001ac1bfbe68e91a1614f5b229"
    },
    "data/server/bin/visionPhases.bin":{
      "bytes":328,
      "sha256":"4e1099f1b9234004b568c7e2899eecd8b63b6ed9a2c50c56b90ed6989f4a8d32"
    },
    "data/server/bin/visionPhasesExclusive.bin":{
      "bytes":916,
      "sha256":"60a6b76d7b7e481923eb87e1dd710dfe6dc3ab694999e061be2453514328ad15"
    },
    "data/server/bin/zone_event_karma.bin":{
      "bytes":224,
      "sha256":"3047b833eb5438a3a12a9b7eca57ae541d9e943dba509cae9e83ab4a61258b94"
    }
  }
}''')
CAPTURE_REPORT_SHA256 = 'd37e8126a874e96b25ba64b8804fc6c4b38970a89e86b2cb80ced985c558515a'


def pascal(value):
    encoded = value.encode()
    raw = struct.pack('<H', len(encoded))+encoded
    return raw+b'\0'*((-len(raw)) % 4)


def parse6(dependencies=None, body=b'\x04\0\0\0body', crc=123):
    """Build a real Parse6 envelope with Files1 entries and root table bytes."""
    if dependencies is None:
        dependencies = [('defs/example.def', 1767225600)]
    table = struct.pack('<I', len(dependencies))
    for name, timestamp in dependencies:
        table += pascal(name)+struct.pack('<I', timestamp)
    return (b'CrypticS'+struct.pack('<I', crc)+pascal('Parse6')+pascal('Files1')+
            struct.pack('<I', len(table))+table+struct.pack('<I', len(body))+body)


class NativeStartupReuseInventoryTests(unittest.TestCase):
    def setUp(self):
        self.before = copy.deepcopy(CAPTURED_INVENTORIES['before'])
        self.after = copy.deepcopy(CAPTURED_INVENTORIES['after'])

    def test_actual_captured_full_inventory_and_exact_eighteen_changes(self):
        self.assertEqual(len(self.before), 191)
        self.assertEqual(len(self.after), 191)
        self.assertEqual(fixture.digest(self.before), 'abb5688ab6aa245ed250d8dc806f438a544fb91cdedad8f537bc81411f47076b')
        self.assertEqual(fixture.digest(self.after), '9a31cc110fe41fc744fa5ab4e73ed2e3a036223569edc0a9b64869fa43056d5d')
        result = fixture.validate_delta(self.before, self.after)
        self.assertFalse(result['added'])
        self.assertFalse(result['removed'])
        self.assertEqual(len(result['changed']), 18)
        self.assertIn('data/server/bin/ProficiencyIds.bin', result['changed'])
        self.assertNotIn('data/server/bin/InvConcept.bin', result['changed'])
        self.assertNotIn('data/bin/PC_Def_UI.bin', result['changed'])
        self.assertEqual(self.before, CAPTURED_INVENTORIES['before'])
        self.assertEqual(self.after, CAPTURED_INVENTORIES['after'])

    def test_missing_added_or_changed_input_is_rejected(self):
        for mode in ('missing', 'added', 'same_count_changed', 'case_changed'):
            before = copy.deepcopy(self.before)
            first = next(iter(before))
            if mode == 'missing':
                before.pop(first)
            elif mode == 'added':
                before['data/bin/unexpected.bin'] = before[first]
            elif mode == 'same_count_changed':
                before[first]['sha256'] = '0'*64
            else:
                before[first.upper()] = before.pop(first)
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                fixture.validate_delta(before, self.after)

    def test_missing_added_changed_or_unregenerated_output_is_rejected(self):
        for mode in ('missing', 'added', 'same_count_changed', 'not_regenerated', 'extra_mutation'):
            after = copy.deepcopy(self.after)
            if mode == 'missing':
                after.pop('data/bin/sequencers.bin')
            elif mode == 'added':
                after['data/bin/unexpected.bin'] = after['data/bin/sequencers.bin']
            elif mode == 'same_count_changed':
                after['data/bin/PC_Def_Animation.bin']['sha256'] = '0'*64
            elif mode == 'not_regenerated':
                after['data/bin/LoyaltyReward.bin'] = self.before['data/bin/LoyaltyReward.bin']
            else:
                after['data/bin/sequencers.bin']['sha256'] = '0'*64
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                fixture.validate_delta(self.before, after)

    def test_only_changed_subset_cannot_replace_complete_inventory(self):
        changed = [name for name in self.before if self.before[name] != self.after[name]]
        with self.assertRaises(ValueError):
            fixture.validate_delta({name: self.before[name] for name in changed},
                                   {name: self.after[name] for name in changed})

    def test_schema_header_dates_allow_new_hashes_but_still_require_raw_validation(self):
        after = copy.deepcopy(self.after)
        schema_names = [name for name in self.before
                        if self.before[name] != self.after[name] and '/PC_' not in name]
        self.assertEqual(len(schema_names), 7)
        for name in schema_names:
            after[name]['sha256'] = hashlib.sha256(name.encode()).hexdigest()
        delta = fixture.validate_delta(self.before, after)
        self.assertEqual(len(delta['changed']), 18)
        self.assertNotEqual(fixture.digest(after), fixture.GENERATED_CACHE)
        # A permitted inventory hash is not payload or timestamp authority.
        with self.assertRaises(ValueError):
            fixture.parse6_equivalence(parse6(), parse6(body=b'\x04\0\0\0evil'))

    def test_schema_output_size_and_malformed_identity_are_rejected(self):
        for pin in ({'bytes': 8141, 'sha256': 'a'*64},
                    {'bytes': 8140, 'sha256': 'a'*63},
                    {'bytes': 8140, 'sha256': 'g'*64},
                    {'bytes': 8140, 'sha256': 123}):
            after = copy.deepcopy(self.after)
            after['data/bin/LoyaltyReward.bin'] = pin
            with self.subTest(pin=pin), self.assertRaises(ValueError):
                fixture.validate_delta(self.before, after)


class NativeStartupReuseParse6Tests(unittest.TestCase):
    def test_unchanged_real_envelope_is_equivalent(self):
        raw = parse6()
        result = fixture.parse6_equivalence(raw, raw)
        self.assertTrue(result['schema_crc_unchanged'])
        self.assertTrue(result['native_payload_bytes_unchanged'])
        self.assertEqual(result['native_payload_sha256'], hashlib.sha256(b'\x04\0\0\0body').hexdigest())

    def test_narrow_player_created_namespace_and_dependency_date_change(self):
        before = parse6([('scripts.loc/Player_Created/pc_rewards.txt', 1767225600)])
        after = parse6([('scripts/Player_Created/pc_rewards.txt', 1767229200)])
        result = fixture.parse6_equivalence(before, after)
        self.assertTrue(result['native_payload_bytes_unchanged'])
        self.assertEqual(result['before']['dependency_count'], 1)
        self.assertEqual(result['after']['dependency_count'], 1)

    def test_actual_native_copy_dates_are_accepted_without_normalizing_them(self):
        before = parse6([('account/loyaltyrewardtree.def', 1767225600)])
        after = parse6([('account/loyaltyrewardtree.def', 1791901234)])
        result = fixture.parse6_equivalence(before, after)
        self.assertEqual(result['after']['dependencies'][0]['timestamp'], 1791901234)
        self.assertTrue(result['native_payload_bytes_unchanged'])

    def test_dependency_reordering_or_reverse_namespace_change_is_rejected(self):
        a, b = ('defs/a.def', 1767225600), ('defs/b.def', 1767225600)
        with self.assertRaises(ValueError):
            fixture.parse6_equivalence(parse6([a, b]), parse6([b, a]))
        with self.assertRaises(ValueError):
            fixture.parse6_equivalence(
                parse6([('scripts/Player_Created/pc_rewards.txt', 1767225600)]),
                parse6([('scripts.loc/Player_Created/pc_rewards.txt', 1767225600)]))

    def test_payload_change_even_same_size_and_schema_change_are_rejected(self):
        before = parse6()
        for after in (parse6(body=b'\x04\0\0\0BODY'), parse6(crc=124),
                      parse6(body=b'\x05\0\0\0extra')):
            with self.subTest(after=after), self.assertRaises(ValueError):
                fixture.parse6_equivalence(before, after)

    def test_unrelated_dependency_membership_or_namespace_change_is_rejected(self):
        before = parse6([('scripts.loc/Player_Created/pc_rewards.txt', 1767225600)])
        dependencies = [[], [('defs/unrelated.def', 1767225600)],
                        [('scripts/Other/pc_rewards.txt', 1767225600)],
                        [('scripts/Player_Created/other.txt', 1767225600)],
                        [('scripts/Player_Created/pc_rewards.txt', 1767225600),
                         ('defs/added.def', 1767225600)]]
        for changed in dependencies:
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                fixture.parse6_equivalence(before, parse6(changed))

    def test_malformed_envelopes_cannot_masquerade_as_equal_payloads(self):
        raw = parse6()
        malformed = [raw[:-1], b'not Parse6', raw.replace(b'Files1', b'Files2'),
                     raw[:8]+b'\0'*4+raw[12:24],
                     parse6([('../escaped.def', 1767225600)]),
                     parse6([('defs/a.def', 1767225600), ('defs/A.def', 1767225600)]),
                     parse6([('defs/a.def', 0x80000000)]),
                     parse6([('defs/a.def', 0xffffffff)]),
                     parse6([('C:/absolute.def', 1767225600)]),
                     parse6([('defs//empty.def', 1767225600)]),
                     parse6([('defs/nul\x00.def', 1767225600)]),
                     raw+b'\0', raw.replace(b'defs/example.def', b'defs/example.de\xff')]
        for changed in malformed:
            with self.subTest(sha256=hashlib.sha256(changed).hexdigest()), self.assertRaises(ValueError):
                fixture.parse6_equivalence(raw, changed)


class NativeStartupReuseDependencyBindingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.runtime = Path(temporary.name)
        self.source = self.runtime/'data/account/loyaltyrewardtree.def'
        self.source.parent.mkdir(parents=True)
        self.source.write_bytes(b'actual immutable source')
        self.date = 1791901234
        self.mtime_ns = self.date*10**9+123456789
        os.utime(self.source, ns=(self.mtime_ns, self.mtime_ns))

    def decoded(self, timestamp=None, name='account/loyaltyrewardtree.def'):
        if timestamp is None:
            timestamp = self.date
        before = parse6([(name, 1767225600)])
        after = parse6([(name, timestamp)])
        return {'data/bin/LoyaltyReward.bin': fixture.parse6_equivalence(before, after)}

    def test_native_dates_bind_actual_case_insensitive_source_and_full_content(self):
        for offset in (0, -3600, 3600):
            with self.subTest(offset=offset):
                result = fixture.bind_dependency_sources(
                    self.runtime, self.decoded(self.date+offset, 'DATA/ACCOUNT/LoyaltyRewardTree.def'))
                bound = result['data/bin/LoyaltyReward.bin'][0]
                self.assertEqual(bound['path'], 'account/loyaltyrewardtree.def')
                self.assertEqual(bound['native_dependency_timestamp'], self.date+offset)
                self.assertEqual(bound['actual_source_mtime_ns'], self.mtime_ns)
                self.assertEqual(bound['actual_source'], {
                    'bytes': 23, 'sha256': hashlib.sha256(self.source.read_bytes()).hexdigest()})

    def test_wrong_date_or_zero_cannot_replace_an_actual_copy_date(self):
        for timestamp in (0, self.date-1, self.date+1, self.date+7200, 1767225600):
            with self.subTest(timestamp=timestamp), self.assertRaises(ValueError):
                fixture.bind_dependency_sources(self.runtime, self.decoded(timestamp))

    def test_missing_source_rejects_including_zero_date(self):
        self.source.unlink()
        for timestamp in (0, self.date):
            with self.subTest(timestamp=timestamp), self.assertRaises(ValueError):
                fixture.bind_dependency_sources(self.runtime, self.decoded(timestamp))

    def test_case_ambiguous_or_linked_source_rejects(self):
        duplicate = self.source.with_name('LoyaltyRewardTree.def')
        duplicate.write_bytes(b'ambiguous')
        with self.assertRaises(ValueError):
            fixture.bind_dependency_sources(self.runtime, self.decoded())
        duplicate.unlink()
        target = self.runtime/'outside.def'
        target.write_bytes(self.source.read_bytes())
        self.source.unlink()
        self.source.symlink_to(target)
        with self.assertRaises(ValueError):
            fixture.bind_dependency_sources(self.runtime, self.decoded())


class NativeStartupReuseProviderTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.parent = Path(temporary.name)
        self.runtime = self.parent/'runtime'
        self.runtime.mkdir()
        self.cache_names = {'data/bin/known.bin', 'data/server/bin/known.bin'}
        files = {'data/defs/source.def': b'source', 'data/bin/known.bin': b'cache',
                 'data/server/bin/known.bin': b'cache', 'data/bin/unlisted.bin': b'input',
                 'data/geobin/also-input.bin': b'world', 'piggs/server-animations.pigg': b'animations',
                 'MapServer.exe': b'native', 'provider.dll': b'dllbytes'}
        for name, data in files.items():
            path = self.runtime/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            os.utime(path, ns=(1767225600000000000, 1767225600000000000))

    def snapshot(self):
        return fixture.native_inputs(self.runtime, self.cache_names)

    def test_only_exact_named_caches_are_excluded(self):
        before = self.snapshot()
        self.assertEqual(before['files'], 6)
        self.assertTrue(before['full_content_hashed'])
        for name in self.cache_names:
            (self.runtime/name).write_bytes(b'new cache payload')
        self.assertEqual(before, self.snapshot())
        (self.runtime/'data/bin/unlisted.bin').write_bytes(b'changed')
        self.assertNotEqual(before, self.snapshot())

    def test_same_size_and_timestamp_provider_edits_change_identity(self):
        for name in ('data/defs/source.def', 'data/geobin/also-input.bin',
                     'piggs/server-animations.pigg', 'MapServer.exe', 'provider.dll'):
            with self.subTest(name=name):
                before = self.snapshot()
                path = self.runtime/name
                raw, stat = path.read_bytes(), path.stat()
                path.write_bytes(bytes(byte ^ 1 for byte in raw))
                os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
                self.assertEqual(path.stat().st_size, stat.st_size)
                self.assertEqual(path.stat().st_mtime_ns, stat.st_mtime_ns)
                self.assertNotEqual(before['inventory_sha256'], self.snapshot()['inventory_sha256'])

    def test_unexpected_provider_addition_or_removal_changes_identity(self):
        before = self.snapshot()
        path = self.runtime/'piggs/unexpected.pigg'
        path.write_bytes(b'unexpected provider')
        self.assertNotEqual(before, self.snapshot())
        path.unlink()
        self.assertEqual(before, self.snapshot())
        (self.runtime/'data/defs/source.def').unlink()
        self.assertNotEqual(before, self.snapshot())

    def test_cross_executable_provider_identity_excludes_only_exact_MapServer(self):
        before = self.snapshot()
        (self.runtime/'MapServer.exe').write_bytes(b'replacement native executable')
        after = self.snapshot()
        self.assertNotEqual(before['inventory_sha256'], after['inventory_sha256'])
        self.assertEqual(before['provider_except_MapServer_sha256'],
                         after['provider_except_MapServer_sha256'])
        (self.runtime/'provider.dll').write_bytes(b'replacement dependency')
        self.assertNotEqual(after['provider_except_MapServer_sha256'],
                            self.snapshot()['provider_except_MapServer_sha256'])

    def test_provider_and_even_excluded_cache_symlinks_are_rejected(self):
        for name in ('data/defs/source.def', 'data/bin/known.bin', 'MapServer.exe'):
            with self.subTest(name=name):
                path = self.runtime/name
                raw = path.read_bytes()
                path.unlink()
                path.symlink_to(self.runtime/'provider.dll')
                with self.assertRaises(ValueError):
                    self.snapshot()
                path.unlink()
                path.write_bytes(raw)

    def test_broken_native_component_symlink_is_rejected(self):
        (self.runtime/'missing.dll').symlink_to(self.parent/'does-not-exist')
        with self.assertRaises(ValueError):
            self.snapshot()

    def test_provider_and_even_excluded_cache_hardlinks_are_rejected(self):
        for name in ('data/defs/source.def', 'data/bin/known.bin', 'MapServer.exe'):
            with self.subTest(name=name):
                path = self.runtime/name
                link = self.parent/'extra-link'
                os.link(path, link)
                try:
                    with self.assertRaises(ValueError):
                        self.snapshot()
                finally:
                    link.unlink()

    def test_linked_provider_directory_or_runtime_root_is_rejected(self):
        directory = self.runtime/'data/linked'
        directory.symlink_to(self.runtime/'piggs', target_is_directory=True)
        with self.assertRaises(ValueError):
            self.snapshot()
        directory.unlink()
        alias = self.parent/'runtime-alias'
        alias.symlink_to(self.runtime, target_is_directory=True)
        with self.assertRaises(ValueError):
            fixture.native_inputs(alias, self.cache_names)


if __name__ == '__main__':
    unittest.main()
