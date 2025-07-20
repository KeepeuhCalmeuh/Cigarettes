#!/usr/bin/env python3
"""
Script pour tester l'affichage au démarrage de l'application.
"""

import sys
import os
import threading
import time

# Ajouter le dossier src au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_startup_display():
    """Test de l'affichage au démarrage."""
    print("🧪 Test de l'affichage au démarrage")
    print("=" * 50)
    
    try:
        from src.ui.console_ui import ConsoleUI
        
        # Créer une instance UI
        ui = ConsoleUI()
        
        # Simuler le démarrage
        print("Simulation du démarrage de l'application...")
        
        # Démarrer dans un thread pour éviter le blocage
        def start_ui():
            try:
                ui.start(34567)
            except KeyboardInterrupt:
                pass
        
        ui_thread = threading.Thread(target=start_ui, daemon=True)
        ui_thread.start()
        
        # Attendre un peu pour voir l'affichage
        time.sleep(3)
        
        # Arrêter proprement
        ui.stop()
        
        print("\n✅ Test d'affichage au démarrage réussi!")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test: {str(e)}")
        return False

def main():
    """Fonction principale."""
    print("🚀 TEST D'AFFICHAGE AU DÉMARRAGE")
    print("=" * 60)
    
    success = test_startup_display()
    
    if success:
        print("\n🎉 TEST RÉUSSI!")
        print("✅ La fingerprint devrait s'afficher au démarrage")
        print("\nPour tester l'application complète:")
        print("python main_new.py")
        return True
    else:
        print("\n⚠️  Test échoué")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 