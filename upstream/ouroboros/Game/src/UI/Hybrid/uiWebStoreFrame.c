#include "UI/Hybrid/uiWebStoreFrame.h"
#include "cmdparse/cmdgame.h"

#include "../../../Common/account/AccountCatalog.h"
#include "../../clientcomm/authclient.h"

extern AuthInfo    auth_info;

void webStoreOpenProduct(const char * product)
{
    if (product && accountCatalog_IsAutoBuyEnabled())
    {
        AccountStoreBuyProduct(auth_info.uid, skuIdFromString(product), 1);
        return;
    }
}

void webStoreOpenCategory(const char * category)
{
    if (category && accountCatalog_IsAutoBuyEnabled())
    {
        return;
    }
}

void webStoreAddToCart(const char * product)
{
    if (product && accountCatalog_IsAutoBuyEnabled())
    {
        AccountStoreBuyProduct(auth_info.uid, skuIdFromString(product), 1);
        return;
    }
}

void webStoreAddMultipleToCart(const ShoppingCart * products, U32 first, U32 last)
{
    U32 i;
    U32 numSkus = last - first;

    if (products && accountCatalog_IsAutoBuyEnabled())
    {
        devassert(numSkus && products->itemCount >= last);

        for (i = 0; i < numSkus; ++i)
        {
            AccountStoreBuyProduct(auth_info.uid, products->items[first+i], 1);
        }

        return;
    }
}
