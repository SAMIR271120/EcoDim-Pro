"""
ecodimpro/cablage.py
Module d'estimation de câblage et de calcul de section de câble cuivre (norme NF C 15-100).
"""

SECTIONS_NORMALISEES = [1.5, 2.5, 4.0, 6.0, 10.0, 16.0]

def estimer_section_cable(
    courant_a: float,
    longueur_m: float,
    chute_tension_max_pct: float = 3.0,
    tension_v: float = 400.0
) -> float:
    """
    Calcule la section de câble en cuivre (en mm²) selon la formule simplifiée NF C 15-100.
    S = (2 * L * I) / ( (dU / 100) * U * sigma )
    Où :
      - L = longueur simple du câble (m)
      - I = courant maximal (A)
      - dU = chute de tension tolérée en % (ex: 3.0 %)
      - U = tension du circuit (V)
      - sigma (conductivité du cuivre) = 56 m / (ohm.mm²)
      
    Retourne la section commerciale normalisée supérieure (1.5, 2.5, 4, 6, 10 ou 16 mm²).
    """
    if courant_a <= 0.0 or longueur_m <= 0.0:
        return 1.5

    dU_v = (chute_tension_max_pct / 100.0) * tension_v
    conductivite_cuivre = 56.0 # m/(ohm*mm2)
    
    # Calcul théorique de la section en mm²
    section_theorique = (2.0 * longueur_m * courant_a) / (dU_v * conductivite_cuivre)
    
    # Choix de la section commerciale immédiatement supérieure ou égale
    for s in SECTIONS_NORMALISEES:
        if s >= section_theorique:
            return s
            
    return SECTIONS_NORMALISEES[-1] # Retourne 16 mm² max par défaut si supérieur

def estimer_metrage_cablage(nb_panneaux: int, distance_toit_onduleur_m: float = 15.0) -> dict:
    """
    Estime de manière forfaitaire la longueur de câble nécessaire (chiffrage indicatif) :
      - Cable DC (rouge & noir) : distance toit-onduleur * 2 + 1.5m de liaison par panneau
      - Cable AC (onduleur-TGBT) : forfait 5 mètres
      - Cable Terre (cuivre 6mm²) : distance toit-TGBT + forfait 10 mètres
    """
    nb_p = max(0, nb_panneaux)
    dist_to = max(0.0, distance_toit_onduleur_m)
    
    cablage_dc = (dist_to * 2.0) + (nb_p * 1.5)
    cablage_ac = 5.0
    cablage_terre = dist_to + 10.0
    
    return {
        "cable_dc_m": round(cablage_dc, 1),
        "cable_ac_m": round(cablage_ac, 1),
        "cable_terre_m": round(cablage_terre, 1)
    }
