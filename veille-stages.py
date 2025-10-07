# Script de Veille Automatisée des Offres de Stage/Emploi International
# Version complète avec toutes les sources identifiées

import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime
import time
import re
import os
import json
from urllib.parse import urljoin, urlparse

class VeilleStagesComplet:
    def __init__(self):
        # Configuration email (à remplir dans GitHub Secrets)
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.email_from = os.environ.get('EMAIL_FROM')
        self.email_password = os.environ.get('EMAIL_PASSWORD')
        self.email_to = os.environ.get('EMAIL_TO')
        
        # Date d'hier pour filtrer les nouvelles offres
        self.hier = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        self.aujourd_hui = datetime.date.today().isoformat()
        
        # Mots-clés pour filtrer les offres pertinentes
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
        
        # Sources complètes à surveiller
        self.sources = [
            # === MINISTÈRE DE L'EUROPE ET DES AFFAIRES ÉTRANGÈRES ===
            {
                "nom": "France Diplomatie - Stages",
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

    def extraire_offres_site(self, source):
        """Extrait les offres d'un site donné avec gestion d'erreur renforcée"""
        print(f"🔍 Extraction des offres de {source['nom']}...")
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(source['url'], headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            offres = []
            
            # Recherche des offres selon les sélecteurs du site
            job_listings = soup.select(source['selector'])
            
            for job in job_listings[:15]:  # Limite à 15 offres par site
                try:
                    # Extraction des informations
                    titre_elem = job.select_one(source['title_selector'])
                    titre = titre_elem.get_text(strip=True) if titre_elem else "Titre non disponible"
                    
                    link_elem = job.select_one(source['link_selector'])
                    if link_elem and link_elem.get('href'):
                        lien = urljoin(source['url'], link_elem['href'])
                    else:
                        lien = source['url']
                    
                    lieu_elem = job.select_one(source['location_selector'])
                    lieu = lieu_elem.get_text(strip=True) if lieu_elem else "Lieu non spécifié"
                    
                    desc_elem = job.select_one(source['description_selector'])
                    description = desc_elem.get_text(strip=True)[:300] + "..." if desc_elem else "Description non disponible"
                    
                    date_elem = job.select_one(source['date_selector'])
                    date_pub = date_elem.get_text(strip=True) if date_elem else self.aujourd_hui
                    
                    # Vérifier si l'offre contient des mots-clés pertinents
                    texte_complet = f"{titre} {description} {lieu}".lower()
                    if any(keyword.lower() in texte_complet for keyword in self.keywords):
                        
                        # Filtrage par zones géographiques ciblées
                        zones_cibles = [
                            "europe", "france", "canada", "moyen-orient", "middle east",
                            "proche-orient", "near east", "iran", "israel", "palestine",
                            "syrie", "liban", "jordanie", "turquie", "egypt", "maroc",
                            "allemagne", "espagne", "italie", "belgique", "pays-bas",
                            "suisse", "royaume-uni", "bruxelles", "genève", "strasbourg"
                        ]
                        
                        if any(zone in texte_complet for zone in zones_cibles):
                            offres.append({
                                'date': date_pub,
                                'organisation': source['nom'],
                                'titre': titre,
                                'lieu': lieu,
                                'lien': lien,
                                'description': description,
                                'mots_cles': [kw for kw in self.keywords if kw.lower() in texte_complet]
                            })
                        
                except Exception as e:
                    print(f"❌ Erreur lors de l'extraction d'une offre de {source['nom']}: {e}")
                    continue
            
            print(f"✅ {len(offres)} offres pertinentes trouvées sur {source['nom']}")
            return offres
            
        except requests.RequestException as e:
            print(f"❌ Erreur de connexion à {source['nom']}: {e}")
            return []
        except Exception as e:
            print(f"❌ Erreur lors de l'extraction de {source['nom']}: {e}")
            return []

    def filtrer_nouvelles_offres(self, offres):
        """Filtre et priorise les offres selon les critères spécifiques"""
        nouvelles_offres = []
        offres_prioritaires = []
        
        for offre in offres:
            if self.est_offre_pertinente(offre):
                # Priorisation des offres
                if self.est_offre_prioritaire(offre):
                    offres_prioritaires.append(offre)
                else:
                    nouvelles_offres.append(offre)
        
        # Retourner d'abord les prioritaires, puis les autres
        return offres_prioritaires + nouvelles_offres[:20]  # Limite totale

    def est_offre_pertinente(self, offre):
        """Vérifie si une offre correspond aux critères recherchés"""
        titre_desc = f"{offre['titre']} {offre['description']}".lower()
        
        # Critères de durée
        duree_keywords = [
            "6 mois", "12 mois", "1 an", "24 mois", "18 mois",
            "avril 2026", "2026", "2027", "long terme"
        ]
        
        # Critères de niveau
        niveau_keywords = [
            "bachelor", "licence", "bac+3", "master 1", "m1",
            "césure", "gap year", "jeune diplômé", "débutant"
        ]
        
        # Vérification des critères
        a_duree = any(duree in titre_desc for duree in duree_keywords)
        a_niveau = any(niveau in titre_desc for niveau in niveau_keywords)
        a_domaine = any(kw in titre_desc for kw in ["relations internationales", "diplomatie", "sécurité", "moyen-orient", "international"])
        
        return a_duree or a_niveau or a_domaine

    def est_offre_prioritaire(self, offre):
        """Identifie les offres à forte priorité"""
        titre_desc = f"{offre['titre']} {offre['description']}".lower()
        
        priorite_keywords = [
            "iran", "moyen-orient", "middle east", "sécurité internationale",
            "vie", "via", "stage diplomatie", "ambassade", "consulat",
            "think tank", "april 2026", "avril 2026"
        ]
        
        return any(kw in titre_desc for kw in priorite_keywords)

    def generer_rapport_html(self, nouvelles_offres):
        """Génère un rapport HTML enrichi des nouvelles offres"""
        if not nouvelles_offres:
            return f"""
            <html>
            <head>
                <title>Veille Stages - {self.aujourd_hui}</title>
                <meta charset="UTF-8">
            </head>
            <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px;">
                <h2>🔍 Veille quotidienne des stages & emplois internationaux</h2>
                <p><strong>Date:</strong> {self.aujourd_hui}</p>
                <p>Aucune nouvelle offre trouvée aujourd'hui.</p>
                <hr>
                <p><em>Domaines surveillés:</em> Relations internationales, Diplomatie, Sécurité internationale, Moyen-Orient, Iran, Proche-Orient</p>
                <p><em>Zones:</em> Europe, Canada, Moyen-Orient, Proche-Orient</p>
                <p><em>Profil:</em> Fin de licence/Bachelor, durée 6-12 mois, avril 2026-avril 2027</p>
            </body>
            </html>
            """
        
        # Séparer les offres prioritaires des autres
        prioritaires = [o for o in nouvelles_offres if self.est_offre_prioritaire(o)]
        normales = [o for o in nouvelles_offres if not self.est_offre_prioritaire(o)]
        
        html = f"""
        <html>
        <head>
            <title>Nouvelles offres - {self.aujourd_hui}</title>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }}
                .offre {{ border: 1px solid #ddd; margin: 15px 0; padding: 15px; border-radius: 8px; }}
                .offre-prioritaire {{ border-left: 5px solid #e53e3e; background-color: #fff5f5; }}
                .titre {{ color: #2c5282; font-weight: bold; font-size: 18px; }}
                .organisation {{ color: #718096; font-weight: bold; }}
                .lieu {{ color: #e53e3e; }}
                .date {{ color: #38a169; font-size: 12px; }}
                .description {{ margin-top: 10px; color: #4a5568; }}
                .mots-cles {{ margin-top: 5px; font-size: 11px; color: #805ad5; }}
                .lien {{ margin-top: 10px; }}
                a {{ color: #3182ce; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
                .stats {{ background-color: #f7fafc; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <h2>🎯 Nouvelles offres de stage/emploi - {self.aujourd_hui}</h2>
            
            <div class="stats">
                <strong>📊 Résumé:</strong>
                <ul>
                    <li><strong>{len(nouvelles_offres)} nouvelle(s) offre(s)</strong> trouvée(s)</li>
                    <li><strong>{len(prioritaires)} offre(s) prioritaire(s)</strong> (forte correspondance)</li>
                    <li><strong>{len(normales)} offre(s) standard(s)</strong></li>
                </ul>
            </div>
            <hr>
        """
        
        # Affichage des offres prioritaires en premier
        if prioritaires:
            html += "<h3>🔥 Offres prioritaires</h3>"
            for offre in prioritaires:
                html += self.generer_html_offre(offre, prioritaire=True)
        
        if normales:
            html += "<h3>📋 Autres offres pertinentes</h3>"
            for offre in normales:
                html += self.generer_html_offre(offre, prioritaire=False)
        
        html += f"""
            <hr>
            <p><em>🤖 Veille automatisée - Relations internationales, Diplomatie, Sécurité, Moyen-Orient</em></p>
            <p><em>🎯 Profil ciblé: Fin de licence/Bachelor, durée 6-12 mois, avril 2026-avril 2027</em></p>
            <p><em>🌍 Zones: Europe, Canada, Moyen-Orient, Proche-Orient</em></p>
            <p><em>📧 Rapport généré automatiquement par GitHub Actions</em></p>
        </body>
        </html>
        """
        
        return html

    def generer_html_offre(self, offre, prioritaire=False):
        """Génère le HTML pour une offre individuelle"""
        classe_css = "offre offre-prioritaire" if prioritaire else "offre"
        
        mots_cles_html = ""
        if offre.get('mots_cles'):
            mots_cles_html = f'<div class="mots-cles">🔑 Mots-clés: {", ".join(offre["mots_cles"][:5])}</div>'
        
        return f"""
        <div class="{classe_css}">
            <div class="titre">{"🔥 " if prioritaire else ""}{offre['titre']}</div>
            <div class="organisation">📍 {offre['organisation']} - {offre['lieu']}</div>
            <div class="date">📅 Publié: {offre['date']}</div>
            <div class="description">{offre['description']}</div>
            {mots_cles_html}
            <div class="lien">
                <a href="{offre['lien']}" target="_blank">🔗 Voir l'offre complète</a>
            </div>
        </div>
        """

    def envoyer_rapport(self, nouvelles_offres):
        """Envoie le rapport par email avec sujet enrichi"""
        if not self.email_from or not self.email_password or not self.email_to:
            print("❌ Configuration email manquante dans les variables d'environnement")
            return False
        
        try:
            # Calcul des statistiques pour le sujet
            prioritaires = len([o for o in nouvelles_offres if self.est_offre_prioritaire(o)])
            
            if prioritaires > 0:
                sujet = f"🔥 {prioritaires} offre(s) prioritaire(s) + {len(nouvelles_offres)-prioritaires} autres - {self.aujourd_hui}"
            elif nouvelles_offres:
                sujet = f"🎯 {len(nouvelles_offres)} nouvelle(s) offre(s) - {self.aujourd_hui}"
            else:
                sujet = f"📭 Aucune nouvelle offre - {self.aujourd_hui}"
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = sujet
            msg['From'] = self.email_from
            msg['To'] = self.email_to
            
            # Version HTML
            html_content = self.generer_rapport_html(nouvelles_offres)
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Envoi via SMTP
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_from, self.email_password)
                server.sendmail(self.email_from, self.email_to, msg.as_string())
            
            print(f"✅ Rapport envoyé avec succès à {self.email_to}")
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors de l'envoi de l'email: {e}")
            return False

    def sauvegarder_resultats(self, nouvelles_offres):
        """Sauvegarde les résultats avec métadonnées enrichies"""
        filename = f"offres_{self.aujourd_hui}.json"
        
        try:
            # Statistiques détaillées
            stats = {
                'date_execution': self.aujourd_hui,
                'nombre_total_offres': len(nouvelles_offres),
                'nombre_prioritaires': len([o for o in nouvelles_offres if self.est_offre_prioritaire(o)]),
                'sources_actives': len(self.sources),
                'zones_ciblées': ["Europe", "Canada", "Moyen-Orient", "Proche-Orient"],
                'mots_cles_recherches': self.keywords,
                'criteres_duree': ["6 mois", "12 mois", "avril 2026-avril 2027"],
                'profil_cible': "Fin de licence/bachelor, césure"
            }
            
            # Groupement des offres par organisation
            offres_par_org = {}
            for offre in nouvelles_offres:
                org = offre['organisation']
                if org not in offres_par_org:
                    offres_par_org[org] = []
                offres_par_org[org].append(offre)
            
            data = {
                'statistiques': stats,
                'offres_par_organisation': offres_par_org,
                'toutes_offres': nouvelles_offres
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"💾 Résultats sauvegardés dans {filename}")
            
        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde: {e}")

    def executer_veille(self):
        """Exécute le processus complet de veille avec monitoring avancé"""
        print(f"🚀 Début de la veille quotidienne - {self.aujourd_hui}")
        print("=" * 80)
        print(f"📊 Configuration:")
        print(f"   • {len(self.sources)} sources à surveiller")
        print(f"   • {len(self.keywords)} mots-clés de recherche")
        print(f"   • Zones ciblées: Europe, Canada, Moyen-Orient, Proche-Orient")
        print(f"   • Profil: Fin licence/bachelor, 6-12 mois, avril 2026-avril 2027")
        print("=" * 80)
        
        toutes_offres = []
        sources_reussies = 0
        sources_echec = 0
        
        # Extraction des offres de chaque source
        for i, source in enumerate(self.sources, 1):
            print(f"[{i}/{len(self.sources)}] Processing {source['nom']}...")
            
            try:
                offres_site = self.extraire_offres_site(source)
                if offres_site:
                    toutes_offres.extend(offres_site)
                    sources_reussies += 1
                else:
                    sources_echec += 1
                    
            except Exception as e:
                print(f"❌ Échec complet pour {source['nom']}: {e}")
                sources_echec += 1
                
            time.sleep(2)  # Pause respectueuse entre les requêtes
        
        # Filtrage et priorisation des offres
        nouvelles_offres = self.filtrer_nouvelles_offres(toutes_offres)
        prioritaires = [o for o in nouvelles_offres if self.est_offre_prioritaire(o)]
        
        print("=" * 80)
        print(f"📊 RÉSULTATS DE LA VEILLE:")
        print(f"   • Sources interrogées: {len(self.sources)}")
        print(f"   • Sources réussies: {sources_reussies}")
        print(f"   • Sources en échec: {sources_echec}")
        print(f"   • Total offres collectées: {len(toutes_offres)}")
        print(f"   • Offres pertinentes: {len(nouvelles_offres)}")
        print(f"   • Offres prioritaires: {len(prioritaires)}")
        print("=" * 80)
        
        # Sauvegarde et envoi du rapport
        if nouvelles_offres or True:  # Toujours envoyer un rapport, même vide
            self.sauvegarder_resultats(nouvelles_offres)
            self.envoyer_rapport(nouvelles_offres)
            
            if nouvelles_offres:
                print("\n📋 NOUVELLES OFFRES TROUVÉES:")
                for i, offre in enumerate(nouvelles_offres[:10], 1):  # Afficher max 10
                    priorite = "🔥" if self.est_offre_prioritaire(offre) else "📄"
                    print(f"{i}. {priorite} {offre['titre']}")
                    print(f"   🏢 {offre['organisation']} ({offre['lieu']})")
                    print(f"   🔗 {offre['lien']}")
                    print()
                    
                if len(nouvelles_offres) > 10:
                    print(f"   ... et {len(nouvelles_offres) - 10} autres offres (voir email)")
            else:
                print("   • Aucune nouvelle offre pertinente trouvée")
        
        print(f"✅ Veille terminée - {datetime.datetime.now().strftime('%H:%M:%S')}")
        print(f"📧 Rapport envoyé à {self.email_to}")

# Point d'entrée principal
if __name__ == "__main__":
    print("🔍 Initialisation du système de veille...")
    veille = VeilleStagesComplet()
    veille.executer_veille()
