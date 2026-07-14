"""
backend/app/services/stripe_service.py — Service de gestion de facturation Stripe et gestion des abonnements multi-tenant
"""
import os
import stripe
from fastapi import HTTPException, status
from backend.app.services.secrets import SecretsManager

# Initialiser Stripe avec la clé d'API sécurisée
stripe.api_key = SecretsManager.get_stripe_api_key()

class StripeBillingService:
    
    @staticmethod
    def verify_tenant_subscription_quota(tenant_id: str, required_feature: str) -> bool:
        """
        Vérifie si le plan d'abonnement actuel du tenant l'autorise à utiliser
        une fonctionnalité spécifique (ex: 'vibe-coding', 'api-access', 'excess-data').
        """
        # Dans une application de production réelle, interroge la base PostgreSQL.
        # Ici on simule une vérification de quotas pour la démonstration.
        
        # Supposons qu'un plan 'freemium' a des limites strictes
        # plan = database.get_tenant_plan(tenant_id)
        plan = "pro" # Mock plan actif du tenant récupéré de PostgreSQL
        
        if plan == "freemium":
            if required_feature in ["api-access", "heavy-etl"]:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=f"Fonctionnalité '{required_feature}' requiert un abonnement Pro ou Enterprise"
                )
        return True

    @staticmethod
    def handle_stripe_webhook(event_payload: dict, stripe_sig: str, endpoint_secret: str) -> dict:
        """
        Intercepte les événements Stripe (Webhook) pour mettre à jour
        les statuts d'abonnements des tenants dans la base de données.
        """
        try:
            event = stripe.Webhook.construct_event(
                event_payload, stripe_sig, endpoint_secret
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail="Payload de webhook invalide")
        except stripe.error.SignatureVerificationError as e:
            raise HTTPException(status_code=400, detail="Signature Stripe invalide")

        event_type = event['type']
        data_object = event['data']['object']

        # Gérer la création ou mise à jour de l'abonnement
        if event_type == 'customer.subscription.created' or event_type == 'customer.subscription.updated':
            stripe_customer_id = data_object['customer']
            status_sub = data_object['status'] # active, trialing, past_due, canceled
            plan_id = data_object['items']['data'][0]['plan']['id']
            
            # TODO: Mettre à jour le statut du tenant dans la base de données PostgreSQL
            # database.update_tenant_by_stripe_customer(stripe_customer_id, status_sub, plan_id)
            return {"status": "success", "event": event_type, "customer": stripe_customer_id, "state": status_sub}

        elif event_type == 'customer.subscription.deleted':
            stripe_customer_id = data_object['customer']
            # Repasser le tenant au plan 'freemium' immédiatement
            # database.downgrade_tenant(stripe_customer_id)
            return {"status": "downgraded", "event": event_type, "customer": stripe_customer_id}

        return {"status": "ignored", "event": event_type}
