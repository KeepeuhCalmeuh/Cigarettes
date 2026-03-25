#include <gtest/gtest.h>
#include "libCryptoSession.hpp"
#include "libCrypto.hpp"
#include <filesystem>

// Helper pour nettoyer les clés générées par le test
void cleanup_keys() {
    if (std::filesystem::exists("keys/private_key.pem")) {
        std::filesystem::remove("keys/private_key.pem");
    }
}

class CryptoSessionTest : public ::testing::Test {
protected:
    void SetUp() override {
        std::filesystem::create_directories("keys");
    }
    void TearDown() override {
        cleanup_keys();
    }
};

TEST_F(CryptoSessionTest, FullExchangeBetweenAliceAndBob) {
    // 1. On simule Alice
    CryptoManager alice_mgr(""); // Génère une clé secp384r1
    auto alice_pub = alice_mgr.get_public_bytes();
    auto alice_priv = alice_mgr.get_private_key();

    // 2. On simule Bob (On renomme le fichier pour ne pas écraser celui d'Alice)
    // Dans un vrai test, on pourrait mocker la lecture fichier, 
    // ici on va juste tricher un peu pour avoir deux paires de clés.
    std::filesystem::rename("keys/private_key.pem", "keys/alice_key.pem");
    
    CryptoManager bob_mgr("");
    auto bob_pub = bob_mgr.get_public_bytes();
    auto bob_priv = bob_mgr.get_private_key();

    // 3. Initialisation de la session sécurisée
    // Alice utilise sa clé privée et la clé publique de Bob
    ASSERT_NO_THROW({
        CryptoSession session_alice(alice_priv, bob_pub);
        CryptoSession session_bob(bob_priv, alice_pub);

        // 4. Test de chiffrement / Déchiffrement
        std::string original = "Message secret entre Alice et Bob";
        auto encrypted = session_alice.encrypt(original);
        std::string decrypted = session_bob.decrypt(encrypted);

        EXPECT_EQ(original, decrypted);
    });
}

TEST_F(CryptoSessionTest, TamperedDataDetection) {
    CryptoManager alice_mgr("");
    CryptoManager bob_mgr("");
    
    CryptoSession session_alice(alice_mgr.get_private_key(), bob_mgr.get_public_bytes());
    
    auto encrypted = session_alice.encrypt("Données intègres");
    
    // Corrompre le tag (les 16 derniers octets)
    encrypted.back() ^= 0xFF;

    EXPECT_THROW({
        session_alice.decrypt(encrypted);
    }, std::runtime_error);
}