#include "libCrypto.hpp"
#include <filesystem>

CryptoManager::CryptoManager(const SecureString& passphrase) {
    load_keys(passphrase);
    derive_public_key();
    compute_fingerprint();
}

CryptoManager::~CryptoManager() {
    if (pkey) {
        EVP_PKEY_free(pkey);
        pkey = nullptr;
    }
}

void CryptoManager::load_keys(const SecureString& passphrase) {
    bool file_exists = false;
    {
        FILE* test_fp = fopen("keys/private_key.pem", "rb");
        if (test_fp) {
            file_exists = true;
            fclose(test_fp);
        }
    }

    if (!file_exists) {
        std::cout << "Private key not found, generating new keys...\n";
        generate_keys(passphrase);
        return;
    }

    bool is_encrypted = is_key_file_encrypted();

    if (is_encrypted && passphrase.empty()) {
        throw std::runtime_error("This private key is encrypted. A passphrase is required to unlock it.");
    }

    if (!is_encrypted && !passphrase.empty()) {
        std::cout << "[Warning] Passphrase provided, but the private key on disk is NOT encrypted. Your identity is vulnerable.\n";
    }

    FILE* fp = fopen("keys/private_key.pem", "rb");
    pkey = PEM_read_PrivateKey(
        fp,
        nullptr,
        nullptr,
        passphrase.empty() ? nullptr : (void*)passphrase.c_str()
    );

    fclose(fp);

    if (!pkey)
        throw std::runtime_error("Failed to load private key (wrong passphrase or corrupted file?)");
}

bool CryptoManager::is_key_file_encrypted() {
    std::ifstream file("keys/private_key.pem");
    if (!file.is_open()) return false;

    std::string line;
    // Check first few lines for "ENCRYPTED"
    for (int i = 0; i < 5 && std::getline(file, line); ++i) {
        if (line.find("ENCRYPTED") != std::string::npos) {
            return true;
        }
    }
    return false;
}

void CryptoManager::generate_keys(const SecureString& passphrase) {
    EVP_PKEY_CTX* pctx = EVP_PKEY_CTX_new_id(EVP_PKEY_EC, nullptr);
    if (!pctx) throw std::runtime_error("EVP_PKEY_CTX_new_id failed");

    if (EVP_PKEY_keygen_init(pctx) <= 0)
        throw std::runtime_error("keygen_init failed");

    if (EVP_PKEY_CTX_set_ec_paramgen_curve_nid(pctx, NID_secp384r1) <= 0)
        throw std::runtime_error("set curve failed");

    if (EVP_PKEY_keygen(pctx, &pkey) <= 0)
        throw std::runtime_error("keygen failed");

    EVP_PKEY_CTX_free(pctx);

    std::filesystem::create_directories("keys");
    FILE* fp = fopen("keys/private_key.pem", "wb");
    if (!fp) throw std::runtime_error("cannot open key file");

    const EVP_CIPHER* cipher =
        passphrase.empty() ? nullptr : EVP_aes_256_cbc();

    if (!PEM_write_PrivateKey(
            fp,
            pkey,
            cipher,
            nullptr,
            0,
            nullptr,
            passphrase.empty() ? nullptr : (void*)passphrase.c_str()))
        throw std::runtime_error("PEM_write_PrivateKey failed");

    fclose(fp);
}

void CryptoManager::derive_public_key() {
    if (!pkey)
        throw std::runtime_error("Private key not loaded");

    size_t len = 0;

    if (EVP_PKEY_get_octet_string_param(
            pkey,
            OSSL_PKEY_PARAM_PUB_KEY,
            nullptr,
            0,
            &len) <= 0)
        throw std::runtime_error("Cannot get public key length");

    publicKey.resize(len);

    if (EVP_PKEY_get_octet_string_param(
            pkey,
            OSSL_PKEY_PARAM_PUB_KEY,
            publicKey.data(),
            publicKey.size(),
            &len) <= 0)
        throw std::runtime_error("Cannot extract public key");
}

void CryptoManager::compute_fingerprint() {
    EVP_MD_CTX* ctx = EVP_MD_CTX_new();
    if (!ctx) throw std::runtime_error("MD_CTX_new failed");

    unsigned int len = 0;

    if (EVP_DigestInit_ex(ctx, EVP_sha256(), nullptr) <= 0)
        throw std::runtime_error("DigestInit failed");

    if (EVP_DigestUpdate(ctx, publicKey.data(), publicKey.size()) <= 0)
        throw std::runtime_error("DigestUpdate failed");

    if (EVP_DigestFinal_ex(ctx, fingerprint.data(), &len) <= 0)
        throw std::runtime_error("DigestFinal failed");

    EVP_MD_CTX_free(ctx);
}

std::vector<uint8_t> CryptoManager::sign_data(const std::vector<uint8_t>& data) {
    EVP_MD_CTX* ctx = EVP_MD_CTX_new();
    if (!ctx) throw std::runtime_error("MD_CTX_new failed");

    if (EVP_DigestSignInit(ctx, nullptr, EVP_sha256(), nullptr, pkey) <= 0) {
        EVP_MD_CTX_free(ctx);
        throw std::runtime_error("DigestSignInit failed");
    }

    if (EVP_DigestSignUpdate(ctx, data.data(), data.size()) <= 0) {
        EVP_MD_CTX_free(ctx);
        throw std::runtime_error("DigestSignUpdate failed");
    }

    size_t siglen = 0;
    if (EVP_DigestSignFinal(ctx, nullptr, &siglen) <= 0) {
        EVP_MD_CTX_free(ctx);
        throw std::runtime_error("DigestSignFinal (get length) failed");
    }

    std::vector<uint8_t> signature(siglen);
    if (EVP_DigestSignFinal(ctx, signature.data(), &siglen) <= 0) {
        EVP_MD_CTX_free(ctx);
        throw std::runtime_error("DigestSignFinal failed");
    }
    signature.resize(siglen);

    EVP_MD_CTX_free(ctx);
    return signature;
}

bool CryptoManager::verify_signature(const std::vector<uint8_t>& data, const std::vector<uint8_t>& signature, const std::vector<uint8_t>& peer_public_key) {
    EVP_PKEY_CTX *pctx = EVP_PKEY_CTX_new_id(EVP_PKEY_EC, nullptr);
    if (!pctx) return false;

    if (EVP_PKEY_fromdata_init(pctx) <= 0) {
        EVP_PKEY_CTX_free(pctx);
        return false;
    }

    OSSL_PARAM params[3];
    params[0] = OSSL_PARAM_construct_utf8_string("group", (char*)"secp384r1", 0);
    params[1] = OSSL_PARAM_construct_octet_string("pub", (void*)peer_public_key.data(), peer_public_key.size());
    params[2] = OSSL_PARAM_construct_end();

    EVP_PKEY *peer_key = nullptr;
    if (EVP_PKEY_fromdata(pctx, &peer_key, EVP_PKEY_PUBLIC_KEY, params) <= 0) {
        EVP_PKEY_CTX_free(pctx);
        return false;
    }
    EVP_PKEY_CTX_free(pctx);

    EVP_MD_CTX* ctx = EVP_MD_CTX_new();
    if (!ctx) {
        EVP_PKEY_free(peer_key);
        return false;
    }

    if (EVP_DigestVerifyInit(ctx, nullptr, EVP_sha256(), nullptr, peer_key) <= 0) {
        EVP_MD_CTX_free(ctx);
        EVP_PKEY_free(peer_key);
        return false;
    }

    if (EVP_DigestVerifyUpdate(ctx, data.data(), data.size()) <= 0) {
        EVP_MD_CTX_free(ctx);
        EVP_PKEY_free(peer_key);
        return false;
    }

    int ret = EVP_DigestVerifyFinal(ctx, signature.data(), signature.size());
    
    EVP_MD_CTX_free(ctx);
    EVP_PKEY_free(peer_key);

    return ret == 1;
}

std::string CryptoManager::get_fingerprint() const {
    std::string fp_str;
    fp_str.reserve(fingerprint.size() * 2);
    for (uint8_t byte : fingerprint) {
        char buf[3];
        sprintf(buf, "%02x", byte);
        fp_str += buf;
    }
    return fp_str;
}

void CryptoManager::reset_key(const SecureString& passphrase) {
    // Generate new keys
    EVP_PKEY* new_pkey = nullptr;
    EVP_PKEY_CTX* pctx = EVP_PKEY_CTX_new_id(EVP_PKEY_EC, nullptr);
    if (!pctx) throw std::runtime_error("EVP_PKEY_CTX_new_id failed");

    if (EVP_PKEY_keygen_init(pctx) <= 0) {
        EVP_PKEY_CTX_free(pctx);
        throw std::runtime_error("keygen_init failed");
    }

    if (EVP_PKEY_CTX_set_ec_paramgen_curve_nid(pctx, NID_secp384r1) <= 0) {
        EVP_PKEY_CTX_free(pctx);
        throw std::runtime_error("set curve failed");
    }

    if (EVP_PKEY_keygen(pctx, &new_pkey) <= 0) {
        EVP_PKEY_CTX_free(pctx);
        throw std::runtime_error("keygen failed");
    }
    EVP_PKEY_CTX_free(pctx);

    // Save to file
    std::filesystem::create_directories("keys");
    FILE* fp = fopen("keys/private_key.pem", "wb");
    if (!fp) {
        EVP_PKEY_free(new_pkey);
        throw std::runtime_error("cannot open key file for writing");
    }

    const EVP_CIPHER* cipher = passphrase.empty() ? nullptr : EVP_aes_256_cbc();

    if (!PEM_write_PrivateKey(
            fp,
            new_pkey,
            cipher,
            nullptr,
            0,
            nullptr,
            passphrase.empty() ? nullptr : (void*)passphrase.c_str())) {
        fclose(fp);
        EVP_PKEY_free(new_pkey);
        throw std::runtime_error("PEM_write_PrivateKey failed during reset");
    }

    fclose(fp);

    // Update internal state
    if (pkey) EVP_PKEY_free(pkey);
    pkey = new_pkey;
    derive_public_key();
    compute_fingerprint();
}

std::string CryptoManager::calculate_fingerprint(const std::vector<uint8_t>& public_key) {
    EVP_MD_CTX* ctx = EVP_MD_CTX_new();
    if (!ctx) return "";

    std::array<unsigned char, 32> hash{};
    unsigned int len = 0;

    if (EVP_DigestInit_ex(ctx, EVP_sha256(), nullptr) <= 0 ||
        EVP_DigestUpdate(ctx, public_key.data(), public_key.size()) <= 0 ||
        EVP_DigestFinal_ex(ctx, hash.data(), &len) <= 0) {
        EVP_MD_CTX_free(ctx);
        return "";
    }

    EVP_MD_CTX_free(ctx);

    std::string fp_str;
    fp_str.reserve(32 * 2);
    for (uint8_t byte : hash) {
        char buf[3];
        sprintf(buf, "%02x", byte);
        fp_str += buf;
    }
    return fp_str;
}