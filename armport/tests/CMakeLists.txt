# ArmPort test programs. Added by the patched top-level CMakeLists through
# -DCOX_ARMPORT_TESTS_DIR=<repo>/armport/tests (ARM64 Windows builds only).
include(StructParser)

# Preflight required by Claude's replay-method review; not packet replay.
add_executable(armport_replay_sink src/replay_sink_test.c)
cox_target_defaults(armport_replay_sink)
target_link_libraries(armport_replay_sink PRIVATE UtilitiesLib)
target_link_options(armport_replay_sink PRIVATE -static)

# M1: the original textparser reads defs/ui/bodyparts.bp and the shipped
# BodyParts.bin on ARM64. BodyPart.c needs the generated bones_h_ast.h.
add_executable(armport_bodyparts
	src/bodyparts_test.c
	"${PROJECT_SOURCE_DIR}/Common/gameData/BodyPart.c"
	"${PROJECT_SOURCE_DIR}/Common/seq/bones.h"
	src/AutoGen/bones_h_ast.h)
set_source_files_properties(src/AutoGen/bones_h_ast.h PROPERTIES
	GENERATED TRUE HEADER_FILE_ONLY TRUE)
cox_target_defaults(armport_bodyparts)
target_include_directories(armport_bodyparts PRIVATE src
	"${PROJECT_SOURCE_DIR}/Common" "${PROJECT_SOURCE_DIR}/Game/src")
target_compile_definitions(armport_bodyparts PRIVATE CLIENT)
target_link_libraries(armport_bodyparts PRIVATE UtilitiesLib)
# One self-contained executable: no compiler runtime DLLs to copy into Wine.
target_link_options(armport_bodyparts PRIVATE -static)
StructParse(armport_bodyparts)

# M2: address space of an ARM64 program under Wine, with and without the
# large-address-aware flag (see src/address_space_test.c).
foreach(variant IN ITEMS laa nolaa)
	add_executable(armport_address_space_${variant} src/address_space_test.c)
	target_link_options(armport_address_space_${variant} PRIVATE -static)
endforeach()
target_link_options(armport_address_space_nolaa PRIVATE "-Wl,-Xlink=/largeaddressaware:no")
