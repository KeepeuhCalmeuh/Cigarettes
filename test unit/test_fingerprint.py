#!/usr/bin/env python3
"""
Script de test spécifique pour vérifier l'affichage de la fingerprint.
"""

import sys
import os

# Ajouter le dossier src au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_fingerprint_display():
    """Test spécifique pour l'affichage de la fingerprint."""
    print("🧪 Test de l'affichage de la fingerprint")
    print("=" * 50)
    
    try:
        from src.core.crypto import CryptoManager
        from src.network.connection import P2PConnection
        
        # Créer une instance crypto
        crypto = CryptoManager()
        fingerprint = crypto.get_public_key_fingerprint()
        print(f"✅ Fingerprint générée: {fingerprint}")
        
        # Créer une instance de connexion avec un callback factice
        def dummy_callback(message):
            pass
        
        connection = P2PConnection(34567, dummy_callback)
        connection_fingerprint = connection.crypto.get_public_key_fingerprint()
        print(f"✅ Fingerprint de la connexion: {connection_fingerprint}")
        
        # Vérifier que les fingerprints sont identiques
        if fingerprint == connection_fingerprint:
            print("✅ Fingerprints identiques - OK")
        else:
            print("❌ Fingerprints différentes - ERREUR")
            return False
            
        print("\n✅ Test de fingerprint réussi!")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test: {str(e)}")
        return False

def test_info_command():
    """Test de la commande /info."""
    print("\n🧪 Test de la commande /info")
    print("=" * 50)
    
    try:
        from src.ui.console_ui import ConsoleUI
        
        # Créer une instance UI
        ui = ConsoleUI()
        
        # Simuler l'initialisation de la connexion
        def dummy_callback(message):
            pass
        
        from src.network.connection import P2PConnection
        ui.connection = P2PConnection(34567, dummy_callback)
        ui.connection.start_server()
        
        # Tester la commande /info
        print("Test de la commande /info:")
        ui._handle_info_command()
        
        print("\n✅ Test de la commande /info réussi!")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test /info: {str(e)}")
        return False

def main():
    """Fonction principale de test."""
    print("🚀 TEST SPÉCIFIQUE DE LA FINGERPRINT")
    print("=" * 60)
    
    success1 = test_fingerprint_display()
    success2 = test_info_command()
    
    if success1 and success2:
        print("\n🎉 TOUS LES TESTS DE FINGERPRINT SONT PASSÉS!")
        print("✅ La fingerprint devrait maintenant s'afficher correctement")
        return True
    else:
        print("\n⚠️  Certains tests de fingerprint ont échoué")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 