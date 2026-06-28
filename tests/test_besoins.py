import pytest
import pandas as pd
from pathlib import Path
from ecodimpro.besoins import (
    calc_besoin_elec, calc_besoin_ecs,
    calc_besoin_chauffage, calc_besoin_chauffage_legacy
)
from ecodimpro.constantes_dpe import (
    ZONES_CLIMATIQUES, UMUR_PAR_PERIODE, UPH_TOITURE, UPB_PLANCHER_BAS_DEFAUT,
    SCENARIOS_ECS
)


# ─── Besoins électriques ──────────────────────────────────────────────────────

def test_calc_besoin_elec_appareils():
    appareils = [
        {"nom": "Réfrigérateur", "puissance_w": 150.0, "heures_jour": 24.0, "jours_semaine": 7.0},
        {"nom": "TV", "puissance_w": 100.0, "heures_jour": 4.0, "jours_semaine": 7.0},
    ]
    expected = (150 / 1000 * 24 * 7 * 52.14) + (100 / 1000 * 4 * 7 * 52.14)
    result = calc_besoin_elec(appareils)
    assert pytest.approx(result, 0.01) == expected


def test_calc_besoin_elec_csv(tmp_path):
    csv_file = tmp_path / "conso_test.csv"
    dates = pd.date_range(start="2023-01-01 00:00:00", periods=24, freq="h")
    data = {"horodatage": dates, "consommation_kwh": [0.5] * 24}
    df = pd.DataFrame(data)
    df.to_csv(csv_file, index=False)

    total, series = calc_besoin_elec(csv_file)
    assert total == 12.0
    assert len(series) == 24
    assert series.sum() == 12.0
    assert isinstance(series, pd.Series)


# ─── Besoin ECS ───────────────────────────────────────────────────────────────

def test_calc_besoin_ecs_valeurs_dpe():
    """Vérification avec les valeurs conventionnelles DPE : 56 L/j à 40°C."""
    expected = 4 * 56 * 365 * (40 - 12) * 1.163 / 1000.0
    result = calc_besoin_ecs(4, 56.0, 12.0, 40.0)
    assert pytest.approx(result, 0.01) == expected


def test_calc_besoin_ecs_zero_personne():
    assert calc_besoin_ecs(0) == 0.0


def test_calc_besoin_ecs_scenarios():
    """Les scénarios SCENARIOS_ECS donnent des résultats cohérents."""
    litres_conv = SCENARIOS_ECS["Conventionnel (réglementaire — 3CL-DPE)"]
    litres_dep  = SCENARIOS_ECS["Usage dépensier"]
    assert litres_dep > litres_conv, "L'usage dépensier doit être supérieur au conventionnel"
    assert litres_conv == 56.0
    assert litres_dep  == 79.0


# ─── Besoin Chauffage — nouvelle formule 3CL-DPE ─────────────────────────────

def test_calc_besoin_chauffage_formule_u():
    """
    Vérification de la formule GV × DH14 / 1000 avec des valeurs connues.
    Surface 100 m², murs non isolés (U=2.5), combles perdus 1988 (U=0.43),
    plancher bas défaut (U=0.45), zone H2 (DH14=33300).
    Ratios par défaut : murs 60%, toiture 30%, plancher 10%.
    """
    surface = 100.0
    umur    = 2.50
    uph     = 0.43
    upb     = UPB_PLANCHER_BAS_DEFAUT  # 0.45
    dh14    = ZONES_CLIMATIQUES["H2"]["dh14"]  # 33300

    s_murs     = surface * 0.6
    s_toiture  = surface * 0.3
    s_plancher = surface * 0.1
    gv = umur * s_murs + uph * s_toiture + upb * s_plancher
    expected = gv * dh14 / 1000.0

    result = calc_besoin_chauffage(
        surface_m2=surface, umur=umur, uph=uph, upb=upb, dh14=dh14
    )
    assert pytest.approx(result, 0.01) == expected


def test_calc_besoin_chauffage_zones_officielles():
    """La zone H1 (DH14 élevé) doit donner un besoin plus grand que H3."""
    kwargs = dict(surface_m2=100, umur=0.26, uph=0.23, upb=0.45)
    besoin_h1 = calc_besoin_chauffage(dh14=ZONES_CLIMATIQUES["H1"]["dh14"], **kwargs)
    besoin_h3 = calc_besoin_chauffage(dh14=ZONES_CLIMATIQUES["H3"]["dh14"], **kwargs)
    assert besoin_h1 > besoin_h3


def test_calc_besoin_chauffage_umur_par_periode():
    """Les constantes UMUR_PAR_PERIODE sont accessibles et cohérentes."""
    for periode, vals in UMUR_PAR_PERIODE.items():
        for zone in ["H1", "H2", "H3"]:
            assert vals[zone] > 0, f"U mur invalide pour {periode} / {zone}"
        assert vals["H1"] <= vals["H3"], "H1 doit être ≤ H3 (isolation plus sévère au nord)"


def test_calc_besoin_chauffage_uph_toiture():
    """Les constantes UPH_TOITURE sont toutes positives."""
    for label, val in UPH_TOITURE.items():
        assert val > 0, f"Uph invalide pour : {label}"


# ─── Formule legacy (rétrocompatibilité) ─────────────────────────────────────

def test_calc_besoin_chauffage_legacy():
    """L'ancienne formule G × DJU doit toujours produire le bon résultat."""
    expected = 100 * 1.5 * (2000 + (19 - 18) * 200) * 24 / 1000.0
    result = calc_besoin_chauffage_legacy(
        surface_m2=100, niveau_isolation="moyen",
        deg_jours_unifies=2000, t_consigne=19
    )
    assert pytest.approx(result, 0.01) == expected


def test_calc_besoin_chauffage_legacy_isolation_inconnue():
    """Niveau d'isolation inconnu → valeur par défaut 'moyen' (G=1.5)."""
    res_moyen   = calc_besoin_chauffage_legacy(100, "moyen",   2000, 19)
    res_inconnu = calc_besoin_chauffage_legacy(100, "inconnu", 2000, 19)
    assert res_moyen == res_inconnu


def test_calc_besoin_chauffage_legacy_rt2012():
    expected = 100 * 0.6 * (2000 + 200) * 24 / 1000.0
    result   = calc_besoin_chauffage_legacy(100, "rt2012", 2000, 19)
    assert pytest.approx(result, 0.01) == expected
