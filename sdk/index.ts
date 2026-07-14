/**
 * Antigravity SDK — Client TypeScript officiel pour l'intégration d'EcoDim Pro SaaS.
 */

export interface SDKConfig {
  baseUrl: string;
  ssoToken?: string;
  apiKey?: string;
}

export interface CablageParams {
  courantA: number;
  longueurM: number;
  chuteTensionMaxPct?: number;
  tensionV?: number;
}

export interface BilanParams {
  productionKwh: number[];
  consommationKwh: number[];
}

export interface ProjectData {
  nomProjet: string;
  clientPrenom: string;
  clientNom: string;
  clientEmail?: string;
  adresse?: string;
  donneesCalcul: Record<string, any>;
}

export class AntigravitySDK {
  private baseUrl: string;
  private ssoToken?: string;
  private apiKey?: string;

  constructor(config: SDKConfig) {
    this.baseUrl = config.baseUrl.replace(/\/$/, "");
    this.ssoToken = config.ssoToken;
    this.apiKey = config.apiKey;
  }

  /**
   * Modifie dynamiquement le jeton d'authentification lors de la connexion/déconnexion de l'utilisateur.
   */
  public setToken(token: string) {
    this.ssoToken = token;
  }

  /**
   * Prépare les en-têtes de requêtes HTTP avec authentification SSO/Bearer.
   */
  private getHeaders(): HeadersInit {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (this.ssoToken) {
      headers["Authorization"] = `Bearer ${this.ssoToken}`;
    } else if (this.apiKey) {
      headers["X-API-Key"] = this.apiKey;
    }
    return headers;
  }

  /**
   * Effectue un appel réseau HTTP générique.
   */
  private async request<T>(endpoint: string, options: RequestInit): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        ...this.getHeaders(),
        ...options.headers,
      },
    });

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`[Antigravity SDK Error] HTTP ${response.status}: ${errText || response.statusText}`);
    }

    return response.json() as Promise<T>;
  }

  /**
   * Calcule la section de câble requise selon la norme NF C 15-100.
   */
  public async calculerCablage(params: CablageParams): Promise<{ section_recommandee_mm2: number; conducteur: string }> {
    return this.request<{ section_recommandee_mm2: number; conducteur: string }>("/api/v1/calculer/cablage", {
      method: "POST",
      body: JSON.stringify({
        courant_a: params.courantA,
        longueur_m: params.longueurM,
        chute_tension_max_pct: params.chuteTensionMaxPct ?? 3.0,
        tension_v: params.tensionV ?? 400.0,
      }),
    });
  }

  /**
   * Calcule le bilan d'autoconsommation énergétique globale.
   */
  public async calculerBilan(params: BilanParams): Promise<any> {
    return this.request<any>("/api/v1/calculer/bilan", {
      method: "POST",
      body: JSON.stringify({
        production_kwh: params.productionKwh,
        consommation_kwh: params.consommationKwh,
      }),
    });
  }

  /**
   * Enregistre une étude / projet solaire dans le cadre multi-tenant.
   */
  public async sauvegarderEtude(project: ProjectData): Promise<{ message: string; tenant_id: string; user_id: string; projet: string }> {
    return this.request<any>("/api/v1/etudes", {
      method: "POST",
      body: JSON.stringify({
        nom_projet: project.nomProjet,
        client_prenom: project.clientPrenom,
        client_nom: project.clientNom,
        client_email: project.clientEmail,
        adresse: project.adresse,
        donnees_calcul: project.donneesCalcul,
      }),
    });
  }
}
