#ifndef COH_QUALIFICATION_NX_OWNED_BOUNDED_STREAM_H
#define COH_QUALIFICATION_NX_OWNED_BOUNDED_STREAM_H

// NONSHIPPING adapter. Compile against the real, unchanged vendor SDK headers.
// NxStream has no error return: check isValid BEFORE and AFTER SDK consumers;
// reject/release a returned mesh on stream failure and always reject NULL mesh.
#include "owned_bounded_stream.h"
#include <NxSimpleTypes.h>
#include <NxStream.h>

namespace coh_qualification {

class NxOwnedBoundedStream : public NxStream {
public:
    typedef OwnedBoundedStream::Allocator Allocator;
    explicit NxOwnedBoundedStream(std::size_t byteLimit, Allocator allocator = Allocator())
        : buffer_(byteLimit, allocator) {}
    NxOwnedBoundedStream(const void* source, std::ptrdiff_t bytes, std::size_t byteLimit,
                         Allocator allocator = Allocator())
        : buffer_(source, bytes, byteLimit, allocator) {}
    virtual ~NxOwnedBoundedStream() {}

    bool isValid() const { return buffer_.isValid(); }
    OwnedBoundedStream::Error error() const { return buffer_.error(); }
    bool beginRead() { return buffer_.beginRead(); }
    const OwnedBoundedStream& buffer() const { return buffer_; }

    virtual NxU8 readByte() const { return buffer_.readPrimitive<NxU8>(); }
    virtual NxU16 readWord() const { return buffer_.readPrimitive<NxU16>(); }
    virtual NxU32 readDword() const { return buffer_.readPrimitive<NxU32>(); }
    virtual NxF32 readFloat() const { return buffer_.readPrimitive<NxF32>(); }
    virtual NxF64 readDouble() const { return buffer_.readPrimitive<NxF64>(); }
    virtual void readBuffer(void* destination, NxU32 bytes) const { buffer_.read(destination, bytes); }

    // Retain the genuine NxStream signed convenience overloads as well.
    using NxStream::storeByte;
    using NxStream::storeWord;
    using NxStream::storeDword;
    virtual NxStream& storeByte(NxU8 value) { buffer_.writePrimitive(value); return *this; }
    virtual NxStream& storeWord(NxU16 value) { buffer_.writePrimitive(value); return *this; }
    virtual NxStream& storeDword(NxU32 value) { buffer_.writePrimitive(value); return *this; }
    virtual NxStream& storeFloat(NxF32 value) { buffer_.writePrimitive(value); return *this; }
    virtual NxStream& storeDouble(NxF64 value) { buffer_.writePrimitive(value); return *this; }
    virtual NxStream& storeBuffer(const void* source, NxU32 bytes) { buffer_.write(source, bytes); return *this; }

private:
    NxOwnedBoundedStream(const NxOwnedBoundedStream&);
    NxOwnedBoundedStream& operator=(const NxOwnedBoundedStream&);
    OwnedBoundedStream buffer_;
};

} // namespace coh_qualification
#endif
