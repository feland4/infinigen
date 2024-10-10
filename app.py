# Importation des librairies nécessaires
import sqlite3
import json
from flask import Flask, render_template, request, redirect, url_for, flash, session, Response, send_file
import os
from fonctions_analyse import analyse_dea
from fonctions_results import traiter_results
from io import StringIO
from threading import Thread
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
from flask_mail import Mail, Message
import click
from flask.cli import with_appcontext

# Initialisation de l'application Flask
app = Flask(__name__)
app.debug = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pydeseq2_db.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SECURITY_PASSWORD_SALT'] = 'your_salt'
app.config['MAIL_SERVER'] = 'localhost'
app.config['MAIL_PORT'] = 1025
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = False

# Initialisation de Flask-Mail
mail = Mail(app)
s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
db = SQLAlchemy(app)

# Définition du modèle de données utilisateur
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    first_name = db.Column(db.String(120), nullable=False)
    last_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(10), default='user', nullable=False)

# Définition du modèle de données pour les résultats d'analyse
class Run(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    analysis_date = db.Column(db.DateTime, default=datetime.utcnow)
    text_results = db.Column(db.Text, nullable=True)
    heatmap_path = db.Column(db.String(255), nullable=True)
    volcanoplot_path = db.Column(db.String(255), nullable=True)
    user = db.relationship('User', backref=db.backref('runs', lazy=True))

# Création de la base de données
with app.app_context():
    db.create_all()

# Fonction pour exécuter une analyse
def execute_analysis(counts_file, metadata_file, refit_cooks, min_reads_per_gene, alpha_thres, lfc_thres, user_id, run_id):
    string_results, heatmap_path, volcanoplot_path = analyse_dea(counts_file, metadata_file, refit_cooks, min_reads_per_gene, alpha_thres, lfc_thres)
    with app.app_context():
        run = Run.query.filter_by(id=run_id, user_id=user_id).first_or_404()
        run.text_results = string_results
        run.heatmap_path = heatmap_path
        run.volcanoplot_path = volcanoplot_path
        db.session.commit()

# Fonction pour exécuter une analyse dans un thread séparé
def execute_analysis_thread(counts_file, metadata_file, refit_cooks, min_reads_per_gene, alpha_thres, lfc_thres, user_id, run_id):
    thread = Thread(target=execute_analysis, args=(counts_file, metadata_file, refit_cooks, min_reads_per_gene, alpha_thres, lfc_thres, user_id, run_id))
    thread.daemon = True
    thread.start()

# Fonction pour vérifier si l'utilisateur est un administrateur
def is_admin():
    return 'role' in session and session['role'] == 'admin'

# Commande CLI pour créer un administrateur
@app.cli.command("create-admin")
@click.argument("email")
@click.argument("first_name")
@click.argument("last_name")
@with_appcontext
def create_admin(email, first_name, last_name):
    """Crée un administrateur."""
    if User.query.filter_by(email=email).first():
        print('User with this email already exists.')
        return
    new_admin = User(email=email, first_name=first_name, last_name=last_name, role='admin')
    db.session.add(new_admin)
    db.session.commit()
    print('Admin created successfully.')

# Route pour vérifier l'email par un token
@app.route('/verify_email/<token>')
def verify_email(token):
    try:
        email = s.loads(token, salt=app.config['SECURITY_PASSWORD_SALT'], max_age=3600)
        user = User.query.filter_by(email=email).first()
        if user:
            session['user_email'] = email
            session['user_id'] = user.id
            session['role'] = user.role  # Sauvegarder le rôle de l'utilisateur dans la session
            flash('Email vérifié avec succès. Vous êtes maintenant connecté.')
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('Aucun compte trouvé pour cet email.', 'error')
            return redirect(url_for('login'))
    except SignatureExpired:
        return 'Le lien de vérification a expiré. Veuillez vous connecter à nouveau.'

# Route pour le tableau de bord de l'administrateur
@app.route('/admin/dashboard')
def admin_dashboard():
    if not is_admin():
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('login'))
    users = User.query.all()
    return render_template('admin_dashboard.html', users=users)

# Route pour supprimer un utilisateur
@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if not is_admin():
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('login'))
    
    user = User.query.get_or_404(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        flash(f'Utilisateur {user.first_name} {user.last_name} supprimé avec succès.', 'success')
    else:
        flash('Utilisateur non trouvé.', 'error')

    return redirect(url_for('admin_dashboard'))

# Route pour supprimer un résultat d'analyse
@app.route('/delete_run/<int:run_id>', methods=['POST'])
def delete_run(run_id):
    run = Run.query.get_or_404(run_id)
    if session.get('user_id') == run.user_id or is_admin():
        db.session.delete(run)
        db.session.commit()
        flash(f'Analyse {run_id} supprimée avec succès.', 'success')
    else:
        flash('Accès non autorisé. Vous ne pouvez supprimer que les analyses que vous possédez.', 'error')
        return redirect(url_for('login'))

    if not is_admin():
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('admin_dashboard'))

# Route pour le tableau de bord de l'utilisateur
@app.route('/dashboard')
def dashboard():
    if 'user_email' in session:
        user_email = session['user_email']
        user = User.query.filter_by(email=user_email).first()
        if user:
            session['user_id'] = user.id
            user_runs = Run.query.filter_by(user_id=user.id).all()
            return render_template('dashboard.html', user_runs=user_runs)
        else:
            flash('Utilisateur non trouvé. Veuillez vous reconnecter.', 'error')
            return redirect(url_for('login'))
    else:
        flash('Veuillez vous connecter pour accéder au tableau de bord.', 'error')
        return redirect(url_for('login'))

# Route pour l'inscription
@app.route('/inscription', methods=['GET', 'POST'])
def inscription():
    if request.method == 'POST':
        email = request.form['courriel']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Cet email existe déjà.', 'email-existe')
            return redirect(url_for('inscription'))
        
        token = s.dumps(email, salt=app.config['SECURITY_PASSWORD_SALT'])
        
        link = url_for('verify_email', token=token, _external=True)
        
        try:
            msg = Message('Confirmer inscription', sender='your_email@example.com', recipients=[email])
            msg.body = 'Votre lien de vérification est : {}'.format(link)
            mail.send(msg)
        except Exception as e:
            app.logger.error('Échec de l\'envoi du lien de vérification: %s', e)
            flash("Échec de l'envoi de l'e-mail de vérification. Veuillez réessayer.", 'inscription-failed')
            return redirect(url_for('inscription'))
        
        new_user = User(email=email, first_name=first_name, last_name=last_name)
        db.session.add(new_user)
        db.session.commit()
        flash("Un lien de vérification a été envoyé à votre adresse courriel. Veuillez vérifier votre boîte de réception.", 'inscription-success')
        return redirect(url_for('login'))
    return render_template('inscription.html')

# Route pour la connexion
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['courriel']
        user = User.query.filter_by(email=email).first()
        if not user:
            flash('Ce courriel n\'est pas enregistré. Veuillez vérifier votre adresse et réessayer.', 'email-non-enregistre')
            return redirect(url_for('login'))
        
        token = s.dumps(email, salt=app.config['SECURITY_PASSWORD_SALT'])
        
        link = url_for('verify_email', token=token, _external=True)
        
        msg = Message('Vérification de la connexion', sender='your_email@example.com', recipients=[email])
        msg.body = 'Veuillez cliquer sur le lien pour vérifier votre email et compléter le processus de connexion : {}'.format(link)
        mail.send(msg)
        
        flash('Un email de vérification a été envoyé à votre adresse courriel. Veuillez vérifier votre boîte de réception.', 'authentication_email_sent')
        return redirect(url_for('index'))
    return render_template('login.html')

# Route pour télécharger les exemples de fichiers de compte
@app.route('/download_example_counts')
def download_example_counts():
    example_counts_file_path = os.path.join("datasets", "count_table.csv")
    return send_file(example_counts_file_path, as_attachment=True)

# Route pour télécharger les exemples de fichiers de métadonnées
@app.route('/download_example_metadata')
def download_example_metadata():
    example_metadata_file_path = os.path.join("datasets", "metadata_table.csv")
    return send_file(example_metadata_file_path, as_attachment=True)

# Route pour lancer une nouvelle analyse
@app.route('/analyse', methods=["GET", "POST"])
def analyse():
    if request.method == "POST":
        refit_cooks = "refit_cooks" in request.form.getlist("options")
        min_reads_per_gene = int(request.form["min_reads_per_gene"])
        alpha_thres = float(request.form["alpha_thres"])
        lfc_thres = float(request.form["lfc_thres"])

        counts_file = request.files['counts_file']
        metadata_file = request.files['metadata_file']
        counts_file.save(os.path.join("datasets", counts_file.filename))
        metadata_file.save(os.path.join("datasets", metadata_file.filename))

        counts_file_path = os.path.join("datasets", counts_file.filename)
        metadata_file_path = os.path.join("datasets", metadata_file.filename)
        
        user_id = session['user_id']
        run_id = None

        new_run = Run(
                user_id=user_id,
                analysis_date=datetime.now(),
                text_results=None,
                heatmap_path=None,
                volcanoplot_path=None
        )

        with app.app_context():
            db.session.add(new_run)
            db.session.commit()
            run_id = new_run.id

        execute_analysis_thread(counts_file_path, metadata_file_path, refit_cooks, min_reads_per_gene, alpha_thres, lfc_thres, user_id, run_id)
        session['run_id'] = run_id

        return redirect(url_for('display_wait'))
    
    return render_template('analyse.html')

# Route pour télécharger les résultats au format CSV
@app.route('/download_csv/<int:run_id>')
def download_csv(run_id):
    user_id = session['user_id']
    with app.app_context():
        run = Run.query.filter_by(id=run_id, user_id=user_id).first_or_404()

        text_dict = traiter_results(run.text_results)
        csv_data = text_dict['matrice']

        headers = {
            "Content-Disposition": f"attachment; filename=matrice_data.csv"
        }

        return Response(
            csv_data,
            mimetype="text/csv",
            headers=headers
        )

# Route pour afficher les résultats d'une analyse
@app.route('/results/<int:run_id>')
def display_results(run_id):
    if 'user_id' not in session:
        flash('Veuillez vous connecter pour accéder à cette page.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']

    with app.app_context():
        run = Run.query.filter_by(id=run_id, user_id=user_id).first_or_404()
        text_results = traiter_results(run.text_results)
        return render_template('results.html', run_id=run_id, text_results=text_results, heatmap_path=run.heatmap_path, volcanoplot_path=run.volcanoplot_path)

# Route pour la page d'attente pendant le traitement de l'analyse
@app.route('/wait', methods=["GET", "POST"])
def display_wait():
    if request.method == "POST":

        user_id = session['user_id']
        run_id = session['run_id']

        with app.app_context():
            run = Run.query.filter_by(id=run_id, user_id=user_id).first_or_404()
            if run.text_results == None:
                return render_template('wait.html')
            else:
                return redirect(url_for('display_results', run_id=run_id))

    return render_template('wait.html')

# Route pour la page d'accueil qui redirige vers la connexion
@app.route('/')
def index():
    return redirect('/login')

# Route pour se déconnecter
@app.route('/logout')
def logout():
    session.clear()
    flash('Vous avez été déconnecté avec succès.', 'info')
    return redirect(url_for('login'))

# Point d'entrée principal de l'application
if __name__ == '__main__':
    app.run(debug=True, port=5559)