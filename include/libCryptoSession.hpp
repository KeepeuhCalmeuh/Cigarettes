#ifndef LIBCRYPTOSESSION_HPP
#define LIBCRYPTOSESSION_HPP

#include <openssl/evp.h>
#include <vector>
#include <cstdint>
#include <string>

class CryptoSession {
public:
    CryptoSession(EVP_PKEY* personal_private_key, const std::vector<uint8_t>& peer_pub_key_bytes);
    ~CryptoSession();

    // prohibit copying
    CryptoSession(const CryptoSession&) = delete;
    CryptoSession& operator=(const CryptoSession&) = delete;

    std::vector<uint8_t> encrypt(const std::string& message);
    std::string decrypt(const std::vector<uint8_t>& encrypted_data);

    std::vector<uint8_t> encrypt_bytes(const std::vector<uint8_t>& data);
    std::vector<uint8_t> decrypt_bytes(const std::vector<uint8_t>& encrypted_data);

    bool sessionEstablished();
private:
    void compute_ecdh();
    void derive_hkdf(const std::vector<uint8_t>& shared_secret);
    
    EVP_PKEY* my_private_key = nullptr;
    EVP_PKEY* peer_public_key = nullptr;
    
    std::vector<uint8_t> session_key; // final session key derived from ECDH + HKDF for AES-256-GCM
};

#endif