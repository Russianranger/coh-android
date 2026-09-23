/***************************************************************************
 *     Copyright (c) 2006-2008, NCNC
 *     All Rights Reserved
 *     Confidential Property of NCSoft NorCal
 ***************************************************************************/
#ifndef REQUEST_SLOT_H
#define REQUEST_SLOT_H

#include "request.hpp"

void handlePacketClientSlot(Packet* pak_in);

class RequestSlot : public AccountClaimRequest {
    virtual bool Start(const void *extraData);
    virtual void State_Fulfill(bool timeout);
};

#endif // REQUEST_SLOT_H
