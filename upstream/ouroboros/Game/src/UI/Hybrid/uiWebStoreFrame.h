#ifndef UIWEBSTOREFRAME_H
#define UIWEBSTOREFRAME_H

#include <utilitieslib/stdtypes.h>
#include "account/AccountTypes.h"

typedef struct ShoppingCart
{
    SkuId * items;
    U32 itemCount;
} ShoppingCart;

void webStoreOpenProduct(const char * product);
void webStoreOpenCategory(const char * category);
void webStoreAddToCart(const char * product);
void webStoreAddMultipleToCart(const ShoppingCart * products, U32 first, U32 last);

#endif //UIWEBSTOREFRAME_H
