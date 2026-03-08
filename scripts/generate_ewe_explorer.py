#!/usr/bin/env python3
"""
Iroko Ewé Explorer — Static Site Generator
Reads Verger_Ewe_Dataset.ttl and generates:
  index.html           — searchable plant browse page
  plant/[ID].html      — one page per plant record
  ewe-style.css        — explorer stylesheet

Usage:
  python3 generate_ewe_explorer.py \
      --ttl path/to/Verger_Ewe_Dataset.ttl \
      --out path/to/output/ \
      --logo path/to/IHS-Logo.jpg
"""

import argparse, html, os, shutil
from pathlib import Path
from rdflib import Graph, Namespace, RDF, URIRef
from rdflib.namespace import SKOS, DCTERMS
import urllib.request

# ── Namespaces ────────────────────────────────────────────────────────────────
IROKO = Namespace("https://ontology.irokosociety.org/iroko#")
DWC   = Namespace("http://rs.tdwg.org/dwc/terms/")

# ── Access level maps ─────────────────────────────────────────────────────────
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
    "medicinal-digestive-support":    "Digestive Support",
    "medicinal-general-tonic":        "General Tonic",
    "medicinal-respiratory-support":  "Respiratory Support",
    "medicinal-skin-topical":         "Skin & Topical",
}

H = lambda s: html.escape(str(s), quote=True)

# ── Data extraction ───────────────────────────────────────────────────────────
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
            if isinstance(o, URIRef):
                continue
            s = str(o)
            if s.startswith("Plant"):
                p["id"] = s

        p["scientific"] = str(g.value(subj, DWC.scientificName) or "")
        pref = g.value(subj, SKOS.prefLabel)
        p["prefLabel"] = str(pref) if pref else ""

        for o in g.objects(subj, SKOS.altLabel):
            lang = getattr(o, "language", None)
            val  = str(o)
            if lang == "en":
                p["en"].append(val)
            elif lang == "yo":
                p["yo"].append(val)
            elif lang in ("es", "sp"):
                if val not in p["es"]: p["es"].append(val)
            elif lang in ("pt-BR", "pt"):
                p["pt"].append(val)
            elif lang == "x-lucumi":
                p["lucumi"].append(val)
            elif lang in ("ht",):
                p["other"].append(val)   # Haiti — no dedicated column yet
            elif lang is None:
                p["other"].append(val)

        ru = g.value(subj, IROKO.ritualUse)
        if ru: p["ritual_use"] = local(str(ru))

        mu = g.value(subj, IROKO.medicinalUse)
        if mu: p["medicinal_use"] = local(str(mu))

        rn = g.value(subj, IROKO.ritualNotes)
        if rn: p["ritual_notes"] = str(rn)

        al = g.value(subj, IROKO.accessLevel)
        if al: p["access_key"] = local(str(al))

        nc = g.value(subj, IROKO.nameCollision)
        if nc: p["name_collision"] = str(nc).lower() in ("yes", "true", "1")

        plants.append(p)

    plants.sort(key=lambda x: x["id"] or "")
    return plants

# ── Badge helpers ─────────────────────────────────────────────────────────────
def access_badge(key, size="normal"):
    if not key or key not in ACCESS_LABEL:
        return ""
    label, css = ACCESS_LABEL[key]
    cls = f"access-badge {css}"
    if size == "large":
        cls += " access-badge-lg"
    return f'<span class="{cls}">{H(label)}</span>'

def gated_value(value_html, access_key):
    """Return value_html if public-unrestricted, else the access badge."""
    if access_key in (None, "access-public-unrestricted"):
        return value_html
    return access_badge(access_key, size="large")

# ── CSS ───────────────────────────────────────────────────────────────────────
EWE_CSS = """\
/* ================================================================
   Iroko Ewé Explorer — Explorer Stylesheet
   Extends iroko-style.css design tokens
   ewe.irokosociety.org
================================================================ */

@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400;1,500&family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500&display=swap');

/* ── Tokens (mirrored from iroko-style.css) ──────────────────── */
:root {
  --ink:          #1c2118;
  --ink-mid:      #3d4a36;
  --ink-soft:     #6b7a62;
  --paper:        #f7f4ed;
  --paper-warm:   #ede9df;
  --paper-deep:   #e4dfd2;
  --rule:         rgba(28,33,24,.12);
  --rule-strong:  rgba(28,33,24,.25);
  --green:        #2e4a1e;
  --green-mid:    #4a7035;
  --green-light:  #e8f0e2;
  --terracotta:   #8b3a1a;
  --gold:         #a07830;
  --gold-light:   #f5edd8;
  --purple:       #5c3d8f;
  --navy:         #1a4a5e;
  --mono:  'DM Mono', monospace;
  --sans:  'DM Sans', sans-serif;
  --serif: 'Cormorant Garamond', Georgia, serif;
}

/* ── Reset ───────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { font-size: 16px; scroll-behavior: smooth; }
body { background: var(--paper); color: var(--ink); font-family: var(--sans); font-weight: 300; line-height: 1.65; }
a { color: var(--green); text-decoration: none; }
a:hover { color: var(--terracotta); }

/* ── Layout ──────────────────────────────────────────────────── */
.page-wrap { max-width: 1080px; margin: 0 auto; padding: 0 2rem; }

/* ── Top bar ─────────────────────────────────────────────────── */
.top-bar { border-bottom: 1px solid var(--rule); padding: .7rem 2rem; display: flex; justify-content: space-between; align-items: center; gap: 1rem; flex-wrap: wrap; }
.top-bar-id { font-family: var(--mono); font-size: .68rem; letter-spacing: .1em; text-transform: uppercase; color: var(--ink-soft); }
.top-bar-links { display: flex; gap: 1.5rem; }
.top-bar-links a { font-family: var(--mono); font-size: .68rem; letter-spacing: .08em; text-transform: uppercase; color: var(--ink-soft); }
.top-bar-links a:hover { color: var(--green); }

/* ── Breadcrumb ──────────────────────────────────────────────── */
.breadcrumb { font-family: var(--mono); font-size: .7rem; letter-spacing: .08em; color: var(--ink-soft); padding: 1rem 0 0; }
.breadcrumb a { color: var(--ink-soft); }
.breadcrumb a:hover { color: var(--green); }
.breadcrumb span { margin: 0 .4em; opacity: .5; }

/* ── Explorer hero ───────────────────────────────────────────── */
.explorer-hero {
  padding: 3rem 0 2.5rem;
  border-bottom: 2px solid var(--ink);
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 2.5rem;
  align-items: start;
}
.explorer-hero-logo img { width: 96px; height: auto; display: block; margin-top: .3rem; }
.explorer-eyebrow { font-family: var(--mono); font-size: .68rem; letter-spacing: .18em; text-transform: uppercase; color: var(--green-mid); margin-bottom: .5rem; }
.explorer-title { font-family: var(--serif); font-size: clamp(2rem, 4vw, 3rem); font-weight: 600; color: var(--green); line-height: 1.05; }
.explorer-title em { font-style: italic; color: var(--terracotta); }
.explorer-sub { font-size: .9rem; color: var(--ink-mid); margin-top: .75rem; max-width: 60ch; line-height: 1.65; }

/* ── Search & filter bar ─────────────────────────────────────── */
.search-bar {
  margin: 2rem 0 1rem;
  display: flex;
  gap: .75rem;
  align-items: center;
  flex-wrap: wrap;
}
.search-input {
  flex: 1;
  min-width: 220px;
  font-family: var(--sans);
  font-size: .88rem;
  padding: .5em 1em;
  border: 1px solid var(--rule-strong);
  border-radius: 3px;
  background: var(--paper);
  color: var(--ink);
  outline: none;
  transition: border-color .15s;
}
.search-input:focus { border-color: var(--green); }
.search-count { font-family: var(--mono); font-size: .68rem; color: var(--ink-soft); white-space: nowrap; }

/* ── Filter pills ────────────────────────────────────────────── */
.filter-row { display: flex; gap: .4rem; flex-wrap: wrap; margin-bottom: 1.5rem; }
.filter-pill {
  font-family: var(--mono);
  font-size: .6rem;
  letter-spacing: .07em;
  text-transform: uppercase;
  padding: .22em .75em;
  border-radius: 2px;
  border: 1px solid var(--rule-strong);
  background: var(--paper);
  color: var(--ink-soft);
  cursor: pointer;
  transition: all .12s;
  user-select: none;
}
.filter-pill:hover { background: var(--paper-warm); color: var(--ink); }
.filter-pill.active { background: var(--green); color: #fff; border-color: var(--green); }
.filter-pill.clear-pill { border-color: transparent; color: var(--ink-soft); }
.filter-pill.clear-pill:hover { color: var(--terracotta); }

/* ── Plant grid ──────────────────────────────────────────────── */
.plant-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1px;
  border: 1px solid var(--rule-strong);
  border-radius: 3px;
  overflow: hidden;
  background: var(--rule-strong);
  margin-bottom: 2rem;
}
.plant-card {
  background: var(--paper);
  padding: 1.1rem 1.3rem;
  transition: background .12s;
  display: flex;
  flex-direction: column;
  gap: .35rem;
}
.plant-card:hover { background: var(--paper-warm); }
.plant-card.hidden { display: none; }

.plant-id {
  font-family: var(--mono);
  font-size: .58rem;
  letter-spacing: .1em;
  color: var(--ink-soft);
  text-transform: uppercase;
}
.plant-pref {
  font-family: var(--serif);
  font-size: 1.15rem;
  font-weight: 600;
  color: var(--green);
  line-height: 1.15;
}
.plant-sci {
  font-family: var(--sans);
  font-size: .78rem;
  font-style: italic;
  color: var(--ink-soft);
}
.plant-en { font-size: .8rem; color: var(--ink-mid); }
.plant-card-foot { margin-top: .4rem; display: flex; gap: .4rem; flex-wrap: wrap; align-items: center; }

/* ── Language toggle ─────────────────────────────────────────── */
.lang-toggle {
  display: flex;
  gap: 0;
  border: 1px solid var(--rule-strong);
  border-radius: 3px;
  overflow: hidden;
  width: fit-content;
}
.lang-btn {
  font-family: var(--mono);
  font-size: .62rem;
  letter-spacing: .1em;
  text-transform: uppercase;
  padding: .28em .85em;
  background: var(--paper);
  color: var(--ink-soft);
  border: none;
  border-right: 1px solid var(--rule-strong);
  cursor: pointer;
  transition: all .12s;
  user-select: none;
}
.lang-btn:last-child { border-right: none; }
.lang-btn:hover { background: var(--paper-warm); color: var(--ink); }
.lang-btn.active { background: var(--green); color: #fff; }
.lang-btn.disabled { opacity: .35; pointer-events: none; }

/* Language visibility — controlled by data-lang on <body> */
.name-block { display: none; }
body[data-lang="en"] .name-block[data-lang="en"],
body[data-lang="yo"] .name-block[data-lang="yo"],
body[data-lang="es"] .name-block[data-lang="es"],
body[data-lang="pt"] .name-block[data-lang="pt"] { display: block; }

/* ── Access badges ───────────────────────────────────────────── */
.access-badge {
  display: inline-block;
  font-family: var(--mono);
  font-size: .58rem;
  letter-spacing: .06em;
  padding: .12em .55em;
  border-radius: 2px;
  white-space: nowrap;
}
.access-badge-lg {
  font-size: .72rem;
  padding: .2em .7em;
}
.access-public    { background: var(--green-light); color: var(--green); }
.access-community { background: var(--gold-light);  color: var(--gold); }
.access-initiated { background: #fde8e0;            color: var(--terracotta); }
.access-none      { background: #2a2a2a;            color: #fff; }

/* ── Plant detail page ───────────────────────────────────────── */
.plant-header {
  padding: 2.5rem 0 2rem;
  border-bottom: 2px solid var(--ink);
}
.plant-header-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem; flex-wrap: wrap; }
.plant-header-title { flex: 1; }
.plant-pref-large {
  font-family: var(--serif);
  font-size: clamp(1.8rem, 4vw, 2.8rem);
  font-weight: 600;
  color: var(--green);
  line-height: 1.05;
}
.plant-sci-large {
  font-family: var(--sans);
  font-size: 1rem;
  font-style: italic;
  color: var(--ink-soft);
  margin-top: .35rem;
}
.plant-id-label {
  font-family: var(--mono);
  font-size: .65rem;
  letter-spacing: .12em;
  text-transform: uppercase;
  color: var(--ink-soft);
  margin-top: .5rem;
}
.plant-header-meta { display: flex; gap: .5rem; flex-wrap: wrap; align-items: center; margin-top: 1rem; }

/* ── Detail sections ─────────────────────────────────────────── */
.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2.5rem;
  margin: 2.5rem 0;
}
.detail-section { }
.detail-section-title {
  font-family: var(--mono);
  font-size: .65rem;
  letter-spacing: .18em;
  text-transform: uppercase;
  color: var(--ink-soft);
  padding-bottom: .5rem;
  border-bottom: 1px solid var(--rule-strong);
  margin-bottom: 1rem;
}
.detail-row { margin-bottom: .85rem; }
.detail-label {
  font-family: var(--mono);
  font-size: .63rem;
  letter-spacing: .1em;
  text-transform: uppercase;
  color: var(--ink-soft);
  margin-bottom: .2rem;
}
.detail-value { font-size: .9rem; color: var(--ink-mid); line-height: 1.5; }
.detail-value-serif { font-family: var(--serif); font-size: 1rem; color: var(--ink); }

/* Name list */
.name-list { list-style: none; display: flex; flex-direction: column; gap: .15rem; }
.name-list li { font-size: .88rem; color: var(--ink-mid); }
.name-list li:first-child { font-size: .96rem; color: var(--ink); font-weight: 400; }

/* Tag cloud for other vernacular names */
.tag-cloud { display: flex; flex-wrap: wrap; gap: .35rem; }
.tag-pill {
  font-family: var(--sans);
  font-size: .73rem;
  background: var(--paper-deep);
  color: var(--ink-mid);
  padding: .18em .65em;
  border-radius: 2px;
  border: 1px solid var(--rule-strong);
  line-height: 1.4;
}
.tag-pill .country-prefix { color: var(--ink-soft); font-size: .68rem; margin-right: .3em; }

/* Gated field */
.gated-row { display: flex; align-items: center; gap: .6rem; }
.gated-label-text { font-family: var(--serif); font-size: .95rem; color: var(--ink-mid); }

/* Ritual/medicinal use value */
.use-value {
  display: inline-block;
  font-family: var(--sans);
  font-size: .85rem;
  font-weight: 500;
  color: var(--ink);
  background: var(--paper-warm);
  border: 1px solid var(--rule-strong);
  padding: .2em .7em;
  border-radius: 2px;
}

/* Collision notice */
.collision-notice {
  display: inline-flex;
  align-items: center;
  gap: .4rem;
  font-family: var(--mono);
  font-size: .62rem;
  letter-spacing: .06em;
  color: var(--gold);
  background: var(--gold-light);
  border: 1px solid rgba(160,120,48,.25);
  padding: .18em .65em;
  border-radius: 2px;
}

/* Nav between plants */
.plant-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem 0;
  border-top: 1px solid var(--rule);
  margin-top: 2rem;
}
.plant-nav a {
  font-family: var(--mono);
  font-size: .68rem;
  letter-spacing: .08em;
  text-transform: uppercase;
  color: var(--ink-soft);
  border: 1px solid var(--rule-strong);
  padding: .3em .9em;
  border-radius: 2px;
  transition: all .12s;
}
.plant-nav a:hover { background: var(--paper-warm); color: var(--ink); }

/* ── Footer ──────────────────────────────────────────────────── */
.site-footer { border-top: 1px solid var(--rule); padding: 1.5rem 0 2.5rem; display: flex; gap: 2rem; flex-wrap: wrap; justify-content: space-between; align-items: center; margin-top: 2rem; }
.footer-left { font-family: var(--mono); font-size: .68rem; letter-spacing: .04em; color: var(--ink-soft); line-height: 1.7; }
.footer-links { display: flex; gap: 1.5rem; }
.footer-links a { font-family: var(--mono); font-size: .68rem; letter-spacing: .05em; color: var(--ink-soft); }
.footer-links a:hover { color: var(--green); }

/* ── Responsive ──────────────────────────────────────────────── */
@media (max-width: 760px) {
  .explorer-hero { grid-template-columns: 1fr; gap: 1rem; }
  .explorer-hero-logo img { width: 56px; }
  .detail-grid { grid-template-columns: 1fr; gap: 1.5rem; }
  .plant-grid { grid-template-columns: 1fr; }
}
"""

# ── Top bar + footer shared HTML ──────────────────────────────────────────────
TOP_BAR = """\
<div class="top-bar">
  <span class="top-bar-id">Iroko Historical Society · Ewé Database</span>
  <nav class="top-bar-links">
    <a href="index.html">All Plants</a>
    <a href="https://ontology.irokosociety.org">Framework ↗</a>
    <a href="https://www.irokosociety.org">irokosociety.org ↗</a>
  </nav>
</div>"""

TOP_BAR_PLANT = """\
<div class="top-bar">
  <span class="top-bar-id">Iroko Historical Society · Ewé Database</span>
  <nav class="top-bar-links">
    <a href="../index.html">All Plants</a>
    <a href="https://ontology.irokosociety.org">Framework ↗</a>
    <a href="https://www.irokosociety.org">irokosociety.org ↗</a>
  </nav>
</div>"""

FOOTER = """\
<footer class="site-footer">
  <div class="footer-left">
    Iroko Historical Society · Ewé Database<br>
    Postcustodial Digital Archives for Afro-Atlantic Cultural Materials<br>
    Source: Pierre Fatumbi Verger, <em>Ewé: The Use of Plants in Yoruba Society</em> (1995) ·
    Dalia Quiros-Moran, <em>Guide to Afro-Cuban Herbalism</em><br>
    Vocabulary: <a href="https://ontology.irokosociety.org">Iroko Framework v2.0.0</a> · License: CC0 1.0
  </div>
  <div class="footer-links">
    <a href="https://www.irokosociety.org">irokosociety.org</a>
    <a href="https://ontology.irokosociety.org">Vocabulary</a>
    <a href="index.html">All Plants</a>
  </div>
</footer>"""

FOOTER_PLANT = FOOTER.replace('href="index.html"', 'href="../index.html"')

LANG_JS = """\
<script>
(function(){
  var stored = localStorage.getItem('ewe-lang') || 'en';
  document.body.setAttribute('data-lang', stored);
  document.querySelectorAll('.lang-btn').forEach(function(btn){
    if(btn.dataset.lang === stored) btn.classList.add('active');
    btn.addEventListener('click', function(){
      var lang = this.dataset.lang;
      if(this.classList.contains('disabled')) return;
      document.body.setAttribute('data-lang', lang);
      localStorage.setItem('ewe-lang', lang);
      document.querySelectorAll('.lang-btn').forEach(function(b){ b.classList.remove('active'); });
      this.classList.add('active');
    }.bind(btn));
  });
})();
</script>"""

def lang_toggle(has_pt=False):
    pt_cls = "" if has_pt else " disabled"
    pt_title = "" if has_pt else ' title="Brazilian Portuguese names coming soon"'
    return f"""\
<div class="lang-toggle">
  <button class="lang-btn" data-lang="en">EN</button>
  <button class="lang-btn" data-lang="yo">YO</button>
  <button class="lang-btn" data-lang="es">ES</button>
  <button class="lang-btn{pt_cls}" data-lang="pt"{pt_title}>PT</button>
</div>"""

# ── Index page ────────────────────────────────────────────────────────────────
def build_index(plants, out_dir):
    ritual_labels = sorted(set(
        RITUAL_LABEL.get(p["ritual_use"], p["ritual_use"])
        for p in plants if p["ritual_use"]
    ))

    # Build cards
    cards = []
    for p in plants:
        en_name  = p["en"][0] if p["en"] else ""
        yo_name  = p["yo"][0] if p["yo"] else ""
        es_name  = p["es"][0] if p["es"] else ""
        ru_key   = p["ritual_use"] or ""
        ru_label = RITUAL_LABEL.get(ru_key, "")
        ac_key   = p["access_key"] or ""

        cards.append(f"""\
    <a class="plant-card" href="plant/{H(p['id'])}.html"
       data-search="{H((p['prefLabel']+' '+p['scientific']+' '+en_name+' '+yo_name+' '+es_name).lower())}"
       data-ritual="{H(ru_label)}">
      <div class="plant-id">{H(p['id'])}</div>
      <div class="plant-pref">{H(p['prefLabel'])}</div>
      <div class="plant-sci">{H(p['scientific'])}</div>
      <div class="name-block" data-lang="en"><div class="plant-en">{H(en_name)}</div></div>
      <div class="name-block" data-lang="yo"><div class="plant-en">{H(yo_name)}</div></div>
      <div class="name-block" data-lang="es"><div class="plant-en">{H(es_name)}</div></div>
      <div class="name-block" data-lang="pt"><div class="plant-en" style="color:var(--ink-soft);font-style:italic;">pt-BR pending</div></div>
      <div class="plant-card-foot">
        {access_badge(ac_key)}
        {"<span class='collision-notice'>⚠ Name collision</span>" if p['name_collision'] else ""}
      </div>
    </a>""")

    filter_pills = '<button class="filter-pill active" data-ritual="">All</button>\n'
    for rl in ritual_labels:
        filter_pills += f'    <button class="filter-pill" data-ritual="{H(rl)}">{H(rl)}</button>\n'

    page = f"""<!DOCTYPE html>
<html lang="en" data-lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Ewé Database — Iroko Historical Society</title>
  <link rel="stylesheet" href="ewe-style.css">
</head>
<body data-lang="en">

{TOP_BAR}

<div class="page-wrap">

  <header class="explorer-hero">
    <div class="explorer-hero-logo">
      <a href="https://www.irokosociety.org"><img src="assets/IHS-Logo.jpg" alt="Iroko Historical Society"></a>
    </div>
    <div>
      <div class="explorer-eyebrow">Iroko Historical Society · Afro-Atlantic Sacred Plant Knowledge</div>
      <h1 class="explorer-title">Ewé Database<br><em>Verger Collection</em></h1>
      <p class="explorer-sub">
        50 sacred plants from Pierre Fatumbi Verger&#x2019;s <em>Ewé: The Use of Plants in Yoruba Society</em>
        and Dalia Quiros-Moran&#x2019;s <em>Guide to Afro-Cuban Herbalism</em>.
        Vocabulary governed by the Iroko Framework. Knowledge access tiers reflect community
        authorization protocols, not editorial choice.
      </p>
      <div style="margin-top:1.2rem; display:flex; gap:1rem; align-items:center; flex-wrap:wrap;">
        {lang_toggle()}
        <span style="font-family:var(--mono);font-size:.65rem;color:var(--ink-soft);">
          Toggle name language display
        </span>
      </div>
    </div>
  </header>

  <div class="search-bar" style="margin-top:2rem;">
    <input class="search-input" type="search" id="plantSearch"
      placeholder="Search by name, scientific name, or vernacular…" autocomplete="off">
    <span class="search-count" id="searchCount">{len(plants)} plants</span>
  </div>

  <div class="filter-row" id="ritualFilter">
    {filter_pills}
  </div>

  <div class="plant-grid" id="plantGrid">
{chr(10).join(cards)}
  </div>

{FOOTER}

</div>

{LANG_JS}

<script>
(function(){{
  var searchEl  = document.getElementById('plantSearch');
  var countEl   = document.getElementById('searchCount');
  var cards     = document.querySelectorAll('.plant-card');
  var pills     = document.querySelectorAll('#ritualFilter .filter-pill');
  var activeRitual = '';

  function applyFilters() {{
    var query = searchEl.value.toLowerCase().trim();
    var visible = 0;
    cards.forEach(function(card) {{
      var matchSearch  = !query || card.dataset.search.includes(query);
      var matchRitual  = !activeRitual || card.dataset.ritual === activeRitual;
      var show = matchSearch && matchRitual;
      card.classList.toggle('hidden', !show);
      if(show) visible++;
    }});
    countEl.textContent = visible + ' plant' + (visible !== 1 ? 's' : '');
  }}

  searchEl.addEventListener('input', applyFilters);

  pills.forEach(function(pill) {{
    pill.addEventListener('click', function() {{
      pills.forEach(function(p) {{ p.classList.remove('active'); }});
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
    print(f"  ✓ index.html  ({len(plants)} plant cards)")

# ── Per-plant page ────────────────────────────────────────────────────────────
def build_plant(p, prev_id, next_id, out_dir):
    pid = p["id"]

    def names_block(label, names, lang_code, fallback=""):
        if not names and not fallback:
            return ""
        items = names if names else [fallback]
        lis = "\n".join(f"<li>{H(n)}</li>" for n in items)
        return f"""\
<div class="detail-row">
  <div class="detail-label">{H(label)}</div>
  <div class="name-block" data-lang="{lang_code}">
    <ul class="name-list">{lis}</ul>
  </div>
</div>"""

    def gated_row(label, value_html, access_key):
        value_part = gated_value(value_html, access_key)
        return f"""\
<div class="detail-row">
  <div class="detail-label">{H(label)}</div>
  <div class="detail-value">{value_part}</div>
</div>"""

    # ── Names section ────────────────────────────────────────────────────────
    ac = p["access_key"] or "access-public-unrestricted"

    en_block = names_block("English", p["en"], "en")
    yo_block = names_block("Yoruba", p["yo"], "yo")
    es_block = names_block("Spanish / Cuban", p["es"], "es")
    pt_block  = f"""\
<div class="detail-row">
  <div class="detail-label">Brazilian Portuguese</div>
  <div class="name-block" data-lang="pt">
    <div style="font-family:var(--mono);font-size:.7rem;color:var(--ink-soft);font-style:italic;">
      Portuguese names from the forthcoming Brazilian manuscript. Not yet in dataset.
    </div>
  </div>
</div>"""

    # Lucumi names — always gated at community-only minimum
    lucumi_key = ac if ac not in ("access-public-unrestricted",) else "access-community-only"
    lucumi_label_str = ", ".join(H(n) for n in p["lucumi"]) if p["lucumi"] else ""
    lucumi_value_html = f'<span class="detail-value-serif">{lucumi_label_str}</span>' if lucumi_label_str else ""
    lucumi_block = gated_row("Lucumí Names", lucumi_value_html, lucumi_key)

    # Other vernacular names — tag cloud
    def format_pill(name):
        if " – " in name or " - " in name:
            sep = " – " if " – " in name else " - "
            parts = name.split(sep, 1)
            return f'<span class="tag-pill"><span class="country-prefix">{H(parts[0])} ·</span>{H(parts[1])}</span>'
        return f'<span class="tag-pill">{H(name)}</span>'

    other_pills = "\n".join(format_pill(n) for n in p["other"]) if p["other"] else ""
    other_cloud = f"""\
<div class="detail-row">
  <div class="detail-label">Other Regional Names</div>
  <div class="tag-cloud">{other_pills if other_pills else
    '<span style="font-family:var(--mono);font-size:.7rem;color:var(--ink-soft);">None recorded</span>'}</div>
</div>"""

    # ── Ritual / medicinal / notes ───────────────────────────────────────────
    ru_slug  = p["ritual_use"] or ""
    ru_label = RITUAL_LABEL.get(ru_slug, ru_slug.replace("-", " ").title() if ru_slug else "")
    ru_html  = f'<span class="use-value">{H(ru_label)}</span>' if ru_label else ""
    ritual_block = gated_row("Ritual Use", ru_html, ac)

    mu_slug  = p["medicinal_use"] or ""
    mu_label = MEDICINAL_LABEL.get(mu_slug, mu_slug.replace("-", " ").title() if mu_slug else "")
    mu_html  = f'<span class="use-value">{H(mu_label)}</span>' if mu_label else ""
    medicinal_block = gated_row("Medicinal Use", mu_html, ac)

    notes_html = f'<p style="font-size:.88rem;color:var(--ink-mid);line-height:1.6;">{H(p["ritual_notes"])}</p>' if p["ritual_notes"] else ""
    notes_block = gated_row("Ritual Notes", notes_html, ac)

    # ── Collision badge ──────────────────────────────────────────────────────
    collision_html = ""
    if p["name_collision"]:
        collision_html = '<span class="collision-notice">⚠ Name collision recorded</span>'

    # ── Access level display ─────────────────────────────────────────────────
    ac_badge_lg = access_badge(ac, size="large")

    # ── Prev / next nav ──────────────────────────────────────────────────────
    prev_link = f'<a href="{H(prev_id)}.html">← {H(prev_id)}</a>' if prev_id else '<span></span>'
    next_link = f'<a href="{H(next_id)}.html">{H(next_id)} →</a>' if next_id else '<span></span>'

    has_pt = bool(p["pt"])

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{H(p['prefLabel'])} — Ewé Database</title>
  <link rel="stylesheet" href="../ewe-style.css">
</head>
<body data-lang="en">

{TOP_BAR_PLANT}

<div class="page-wrap">

  <p class="breadcrumb">
    <a href="../index.html">Ewé Database</a>
    <span>/</span>
    {H(pid)}
  </p>

  <header class="plant-header">
    <div class="plant-header-top">
      <div class="plant-header-title">
        <div class="plant-pref-large">{H(p['prefLabel'])}</div>
        <div class="plant-sci-large">{H(p['scientific'])}</div>
        <div class="plant-id-label">{H(pid)} · iroko:EwePlantRecord</div>
      </div>
      {lang_toggle(has_pt)}
    </div>
    <div class="plant-header-meta">
      {ac_badge_lg}
      {collision_html}
    </div>
  </header>

  <div class="detail-grid">

    <div class="detail-section">
      <div class="detail-section-title">Names by Language</div>
      {en_block}
      {yo_block}
      {es_block}
      {pt_block}
      {lucumi_block}
    </div>

    <div class="detail-section">
      <div class="detail-section-title">Regional & Vernacular Names</div>
      {other_cloud}
    </div>

  </div>

  <div class="detail-grid">

    <div class="detail-section">
      <div class="detail-section-title">Sacred Knowledge</div>
      {ritual_block}
      {notes_block}
    </div>

    <div class="detail-section">
      <div class="detail-section-title">Classification</div>
      {medicinal_block}
      <div class="detail-row">
        <div class="detail-label">Scientific Name</div>
        <div class="detail-value" style="font-style:italic;">{H(p['scientific'])}</div>
      </div>
      <div class="detail-row">
        <div class="detail-label">Iroko URI</div>
        <div class="detail-value">
          <a href="{H(p['uri'])}" style="font-family:var(--mono);font-size:.72rem;word-break:break-all;">
            {H(p['uri'])}
          </a>
        </div>
      </div>
      <div class="detail-row">
        <div class="detail-label">Vocabulary</div>
        <div class="detail-value">
          <a href="https://ontology.irokosociety.org/vocab/iroko-ewe.html"
             style="font-family:var(--mono);font-size:.72rem;">iroko-ewe ↗</a>
        </div>
      </div>
    </div>

  </div>

  <div class="plant-nav">
    {prev_link}
    <a href="../index.html">All Plants</a>
    {next_link}
  </div>

{FOOTER_PLANT}

</div>

{LANG_JS}
</body>
</html>"""

    (out_dir / f"{pid}.html").write_text(page, encoding="utf-8")

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ttl",  default="Verger_Ewe_Dataset.ttl")
    parser.add_argument("--out",  default="ewe-explorer-output")
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

    # Write CSS
    (out_dir / "ewe-style.css").write_text(EWE_CSS, encoding="utf-8")
    print("  ✓ ewe-style.css")

    # Copy logo if provided
    if args.logo and Path(args.logo).exists():
        shutil.copy(args.logo, asset_dir / "IHS-Logo.jpg")
        print(f"  ✓ assets/IHS-Logo.jpg")

    # Index
    build_index(plants, out_dir)

    # Plant pages
    for i, p in enumerate(plants):
        prev_id = plants[i-1]["id"] if i > 0 else None
        next_id = plants[i+1]["id"] if i < len(plants)-1 else None
        build_plant(p, prev_id, next_id, plant_dir)

    print(f"\n{'─'*50}")
    print(f"Done: {len(plants)+2} files written to {out_dir}/")
    print(f"  index.html + ewe-style.css + {len(plants)} plant pages")

if __name__ == "__main__":
    main()
