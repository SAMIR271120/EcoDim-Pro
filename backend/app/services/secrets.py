"""
backend/app/services/secrets.py — Gestionnaire de secrets et configuration pour le backend EcoDim Pro
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Charger le fichier .env si présent
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

class SecretsManager:
    """Gestionnaire centralisé pour la sécurité des clés d'API et variables d'environnement."""
    
    @staticmethod
    def get_database_url() -> str:
        """Récupère l'URL de connexion PostgreSQL."""
        url = os.getenv("DATABASE_URL")
        if not url:
            # Fallback local de développement
            return "postgresql://postgres:postgres@localhost:5432/ecodimpro"
        return url

    @staticmethod
    def get_redis_url() -> str:
        """Récupère l'URL du cache Redis."""
        return os.getenv("REDIS_URL", "redis://localhost:6379/0")

    @staticmethod
    def get_stripe_api_key() -> str:
        """Récupère la clé secrète Stripe."""
        key = os.getenv("STRIPE_SECRET_KEY")
        if not key and os.getenv("ENV") == "production":
            raise ValueError("STRIPE_SECRET_KEY manquant en production")
        return key or "sk_test_mock"

    @staticmethod
    def get_clerk_pem_key() -> str:
        """Récupère la clé de chiffrement PEM de Clerk."""
        key = os.getenv("CLERK_PEM_KEY")
        if not key and os.getenv("ENV") == "production":
            raise ValueError("CLERK_PEM_KEY manquant en production")
        return key or ""
        
    @staticmethod
    def verify_env_integrity():
        """Vérifie l'intégrité de la configuration en production."""
        if os.getenv("ENV") == "production":
            required = ["DATABASE_URL", "CLERK_JWKS_URL", "STRIPE_SECRET_KEY"]
            missing = [r for r in required if not os.getenv(r)]
            if missing:
                raise RuntimeError(f"Configuration critique manquante en production : {', '.join(missing)}")
