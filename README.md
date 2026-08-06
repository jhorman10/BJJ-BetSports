# 🎯 BJJ - BetSports: Intelligent Betting Assistant

> **Plataforma de Alta Precisión forjada en IA y Estadística, diseñada para la Optimización de Inferencia Deportiva.**

![BJJ BetSports](https://img.shields.io/badge/BJJ-BetSports-6366f1?style=for-the-badge&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11+-3776ab?style=flat-square&logo=python&logoColor=white)
![ML](https://img.shields.io/badge/ML-Random_Forest-F7931E?style=flat-square&logo=scikitlearn&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Portable-2496ED?style=flat-square&logo=docker&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React_19-20232A?style=flat-square&logo=react&logoColor=61DAFB)

---

## 💡 Propósito Estratégico

**BJJ-BetSports** no es un simple script de predicciones; es un ecosistema avanzado en arquitectura de microservicios diseñado para ser **totalmente autosuficiente y portátil**.

### 🏗️ Arquitectura Dual de Despliegue

La plataforma posee una ingeniería que separa inteligentemente los procesos pesados de Machine Learning de la ligereza requerida para un Frontend responsivo, permitiendo dos modalidades operativas:

1. **Modo Producción Serverless (Lightweight / API-Only)**
   - Diseñado para entornos hosteados (Render). El servidor opera en `API_ONLY_MODE=true` consumiendo una base de datos **PostgreSQL**.
   - El entrenamiento de IA pesado ("El Cerebro") se orquesta externamente vía un worker en **GitHub Actions** cada 6 horas.
   - Resultado: Una API que consume apenas ~100MB (en lugar de +500MB) entregando predicciones cacheadas pre-computadas ultrarrápidas a la PWA.

2. **Modo Local Portable (Inteligencia Autónoma)**
   - Pensado para la investigación y modelado rápido sin depender de la nube.
   - Utiliza **MongoDB** y se lanza todo el ecosistema (Frontend, Backend, bases de datos y Workers) con un solo comando Docker garantizando contenedores saludables y resolviendo problemas de *split-brain*.
   - El pipeline y el motor MLOps se corren directamente en tu máquina, permitiendo entrenar con periodos de tiempo personalizados (ej. últimos 10 años).

---

## 🎯 Alcance Operativo & Ligas

El pipeline de extracción consolida datos pasados y presentes a partir de integraciones automáticas como *Football-Data.co.uk* y *Football-Data.org*, cruzándolos con proyecciones de apuestas (vía *The Odds API*).

### 🥇 19+ Ligas Locales y Europeas Respaldadas Oficialmente:
- **🇬🇧 Inglaterra:** E0 (Premier League), E1 (Championship), E2 (League One), E3 (League Two)
- **🇪🇸 España:** SP1 (La Liga), SP2 (Segunda División)
- **🇩🇪 Alemania:** D1 (Bundesliga), D2 (2. Bundesliga)
- **🇮🇹 Italia:** I1 (Serie A), I2 (Serie B)
- **🇫🇷 Francia:** F1 (Ligue 1), F2 (Ligue 2)
- **🇳🇱 Países Bajos:** N1 (Eredivisie)
- **🇵🇹 Portugal:** P1 (Primeira Liga)
- **🇧🇪 Bélgica:** B1 (Pro League)
- **🏴󠁧󠁢󠁳󠁣󠁴󠁿 Escocia:** SC0 (Premiership), SC1 (Championship)
- **🇹🇷 Turquía:** T1 (Süper Lig)
- **🇬🇷 Grecia:** G1 (Super League)
- **🇪🇺 Torneos Oficiales:** UCL (Champions League), UEL (Europa League), UECL (Conference League) (*dinámicos*)

### ⚽ Mercados Incluidos
- **Probabilidad de Resultado (1X2)**
- **Mercados Estadísticos Específicos**: Córners y Tarjetas (Over/Under)
- **Handicaps Asiáticos (VA)** de ventaja competitiva basado en la dominancia histórica.
- **Ambos Equipos Anotan (BTTS)** basado en el cruce de potencia ofensiva / pasividad defensiva.

---

## 🧠 El "Cerebro": Lógica Core de MLOps

Para garantizar la integridad y rentabilidad de los picks, el sistema implementa una política **"No-Mock Data"**:

- **Random Forest Classifier**: Aprende el comportamiento global procesando datasets que por defecto varían entre **550 y 3650 días** (hasta 10 años de historia deportiva) para revelar rentabilidad no-lineal.
- **Distribución de variables de Poisson & Skellam**: Para modelar las apariciones discretas pero seguras y continuas (Tarjetas y Córners).
- **Gestión de Riesgo Integrada**: Con un servicio basado en el **Criterio de Kelly (Kelly Criterion)**. El sistema audita la ventaja estadística (Expected Value - EV) que otorgan los *bookmakers* y te recomienda de forma científica las aportaciones.

---

## 🚀 Levantamiento Rápido Local (Portable First)

### 1. Requisitos Indispensables
- [Docker](https://docs.docker.com/get-docker/) + [Docker Compose](https://docs.docker.com/compose/install/)

### 2. Configuración y Setup Base
```bash
# Otorgar permisos al shell interactivo local y copiar las variables de entorno
./scripts/setup-dev.sh
cp backend/.env.example backend/.env
```

### 3. Lanzar la Plataforma (Daemon Mode)
Levanta de forma orquestada MongoDB, Backend API y el Frontend. Todo comunicándose en una red bridge custom.
```bash
docker compose -f docker-compose.dev.yml up -d
```

### 4. Forzar el Ciclo de Inteligencia (Re-Entrenar Localmente)
El modelo requiere que se le ordene ejecutar el MLOps Pipeline el cual purga datos viejos, procesa el training dataset, extrae las predicciones de la semana en base a las cuotas y sube los "Top Picks".
```bash
docker compose -f docker-compose.dev.yml --profile mlops run --rm mlops-pipeline
```
*(Tip: Puedes usar `python3 -m scripts.orchestrator_cli run-all` dentro del bash local de la carpeta de backend)*

### 5. Reclamar Espacio en Disco (Docker Prunes)
Tras múltiples ciclos de entrenamiento MLOps, los artefactos de build y las imágenes intermedias acumulan varios GB. Para reclamar espacio de forma segura (no afecta volúmenes ni bases de datos):
```bash
docker builder prune -a      # ~9GB de capas de build intermedias
docker image prune -a        # ~3.4GB de imágenes huérfanas
```
*(Aplica a builds locales; en CI el cache de Docker se gestiona aparte.)*

---

## 📡 Mapa de Servicios Local

| Servicio         | URL / Conexión                | Descripción                               |
| :--------------- | :---------------------------- | :---------------------------------------- |
| **Frontend UI**  | `http://localhost:5173`       | PWA principal con dashboards y sugerencias. |
| **Backend API**  | `http://localhost:8000`       | Core REST (FastAPI) leyendo del MongoDB local. |
| **Documentación**| `http://localhost:8000/docs`  | Swagger Interactivo de endpoints.         |
| **MongoDB**      | `mongodb://localhost:27017`   | Motor de base portatil.                   |

---

## 📂 Estructura Principal del Proyecto
```bash
.
├── backend/            # FastAPI, Random Forest, MLOps, Workers y Repositorios
├── frontend/           # PWA elaborada en React 19, TypeScript y Vite
├── scripts/            # Automatizaciones shell de dev/MLOps portability
├── specs/              # Documentos conceptuales y estándares de equipo (Agent Teams Lite)
├── docker-compose.dev.yml # Orquestación multio-perfiles local (MongoDB)
└── Dockerfile.portable # Definición de Container robusta e insulada (Unificada)
```

---

## 📄 Disclaimer
Software para fines estrictamente **educativos, de experimentación Data Science e investigativos**. Las predicciones y algoritmos probabilísticos del Random Forest no garantizan resultados financieros seguros de ninguna forma. Apuesta, invierte y analiza con total responsabilidad.

*Desarrollado y conceptualizado por* **[Jhorman Orozco](https://github.com/jhorman10)** y potenciado por Machine Learning Local.
