/* sha512.h: Encapsulates the class representing the SHA-512 algorithm.
* 
* @author: Chris Cowden, ccowden@ncsoft.com
*
* created: 8/24/2006
*
* @file
*
* Functions:
*/

#ifndef _SHA512_H_
#define _SHA512_H_

#include "sha.h"
#include <string>

namespace cryptLib
{
    class sha512Impl;
    class sha512
    {
    public:

        // Construction/Destruction
        sha512();
        ~sha512();

        void GetMessageDigest(digest512& hash, std::string message);

    private:

        sha512Impl*    m_impl;
    };
} // namespace cryptLib

#endif // _SHA512_H_
