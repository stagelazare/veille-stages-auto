# Script de veille automatisée des offres de stage
# Relations internationales, diplomatie, sécurité, Moyen-Orient
# Profil: fin de licence/bachelor, durée 6-12 mois, avril 2026-avril 2027

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

class VeilleStages:
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
            "union européenne", "european union", "onu", "un", "osce"
        ]
        
        # Sources à surveiller
        self.sources = [
            {
                "nom": "France Diplomatie",
                "url": "https://www.diplomatie.gouv.fr/fr/emplois-stages-concours/",
                "selector": ".job-listing",
                "date_selector": ".date-posted",
                "title_selector": "h3",
                "link_selector": "a",
                "location_selector": ".location",
                "description_selector": ".description"
            },
            {
                "nom": "PASS Fonction Publique",
                "url": "https://www.pass.fonction-publique.gouv.fr/",
                "selector": ".offre",
                "date_selector": ".date",
                "title_selector": ".titre",
                "link_selector": "a",
                "location_selector": ".lieu",
                "description_selector": ".resume"
            },
            {
                "nom": "ONU Carrières",
                "url": "https://careers.un.org/",
                "selector": ".job-item",
                "date_selector": ".posting-date",
                "title_selector": ".job-title",
                "link_selector": "a",
                "location_selector": ".duty-station",
                "description_selector": ".job-summary"
            },
            {
                "nom": "OSCE Jobs",
                "url": "https://jobs.osce.org/",
                "selector": ".vacancy",
                "date_selector": ".date-published",
                "title_selector": ".title",
                "link_selector": "a",
                "location_selector": ".location",
                "description_selector": ".summary"
            }
        ]

    def extraire_offres_site(self, source):
        """Extrait les offres d'un site donné"""
        print(f"Extraction des offres de {source['nom']}...")
        
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
            
            for job in job_listings[:10]:  # Limite à 10 offres par site
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
                    description = desc_elem.get_text(strip=True)[:200] + "..." if desc_elem else "Description non disponible"
                    
                    date_elem = job.select_one(source['date_selector'])
                    date_pub = date_elem.get_text(strip=True) if date_elem else self.aujourd_hui
                    
                    # Vérifier si l'offre contient des mots-clés pertinents
                    texte_complet = f"{titre} {description} {lieu}".lower()
                    if any(keyword.lower() in texte_complet for keyword in self.keywords):
                        offres.append({
                            'date': date_pub,
                            'organisation': source['nom'],
                            'titre': titre,
                            'lieu': lieu,
                            'lien': lien,
                            'description': description
                        })
                        
                except Exception as e:
                    print(f"Erreur lors de l'extraction d'une offre: {e}")
                    continue
            
            print(f"✅ {len(offres)} offres trouvées sur {source['nom']}")
            return offres
            
        except requests.RequestException as e:
            print(f"❌ Erreur de connexion à {source['nom']}: {e}")
            return []
        except Exception as e:
            print(f"❌ Erreur lors de l'extraction de {source['nom']}: {e}")
            return []

    def filtrer_nouvelles_offres(self, offres):
        """Filtre les offres publiées hier (simulation - en production, comparer avec base de données)"""
        nouvelles_offres = []
        
        for offre in offres:
            # Simulation: considérer toutes les offres comme nouvelles pour le test
            # En production, comparer avec une base de données des offres précédentes
            if self.est_offre_pertinente(offre):
                nouvelles_offres.append(offre)
        
        return nouvelles_offres

    def est_offre_pertinente(self, offre):
        """Vérifie si une offre correspond aux critères recherchés"""
        titre_desc = f"{offre['titre']} {offre['description']}".lower()
        
        # Vérifier les mots-clés
        mots_cles_pertinents = [
            "stage", "intern", "stagiaire", "internship", "trainee",
            "bachelor", "licence", "césure", "gap year", "6 mois", "12 mois"
        ]
        
        # Vérifier les zones géographiques
        zones_geo = [
            "europe", "france", "canada", "moyen-orient", "middle east",
            "proche-orient", "near east", "iran", "israel", "palestine",
            "syrie", "liban", "jordanie", "turquie", "egypt"
        ]
        
        a_mots_cles = any(mot in titre_desc for mot in mots_cles_pertinents)
        a_zone_geo = any(zone in titre_desc for zone in zones_geo)
        
        return a_mots_cles or a_zone_geo

    def generer_rapport_html(self, nouvelles_offres):
        """Génère un rapport HTML des nouvelles offres"""
        if not nouvelles_offres:
            return f"""
            <html>
            <head><title>Veille Stages - {self.aujourd_hui}</title></head>
            <body>
                <h2>🔍 Veille quotidienne des stages</h2>
                <p><strong>Date:</strong> {self.aujourd_hui}</p>
                <p>Aucune nouvelle offre trouvée aujourd'hui.</p>
                <p><em>Domaines surveillés:</em> Relations internationales, Diplomatie, Sécurité internationale, Moyen-Orient</p>
            </body>
            </html>
            """
        
        html = f"""
        <html>
        <head>
            <title>Nouvelles offres de stage - {self.aujourd_hui}</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
                .offre {{ border: 1px solid #ddd; margin: 15px 0; padding: 15px; border-radius: 8px; }}
                .titre {{ color: #2c5282; font-weight: bold; font-size: 18px; }}
                .organisation {{ color: #718096; font-weight: bold; }}
                .lieu {{ color: #e53e3e; }}
                .date {{ color: #38a169; font-size: 12px; }}
                .description {{ margin-top: 10px; color: #4a5568; }}
                .lien {{ margin-top: 10px; }}
                a {{ color: #3182ce; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <h2>🎯 Nouvelles offres de stage - {self.aujourd_hui}</h2>
            <p><strong>{len(nouvelles_offres)} nouvelle(s) offre(s) trouvée(s)</strong></p>
            <hr>
        """
        
        for offre in nouvelles_offres:
            html += f"""
            <div class="offre">
                <div class="titre">{offre['titre']}</div>
                <div class="organisation">📍 {offre['organisation']} - {offre['lieu']}</div>
                <div class="date">📅 Publié: {offre['date']}</div>
                <div class="description">{offre['description']}</div>
                <div class="lien">
                    <a href="{offre['lien']}" target="_blank">🔗 Voir l'offre complète</a>
                </div>
            </div>
            """
        
        html += """
            <hr>
            <p><em>Veille automatisée - Relations internationales, Diplomatie, Sécurité, Moyen-Orient</em></p>
            <p><em>Profil ciblé: Fin de licence/Bachelor, durée 6-12 mois, avril 2026-avril 2027</em></p>
        </body>
        </html>
        """
        
        return html

    def envoyer_rapport(self, nouvelles_offres):
        """Envoie le rapport par email"""
        if not self.email_from or not self.email_password or not self.email_to:
            print("❌ Configuration email manquante dans les variables d'environnement")
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"🎯 Veille stages - {len(nouvelles_offres)} nouvelle(s) offre(s) - {self.aujourd_hui}"
            msg['From'] = self.email_from
            msg['To'] = self.email_to
            
            # Version HTML
            html_content = self.generer_rapport_html(nouvelles_offres)
            html_part = MIMEText(html_content, 'html')
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
        """Sauvegarde les résultats dans un fichier JSON"""
        filename = f"offres_{self.aujourd_hui}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    'date': self.aujourd_hui,
                    'nombre_offres': len(nouvelles_offres),
                    'offres': nouvelles_offres
                }, f, ensure_ascii=False, indent=2)
            
            print(f"💾 Résultats sauvegardés dans {filename}")
            
        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde: {e}")

    def executer_veille(self):
        """Exécute le processus complet de veille"""
        print(f"🚀 Début de la veille quotidienne - {self.aujourd_hui}")
        print("=" * 60)
        
        toutes_offres = []
        
        # Extraction des offres de chaque source
        for source in self.sources:
            offres_site = self.extraire_offres_site(source)
            toutes_offres.extend(offres_site)
            time.sleep(2)  # Pause entre les requêtes
        
        # Filtrage des nouvelles offres pertinentes
        nouvelles_offres = self.filtrer_nouvelles_offres(toutes_offres)
        
        print("=" * 60)
        print(f"📊 RÉSULTATS:")
        print(f"   • Total offres collectées: {len(toutes_offres)}")
        print(f"   • Nouvelles offres pertinentes: {len(nouvelles_offres)}")
        
        # Sauvegarde et envoi du rapport
        if nouvelles_offres:
            self.sauvegarder_resultats(nouvelles_offres)
            self.envoyer_rapport(nouvelles_offres)
            
            print("\n📋 NOUVELLES OFFRES:")
            for i, offre in enumerate(nouvelles_offres, 1):
                print(f"{i}. {offre['titre']} - {offre['organisation']} ({offre['lieu']})")
                print(f"   🔗 {offre['lien']}")
                print()
        else:
            print("   • Aucune nouvelle offre pertinente trouvée")
            # Envoyer quand même un rapport vide pour confirmer que le script fonctionne
            self.envoyer_rapport([])
        
        print(f"✅ Veille terminée - {datetime.datetime.now().strftime('%H:%M:%S')}")

# Point d'entrée principal
if __name__ == "__main__":
    veille = VeilleStages()
    veille.executer_veille()
