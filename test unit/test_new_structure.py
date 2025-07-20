#!/usr/bin/env python3
"""
Script de test pour vérifier la nouvelle structure modulaire.
Ce script teste tous les composants de la nouvelle architecture.
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path


def print_test_header(test_name):
    """Afficher l'en-tête d'un test."""
    print(f"\n{'='*50}")
    print(f"🧪 TEST: {test_name}")
    print(f"{'='*50}")


def test_imports():
    """Tester les imports de la nouvelle structure."""
    print_test_header("Imports des modules")
    
    try:
        # Ajouter le dossier src au path
        src_path = os.path.join(os.path.dirname(__file__), 'src')
        sys.path.insert(0, src_path)
        
        # Test des imports principaux
        from src.core.crypto import CryptoManager
        from src.core.hosts import KnownHostsManager
        from src.network.connection import P2PConnection
        from src.network.tor_manager import TorManager
        from src.ui.console_ui import ConsoleUI
        
        print("✅ Tous les imports réussis")
        return True
        
    except Exception as e:
        print(f"❌ Erreur d'import: {str(e)}")
        return False


def test_crypto_manager():
    """Tester le gestionnaire cryptographique."""
    print_test_header("Gestionnaire cryptographique")
    
    try:
        from src.core.crypto import CryptoManager
        
        # Créer une instance
        crypto = CryptoManager()
        
        # Tester la génération de fingerprint
        fingerprint = crypto.get_public_key_fingerprint()
        print(f"✅ Fingerprint généré: {fingerprint[:16]}...")
        
        # Tester le chiffrement/déchiffrement
        test_message = "Test message"
        encrypted = crypto.encrypt_message(test_message)
        print(f"✅ Message chiffré: {len(encrypted)} bytes")
        
        # Note: Le déchiffrement nécessite une session établie
        print("✅ Tests crypto réussis")
        return True
        
    except Exception as e:
        print(f"❌ Erreur crypto: {str(e)}")
        return False


def test_hosts_manager():
    """Tester le gestionnaire d'hôtes."""
    print_test_header("Gestionnaire d'hôtes")
    
    try:
        from src.core.hosts import KnownHostsManager
        
        # Créer un fichier temporaire pour les tests
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_hosts_file = f.name
        
        # Créer une instance
        hosts = KnownHostsManager(temp_hosts_file)
        
        # Tester l'ajout d'un hôte
        test_address = "test.onion:34567"
        test_fingerprint = "a" * 64  # Fingerprint de test
        success = hosts.add_host(test_address, test_fingerprint)
        
        if success:
            print("✅ Ajout d'hôte réussi")
            
            # Tester la récupération
            retrieved = hosts.get_host_fingerprint(test_address)
            if retrieved == test_fingerprint:
                print("✅ Récupération d'hôte réussie")
            else:
                print("❌ Récupération d'hôte échouée")
                return False
        else:
            print("❌ Ajout d'hôte échoué")
            return False
        
        # Nettoyer
        os.unlink(temp_hosts_file)
        print("✅ Tests hosts réussis")
        return True
        
    except Exception as e:
        print(f"❌ Erreur hosts: {str(e)}")
        return False


def test_tor_manager():
    """Tester le gestionnaire Tor."""
    print_test_header("Gestionnaire Tor")
    
    try:
        from src.network.tor_manager import TorManager
        
        # Créer une instance
        tor_manager = TorManager()
        
        # Tester la détection d'OS
        os_name = tor_manager.detect_os()
        print(f"✅ OS détecté: {os_name}")
        
        # Tester la génération d'URL
        url = tor_manager.get_tor_url()
        print(f"✅ URL Tor générée: {url[:50]}...")
        
        # Tester la vérification de présence Tor
        is_present = tor_manager.is_tor_present()
        print(f"✅ Tor présent: {is_present}")
        
        print("✅ Tests Tor réussis")
        return True
        
    except Exception as e:
        print(f"❌ Erreur Tor: {str(e)}")
        return False


def test_console_ui():
    """Tester l'interface console."""
    print_test_header("Interface console")
    
    try:
        from src.ui.console_ui import ConsoleUI
        
        # Créer une instance
        ui = ConsoleUI()
        
        # Tester l'affichage d'aide
        ui.display_help()
        print("✅ Affichage d'aide réussi")
        
        # Tester la gestion des commandes
        test_command = "/help"
        ui._handle_command(test_command)
        print("✅ Gestion de commande réussie")
        
        print("✅ Tests UI réussis")
        return True
        
    except Exception as e:
        print(f"❌ Erreur UI: {str(e)}")
        return False


def test_connection_manager():
    """Tester le gestionnaire de connexion."""
    print_test_header("Gestionnaire de connexion")
    
    try:
        from src.network.connection import P2PConnection
        
        # Créer une instance avec un callback factice
        def dummy_callback(message):
            pass
        
        connection = P2PConnection(34567, dummy_callback)
        
        # Tester la validation d'IP
        valid_ip = connection._validate_ip_address("127.0.0.1")
        invalid_ip = connection._validate_ip_address("invalid.ip")
        
        if valid_ip and not invalid_ip:
            print("✅ Validation d'IP réussie")
        else:
            print("❌ Validation d'IP échouée")
            return False
        
        # Tester la détection d'IP privée
        is_private = connection._is_private_ip("192.168.1.1")
        is_public = connection._is_private_ip("8.8.8.8")
        
        if is_private and not is_public:
            print("✅ Détection d'IP privée réussie")
        else:
            print("❌ Détection d'IP privée échouée")
            return False
        
        print("✅ Tests connexion réussis")
        return True
        
    except Exception as e:
        print(f"❌ Erreur connexion: {str(e)}")
        return False


def test_main_module():
    """Tester le module principal."""
    print_test_header("Module principal")
    
    try:
        from src.main import print_banner, validate_port
        
        # Tester la validation de port
        valid_port = validate_port("34567")
        try:
            invalid_port = validate_port("99999")
            print("❌ Validation de port échouée (devrait échouer)")
            return False
        except ValueError:
            print("✅ Validation de port réussie")
        
        print("✅ Tests module principal réussis")
        return True
        
    except Exception as e:
        print(f"❌ Erreur module principal: {str(e)}")
        return False


def run_all_tests():
    """Exécuter tous les tests."""
    print("🚀 DÉMARRAGE DES TESTS DE LA NOUVELLE STRUCTURE")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Crypto Manager", test_crypto_manager),
        ("Hosts Manager", test_hosts_manager),
        ("Tor Manager", test_tor_manager),
        ("Console UI", test_console_ui),
        ("Connection Manager", test_connection_manager),
        ("Main Module", test_main_module),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSÉ")
            else:
                print(f"❌ {test_name}: ÉCHOUÉ")
        except Exception as e:
            print(f"❌ {test_name}: ERREUR - {str(e)}")
    
    print("\n" + "=" * 60)
    print(f"📊 RÉSULTATS: {passed}/{total} tests réussis")
    print("=" * 60)
    
    if passed == total:
        print("🎉 TOUS LES TESTS SONT PASSÉS!")
        print("✅ La nouvelle structure fonctionne correctement")
        return True
    else:
        print("⚠️  Certains tests ont échoué")
        print("🔧 Vérifiez les erreurs ci-dessus")
        return False


def main():
    """Fonction principale de test."""
    try:
        success = run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\n❌ Tests interrompus par l'utilisateur")
        return 1
    except Exception as e:
        print(f"\n\n❌ Erreur générale: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 