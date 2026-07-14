# EcoDim Pro — Guide Technique et Hypothèses

**EcoDim Pro** est une application Python professionnelle et académique conçue pour évaluer les besoins énergétiques d'un logement résidentiel (électricité, eau chaude sanitaire, chauffage) et dimensionner des installations solaires d'autoconsommation : photovoltaïque (PV) et solaire thermique (ECS / appoint chauffage).

Ce document décrit le fonctionnement de l'application, l'architecture du code, les instructions d'installation et de lancement, ainsi que les limites physiques des modèles utilisés.

---

## 🚀 Installation et Lancement

### Prérequis
- Python 3.11+
- Gestionnaire de paquets `pip`

### 1. Installation des dépendances
Installez les packages requis via le fichier `requirements.txt` à la racine :
```bash
pip install -r requirements.txt
```

### 2. Lancement de l'interface graphique (Streamlit)
Pour démarrer l'application locale et interagir avec l'interface :
```bash
streamlit run app/streamlit_app.py
```
L'application s'ouvre automatiquement dans votre navigateur (généralement à l'adresse `http://localhost:8501`).

### 3. Exécution des tests unitaires
Pour exécuter la suite complète de tests de validation (formules physiques, intégration, scénarios) :
```bash
pytest
```

---

## 📁 Architecture du Projet

L'application est découpée de manière modulaire :

- `ecodimpro/` (Package principal)
  - `besoins.py` : Calculs de l'électricité spécifique (appareils), des besoins ECS et chauffage (méthode Degrés-Jours).
  - `pv.py` : Connexion à l'API européenne PVGIS (v5.2) avec cache local et algorithme de repli géographique.
  - `thermique.py` : Dimensionnement du solaire thermique (volume de ballon, surface de capteurs et couverture utile).
  - `batterie.py` : Simulation d'un système de stockage par batterie (méthodes horaire chronologique et mensuelle empirique).
  - `bilan.py` : Calculs de taux d'autoconsommation, autonomie et bilans d'énergie annuelle.
  - `economie.py` : Calcul du CAPEX initial, gains financiers annuels, temps de retour (payback) et Valeur Actuelle Nette (VAN).
  - `rapport.py` : Génération du rapport PDF personnalisé (ReportLab) avec intégration de graphiques Plotly.
- `app/`
  - `streamlit_app.py` : Interface utilisateur web interactive.
- `data/pvgis_cache/`
  - Dossier de cache local pour éviter les requêtes répétitives vers l'API européenne.
- `tests/`
  - Tests unitaires par module et tests d'intégration complets sur 3 profils types de foyers.

---

## 📊 Hypothèses de Calcul et Limites Physiques

### 1. Électricité spécifique (appareils)
- **Modèle de base** : Somme pondérée par la puissance, l'usage quotidien et la récurrence hebdomadaire des appareils $\left(\sum \frac{P \times h \times j \times 52.14}{1000}\right)$.
- **Modèle temporel** : Import d'un CSV (résolution horaire). Si des pas de temps plus fins sont fournis (15 min ou 30 min), les données sont agrégées à l'heure (`resample('H').sum()`) pour être conformes aux modèles solaires.

### 2. Eau Chaude Sanitaire (ECS)
- La formule physique s'appuie sur la capacité thermique de l'eau ($1.163 \text{ Wh/L/°C}$) :
  $$E_{ecs} = nb\_personnes \times L_{jour} \times 365 \times (T_{sortie} - T_{entree}) \times 1.163 / 1000$$
- Volume de ballon recommandé : $1.5 \times \text{besoin quotidien}$.

### 3. Chauffage
- **Méthode** : Degrés-Jours Unifiés (DJU base 18°C).
- **Consigne** : Les DJU sont ajustés en fonction de la température de consigne ($T_{consigne}$) :
  $$DJU_{corrige} = DJU_{base} + (T_{consigne} - 18) \times 200$$
  *(Le facteur 200 représente une saison de chauffe moyenne de 200 jours en France)*.
- **Coefficient G** : Coefficient de déperdition simplifié mappé selon le niveau d'isolation déclarée (faible=2.5, moyen=1.5, bon=1.0, RT2012=0.6 W/m²/°C).

### 4. Solaire Thermique & Risque de Stagnation
- La production thermique brute est calculée par :
  $$P_{thermique} = \text{Surface capteurs} \times \text{Rendement} \times \text{Irradiation annuelle}$$
- En résidentiel, le taux de couverture utile annuel pour l'ECS est physiquement plafonné à **80%** car l'excédent estival ne peut pas être stocké à long terme.
- Si le taux de couverture brut dépasse **85%**, l'outil émet une alerte de **risque de stagnation estivale (surchauffe)**. Cela peut détériorer le fluide caloporteur.

### 5. Batterie de Stockage
- **Modèle horaire** : Cycle d'énergie chronologique avec rendement appliqué symétriquement en charge et décharge $(\eta = \sqrt{\text{rendement}})$.
- **Modèle mensuel (fallback)** : Si les données horaires ne sont pas disponibles, la batterie est supposée effectuer 25 cycles complets par mois en moyenne (0.8 cycle/jour), limitant le transit d'énergie mensuelle.

### 6. Analyse Économique
- Les calculs de rentabilité n'incluent pas l'inflation, l'usure de l'onduleur (à remplacer à 10 ans), ni la dégradation annuelle de rendement des modules (typiquement 0.5%/an). La Valeur Actuelle Nette (VAN) s'appuie sur un taux d'actualisation de l'argent fixe (défaut 3.0%).
