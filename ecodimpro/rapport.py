import os
import tempfile
import shutil
from pathlib import Path
from typing import Union
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Backend sans interface graphique pour serveur
import matplotlib.pyplot as plt

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak, PageTemplate, Frame, NextPageTemplate, Flowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# ---------------------------------------------------------------------------
# PALETTE DE COULEURS (tokens definitifs)
# ---------------------------------------------------------------------------
COULEURS = {
    "graphite_fonce":             "#14171C",
    "graphite_clair":             "#1C2128",
    "ambre":                      "#E8A33D",
    "sarcelle":                   "#3DBFAE",
    "bleu_gris":                  "#5B7C99",
    "blanc_casse":                "#F4F1EA",
    "fond_clair":                 "#FFFFFF",
    "fond_encadre":               "#F7F5F0",
    "fond_surbrillance_ambre":    "#FBF0DC",
    "fond_surbrillance_sarcelle": "#E3F5F2",
    "texte_principal":            "#1A1D21",
    "texte_attenue":              "#6B7280",
    "bordure_legere":             "#E5E5E5",
    "noir_entete_tableau":        "#14171C",
    "vert_co2":                   "#22896B",
}

# ---------------------------------------------------------------------------
# GESTION DES POLICES PERSONNALISEES
# ---------------------------------------------------------------------------
_FONTS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "fonts")
_POLICES_CHARGEES = set()

def _enregistrer_polices():
    """Charge les polices TTF personnalisees avec fallback silencieux vers Helvetica."""
    global _POLICES_CHARGEES
    if _POLICES_CHARGEES:
        return  # Deja charge
    polices = {
        "SpaceGrotesk-Bold":       "SpaceGrotesk-Bold.ttf",
        "SpaceGrotesk-Medium":     "SpaceGrotesk-Medium.ttf",
        "Inter-Regular":           "Inter-Regular.ttf",
        "Inter-Medium":            "Inter-Medium.ttf",
        "JetBrainsMono-Medium":    "JetBrainsMono-Medium.ttf",
        "JetBrainsMono-SemiBold":  "JetBrainsMono-SemiBold.ttf",
    }
    for nom, fichier in polices.items():
        chemin = os.path.join(_FONTS_DIR, fichier)
        try:
            if os.path.exists(chemin) and os.path.getsize(chemin) > 10_000:
                pdfmetrics.registerFont(TTFont(nom, chemin))
                _POLICES_CHARGEES.add(nom)
        except Exception:
            pass  # Fallback silencieux vers Helvetica

def _f(nom_custom, fallback="Helvetica"):
    """Retourne le nom de police custom si charge, sinon le fallback."""
    return nom_custom if nom_custom in _POLICES_CHARGEES else fallback

def _fb(nom_custom, fallback="Helvetica-Bold"):
    """Fallback pour les polices Bold."""
    return nom_custom if nom_custom in _POLICES_CHARGEES else fallback


# ---------------------------------------------------------------------------
# PUCE COULEUR (remplace le glyphe Unicode casse)
# ---------------------------------------------------------------------------
class PuceCouleur(Flowable):
    """Petit rectangle plein colore pour les puces de section."""
    def __init__(self, couleur_hex, taille=8, decalage_y=2):
        Flowable.__init__(self)
        self.couleur = HexColor(couleur_hex)
        self.taille = taille
        self.decalage_y = decalage_y
        self.width = taille + 6
        self.height = taille + decalage_y
    def draw(self):
        self.canv.setFillColor(self.couleur)
        self.canv.rect(0, self.decalage_y, self.taille, self.taille, fill=1, stroke=0)

class NumberedCanvas(canvas.Canvas):
    """
    Canvas personnalisé pour ajouter des éléments dynamiques de mise en page.
    Pour la couverture (page 1), on ne dessine ni en-tête ni pied de page.
    Pour les pages suivantes, on dessine l'en-tête (mini logo + nom installateur)
    et le pied de page épuré avec pagination "Page X sur Y".
    """
    installateur_nom = "EcoDim Pro"
    date_etude = ""
    logo_valide_path = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        
        # Page 1 : Couverture (décorée entièrement via le template de couverture)
        if self._pageNumber == 1:
            self.restoreState()
            return
            
        # Pages de contenu : En-tête sobre
        self.setFont("Helvetica", 9)
        self.setFillColor(HexColor("#64748B"))
        
        # Dessiner le mini logo s'il existe et est valide
        if NumberedCanvas.logo_valide_path:
            try:
                self.drawImage(NumberedCanvas.logo_valide_path, 54, 802, width=32, height=14, preserveAspectRatio=True, mask='auto')
                self.drawString(92, 805, f"— {NumberedCanvas.installateur_nom}")
            except Exception:
                self.drawString(54, 805, NumberedCanvas.installateur_nom)
        else:
            self.drawString(54, 805, NumberedCanvas.installateur_nom)
            
        self.setStrokeColor(HexColor("#E5E5E5"))
        self.setLineWidth(0.5)
        self.line(54, 796, 541.27, 796)
            
        # Pages de contenu : Pied de page épuré
        self.line(54, 55, 541.27, 55)
        page_text = f"Page {self._pageNumber} sur {page_count}"
        self.drawRightString(541.27, 40, page_text)
        self.drawString(54, 40, f"{NumberedCanvas.installateur_nom}  •  Étude réalisée le {NumberedCanvas.date_etude}")
        self.restoreState()


def draw_cover_background(canvas_obj, doc_obj):
    """
    Trace le fond de la page de couverture (blanc propre selon demande v3).
    Dessine aussi la mention confidentielle en bas de page directement sur le canvas
    pour éviter qu'elle déborde dans une page orpheline.
    """
    canvas_obj.saveState()
    canvas_obj.setFillColor(HexColor("#FFFFFF"))  # Fond blanc pur
    canvas_obj.rect(0, 0, 595.27, 841.89, stroke=0, fill=1)
    # Mention confidentielle ancrée en bas de la couverture
    canvas_obj.setFont("Helvetica", 8)
    canvas_obj.setFillColor(HexColor("#94A3B8"))
    canvas_obj.drawCentredString(595.27 / 2, 55, "Document confidentiel — usage professionnel")
    canvas_obj.restoreState()


def _est_image_valide_reportlab(path: str) -> bool:
    """
    Vérifie si un fichier image existe, n'est pas un SVG (incompatible nativement avec ReportLab/Pillow),
    et est correctement identifiable par Pillow.
    """
    if not path or not os.path.exists(path):
        return False
    if path.lower().endswith(".svg"):
        return False
    try:
        from PIL import Image as PILImage
        with PILImage.open(path) as img:
            img.verify()
        return True
    except Exception:
        return False


def _generer_graphiques_matplotlib(resultats: dict, besoins: dict, temp_dir: str) -> tuple[str, str, str, str, str]:
    """
    Génère les graphiques statiques avec Matplotlib et les enregistre en PNG.
    """
    # Palette de couleurs harmonisée
    c_ambre = '#E8A33D'
    c_sarcelle = '#3DBFAE'
    c_neutre = '#5B7C99'  # Gris-bleu neutre professionnel

    # 1. Graphique répartition des besoins (Camembert)
    elec_kwh = besoins.get("elec_annuel", 0.0)
    ecs_kwh = besoins.get("ecs_annuel", 0.0)
    chauffage_kwh = besoins.get("chauffage_annuel", 0.0)
    
    labels = ['Électricité spécifique', 'ECS', 'Chauffage']
    valeurs = [elec_kwh, ecs_kwh, chauffage_kwh]
    valeurs_non_nulles = [(l, v) for l, v in zip(labels, valeurs) if v > 0]
    
    path_pie = os.path.join(temp_dir, "repartition_besoins.png")
    fig, ax = plt.subplots(figsize=(4.5, 4.0), facecolor='white')
    if valeurs_non_nulles:
        ax.pie([v for _, v in valeurs_non_nulles], 
               labels=[l for l, _ in valeurs_non_nulles],
               colors=[c_ambre, c_sarcelle, c_neutre], 
               autopct='%1.0f%%',
               textprops={'fontsize': 9, 'color': '#1E293B'})
    else:
        ax.pie([1], labels=["Aucun besoin saisi"], colors=["#CBD5E1"])
    ax.set_title("Répartition des Besoins Annuels", fontsize=10, fontweight='bold', color='#1E3A8A', pad=10)
    fig.tight_layout()
    fig.savefig(path_pie, dpi=150)
    plt.close(fig)

    # 2. Graphique production PV mensuelle (Barres)
    prod_mensuelle = resultats.get("production_pv_mensuelle", [0.0]*12)
    if hasattr(prod_mensuelle, "tolist"):
        prod_mensuelle = prod_mensuelle.tolist()
    elif not isinstance(prod_mensuelle, list):
        prod_mensuelle = list(prod_mensuelle)
        
    mois = ['Jan','Fév','Mar','Avr','Mai','Jun','Jul','Aoû','Sep','Oct','Nov','Déc']
    path_prod = os.path.join(temp_dir, "production_mensuelle.png")
    fig, ax = plt.subplots(figsize=(6.2, 2.8), facecolor='white')
    ax.bar(mois, prod_mensuelle, color=c_ambre, edgecolor='#C28229', alpha=0.9, width=0.6)
    ax.set_ylabel('Production (kWh)', fontsize=8, color='#475569')
    ax.set_title('Production Photovoltaïque Mensuelle Estimée (kWh)', fontsize=10, fontweight='bold', color='#1E3A8A', pad=10)
    ax.grid(axis='y', linestyle='--', alpha=0.5, color='#CBD5E1')
    ax.tick_params(colors='#475569', labelsize=8)
    fig.tight_layout()
    fig.savefig(path_prod, dpi=150)
    plt.close(fig)

    # 3. Graphique Production vs Consommation (Barres groupées)
    conso_mensuelle = resultats.get("conso_mensuelle")
    if conso_mensuelle is None:
        elec_m = besoins.get("elec_annuel", 0.0) / 12.0
        ecs_m = besoins.get("ecs_annuel", 0.0) / 12.0
        
        # Répartition du chauffage selon la zone climatique (H1/H2/H3)
        zone = resultats.get("dimensionnement", {}).get("zone_climatique", "H2")
        if zone == "H3":
            heat_weights = [0.25, 0.20, 0.15, 0.05, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.10, 0.25]
        elif zone == "H1":
            heat_weights = [0.20, 0.18, 0.14, 0.08, 0.02, 0.0, 0.0, 0.0, 0.0, 0.05, 0.13, 0.20]
        else: # H2
            heat_weights = [0.22, 0.18, 0.14, 0.06, 0.0, 0.0, 0.0, 0.0, 0.0, 0.02, 0.13, 0.25]
            
        heat_annuel = besoins.get("chauffage_annuel", 0.0)
        heat_m = [heat_annuel * w for w in heat_weights]
        conso_mensuelle = [elec_m + ecs_m + h_val for h_val in heat_m]
    
    if hasattr(conso_mensuelle, "tolist"):
        conso_mensuelle = conso_mensuelle.tolist()
    elif not isinstance(conso_mensuelle, list):
        conso_mensuelle = list(conso_mensuelle)

    path_vs = os.path.join(temp_dir, "production_vs_consommation.png")
    fig, ax = plt.subplots(figsize=(6.2, 2.8), facecolor='white')
    x = range(12)
    largeur = 0.35
    ax.bar([i - largeur/2 for i in x], prod_mensuelle, largeur, label='Production PV', color=c_ambre, edgecolor='#C28229')
    ax.bar([i + largeur/2 for i in x], conso_mensuelle, largeur, label='Consommation', color=c_sarcelle, edgecolor='#259A9F')
    ax.set_xticks(list(x))
    ax.set_xticklabels(mois, fontsize=8, color='#475569')
    ax.set_ylabel('kWh', fontsize=8, color='#475569')
    ax.set_title('Production PV vs Consommation Mensuelle', fontsize=10, fontweight='bold', color='#1E3A8A', pad=10)
    ax.grid(axis='y', linestyle='--', alpha=0.5, color='#CBD5E1')
    ax.tick_params(colors='#475569', labelsize=8)
    ax.legend(frameon=True, facecolor='white', edgecolor='none', fontsize=8)
    fig.tight_layout()
    fig.savefig(path_vs, dpi=150)
    plt.close(fig)
    
    # 4. Graphique Trésorerie Cumulée (évolution sur 20 ans)
    capex_total = resultats.get("capex_total", 0.0)
    economies_annuelles = resultats.get("economies_annuelles", 0.0)
    duree_ans = resultats.get("dimensionnement", {}).get("duree_financement", 20)
    
    path_cash = os.path.join(temp_dir, "evolution_tresorerie.png")
    fig, ax = plt.subplots(figsize=(6.2, 2.8), facecolor='white')
    annees = list(range(duree_ans + 1))
    cash_flow = [-capex_total + t * economies_annuelles for t in annees]
    
    ax.plot(annees, cash_flow, color=c_sarcelle, linewidth=2.0, marker='o', markersize=3, label='Trésorerie cumulée')
    ax.axhline(0, color='#C75D3C', linestyle='--', linewidth=1, alpha=0.7)
    
    ax.fill_between(annees, cash_flow, 0, where=[val >= 0 for val in cash_flow], color=c_sarcelle, alpha=0.1, interpolate=True)
    ax.fill_between(annees, cash_flow, 0, where=[val < 0 for val in cash_flow], color='#C75D3C', alpha=0.1, interpolate=True)
    
    ax.set_xlabel('Année', fontsize=8, color='#475569')
    ax.set_ylabel('Gain cumulé (€)', fontsize=8, color='#475569')
    ax.set_title('Évolution de la Trésorerie Cumulée (Payback)', fontsize=10, fontweight='bold', color='#1E3A8A', pad=10)
    ax.grid(True, linestyle='--', alpha=0.5, color='#CBD5E1')
    ax.tick_params(colors='#475569', labelsize=8)
    fig.tight_layout()
    fig.savefig(path_cash, dpi=150)
    plt.close(fig)

    # 5. Graphique de surplus injecté mensuel (revente au réseau)
    # Calcul du surplus : production - consommation (si positif)
    surplus_mensuel = [max(0.0, prod_mensuelle[i] - conso_mensuelle[i]) for i in range(12)]
    path_surplus = os.path.join(temp_dir, "surplus_mensuel.png")
    fig, ax = plt.subplots(figsize=(6.2, 2.8), facecolor='white')
    ax.bar(mois, surplus_mensuel, color='#F59E0B', edgecolor='#D97706', alpha=0.9, width=0.6)
    ax.set_ylabel('Surplus (kWh)', fontsize=8, color='#475569')
    ax.set_title('Estimation de l\'Électricité Injectée au Réseau (kWh)', fontsize=10, fontweight='bold', color='#1E3A8A', pad=10)
    ax.grid(axis='y', linestyle='--', alpha=0.5, color='#CBD5E1')
    ax.tick_params(colors='#475569', labelsize=8)
    fig.tight_layout()
    fig.savefig(path_surplus, dpi=150)
    plt.close(fig)

    return path_pie, path_prod, path_vs, path_cash, path_surplus


def generer_rapport_pdf(resultats: dict, client_info: dict, logo_path: str = None, output_path: str = "rapport.pdf") -> str:
    """
    Genere un rapport PDF d'ingenierie et de faisabilite solaire multi-pages.
    """
    # 0. Chargement des polices personnalisees (silencieux si absentes)
    _enregistrer_polices()

    # 1. Configuration des variables de classe du Canvas
    installateur = client_info.get("installateur_nom", "EcoDim Pro")
    if not installateur or installateur == "EcoDim Expertises":
        installateur = "EcoDim Pro"
    NumberedCanvas.installateur_nom = installateur
    NumberedCanvas.date_etude = client_info.get("date", pd.Timestamp.now().strftime("%d/%m/%Y"))

    # Gestion sécurisée du logo de couverture
    logo_file = None
    if logo_path and _est_image_valide_reportlab(logo_path):
        logo_file = logo_path
    else:
        # Fallbacks vers images par défaut
        fallback_files = [
            "logo/ChatGPT Image Jun 27, 2026, 02_56_31 PM.png",
            "logo/ecodimpro_logo_transparent_v2.svg"
        ]
        for f in fallback_files:
            if _est_image_valide_reportlab(f):
                logo_file = f
                break
    NumberedCanvas.logo_valide_path = logo_file

    # Dossier temporaire pour les graphiques
    temp_dir = tempfile.mkdtemp()

    # 2. Besoins énergétiques
    besoins = {
        "elec_annuel": float(resultats.get("besoin_elec_kwh", 0.0)),
        "ecs_annuel": float(resultats.get("besoin_ecs_kwh", 0.0)),
        "chauffage_annuel": float(resultats.get("besoin_chauffage_kwh", 0.0)),
        "total_annuel": float(resultats.get("besoin_elec_kwh", 0.0) + 
                              resultats.get("besoin_ecs_kwh", 0.0) + 
                              resultats.get("besoin_chauffage_kwh", 0.0))
    }

    # Génération des graphiques
    path_pie, path_prod, path_vs, path_cash, path_surplus = _generer_graphiques_matplotlib(resultats, besoins, temp_dir)

    # Configuration du document ReportLab
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=72
    )

    # Déclaration et configuration des PageTemplates (CoverPage et LaterPages)
    # pour dessiner le fond blanc de couverture (avant les flowables)
    frame_largeur = 487.27  # 595.27 - 108
    frame_hauteur = 715.89  # 841.89 - 126
    frame = Frame(54, 72, frame_largeur, frame_hauteur, id='normal')
    
    cover_template = PageTemplate(id='CoverPage', frames=frame, onPage=draw_cover_background)
    later_template = PageTemplate(id='LaterPages', frames=frame)
    
    doc.addPageTemplates([cover_template, later_template])

    styles = getSampleStyleSheet()

    # -----------------------------------------------------------------------
    # ECHELLE TYPOGRAPHIQUE — charte graphique definitive
    # -----------------------------------------------------------------------
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Normal"],
        fontName=_fb("SpaceGrotesk-Bold"),
        fontSize=26,
        leading=32,
        textColor=HexColor(COULEURS["graphite_fonce"]),
        alignment=1,
        spaceAfter=10
    )

    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName=_fb("SpaceGrotesk-Medium", "Helvetica"),
        fontSize=14,
        leading=18,
        textColor=HexColor(COULEURS["ambre"]),
        alignment=1,
        spaceAfter=20
    )

    h1_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Normal"],
        fontName=_fb("SpaceGrotesk-Bold"),
        fontSize=15,
        leading=19,
        textColor=HexColor(COULEURS["texte_principal"]),
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        "BodyTextCustom",
        parent=styles["Normal"],
        fontName=_f("Inter-Regular"),
        fontSize=10,
        leading=14.5,
        textColor=HexColor(COULEURS["texte_principal"]),
        spaceAfter=5
    )

    # Styles d'encarts pour fond blanc de couverture
    cover_label_style = ParagraphStyle(
        "CoverLabel",
        parent=styles["Normal"],
        fontName=_fb("SpaceGrotesk-Medium", "Helvetica-Bold"),
        fontSize=7.5,
        leading=10,
        textColor=HexColor(COULEURS["texte_attenue"]),
        spaceAfter=3
    )

    cover_val_style = ParagraphStyle(
        "CoverValue",
        parent=styles["Normal"],
        fontName=_fb("SpaceGrotesk-Bold"),
        fontSize=11,
        leading=14,
        textColor=HexColor(COULEURS["texte_principal"])
    )

    cover_sub_val_style = ParagraphStyle(
        "CoverSubValue",
        parent=styles["Normal"],
        fontName=_f("Inter-Regular"),
        fontSize=9,
        leading=13,
        textColor=HexColor("#475569")
    )

    bold_body = ParagraphStyle(
        "BoldBodyText",
        parent=body_style,
        fontName=_f("Inter-Medium", "Helvetica-Bold")
    )

    white_bold_body = ParagraphStyle(
        "WhiteBoldBody",
        parent=body_style,
        fontName=_f("Inter-Medium", "Helvetica-Bold"),
        textColor=HexColor("#FFFFFF")
    )

    warning_style = ParagraphStyle(
        "WarningText",
        parent=body_style,
        fontName=_f("Inter-Regular", "Helvetica-Oblique"),
        textColor=HexColor("#B45309")
    )

    story = []

    # ==========================================
    # PAGE 1 : PAGE DE GARDE DÉDIÉE (FOND BLANC)
    # ==========================================
    story.append(Spacer(1, 2.5 * cm))

    # Logo centré
    if logo_file:
        try:
            logo_img = Image(logo_file, width=4.5 * cm, height=1.6 * cm)
            # Mettre l'image dans une table centrée
            logo_table = Table([[logo_img]], colWidths=[487], hAlign='CENTER')
            logo_table.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                ('TOPPADDING', (0,0), (-1,-1), 0),
            ]))
            story.append(logo_table)
        except Exception:
            story.append(Paragraph(f"<font size=16 color='#E8A33D'><b>{NumberedCanvas.installateur_nom.upper()}</b></font>", ParagraphStyle("LogoText", parent=styles["Normal"], alignment=1)))
    else:
        story.append(Paragraph(f"<font size=16 color='#E8A33D'><b>{NumberedCanvas.installateur_nom.upper()}</b></font>", ParagraphStyle("LogoText", parent=styles["Normal"], alignment=1)))

    story.append(Spacer(1, 0.4 * cm))
    
    # Ligne fine de séparation ambre (#E8A33D) sous le logo
    line_sep_table = Table([[""]], colWidths=[487], rowHeights=[2], hAlign='CENTER')
    line_sep_table.setStyle(TableStyle([
        ('LINEBELOW', (0,0), (-1,-1), 1.5, HexColor("#E8A33D")),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(line_sep_table)
    
    story.append(Spacer(1, 2.8 * cm))
    story.append(Paragraph("Étude de Dimensionnement Solaire", title_style))
    story.append(Paragraph(f"Projet : {client_info.get('nom_etude', 'Installation Solaire')}", subtitle_style))
    
    maison_image_path = client_info.get("maison_image_path")
    if maison_image_path and _est_image_valide_reportlab(maison_image_path):
        try:
            # Calcul du ratio réel de l'image pour respecter les proportions (1:1 ou autre)
            from PIL import Image as PILImage
            with PILImage.open(maison_image_path) as _pil_img:
                _orig_w, _orig_h = _pil_img.size
            _target_w = 10 * cm
            _ratio = _orig_h / _orig_w if _orig_w > 0 else 1.0
            _target_h = min(_target_w * _ratio, 10 * cm)  # plafonné à 10 cm de haut
            maison_img = Image(maison_image_path, width=_target_w, height=_target_h)
            maison_table = Table([[maison_img]], colWidths=[487], hAlign='CENTER')
            maison_table.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                ('TOPPADDING', (0,0), (-1,-1), 0),
            ]))
            story.append(Spacer(1, 0.4 * cm))
            story.append(maison_table)
            story.append(Spacer(1, 0.5 * cm))
        except Exception:
            story.append(Spacer(1, 3.2 * cm))
    else:
        story.append(Spacer(1, 3.2 * cm))

    # Encarts Client & Cabinet côte à côte avec fond plus clair (#F8FAFC)
    client_name = f"{client_info.get('prenom', '')} {client_info.get('nom', '')}".strip() or "Client"
    client_email = client_info.get("email", "Non communiqué")
    client_adresse = client_info.get("adresse", "Non renseignée")
    client_societe = client_info.get("societe", "")
    
    dest_flow = [
        Paragraph("CLIENT", cover_label_style),
        Paragraph(client_name, cover_val_style),
        Paragraph(f"Société : {client_societe}" if client_societe else "", cover_sub_val_style),
        Paragraph(f"Adresse : {client_adresse}", cover_sub_val_style),
        Paragraph(f"Email : {client_email}", cover_sub_val_style),
    ]
    
    install_flow = [
        Paragraph("RÉALISÉ PAR", cover_label_style),
        Paragraph(NumberedCanvas.installateur_nom, cover_val_style),
        Paragraph(f"Date d'étude : {NumberedCanvas.date_etude}", cover_sub_val_style),
        Paragraph("Outil de calcul : EcoDim Pro", cover_sub_val_style),
    ]

    info_cover_data = [
        [dest_flow, install_flow]
    ]
    info_cover_table = Table(info_cover_data, colWidths=[210, 210], hAlign='CENTER')
    info_cover_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), HexColor("#F8FAFC")),
        ('BOX', (0,0), (-1,-1), 0.5, HexColor("#E2E8F0")),
        ('LINEABOVE', (0,0), (0,0), 2.5, HexColor("#E8A33D")),  # Ligne supérieure ambre pour Client
        ('LINEABOVE', (1,0), (1,0), 2.5, HexColor("#3DBFAE")),  # Ligne supérieure sarcelle pour Installateur
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
        ('TOPPADDING', (0,0), (-1,-1), 12),
        ('LEFTPADDING', (0,0), (-1,-1), 14),
        ('RIGHTPADDING', (0,0), (-1,-1), 14),
    ]))
    story.append(info_cover_table)
    # NOTE: "Document confidentiel" est dessiné directement sur le canvas via draw_cover_background
    # pour ne pas déborder du Frame et créer une page orpheline.

    # Dire à ReportLab d'utiliser le template standard (LaterPages) pour la suite
    story.append(NextPageTemplate('LaterPages'))
    # Saut vers la page 2
    story.append(PageBreak())

    # ==========================================
    # PAGE 2 : RÉSUMÉ EXÉCUTIF (PAGE DÉDIÉE)
    # ==========================================
    # Titre de section avec puce coloree reelle (remplace le glyphe Unicode casse)
    _titre_h1 = ParagraphStyle("_TitreH1", parent=styles["Normal"],
        fontName=_fb("SpaceGrotesk-Bold"), fontSize=15, leading=19,
        textColor=HexColor(COULEURS["texte_principal"]),
        spaceBefore=0, spaceAfter=4, keepWithNext=True)
    resume_titre_row = Table(
        [[PuceCouleur(COULEURS["bleu_gris"], taille=9, decalage_y=3),
          Paragraph("Resume Executif", _titre_h1)]],
        colWidths=[16, 471], hAlign="LEFT"
    )
    resume_titre_row.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(resume_titre_row)
    story.append(Spacer(1, 10))

    # Calcul des variables clés pour le Résumé Exécutif
    eq_summary = resultats.get("equipements", {})
    nb_p_sum = eq_summary.get("nb_panneaux", 0)
    p_wc_sum = eq_summary.get("panneau", {}).get("puissance_wc", 425) if eq_summary.get("panneau") else 425
    puissance_instal_kwc = (nb_p_sum * p_wc_sum) / 1000.0

    bilan_pv_sum = resultats.get("bilan_pv", {})
    taux_couv_sol = float(bilan_pv_sum.get("taux_autosuffisance", 0.0))

    capex_tot = float(resultats.get("capex_total", 0.0))
    pb_years = resultats.get("payback_simple", 0.0)
    pb_years_str = f"{pb_years:.1f} ans" if pb_years and pb_years > 0 else "N/A"

    # KPIs : grands chiffres en JetBrains Mono SemiBold 34pt
    _kpi_val = ParagraphStyle("KpiVal", parent=styles["Normal"],
        fontName=_fb("JetBrainsMono-SemiBold"),
        fontSize=34, leading=38,
        textColor=HexColor(COULEURS["texte_principal"]), alignment=1)
    _kpi_lbl = ParagraphStyle("KpiLbl", parent=styles["Normal"],
        fontName=_f("Inter-Regular"),
        fontSize=8, leading=11,
        textColor=HexColor(COULEURS["texte_attenue"]), alignment=1, spaceBefore=5)

    def _kpi_cell(val_txt, lbl_txt):
        return [Paragraph(val_txt, _kpi_val), Paragraph(lbl_txt.upper(), _kpi_lbl)]

    cell_p = _kpi_cell(f"{puissance_instal_kwc:.2f} kWc", "Puissance solaire installee")
    cell_c = _kpi_cell(f"{taux_couv_sol:.1f} %", "Taux d'autosuffisance solaire")
    cell_i = _kpi_cell(f"{capex_tot:,.0f} EUR", "Investissement total (CAPEX)")
    cell_r = _kpi_cell(pb_years_str, "Retour sur investissement")

    t_style_grid = TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), HexColor(COULEURS["fond_encadre"])),
        ('BOX', (0,0), (-1,-1), 0.5, HexColor(COULEURS["bordure_legere"])),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 28),
        ('TOPPADDING', (0,0), (-1,-1), 28),
        ('LEFTPADDING', (0,0), (-1,-1), 18),
        ('RIGHTPADDING', (0,0), (-1,-1), 18),
    ])

    row1_t = Table([[cell_p, cell_c]], colWidths=[238, 238])
    row1_t.setStyle(t_style_grid)
    row1_t.setStyle(TableStyle([
        ('LINEABOVE', (0,0), (0,0), 3.0, HexColor(COULEURS["ambre"])),
        ('LINEABOVE', (1,0), (1,0), 3.0, HexColor(COULEURS["sarcelle"])),
    ]))

    row2_t = Table([[cell_i, cell_r]], colWidths=[238, 238])
    row2_t.setStyle(t_style_grid)
    row2_t.setStyle(TableStyle([
        ('LINEABOVE', (0,0), (0,0), 3.0, HexColor(COULEURS["ambre"])),
        ('LINEABOVE', (1,0), (1,0), 3.0, HexColor(COULEURS["sarcelle"])),
    ]))

    # Phrase résumé AU-DESSUS des données
    story.append(Paragraph(
        f"L'étude technique valide une puissance de raccordement optimale de <b>{puissance_instal_kwc:.2f} kWc</b>. "
        f"Elle permet de couvrir en direct environ <b>{taux_couv_sol:.1f} %</b> de l'ensemble de vos besoins énergétiques annuels "
        f"(électricité, chauffage et ECS), pour un retour sur investissement estimé à <b>{pb_years_str}</b>.",
        body_style
    ))
    story.append(Spacer(1, 16))

    story.append(row1_t)
    story.append(Spacer(1, 18))
    story.append(row2_t)

    # ---- Calculs d'impact écologique — clés réelles du dict resultats_pdf ----
    prod_pv_eco = float(resultats.get("production_pv_annuelle", 0.0))
    co2_evite_kg = prod_pv_eco * 0.040           # 40 g CO2/kWh (facteur mix FR)
    co2_evite_t25 = co2_evite_kg * 25 / 1000    # tonnes sur 25 ans
    economie_annuelle = float(resultats.get("economies_annuelles", 0.0))
    economie_25 = economie_annuelle * 25

    story.append(Spacer(1, 20))
    # Titre Benefices avec puce coloree (sarcelle)
    _ben_titre_style = ParagraphStyle("_BenTitre", parent=styles["Normal"],
        fontName=_fb("SpaceGrotesk-Bold"), fontSize=12, leading=16,
        textColor=HexColor(COULEURS["texte_principal"]),
        spaceBefore=0, spaceAfter=4, keepWithNext=True)
    ben_titre_row = Table(
        [[PuceCouleur(COULEURS["sarcelle"], taille=8, decalage_y=3),
          Paragraph("Benefices Attendus & Impact Ecologique", _ben_titre_style)]],
        colWidths=[16, 471], hAlign="LEFT"
    )
    ben_titre_row.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(ben_titre_row)
    story.append(Spacer(1, 8))

    # Styles des 3 colonnes Benefices
    _col_lbl = ParagraphStyle("_ColLbl2", parent=styles["Normal"],
        fontName=_f("Inter-Medium", "Helvetica-Bold"), fontSize=7.5,
        textColor=HexColor(COULEURS["texte_attenue"]), alignment=1, leading=10)
    _col_val = ParagraphStyle("_ColVal2", parent=styles["Normal"],
        fontName=_fb("JetBrainsMono-SemiBold"), fontSize=18,
        textColor=HexColor(COULEURS["texte_principal"]), alignment=1,
        spaceBefore=6, leading=22)
    _col_sub = ParagraphStyle("_ColSub2", parent=styles["Normal"],
        fontName=_f("Inter-Regular"), fontSize=7.5,
        textColor=HexColor(COULEURS["texte_attenue"]), alignment=1,
        spaceAfter=6, leading=11)

    def _ben_cell(lbl, val, sub):
        return [Paragraph(lbl, _col_lbl), Paragraph(val, _col_val), Paragraph(sub, _col_sub)]

    ben_table = Table(
        [[
            _ben_cell("ECONOMIES FINANCIERES",
                      f"{economie_annuelle:,.0f} EUR/an",
                      f"~{economie_25:,.0f} EUR cumules sur 25 ans"),
            _ben_cell("PRODUCTION SOLAIRE",
                      f"{prod_pv_eco:,.0f} kWh/an",
                      "energie propre generee sur site"),
            _ben_cell("CO2 EVITE",
                      f"{co2_evite_kg:,.0f} kg/an",
                      f"~{co2_evite_t25:.1f} t evitees sur 25 ans"),
        ]],
        colWidths=[162, 162, 162],
        hAlign='CENTER'
    )
    ben_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), HexColor(COULEURS["fond_encadre"])),
        ('LINEABOVE', (0,0), (0,0), 3, HexColor(COULEURS["ambre"])),
        ('LINEABOVE', (1,0), (1,0), 3, HexColor(COULEURS["sarcelle"])),
        ('LINEABOVE', (2,0), (2,0), 3, HexColor(COULEURS["vert_co2"])),
        ('BOX', (0,0), (-1,-1), 0.5, HexColor(COULEURS["bordure_legere"])),
        ('INNERGRID', (0,0), (-1,-1), 0.4, HexColor(COULEURS["bordure_legere"])),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 12),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(ben_table)
    story.append(Spacer(1, 10))

    # Note de bas de section
    _note_s = ParagraphStyle("_Note2", parent=styles["Normal"],
        fontName=_f("Inter-Regular"), fontSize=7.5,
        textColor=HexColor(COULEURS["texte_attenue"]), alignment=1,
        leading=11)
    story.append(Paragraph(
        "Conseil : Decalez vos usages (lave-linge, chauffe-eau) de 10h a 16h pour maximiser l'autoconsommation. "
        "Un systeme EMS ou une batterie peut encore augmenter votre autosuffisance de 5 a 20 %.",
        ParagraphStyle("_Conseil2", parent=styles["Normal"],
            fontName=_f("Inter-Regular"), fontSize=8.5,
            textColor=HexColor(COULEURS["texte_principal"]), leading=13)
    ))
    story.append(Spacer(1, 5))
    story.append(Paragraph(
        "Estimations basees sur le prix de l'electricite et le facteur d'emission du reseau au moment de l'etude — a titre indicatif.",
        _note_s
    ))

    story.append(PageBreak())

    # ==========================================
    # PAGE 3 : BESOINS ÉNERGÉTIQUES & GRAPHIQUE
    # ==========================================
    # Page 3 titre avec puce sarcelle
    _s1_titre = Table(
        [[PuceCouleur(COULEURS["sarcelle"], taille=9, decalage_y=3),
          Paragraph("1. Evaluation des Besoins Energetiques", _titre_h1)]],
        colWidths=[16, 471], hAlign="LEFT"
    )
    _s1_titre.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(_s1_titre)
    
    # Extraction sécurisée de la surface habitable
    dim = resultats.get("dimensionnement", {})
    logement_dict = resultats.get("logement", {})
    surface_m2_val = dim.get("surface_m2") or logement_dict.get("surface_m2") or 0.0

    story.append(Paragraph(
        f"L'analyse porte sur un logement d'une surface habitable de <b>{surface_m2_val:.0f} m²</b>. "
        f"Les besoins de chauffage et d'eau chaude sanitaire (ECS) ont été modélisés à l'aide de la méthode simplifiée 3CL-DPE "
        f"pour la zone climatique configurée.",
        body_style
    ))
    story.append(Spacer(1, 10))

    needs_data = [
        [Paragraph("<b>Poste de Consommation</b>", white_bold_body), Paragraph("<b>Consommation Annuelle</b>", white_bold_body)],
        [Paragraph("Électricité spécifique (Appareils)", body_style), Paragraph(f"{besoins['elec_annuel']:,.1f} kWh/an", body_style)],
        [Paragraph("Eau Chaude Sanitaire (ECS)", body_style), Paragraph(f"{besoins['ecs_annuel']:,.1f} kWh/an", body_style)],
        [Paragraph("Chauffage", body_style), Paragraph(f"{besoins['chauffage_annuel']:,.1f} kWh/an", body_style)],
        [Paragraph("<b>BESOIN TOTAL ESTIMÉ</b>", bold_body), Paragraph(f"<b>{besoins['total_annuel']:,.1f} kWh/an</b>", bold_body)]
    ]
    needs_table = Table(needs_data, colWidths=[250, 237])
    needs_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), HexColor("#14171C")),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, HexColor("#E5E5E5")),
        ('BACKGROUND', (0,-1), (-1,-1), HexColor("#E3F5F2")),  # Sarcelle clair pour le total besoins
    ]))
    story.append(needs_table)
    story.append(Spacer(1, 15))

    # Notes d'audit si disponibles
    if client_info.get("notes"):
        story.append(Paragraph("<b>Notes d'audit & Constats sur site :</b>", bold_body))
        story.append(Paragraph(client_info.get("notes"), body_style))
        story.append(Spacer(1, 10))

    if os.path.exists(path_pie):
        try:
            story.append(KeepTogether([
                Spacer(1, 5),
                Image(path_pie, width=12 * cm, height=10.6 * cm),
                Spacer(1, 10)
            ]))
        except Exception:
            pass

    story.append(PageBreak())

    # ==========================================
    # PAGE 4 : ÉTUDE DE TOITURE & ÉQUIPEMENTS
    # ==========================================
    # Section 2 : Toitures (Puce ambre)
    _s2_titre = Table(
        [[PuceCouleur(COULEURS["ambre"], taille=9, decalage_y=3),
          Paragraph("2. Etude de Toiture &amp; Surfaces Utiles", _titre_h1)]],
        colWidths=[16, 471], hAlign="LEFT"
    )
    _s2_titre.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(_s2_titre)
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Les différents pans de toiture configurés permettent d'évaluer la surface utile disponible "
        "pour la pose de modules solaires, en déduisant les obstacles (velux, cheminées, etc.).",
        body_style
    ))
    story.append(Spacer(1, 8))

    pans = resultats.get("pans_toiture", [])
    if pans:
        roof_rows = [[
            Paragraph("<b>Pan de Toiture</b>", white_bold_body),
            Paragraph("<b>Type</b>", white_bold_body),
            Paragraph("<b>Surf. brute</b>", white_bold_body),
            Paragraph("<b>Obstacles</b>", white_bold_body),
            Paragraph("<b>Surf. utile</b>", white_bold_body),
            Paragraph("<b>Ori. (Azimut)</b>", white_bold_body),
            Paragraph("<b>Incl.</b>", white_bold_body)
        ]]
        for p in pans:
            roof_rows.append([
                Paragraph(p.get("nom", "Pan"), body_style),
                Paragraph(p.get("type", "Pente"), body_style),
                Paragraph(f"{p.get('surface_disponible_m2', 0.0):.1f} m²", body_style),
                Paragraph(f"{p.get('surface_obstacles_m2', 0.0):.1f} m²", body_style),
                Paragraph(f"{p.get('surface_utile_m2', 0.0):.1f} m²", body_style),
                Paragraph(f"{p.get('orientation', 'S')} ({p.get('azimut', 0.0)}°)", body_style),
                Paragraph(f"{p.get('inclinaison', 30)}°", body_style)
            ])
            
        roof_table = Table(roof_rows, colWidths=[90, 85, 60, 60, 60, 90, 42])
        roof_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), HexColor("#14171C")),
            ('LINEBELOW', (0,0), (-1,-1), 0.5, HexColor("#E5E5E5")),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('ALIGN', (2,0), (-1,-1), 'CENTER'),
        ]))
        story.append(roof_table)
    else:
        story.append(Paragraph("Aucun pan de toiture configuré.", warning_style))
    
    story.append(Spacer(1, 15))

    # Section 3 : Matériel (Puce ambre)
    _s3_titre = Table(
        [[PuceCouleur(COULEURS["ambre"], taille=9, decalage_y=3),
          Paragraph("3. Fiche Technique des Equipements Retenus", _titre_h1)]],
        colWidths=[16, 471], hAlign="LEFT"
    )
    _s3_titre.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(_s3_titre)
    story.append(Spacer(1, 5))

    eq = resultats.get("equipements", {})
    panneau_choisi = eq.get("panneau")
    onduleur_choisi = eq.get("onduleur")
    batterie_choisie = eq.get("batterie")
    nb_p = eq.get("nb_panneaux", 0)

    eq_rows = [[
        Paragraph("<b>Équipement</b>", white_bold_body),
        Paragraph("<b>Modèle Sélectionné</b>", white_bold_body),
        Paragraph("<b>Caractéristiques Techniques Clés</b>", white_bold_body)
    ]]
    if panneau_choisi:
        eq_rows.append([
            Paragraph("Panneau Photovoltaïque", body_style),
            Paragraph(panneau_choisi.get("nom", "Standard"), body_style),
            Paragraph(f"Qté : {nb_p} modules | Puissance : {panneau_choisi.get('puissance_wc')} Wc ({nb_p * panneau_choisi.get('puissance_wc') / 1000.0:.2f} kWc)<br/>"
                      f"Dimensions : {panneau_choisi.get('longueur_m')}m × {panneau_choisi.get('largeur_m')}m | Garanties : {panneau_choisi.get('garantie_produit_ans')} ans prod / {panneau_choisi.get('garantie_production_ans')} ans rendement.", body_style)
        ])
    if onduleur_choisi:
        eq_rows.append([
            Paragraph("Onduleur Réseau", body_style),
            Paragraph(onduleur_choisi.get("nom", "Onduleur"), body_style),
            Paragraph(f"Type : {onduleur_choisi.get('type').upper()} | P. nominale : {onduleur_choisi.get('puissance_kw')} kW<br/>"
                      f"Rendement : {onduleur_choisi.get('rendement_pct')}% | Garantie : {onduleur_choisi.get('garantie_ans')} ans.", body_style)
        ])
    if batterie_choisie and float(resultats.get("dimensionnement", {}).get("capacite_bat", 0.0)) > 0.0:
        eq_rows.append([
            Paragraph("Batterie de Stockage", body_style),
            Paragraph(batterie_choisie.get("nom", "Batterie"), body_style),
            Paragraph(f"Capacité : {batterie_choisie.get('capacite_kwh')} kWh | Techno : {batterie_choisie.get('technologie')}<br/>"
                      f"Rendement : {batterie_choisie.get('rendement_pct')}% | Garantie : {batterie_choisie.get('garantie_ans')} ans.", body_style)
        ])
    
    eq_table = Table(eq_rows, colWidths=[120, 140, 227])
    eq_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), HexColor("#14171C")),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, HexColor("#E5E5E5")),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(eq_table)

    # Section 4 : Cablage et Conformite (deplacee sur la page 4 pour eviter toute coupure)
    story.append(Spacer(1, 15))
    _s4_cablage_titre = Table(
        [[PuceCouleur(COULEURS["ambre"], taille=9, decalage_y=3),
          Paragraph("4. Cablage &amp; Conformite Electrique (Norme NF C 15-100)", _titre_h1)]],
        colWidths=[16, 471], hAlign="LEFT"
    )
    _s4_cablage_titre.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(_s4_cablage_titre)
    story.append(Spacer(1, 5))

    cablage = resultats.get("cablage", {})
    if cablage:
        cab_rows = [
            [
                Paragraph("<b>Liaison de cablage</b>", white_bold_body),
                Paragraph("<b>Section cuivre recommandee</b>", white_bold_body),
                Paragraph("<b>Longueur estimee</b>", white_bold_body)
            ],
            [
                Paragraph("Ligne Principale DC (Toit-Onduleur)", body_style),
                Paragraph(f"{cablage.get('section_dc_mm2')} mm2", body_style),
                Paragraph(f"{cablage.get('cable_dc_m')} m", body_style)
            ],
            [
                Paragraph("Ligne Alternative AC (Onduleur-TGBT)", body_style),
                Paragraph("2.5 mm2 (standard)", body_style),
                Paragraph(f"{cablage.get('cable_ac_m')} m", body_style)
            ],
            [
                Paragraph("Liaison de mise a la Terre (Toit-TGBT)", body_style),
                Paragraph("6.0 mm2 (standard)", body_style),
                Paragraph(f"{cablage.get('cable_terre_m')} m", body_style)
            ]
        ]
        cab_table = Table(cab_rows, colWidths=[200, 160, 127])
        cab_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), HexColor("#14171C")),
            ('LINEBELOW', (0,0), (-1,-1), 0.5, HexColor("#E5E5E5")),
            ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(cab_table)
    else:
        story.append(Paragraph("Données de câblage non renseignées.", warning_style))

    # Fin de la page 4 (Conception Technique)
    story.append(PageBreak())

    # ==========================================
    # PAGE 5 : ANALYSE DE PRODUCTION SOLAIRE
    # ==========================================
    # Section 5 : Production PV (Puce ambre)
    _s5_titre = Table(
        [[PuceCouleur(COULEURS["ambre"], taille=9, decalage_y=3),
          Paragraph("5. Analyse de la Production Solaire", _titre_h1)]],
        colWidths=[16, 471], hAlign="LEFT"
    )
    _s5_titre.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(_s5_titre)
    story.append(Spacer(1, 4))

    prod_pv_an = float(resultats.get("production_pv_annuelle", 0.0))

    story.append(Paragraph(
        f"Production photovoltaique annuelle estimee : <b>{prod_pv_an:,.0f} kWh/an</b>. "
        "Les graphiques ci-dessous detaillent la repartition mensuelle de la production solaire "
        "ainsi que la comparaison directe avec votre profil de consommation globale.",
        body_style
    ))
    story.append(Spacer(1, 5))

    if os.path.exists(path_prod):
        try:
            story.append(Image(path_prod, width=15 * cm, height=6.5 * cm))
            story.append(Spacer(1, 10))
        except Exception:
            pass

    if os.path.exists(path_vs):
        try:
            story.append(Image(path_vs, width=15 * cm, height=6.5 * cm))
            story.append(Spacer(1, 10))
        except Exception:
            pass

    # Fin de la page 5 (Production Solaire)
    story.append(PageBreak())

    # ==========================================
    # PAGE 6 : INJECTION RÉSEAU & VALORISATION DES SURPLUS
    # ==========================================
    # Section 6 : Injection Reseau (Puce sarcelle)
    _s6_inj_titre = Table(
        [[PuceCouleur(COULEURS["sarcelle"], taille=9, decalage_y=3),
          Paragraph("6. Injection Reseau &amp; Valorisation des Surplus", _titre_h1)]],
        colWidths=[16, 471], hAlign="LEFT"
    )
    _s6_inj_titre.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(_s6_inj_titre)
    story.append(Spacer(1, 4))

    bilan_pv = resultats.get("bilan_pv", {})
    auto_kwh = float(bilan_pv.get("energie_autoconsommee_kwh") or bilan_pv.get("autoconsommation_directe") or 0.0)
    surplus_kwh = float(bilan_pv.get("surplus_kwh") or bilan_pv.get("surplus_injecte") or 0.0)
    
    pct_auto = (auto_kwh / prod_pv_an * 100.0) if prod_pv_an > 0 else 0.0
    pct_surplus = (surplus_kwh / prod_pv_an * 100.0) if prod_pv_an > 0 else 0.0
    
    t_rachat = float(resultats.get("dimensionnement", {}).get("tarif_rachat", 0.13))
    p_res = float(resultats.get("dimensionnement", {}).get("prix_reseau", 0.2516))
    
    revenu_surplus = surplus_kwh * t_rachat
    eco_directe = auto_kwh * p_res
    total_valeur = eco_directe + revenu_surplus

    # Texte explicatif indiquant le rôle de la batterie et de l'injection
    has_bat = float(resultats.get("dimensionnement", {}).get("capacite_bat", 0.0)) > 0.0
    if has_bat:
        contexte_bat = (
            "Apres alimentation en direct de la maison et chargement des batteries de stockage, "
            "le surplus de production d'electricite est retransmis sur le reseau national."
        )
    else:
        contexte_bat = (
            "Apres alimentation en direct des appareils de la maison, le surplus de production d'electricite "
            "non consomme instantanement est reinjecte directement sur le reseau national."
        )

    story.append(Paragraph(
        f"{contexte_bat} Cette injection est valorisee au tarif de rachat en vigueur de <b>{t_rachat:.4f} EUR/kWh</b>, "
        "ce qui constitue un gain financier non negligeable.",
        body_style
    ))
    story.append(Spacer(1, 5))

    if os.path.exists(path_surplus):
        try:
            story.append(Image(path_surplus, width=15 * cm, height=6.5 * cm))
            story.append(Spacer(1, 10))
        except Exception:
            pass

    # Tableau recapitulatif detaille avec Valorisation Financiere
    val_rows = [
        [
            Paragraph("<b>Flux d'Energie Solaire</b>", white_bold_body),
            Paragraph("<b>Quantite</b>", white_bold_body),
            Paragraph("<b>Part (%)</b>", white_bold_body),
            Paragraph("<b>Valorisation financiere</b>", white_bold_body)
        ],
        [
            Paragraph("Autoconsommation (Directe + Batterie)", body_style),
            Paragraph(f"{auto_kwh:,.0f} kWh/an", body_style),
            Paragraph(f"{pct_auto:.1f} %", body_style),
            Paragraph(f"Economie : {eco_directe:,.2f} EUR/an", body_style)
        ],
        [
            Paragraph("Surplus injecte (Revente au reseau)", body_style),
            Paragraph(f"{surplus_kwh:,.0f} kWh/an", body_style),
            Paragraph(f"{pct_surplus:.1f} %", body_style),
            Paragraph(f"Revenu : {revenu_surplus:,.2f} EUR/an (Tarif : {t_rachat:.4f} EUR/kWh)", body_style)
        ],
        [
            Paragraph("<b>PRODUCTION ANNUELLE TOTALE</b>", bold_body),
            Paragraph(f"<b>{prod_pv_an:,.0f} kWh/an</b>", bold_body),
            Paragraph("<b>100 %</b>", bold_body),
            Paragraph(f"<b>Gains totaux : {total_valeur:,.2f} EUR/an</b>", bold_body)
        ]
    ]

    val_table = Table(val_rows, colWidths=[180, 85, 65, 157])
    val_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), HexColor(COULEURS["graphite_fonce"])),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, HexColor(COULEURS["bordure_legere"])),
        ('ALIGN', (1,0), (2,-1), 'CENTER'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BACKGROUND', (0,2), (-1,2), HexColor(COULEURS["fond_surbrillance_ambre"])), # Ligne revente surbrillance
        ('BACKGROUND', (0,3), (-1,3), HexColor(COULEURS["fond_surbrillance_sarcelle"])), # Ligne total surbrillance
    ]))
    story.append(val_table)
    story.append(Spacer(1, 10))

    # Placer la section economique dans sa propre page pour eviter toute coupure
    story.append(PageBreak())

    # ==========================================
    # PAGE 7 : BUDGET, RENTABILITÉ & ROI
    # ==========================================
    # Section 7 : Analyse Economique (Puce bleu_gris)
    _s7_eco_titre = Table(
        [[PuceCouleur(COULEURS["bleu_gris"], taille=9, decalage_y=3),
          Paragraph("7. Analyse Economique &amp; ROI", _titre_h1)]],
        colWidths=[16, 471], hAlign="LEFT"
    )
    _s7_eco_titre.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(_s7_eco_titre)
    story.append(Spacer(1, 4))
    
    eco_fin = resultats.get("dimensionnement", {})
    capex_details = resultats.get("capex_details", {})
    pb = resultats.get("payback_simple", float("inf"))
    pb_str = f"{pb:.1f} ans" if pb != float("inf") else "Indéterminé"

    story.append(Paragraph(
        f"L'étude financière s'établit sur une durée d'exploitation de <b>{eco_fin.get('duree_financement', 20)} ans</b> "
        f"avec un taux d'actualisation de {eco_fin.get('taux_act', 0.03):.1%}.",
        body_style
    ))
    story.append(Spacer(1, 8))

    # Tableau économique corrigé
    eco_rows = [
        [
            Paragraph("<b>Poste Budgétaire / Financier</b>", white_bold_body),
            Paragraph("<b>Détail du Poste</b>", white_bold_body),
            Paragraph("<b>Montant</b>", white_bold_body)
        ],
        [
            Paragraph("Matériel Photovoltaïque (Panneaux)", body_style),
            Paragraph(f"{nb_p} panneaux installés", body_style),
            Paragraph(f"{capex_details.get('panneaux_fact', 0.0):,.2f} €", body_style)
        ],
        [
            Paragraph("Onduleur Réseau", body_style),
            Paragraph(eq.get('onduleur', {}).get('nom', 'Standard') if eq.get('onduleur') else 'Standard', body_style),
            Paragraph(f"{capex_details.get('onduleur_fact', 0.0):,.2f} €", body_style)
        ],
        [
            Paragraph("Forfait Câblage, Structures & Pose", body_style),
            Paragraph("Structures rails et pose toiture", body_style),
            Paragraph(f"{capex_details.get('pose_fact', 0.0):,.2f} €", body_style)
        ],
        [
            Paragraph("Solaire Thermique (Matériel & Pose)", body_style),
            Paragraph("Capteurs thermiques et ballon ECS", body_style),
            Paragraph(f"{capex_details.get('thermique_fact', 0.0):,.2f} €", body_style)
        ],
        [
            Paragraph("Stockage Batterie (Matériel)", body_style),
            Paragraph(eq.get('batterie', {}).get('nom', 'Aucune') if eq.get('batterie') else 'Aucune', body_style),
            Paragraph(f"{capex_details.get('batterie_fact', 0.0):,.2f} €", body_style)
        ],
        [
            Paragraph("<b>INVESTISSEMENT TOTAL INITIAL (CAPEX)</b>", bold_body),
            Paragraph("", body_style),
            Paragraph(f"<b>{resultats.get('capex_total', 0.0):,.2f} €</b>", bold_body)
        ],
        [
            Paragraph("Économies & gains annuels (Electricité + Thermique)", body_style),
            Paragraph("Appoint évité et autoconsommation", body_style),
            Paragraph(f"{resultats.get('economies_annuelles', 0.0):,.2f} € / an", body_style)
        ],
        [
            Paragraph("<b>Temps de retour sur investissement (Payback)</b>", bold_body),
            Paragraph("", body_style),
            Paragraph(f"<b>{pb_str}</b>", bold_body)
        ],
        [
            Paragraph("<b>Valeur Actuelle Nette (VAN) à 20 ans</b>", bold_body),
            Paragraph("", body_style),
            Paragraph(f"<b>{resultats.get('van', 0.0):,.2f} €</b>", bold_body)
        ]
    ]
    
    eco_table = Table(eco_rows, colWidths=[180, 180, 127])
    eco_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), HexColor("#14171C")),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, HexColor("#E5E5E5")),
        ('ALIGN', (2,0), (2,-1), 'RIGHT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('SPAN', (0,6), (1,6)),
        ('SPAN', (0,8), (1,8)),
        ('SPAN', (0,9), (1,9)),
        ('BACKGROUND', (0,6), (-1,6), HexColor("#FBF0DC")),  # Ambre clair
        ('BACKGROUND', (0,8), (-1,-1), HexColor("#E3F5F2")),  # Sarcelle clair pour le ROI / VAN
    ]))
    story.append(eco_table)
    
    # =========================================================================
    # TABLEAU COMPARATIF DES 3 SCÉNARIOS (Les 3 Scénarios d'Étude)
    # =========================================================================
    story.append(Spacer(1, 12))
    story.append(Paragraph("<b>Comparatif des Scénarios de Dimensionnement</b>", bold_body))
    story.append(Spacer(1, 5))
    
    p_res = eco_fin.get("prix_reseau", 0.2516)
    t_rachat = eco_fin.get("tarif_rachat", 0.13)
    facture_reseau_seul = besoins["total_annuel"] * p_res
    
    # Scénario 2 (PV Seul)
    capex_pv_seul = capex_details.get("panneaux_fact", 0.0) + capex_details.get("onduleur_fact", 0.0) + capex_details.get("pose_fact", 0.0)
    prod_pv_an = float(resultats.get("production_pv_annuelle", 0.0))
    auto_kwh_pv = prod_pv_an * 0.35
    surplus_kwh_pv = max(0.0, prod_pv_an - auto_kwh_pv)
    economies_pv_seul = (auto_kwh_pv * p_res) + (surplus_kwh_pv * t_rachat)
    facture_pv_seul = max(0.0, facture_reseau_seul - economies_pv_seul)
    pb_pv_seul_val = capex_pv_seul / economies_pv_seul if economies_pv_seul > 0 else 0.0
    pb_pv_seul_str = f"{pb_pv_seul_val:.1f} ans" if pb_pv_seul_val > 0 else "—"
    
    # Scénario 3 (Installation complète proposée)
    economies_totales = resultats.get("economies_annuelles", 0.0)
    facture_complete = max(0.0, facture_reseau_seul - economies_totales)

    scenarios_rows = [
        [
            Paragraph("<b>Scénario d'Étude</b>", white_bold_body),
            Paragraph("<b>CAPEX Initial</b>", white_bold_body),
            Paragraph("<b>Facture Annuelle</b>", white_bold_body),
            Paragraph("<b>Économie / an</b>", white_bold_body),
            Paragraph("<b>Temps de Retour</b>", white_bold_body)
        ],
        [
            Paragraph("1. Raccordement Réseau (Réf)", body_style),
            Paragraph("0.00 €", body_style),
            Paragraph(f"{facture_reseau_seul:,.2f} €", body_style),
            Paragraph("0.00 €", body_style),
            Paragraph("—", body_style)
        ],
        [
            Paragraph("2. Autoconsommation PV simple", body_style),
            Paragraph(f"{capex_pv_seul:,.2f} €", body_style),
            Paragraph(f"{facture_pv_seul:,.2f} €", body_style),
            Paragraph(f"{economies_pv_seul:,.2f} €", body_style),
            Paragraph(pb_pv_seul_str, body_style)
        ],
        [
            Paragraph("3. Projet complet proposé", bold_body),
            Paragraph(f"{resultats.get('capex_total', 0.0):,.2f} €", bold_body),
            Paragraph(f"{facture_complete:,.2f} €", bold_body),
            Paragraph(f"{economies_totales:,.2f} €", bold_body),
            Paragraph(pb_str, bold_body)
        ]
    ]
    
    scenarios_table = Table(scenarios_rows, colWidths=[175, 80, 85, 80, 67])
    scenarios_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), HexColor("#14171C")),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, HexColor("#E5E5E5")),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BACKGROUND', (0,3), (-1,3), HexColor("#E3F5F2")),  # Sarcelle clair pour le projet proposé
    ]))
    story.append(scenarios_table)
    
    story.append(Spacer(1, 10))

    if os.path.exists(path_cash):
        try:
            story.append(Image(path_cash, width=15 * cm, height=5.0 * cm))
            story.append(Spacer(1, 10))
        except Exception:
            pass

    # Placer la section hypotheses dans sa propre page pour eviter toute coupure
    story.append(PageBreak())

    # Section 8 : Hypotheses & Limites (Puce bleu_gris)
    _s8_titre = Table(
        [[PuceCouleur(COULEURS["bleu_gris"], taille=9, decalage_y=3),
          Paragraph("8. Hypotheses, Methodologie et Limites", _titre_h1)]],
        colWidths=[16, 471], hAlign="LEFT"
    )
    _s8_titre.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(_s8_titre)
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Ce rapport constitue un outil d'aide à la décision technique et financière. Les calculs reposent sur les hypothèses suivantes :<br/>"
        "• L'ensoleillement est simulé à partir des données historiques de l'API PVGIS v5.2 pour une année météorologique type.<br/>"
        "• Les besoins de chauffage sont calculés par la méthode simplifiée 3CL-DPE réglementaire (Degrés-Heures base 14°C), sans prise en compte des apports solaires passifs ou de l'inertie fine du bâtiment.<br/>"
        "• La section de câblage cuivre est estimée d'après la norme NF C 15-100 avec une chute de tension maximale DC de 3%.<br/>"
        "• Les tarifs d'électricité réseau et de rachat de surplus sont supposés constants sur toute la durée de l'étude.",
        body_style
    ))
    
    if resultats.get("disclaimer_dpe"):
        story.append(Spacer(1, 8))
        story.append(Paragraph(resultats.get("disclaimer_dpe"), warning_style))

    # Compilation du PDF (avec les templates CoverPage et LaterPages déclarés)
    doc.build(story, canvasmaker=NumberedCanvas)

    # Nettoyage des fichiers temporaires
    try:
        shutil.rmtree(temp_dir)
    except Exception:
        pass

    return os.path.abspath(output_path)
