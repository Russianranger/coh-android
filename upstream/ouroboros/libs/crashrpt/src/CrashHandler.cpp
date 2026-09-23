///////////////////////////////////////////////////////////////////////////////
//
//  Module: CrashHandler.cpp
//
//    Desc: See CrashHandler.h
//
// Copyright (c) 2003 Michael Carruth
//
///////////////////////////////////////////////////////////////////////////////

#include "pch.h"
#include "CrashHandler.h"
#include <process.h>
#include <stdio.h>
#include <map>

static std::map<int, CCrashHandler*> _crashStateMap;

// unhandled exception callback set with SetUnhandledExceptionFilter()
LONG WINAPI CustomUnhandledExceptionFilter(PEXCEPTION_POINTERS pExInfo)
{
    //CCrashHandler* handler= _crashStateMap.Lookup(_getpid());
    auto it = _crashStateMap.find(_getpid());
    if (it != _crashStateMap.end())
    {
        it->second->GenerateErrorReport(pExInfo, "UnknownAuth", "UnknownEntity", "UnknownShard", "UnknownShardTime", "0.0", "CustomUnhandledExceptionFilter", "UnknownGLFileName", "UnknownLauncherLogFile", GetCurrentThreadId());
        //handler->HandleException(pExInfo);
    }
    return EXCEPTION_EXECUTE_HANDLER;
}

CCrashHandler::CCrashHandler(LPGETLOGFILE lpfn /*=NULL*/)
{
    // Save user supplied callback
    if (lpfn)
    {
        m_lpfnCallback = lpfn;
    }

    // add this filter in the exception callback chain
    m_oldFilter = SetUnhandledExceptionFilter(CustomUnhandledExceptionFilter);

    // attach this handler with this process
    m_pid = _getpid();
    _crashStateMap.emplace(m_pid, this);
}

CCrashHandler::~CCrashHandler()
{
    // Reset exception callback
    if (m_oldFilter)
    {
        SetUnhandledExceptionFilter(m_oldFilter);
    }

    _crashStateMap.erase(m_pid);
}

void CCrashHandler::AddFile(LPCTSTR lpFile, LPCTSTR lpDesc)
{
}

static bool isEmtpyString(const char* str)
{
    const char* cursor = str;
    if (!str)
    {
        return false;
    }

    while(*cursor)
    {
        if (!isspace((unsigned char)* cursor))
        {
            return false;
        }
        cursor++;
    }

    return true;
}
void CCrashHandler::GenerateErrorReport(PEXCEPTION_POINTERS pExInfo, const char *szAuth, const char *szEntity, const char *szShard, const char *szShardTime, const char *szVersion, const char *szMessage, const char *glReportFileName, const char *launcherLogFileName, DWORD dwThreadID)
{
}

void CCrashHandler::AbortErrorReport()
{
}

void CCrashHandler::HandleException(PEXCEPTION_POINTERS pExInfo)
{
    if (this->m_oldFilter)
    {
        this->m_oldFilter(pExInfo);
    }
}
