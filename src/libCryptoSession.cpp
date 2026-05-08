#include "libCryptoSession.hpp"
#include <openssl/core_names.h>
#include <openssl/kdf.h>   
#include <openssl/rand.h>  
#include <stdexcept>
#include <cstring>         

CryptoSession::CryptoSession(EVP_PKEY* personal_private_key, const std::vector<uint8_t>& peer_pub_key_bytes) 
    : my_private_key(personal_private_key) {
    
    if (!my_private_key) throw std::runtime_error("Private key is null");

    EVP_PKEY_CTX* ctx = EVP_PKEY_CTX_new_id(EVP_PKEY_EC, NULL);
    if (!ctx || EVP_PKEY_fromdata_init(ctx) <= 0) {
        if (ctx) EVP_PKEY_CTX_free(ctx);
        throw std::runtime_error("Failed to init fromdata context");
    }

    OSSL_PARAM params[3];
    params[0] = OSSL_PARAM_construct_utf8_string(OSSL_PKEY_PARAM_GROUP_NAME, (char*)"secp384r1", 0);
    params[1] = OSSL_PARAM_construct_octet_string(OSSL_PKEY_PARAM_PUB_KEY, (void*)peer_pub_key_bytes.data(), peer_pub_key_bytes.size());
    params[2] = OSSL_PARAM_construct_end();

    if (EVP_PKEY_fromdata(ctx, &peer_public_key, EVP_PKEY_PUBLIC_KEY, params) <= 0) {
        EVP_PKEY_CTX_free(ctx);
        throw std::runtime_error("Failed to decode peer public key (fromdata)");
    }

    EVP_PKEY_CTX_free(ctx);
    compute_ecdh();
}

CryptoSession::~CryptoSession() {
    if (peer_public_key) EVP_PKEY_free(peer_public_key);
    // DO NOT FREE my_private_key 
}

void CryptoSession::compute_ecdh() {
    EVP_PKEY_CTX* ctx = EVP_PKEY_CTX_new(my_private_key, nullptr);
    if (!ctx) throw std::runtime_error("Failed to create CTX");

    if (EVP_PKEY_derive_init(ctx) <= 0) {
        EVP_PKEY_CTX_free(ctx);
        throw std::runtime_error("Derive init failed");
    }

    if (EVP_PKEY_derive_set_peer(ctx, peer_public_key) <= 0) {
        EVP_PKEY_CTX_free(ctx);
        throw std::runtime_error("Failed to set peer key");
    }

    size_t secret_len;
    EVP_PKEY_derive(ctx, nullptr, &secret_len);

    SecureVector shared_secret(secret_len);
    if (EVP_PKEY_derive(ctx, shared_secret.data(), &secret_len) <= 0) {
        EVP_PKEY_CTX_free(ctx);
        throw std::runtime_error("Derivation failed");
    }

    EVP_PKEY_CTX_free(ctx);

    derive_hkdf(shared_secret);
}

void CryptoSession::derive_hkdf(const SecureVector& shared_secret) {
    EVP_KDF *kdf = EVP_KDF_fetch(NULL, "HKDF", NULL);
    EVP_KDF_CTX *kctx = EVP_KDF_CTX_new(kdf);

    const char *info = "Cigarettes-session-key";
    OSSL_PARAM params[5];
    
    params[0] = OSSL_PARAM_construct_utf8_string(OSSL_KDF_PARAM_DIGEST, (char*)"SHA256", 0);
    params[1] = OSSL_PARAM_construct_octet_string(OSSL_KDF_PARAM_KEY, (void*)shared_secret.data(), shared_secret.size());
    params[2] = OSSL_PARAM_construct_octet_string(OSSL_KDF_PARAM_INFO, (void*)info, strlen(info));
    params[3] = OSSL_PARAM_construct_end();

    session_key.resize(32);
    if (EVP_KDF_derive(kctx, session_key.data(), session_key.size(), params) <= 0) {
        EVP_KDF_CTX_free(kctx);
        EVP_KDF_free(kdf);
        throw std::runtime_error("HKDF derivation failed");
    }



    EVP_KDF_CTX_free(kctx);
    EVP_KDF_free(kdf);
}

std::vector<uint8_t> CryptoSession::encrypt(const std::string& message) {
    EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
    std::vector<uint8_t> ciphertext;
    
    std::vector<uint8_t> nonce(12);
    RAND_bytes(nonce.data(), nonce.size());

    EVP_EncryptInit_ex(ctx, EVP_aes_256_gcm(), NULL, NULL, NULL);
    EVP_EncryptInit_ex(ctx, NULL, NULL, session_key.data(), nonce.data());

    ciphertext.resize(message.size());
    int len;
    EVP_EncryptUpdate(ctx, ciphertext.data(), &len, (unsigned char*)message.c_str(), message.size());
    
    EVP_EncryptFinal_ex(ctx, ciphertext.data() + len, &len);

    std::vector<uint8_t> tag(16);
    EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_GET_TAG, 16, tag.data());

    EVP_CIPHER_CTX_free(ctx);

    std::vector<uint8_t> final_payload;
    final_payload.insert(final_payload.end(), nonce.begin(), nonce.end());
    final_payload.insert(final_payload.end(), ciphertext.begin(), ciphertext.end());
    final_payload.insert(final_payload.end(), tag.begin(), tag.end());

    return final_payload;
}

std::string CryptoSession::decrypt(const std::vector<uint8_t>& encrypted_data) {
    if (encrypted_data.size() < 12 + 16) {
        throw std::runtime_error("Payload too short to be valid");
    }

    size_t nonce_len = 12;
    size_t tag_len = 16;
    size_t ciphertext_len = encrypted_data.size() - nonce_len - tag_len;

    const uint8_t* nonce = encrypted_data.data();
    const uint8_t* ciphertext = encrypted_data.data() + nonce_len;
    const uint8_t* tag = encrypted_data.data() + nonce_len + ciphertext_len;

    EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
    if (!ctx) throw std::runtime_error("Failed to create cipher context");

    EVP_DecryptInit_ex(ctx, EVP_aes_256_gcm(), NULL, NULL, NULL);
    
    EVP_DecryptInit_ex(ctx, NULL, NULL, session_key.data(), nonce);

    std::vector<uint8_t> plaintext(ciphertext_len);
    int len;
    if (EVP_DecryptUpdate(ctx, plaintext.data(), &len, ciphertext, ciphertext_len) <= 0) {
        EVP_CIPHER_CTX_free(ctx);
        throw std::runtime_error("Failed to update decryption");
    }

    EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_TAG, tag_len, (void*)tag);

    int ret = EVP_DecryptFinal_ex(ctx, plaintext.data() + len, &len);

    EVP_CIPHER_CTX_free(ctx);

    if (ret > 0) {
        return std::string(plaintext.begin(), plaintext.end());
    } else {
        throw std::runtime_error("Failed authentication: data corrupted or wrong key");
    }
}

std::vector<uint8_t> CryptoSession::encrypt_bytes(const std::vector<uint8_t>& data) {
    EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
    std::vector<uint8_t> ciphertext;
    
    std::vector<uint8_t> nonce(12);
    RAND_bytes(nonce.data(), nonce.size());

    EVP_EncryptInit_ex(ctx, EVP_aes_256_gcm(), NULL, NULL, NULL);
    EVP_EncryptInit_ex(ctx, NULL, NULL, session_key.data(), nonce.data());

    ciphertext.resize(data.size());
    int len;
    EVP_EncryptUpdate(ctx, ciphertext.data(), &len, (unsigned char*)data.data(), data.size());
    
    EVP_EncryptFinal_ex(ctx, ciphertext.data() + len, &len);

    std::vector<uint8_t> tag(16);
    EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_GET_TAG, 16, tag.data());

    EVP_CIPHER_CTX_free(ctx);

    std::vector<uint8_t> final_payload;
    final_payload.insert(final_payload.end(), nonce.begin(), nonce.end());
    final_payload.insert(final_payload.end(), ciphertext.begin(), ciphertext.end());
    final_payload.insert(final_payload.end(), tag.begin(), tag.end());

    return final_payload;
}

std::vector<uint8_t> CryptoSession::decrypt_bytes(const std::vector<uint8_t>& encrypted_data) {
    if (encrypted_data.size() < 12 + 16) {
        throw std::runtime_error("Payload too short to be valid");
    }

    size_t nonce_len = 12;
    size_t tag_len = 16;
    size_t ciphertext_len = encrypted_data.size() - nonce_len - tag_len;

    const uint8_t* nonce = encrypted_data.data();
    const uint8_t* ciphertext = encrypted_data.data() + nonce_len;
    const uint8_t* tag = encrypted_data.data() + nonce_len + ciphertext_len;

    EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
    if (!ctx) throw std::runtime_error("Failed to create cipher context");

    EVP_DecryptInit_ex(ctx, EVP_aes_256_gcm(), NULL, NULL, NULL);
    EVP_DecryptInit_ex(ctx, NULL, NULL, session_key.data(), nonce);

    std::vector<uint8_t> plaintext(ciphertext_len);
    int len;
    if (EVP_DecryptUpdate(ctx, plaintext.data(), &len, ciphertext, ciphertext_len) <= 0) {
        EVP_CIPHER_CTX_free(ctx);
        throw std::runtime_error("Failed to update decryption");
    }

    EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_TAG, tag_len, (void*)tag);

    int ret = EVP_DecryptFinal_ex(ctx, plaintext.data() + len, &len);

    EVP_CIPHER_CTX_free(ctx);

    if (ret > 0) {
        return plaintext;
    } else {
        throw std::runtime_error("Failed authentication: data corrupted or wrong key");
    }
}

bool CryptoSession::sessionEstablished() {
    return !session_key.empty();
}