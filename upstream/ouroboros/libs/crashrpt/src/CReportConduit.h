#ifndef CREPORTCONDUIT_H
#define CREPORTCONDUIT_H

class CReportConduit
{
public:
    virtual int send(LPCSTR filename) = 0;
    virtual ~CReportConduit(){};
};

#endif
