#ifndef LIBCRYPTO_HPP
#define LIBCRYPTO_HPP

#include <stdio.h>
#include <iostream>
#include <fstream>
#include <vector>
#include <array>
#include <stdexcept>

#include <openssl/evp.h>
#include <openssl/pem.h>
#include <openssl/ec.h>
#include <openssl/sha.h>
#include <openssl/core_names.h>

#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#define EXPORT
#endif

class CryptoManager {
public:
    CryptoManager(std::string passphrase);
    ~CryptoManager();

    EVP_PKEY* get_private_key() const { return pkey; }
    std::vector<uint8_t> get_public_bytes() const { return publicKey; }

    std::vector<uint8_t> sign_data(const std::vector<uint8_t>& data);
    bool verify_signature(const std::vector<uint8_t>& data, const std::vector<uint8_t>& signature, const std::vector<uint8_t>& peer_public_key);
    std::string get_fingerprint() const;
    static std::string calculate_fingerprint(const std::vector<uint8_t>& public_key);
    void reset_key(std::string passphrase);
private:
    void generate_keys(std::string passphrase);
    void load_keys(std::string passphrase);
    bool is_key_file_encrypted();
    void derive_public_key();
    void compute_fingerprint();

    EVP_PKEY* pkey = nullptr; // internal OpenSSL key structure

    std::vector<unsigned char> publicKey;
    std::array<unsigned char, 32> fingerprint{};
};

#endif // LIBCRYPTO_HPP