/* Optional host backend; stock Android NDK deliberately does not link this.
 * OpenSSL handles entropy, constant-time exponentiation, digest and OAEP. */
#include "coh_auth.h"
#include <openssl/bn.h>
#include <openssl/evp.h>
#include <openssl/core_names.h>
#include <openssl/param_build.h>
#include <openssl/rsa.h>
#include <string.h>
static int group(BIGNUM **p,BIGNUM **q,BN_CTX *ctx){
 *p=BN_bin2bn(coh_auth_dh_prime,64,NULL);
 *q=BN_new();
 return *p&&*q&&BN_copy(*q,*p)&&BN_sub_word(*q,1)&&BN_rshift1(*q,*q)&&ctx;
}
static int peer_valid(const BIGNUM *v,const BIGNUM *p,const BIGNUM *q,BN_CTX *ctx){
 BIGNUM *upper=BN_dup(p),*check=BN_new();
 int ok=upper&&check&&BN_sub_word(upper,1)&&BN_cmp(v,BN_value_one())>0&&BN_cmp(v,upper)<0&&BN_mod_exp(check,v,q,p,ctx)&&BN_is_one(check);
 BN_clear_free(upper);
 BN_clear_free(check);
 return ok;
}
static CohStatus keypair(void *unused,uint8_t private_key[64],uint8_t public_key[64]){
 BIGNUM *p=NULL,*q=NULL,*x=BN_secure_new(),*y=BN_new(),*g=BN_new();
 BN_CTX *ctx=BN_CTX_secure_new();
 uint8_t a[64]={0},b[64]={0};
 CohStatus s=COH_IO;
 (void)unused;
 if(!x||!y||!g||!group(&p,&q,ctx)||!BN_set_word(g,2))goto done;
 BN_set_flags(x,BN_FLG_CONSTTIME);
 do{if(!BN_priv_rand_range(x,q))goto done;
 }while(BN_cmp(x,BN_value_one())<=0);
 if(!BN_mod_exp_mont_consttime(y,g,x,p,ctx,NULL)||!peer_valid(y,p,q,ctx)||BN_bn2binpad(x,a,64)!=64||BN_bn2binpad(y,b,64)!=64)goto done;
 memcpy(private_key,a,64);
 memcpy(public_key,b,64);
 s=COH_OK;
 done:coh_auth_wipe(a,64);
 coh_auth_wipe(b,64);
 BN_clear_free(x);
 BN_clear_free(y);
 BN_free(g);
 BN_free(p);
 BN_free(q);
 BN_CTX_free(ctx);
 return s;
}
static CohStatus shared(void *unused,const uint8_t private_key[64],const uint8_t peer_key[64],uint8_t out[64]){
 BIGNUM *p=NULL,*q=NULL,*x=BN_bin2bn(private_key,64,NULL),*peer=BN_bin2bn(peer_key,64,NULL),*secret=BN_secure_new();
 BN_CTX *ctx=BN_CTX_secure_new();
 uint8_t b[64]={0};
 CohStatus s=COH_IO;
 (void)unused;
 if(!x||!peer||!secret||!group(&p,&q,ctx))goto done;
 if(BN_cmp(x,BN_value_one())<=0||BN_cmp(x,q)>=0||!peer_valid(peer,p,q,ctx)){s=COH_INVALID;
 goto done;
 }
 BN_set_flags(x,BN_FLG_CONSTTIME);
 if(!BN_mod_exp_mont_consttime(secret,peer,x,p,ctx,NULL)||BN_is_zero(secret)||BN_is_one(secret)||BN_bn2binpad(secret,b,64)!=64)goto done;
 memcpy(out,b,64);
 s=COH_OK;
 done:coh_auth_wipe(b,64);
 BN_clear_free(x);
 BN_free(peer);
 BN_clear_free(secret);
 BN_free(p);
 BN_free(q);
 BN_CTX_free(ctx);
 return s;
}
static CohStatus digest(const EVP_MD *md,CohBytes in,uint8_t *out,unsigned expected){
 uint8_t b[EVP_MAX_MD_SIZE];
 unsigned n=0;
 if((!in.data&&in.size)||!out)return COH_INVALID;
 if(!EVP_Digest(in.data,in.size,b,&n,md,NULL)||n!=expected){coh_auth_wipe(b,sizeof(b));
 return COH_IO;
 }
 memcpy(out,b,n);
 coh_auth_wipe(b,sizeof(b));
 return COH_OK;
}
static CohStatus md5(void *ctx,CohBytes in,uint8_t out[16]){(void)ctx;
 return digest(EVP_md5(),in,out,16);
 }
static CohStatus sha512(void *ctx,CohBytes in,uint8_t out[64]){(void)ctx;
 return digest(EVP_sha512(),in,out,64);
 }
static CohStatus rsa(void *unused,CohBytes modulus,CohBytes exponent,CohBytes plain,uint8_t *out,size_t cap,size_t *bytes){
 BIGNUM *n=NULL,*e=NULL;
 EVP_PKEY *key=NULL;
 EVP_PKEY_CTX *build=NULL,*enc=NULL;
 OSSL_PARAM_BLD *builder=NULL;
 OSSL_PARAM *params=NULL;
 size_t k,chunk,total,i,used=0;
 uint8_t result[COH_AUTH_RSA_MAX];
 CohStatus s=COH_IO;
 (void)unused;
 if(!modulus.data||modulus.size<64||modulus.size>COH_AUTH_RSA_MAX||!exponent.data||!exponent.size||exponent.size>8||!plain.data||!plain.size||!out||!bytes)return COH_INVALID;
 n=BN_bin2bn(modulus.data,(int)modulus.size,NULL);
 e=BN_bin2bn(exponent.data,(int)exponent.size,NULL);
 if(!n||!e||!BN_is_odd(n)||!BN_is_odd(e)||BN_cmp(e,BN_value_one())<=0){s=COH_INVALID;
 goto done;
 }
 builder=OSSL_PARAM_BLD_new();
 if(!builder||!OSSL_PARAM_BLD_push_BN(builder,OSSL_PKEY_PARAM_RSA_N,n)||!OSSL_PARAM_BLD_push_BN(builder,OSSL_PKEY_PARAM_RSA_E,e))goto done;
 params=OSSL_PARAM_BLD_to_param(builder);
 build=EVP_PKEY_CTX_new_from_name(NULL,"RSA",NULL);
 if(!params||!build||EVP_PKEY_fromdata_init(build)<=0||EVP_PKEY_fromdata(build,&key,EVP_PKEY_PUBLIC_KEY,params)<=0)goto done;
 k=(size_t)EVP_PKEY_get_size(key);
 if(k<43||k>sizeof(result)){s=COH_INVALID;
 goto done;
 }chunk=k-42;
 if(plain.size>sizeof(result)||((plain.size+chunk-1)/chunk)>sizeof(result)/k){s=COH_LIMIT;
 goto done;
 }total=((plain.size+chunk-1)/chunk)*k;
 if(total>cap){s=COH_LIMIT;
 goto done;
 }
 enc=EVP_PKEY_CTX_new(key,NULL);
 if(!enc||EVP_PKEY_encrypt_init(enc)<=0||EVP_PKEY_CTX_set_rsa_padding(enc,RSA_PKCS1_OAEP_PADDING)<=0||EVP_PKEY_CTX_set_rsa_oaep_md(enc,EVP_sha1())<=0||EVP_PKEY_CTX_set_rsa_mgf1_md(enc,EVP_sha1())<=0)goto done;
 for(i=0;i<plain.size;i+=chunk){size_t size=k,take=plain.size-i;
 if(take>chunk)take=chunk;
 if(EVP_PKEY_encrypt(enc,result+used,&size,plain.data+i,take)<=0||size!=k)goto done;
 used+=size;
 }
 memcpy(out,result,used);
 *bytes=used;
 s=COH_OK;
 done:coh_auth_wipe(result,sizeof(result));
 BN_free(n);
 BN_free(e);
 EVP_PKEY_CTX_free(build);
 EVP_PKEY_CTX_free(enc);
 EVP_PKEY_free(key);
 OSSL_PARAM_free(params);
 OSSL_PARAM_BLD_free(builder);
 return s;
}
const CohAuthCrypto *coh_auth_openssl_provider(void){static const CohAuthCrypto p={NULL,keypair,shared,md5,sha512,rsa};
 return &p;
 }
