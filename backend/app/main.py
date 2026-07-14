"""
backend/app/main.py — Serveur d'API REST EcoDim Pro B2B SaaS
"""
import sys
import os
from pathlib import Path

# Ajouter le root path pour importer les modules ecodimpro
root_path = str(Path(__file__).resolve().parent.parent.parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from backend.app.services.auth import verify_token
from ecodimpro.cablage import estimer_section_cable, estimer_metrage_cablage
from ecodimpro.bilan import calc_autoconsommation
# Les autres imports de calculs d'ingénierie d'EcoDim Pro
# (pv, thermique, etc. seront importés au besoin)

app = FastAPI(
    title="EcoDim Pro API Engine",
    description="API de calcul photovoltaïque et thermique multi-tenant",
    version="1.0.0"
)

# Configuration CORS pour permettre aux clients d'intégrer l'API (Next.js, Streamlit, Whitelabel)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # En production, restreindre aux domaines autorisés
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- SCHÉMAS DE DONNÉES PYDANTIC ---

class CablageInput(BaseModel):
    courant_a: float = Field(..., description="Courant maximal DC", example=12.5)
    longueur_m: float = Field(..., description="Longueur simple du câble", example=15.0)
    chute_tension_max_pct: float = Field(3.0, description="Chute de tension maximale admise", example=3.0)
    tension_v: float = Field(400.0, description="Tension de service du circuit", example=400.0)

class BilanInput(BaseModel):
    production_kwh: List[float] = Field(..., description="Série ou mensuels de production", example=[100, 150, 200])
    consommation_kwh: List[float] = Field(..., description="Série ou mensuels de consommation", example=[120, 140, 180])

class ProjectInput(BaseModel):
    nom_projet: str
    client_prenom: str
    client_nom: str
    client_email: Optional[str] = None
    adresse: Optional[str] = None
    donnees_calcul: Dict[str, Any]

# --- ENDPOINTS ---

@app.get("/")
def read_root():
    return {"status": "running", "engine": "EcoDim Pro SaaS REST API"}

@app.post("/api/v1/calculer/cablage", dependencies=[Depends(verify_token)])
def calculer_cablage(input_data: CablageInput):
    """
    Calcule la section de câble normalisée et estime les longueurs de ligne
    DC, AC et Terre recommandées selon la norme NF C 15-100.
    """
    try:
        section = estimer_section_cable(
            courant_a=input_data.courant_a,
            longueur_m=input_data.longueur_m,
            chute_tension_max_pct=input_data.chute_tension_max_pct,
            tension_v=input_data.tension_v
        )
        return {
            "section_recommandee_mm2": section,
            "conducteur": "Cuivre"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur interne de calcul : {str(e)}"
        )

@app.post("/api/v1/calculer/bilan", dependencies=[Depends(verify_token)])
def calculer_bilan(input_data: BilanInput):
    """
    Calcule le bilan d'autoconsommation solaire de l'installation.
    """
    try:
        # Conversion des listes en Pandas Series pour calcul d'intégration temporelle
        import pandas as pd
        prod_series = pd.Series(input_data.production_kwh)
        cons_series = pd.Series(input_data.consommation_kwh)
        
        res = calc_autoconsommation(prod_series, cons_series)
        return res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur de calcul du bilan : {str(e)}"
        )

@app.post("/api/v1/etudes", dependencies=[Depends(verify_token)])
def creer_etude(projet: ProjectInput, token_data: dict = Depends(verify_token)):
    """
    Enregistre un nouveau projet d'étude multi-tenant dans la base de données.
    Note : Le tenant_id est automatiquement extrait de la session sécurisée SSO.
    """
    tenant_id = token_data.get("tenant_id")
    user_id = token_data.get("user_id")
    
    # Ici se connecte à Postgres via SQLAlchemy/SQLModel et applique RLS
    return {
        "message": f"Dossier '{projet.nom_projet}' créé avec succès pour le Tenant : {tenant_id}",
        "tenant_id": tenant_id,
        "user_id": user_id,
        "projet": projet.nom_projet
    }

@app.get("/api/v1/audit/export", dependencies=[Depends(verify_token)])
def exporter_logs_audit(token_data: dict = Depends(verify_token)):
    """
    Exporte les journaux d'audit de sécurité du tenant connecté.
    Requis pour la conformité SOC2 / GDPR.
    """
    tenant_id = token_data.get("tenant_id")
    user_id = token_data.get("user_id")

    # Mock de données d'audit de sécurité avec isolation par tenant
    return [
        {
            "id": "audit_log_1",
            "tenant_id": tenant_id,
            "user_id": user_id,
            "action": "USER_LOGIN_SSO",
            "details": {"provider": "clerk", "mfa": True},
            "ip_address": "192.168.1.10",
            "created_at": "2026-07-11T12:00:00Z"
        },
        {
            "id": "audit_log_2",
            "tenant_id": tenant_id,
            "user_id": user_id,
            "action": "DB_QUERY_EXECUTE_RLS",
            "details": {"table": "etudes", "policy": "etudes_isolation_policy"},
            "ip_address": "192.168.1.10",
            "created_at": "2026-07-11T12:05:00Z"
        }
    ]

# --- COLLABORATION EN TEMPS RÉEL (WEBSOCKETS) ---

class ConnectionManager:
    """Gère la liste des connexions actives et diffuse les messages par projet."""
    def __init__(self):
        # Dictionnaire associant un project_id à une liste de WebSocket actives
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, project_id: str):
        await websocket.accept()
        if project_id not in self.active_connections:
            self.active_connections[project_id] = []
        self.active_connections[project_id].append(websocket)

    def disconnect(self, websocket: WebSocket, project_id: str):
        if project_id in self.active_connections:
            self.active_connections[project_id].remove(websocket)
            if not self.active_connections[project_id]:
                del self.active_connections[project_id]

    async def broadcast_to_project(self, message: str, project_id: str, exclude_ws: WebSocket = None):
        """Envoie un message de modification ou de curseur à tous les collaborateurs."""
        if project_id in self.active_connections:
            for connection in self.active_connections[project_id]:
                if connection != exclude_ws:
                    await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/api/v1/collab/ws/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str):
    """
    Canal WebSocket pour synchroniser en temps réel les curseurs, 
    les sélections et les modifications de code des utilisateurs.
    """
    await manager.connect(websocket, project_id)
    try:
        while True:
            # Attendre les données envoyées par l'éditeur du client
            data = await websocket.receive_text()
            # Diffuser la modification aux autres collaborateurs sur le même projet
            await manager.broadcast_to_project(data, project_id, exclude_ws=websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket, project_id)


# --- VERSIONING, SNAPSHOTS & BRANCHES ---

class SnapshotRequest(BaseModel):
    project_id: str
    nom_snapshot: str
    code_snapshot: str

class BranchRequest(BaseModel):
    project_id: str
    nom_branche_source: str
    nom_nouvelle_branche: str

@app.post("/api/v1/etudes/snapshot", dependencies=[Depends(verify_token)])
def creer_snapshot(req: SnapshotRequest, token_data: dict = Depends(verify_token)):
    """
    Crée un instantané de l'état actuel d'un projet pour permettre le retour en arrière.
    """
    tenant_id = token_data.get("tenant_id")
    return {
        "status": "success",
        "message": f"Snapshot '{req.nom_snapshot}' créé pour le projet {req.project_id}",
        "tenant_id": tenant_id,
        "snapshot_id": "snap_mock_12345"
    }

@app.post("/api/v1/etudes/branch", dependencies=[Depends(verify_token)])
def creer_branche(req: BranchRequest, token_data: dict = Depends(verify_token)):
    """
    Crée une branche de travail isolée pour expérimenter des modifications de calculs solaires.
    """
    tenant_id = token_data.get("tenant_id")
    return {
        "status": "success",
        "message": f"Nouvelle branche '{req.nom_nouvelle_branche}' créée à partir de '{req.nom_branche_source}'",
        "tenant_id": tenant_id,
        "project_id": req.project_id
    }

# --- STRIPE BILLING & MONÉTISATION ---

@app.post("/api/v1/billing/webhook")
async def stripe_webhook(
    request: Request, 
    stripe_signature: str = Header(None, alias="Stripe-Signature")
):
    """
    Webhook Stripe pour la synchronisation automatique des abonnements
    multi-tenant de la plateforme.
    """
    from backend.app.services.stripe_service import StripeBillingService
    from fastapi import Request as FastAPIRequest
    
    payload = await request.body()
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_mock")
    
    # Process event payload using Stripe Service
    res = StripeBillingService.handle_stripe_webhook(
        event_payload=payload.decode("utf-8"),
        stripe_sig=stripe_signature or "",
        endpoint_secret=endpoint_secret
    )
    return res


# --- MARKETPLACE & TEMPLATES ---

class TemplatePublishRequest(BaseModel):
    nom_template: str
    description: str
    code_content: str
    is_public: bool = True

@app.get("/api/v1/templates", dependencies=[Depends(verify_token)])
def lister_templates(token_data: dict = Depends(verify_token)):
    """
    Liste les templates de projets de vibe coding disponibles (système et tenant).
    """
    tenant_id = token_data.get("tenant_id")
    return [
        {
            "id": "tpl_1",
            "nom_template": "Villa Solaire standard",
            "description": "Template de calcul photovoltaïque résidentiel classique",
            "code_content": "<h3>Villa Solaire</h3>",
            "is_public": True,
            "creator_tenant_id": None
        },
        {
            "id": "tpl_2",
            "nom_template": "Système de stockage hybride",
            "description": "Calcul de capacité de batterie optimale",
            "code_content": "<h3>Batterie de Stockage</h3>",
            "is_public": False,
            "creator_tenant_id": tenant_id
        }
    ]

@app.post("/api/v1/templates", dependencies=[Depends(verify_token)])
def publier_template(
    req: TemplatePublishRequest, 
    token_data: dict = Depends(verify_token)
):
    """
    Publie un nouveau template dans la marketplace pour le tenant ou de façon publique.
    """
    tenant_id = token_data.get("tenant_id")
    return {
        "status": "success",
        "message": f"Template '{req.nom_template}' publié avec succès dans la marketplace",
        "tenant_id": tenant_id,
        "template_id": "tpl_mock_generated"
    }
