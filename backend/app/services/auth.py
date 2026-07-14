"""
backend/app/services/auth.py — Validation et décodage sécurisé des tokens Clerk SSO (JWT RS256)
"""
import os
import time
import jwt
import requests
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Sécurité Bearer Token
security = HTTPBearer()

# Variables d'environnement Clerk (avec fallbacks pour le local)
CLERK_API_URL = os.getenv("CLERK_API_URL", "https://api.clerk.dev/v1")
CLERK_JWKS_URL = os.getenv(
    "CLERK_JWKS_URL", 
    "https://clerk.yourdomain.com/.well-known/jwks.json" # Remplacé par l'URL Clerk réelle du tenant
)

# Cache en mémoire des clés publiques JWK pour éviter d'appeler l'API à chaque requête
_jwks_cache = None
_jwks_cache_expiry = 0
CACHE_DURATION_SECONDS = 86400  # 24h

def _get_jwks():
    """Récupère les clés publiques JWKS de Clerk avec cache."""
    global _jwks_cache, _jwks_cache_expiry
    now = time.time()
    if _jwks_cache is None or now > _jwks_cache_expiry:
        try:
            resp = requests.get(CLERK_JWKS_URL, timeout=10)
            resp.raise_for_status()
            _jwks_cache = resp.json()
            _jwks_cache_expiry = now + CACHE_DURATION_SECONDS
        except Exception as e:
            # Fallback en mode développement local : clé factice si non configuré
            if os.getenv("ENV") != "production":
                return {"keys": []}
            raise HTTPException(
                status_code=500,
                detail=f"Erreur de récupération des clés de sécurité SSO Clerk: {str(e)}"
            )
    return _jwks_cache

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """
    Décode, vérifie la signature RS256 et valide le token JWT SSO fourni par Clerk.
    Retourne le payload décodé contenant l'identité de l'utilisateur et du tenant.
    """
    token = credentials.credentials
    try:
        # Extraire le header pour trouver le kid (Key ID)
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if not kid:
            raise jwt.InvalidTokenError("kid manquant dans l'en-tête du token")

        # Trouver la clé publique correspondante dans le JWKS
        jwks = _get_jwks()
        public_key = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                break

        # Si pas de clé trouvée en mode dev, on peut bypasser si configuration locale explicite
        if not public_key:
            if os.getenv("ENV") != "production":
                # Mock token en local pour faciliter le vibe coding
                return {
                    "sub": "user_local_mock",
                    "org_id": "tenant_local_mock",
                    "email": "contact@mock-tenant.com",
                    "role": "admin"
                }
            raise jwt.InvalidTokenError("Clé de signature JWK correspondante introuvable")

        # Décoder et valider le token
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            options={"verify_aud": False} # Permet de s'intégrer de manière générique
        )
        
        # Validation complémentaire de l'organisation (Tenant)
        # Clerk stocke l'organisation active dans org_id
        if not payload.get("org_id") and not payload.get("org"):
            raise jwt.InvalidTokenError("Aucun Tenant associé à la session de l'utilisateur")

        return {
            "user_id": payload.get("sub"),
            "tenant_id": payload.get("org_id") or payload.get("org"),
            "email": payload.get("email"),
            "role": payload.get("role", "diagnostiqueur")
        }

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="La session a expiré, veuillez vous reconnecter")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Session invalide : {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Erreur d'authentification SSO")
