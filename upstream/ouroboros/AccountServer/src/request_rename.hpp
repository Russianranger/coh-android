/***************************************************************************
 *     Copyright (c) 2006-2007, Cryptic Studios
 *     All Rights Reserved
 *     Confidential Property of Cryptic Studios
 ***************************************************************************/
#ifndef ORDER_RENAME_H
#define ORDER_RENAME_H

#include "request.hpp"

void handlePacketClientRename(Packet* pak_in);

class RequestRename : public AccountClaimRequest
{
    virtual bool Start(const void *extraData);
    virtual void State_Validate(bool timeout);
    virtual void State_Fulfill(bool timeout);
};

#endif // ORDER_RENAME_H
