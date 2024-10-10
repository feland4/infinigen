#### Membres de l'équipe
- Fatima Mawassi,
- Nathalia Gomide Cruz,
- Mathura Kanapathippillai,
- Andres Felipe Ordonez Bustos,

#### Nom du projet GitLab: INF8214_TP2
#### Date: 2 Mai 2024
#### Version: 1.0

# 🧬 InfiniGenLog: Plan du projet

Bienvenue dans l'application web InfiniGenLog avec pyDESeq2 ! Cet outil facilite l'analyse de l'expression génique différentielle en utilisant une interface web à la fois conviviale et puissante.

## 🛠 Installation et exécution
Avant de lancer l'application, assurez-vous que Python et pip sont installés sur votre machine. Suivez ces étapes pour démarrer l'application :

1. **Cloner le dépôt**
 ```shell
 git clone <url-du-dépôt>
 cd INF8214_TP2
 ```

2. **Configurer un environnement virtuel** (optionnel mais recommandé) :
```shell
python -m venv venv
source venv/bin/activate  # Sur Windows, utilisez `venv\Scripts\activate`
```

3. **Installer les dépendances** :
```shell
pip install -r requirements.txt
```

4. **Lancer l'application** :
```shell
flask run
```

5. **Accéder à l'application web** :
Naviguez vers `http://127.0.0.1:5559` dans votre navigateur web pour commencer à utiliser l'application.

6. **Lancer le serveur Sendria** : 
Exécuter la commande dans `sendria_sh.txt` dans un nouveau terminal pour lancer le serveur de Sendria en parallèle.
```shell
sendria --smtp-port 1025 --http-port 1080 --db ./sendria_db.sqlite
```
7. **Accéder au serveur Sendria** : 
Naviguez vers `http://127.0.0.1:1080` dans un autre onglet ou fenêtre de votre navigateur web pour accéder à une boîte de réception de courriels fictifs.

8. **Initialiser le compte Admin** :
Exécuter la commande dans `admin_sh.txt` dans un nouveau terminal.
```shell
flask create-admin admin@example.com Prenom Nom_de_famille
```

Voilà! Vous êtes maintenant prêt à utiliser l'interface web d'InfiniGenLog 👏

## 📊 Utilisation de pyDESeq2
Voici ce que pyDESeq2 a besoin pour faire une analyse.

Visitez la [documentation](https://pydeseq2.readthedocs.io/en/latest/) de pyDESeq2 pour plus de détails.
>B. Muzellec, M. Teleńczuk, V. Cabeli, and M. Andreux, "PyDESeq2: a python package for bulk RNA-seq differential expression analysis," Bioinformatics, vol. 39, no. 9, 2023, doi: 10.1093/bioinformatics/btad547.


#### Données d'entrée : 
  - `counts` (pandas.DataFrame)
  - `metadata` (pandas.DataFrame)

#### Paramètres pyDESeq2 :
- `design_factors` (str ou liste) : Colonnes de metadata utilisées comme variables de conception (défaut : 'condition')
- `refit_cooks` (bool) : Si vrai, recalcul des outliers de Cook

#### Paramètres supplémentaires pour les calculs statistiques :
- `min_reads_per_gene` (int) : Nombre entier du nombre de comptes de reads minimal par gène
- `alpha_thres` (float) : Seuil pour la p-value ajustée avec une valeur de \[0,1]
- `lfc_thres` (float) : Seuil pour le log2FoldChange
<br><br>
## 🌐 Interface Web

### 1) **Page de connexion (login) et d'inscription** 🔐
   - `http://127.0.0.1:5559/login` et `http://127.0.0.1:5559/inscription`
   - Champ de texte pour saisir un courriel d'un compte déjà inscrit
   - Pour un nouveau utilisateur, un lien vers la page d'inscription
      - Authentification initiale par nom, prénom et courriel
   - Un lien unique est envoyé au courriel de l'utilisateur dans la boîte de réception Sendria pour vérifier son identité et fournir un lien de connexion
   - Des jetons de sécurité temporaires sont générés pour la vérification des e-mails

### 2) **Historique de l'utilisateur** 📚👤
   - `http://127.0.0.1:5559/dashboard`
   - Affiche toutes les analyses précédentes de **l'utilisateur**
   - Bouton pour supprimer une analyse antérieure
   - Classe User définie dans la base de données pour gérer les ID, emails, prénoms et noms des utilisateurs.
   - Boutons pour faire une déconnexion et démarrer une nouvelle analyse

### 3) **Historique de l'admin** 📚🛡️
   - `http://127.0.0.1:5559/admin/dashboard`
   - Affiche toutes les analyses précédentes de **l'admin et de tous les autres utilisateurs**
   - Bouton pour supprimer des utilisateurs et des analyses antérieurs
   - Classe User définie dans la base de données pour gérer les ID, emails, prénoms et noms des utilisateurs.
   - Boutons pour faire une déconnexion et démarrer une nouvelle analyse

### 4) **Page de démarrage de l'analyse** 🚀
   - `http://127.0.0.1:5559/analyse`
   - Zones de dépôt pour les fichiers 'counts' et 'metadata' au format .csv.
   - Boutons pour télécharger des fichiers .csv d'exemples de 'counts' et 'metadata'
   - Case à cocher pour activer ou désactiver le recalcul des outliers de Cook.
   - Champs numéricals pour saisir le nombre minimal de compte de reads pour chaque gène, le seuil alpha pour le p-value et le seuil du log2FoldChange
   - Bouton pour soumettre les fichiers d'entrée et paramètres afin de démarrer l'analyse pyDESeq2

### 5) **Page d'attente** ⏳
   - `http://127.0.0.1:5559/wait`
   - Affiche une animation de chargement pendant que les résultats sont en cours de traitement.
   - Interroge le serveur toutes les 5 secondes pour vérifier si l'analyse est terminée.
   - Redirige vers la page des résultats une fois l'analyse terminée.

### 6) **Page de résultats** 📈
   - `http://127.0.0.1:5559/results/<int:run_id>`
   - Option de télécharger les résultats statistiques pour des analyses en aval (fichier .csv avec les p-values, log2FoldChange pour chaque gène).
   - Visualisations Heatmap et Volcano plot.



**N'hésitez pas à explorer l'application et à réaliser vos analyses !**
