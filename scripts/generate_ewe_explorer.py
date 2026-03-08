#!/usr/bin/env python3
"""
Iroko Ewé Explorer — Static Site Generator v2
Language toggle = interface language (labels, prose, notes)
Plant names = always fully displayed, organized by language
"""

import argparse, html, os, shutil
from pathlib import Path
from rdflib import Graph, Namespace, RDF, URIRef
from rdflib.namespace import SKOS, DCTERMS

IROKO = Namespace("https://ontology.irokosociety.org/iroko#")
DWC   = Namespace("http://rs.tdwg.org/dwc/terms/")

ACCESS_LABEL = {
    "access-public-unrestricted":     ("Public",           "access-public"),
    "access-public-no-amplification": ("No Amplification", "access-public"),
    "access-community-only":          ("Community Only",   "access-community"),
    "access-initiated-only":          ("Initiated Only",   "access-initiated"),
    "access-initiated-elder":         ("Elder Initiated",  "access-initiated"),
    "access-no-access":               ("No Access",        "access-none"),
}

RITUAL_LABEL = {
    "ritual-cosmological-symbolic":    "Cosmological / Symbolic",
    "ritual-healing-restoration":      "Healing & Restoration",
    "ritual-invocation-communication": "Invocation & Communication",
    "ritual-offering-devotion":        "Offering & Devotion",
    "ritual-protection-boundary":      "Protection & Boundary",
    "ritual-purification-cleansing":   "Purification & Cleansing",
    "ritual-rites-of-transition":      "Rites of Transition",
}

MEDICINAL_LABEL = {
    "medicinal-digestive-support":   "Digestive Support",
    "medicinal-general-tonic":       "General Tonic",
    "medicinal-respiratory-support": "Respiratory Support",
    "medicinal-skin-topical":        "Skin & Topical",
}

# ── Interface string translations ─────────────────────────────────────────────
# Keys: en, es, fr, yo, pt
UI = {
    "names_by_language":     {"en":"Names by Language",   "es":"Nombres por Idioma",     "fr":"Noms par Langue",       "yo":"Àwọn Orúkọ",           "pt":"Nomes por Idioma"},
    "english":               {"en":"English",             "es":"Inglés",                 "fr":"Anglais",               "yo":"Èdè Gẹ̀ẹ́sì",           "pt":"Inglês"},
    "yoruba":                {"en":"Yoruba",              "es":"Yoruba",                 "fr":"Yoruba",                "yo":"Èdè Yorùbá",            "pt":"Yoruba"},
    "spanish_cuban":         {"en":"Spanish / Cuban",     "es":"Español / Cubano",       "fr":"Espagnol / Cubain",     "yo":"Èdè Spéénì / Kúbà",    "pt":"Espanhol / Cubano"},
    "lucumi":                {"en":"Lucumí Names",        "es":"Nombres Lucumí",         "fr":"Noms Lucumí",           "yo":"Àwọn Orúkọ Lucumí",    "pt":"Nomes Lucumí"},
    "pt_names":              {"en":"Brazilian Portuguese","es":"Portugués Brasileño",    "fr":"Portugais Brésilien",   "yo":"Èdè Potogí",           "pt":"Português Brasileiro"},
    "pt_pending":            {"en":"Brazilian Portuguese names pending — forthcoming manuscript.",
                              "es":"Nombres en portugués pendientes — manuscrito en preparación.",
                              "fr":"Noms en portugais en attente — manuscrit à venir.",
                              "yo":"Àwọn orúkọ Potogí ń dìde — ìwé àfọwọkọ tí ń bọ̀.",
                              "pt":"Nomes em português pendentes — manuscrito vindouro."},
    "regional_vernacular":   {"en":"Regional & Vernacular Names","es":"Nombres Regionales y Vernáculos","fr":"Noms Régionaux et Vernaculaires","yo":"Àwọn Orúkọ Ẹkùn","pt":"Nomes Regionais e Vernáculos"},
    "other_regional":        {"en":"Other Regional Names","es":"Otros Nombres Regionales","fr":"Autres Noms Régionaux","yo":"Àwọn Orúkọ Mìíràn","pt":"Outros Nomes Regionais"},
    "none_recorded":         {"en":"None recorded",      "es":"Ninguno registrado",     "fr":"Aucun enregistré",      "yo":"Kò sí tí a kọ",        "pt":"Nenhum registrado"},
    "sacred_knowledge":      {"en":"Sacred Knowledge",   "es":"Conocimiento Sagrado",   "fr":"Savoir Sacré",          "yo":"Ìmọ̀ Mímọ́",            "pt":"Conhecimento Sagrado"},
    "ritual_use":            {"en":"Ritual Use",         "es":"Uso Ritual",             "fr":"Usage Rituel",          "yo":"Lílo Àṣà",              "pt":"Uso Ritual"},
    "ritual_notes":          {"en":"Ritual Notes",       "es":"Notas Rituales",         "fr":"Notes Rituelles",       "yo":"Àwọn Àkọsílẹ̀ Àṣà",   "pt":"Notas Rituais"},
    "classification":        {"en":"Classification",     "es":"Clasificación",          "fr":"Classification",        "yo":"Ìpín",                 "pt":"Classificação"},
    "medicinal_use":         {"en":"Medicinal Use",      "es":"Uso Medicinal",          "fr":"Usage Médicinal",       "yo":"Lílo Ìwòsàn",          "pt":"Uso Medicinal"},
    "scientific_name":       {"en":"Scientific Name",    "es":"Nombre Científico",      "fr":"Nom Scientifique",      "yo":"Orúkọ Sáyẹ́ǹsì",       "pt":"Nome Científico"},
    "iroko_uri":             {"en":"Iroko URI",          "es":"URI de Iroko",           "fr":"URI Iroko",             "yo":"Iroko URI",             "pt":"URI Iroko"},
    "vocabulary":            {"en":"Vocabulary",         "es":"Vocabulario",            "fr":"Vocabulaire",           "yo":"Àwọn Ọ̀rọ̀",           "pt":"Vocabulário"},
    "all_plants":            {"en":"All Plants",         "es":"Todas las Plantas",      "fr":"Toutes les Plantes",   "yo":"Gbogbo Ewé",           "pt":"Todas as Plantas"},
    "prev_plant":            {"en":"Previous",           "es":"Anterior",               "fr":"Précédent",             "yo":"Tẹ́lẹ̀",                "pt":"Anterior"},
    "next_plant":            {"en":"Next",               "es":"Siguiente",              "fr":"Suivant",               "yo":"Tókàn",                "pt":"Próximo"},
    "search_placeholder":    {"en":"Search by name, scientific name, or vernacular…",
                              "es":"Buscar por nombre, nombre científico o vernáculo…",
                              "fr":"Rechercher par nom, nom scientifique ou vernaculaire…",
                              "yo":"Wá nínú àwọn orúkọ…",
                              "pt":"Pesquisar por nome, nome científico ou vernáculo…"},
    "plants_label":          {"en":"plants",             "es":"plantas",                "fr":"plantes",               "yo":"ewé",                  "pt":"plantas"},
    "access_info":           {"en":"Access",             "es":"Acceso",                 "fr":"Accès",                 "yo":"Àyèwọ̀lé",             "pt":"Acesso"},
    "name_collision_note":   {"en":"Name collision recorded","es":"Colisión de nombre","fr":"Collision de nom",      "yo":"Ìforúkọwé orúkọ",      "pt":"Colisão de nome"},
    "about_title":           {"en":"About the Ewé Database",
                              "es":"Acerca de la Base de Datos Ewé",
                              "fr":"À propos de la Base de Données Ewé",
                              "yo":"Nípa Àkójọpọ̀ Ewé",
                              "pt":"Sobre a Base de Dados Ewé"},
    "about_body":            {
        "en": "The Ewé Database provides a public interface for plant records structured using the Iroko Framework. Botanical, linguistic, and vernacular knowledge is fully discoverable. Knowledge governed by community authorization — Lucumí names, ritual use, and sacred notes — is shown with explicit access tier indicators, not suppressed. This environment demonstrates Sacred Metadata governance: the CARE Principles (Collective Benefit, Authority to Control, Responsibility, Ethics) applied to Afro-Atlantic ethnobotanical knowledge.",
        "es": "La Base de Datos Ewé ofrece una interfaz pública para registros botánicos estructurados mediante el Iroko Framework. El conocimiento botánico, lingüístico y vernáculo es plenamente accesible. El conocimiento regido por autorización comunitaria — nombres lucumí, uso ritual y notas sagradas — se muestra con indicadores explícitos de nivel de acceso, sin suprimirse. Este entorno demuestra la gobernanza de Metadatos Sagrados: los Principios CARE aplicados al conocimiento etnobotánico afroatlántico.",
        "fr": "La Base de Données Ewé fournit une interface publique pour les notices botaniques structurées par le Cadre Iroko. La connaissance botanique, linguistique et vernaculaire est entièrement accessible. Les savoirs régis par autorisation communautaire — noms lucumí, usages rituels et notes sacrées — sont affichés avec des indicateurs explicites de niveau d'accès, sans être supprimés. Cet environnement illustre la gouvernance des Métadonnées Sacrées : les Principes CARE appliqués au savoir ethnobotanique afro-atlantique.",
        "yo": "Àkójọpọ̀ Ewé pèsè ọ̀nà gbangba fún àwọn àkọsílẹ̀ ọgbìn tí a ṣètò pẹ̀lú Iroko Framework. Ìmọ̀ ìjìnlẹ̀ ewéko, èdè, àti àwọn orúkọ ẹkùn jẹ́ ṣíṣí gbangba. Ìmọ̀ tí àwùjọ ń ṣàkóso — àwọn orúkọ Lucumí, lílo àṣà, àti àkọsílẹ̀ mímọ́ — wà pẹ̀lú àmì ìpele àyèwọ̀lé gbangba. Ipò yìí ń fi ìṣàkóso Sacred Metadata hàn: àwọn Ìlànà CARE tí a lo sí ìmọ̀ ewéko Afro-Atlantic.",
        "pt": "A Base de Dados Ewé oferece uma interface pública para registros botânicos estruturados pelo Iroko Framework. O conhecimento botânico, linguístico e vernáculo é totalmente acessível. O conhecimento regido por autorização comunitária — nomes lucumí, uso ritual e notas sagradas — é exibido com indicadores explícitos de nível de acesso, sem supressão. Este ambiente demonstra a governança de Metadados Sagrados: os Princípios CARE aplicados ao conhecimento etnobotânico afro-atlântico.",
    },
    "footer_site":           {"en":"Iroko Historical Society · Ewé Database",
                              "es":"Sociedad Histórica Iroko · Base de Datos Ewé",
                              "fr":"Société Historique Iroko · Base de Données Ewé",
                              "yo":"Àwùjọ Ìtàn Iroko · Àkójọpọ̀ Ewé",
                              "pt":"Sociedade Histórica Iroko · Base de Dados Ewé"},
    "footer_desc":           {"en":"Postcustodial Digital Archives for Afro-Atlantic Cultural Materials",
                              "es":"Archivos Digitales Postcustodiales para Materiales Culturales Afroatlánticos",
                              "fr":"Archives Numériques Post-custodiales pour Matériaux Culturels Afro-atlantiques",
                              "yo":"Àwọn Àkọsílẹ̀ Ìròyìn Àfikà-Adágún-Atlantiki",
                              "pt":"Arquivos Digitais Pós-custodiais para Materiais Culturais Afro-Atlânticos"},
}

H = lambda s: html.escape(str(s), quote=True)

def ui_attrs(key):
    """Return data-ui attributes for all 5 languages."""
    d = UI.get(key, {})
    return " ".join(f'data-{lang}="{H(v)}"' for lang, v in d.items())

def ui_span(key, default_lang="en"):
    """Inline <span data-ui> element — text swaps via JS."""
    d = UI.get(key, {})
    default = d.get(default_lang, key)
    attrs = " ".join(f'data-{lang}="{H(v)}"' for lang, v in d.items())
    return f'<span class="ui" {attrs}>{H(default)}</span>'

def local(uri):
    s = str(uri)
    return s.split("#")[-1] if "#" in s else s.split("/")[-1]

def extract_plants(g):
    plants = []
    for subj in g.subjects(RDF.type, IROKO.EwePlantRecord):
        p = {"uri": str(subj), "id": None, "scientific": None,
             "prefLabel": None,
             "en": [], "yo": [], "es": [], "pt": [],
             "lucumi": [], "other": [],
             "ritual_use": None, "medicinal_use": None,
             "ritual_notes": None, "access_key": None,
             "name_collision": False}

        for o in g.objects(subj, DCTERMS.identifier):
            if isinstance(o, URIRef): continue
            s = str(o)
            if s.startswith("Plant"): p["id"] = s

        p["scientific"] = str(g.value(subj, DWC.scientificName) or "")
        pref = g.value(subj, SKOS.prefLabel)
        p["prefLabel"] = str(pref) if pref else ""

        for o in g.objects(subj, SKOS.altLabel):
            lang = getattr(o, "language", None)
            val  = str(o)
            if lang == "en":              p["en"].append(val)
            elif lang == "yo":            p["yo"].append(val)
            elif lang in ("es", "sp"):
                if val not in p["es"]:   p["es"].append(val)
            elif lang in ("pt-BR","pt"): p["pt"].append(val)
            elif lang == "x-lucumi":     p["lucumi"].append(val)
            else:                        p["other"].append(val)

        ru = g.value(subj, IROKO.ritualUse)
        if ru: p["ritual_use"] = local(str(ru))
        mu = g.value(subj, IROKO.medicinalUse)
        if mu: p["medicinal_use"] = local(str(mu))
        rn = g.value(subj, IROKO.ritualNotes)
        if rn: p["ritual_notes"] = str(rn)
        al = g.value(subj, IROKO.accessLevel)
        if al: p["access_key"] = local(str(al))
        nc = g.value(subj, IROKO.nameCollision)
        if nc: p["name_collision"] = str(nc).lower() in ("yes","true","1")

        plants.append(p)
    plants.sort(key=lambda x: x["id"] or "")
    return plants

def access_badge(key, size=""):
    if not key or key not in ACCESS_LABEL: return ""
    label, css = ACCESS_LABEL[key]
    cls = f"access-badge {css}" + (f" {size}" if size else "")
    return f'<span class="{cls}">{H(label)}</span>'

def gated_value(value_html, access_key):
    """Show value if public-unrestricted, else show access badge."""
    if access_key in (None, "access-public-unrestricted"):
        return value_html
    return access_badge(access_key, "access-badge-lg")

# ── CSS ───────────────────────────────────────────────────────────────────────
CSS = """\
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400;1,500&family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500&display=swap');

:root {
  --ink:         #1c2118;
  --ink-mid:     #3d4a36;
  --ink-soft:    #6b7a62;
  --paper:       #f7f4ed;
  --paper-warm:  #ede9df;
  --paper-deep:  #e4dfd2;
  --rule:        rgba(28,33,24,.12);
  --rule-strong: rgba(28,33,24,.25);
  --green:       #2e4a1e;
  --green-mid:   #4a7035;
  --green-light: #e8f0e2;
  --terracotta:  #8b3a1a;
  --gold:        #a07830;
  --gold-light:  #f5edd8;
  --purple:      #5c3d8f;
  --navy:        #1a4a5e;
  --mono: 'DM Mono', monospace;
  --sans: 'DM Sans', sans-serif;
  --serif:'Cormorant Garamond', Georgia, serif;
}

*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
html{font-size:16px;scroll-behavior:smooth;}
body{background:var(--paper);color:var(--ink);font-family:var(--sans);font-weight:300;line-height:1.65;}
a{color:var(--green);text-decoration:none;}
a:hover{color:var(--terracotta);}

.page-wrap{max-width:1080px;margin:0 auto;padding:0 2rem;}

/* ── Top bar ── */
.top-bar{border-bottom:1px solid var(--rule);padding:.7rem 2rem;display:flex;justify-content:space-between;align-items:center;gap:1rem;flex-wrap:wrap;}
.top-bar-id{font-family:var(--mono);font-size:.68rem;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-soft);}
.top-bar-links{display:flex;gap:1.5rem;}
.top-bar-links a{font-family:var(--mono);font-size:.68rem;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-soft);}
.top-bar-links a:hover{color:var(--green);}

/* ── Lang toggle ── */
.lang-toggle{display:flex;gap:0;border:1px solid var(--rule-strong);border-radius:3px;overflow:hidden;width:fit-content;}
.lang-btn{font-family:var(--mono);font-size:.62rem;letter-spacing:.1em;text-transform:uppercase;padding:.3em .9em;background:var(--paper);color:var(--ink-soft);border:none;border-right:1px solid var(--rule-strong);cursor:pointer;transition:all .12s;user-select:none;}
.lang-btn:last-child{border-right:none;}
.lang-btn:hover{background:var(--paper-warm);color:var(--ink);}
.lang-btn.active{background:var(--green);color:#fff;}
.lang-btn.disabled{opacity:.35;pointer-events:none;}

/* ── Breadcrumb ── */
.breadcrumb{font-family:var(--mono);font-size:.7rem;letter-spacing:.08em;color:var(--ink-soft);padding:1rem 0 0;}
.breadcrumb a{color:var(--ink-soft);}
.breadcrumb a:hover{color:var(--green);}
.breadcrumb span{margin:0 .4em;opacity:.5;}

/* ── Explorer hero (index) ── */
.explorer-hero{padding:3rem 0 2.5rem;border-bottom:2px solid var(--ink);}
.hero-inner{display:grid;grid-template-columns:auto 1fr auto;gap:2.5rem;align-items:start;}
.hero-logo img{width:88px;height:auto;display:block;}
.explorer-eyebrow{font-family:var(--mono);font-size:.68rem;letter-spacing:.18em;text-transform:uppercase;color:var(--green-mid);margin-bottom:.5rem;}
.explorer-title{font-family:var(--serif);font-size:clamp(1.8rem,3.5vw,2.8rem);font-weight:600;color:var(--green);line-height:1.05;}
.explorer-title em{font-style:italic;color:var(--terracotta);}
.explorer-sub{font-size:.88rem;color:var(--ink-mid);margin-top:.75rem;max-width:58ch;line-height:1.65;}

/* About block */
.about-block{border-left:3px solid var(--green);padding:.85rem 1.1rem;background:var(--green-light);border-radius:0 3px 3px 0;margin:2rem 0 0;}
.about-block-title{font-family:var(--mono);font-size:.65rem;letter-spacing:.15em;text-transform:uppercase;color:var(--green);margin-bottom:.5rem;}
.about-block p{font-size:.84rem;color:var(--ink-mid);line-height:1.65;}

/* ── Search + filter ── */
.toolbar{margin:2rem 0 1rem;display:flex;gap:.75rem;align-items:center;flex-wrap:wrap;}
.search-input{flex:1;min-width:220px;font-family:var(--sans);font-size:.88rem;padding:.5em 1em;border:1px solid var(--rule-strong);border-radius:3px;background:var(--paper);color:var(--ink);outline:none;transition:border-color .15s;}
.search-input:focus{border-color:var(--green);}
.search-count{font-family:var(--mono);font-size:.68rem;color:var(--ink-soft);white-space:nowrap;}
.filter-row{display:flex;gap:.4rem;flex-wrap:wrap;margin-bottom:1.5rem;}
.filter-pill{font-family:var(--mono);font-size:.6rem;letter-spacing:.07em;text-transform:uppercase;padding:.22em .75em;border-radius:2px;border:1px solid var(--rule-strong);background:var(--paper);color:var(--ink-soft);cursor:pointer;transition:all .12s;user-select:none;}
.filter-pill:hover{background:var(--paper-warm);color:var(--ink);}
.filter-pill.active{background:var(--green);color:#fff;border-color:var(--green);}

/* ── Plant grid (index) ── */
.plant-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:1px;border:1px solid var(--rule-strong);border-radius:3px;overflow:hidden;background:var(--rule-strong);margin-bottom:2rem;}
.plant-card{background:var(--paper);padding:1.2rem 1.4rem;transition:background .12s;display:flex;flex-direction:column;gap:.3rem;cursor:pointer;}
.plant-card:hover{background:var(--paper-warm);}
.plant-card.hidden{display:none;}
.card-id{font-family:var(--mono);font-size:.58rem;letter-spacing:.1em;color:var(--ink-soft);text-transform:uppercase;}
.card-pref{font-family:var(--serif);font-size:1.15rem;font-weight:600;color:var(--green);line-height:1.15;}
.card-sci{font-size:.76rem;font-style:italic;color:var(--ink-soft);}
/* Name rows on card — always shown, stacked */
.card-names{display:flex;flex-direction:column;gap:.1rem;margin-top:.25rem;}
.card-name-row{display:grid;grid-template-columns:28px 1fr;gap:.4rem;align-items:baseline;}
.card-name-lang{font-family:var(--mono);font-size:.52rem;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-soft);}
.card-name-val{font-size:.78rem;color:var(--ink-mid);}
.card-foot{margin-top:.5rem;display:flex;gap:.4rem;flex-wrap:wrap;align-items:center;}

/* ── Access badges ── */
.access-badge{display:inline-block;font-family:var(--mono);font-size:.58rem;letter-spacing:.06em;padding:.12em .55em;border-radius:2px;white-space:nowrap;}
.access-badge-lg{font-size:.72rem;padding:.2em .7em;}
.access-public   {background:var(--green-light);color:var(--green);}
.access-community{background:var(--gold-light);color:var(--gold);}
.access-initiated{background:#fde8e0;color:var(--terracotta);}
.access-none     {background:#2a2a2a;color:#fff;}

/* ── Plant detail page ── */
.plant-header{padding:2.5rem 0 2rem;border-bottom:2px solid var(--ink);}
.plant-header-inner{display:grid;grid-template-columns:1fr auto;gap:2rem;align-items:start;}
.plant-pref-large{font-family:var(--serif);font-size:clamp(2rem,4vw,3rem);font-weight:600;color:var(--green);line-height:1.05;}
.plant-sci-large{font-size:1rem;font-style:italic;color:var(--ink-soft);margin-top:.3rem;}
.plant-id-label{font-family:var(--mono);font-size:.65rem;letter-spacing:.12em;text-transform:uppercase;color:var(--ink-soft);margin-top:.5rem;}
.plant-header-meta{display:flex;gap:.5rem;flex-wrap:wrap;align-items:center;margin-top:.85rem;}

/* Detail grid */
.detail-grid{display:grid;grid-template-columns:1fr 1fr;gap:3rem;margin:2.5rem 0;}
.detail-section-title{font-family:var(--mono);font-size:.65rem;letter-spacing:.18em;text-transform:uppercase;color:var(--ink-soft);padding-bottom:.5rem;border-bottom:1px solid var(--rule-strong);margin-bottom:1.2rem;}
.detail-row{margin-bottom:1rem;}
.detail-label{font-family:var(--mono);font-size:.63rem;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-soft);margin-bottom:.3rem;}

/* Names table — always fully visible */
.names-table{width:100%;border-collapse:collapse;}
.names-table tr{border-bottom:1px solid var(--rule);}
.names-table tr:last-child{border-bottom:none;}
.names-table td{padding:.55rem 0;vertical-align:top;}
.names-table td:first-child{font-family:var(--mono);font-size:.6rem;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-soft);white-space:nowrap;padding-right:1rem;width:130px;padding-top:.65rem;}
.names-table .name-entry{font-size:.9rem;color:var(--ink-mid);line-height:1.5;}
.names-table .name-entry:first-child{font-size:.98rem;color:var(--ink);font-weight:400;}
.names-table .name-empty{font-family:var(--mono);font-size:.68rem;color:var(--ink-soft);font-style:italic;}

/* Gated row */
.gated-cell{display:inline-flex;align-items:center;gap:.6rem;}

/* Use value pill */
.use-value{display:inline-block;font-size:.85rem;font-weight:400;color:var(--ink);background:var(--paper-warm);border:1px solid var(--rule-strong);padding:.2em .75em;border-radius:2px;}

/* Tag cloud */
.tag-cloud{display:flex;flex-wrap:wrap;gap:.35rem;}
.tag-pill{font-family:var(--sans);font-size:.73rem;background:var(--paper-deep);color:var(--ink-mid);padding:.18em .65em;border-radius:2px;border:1px solid var(--rule-strong);line-height:1.4;}
.tag-pill .country-prefix{color:var(--ink-soft);font-size:.68rem;margin-right:.3em;}

/* Collision */
.collision-notice{display:inline-flex;align-items:center;gap:.4rem;font-family:var(--mono);font-size:.62rem;letter-spacing:.06em;color:var(--gold);background:var(--gold-light);border:1px solid rgba(160,120,48,.25);padding:.18em .65em;border-radius:2px;}

/* Ritual notes block */
.notes-block{background:var(--paper-warm);border:1px solid var(--rule-strong);border-radius:3px;padding:.85rem 1rem;font-size:.87rem;color:var(--ink-mid);line-height:1.65;}

/* Nav */
.plant-nav{display:flex;justify-content:space-between;align-items:center;padding:1.5rem 0;border-top:1px solid var(--rule);margin-top:2rem;}
.plant-nav a{font-family:var(--mono);font-size:.68rem;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-soft);border:1px solid var(--rule-strong);padding:.3em .9em;border-radius:2px;transition:all .12s;}
.plant-nav a:hover{background:var(--paper-warm);color:var(--ink);}

/* Footer */
.site-footer{border-top:1px solid var(--rule);padding:1.5rem 0 2.5rem;display:flex;gap:2rem;flex-wrap:wrap;justify-content:space-between;align-items:center;margin-top:2rem;}
.footer-left{font-family:var(--mono);font-size:.68rem;letter-spacing:.04em;color:var(--ink-soft);line-height:1.7;}
.footer-links{display:flex;gap:1.5rem;}
.footer-links a{font-family:var(--mono);font-size:.68rem;letter-spacing:.05em;color:var(--ink-soft);}
.footer-links a:hover{color:var(--green);}

@media(max-width:760px){
  .hero-inner{grid-template-columns:1fr;gap:1rem;}
  .hero-logo img{width:52px;}
  .detail-grid{grid-template-columns:1fr;gap:1.5rem;}
  .plant-grid{grid-template-columns:1fr;}
  .plant-header-inner{grid-template-columns:1fr;}
}
"""

# ── Interface language JS ─────────────────────────────────────────────────────
LANG_JS = """\
<script>
(function(){
  var LANGS = ['en','es','fr','yo','pt'];
  var stored = (localStorage.getItem('ewe-ui-lang') || 'en');
  if(LANGS.indexOf(stored) < 0) stored = 'en';

  function applyLang(lang){
    document.body.setAttribute('data-ui-lang', lang);
    // Update all .ui spans
    document.querySelectorAll('.ui[data-'+lang+']').forEach(function(el){
      el.textContent = el.getAttribute('data-'+lang);
    });
    // Update search placeholder
    var si = document.querySelector('.search-input');
    if(si){
      var ph = si.getAttribute('data-ph-'+lang);
      if(ph) si.placeholder = ph;
    }
    // Update lang buttons
    document.querySelectorAll('.lang-btn').forEach(function(b){
      b.classList.toggle('active', b.dataset.lang === lang);
    });
    localStorage.setItem('ewe-ui-lang', lang);
  }

  document.querySelectorAll('.lang-btn').forEach(function(btn){
    btn.addEventListener('click', function(){
      if(!this.classList.contains('disabled')) applyLang(this.dataset.lang);
    });
  });

  applyLang(stored);
})();
</script>"""

def lang_toggle_html(has_pt_data=True):
    pt_cls = " disabled" if not has_pt_data else ""
    return f"""\
<div class="lang-toggle">
  <button class="lang-btn" data-lang="en">EN</button>
  <button class="lang-btn" data-lang="es">ES</button>
  <button class="lang-btn" data-lang="fr">FR</button>
  <button class="lang-btn" data-lang="yo">YO</button>
  <button class="lang-btn{pt_cls}" data-lang="pt">PT</button>
</div>"""

def top_bar(depth=""):
    index_href = f"{depth}index.html"
    return f"""\
<div class="top-bar">
  <span class="top-bar-id">Iroko Historical Society · Ewé Database</span>
  <nav class="top-bar-links">
    <a href="{index_href}" class="ui" {ui_attrs('all_plants')}>All Plants</a>
    <a href="https://ontology.irokosociety.org">Framework ↗</a>
    <a href="https://www.irokosociety.org">irokosociety.org ↗</a>
  </nav>
</div>"""

def footer_html(depth=""):
    return f"""\
<footer class="site-footer">
  <div class="footer-left">
    <span class="ui" {ui_attrs('footer_site')}>Iroko Historical Society · Ewé Database</span><br>
    <span class="ui" {ui_attrs('footer_desc')}>Postcustodial Digital Archives for Afro-Atlantic Cultural Materials</span><br>
    Source: Pierre Fatumbi Verger, <em>Ewé: The Use of Plants in Yoruba Society</em> (1995) ·
    Dalia Quiros-Moran, <em>Guide to Afro-Cuban Herbalism</em><br>
    Vocabulary: <a href="https://ontology.irokosociety.org">Iroko Framework v2.0.0</a> · License: CC0 1.0
  </div>
  <div class="footer-links">
    <a href="https://www.irokosociety.org">irokosociety.org</a>
    <a href="https://ontology.irokosociety.org">Vocabulary</a>
    <a href="{depth}index.html" class="ui" {ui_attrs('all_plants')}>All Plants</a>
  </div>
</footer>"""

# ── Index page ────────────────────────────────────────────────────────────────
def build_index(plants, out_dir):
    ritual_labels = sorted(set(
        RITUAL_LABEL.get(p["ritual_use"], p["ritual_use"])
        for p in plants if p["ritual_use"]
    ))

    about_d = UI["about_body"]
    about_divs = "\n".join(
        f'<p class="ui" data-en="{H(about_d["en"])}" data-es="{H(about_d["es"])}" '
        f'data-fr="{H(about_d["fr"])}" data-yo="{H(about_d["yo"])}" data-pt="{H(about_d["pt"])}">'
        f'{H(about_d["en"])}</p>'
    )

    cards = []
    for p in plants:
        en_first = p["en"][0] if p["en"] else ""
        yo_first = p["yo"][0] if p["yo"] else ""
        es_first = p["es"][0] if p["es"] else ""
        ru_key   = p["ritual_use"] or ""
        ru_label = RITUAL_LABEL.get(ru_key, "")
        ac_key   = p["access_key"] or ""
        search_str = " ".join([p["prefLabel"], p["scientific"], en_first, yo_first, es_first]).lower()

        name_rows = ""
        if en_first:
            name_rows += f'<div class="card-name-row"><span class="card-name-lang">EN</span><span class="card-name-val">{H(en_first)}</span></div>'
        if yo_first:
            name_rows += f'<div class="card-name-row"><span class="card-name-lang">YO</span><span class="card-name-val">{H(yo_first)}</span></div>'
        if es_first:
            name_rows += f'<div class="card-name-row"><span class="card-name-lang">ES</span><span class="card-name-val">{H(es_first)}</span></div>'

        cards.append(f"""\
    <a class="plant-card" href="plant/{H(p['id'])}.html"
       data-search="{H(search_str)}" data-ritual="{H(ru_label)}">
      <div class="card-id">{H(p['id'])}</div>
      <div class="card-pref">{H(p['prefLabel'])}</div>
      <div class="card-sci">{H(p['scientific'])}</div>
      <div class="card-names">{name_rows}</div>
      <div class="card-foot">
        {access_badge(ac_key)}
        {'<span class="collision-notice">⚠</span>' if p['name_collision'] else ''}
      </div>
    </a>""")

    filter_pills = f'<button class="filter-pill active" data-ritual="">{ui_span("all_plants")}</button>\n'
    for rl in ritual_labels:
        filter_pills += f'    <button class="filter-pill" data-ritual="{H(rl)}">{H(rl)}</button>\n'

    ph = UI["search_placeholder"]
    ph_attrs = " ".join(f'data-ph-{lang}="{H(v)}"' for lang, v in ph.items())

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="Ewé Database — Iroko Historical Society">
  <title>Ewé Database — Iroko Historical Society</title>
  <style>{CSS}</style>
</head>
<body>

{top_bar()}

<div class="page-wrap">

  <header class="explorer-hero">
    <div class="hero-inner">
      <div class="hero-logo">
        <a href="https://www.irokosociety.org">
          <img src="assets/IHS-Logo.jpg" alt="Iroko Historical Society">
        </a>
      </div>
      <div>
        <div class="explorer-eyebrow">Iroko Historical Society · Afro-Atlantic Sacred Plant Knowledge</div>
        <h1 class="explorer-title">Ewé Database<br><em>Verger Collection</em></h1>
        <p class="explorer-sub">
          50 sacred plants from Pierre Fatumbi Verger&#x2019;s <em>Ewé: The Use of Plants in Yoruba Society</em>
          and Dalia Quiros-Moran&#x2019;s <em>Guide to Afro-Cuban Herbalism</em>,
          structured using the Iroko Framework.
        </p>
      </div>
      <div>{lang_toggle_html()}</div>
    </div>
    <div class="about-block" style="margin-top:2rem;">
      <div class="about-block-title ui" {ui_attrs('about_title')}>About the Ewé Database</div>
      {about_divs}
    </div>
  </header>

  <div class="toolbar">
    <input class="search-input" type="search" id="plantSearch"
      placeholder="{H(ph['en'])}" {ph_attrs} autocomplete="off">
    <span class="search-count" id="searchCount">{len(plants)} <span class="ui" {ui_attrs('plants_label')}>plants</span></span>
  </div>

  <div class="filter-row" id="ritualFilter">
    {filter_pills}
  </div>

  <div class="plant-grid" id="plantGrid">
{chr(10).join(cards)}
  </div>

{footer_html()}

</div>

{LANG_JS}

<script>
(function(){{
  var searchEl = document.getElementById('plantSearch');
  var countEl  = document.getElementById('searchCount');
  var cards    = document.querySelectorAll('.plant-card');
  var pills    = document.querySelectorAll('#ritualFilter .filter-pill');
  var activeRitual = '';

  function applyFilters(){{
    var query = searchEl.value.toLowerCase().trim();
    var visible = 0;
    cards.forEach(function(card){{
      var ok = (!query || card.dataset.search.includes(query)) &&
               (!activeRitual || card.dataset.ritual === activeRitual);
      card.classList.toggle('hidden', !ok);
      if(ok) visible++;
    }});
    var lbl = document.querySelector('#searchCount .ui');
    countEl.firstChild.textContent = visible + '\u00a0';
  }}

  searchEl.addEventListener('input', applyFilters);
  pills.forEach(function(pill){{
    pill.addEventListener('click', function(){{
      pills.forEach(function(p){{p.classList.remove('active');}});
      this.classList.add('active');
      activeRitual = this.dataset.ritual;
      applyFilters();
    }});
  }});
}})();
</script>

</body>
</html>"""
    (out_dir / "index.html").write_text(page, encoding="utf-8")
    print(f"  ✓ index.html ({len(plants)} plant cards)")


# ── Per-plant page ────────────────────────────────────────────────────────────
def build_plant(p, prev_id, next_id, out_dir):
    pid = p["id"]
    ac  = p["access_key"] or "access-public-unrestricted"

    # ── Names table ─────────────────────────────────────────────────────────
    def name_cells(names, empty_key="none_recorded"):
        if not names:
            empty_txt = UI[empty_key]
            spans = " ".join(f'data-{l}="{H(v)}"' for l,v in empty_txt.items())
            return f'<span class="name-empty ui" {spans}>{H(empty_txt["en"])}</span>'
        return "".join(f'<div class="name-entry">{H(n)}</div>' for n in names)

    # Lucumí gated
    lucumi_key = ac if ac not in ("access-public-unrestricted",) else "access-community-only"
    lucumi_content = (
        f'<div class="gated-cell">{access_badge(lucumi_key, "access-badge-lg")}</div>'
        if lucumi_key != "access-public-unrestricted" and not (ac == "access-public-unrestricted" and p["lucumi"])
        else name_cells(p["lucumi"])
    )
    # Actually always gate lucumi at minimum community
    if p["lucumi"]:
        if ac in ("access-public-unrestricted", "access-public-no-amplification"):
            lucumi_content = f'<div class="gated-cell">{access_badge("access-community-only","access-badge-lg")}</div>'
        else:
            lucumi_content = name_cells(p["lucumi"])
    else:
        lucumi_content = name_cells([], "none_recorded")

    pt_content = name_cells(p["pt"]) if p["pt"] else (
        f'<span class="name-empty ui" {ui_attrs("pt_pending")}>{H(UI["pt_pending"]["en"])}</span>'
    )

    names_table = f"""\
<table class="names-table">
  <tr>
    <td class="ui" {ui_attrs('english')}>English</td>
    <td>{name_cells(p['en'])}</td>
  </tr>
  <tr>
    <td class="ui" {ui_attrs('yoruba')}>Yoruba</td>
    <td>{name_cells(p['yo'])}</td>
  </tr>
  <tr>
    <td class="ui" {ui_attrs('spanish_cuban')}>Spanish / Cuban</td>
    <td>{name_cells(p['es'])}</td>
  </tr>
  <tr>
    <td class="ui" {ui_attrs('pt_names')}>Brazilian Portuguese</td>
    <td>{pt_content}</td>
  </tr>
  <tr>
    <td class="ui" {ui_attrs('lucumi')}>Lucumí Names</td>
    <td>{lucumi_content}</td>
  </tr>
</table>"""

    # ── Regional names ───────────────────────────────────────────────────────
    def format_pill(name):
        if " – " in name or " - " in name:
            sep = " – " if " – " in name else " - "
            parts = name.split(sep, 1)
            return f'<span class="tag-pill"><span class="country-prefix">{H(parts[0])} ·</span>{H(parts[1])}</span>'
        return f'<span class="tag-pill">{H(name)}</span>'

    if p["other"]:
        other_content = '<div class="tag-cloud">' + "".join(format_pill(n) for n in p["other"]) + '</div>'
    else:
        empty_attrs = ui_attrs("none_recorded")
        other_content = f'<span class="name-empty ui" {empty_attrs}>{H(UI["none_recorded"]["en"])}</span>'

    # ── Sacred knowledge ─────────────────────────────────────────────────────
    ru_slug  = p["ritual_use"] or ""
    ru_label = RITUAL_LABEL.get(ru_slug, ru_slug.replace("-"," ").title() if ru_slug else "")
    ru_value = f'<span class="use-value">{H(ru_label)}</span>' if ru_label else ""
    ritual_display = gated_value(ru_value, ac)

    rn_value = f'<div class="notes-block">{H(p["ritual_notes"])}</div>' if p["ritual_notes"] else ""
    notes_display = gated_value(rn_value, ac)

    mu_slug  = p["medicinal_use"] or ""
    mu_label = MEDICINAL_LABEL.get(mu_slug, mu_slug.replace("-"," ").title() if mu_slug else "")
    mu_value = f'<span class="use-value">{H(mu_label)}</span>' if mu_label else ""
    medicinal_display = gated_value(mu_value, ac)

    collision_html = ""
    if p["name_collision"]:
        nc_attrs = ui_attrs("name_collision_note")
        collision_html = f'<span class="collision-notice ui" {nc_attrs}>⚠ Name collision recorded</span>'

    prev_link = f'<a href="{H(prev_id)}.html">← <span class="ui" {ui_attrs("prev_plant")}>Previous</span> · {H(prev_id)}</a>' if prev_id else '<span></span>'
    next_link = f'<a href="{H(next_id)}.html">{H(next_id)} · <span class="ui" {ui_attrs("next_plant")}>Next</span> →</a>' if next_id else '<span></span>'

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{H(p['prefLabel'])} · {H(p['scientific'])} — Ewé Database</title>
  <style>{CSS}</style>
</head>
<body>

{top_bar(depth="../")}

<div class="page-wrap">

  <p class="breadcrumb">
    <a href="../index.html" class="ui" {ui_attrs('all_plants')}>All Plants</a>
    <span>/</span>
    {H(pid)}
  </p>

  <header class="plant-header">
    <div class="plant-header-inner">
      <div>
        <div class="plant-pref-large">{H(p['prefLabel'])}</div>
        <div class="plant-sci-large">{H(p['scientific'])}</div>
        <div class="plant-id-label">{H(pid)} · iroko:EwePlantRecord</div>
        <div class="plant-header-meta">
          {access_badge(ac, "access-badge-lg")}
          {collision_html}
        </div>
      </div>
      <div>{lang_toggle_html()}</div>
    </div>
  </header>

  <div class="detail-grid">

    <div>
      <div class="detail-section-title ui" {ui_attrs('names_by_language')}>Names by Language</div>
      {names_table}
    </div>

    <div>
      <div class="detail-section-title ui" {ui_attrs('regional_vernacular')}>Regional &amp; Vernacular Names</div>
      <div class="detail-label ui" {ui_attrs('other_regional')}>Other Regional Names</div>
      <div style="margin-top:.4rem;">{other_content}</div>
    </div>

  </div>

  <div class="detail-grid">

    <div>
      <div class="detail-section-title ui" {ui_attrs('sacred_knowledge')}>Sacred Knowledge</div>
      <div class="detail-row">
        <div class="detail-label ui" {ui_attrs('ritual_use')}>Ritual Use</div>
        <div style="margin-top:.3rem;">{ritual_display}</div>
      </div>
      <div class="detail-row">
        <div class="detail-label ui" {ui_attrs('ritual_notes')}>Ritual Notes</div>
        <div style="margin-top:.3rem;">{notes_display if notes_display else
          f'<span class="name-empty ui" {ui_attrs("none_recorded")}>{H(UI["none_recorded"]["en"])}</span>'}</div>
      </div>
    </div>

    <div>
      <div class="detail-section-title ui" {ui_attrs('classification')}>Classification</div>
      <div class="detail-row">
        <div class="detail-label ui" {ui_attrs('medicinal_use')}>Medicinal Use</div>
        <div style="margin-top:.3rem;">{medicinal_display}</div>
      </div>
      <div class="detail-row">
        <div class="detail-label ui" {ui_attrs('scientific_name')}>Scientific Name</div>
        <div style="margin-top:.3rem;font-style:italic;font-size:.9rem;color:var(--ink-mid);">{H(p['scientific'])}</div>
      </div>
      <div class="detail-row">
        <div class="detail-label ui" {ui_attrs('iroko_uri')}>Iroko URI</div>
        <div style="margin-top:.3rem;">
          <a href="{H(p['uri'])}" style="font-family:var(--mono);font-size:.72rem;word-break:break-all;">{H(p['uri'])}</a>
        </div>
      </div>
      <div class="detail-row">
        <div class="detail-label ui" {ui_attrs('vocabulary')}>Vocabulary</div>
        <div style="margin-top:.3rem;">
          <a href="https://ontology.irokosociety.org/vocab/iroko-ewe.html"
             style="font-family:var(--mono);font-size:.72rem;">iroko-ewe ↗</a>
        </div>
      </div>
    </div>

  </div>

  <div class="plant-nav">{prev_link}<a href="../index.html" class="ui" {ui_attrs('all_plants')}>All Plants</a>{next_link}</div>

{footer_html(depth="../")}

</div>

{LANG_JS}
</body>
</html>"""
    (out_dir / f"{pid}.html").write_text(page, encoding="utf-8")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ttl",  default="Verger_Ewe_Dataset.ttl")
    parser.add_argument("--out",  default="ewe-explorer-v2")
    parser.add_argument("--logo", default=None)
    args = parser.parse_args()

    out_dir   = Path(args.out)
    plant_dir = out_dir / "plant"
    asset_dir = out_dir / "assets"
    out_dir.mkdir(parents=True, exist_ok=True)
    plant_dir.mkdir(exist_ok=True)
    asset_dir.mkdir(exist_ok=True)

    print(f"Parsing {args.ttl} …")
    g = Graph()
    g.parse(args.ttl, format="turtle")

    plants = extract_plants(g)
    print(f"  {len(plants)} EwePlantRecord instances\n")

    if args.logo and Path(args.logo).exists():
        shutil.copy(args.logo, asset_dir / "IHS-Logo.jpg")
        print("  ✓ assets/IHS-Logo.jpg")

    build_index(plants, out_dir)

    for i, p in enumerate(plants):
        prev_id = plants[i-1]["id"] if i > 0 else None
        next_id = plants[i+1]["id"] if i < len(plants)-1 else None
        build_plant(p, prev_id, next_id, plant_dir)

    print(f"\n{'─'*50}")
    print(f"Done: {len(plants)+1} files → {out_dir}/")

if __name__ == "__main__":
    main()
