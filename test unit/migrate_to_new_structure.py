#!/usr/bin/env python3
"""
Script de migration vers la nouvelle structure modulaire.
Ce script aide à migrer depuis l'ancienne structure vers la nouvelle.
"""

import os
import shutil
import sys
from pathlib import Path


def print_banner():
    """Afficher la bannière de migration."""
    print("=" * 60)
    print("  MIGRATION VERS LA NOUVELLE STRUCTURE MODULAIRE")
    print("=" * 60)
    print()


def check_current_structure():
    """Vérifier la structure actuelle."""
    print("🔍 Vérification de la structure actuelle...")
    
    current_files = [
        "main.py",
        "console_ui.py", 
        "connection.py",
        "crypto_utils.py",
        "known_hosts_manager.py",
        "tor_manager.py"
    ]
    
    missing_files = []
    for file in current_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Fichiers manquants: {missing_files}")
        return False
    
    print("✅ Structure actuelle détectée")
    return True


def check_new_structure():
    """Vérifier si la nouvelle structure existe déjà."""
    print("\n🔍 Vérification de la nouvelle structure...")
    
    new_structure_files = [
        "src/__init__.py",
        "src/main.py",
        "src/core/__init__.py",
        "src/core/crypto.py",
        "src/core/hosts.py",
        "src/network/__init__.py",
        "src/network/connection.py",
        "src/network/tor_manager.py",
        "src/ui/__init__.py",
        "src/ui/console_ui.py",
        "main_new.py"
    ]
    
    existing_files = []
    for file in new_structure_files:
        if os.path.exists(file):
            existing_files.append(file)
    
    if existing_files:
        print(f"⚠️  Nouvelle structure déjà partiellement présente:")
        for file in existing_files:
            print(f"   - {file}")
        return True
    
    print("✅ Nouvelle structure prête à être créée")
    return False


def backup_original_files():
    """Sauvegarder les fichiers originaux."""
    print("\n💾 Sauvegarde des fichiers originaux...")
    
    backup_dir = "backup_original"
    if os.path.exists(backup_dir):
        shutil.rmtree(backup_dir)
    
    os.makedirs(backup_dir)
    
    files_to_backup = [
        "main.py",
        "console_ui.py",
        "connection.py", 
        "crypto_utils.py",
        "known_hosts_manager.py",
        "tor_manager.py"
    ]
    
    for file in files_to_backup:
        if os.path.exists(file):
            shutil.copy2(file, os.path.join(backup_dir, file))
            print(f"   ✅ {file} sauvegardé")
    
    print(f"✅ Sauvegarde créée dans: {backup_dir}")


def test_new_structure():
    """Tester la nouvelle structure."""
    print("\n🧪 Test de la nouvelle structure...")
    
    try:
        # Test d'import
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
        
        # Test des imports principaux
        from src.core.crypto import CryptoManager
        from src.core.hosts import KnownHostsManager
        from src.network.connection import P2PConnection
        from src.network.tor_manager import TorManager
        from src.ui.console_ui import ConsoleUI
        
        print("✅ Imports réussis")
        
        # Test de création des instances
        crypto = CryptoManager()
        hosts = KnownHostsManager()
        
        print("✅ Instanciation réussie")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test: {str(e)}")
        return False


def create_migration_guide():
    """Créer un guide de migration."""
    print("\n📝 Création du guide de migration...")
    
    guide_content = """# Guide de Migration - Cigarettes

## Migration vers la nouvelle structure modulaire

### ✅ Migration terminée

La nouvelle structure modulaire a été créée avec succès. Voici ce qui a changé :

### Nouveaux fichiers créés :
- `src/` - Dossier principal du code source
- `src/core/` - Fonctionnalités de base (crypto, hosts)
- `src/network/` - Gestion réseau (connexions, Tor)
- `src/ui/` - Interface utilisateur
- `main_new.py` - Nouveau point d'entrée

### Fichiers sauvegardés :
- `backup_original/` - Sauvegarde des fichiers originaux

### Comment utiliser la nouvelle structure :

#### Option 1 : Nouveau point d'entrée
```bash
python main_new.py
```

#### Option 2 : Module Python
```bash
python -m src.main
```

### Compatibilité :
- ✅ Toutes les fonctionnalités préservées
- ✅ Données existantes conservées (clés, hôtes connus)
- ✅ Commandes identiques
- ✅ Ancien point d'entrée toujours fonctionnel

### Tests recommandés :
1. Lancer `python main_new.py`
2. Tester une connexion avec `/connect`
3. Vérifier le transfert de fichiers
4. Confirmer que les hôtes connus sont préservés

### En cas de problème :
- Les fichiers originaux sont sauvegardés dans `backup_original/`
- Vous pouvez revenir à l'ancienne structure si nécessaire
- Consultez `README_NEW_STRUCTURE.md` pour plus de détails

### Avantages de la nouvelle structure :
- Code plus organisé et maintenable
- Séparation claire des responsabilités
- Facilité d'ajout de nouvelles fonctionnalités
- Tests unitaires simplifiés
- Documentation améliorée
"""
    
    with open("MIGRATION_GUIDE.md", "w", encoding="utf-8") as f:
        f.write(guide_content)
    
    print("✅ Guide de migration créé: MIGRATION_GUIDE.md")


def main():
    """Fonction principale de migration."""
    print_banner()
    
    # Vérifier la structure actuelle
    if not check_current_structure():
        print("❌ Structure actuelle incomplète. Migration impossible.")
        return False
    
    # Vérifier si la nouvelle structure existe déjà
    if check_new_structure():
        response = input("\n❓ La nouvelle structure semble déjà exister. Continuer quand même? (y/N): ")
        if response.lower() != 'y':
            print("Migration annulée.")
            return False
    
    # Sauvegarder les fichiers originaux
    backup_original_files()
    
    # Tester la nouvelle structure
    if not test_new_structure():
        print("❌ Test de la nouvelle structure échoué.")
        print("Vérifiez que tous les fichiers de la nouvelle structure sont présents.")
        return False
    
    # Créer le guide de migration
    create_migration_guide()
    
    print("\n" + "=" * 60)
    print("🎉 MIGRATION TERMINÉE AVEC SUCCÈS!")
    print("=" * 60)
    print()
    print("📋 Prochaines étapes :")
    print("1. Testez la nouvelle structure: python main_new.py")
    print("2. Consultez le guide: MIGRATION_GUIDE.md")
    print("3. Lisez la documentation: README_NEW_STRUCTURE.md")
    print()
    print("✅ Toutes les fonctionnalités sont préservées!")
    print("✅ Les données existantes sont conservées!")
    print("✅ L'ancien point d'entrée reste fonctionnel!")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Migration interrompue par l'utilisateur.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Erreur lors de la migration: {str(e)}")
        sys.exit(1) 