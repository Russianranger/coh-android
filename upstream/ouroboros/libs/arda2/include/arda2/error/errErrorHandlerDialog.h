/*****************************************************************************
    created:    2002/05/02
    copyright:    2002, NCSoft. All Rights Reserved
    author(s):    Peter M. Freese

    purpose:    Error dialog with stack trace and ignore capability
*****************************************************************************/

#ifndef   INCLUDED_errErrorHandlerDialog
#define   INCLUDED_errErrorHandlerDialog
#if _MSC_VER > 1000
#pragma once
#endif // _MSC_VER > 1000


#include "../core/corErrorHandler.h"
#include "../core/corStlHashSet.h"

struct FileLine
{
    const char *m_filename;
    int            m_line;

    bool operator==( const FileLine &o ) const
    { 
        return o.m_filename == m_filename && o.m_line == m_line;
    }
};

namespace std
{
    template<> struct hash<FileLine>
    {
        std::size_t operator()(const FileLine& key) const
        {
            return reinterpret_cast<size_t>(key.m_filename) ^ static_cast<size_t>(key.m_line);
        }
    };
}

#if !CORE_SYSTEM_XENON

class errErrorHandlerDialog : public corErrorHandler
{
    typedef std::unordered_set<FileLine> IgnoreHashSet;

public:
    errErrorHandlerDialog( HINSTANCE hInst );

    //* This is set so fullscreen errors are reported over the 3D window
    static void SetRootHWND( HWND root ) { s_RootHWND = root; }

protected:  
    errHandlerResult Report(const char* szFileName, int iLineNumber, 
        errSeverity nSeverity, const char *szErrorLevel, const char* szDescription);

    IgnoreHashSet        m_ignores;
    HINSTANCE            m_hInst;

    static HWND s_RootHWND;
};

#endif // !CORE_SYSTEM_XENON

#endif // INCLUDED_errErrorHandlerDialog

