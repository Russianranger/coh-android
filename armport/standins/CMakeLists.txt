# ArmPort stand-ins for the x86-only binary SDKs the client links on Win32.
# Added by the patched Game/CMakeLists.txt on ARM64 Windows builds only.

set(_coh_3rdparty "${PROJECT_SOURCE_DIR}/3rdparty")

# PhysX: compiled out on ARM64 (NOVODEX undefined). Headers only, for any
# remaining includes; nothing is linked.
foreach(component IN ITEMS Loader Cooking)
	add_library(PhysX::${component} INTERFACE IMPORTED GLOBAL)
	set_target_properties(PhysX::${component} PROPERTIES INTERFACE_INCLUDE_DIRECTORIES
		"${_coh_3rdparty}/PhysX/SDKs/Physics/include;${_coh_3rdparty}/PhysX/SDKs/Cooking/include;${_coh_3rdparty}/PhysX/SDKs/Foundation/include;${_coh_3rdparty}/PhysX/SDKs/PhysXLoader/include")
endforeach()
function(cox_stage_physx target)
endfunction()

# AlienFX and NvCpl: vendor extras; headers only.
add_library(AlienFX::AlienFX INTERFACE IMPORTED GLOBAL)
set_target_properties(AlienFX::AlienFX PROPERTIES INTERFACE_INCLUDE_DIRECTORIES
	"${_coh_3rdparty}/AlienFX SDK/Unmanaged/includes")
add_library(NvCpl::NvCpl INTERFACE IMPORTED GLOBAL)
set_target_properties(NvCpl::NvCpl PROPERTIES INTERFACE_INCLUDE_DIRECTORIES
	"${_coh_3rdparty}/nvcpl")

# nvDXT: stand-in for the four functions the client calls.
add_library(armport_nvdxt STATIC nvdxt/nvdxt_standin.cpp)
target_include_directories(armport_nvdxt PUBLIC "${_coh_3rdparty}/nvdxt")
target_compile_definitions(armport_nvdxt PUBLIC EXCLUDE_LIBS)
add_library(NvDxt::NvDxt ALIAS armport_nvdxt)

# Cg runtime: stand-in for the functions the client calls (cg/generate_standin.py).
add_library(armport_cg STATIC cg/cg_standin.cpp)
target_include_directories(armport_cg PUBLIC "${_coh_3rdparty}/cg/include")
add_library(Cg::Cg ALIAS armport_cg)
add_library(Cg::CgGL ALIAS armport_cg)
function(cox_stage_cg target)
endfunction()
