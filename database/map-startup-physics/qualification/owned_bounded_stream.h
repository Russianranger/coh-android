#ifndef COH_QUALIFICATION_OWNED_BOUNDED_STREAM_H
#define COH_QUALIFICATION_OWNED_BOUNDED_STREAM_H

// NONSHIPPING qualification prerequisite. Not included by any native producer.
// No PhysX implementation is reproduced here; this is an owned byte buffer.
#include <cstddef>
#include <cstdlib>
#include <cstring>
#include <stdint.h>

namespace coh_qualification {

class OwnedBoundedStream {
public:
    enum Mode { Writing, Reading };
    enum Error {
        None, InvalidSize, InvalidAllocator, ModeMismatch, CapacityExceeded,
        AllocationFailed, ReadOverrun, NullBuffer, SourceExtent
    };

    typedef void* (*Allocate)(void*, std::size_t);
    typedef void (*Release)(void*, void*);

    static void* defaultAllocate(void*, std::size_t bytes) { return std::malloc(bytes); }
    static void defaultRelease(void*, void* pointer) { std::free(pointer); }

    struct Allocator {
        Allocate allocate;
        Release release;
        void* context;
        Allocator(Allocate allocateFunction = &defaultAllocate,
                  Release releaseFunction = &defaultRelease, void* allocatorContext = NULL)
            : allocate(allocateFunction), release(releaseFunction), context(allocatorContext) {}
    };

    explicit OwnedBoundedStream(std::size_t byteLimit, Allocator allocator = Allocator())
        : data_(NULL), capacity_(0), used_(0), cursor_(0), limit_(byteLimit),
          mode_(Writing), error_(None), allocator_(allocator) {
        validateAllocator();
    }

    // Signed size is deliberate: legacy callers pass int and must not convert
    // a negative stream size to a huge unsigned allocation request.
    OwnedBoundedStream(const void* source, std::ptrdiff_t bytes,
                       std::size_t byteLimit, Allocator allocator = Allocator())
        : data_(NULL), capacity_(0), used_(0), cursor_(0), limit_(byteLimit),
          mode_(Writing), error_(None), allocator_(allocator) {
        validateAllocator();
        if (bytes < 0) fail(InvalidSize);
        else write(source, static_cast<std::size_t>(bytes));
        beginRead(); // This cannot clear or revive an earlier error.
    }

    ~OwnedBoundedStream() {
        if (data_ != NULL) allocator_.release(allocator_.context, data_);
    }

    bool isValid() const { return error_ == None; }
    Error error() const { return error_; }
    Mode mode() const { return mode_; }
    std::size_t capacity() const { return capacity_; }
    std::size_t used() const { return used_; }
    std::size_t cursor() const { return cursor_; }
    std::size_t limit() const { return limit_; }
    std::size_t remaining() const { return used_ - cursor_; }
    const unsigned char* data() const { return data_; }

    bool beginRead() {
        if (!isValid()) return false;
        if (mode_ != Writing) return fail(ModeMismatch);
        mode_ = Reading;
        cursor_ = 0;
        return true;
    }

    bool write(const void* source, std::size_t bytes) {
        if (!isValid()) return false;
        if (mode_ != Writing) return fail(ModeMismatch);
        if (bytes == 0) return true;
        if (source == NULL) return fail(NullBuffer);
        // Subtraction checks avoid used + bytes overflow before any allocation.
        if (bytes > limit_ - used_) return fail(CapacityExceeded);

        // Self append remains safe if reserve relocates our allocation. Only
        // already initialized bytes may be copied from our own buffer.
        bool internalSource = false;
        std::size_t sourceOffset = 0;
        if (data_ != NULL) {
            const uintptr_t address = reinterpret_cast<uintptr_t>(source);
            const uintptr_t base = reinterpret_cast<uintptr_t>(data_);
            if (address >= base && address - base <= capacity_) {
                internalSource = true;
                sourceOffset = static_cast<std::size_t>(address - base);
                if (sourceOffset > used_ || bytes > used_ - sourceOffset)
                    return fail(SourceExtent);
            }
        }
        if (!reserve(used_ + bytes)) return false;
        if (internalSource) source = data_ + sourceOffset;
        std::memmove(data_ + used_, source, bytes);
        used_ += bytes;
        return true;
    }

    bool read(void* destination, std::size_t bytes) const {
        if (!isValid()) return false;
        if (mode_ != Reading) return fail(ModeMismatch);
        if (bytes == 0) return true;
        if (destination == NULL) return fail(NullBuffer);
        if (bytes > used_ - cursor_) return fail(ReadOverrun);
        std::memmove(destination, data_ + cursor_, bytes);
        cursor_ += bytes;
        return true;
        // Failure leaves the destination/cursor untouched. In particular, do
        // not memset an SDK-supplied bulk size after a malformed-input failure.
    }

    template <typename T> bool writePrimitive(T value) { return write(&value, sizeof(value)); }
    template <typename T> T readPrimitive() const {
        T value = T(); // Bounded scalar fallback only; validity must be checked.
        read(&value, sizeof(value));
        return value;
    }

private:
    OwnedBoundedStream(const OwnedBoundedStream&);
    OwnedBoundedStream& operator=(const OwnedBoundedStream&);

    void validateAllocator() {
        if (allocator_.allocate == NULL || allocator_.release == NULL) fail(InvalidAllocator);
    }

    bool fail(Error reason) const {
        if (error_ == None) error_ = reason;
        return false;
    }

    bool reserve(std::size_t required) {
        if (required <= capacity_) return true;
        std::size_t next = capacity_;
        if (next == 0) next = limit_ < 1024 ? limit_ : 1024;
        while (next < required) {
            const std::size_t growth = next / 2 == 0 ? 1 : next / 2;
            next = growth > limit_ - next ? limit_ : next + growth;
        }
        void* allocation = allocator_.allocate(allocator_.context, next);
        if (allocation == NULL) return fail(AllocationFailed);
        unsigned char* replacement = static_cast<unsigned char*>(allocation);
        if (used_ != 0) std::memcpy(replacement, data_, used_);
        unsigned char* old = data_;
        data_ = replacement;
        capacity_ = next;
        if (old != NULL) allocator_.release(allocator_.context, old);
        return true;
    }

    unsigned char* data_;
    std::size_t capacity_;
    std::size_t used_;
    mutable std::size_t cursor_;
    std::size_t limit_;
    Mode mode_;
    mutable Error error_;
    Allocator allocator_;
};

} // namespace coh_qualification
#endif
