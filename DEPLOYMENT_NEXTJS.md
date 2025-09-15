# 🚀 Guide de Déploiement - GenAI Trading Bot (Next.js UI)

Ce guide vous accompagne dans le déploiement du bot de trading autonome avec l'interface Next.js moderne.

## 📋 Prérequis

### 1. Environnement Système
- **Docker & Docker Compose** (recommandé)
- **Node.js 18+** (pour développement local)
- **Python 3.9+** (pour le backend)
- **RAM**: Minimum 4GB, recommandé 8GB+
- **Stockage**: 15GB+ d'espace libre
- **Réseau**: Connexion stable à Internet

### 2. Comptes et API Keys
- **Binance Account** (avec API keys)
- **OpenAI Account** (ou Anthropic/Gemini)
- **Telegram Bot** (optionnel, via @BotFather)

## 🏗️ Architecture

```
┌─────────────────┐    HTTP/WebSocket    ┌─────────────────┐
│   Next.js UI    │ ◄─────────────────► │   FastAPI       │
│   (Port 3000)   │                     │   (Port 8000)   │
└─────────────────┘                     └─────────────────┘
         │                                       │
         │                                       │
    ┌────▼────┐                            ┌────▼────┐
    │  Pages  │                            │  API    │
    │  - Config│                            │  - REST │
    │  - Dashboard│                          │  - WS   │
    │  - Journal│                           │  - Bot  │
    └─────────┘                            └─────────┘
```

## 🔧 Installation

### 1. Cloner le Repository
```bash
git clone <repository-url>
cd trading_bot
```

### 2. Configuration via l'Interface Web

**⚠️ IMPORTANT :** La configuration se fait entièrement via l'interface web Next.js, pas via un fichier `.env` !

**Étapes de configuration :**

1. **Démarrer les services** :
   ```bash
   docker-compose up -d
   ```

2. **Accéder à l'interface de configuration** :
   - URL : http://localhost:3000/config
   - L'interface guide à travers 3 étapes obligatoires

3. **Étape 1 - Configuration des Services** :
   - **LLM Configuration** (obligatoire) :
     - Provider : OpenAI, Anthropic, ou Gemini
     - API Key : Votre clé API
     - Model : Modèle à utiliser (ex: gpt-4)
   - **Binance Configuration** (obligatoire) :
     - API Key : Votre clé API Binance
     - Secret Key : Votre clé secrète Binance
     - Mode : Paper (test) ou Live
   - **Telegram Configuration** (optionnel) :
     - Bot Token : Token du bot Telegram
     - Chat ID : ID du chat
     - Allowed Users : Utilisateurs autorisés

4. **Tests de Connectivité** :
   - Boutons de test pour chaque service
   - Validation en temps réel
   - Messages d'erreur détaillés

5. **Étape 2 - Upload des Données** :
   - Upload du fichier CSV historique
   - Validation automatique du format
   - Spécification du timeframe et durée

6. **Étape 3 - Lancement** :
   - Bouton de lancement activé uniquement après validation
   - Démarrage du bot de trading
   - Redirection vers le dashboard

### 3. Données Historiques

**📁 Fichier d'exemple fourni :**
- Le fichier `examples/sample_data.csv` est déjà fourni avec 96 heures de données BTCUSDT
- Format : CSV avec colonnes `timestamp,open,high,low,close,volume,symbol`
- Timeframe : 1 minute (compatible avec l'analyse en streaming)

**📤 Upload via l'interface :**
- Utilisez l'interface web pour uploader vos propres données
- Validation automatique du format
- Spécification du timeframe et durée dans l'interface

## 🚀 Déploiement avec Docker Compose

### 1. Déploiement Complet
```bash
# Démarrer tous les services
docker-compose up -d

# Vérifier le statut
docker-compose ps

# Voir les logs
docker-compose logs -f
```

### 2. Services Disponibles

**Services principaux :**
- **API Server** : http://localhost:8000 (Backend FastAPI)
- **Next.js UI** : http://localhost:3000 (Interface utilisateur)

**Services optionnels :**
- **Redis** : `docker-compose --profile redis up -d`
- **PostgreSQL** : `docker-compose --profile postgres up -d`

### 3. Gestion des Services
```bash
# Démarrer seulement l'API et l'UI
docker-compose up -d trading-bot-api trading-bot-ui

# Démarrer avec le bot de trading
docker-compose --profile bot up -d

# Arrêter tous les services
docker-compose down

# Redémarrer un service spécifique
docker-compose restart trading-bot-ui

# Voir les logs d'un service
docker-compose logs -f trading-bot-ui
```

## 🌐 Utilisation de l'Interface

### 1. Page d'Accueil
- **URL** : http://localhost:3000
- **Fonctionnalités** :
  - Navigation vers les différentes sections
  - Vue d'ensemble du système
  - Statut des services

### 2. Configuration et Startup
- **URL** : http://localhost:3000/config
- **Étapes** :
  1. **Configuration des services** (via l'interface web)
     - LLM (OpenAI, Anthropic, Gemini) - API Key et modèle
     - Binance API - API Key et Secret Key
     - Telegram (optionnel) - Bot Token et Chat ID
     - Tests de connectivité en temps réel avec boutons de test
  2. **Upload des données historiques**
     - Format CSV uniquement
     - Validation automatique du format
     - Spécification du timeframe et durée dans l'interface
     - Utilisation du fichier d'exemple fourni ou upload de vos données
  3. **Lancement du bot**
     - Bouton de lancement activé uniquement après validation de toutes les étapes
     - Démarrage automatique du bot de trading
     - Redirection vers le dashboard de monitoring

### 3. Dashboard de Performance
- **URL** : http://localhost:3000/dashboard
- **Fonctionnalités** :
  - Statut du bot en temps réel
  - Graphiques de performance
  - Décisions LLM en direct
  - Gestion des ordres
  - Métriques de trading

### 4. Journal et Historique
- **URL** : http://localhost:3000/journal
- **Fonctionnalités** :
  - Historique des décisions LLM
  - Logs système
  - Sessions de trading
  - Export des données
  - Filtres et recherche

## 🔧 Développement Local

### 1. Backend (FastAPI)
```bash
# Installer les dépendances Python
pip install -e .

# Démarrer l'API server
python -m src.api_cli

# Ou utiliser le script
api-server
```

### 2. Frontend (Next.js)
```bash
# Aller dans le dossier UI
cd ui

# Installer les dépendances
npm install

# Démarrer en mode développement
npm run dev

# Build pour la production
npm run build
npm start
```

### 3. Tests
```bash
# Tests backend
python -m scripts.run_tests all

# Tests frontend
cd ui
npm test

# Tests d'intégration
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

## 📊 Monitoring et Maintenance

### 1. Health Checks
```bash
# Vérification de l'API
curl http://localhost:8000/health

# Vérification de l'UI
curl http://localhost:3000

# Health check complet
docker-compose exec trading-bot-api python -m scripts.health_check
```

### 2. Logs
```bash
# Logs de l'API
docker-compose logs -f trading-bot-api

# Logs de l'UI
docker-compose logs -f trading-bot-ui

# Logs du bot de trading
docker-compose logs -f trading-bot

# Logs avec timestamps
docker-compose logs -f -t
```

### 3. Backup et Restore
```bash
# Créer un backup
docker-compose exec trading-bot-api python -m scripts.backup_restore create

# Lister les backups
docker-compose exec trading-bot-api python -m scripts.backup_restore list

# Restaurer un backup
docker-compose exec trading-bot-api python -m scripts.backup_restore restore backup_name
```

## 🛡️ Sécurité

### 1. Variables d'Environnement
```bash
# Permissions restrictives
chmod 600 .env

# Ne jamais commiter les clés
echo ".env" >> .gitignore
```

### 2. Configuration Binance
- **Restrictions IP** : Limiter aux IPs de production
- **Permissions API** : Trading seulement (pas de retrait)
- **Whitelist** : Adresses IP autorisées uniquement

### 3. Configuration Télégramme
- **Utilisateurs autorisés** : Liste restrictive
- **Chat privé** : Éviter les groupes publics
- **Token sécurisé** : Rotation régulière

## 🔧 Dépannage

### 1. Problèmes Courants

**L'UI ne se connecte pas à l'API :**
```bash
# Vérifier que l'API est démarrée
docker-compose ps trading-bot-api

# Vérifier les logs
docker-compose logs trading-bot-api

# Tester la connectivité
curl http://localhost:8000/health
```

**Erreur de build Next.js :**
```bash
# Nettoyer le cache
cd ui
rm -rf .next node_modules
npm install
npm run build
```

**Problème de WebSocket :**
```bash
# Vérifier la configuration CORS
# Vérifier les variables d'environnement
# Redémarrer les services
docker-compose restart
```

### 2. Logs de Debug
```bash
# Activer le debug
export DEBUG=true
export LOG_LEVEL=DEBUG

# Redémarrer avec debug
docker-compose down
docker-compose up -d
```

### 3. Reset Complet
```bash
# Arrêter et supprimer tout
docker-compose down -v
docker system prune -f

# Redéployer
docker-compose up -d
```

## 📈 Optimisation

### 1. Performance
- **RAM** : Augmenter si nécessaire
- **CPU** : Plus de cœurs pour analyses parallèles
- **Réseau** : Connexion stable pour WebSocket

### 2. Configuration
- **Intervalle d'analyse** : Ajuster selon la volatilité
- **Taille du buffer** : Plus de données = meilleures décisions
- **Limites de risque** : Ajuster selon la tolérance

### 3. Scaling
- **Multi-symboles** : Lancer plusieurs instances
- **Load balancing** : Répartir la charge
- **Monitoring** : Alertes automatiques

## ⚠️ Avertissements Importants

1. **Commencez TOUJOURS en mode paper**
2. **Testez avec de petits montants**
3. **Surveillez constamment les performances**
4. **Ayez un plan d'arrêt d'urgence**
5. **Ne risquez jamais plus que vous ne pouvez perdre**

## 🎯 Checklist de Déploiement

- [ ] Docker et Docker Compose installés
- [ ] Services démarrés avec `docker-compose up -d`
- [ ] Interface accessible sur http://localhost:3000
- [ ] API accessible sur http://localhost:8000
- [ ] Configuration des services via l'interface web (LLM, Binance, Telegram)
- [ ] Tests de connectivité réussis via l'interface
- [ ] Données historiques uploadées via l'interface
- [ ] Bot lancé via l'interface de configuration
- [ ] Dashboard de monitoring accessible
- [ ] Journal des décisions fonctionnel

**Le système est prêt pour le déploiement ! 🚀**

## 🔗 URLs Importantes

- **Interface Principale** : http://localhost:3000
- **Configuration** : http://localhost:3000/config
- **Dashboard** : http://localhost:3000/dashboard
- **Journal** : http://localhost:3000/journal
- **API Health** : http://localhost:8000/health
- **API Docs** : http://localhost:8000/docs
