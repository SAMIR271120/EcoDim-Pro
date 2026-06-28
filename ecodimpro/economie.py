def calc_capex_pv(kwp: float, prix_eur_par_kwp: float = 1900.0) -> float:
    """
    Calcule le coût d'investissement initial (CAPEX) pour le photovoltaïque.
    """
    return max(0.0, kwp) * max(0.0, prix_eur_par_kwp)

def calc_capex_thermique(surface_m2: float, prix_eur_par_m2: float = 700.0) -> float:
    """
    Calcule le coût d'investissement initial (CAPEX) pour le solaire thermique.
    """
    return max(0.0, surface_m2) * max(0.0, prix_eur_par_m2)

def economies_annuelles(
    energie_autoconsommee_kwh: float,
    prix_elec_eur_kwh: float,
    energie_injectee_kwh: float = 0.0,
    tarif_rachat_eur_kwh: float = 0.0
) -> float:
    """
    Calcule les économies annuelles générées (en €/an).
    
    Économies = (Énergie autoconsommée * Prix d'achat élec réseau) + (Énergie injectée * Tarif de rachat surplus)
    """
    gain_autoconso = max(0.0, energie_autoconsommee_kwh) * max(0.0, prix_elec_eur_kwh)
    gain_surplus = max(0.0, energie_injectee_kwh) * max(0.0, tarif_rachat_eur_kwh)
    return gain_autoconso + gain_surplus

def payback_simple(capex_total: float, economies_annuelles: float) -> float:
    """
    Calcule le temps de retour sur investissement (payback simple) en années.
    Retourne l'infini (float('inf')) si les économies annuelles sont nulles ou négatives.
    """
    if economies_annuelles <= 0.0:
        return float("inf")
    return max(0.0, capex_total) / economies_annuelles

def van(
    capex_total: float,
    economies_annuelles: float,
    duree_ans: int = 20,
    taux_actualisation: float = 0.03
) -> float:
    """
    Calcule la Valeur Actuelle Nette (VAN) de l'investissement sur une durée donnée.
    
    Formule :
    VAN = -CAPEX + Somme_{t=1}^{duree_ans} (economies_annuelles / (1 + taux_actualisation)^t)
    """
    capex = max(0.0, capex_total)
    cf_total = 0.0
    for t in range(1, duree_ans + 1):
        cf_total += economies_annuelles / ((1.0 + taux_actualisation) ** t)
    return cf_total - capex
