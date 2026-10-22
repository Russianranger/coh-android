# ArmPort test programs. Added by the patched top-level CMakeLists through
# -DCOX_ARMPORT_TESTS_DIR=<repo>/armport/tests (ARM64 Windows builds only).
include(StructParser)

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
