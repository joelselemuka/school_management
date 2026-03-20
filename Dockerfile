# Utilise une image Python officielle en version allégée (alpine ou slim)
FROM python:3.11-slim

# Met en place des variables d'environnement utiles pour Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Définit le dossier de travail dans le conteneur
WORKDIR /app

# Installe les dépendances sytèmes critiques
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copie le fichier des requirements et l'installe
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install gunicorn uvicorn # Serveur production performant

# Copie tout le reste de votre code
COPY . /app/

# Collecte des fichiers statiques (indispensable pour que Swagger/DRF ait un design)
RUN SECRET_KEY="dummy_key_for_build" python manage.py collectstatic --noinput

# Port utilisé par Render
EXPOSE 8000

# Lance les migrations et démarre le serveur ASGI (Gunicorn avec workers Uvicorn)
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000"]
