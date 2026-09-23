/* sha.h: Defines the global variables and types for the SHA (Secure Hash Algorithm) library.
* 
* @author: Chris Cowden, ccowden@ncsoft.com
*
* created: 8/23/2006
*
* @file
*
* Functions:
*/

#ifndef _SHA_H_
#define _SHA_H_

#include <string>
#include <cstdio>
#include <cstdint>

#define w_32_bits 32    // SHA-1, SHA-256 uses w=32, i.e. 32-bit "blocks"
#define w_64_bits 64    // SHA-512 uses w=64, i.e. 64-bit "blocks"

namespace cryptLib
{
    // the 512-bit hash (message digest)
    struct digest512
    {
        uint64_t _[8];
        std::string ToString()
        {
            char buf[129];
            snprintf(buf,129,"%16.16llx%16.16llx%16.16llx%16.16llx%16.16llx%16.16llx%16.16llx%16.16llx",_[0],_[1],_[2],_[3],_[4],_[5],_[6],_[7]);
            return std::string(buf);
        }
    };
} // namespace cryptLib

#endif // _SHA_H_
