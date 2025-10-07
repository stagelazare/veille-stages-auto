import requests
from bs4 import BeautifulSoup
import datetime
import time
import re
import os
import json
import feedparser
import certifi
from urllib.parse import urljoin, urlparse

class VeilleStagesComplete:
    def __init__(self):
        # Configuration Telegram via GitHub Secrets
        self.telegram_token = os.environ.get('TELEGRAM_TOKEN')
        self.telegram_chat_id = os.environ.get('TELEGRAM_CHAT_ID')

        # Dates
        self.hier = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        self.aujourd_hui = datetime.date.today().isoformat()

        # Mots-clés de filtrage
        self.keywords = [
            "relations internationales", "international relations", "diplomatie", "diplomacy",
            "sécurité internationale", "international security", "défense", "defense",
            "analyse de données", "data analysis", "moyen-orient", "middle east",
            "iran", "proche-orient", "near east", "ambassade", "embassy",
            "consulat", "consulate", "think tank", "ong", "ngo",
            "institut culturel", "cultural institute", "otan", "nato",
            "union européenne", "european union", "onu", "un", "osce",
            "stage", "intern", "stagiaire", "internship", "trainee",
            "bachelor", "licence", "césure", "gap year", "6 mois", "12 mois",
            "vie", "via", "volontariat international"
        ]

        # Sources HTML
        self.sources = [
            {
                "nom": "France Diplomatie",
                "url": "https://www.diplomatie.gouv.fr/fr/emplois-stages-concours/",
                "selector": ".job-listing, .offre",
                "date_selector": ".date-posted, .date",
                "title_selector": "h3, .titre",
                "link_selector": "a",
                "location_selector": ".location, .lieu",
                "description_selector": ".description, .resume"
            },
            {
                "nom": "PASS Fonction Publique",
                "url": "https://www.pass.fonction-publique.gouv.fr/",
                "selector": ".offre, .job-item",
                "date_selector": ".date, .date-publication",
                "title_selector": ".titre, h3",
                "link_selector": "a",
                "location_selector": ".lieu, .location",
                "description_selector": ".resume, .description"
            },
            
            # === OPÉRATEURS DU MEAE - AIDE AU DÉVELOPPEMENT ===
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

         self.rss_urls = [
            "https://www.indeed.fr/rss?q=stage+relations+internationales",
            "https://euraxess.ec.europa.eu/jobs/feed",
            "https://reliefweb.int/feeds/world",
            "https://www.devex.com/jobs/feed",
            "https://careers.un.org/feed/RSS.aspx?Lang=FR",
            "https://jobs.osce.org/feed",
            "https://www.diplomatie.gouv.fr/fr/actualites/rss/"
        ]

        # Sources spécifiques par zone géographique
        self.sources_zones = {
            "Canada": [
                "https://www.international.gc.ca/about-a_propos/employment-emploi/index.aspx",
                "https://ambassadedefrance-ca.org/Travailler-a-l-Ambassade"
            ],
            "Moyen-Orient": [
                "https://www.institutfrancais.com/fr/reseau-culturel-francais-monde",
                "https://www.aefe.fr/vie-du-reseau/ressources-humaines"
            ]
        }

def extraire_offres_rss(self, url):
        print(f"🔍 Extraction RSS {url}...")
        feed = feedparser.parse(url)
        offres = []
        for entry in feed.entries:
            date_pub = entry.get('published', entry.get('updated', ''))
            titre = entry.get('title', '')
            lien = entry.get('link', '')
            desc = entry.get('summary', '')[:200] + '...'
            texte = f"{titre} {desc}".lower()
            if any(kw in texte for kw in self.keywords):
                offres.append({
                    'date': date_pub,
                    'organisation': 'RSS',
                    'titre': titre,
                    'lieu': '',
                    'lien': lien,
                    'description': desc
                })
        print(f"✅ {len(offres)} offres RSS trouvées")
        return offres


    
    
    def extraire_offres_site(self, source):
        print(f"🔍 Extraction HTML {source['nom']}...")
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(source['url'], headers=headers,
                                    timeout=30, verify=certifi.where())
            if response.status_code not in (200, 301, 302):
                print(f"⚠️ Statut {response.status_code} pour {source['nom']}")
                return []
            soup = BeautifulSoup(response.text, 'html.parser')
            offres = []
            for job in soup.select(source['selector'])[:15]:
                try:
                    titre = job.select_one(source['title_selector']).get_text(strip=True)
                    link_elem = job.select_one(source['link_selector'])
                    lien = urljoin(source['url'], link_elem['href']) if link_elem else source['url']
                    lieu = job.select_one(source['location_selector']).get_text(strip=True)
                    desc = job.select_one(source['description_selector']).get_text(strip=True)[:300] + "..."
                    date_pub = job.select_one(source['date_selector']).get_text(strip=True)
                    texte = f"{titre} {desc} {lieu}".lower()
                    if any(kw in texte for kw in self.keywords):
                        offres.append({
                            'date': date_pub,
                            'organisation': source['nom'],
                            'titre': titre,
                            'lieu': lieu,
                            'lien': lien,
                            'description': desc
                        })
                except Exception as e:
                    print(f"⚠️ Erreur offre {source['nom']}: {e}")
            print(f"✅ {len(offres)} offres HTML trouvées")
            return offres
        except Exception as e:
            print(f"❌ Erreur connexion {source['nom']}: {e}")
            return []

    def filtrer_nouvelles_offres(self, offres):
        nouvelles = []
        for o in offres:
            if self.est_offre_pertinente(o):
                nouvelles.append(o)
        return nouvelles

    def est_offre_pertinente(self, o):
        t = f"{o['titre']} {o['description']}".lower()
        return any(kw in t for kw in self.keywords)

    def est_offre_prioritaire(self, o):
        t = f"{o['titre']} {o['description']}".lower()
        return any(kw in t for kw in ["iran","moyen-orient","security","via","vie"])

    def envoyer_rapport(self, offres):
        if not self.telegram_token or not self.telegram_chat_id:
            print("❌ Telegram non configuré")
            return
        if offres:
            text = f"🎯 {len(offres)} offres détectées :\n"
            for o in offres[:10]:
                prio = "🔥" if self.est_offre_prioritaire(o) else "📄"
                text += f"{prio} {o['titre']} - {o['organisation']}\n{o['lien']}\n"
            if len(offres)>10:
                text += f"... et {len(offres)-10} autres\n"
        else:
            text = "📭 Aucune nouvelle offre"
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        resp = requests.post(url, data={
            'chat_id': self.telegram_chat_id,
            'text': text,
            'parse_mode': 'Markdown'
        })
        print("✅ Telegram status", resp.status_code)

    def sauvegarder_resultats(self, offres):
        fn = f"offres_{self.aujourd_hui}.json"
        with open(fn,'w',encoding='utf-8') as f:
            json.dump(offres, f, ensure_ascii=False, indent=2)
        print(f"💾 Sauvegardé {fn}")

    def executer_veille(self):
        print(f"🚀 Veille {self.aujourd_hui}")
        toutes = []
        for src in self.sources:
            toutes += self.extraire_offres_site(src)
            time.sleep(1)
        for rss in self.rss_urls:
            toutes += self.extraire_offres_rss(rss)
            time.sleep(1)
        nouvelles = self.filtrer_nouvelles_offres(toutes)
        self.sauvegarder_resultats(nouvelles)
        self.envoyer_rapport(nouvelles)
        print("✅ Terminé")

if __name__ == "__main__":
    veille = VeilleStagesComplete()
    veille.executer_veille()
