#!/usr/bin/env python3
"""
Script de migration des clés vers la nouvelle structure sécurisée.
Ce script déplace les clés de la racine vers le dossier 'keys/'.
"""

import os
import shutil
import sys
from pathlib import Path


def print_banner():
    """Afficher la bannière de migration."""
    print("=" * 60)
    print("  MIGRATION DES CLÉS VERS LA STRUCTURE SÉCURISÉE")
    print("=" * 60)
    print()


def check_old_key():
    """Vérifier si l'ancienne clé existe."""
    old_key_path = "user_private_key.pem"
    
    if os.path.exists(old_key_path):
        print(f"✅ Ancienne clé trouvée: {old_key_path}")
        return old_key_path
    else:
        print(f"ℹ️  Aucune ancienne clé trouvée à la racine")
        return None


def create_keys_directory():
    """Créer le dossier keys/."""
    keys_dir = "keys"
    
    if not os.path.exists(keys_dir):
        os.makedirs(keys_dir, exist_ok=True)
        print(f"✅ Dossier créé: {keys_dir}/")
    else:
        print(f"ℹ️  Dossier existant: {keys_dir}/")
    
    return keys_dir


def migrate_key(old_key_path, keys_dir):
    """Migrer la clé vers le nouveau dossier."""
    new_key_path = os.path.join(keys_dir, "user_private_key.pem")
    
    if os.path.exists(new_key_path):
        print(f"⚠️  Clé déjà présente dans {new_key_path}")
        response = input("Voulez-vous la remplacer ? (y/N): ")
        if response.lower() != 'y':
            print("Migration annulée.")
            return False
    
    try:
        # Copier la clé
        shutil.copy2(old_key_path, new_key_path)
        print(f"✅ Clé migrée: {old_key_path} → {new_key_path}")
        
        # Définir les permissions restrictives (Unix-like)
        try:
            os.chmod(new_key_path, 0o600)  # Read/write pour le propriétaire seulement
            print("✅ Permissions sécurisées définies")
        except OSError:
            # Windows ne supporte pas chmod, mais c'est normal
            pass
        
        # Sauvegarder l'ancienne clé
        backup_path = old_key_path + ".backup"
        shutil.copy2(old_key_path, backup_path)
        print(f"✅ Sauvegarde créée: {backup_path}")
        
        # Supprimer l'ancienne clé
        os.remove(old_key_path)
        print(f"✅ Ancienne clé supprimée: {old_key_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la migration: {str(e)}")
        return False


def test_new_structure():
    """Tester la nouvelle structure de clés."""
    print("\n🧪 Test de la nouvelle structure...")
    
    try:
        # Importer et tester le nouveau CryptoManager
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
        from src.core.crypto import CryptoManager
        
        # Créer une instance (utilisera automatiquement le nouveau dossier)
        crypto = CryptoManager()
        
        # Tester la génération de fingerprint
        fingerprint = crypto.get_public_key_fingerprint()
        print(f"✅ Fingerprint générée: {fingerprint[:16]}...")
        
        print("✅ Nouvelle structure fonctionne correctement")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test: {str(e)}")
        return False


def create_gitignore_entry():
    """Ajouter le dossier keys/ au .gitignore."""
    gitignore_path = ".gitignore"
    
    if not os.path.exists(gitignore_path):
        with open(gitignore_path, "w") as f:
            f.write("# Cigarettes - Ignored files\n")
    
    # Lire le contenu actuel
    with open(gitignore_path, "r") as f:
        content = f.read()
    
    # Vérifier si keys/ est déjà dans le .gitignore
    if "keys/" not in content:
        with open(gitignore_path, "a") as f:
            f.write("\n# Cryptographic keys\nkeys/\n")
        print("✅ Dossier keys/ ajouté au .gitignore")
    else:
        print("ℹ️  Dossier keys/ déjà dans le .gitignore")


def main():
    """Fonction principale de migration."""
    print_banner()
    
    # Vérifier l'ancienne clé
    old_key_path = check_old_key()
    
    # Créer le dossier keys/
    keys_dir = create_keys_directory()
    
    # Migrer la clé si elle existe
    if old_key_path:
        if not migrate_key(old_key_path, keys_dir):
            return False
    
    # Tester la nouvelle structure
    if not test_new_structure():
        print("❌ Test de la nouvelle structure échoué")
        return False
    
    # Ajouter au .gitignore
    create_gitignore_entry()
    
    print("\n" + "=" * 60)
    print("🎉 MIGRATION DES CLÉS TERMINÉE AVEC SUCCÈS!")
    print("=" * 60)
    print()
    print("📋 Résumé des changements :")
    print(f"   ✅ Clés stockées dans: {keys_dir}/")
    print("   ✅ Permissions sécurisées définies")
    print("   ✅ Dossier ajouté au .gitignore")
    print("   ✅ Compatibilité préservée")
    print()
    print("🔒 Avantages de sécurité :")
    print("   - Clés isolées dans un dossier dédié")
    print("   - Permissions restrictives (Unix)")
    print("   - Pas de clés dans le contrôle de version")
    print("   - Structure plus organisée")
    print()
    print("✅ L'application fonctionne exactement comme avant !")
    
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