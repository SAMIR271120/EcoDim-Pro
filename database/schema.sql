-- ============================================================================
-- database/schema.sql — Schéma Multi-Tenant PostgreSQL pour EcoDim Pro SaaS
-- ============================================================================

-- Extensions nécessaires
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table des tenants (entreprises clientes)
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nom VARCHAR(255) NOT NULL,
    plan_tarifaire VARCHAR(50) NOT NULL DEFAULT 'freemium' CHECK (plan_tarifaire IN ('freemium', 'pro', 'enterprise')),
    stripe_customer_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table des utilisateurs (multi-tenant)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'diagnostiqueur' CHECK (role IN ('admin', 'diagnostiqueur', 'viewer')),
    mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    mfa_secret VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table des études / projets solaires et thermiques
CREATE TABLE etudes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE SET NULL,
    nom_etude VARCHAR(255) NOT NULL,
    client_prenom VARCHAR(100),
    client_nom VARCHAR(100),
    client_email VARCHAR(255),
    client_societe VARCHAR(255),
    adresse VARCHAR(550),
    notes TEXT,
    donnees_saisie JSONB NOT NULL DEFAULT '{}'::jsonb,
    resultats_calculs JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table des logs d'audit de sécurité et exécution
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    details JSONB DEFAULT '{}'::jsonb,
    ip_address VARCHAR(45),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table de la marketplace des templates de projets vibe-coding
CREATE TABLE templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE SET NULL, -- NULL si template système/public
    nom_template VARCHAR(255) NOT NULL,
    description TEXT,
    code_content TEXT NOT NULL, -- Contenu du template Monaco
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index pour accélérer le filtrage par tenant_id
CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_etudes_tenant ON etudes(tenant_id);
CREATE INDEX idx_audit_logs_tenant ON audit_logs(tenant_id);

-- ============================================================================
-- ROW-LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

-- Activer la RLS sur les tables multi-tenant
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE etudes ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE templates ENABLE ROW LEVEL SECURITY;

-- 1. Politique sur la table users (un utilisateur ne voit que les membres de son tenant)
CREATE POLICY users_isolation_policy ON users
    FOR ALL
    USING (tenant_id = (SELECT tenant_id FROM users WHERE id = auth.uid())); -- auth.uid() simule l'ID connecté (NextAuth/Clerk)

-- 2. Politique sur la table etudes (lecture/écriture uniquement pour le tenant_id de l'utilisateur)
CREATE POLICY etudes_isolation_policy ON etudes
    FOR ALL
    USING (tenant_id = (SELECT tenant_id FROM users WHERE id = auth.uid()))
    WITH CHECK (tenant_id = (SELECT tenant_id FROM users WHERE id = auth.uid()));

-- 3. Politique sur la table audit_logs (les admins du tenant peuvent lire les logs d'audit du tenant)
CREATE POLICY audit_logs_isolation_policy ON audit_logs
    FOR ALL
    USING (tenant_id = (SELECT tenant_id FROM users WHERE id = auth.uid()));

-- 4. Politique sur les templates (publics ou appartenant au tenant)
CREATE POLICY templates_isolation_policy ON templates
    FOR ALL
    USING (is_public = TRUE OR tenant_id = (SELECT tenant_id FROM users WHERE id = auth.uid()));
