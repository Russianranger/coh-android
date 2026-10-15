// Host byte-stream fixtures only. No PhysX DLL, cooker, or mesh executes here.
#include "nx_owned_bounded_stream.h"
#include <cstdio>
#include <limits>
#include <map>
#include <string>
#include <vector>

using coh_qualification::OwnedBoundedStream;
using coh_qualification::NxOwnedBoundedStream;

#define CHECK(condition) do { if (!(condition)) { \
    std::fprintf(stderr, "check failed at line %d: %s\n", __LINE__, #condition); \
    std::exit(1); } } while (0)

struct TrackingAllocator {
    std::map<void*, std::size_t> blocks;
    std::size_t calls, releases, failOn, live, peak;
    TrackingAllocator() : calls(0), releases(0), failOn(0), live(0), peak(0) {}
    ~TrackingAllocator() { CHECK(blocks.empty()); CHECK(live == 0); }
    static void* allocate(void* context, std::size_t bytes) {
        TrackingAllocator& self = *static_cast<TrackingAllocator*>(context);
        ++self.calls;
        CHECK(bytes != 0);
        if (self.calls == self.failOn) return NULL;
        void* block = std::malloc(bytes);
        CHECK(block != NULL);
        std::memset(block, 0xa5, bytes);
        CHECK(self.blocks.insert(std::make_pair(block, bytes)).second);
        self.live += bytes;
        if (self.live > self.peak) self.peak = self.live;
        return block;
    }
    static void release(void* context, void* block) {
        TrackingAllocator& self = *static_cast<TrackingAllocator*>(context);
        CHECK(block != NULL);
        std::map<void*, std::size_t>::iterator found = self.blocks.find(block);
        CHECK(found != self.blocks.end()); // Catches double release or wrong owner.
        self.live -= found->second;
        self.blocks.erase(found);
        ++self.releases;
        std::free(block);
    }
    OwnedBoundedStream::Allocator allocator() {
        return OwnedBoundedStream::Allocator(&allocate, &release, this);
    }
};

static void ownership() {
    TrackingAllocator firstOwner, secondOwner;
    {
        NxOwnedBoundedStream first(4096, firstOwner.allocator());
        first.storeDword(NxU32(0x11223344));
        {
            NxOwnedBoundedStream second(4096, secondOwner.allocator());
            second.storeDword(NxU32(0x55667788));
            CHECK(first.buffer().data() != second.buffer().data());
            CHECK(second.beginRead());
            CHECK(second.readDword() == NxU32(0x55667788));
        }
        CHECK(secondOwner.calls == secondOwner.releases);
        CHECK(first.beginRead());
        CHECK(first.readDword() == NxU32(0x11223344));
        CHECK(first.isValid());
    }
    CHECK(firstOwner.calls == firstOwner.releases);
}

template <typename T> static void appendExpected(std::vector<unsigned char>& bytes, T value) {
    const unsigned char* source = reinterpret_cast<const unsigned char*>(&value);
    bytes.insert(bytes.end(), source, source + sizeof(value));
}

static void parity() {
    NxOwnedBoundedStream stream(4096);
    NxStream& polymorphic = stream; // Actual vendor vtable/signatures, no fake NxStream.
    std::vector<unsigned char> expected;
    const NxU8 byte = 0xff;
    const NxU16 word = 0x1234;
    const NxU32 dword = 0x89abcdef;
    const NxF32 single = -123.25f;
    const NxF64 dbl = 1.0 / 3.0;
    const unsigned char bulk[] = {0, 7, 255, 128};
    polymorphic.storeByte(byte).storeWord(word).storeDword(dword).storeFloat(single).storeDouble(dbl);
    polymorphic.storeBuffer(bulk, sizeof(bulk));
    appendExpected(expected, byte); appendExpected(expected, word); appendExpected(expected, dword);
    appendExpected(expected, single); appendExpected(expected, dbl);
    expected.insert(expected.end(), bulk, bulk + sizeof(bulk));
    CHECK(stream.buffer().used() == expected.size());
    CHECK(std::memcmp(stream.buffer().data(), &expected[0], expected.size()) == 0);
    CHECK(stream.beginRead());
    CHECK(polymorphic.readByte() == byte);
    CHECK(polymorphic.readWord() == word);
    CHECK(polymorphic.readDword() == dword);
    CHECK(polymorphic.readFloat() == single);
    CHECK(polymorphic.readDouble() == dbl);
    unsigned char actual[sizeof(bulk)] = {0};
    polymorphic.readBuffer(actual, sizeof(actual));
    CHECK(std::memcmp(actual, bulk, sizeof(bulk)) == 0);
    CHECK(stream.buffer().remaining() == 0);
    CHECK(stream.isValid());
    NxOwnedBoundedStream signedWrappers(7);
    signedWrappers.storeByte(NxI8(-1));
    signedWrappers.storeWord(NxI16(-2));
    signedWrappers.storeDword(NxI32(-3));
    CHECK(signedWrappers.beginRead());
    CHECK(signedWrappers.readByte() == NxU8(-1));
    CHECK(signedWrappers.readWord() == NxU16(-2));
    CHECK(signedWrappers.readDword() == NxU32(-3));
}

static void shortReads() {
    const unsigned char source[] = {1, 2, 3, 4, 5, 6, 7, 8};
    NxOwnedBoundedStream byte(source, 0, 8); CHECK(byte.readByte() == 0); CHECK(!byte.isValid());
    NxOwnedBoundedStream word(source, 1, 8); CHECK(word.readWord() == 0); CHECK(!word.isValid());
    NxOwnedBoundedStream dword(source, 3, 8); CHECK(dword.readDword() == 0); CHECK(!dword.isValid());
    NxOwnedBoundedStream single(source, 3, 8); CHECK(single.readFloat() == 0); CHECK(!single.isValid());
    NxOwnedBoundedStream dbl(source, 7, 8); CHECK(dbl.readDouble() == 0); CHECK(!dbl.isValid());
    CHECK(dbl.error() == OwnedBoundedStream::ReadOverrun);
    CHECK(dbl.buffer().cursor() == 0);
    NxOwnedBoundedStream bulk(source, 4, 8);
    unsigned char destination[] = {0x9a};
    bulk.readBuffer(destination, std::numeric_limits<NxU32>::max());
    CHECK(destination[0] == 0x9a); // No bulk memset or partial copy on failure.
    CHECK(bulk.buffer().cursor() == 0);
    CHECK(bulk.error() == OwnedBoundedStream::ReadOverrun);
    bulk.readBuffer(destination, 1);
    CHECK(destination[0] == 0x9a); // Sticky failure, despite sufficient remaining input.
}

static void overflowAndCap() {
    OwnedBoundedStream huge(4);
    unsigned char source = 1;
    CHECK(!huge.write(&source, std::numeric_limits<std::size_t>::max()));
    CHECK(huge.error() == OwnedBoundedStream::CapacityExceeded);
    CHECK(huge.capacity() == 0 && huge.used() == 0);
    NxOwnedBoundedStream exact(4);
    exact.storeDword(NxU32(123));
    CHECK(exact.isValid() && exact.buffer().used() == 4 && exact.buffer().capacity() == 4);
    const unsigned char* before = exact.buffer().data();
    exact.storeByte(NxU8(1));
    CHECK(exact.error() == OwnedBoundedStream::CapacityExceeded);
    CHECK(exact.buffer().data() == before && exact.buffer().used() == 4);
    CHECK(!exact.beginRead());
    NxOwnedBoundedStream empty(0);
    empty.storeBuffer(NULL, 0);
    CHECK(empty.beginRead());
    empty.readBuffer(NULL, 0);
    CHECK(empty.isValid() && empty.buffer().data() == NULL);
    OwnedBoundedStream input(&source, 1, 4);
    unsigned char destination = 99;
    CHECK(!input.read(&destination, std::numeric_limits<std::size_t>::max()));
    CHECK(destination == 99 && input.cursor() == 0);
}

static void allocationFailure() {
    TrackingAllocator owner;
    owner.failOn = 1;
    {
        NxOwnedBoundedStream initial(4096, owner.allocator());
        initial.storeByte(NxU8(1));
        CHECK(initial.error() == OwnedBoundedStream::AllocationFailed);
        CHECK(initial.buffer().data() == NULL && initial.buffer().used() == 0);
        CHECK(!initial.beginRead());
    }
    owner.failOn = owner.calls + 2;
    {
        NxOwnedBoundedStream growing(4096, owner.allocator());
        growing.storeWord(NxU16(0x1234));
        const unsigned char* before = growing.buffer().data();
        const std::size_t oldCapacity = growing.buffer().capacity();
        std::vector<unsigned char> bytes(1024, 0x67);
        growing.storeBuffer(&bytes[0], static_cast<NxU32>(bytes.size()));
        CHECK(growing.error() == OwnedBoundedStream::AllocationFailed);
        CHECK(growing.buffer().data() == before);
        CHECK(growing.buffer().used() == 2 && growing.buffer().capacity() == oldCapacity);
        NxU16 oldWord = 0; std::memcpy(&oldWord, before, sizeof(oldWord));
        CHECK(oldWord == 0x1234);
        CHECK(!growing.beginRead());
        growing.storeBuffer(NULL, 1);
        CHECK(growing.error() == OwnedBoundedStream::AllocationFailed);
    }
    CHECK(owner.blocks.empty());
}

static void modes() {
    NxOwnedBoundedStream prematureRead(4);
    CHECK(prematureRead.readByte() == 0);
    CHECK(prematureRead.error() == OwnedBoundedStream::ModeMismatch);
    CHECK(!prematureRead.beginRead());
    NxOwnedBoundedStream afterRead(4);
    afterRead.storeByte(NxU8(1)); CHECK(afterRead.beginRead());
    afterRead.storeBuffer(NULL, 0);
    CHECK(afterRead.error() == OwnedBoundedStream::ModeMismatch);
    CHECK(afterRead.buffer().used() == 1);
    NxOwnedBoundedStream repeated(4);
    repeated.storeByte(NxU8(2)); CHECK(repeated.beginRead());
    CHECK(repeated.readByte() == 2);
    CHECK(!repeated.beginRead());
    CHECK(repeated.buffer().cursor() == 1);
}

static void invalidInput() {
    NxOwnedBoundedStream negative(NULL, -1, 4);
    CHECK(negative.error() == OwnedBoundedStream::InvalidSize);
    CHECK(!negative.beginRead());
    NxOwnedBoundedStream inputNull(NULL, 1, 4);
    CHECK(inputNull.error() == OwnedBoundedStream::NullBuffer);
    NxOwnedBoundedStream outputNull(4);
    outputNull.storeBuffer(NULL, 1); CHECK(outputNull.error() == OwnedBoundedStream::NullBuffer);
    const unsigned char byte = 1;
    NxOwnedBoundedStream destinationNull(&byte, 1, 4);
    destinationNull.readBuffer(NULL, 1);
    CHECK(destinationNull.error() == OwnedBoundedStream::NullBuffer);
    CHECK(destinationNull.buffer().cursor() == 0);
    OwnedBoundedStream badAllocate(4, OwnedBoundedStream::Allocator(NULL, &OwnedBoundedStream::defaultRelease));
    CHECK(badAllocate.error() == OwnedBoundedStream::InvalidAllocator);
    OwnedBoundedStream badRelease(4, OwnedBoundedStream::Allocator(&OwnedBoundedStream::defaultAllocate, NULL));
    CHECK(badRelease.error() == OwnedBoundedStream::InvalidAllocator);
    NxOwnedBoundedStream tooLarge(&byte, 5, 4);
    CHECK(tooLarge.error() == OwnedBoundedStream::CapacityExceeded);
    CHECK(tooLarge.buffer().capacity() == 0);
}

static void selfAppend() {
    OwnedBoundedStream stream(4096);
    std::vector<unsigned char> source(700, 0x17);
    CHECK(stream.write(&source[0], source.size()));
    CHECK(stream.write(stream.data(), stream.used()));
    CHECK(stream.used() == 1400 && stream.capacity() >= stream.used());
    CHECK(std::memcmp(stream.data(), &source[0], 700) == 0);
    CHECK(std::memcmp(stream.data() + 700, &source[0], 700) == 0);
    CHECK(stream.beginRead());
    OwnedBoundedStream bad(4096);
    CHECK(bad.write(&source[0], 1));
    CHECK(!bad.write(bad.data() + 1, 1));
    CHECK(bad.error() == OwnedBoundedStream::SourceExtent);
    CHECK(bad.used() == 1);
    OwnedBoundedStream onePast(4096);
    std::vector<unsigned char> full(1024, 0x32);
    CHECK(onePast.write(&full[0], full.size()));
    CHECK(onePast.used() == onePast.capacity());
    CHECK(!onePast.write(onePast.data() + onePast.capacity(), 1));
    CHECK(onePast.error() == OwnedBoundedStream::SourceExtent);
    CHECK(onePast.used() == 1024);
}

// A fake consumer demonstrates *caller* checks only. It is never labeled as
// SDK/collision qualification, and intentionally can return a mesh on bad IO.
struct Consumer {
    unsigned calls, releases;
    bool truncated, returnNull;
    Consumer() : calls(0), releases(0), truncated(false), returnNull(false) {}
    void* create(NxStream& stream) {
        ++calls;
        if (truncated) stream.readDouble(); else stream.readDword();
        return returnNull ? NULL : this;
    }
    void release(void* mesh) { CHECK(mesh == this); ++releases; }
};

static void* checkedConsumer(NxOwnedBoundedStream& stream, Consumer& consumer) {
    if (!stream.isValid() || stream.buffer().mode() != OwnedBoundedStream::Reading) return NULL;
    void* mesh = consumer.create(stream);
    if (!stream.isValid()) {
        if (mesh != NULL) consumer.release(mesh);
        return NULL;
    }
    if (mesh == NULL) return NULL;
    return mesh;
}

static void consumerBoundary() {
    const NxU32 input = 123;
    Consumer validConsumer;
    NxOwnedBoundedStream valid(&input, sizeof(input), 4);
    CHECK(checkedConsumer(valid, validConsumer) == &validConsumer);
    CHECK(validConsumer.calls == 1 && validConsumer.releases == 0);
    Consumer nullConsumer; nullConsumer.returnNull = true;
    NxOwnedBoundedStream nullMesh(&input, sizeof(input), 4);
    CHECK(checkedConsumer(nullMesh, nullConsumer) == NULL);
    CHECK(nullConsumer.calls == 1);
    Consumer badConsumer; badConsumer.truncated = true;
    NxOwnedBoundedStream shortMesh(&input, sizeof(input), 4);
    CHECK(checkedConsumer(shortMesh, badConsumer) == NULL);
    CHECK(badConsumer.calls == 1 && badConsumer.releases == 1);
    Consumer invalidConsumer;
    NxOwnedBoundedStream invalid(NULL, -1, 4);
    CHECK(checkedConsumer(invalid, invalidConsumer) == NULL);
    CHECK(invalidConsumer.calls == 0);
    Consumer writeConsumer;
    NxOwnedBoundedStream stillWriting(4);
    CHECK(checkedConsumer(stillWriting, writeConsumer) == NULL);
    CHECK(writeConsumer.calls == 0);
}

static void growth() {
    TrackingAllocator owner;
    {
        NxOwnedBoundedStream stream(3000, owner.allocator());
        std::vector<unsigned char> expected;
        for (unsigned i = 0; i < 3000; ++i) {
            const NxU8 byte = static_cast<NxU8>(i);
            stream.storeByte(byte); expected.push_back(byte);
            CHECK(stream.isValid());
            CHECK(stream.buffer().used() == expected.size());
            CHECK(stream.buffer().capacity() <= stream.buffer().limit());
        }
        CHECK(stream.buffer().capacity() == 3000);
        CHECK(std::memcmp(stream.buffer().data(), &expected[0], expected.size()) == 0);
        CHECK(owner.peak <= 6000); // Atomic allocate/copy/release can briefly hold two buffers.
        CHECK(stream.beginRead());
        for (unsigned i = 0; i < 3000; ++i) CHECK(stream.readByte() == static_cast<NxU8>(i));
        CHECK(stream.isValid() && stream.buffer().remaining() == 0);
    }
    CHECK(owner.calls == owner.releases);
    // No full-buffer zero initialization: unfilled allocation tail stays poisoned.
    TrackingAllocator poisonOwner;
    {
        OwnedBoundedStream stream(1024, poisonOwner.allocator());
        const unsigned char value = 1;
        CHECK(stream.write(&value, 1));
        CHECK(stream.capacity() == 1024 && stream.data()[1023] == 0xa5);
    }
}

int main(int argc, char** argv) {
    CHECK(argc == 2);
    const std::string selected(argv[1]);
    if (selected == "ownership") ownership();
    else if (selected == "parity") parity();
    else if (selected == "short_reads") shortReads();
    else if (selected == "overflow_and_cap") overflowAndCap();
    else if (selected == "allocation_failure") allocationFailure();
    else if (selected == "modes") modes();
    else if (selected == "invalid_input") invalidInput();
    else if (selected == "self_append") selfAppend();
    else if (selected == "consumer_boundary") consumerBoundary();
    else if (selected == "growth") growth();
    else { std::fprintf(stderr, "unknown fixture: %s\n", argv[1]); return 1; }
    std::printf("host bounded stream fixture passed: %s\n", argv[1]);
    return 0;
}
