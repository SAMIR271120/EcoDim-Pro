# Guide Utilisateur — EcoDim Pro

Bienvenue dans le guide d'utilisation de **EcoDim Pro**, votre outil professionnel de dimensionnement solaire photovoltaïque et thermique. Ce guide pas-à-pas est conçu pour aider les installateurs indépendants et les diagnostiqueurs immobiliers à utiliser au mieux l'application pour conseiller leurs clients.

---

## 📋 Étape 1 : Personnaliser l'Application (Branding B2B)

Avant de commencer la saisie des données d'un client, rendez-vous dans le panneau latéral gauche (Sidebar) de l'application :
1. **Nom de l'entreprise** : Saisissez le nom de votre cabinet ou entreprise d'installation (ex: *Soleil & Co*). Ce nom figurera sur le rapport PDF.
2. **Logo** : Importez le logo de votre entreprise (au format PNG ou JPG). Il sera automatiquement dimensionné et inséré en haut à droite de la couverture du rapport PDF généré.
3. **Données du client** : Saisissez le nom, l'adresse du logement et l'adresse e-mail de votre client pour personnaliser l'en-tête du rapport.

---

## 🏠 Étape 2 : Caractéristiques du Logement

Dans l'onglet **"🏠 Logement & Localisation"** :
- **Localisation** : Sélectionnez une ville de référence française la plus proche du logement du client pour obtenir des DJU et des valeurs d'ensoleillement réalistes. Si vous souhaitez être extrêmement précis, choisissez "Coordonnées manuelles GPS" et entrez directement la latitude et la longitude du projet.
- **Surface** : Indiquez la surface habitable en m² (utile pour évaluer le volume de chauffe).
- **Isolation** : Sélectionnez le niveau d'isolation. Ce paramètre influe directement sur le besoin de chauffage estimé.
- **Consigne** : Ajustez la température de consigne souhaitée par le client (19°C par défaut). Une hausse de 1°C augmente le besoin de chauffage d'environ 7%.

---

## 🔌 Étape 3 : Évaluation de la Consommation Électrique

Dans l'onglet **"🔌 Besoins Électriques"** :
- **Option 1 : Liste des appareils** : Si le client n'a pas de relevé précis, remplissez le tableau dynamique en y ajoutant les principaux appareils électriques du foyer, leur puissance en Watts et leur fréquence d'utilisation par jour et par semaine. Vous pouvez ajouter ou supprimer des lignes de manière interactive.
- **Option 2 : Import CSV** : Si le client possède un export de sa courbe de charge horaire (ex: fichier Enedis en kWh), chargez le fichier CSV directement. L'application calculera automatiquement le cumul annuel et utilisera le profil horaire exact pour simuler la charge de la batterie.

---

## 🛁 Étape 4 : Eau Chaude & Chauffage

Dans l'onglet **"🛁 ECS & Chauffage"** :
- **Eau Chaude Sanitaire** : Indiquez le nombre d'occupants. Le volume par jour est estimé à 50 Litres par personne. L'application calcule le besoin d'énergie nécessaire pour élever l'eau de la température du réseau (~12°C) à la température d'utilisation (~55°C).
- **Chauffage** : Activez ou désactivez l'intégration du chauffage selon le type d'installation visée chez le client.

---

## ☀️ Étape 5 : Dimensionnement des Systèmes Solaires

Dans l'onglet **"☀️ Solaire & Batterie"** :
- **Puissance PV (kWp)** : Configurez la puissance totale des panneaux photovoltaïques envisagée (ex: 3 kWp pour une toiture standard de ~15 m²).
- **Orientation & Inclinaison** : Ajustez l'angle d'inclinaison de la toiture (30° par défaut) et l'azimut (0° = Sud, -90° = Est, 90° = Ouest).
- **Solaire Thermique (m²)** : Saisissez la surface de capteurs pour la production d'eau chaude. Si vous n'installez pas de solaire thermique, laissez la valeur à 0.
- **Batterie** : Cochez l'option pour simuler un stockage batterie, puis ajustez la capacité (kWh) et le rendement.

---

## 💰 Étape 6 : Paramètres Économiques

Dans l'onglet **"💰 Tarifs & CAPEX"** :
- Remplissez les tarifs d'achat de l'électricité au réseau et de vente de votre surplus au fournisseur d'énergie.
- Indiquez vos tarifs de pose de matériel (CAPEX) pour le PV, le thermique, et la batterie afin que le calcul de temps de retour sur investissement soit adapté à vos propres devis.

---

## 📊 Étape 7 : Analyse des Résultats et Export PDF

Dans l'onglet **"📊 Résultats & Rapport"** :
1. **Indicateurs Clés** : Visualisez instantanément la production PV annuelle estimée, votre taux d'autoconsommation global (combien d'énergie solaire est consommée par le foyer) et votre taux d'autonomie.
2. **Comparatif de Scénarios** : L'application compare automatiquement 3 scénarios :
   - *Scénario 1* : Raccordement classique au réseau électrique (sans investissement).
   - *Scénario 2* : Autoconsommation photovoltaïque simple (sans batterie).
   - *Scénario 3* : Installation complète (PV + Batterie + Solaire Thermique).
3. **Graphiques** : Étudiez le graphique de croisement entre la production mensuelle et la consommation estimée du logement pour voir les mois de surplus ou de déficit énergétique.
4. **Télécharger le Rapport** : Cliquez sur **"Générer le rapport PDF"**, puis sur le bouton de téléchargement pour récupérer le document PDF final personnalisé. Ce document de 2 pages à vos couleurs est prêt à être imprimé ou envoyé par e-mail au client !
