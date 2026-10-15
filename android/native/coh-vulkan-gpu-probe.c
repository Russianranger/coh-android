/* Finite ARM64/glibc Vulkan prerequisite for the opt-in KGSL Turnip route.
 * KGSL property layouts mirror authenticated Mesa 26.0.0 msm_kgsl.h.
 * No renderer override, device selector, shader, game or user input is accepted.
 * A host-only fixture build exercises the queue against software Vulkan. That
 * build marker is explicitly forbidden in the distributed production package.
 */
#define _POSIX_C_SOURCE 200809L
#include <vulkan/vulkan.h>
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <time.h>
#include <unistd.h>

enum { FILL_BYTES = 4096, MAX_QUEUE_FAMILIES = 32 };
#define FILL_WORD UINT32_C(0x51c0a740)

struct coh_kgsl_devinfo {
    unsigned int device_id, chip_id, mmu_enabled;
    unsigned long gmem_gpubaseaddr;
    unsigned int gpu_id;
    size_t gmem_sizebytes;
};
struct coh_kgsl_getproperty { unsigned int type; void *value; size_t sizebytes; };
#define COH_KGSL_GETPROPERTY _IOWR(0x09, 0x2, struct coh_kgsl_getproperty)
_Static_assert(VK_DRIVER_ID_MESA_TURNIP == 18, "Pinned Vulkan Turnip driver ID");
_Static_assert(sizeof(struct coh_kgsl_devinfo) == 40, "ARM64 KGSL devinfo ABI");
_Static_assert(sizeof(struct coh_kgsl_getproperty) == 24, "ARM64 KGSL property ABI");

struct result {
    uint32_t vendor_id, device_id, device_type, api_version, driver_version, driver_id;
    uint32_t kgsl_chip_id, bytes_verified;
    int kgsl_verified, native_gpu_executed, fill_verified, passed;
    const char *failure_stage;
};

static uint64_t clock_ms(void) {
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now)) return 0;
    return (uint64_t)now.tv_sec * 1000 + (uint64_t)now.tv_nsec / 1000000;
}

static int a740_chip(uint32_t id) {
    return id == UINT32_C(0x43050a01) || id == UINT32_C(0x43050b00) ||
        (id & UINT32_C(0xffffff00)) == UINT32_C(0x07040000);
}

static int candidate_environment(void) {
    const char *driver = getenv("VK_DRIVER_FILES"), *icd = getenv("VK_ICD_FILENAMES");
    if (!driver || !icd || !driver[0] || strcmp(driver, icd) ||
        strlen(driver) > 1024 || driver[0] != '/' || strchr(driver, ':')) return 0;
    /* The Java launch begins with env -i; reject driver/device forcing anyway. */
    if (getenv("TU_FORCE_GPU_ID") || getenv("MESA_VK_DEVICE_SELECT") ||
        getenv("MESA_VK_DEVICE_SELECT_FORCE_DEFAULT_DEVICE") || getenv("VK_INSTANCE_LAYERS") ||
        getenv("VK_LAYER_PATH") || getenv("VK_ADD_DRIVER_FILES")) return 0;
    return 1;
}

static int kgsl_identity(struct result *r) {
    struct coh_kgsl_devinfo info;
    struct coh_kgsl_getproperty property;
    int fd, status;
    memset(&info, 0, sizeof(info)); memset(&property, 0, sizeof(property));
    fd = open("/dev/kgsl-3d0", O_RDWR);
    if (fd < 0) return 0;
    property.type = 1; property.value = &info; property.sizebytes = sizeof(info);
    do { status = ioctl(fd, COH_KGSL_GETPROPERTY, &property); } while (status < 0 && errno == EINTR);
    close(fd);
    if (status < 0 || !a740_chip(info.chip_id)) return 0;
    r->kgsl_chip_id = info.chip_id; r->kgsl_verified = 1;
    return 1;
}

static int hardware_identity(const struct result *r) {
    return r->vendor_id == 0x5143 && r->driver_id == VK_DRIVER_ID_MESA_TURNIP &&
        r->driver_version == VK_MAKE_VERSION(26, 0, 0) &&
        r->device_type == VK_PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU &&
        r->api_version >= VK_API_VERSION_1_2 && r->kgsl_verified &&
        r->device_id == r->kgsl_chip_id && a740_chip(r->device_id);
}

static void emit(const struct result *r, uint64_t elapsed) {
    printf("COH_VULKAN_GPU_PROBE_V1 {\"format\":1,\"pointer_bits\":64,"
        "\"status\":\"%s\",\"failure_stage\":\"%s\","
        "\"vendor_id\":%" PRIu32 ",\"device_id\":%" PRIu32 ",\"device_type\":%" PRIu32 ","
        "\"api_version\":%" PRIu32 ",\"driver_version\":%" PRIu32 ",\"driver_id\":%" PRIu32 ","
        "\"kgsl_chip_id\":%" PRIu32 ",\"kgsl_verified\":%s,"
        "\"native_gpu_executed\":%s,\"fill_verified\":%s,\"bytes_verified\":%" PRIu32 ","
        "\"expected_bytes\":4096,\"elapsed_ms\":%" PRIu64 "}\n",
        r->passed ? "passed" : "failed", r->passed ? "" : r->failure_stage,
        r->vendor_id, r->device_id, r->device_type, r->api_version, r->driver_version, r->driver_id,
        r->kgsl_chip_id, r->kgsl_verified ? "true" : "false",
        r->native_gpu_executed ? "true" : "false", r->fill_verified ? "true" : "false",
        r->bytes_verified, elapsed);
}

int main(int argc, char **argv) {
    struct result r = {0};
    uint64_t started = clock_ms();
    VkInstance instance = VK_NULL_HANDLE;
    VkDevice device = VK_NULL_HANDLE;
    VkBuffer buffer = VK_NULL_HANDLE;
    VkDeviceMemory memory = VK_NULL_HANDLE;
    VkCommandPool pool = VK_NULL_HANDLE;
    VkFence fence = VK_NULL_HANDLE;
    VkPhysicalDevice physical = VK_NULL_HANDLE;
    VkCommandBuffer command = VK_NULL_HANDLE;
    VkQueue queue = VK_NULL_HANDLE;
    VkPhysicalDeviceDriverProperties driver_properties = { .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_DRIVER_PROPERTIES };
    VkPhysicalDeviceProperties2 properties = { .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2, .pNext = &driver_properties };
    VkApplicationInfo app = { .sType = VK_STRUCTURE_TYPE_APPLICATION_INFO, .pApplicationName = "COH finite GPU prerequisite", .apiVersion = VK_API_VERSION_1_2 };
    VkInstanceCreateInfo instance_info = { .sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO, .pApplicationInfo = &app };
    VkQueueFamilyProperties families[MAX_QUEUE_FAMILIES];
    VkPhysicalDeviceMemoryProperties memory_properties;
    VkMemoryRequirements memory_requirements;
    uint32_t count = 0, family = UINT32_MAX, memory_type = UINT32_MAX, i;
    VkMemoryPropertyFlags selected_memory = 0;
    void *mapped = NULL;
    int submitted = 0;
    (void)argv;
    r.failure_stage = "arguments";
#ifdef COH_VULKAN_GPU_PROBE_HOST_FIXTURE
    fputs("COH_VULKAN_GPU_PROBE_BUILD:host_fixture\n", stderr);
#else
    fputs("COH_VULKAN_GPU_PROBE_BUILD:production\n", stderr);
#endif
    if (argc != 1 || sizeof(void *) != 8) goto cleanup;
    r.failure_stage = "environment";
    if (!candidate_environment()) goto cleanup;
#ifndef COH_VULKAN_GPU_PROBE_HOST_FIXTURE
    r.failure_stage = "kgsl";
    if (!kgsl_identity(&r)) goto cleanup;
#else
    /* Retain/reach production helpers in fixture builds without granting identity. */
    (void)kgsl_identity;
#endif
    r.failure_stage = "instance";
    if (vkCreateInstance(&instance_info, NULL, &instance) != VK_SUCCESS) goto cleanup;
    r.failure_stage = "devices";
    if (vkEnumeratePhysicalDevices(instance, &count, NULL) != VK_SUCCESS || count != 1) goto cleanup;
    if (vkEnumeratePhysicalDevices(instance, &count, &physical) != VK_SUCCESS || count != 1) goto cleanup;
    vkGetPhysicalDeviceProperties2(physical, &properties);
    r.vendor_id = properties.properties.vendorID; r.device_id = properties.properties.deviceID;
    r.device_type = properties.properties.deviceType; r.api_version = properties.properties.apiVersion;
    r.driver_version = properties.properties.driverVersion; r.driver_id = (uint32_t)driver_properties.driverID;
    r.failure_stage = "identity";
#ifndef COH_VULKAN_GPU_PROBE_HOST_FIXTURE
    if (!hardware_identity(&r)) goto cleanup;
#endif
    r.failure_stage = "queues";
    vkGetPhysicalDeviceQueueFamilyProperties(physical, &count, NULL);
    if (!count || count > MAX_QUEUE_FAMILIES) goto cleanup;
    vkGetPhysicalDeviceQueueFamilyProperties(physical, &count, families);
    for (i = 0; i < count; ++i) if (families[i].queueCount &&
        (families[i].queueFlags & (VK_QUEUE_TRANSFER_BIT | VK_QUEUE_GRAPHICS_BIT | VK_QUEUE_COMPUTE_BIT))) { family = i; break; }
    if (family == UINT32_MAX) goto cleanup;
    r.failure_stage = "device";
    {
        float priority = 1.0f;
        VkDeviceQueueCreateInfo queue_info = { .sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,
            .queueFamilyIndex = family, .queueCount = 1, .pQueuePriorities = &priority };
        VkDeviceCreateInfo info = { .sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO, .queueCreateInfoCount = 1, .pQueueCreateInfos = &queue_info };
        if (vkCreateDevice(physical, &info, NULL, &device) != VK_SUCCESS) goto cleanup;
        vkGetDeviceQueue(device, family, 0, &queue);
    }
    r.failure_stage = "buffer";
    {
        VkBufferCreateInfo info = { .sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO,
            .size = FILL_BYTES, .usage = VK_BUFFER_USAGE_TRANSFER_DST_BIT, .sharingMode = VK_SHARING_MODE_EXCLUSIVE };
        if (vkCreateBuffer(device, &info, NULL, &buffer) != VK_SUCCESS) goto cleanup;
    }
    vkGetBufferMemoryRequirements(device, buffer, &memory_requirements);
    vkGetPhysicalDeviceMemoryProperties(physical, &memory_properties);
    r.failure_stage = "memory";
    if (memory_requirements.size < FILL_BYTES || memory_requirements.size > 1024 * 1024) goto cleanup;
    for (i = 0; i < memory_properties.memoryTypeCount; ++i) if (
        (memory_requirements.memoryTypeBits & (UINT32_C(1) << i)) &&
        (memory_properties.memoryTypes[i].propertyFlags & VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT)) {
        memory_type = i; selected_memory = memory_properties.memoryTypes[i].propertyFlags;
        if (selected_memory & VK_MEMORY_PROPERTY_HOST_COHERENT_BIT) break;
    }
    if (memory_type == UINT32_MAX) goto cleanup;
    {
        VkMemoryAllocateInfo info = { .sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO,
            .allocationSize = memory_requirements.size, .memoryTypeIndex = memory_type };
        if (vkAllocateMemory(device, &info, NULL, &memory) != VK_SUCCESS ||
            vkBindBufferMemory(device, buffer, memory, 0) != VK_SUCCESS) goto cleanup;
    }
    r.failure_stage = "map";
    if (vkMapMemory(device, memory, 0, VK_WHOLE_SIZE, 0, &mapped) != VK_SUCCESS) goto cleanup;
    memset(mapped, 0, FILL_BYTES);
    if (!(selected_memory & VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)) {
        VkMappedMemoryRange range = { .sType = VK_STRUCTURE_TYPE_MAPPED_MEMORY_RANGE, .memory = memory, .size = VK_WHOLE_SIZE };
        if (vkFlushMappedMemoryRanges(device, 1, &range) != VK_SUCCESS) goto cleanup;
    }
    vkUnmapMemory(device, memory); mapped = NULL;
    r.failure_stage = "pool";
    {
        VkCommandPoolCreateInfo info = { .sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO, .queueFamilyIndex = family };
        if (vkCreateCommandPool(device, &info, NULL, &pool) != VK_SUCCESS) goto cleanup;
    }
    r.failure_stage = "command";
    {
        VkCommandBufferAllocateInfo info = { .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,
            .commandPool = pool, .level = VK_COMMAND_BUFFER_LEVEL_PRIMARY, .commandBufferCount = 1 };
        VkCommandBufferBeginInfo begin = { .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO, .flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT };
        VkBufferMemoryBarrier barrier = { .sType = VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER,
            .srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT, .dstAccessMask = VK_ACCESS_HOST_READ_BIT,
            .srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED, .dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED,
            .buffer = buffer, .offset = 0, .size = FILL_BYTES };
        if (vkAllocateCommandBuffers(device, &info, &command) != VK_SUCCESS ||
            vkBeginCommandBuffer(command, &begin) != VK_SUCCESS) goto cleanup;
        vkCmdFillBuffer(command, buffer, 0, FILL_BYTES, FILL_WORD);
        vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_HOST_BIT,
            0, 0, NULL, 1, &barrier, 0, NULL);
        if (vkEndCommandBuffer(command) != VK_SUCCESS) goto cleanup;
    }
    r.failure_stage = "fence";
    {
        VkFenceCreateInfo info = { .sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO };
        if (vkCreateFence(device, &info, NULL, &fence) != VK_SUCCESS) goto cleanup;
    }
    r.failure_stage = "submit";
    {
        VkSubmitInfo info = { .sType = VK_STRUCTURE_TYPE_SUBMIT_INFO, .commandBufferCount = 1, .pCommandBuffers = &command };
        if (vkQueueSubmit(queue, 1, &info, fence) != VK_SUCCESS) goto cleanup;
        submitted = 1;
    }
    r.failure_stage = "wait";
    if (vkWaitForFences(device, 1, &fence, VK_TRUE, UINT64_C(5000000000)) != VK_SUCCESS) goto cleanup;
    submitted = 0;
    r.failure_stage = "map";
    if (vkMapMemory(device, memory, 0, VK_WHOLE_SIZE, 0, &mapped) != VK_SUCCESS) goto cleanup;
    if (!(selected_memory & VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)) {
        VkMappedMemoryRange range = { .sType = VK_STRUCTURE_TYPE_MAPPED_MEMORY_RANGE, .memory = memory, .size = VK_WHOLE_SIZE };
        if (vkInvalidateMappedMemoryRanges(device, 1, &range) != VK_SUCCESS) goto cleanup;
    }
    r.failure_stage = "readback";
    for (i = 0; i < FILL_BYTES / sizeof(uint32_t); ++i) {
        if (((const uint32_t *)mapped)[i] != FILL_WORD) goto cleanup;
        r.bytes_verified += sizeof(uint32_t);
    }
    r.fill_verified = 1; r.native_gpu_executed = hardware_identity(&r); r.passed = 1;
cleanup:
    /* External supervisor bounds all driver calls, including lost-device cleanup. */
    if (submitted && device) (void)vkDeviceWaitIdle(device);
    if (mapped && device && memory) vkUnmapMemory(device, memory);
    if (fence && device) vkDestroyFence(device, fence, NULL);
    if (pool && device) vkDestroyCommandPool(device, pool, NULL);
    if (buffer && device) vkDestroyBuffer(device, buffer, NULL);
    if (memory && device) vkFreeMemory(device, memory, NULL);
    if (device) vkDestroyDevice(device, NULL);
    if (instance) vkDestroyInstance(instance, NULL);
    emit(&r, clock_ms() - started);
    return r.passed ? 0 : 1;
}
