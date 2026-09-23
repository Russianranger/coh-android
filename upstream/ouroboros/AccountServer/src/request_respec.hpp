/***************************************************************************
 *     Copyright (c) 2006-2007, Cryptic Studios
 *     All Rights Reserved
 *     Confidential Property of Cryptic Studios
 ***************************************************************************/
#ifndef REQUEST_RESPEC_H
#define REQUEST_RESPEC_H

#include "request.hpp"

void handlePacketClientRespec(Packet* pak_in);

class RequestRespec : public AccountClaimRequest {
    virtual void State_Validate(bool timeout);
    virtual void State_Fulfill(bool timeout);
};

#endif // REQUEST_RESPEC_H
