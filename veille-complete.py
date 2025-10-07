# -*- coding: utf-8 -*-
"""
Veille automatique Stages/Emplois — Relations internationales & domaines connexes
Version : 2025-10-07 (Europe/London)

Fonctions clés :
- Agrège des offres via HTML ET surtout via RSS/API plus stables.
- Filtre par mots-clés riches (IR/diplomatie/Moyen-Orient + catégories larges).
- Ne notifie que les nouveautés par rapport à la veille (seen_links.json).
- Sauvegarde un JSON daté + envoie un résumé vers Telegram.
- Journalisation claire et résiliente (retries, timeouts, SSL, limites Telegram).

Secrets attendus dans GitHub Actions :
- TELEGRAM_TOKEN
- TELEGRAM_CHAT_ID
"""

import os
import re
import json
import time
import certifi
import datetime
import traceback
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
import feedparser

# ---------- Utilitaires généraux ----------

def iso_today():
    return datetime.date.today().isoformat()

def iso_yesterday():
    return (datetime.date.today() - datetime.timedelta(days=1)).isoformat()

def safe_get(url, headers=None, timeout=25, max_retries=2, verify_ssl=True):
    err = None
    if headers is None:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/124.0 Safari/537.36"
        }
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(
                url,
                headers=headers,
                timeout=timeout,
                verify=certifi.where() if verify_ssl else False
            )
            resp.raise_for_status()
            return resp
        except Exception as e:
            err = e
            time.sleep(1.5 * attempt)
    raise err

def truncate(s, n=300):
    if s is None:
        return ""
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= n else s[: n - 1] + "…"

def chunk_telegram(text, limit=4096):
    parts = []
    buf = []
    size = 0
    for line in text.splitlines(True):  # conserve \n
        line_len = len(line)
        if size + line_len > limit:
            parts.append("".join(buf))
            buf, size = [line], line_len
        else:
            buf.append(line)
            size += line_len
    if buf:
        parts.append("".join(buf))
    return parts

# ---------- Classe de veille ----------

class VeilleStagesComplete:
    def __init__(self):
        # Telegram
        self.telegram_token = os.environ.get("TELEGRAM_TOKEN")
        self.telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID")

        # Dates
        self.hier = iso_yesterday()
        self.aujourd_hui = iso_today()

        # État des liens déjà vus
        self.seen_path = "seen_links.json"
        self.seen = self._load_seen()

        # Mots-clés étendus
        base_ir = [
            "relations internationales", "international relations", "diplomatie", "diplomacy",
            "sécurité internationale", "international security", "défense", "defense",
            "géopolitique", "geopolitics", "politique étrangère", "foreign policy",
            "analyse de données", "data analysis", "data scientist", "quantitative", "qualitative",
            "open source", "osint", "policy", "research assistant", "analyste", "researcher",
            "think tank", "ngos", "ngo", "ong", "charity",
            "moyen-orient", "middle east", "proche-orient", "near east", "iran", "turkey", "turquie",
            "lebanon", "liban", "syria", "syrie", "iraq", "irak", "saudi", "émirats", "uae",
            "qatar", "yemen", "oman", "israel", "palestine", "egypt", "egypte", "jordan", "jordanie",
            "caucasus", "caucase", "armenia", "azerbaijan", "georgia", "géorgie",
            "union européenne", "european union", "ue", "eu", "commission", "parlement européen",
            "otan", "nato", "onu", "un", "osce", "odhir", "coe", "council of europe",
            "ambassade", "embassy", "consulat", "consulate", "institut culturel", "cultural institute",
            "alliances françaises", "alliance française", "institut français",
            "stage", "intern", "internship", "trainee", "traineeship", "stagiaire",
            "assistant", "junior", "entry-level", "graduate programme", "programme diplômé",
            "bachelor", "licence", "bac+3", "césure", "gap year", "6 mois", "12 mois", "1 an",
            "vie", "via", "volontariat international", "service civique", "service national universel",
            "schuman", "blue book", "traineeships"
        ]

        # Catégories plus larges demandées
        larges = [
            "accueil", "accueil du public", "front desk", "reception",
            "finance", "financial", "comptabilité", "accounting", "budget", "grants",
            "voyage", "travel", "logistics", "visa", "procurement",
            "académique", "academic", "université", "university", "research centre",
            "sports", "sport", "événementiel", "events", "event",
            "bibliothèque", "library", "documentation", "archives",
            "communication", "communications", "digital", "content", "editorial", "web",
            "press", "presse", "media", "journalism", "public affairs", "advocacy",
            "humanitarian", "relief", "development", "développement"
        ]

        self.keywords = [k.lower() for k in base_ir + larges]

        # Zones géographiques cibles (filtrage assoupli)
        self.zones = [z.lower() for z in [
            "europe", "france", "royaume-uni", "uk", "londres", "bruxelles", "brussels",
            "strasbourg", "genève", "geneva", "berlin", "rome", "madrid", "lisbon", "vienna",
            "canada", "ottawa", "montreal", "montréal", "toronto", "vancouver",
            "moyen-orient", "proche-orient", "middle east", "near east", "iran", "turkey",
            "lebanon", "syria", "iraq", "saudi", "uae", "qatar", "oman", "yemen", "israel",
            "palestine", "egypt", "jordan", "armenia", "azerbaijan", "georgia"
        ]]

        # Fenêtre temporelle indicative demandée dans votre brief
        self.duree_terms = [t.lower() for t in [
            "6 mois", "12 mois", "1 an", "18 mois", "24 mois",
            "avril 2026", "2026", "2027", "long term", "long terme"
        ]]

        # Sources RSS — plus fiables dans les environnements CI
        self.rss_urls = [
            # Général
            "https://www.indeed.fr/rss?q=stage+relations+internationales",
            "https://reliefweb.int/feeds/world",
            # IR/IO
            "https://careers.un.org/feed/RSS.aspx?Lang=FR",
            "https://jobs.osce.org/feed",
            # Recherche / acad / développement
            "https://euraxess.ec.europa.eu/jobs/feed",
            # Fil d’actu MEAE utile pour repérer des pages carrières
            "https://www.diplomatie.gouv.fr/fr/actualites/rss/",
        ]

        # Quelques sources HTML (best-effort, sélecteurs prudents)
        self.sources_html = [
            {
                "nom": "OSCE Jobs HTML",
                "url": "https://jobs.osce.org/",
                "selector": ".views-row, .vacancy, .job-listing",
                "date_selector": ".date, .date-published, time",
                "title_selector": "h3, .title, a",
                "link_selector": "a",
                "location_selector": ".location, .field--name-field-location",
                "description_selector": ".summary, .teaser, .field--name-body"
            },
            {
                "nom": "EUISS Traineeships",
                "url": "https://www.iss.europa.eu/about-us/opportunities",
                "selector": ".node--type-opportunity, .view-content .views-row",
                "date_selector": "time, .date",
                "title_selector": "h2 a, h3 a, h2, h3",
                "link_selector": "a",
                "location_selector": ".field--name-field-location, .meta",
                "description_selector": ".field--name-body, .teaser, p"
            },
            {
                "nom": "EU-Japan Centre Internships",
                "url": "https://www.eu-japan.eu/internships",
                "selector": ".node, .block, article",
                "date_selector": "time, .date",
                "title_selector": "h2 a, h3 a, h2, h3",
                "link_selector": "a",
                "location_selector": "em, strong, .location",
                "description_selector": "p"
            },
                        {
                "nom": "AFD - Agence Française de Développement",
                "url": "https://www.afd.fr/fr/carrieres",
                "selector": ".job-offer, .offre-emploi",
                "date_selector": ".date-publication",
                "title_selector": ".job-title, h3",
                "link_selector": "a",
                "location_selector": ".job-location",
                "description_selector": ".job-description"
            },
            {
                "nom": "CFI - Agence française de développement médias",
                "url": "https://www.cfi.fr/recrutement",
                "selector": ".job-listing",
                "date_selector": ".date",
                "title_selector": ".title",
                "link_selector": "a",
                "location_selector": ".location",
                "description_selector": ".excerpt"
            },
            {
                "nom": "Expertise France",
                "url": "https://www.expertisefrance.fr/recrutement",
                "selector": ".offre, .job-item",
                "date_selector": ".date-publication",
                "title_selector": ".titre",
                "link_selector": "a",
                "location_selector": ".lieu",
                "description_selector": ".description"
            },
            {
                "nom": "France Volontaires",
                "url": "https://france-volontaires.org/offres-emploi",
                "selector": ".job-offer",
                "date_selector": ".date",
                "title_selector": "h3",
                "link_selector": "a",
                "location_selector": ".location",
                "description_selector": ".summary"
            },
            {
                "nom": "CIRAD",
                "url": "https://www.cirad.fr/nous-rejoindre",
                "selector": ".offre-emploi",
                "date_selector": ".date",
                "title_selector": ".titre",
                "link_selector": "a",
                "location_selector": ".lieu",
                "description_selector": ".resume"
            },
            {
                "nom": "IRD - Institut de Recherche pour le Développement",
                "url": "https://www.ird.fr/nous-rejoindre",
                "selector": ".job-listing",
                "date_selector": ".date",
                "title_selector": ".title",
                "link_selector": "a",
                "location_selector": ".location",
                "description_selector": ".description"
            },
            
            # === OPÉRATEURS MEAE - CULTURE, ÉDUCATION, FRANCOPHONIE ===
            {
                "nom": "Institut français",
                "url": "https://www.institutfrancais.com/fr/carrieres",
                "selector": ".job-offer",
                "date_selector": ".date",
                "title_selector": ".title",
                "link_selector": "a",
                "location_selector": ".location",
                "description_selector": ".summary"
            },
            {
                "nom": "AEFE - Agence pour l'enseignement français à l'étranger",
                "url": "https://www.aefe.fr/vie-du-reseau/ressources-humaines",
                "selector": ".offre",
                "date_selector": ".date",
                "title_selector": ".titre",
                "link_selector": "a",
                "location_selector": ".lieu",
                "description_selector": ".description"
            },
            {
                "nom": "Campus France",
                "url": "https://www.campusfrance.org/fr/recrutement",
                "selector": ".job-listing",
                "date_selector": ".date",
                "title_selector": ".title",
                "link_selector": "a",
                "location_selector": ".location",
                "description_selector": ".excerpt"
            },
            
            # === OPÉRATEURS MEAE - COMMERCE EXTÉRIEUR ===
            {
                "nom": "Business France - VIE/VIA",
                "url": "https://mon-vie-via.businessfrance.fr/",
                "selector": ".offer-item, .job-item",
                "date_selector": ".date-publication",
                "title_selector": ".offer-title, h3",
                "link_selector": "a",
                "location_selector": ".offer-location",
                "description_selector": ".offer-description"
            },
            {
                "nom": "Business France - Emplois",
                "url": "https://businessfrance-recrute.talent-soft.com/",
                "selector": ".job-listing",
                "date_selector": ".date",
                "title_selector": ".title",
                "link_selector": "a",
                "location_selector": ".location",
                "description_selector": ".summary"
            },
            
            # === ORGANISATIONS INTERNATIONALES ===
            {
                "nom": "ONU Carrières",
                "url": "https://careers.un.org/lbw/home.aspx?lang=FR",
                "selector": ".job-item, .vacancy",
                "date_selector": ".posting-date, .date-posted",
                "title_selector": ".job-title, h3",
                "link_selector": "a",
                "location_selector": ".duty-station, .location",
                "description_selector": ".job-summary, .description"
            },
            {
                "nom": "OSCE Jobs",
                "url": "https://jobs.osce.org/",
                "selector": ".vacancy, .job-listing",
                "date_selector": ".date-published, .date",
                "title_selector": ".title, h3",
                "link_selector": "a",
                "location_selector": ".location",
                "description_selector": ".summary, .description"
            },
            {
                "nom": "OTAN Stages",
                "url": "https://www.nato.int/cps/fr/natolive/72041.htm",
                "selector": ".internship-listing",
                "date_selector": ".date",
                "title_selector": ".title",
                "link_selector": "a",
                "location_selector": ".location",
                "description_selector": ".description"
            },
            
            # === UNION EUROPÉENNE ===
            {
                "nom": "Commission européenne - Stages",
                "url": "https://ec.europa.eu/stages/home_fr",
                "selector": ".stage-offer",
                "date_selector": ".date",
                "title_selector": ".title",
                "link_selector": "a",
                "location_selector": ".location",
                "description_selector": ".description"
            },
            {
                "nom": "Parlement européen - Stages Schuman",
                "url": "https://ep-stages.gestmax.eu/website/homepage",
                "selector": ".stage-listing",
                "date_selector": ".date",
                "title_selector": ".title",
                "link_selector": "a",
                "location_selector": ".location",
                "description_selector": ".summary"
            },
            {
                "nom": "EUISS - Institut d'études de sécurité",
                "url": "https://www.iss.europa.eu/about-us/opportunities/euiss-traineeships-2025-2026",
                "selector": ".opportunity",
                "date_selector": ".date",
                "title_selector": ".title",
                "link_selector": "a",
                "location_selector": ".location",
                "description_selector": ".description"
            },
            {
                "nom": "EU-Japan Centre",
                "url": "https://www.eu-japan.eu/internships",
                "selector": ".internship-offer",
                "date_selector": ".date",
                "title_selector": ".title",
                "link_selector": "a",
                "location_selector": ".location",
                "description_selector": ".description"
            },
            
            # === THINK TANKS ET INSTITUTS ===
            {
                "nom": "IFRI",
                "url": "https://www.ifri.org/fr/recrutement",
                "selector": ".job-offer",
                "date_selector": ".date",
                "title_selector": ".title",
                "link_selector": "a",
                "location_selector": ".location",
                "description_selector": ".summary"
            },
            {
                "nom": "Institut du Monde Arabe",
                "url": "https://www.imarabe.org/fr/nous-rejoindre",
                "selector": ".offre",
                "date_selector": ".date",
                "title_selector": ".titre",
                "link_selector": "a",
                "location_selector": ".lieu",
                "description_selector": ".description"
            },
            {
                "nom": "Foundation Alliance Française",
                "url": "https://www.fondation-alliancefr.org/?cat=803",
                "selector": ".job-listing",
                "date_selector": ".date",
                "title_selector": ".title",
                "link_selector": "a",
                "location_selector": ".location",
                "description_selector": ".excerpt"
            },
            
            # === AUTRES SOURCES IMPORTANTES ===
            {
                "nom": "Trésor International",
                "url": "https://www.tresor.economie.gouv.fr/tresor-international",
                "selector": ".offre",
                "date_selector": ".date",
                "title_selector": ".titre",
                "link_selector": "a",
                "location_selector": ".lieu",
                "description_selector": ".description"
            },
            {
                "nom": "Sciences Po Carrières",
                "url": "https://www.sciencespo.fr/carrieres/fr/stages/",
                "selector": ".stage-offer",
                "date_selector": ".date",
                "title_selector": ".title",
                "link_selector": "a",
                "location_selector": ".location",
                "description_selector": ".description"
            }
        ]

    # ---------- Persistance des liens vus ----------

    def _load_seen(self):
        if os.path.exists(self.seen_path):
            try:
                with open(self.seen_path, "r", encoding="utf-8") as f:
                    return set(json.load(f))
            except Exception:
                return set()
        return set()

    def _save_seen(self):
        try:
            with open(self.seen_path, "w", encoding="utf-8") as f:
                json.dump(sorted(list(self.seen)), f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ---------- Critères ----------

    def match_keywords(self, text):
        t = text.lower()
        return any(kw in t for kw in self.keywords)

    def match_zone(self, text):
        t = text.lower()
        return any(z in t for z in self.zones)

    def match_duree(self, text):
        t = text.lower()
        return any(d in t for d in self.duree_terms)

    def is_prioritaire(self, text):
        t = text.lower()
        return any(p in t for p in [
            "iran", "moyen-orient", "middle east", "sécurité internationale",
            "vie", "via", "ambassade", "consulat", "think tank", "schuman", "blue book"
        ])

    # ---------- Extraction RSS ----------

    def extraire_offres_rss(self, url):
        print(f"🔎 RSS → {url}")
        offres = []
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                titre = entry.get("title", "").strip()
                lien = entry.get("link", "").strip()
                desc = entry.get("summary", "") or entry.get("description", "")
                date_pub = entry.get("published", "") or entry.get("updated", "") or ""

                if not lien:
                    continue

                texte = f"{titre} {desc}".lower()
                if not self.match_keywords(texte):
                    continue

                # Souplesse : zone OU durée OU mots-clés seuls si org pertinente
                zone_ok = self.match_zone(texte)
                duree_ok = self.match_duree(texte)

                if not (zone_ok or duree_ok):
                    # On laisse passer si c'est clairement IR/IO
                    if not any(x in texte for x in ["un ", " osce", "nato", "eu ", "commission", "parliament", "ngo", "think tank"]):
                        continue

                offres.append({
                    "date": date_pub,
                    "organisation": "RSS",
                    "titre": titre,
                    "lieu": "",
                    "lien": lien,
                    "description": truncate(BeautifulSoup(desc, "html.parser").get_text(" "))
                })
        except Exception as e:
            print(f"❌ RSS error: {e}")
        print(f"✅ RSS offres retenues: {len(offres)}")
        return offres

    # ---------- Extraction HTML ----------

    def extraire_offres_html(self, source):
        print(f"🌐 HTML → {source['nom']} | {source['url']}")
        offres = []
        try:
            resp = safe_get(source["url"])
            soup = BeautifulSoup(resp.text, "lxml")

            for job in soup.select(source["selector"])[:30]:
                try:
                    title_el = job.select_one(source["title_selector"])
                    link_el = job.select_one(source["link_selector"])
                    date_el = job.select_one(source["date_selector"])
                    loc_el = job.select_one(source["location_selector"])
                    desc_el = job.select_one(source["description_selector"])

                    titre = (title_el.get_text(" ", strip=True) if title_el else "").strip()
                    href = (link_el.get("href") if link_el else "").strip()
                    lien = urljoin(source["url"], href) if href else source["url"]
                    date_pub = (date_el.get_text(" ", strip=True) if date_el else "").strip()
                    lieu = (loc_el.get_text(" ", strip=True) if loc_el else "")
                    description = truncate(BeautifulSoup(
                        desc_el.get_text(" ", strip=True) if desc_el else "", "html.parser"
                    ).get_text(" "))

                    blob = f"{titre} {description} {lieu}"
                    if not self.match_keywords(blob):
                        continue

                    zone_ok = self.match_zone(blob)
                    duree_ok = self.match_duree(blob)
                    if not (zone_ok or duree_ok):
                        # tolérer si la source elle-même est pertinente
                        if source["nom"].lower().startswith(("osce", "euiss", "eu-japan", "commission", "parlement")):
                            pass
                        else:
                            continue

                    offres.append({
                        "date": date_pub,
                        "organisation": source["nom"],
                        "titre": titre or "Titre non disponible",
                        "lieu": lieu or "Non précisé",
                        "lien": lien,
                        "description": description or "—"
                    })
                except Exception:
                    continue
        except Exception as e:
            print(f"❌ HTML error {source['nom']}: {e}")
        print(f"✅ HTML offres retenues: {len(offres)}")
        return offres

    # ---------- Filtrage nouveautés & priorisation ----------

    def dedupe_and_new_only(self, offres):
        nouveaux = []
        uniques = set()
        for o in offres:
            key = o["lien"].strip()
            if not key or key in uniques:
                continue
            uniques.add(key)
            if key not in self.seen:
                nouveaux.append(o)
        return nouveaux

    def sort_prioritaires_first(self, offres):
        return sorted(
            offres,
            key=lambda o: (0 if self.is_prioritaire(f"{o['titre']} {o['description']}") else 1, o.get("organisation",""), o.get("titre",""))
        )

    # ---------- Sortie fichiers ----------

    def save_of_day(self, offres):
        fn = f"offres_{self.aujourd_hui}.json"
        try:
            with open(fn, "w", encoding="utf-8") as f:
                json.dump({
                    "date_execution": self.aujourd_hui,
                    "total": len(offres),
                    "offres": offres
                }, f, ensure_ascii=False, indent=2)
            print(f"💾 Sauvegarde: {fn}")
        except Exception as e:
            print(f"❌ Erreur sauvegarde {fn}: {e}")

    # ---------- Telegram ----------

    def send_telegram(self, offres):
        if not self.telegram_token or not self.telegram_chat_id:
            print("⚠️ Telegram non configuré (TELEGRAM_TOKEN / TELEGRAM_CHAT_ID).")
            return

        if not offres:
            msg = f"📭 Veille du {self.aujourd_hui} — aucune nouvelle offre pertinente."
            self._telegram_post(msg)
            return

        head = f"🎯 Veille du {self.aujourd_hui} — {len(offres)} nouvelle(s) offre(s)\n"
        lines = [head]
        max_preview = 15
        for i, o in enumerate(offres[:max_preview], 1):
            prio = "🔥" if self.is_prioritaire(f"{o['titre']} {o['description']}") else "📄"
            org = o.get("organisation","").strip()
            lieu = o.get("lieu","").strip()
            titre = o.get("titre","").strip()
            lien = o.get("lien","").strip()
            line = f"{i:02d}. {prio} {titre} — {org}"
            if lieu and lieu.lower() != "non précisé":
                line += f" ({lieu})"
            line += f"\n{lien}\n"
            lines.append(line)

        if len(offres) > max_preview:
            lines.append(f"… et {len(offres) - max_preview} autres. Fichier JSON du jour dans les artefacts.\n")

        payload = "".join(lines)
        for part in chunk_telegram(payload):
            self._telegram_post(part)

    def _telegram_post(self, text):
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            resp = requests.post(url, data={
                "chat_id": self.telegram_chat_id,
                "text": text
            }, timeout=15)
            if resp.ok:
                print("✅ Telegram OK")
            else:
                print(f"❌ Telegram HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            print(f"❌ Telegram exception: {e}")

    # ---------- Orchestration ----------

    def executer_veille(self):
        print(f"🚀 Début veille — {self.aujourd_hui}")
        print(f"• Mots-clés: {len(self.keywords)} | Zones: {len(self.zones)} | Durée: {len(self.duree_terms)}")
        toutes = []

        # RSS d’abord (plus robustes en CI)
        for rss in self.rss_urls:
            try:
                toutes.extend(self.extraire_offres_rss(rss))
            except Exception:
                print(traceback.format_exc())
            time.sleep(1)

        # HTML ensuite (best-effort)
        for src in self.sources_html:
            try:
                toutes.extend(self.extraire_offres_html(src))
            except Exception:
                print(traceback.format_exc())
            time.sleep(1.5)

        # Nouveautés seulement
        nouvelles = self.dedupe_and_new_only(toutes)
        nouvelles = self.sort_prioritaires_first(nouvelles)

        # Persistance
        self.save_of_day(nouvelles)

        # Mise à jour du “vu”
        for o in nouvelles:
            self.seen.add(o["lien"])
        self._save_seen()

        # Envoi Telegram
        self.send_telegram(nouvelles)

        # Log console final
        prios = sum(1 for o in nouvelles if self.is_prioritaire(f"{o['titre']} {o['description']}"))
        print(f"📊 Total collectées: {len(toutes)} | Nouvelles: {len(nouvelles)} | Prioritaires: {prios}")
        print("✅ Veille terminée.")

# --------- Entrée principale ---------

if __name__ == "__main__":
    bot = VeilleStagesComplete()
    bot.executer_veille()
