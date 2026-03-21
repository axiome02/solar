# Utilisation d'une image Python légère
FROM python:3.11-slim

# Désactiver la mise en cache de pip et l'écriture de fichiers .pyc
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Installation des dépendances système pour les calculs géospatiaux (GEOS, PROJ)
RUN apt-get update && apt-get install -y \
    build-essential \
    libgeos-dev \
    libproj-dev \
    proj-bin \
    && rm -rf /var/lib/apt/lists/*

# Définir le répertoire de travail
WORKDIR /app

# Copier le fichier des dépendances en premier (optimisation du cache Docker)
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste du code de l'application
COPY . .

# Exposer le port par défaut de Streamlit
EXPOSE 8501

# Commande pour lancer l'application
# On désactive le CORS et le tracking pour faciliter le déploiement
CMD ["streamlit", "run", "app_jima2.py", "--server.port=8501", "--server.address=0.0.0.0"]