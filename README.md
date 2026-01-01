# 🎯 BJJ - BetSports: Intelligent Betting Assistant

> **Sistema Avanzado de Predicción Deportiva Optimizado para Cloud Free-Tier**

![BJJ BetSports](https://img.shields.io/badge/BJJ-BetSports-6366f1?style=for-the-badge&logo=dependabot&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11+-3776ab?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688?style=flat-square&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61dafb?style=flat-square&logo=react&logoColor=white)
![MUI](https://img.shields.io/badge/MUI-v5-007FFF?style=flat-square&logo=mui&logoColor=white)
![Render](https://img.shields.io/badge/Render-Hosted-46E3B7?style=flat-square&logo=render&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-CI%2FCD-2088FF?style=flat-square&logo=github-actions&logoColor=white)

## 📋 Descripción General

**BJJ-BetSports** es una plataforma de análisis y predicción de fútbol "Cloud-Native" diseñada para operar eficientemente en entornos de recursos limitados (como Render Free Tier).

Utiliza un enfoque de **Arquitectura Desacoplada**:

1.  **Entrenamiento Pesado**: Se delega a **GitHub Actions**, que procesa 10 años de datos históricos y entrena un modelo **Random Forest** diariamente.
2.  **Inferencia Ligera**: La API en **Render** carga solo el modelo pre-entrenado y sirve predicciones en milisegundos, consumiendo mínima RAM (<512MB).
3.  **Persistencia Híbrida**: Combina **Redis (Upstash/External)** para datos en tiempo real y **DiskCache** para resiliencia local.

---

## ✨ Características Principales

### 🧠 Inteligencia Artificial & ML

- **Modelo**: Random Forest Classifier optimizado (60 estimadores, profundidad limitada).
- **Backtesting**: Simulación de rentabilidad (ROI) con ventana deslizante de 365 días.
- **Lazy Loading**: Carga de librerías de ML (`sklearn`, `pandas`) bajo demanda para inicio ultrarrápido.
- **Métricas**: Accuracy, ROI, Unidades de Beneficio y Eficiencia por tipo de apuesta.

### 🏗️ Arquitectura & DevOps

- **Entrenamiento Automatizado**: Workflow de GitHub Actions (`daily_training.yml`) re-entrena el modelo cada día a las 06:00 AM UTC.
- **Gestión de Memoria OOM**: Flag `DISABLE_ML_TRAINING=true` para prevenir crashes en instancias pequeñas.
- **Caching Multi-Nivel**:
  - **L1**: Memoria (RAM)
  - **L2**: Redis (Distribuido/Persistente)
  - **L3**: DiskCache (Sistema de archivos)

### 💻 Frontend (PWA)

- **Tecnología**: React 19 + TypeScript + Vite.
- **UI/UX**: Material UI v5 con modo oscuro y diseño responsivo.
- **Estado Global**: Zustand para gestión eficiente del estado.
- **Visualización**: Gráficos interactivos con Recharts (Evolución de ROI, Eficiencia).
- **PWA**: Instalable como aplicación nativa en móviles.

---

## 🛠️ Stack Tecnológico Completo

| Área         | Tecnología         | Uso                                         |
| ------------ | ------------------ | ------------------------------------------- |
| **Backend**  | Python 3.11        | Lenguaje base                               |
|              | **FastAPI**        | Framework API asíncrono de alto rendimiento |
|              | **Scikit-learn**   | Entrenamiento de modelos (Random Forest)    |
|              | **Joblib**         | Serialización eficiente de modelos          |
|              | **APScheduler**    | Orquestación de tareas en segundo plano     |
|              | **Pydantic**       | Validación de datos y settings              |
| **Frontend** | **React 19**       | Biblioteca UI                               |
|              | **TypeScript**     | Tipado estático y seguridad                 |
|              | **Vite**           | Build tool de próxima generación            |
|              | **Material UI**    | Sistema de diseño de componentes            |
|              | **Zustand**        | State Management ligero                     |
|              | **Recharts**       | Gráficos estadísticos                       |
| **Data**     | **Redis**          | Caché distribuida y persistencia de sesión  |
|              | **DiskCache**      | Persistencia local de respaldo              |
|              | **Pandas/NumPy**   | Manipulación de datasets                    |
| **Infra**    | **GitHub Actions** | CI/CD y Pipeline de ML Training             |
|              | **Render**         | Hosting de API y Web Service                |

---

## 📂 Estructura del Proyecto

```bash
BJJ-BetSports/
├── .github/workflows/      # 🤖 CI/CD Pipelines
│   └── daily_training.yml  # Workflow de entrenamiento diario
├── backend/                # 🧠 API FastAPI
│   ├── scripts/            # Scripts standalone (Training)
│   ├── src/
│   │   ├── api/            # Rutas y Endpoints
│   │   ├── application/    # Casos de uso y Orquestadores
│   │   ├── domain/         # Lógica de negocio pura (Entidades)
│   │   └── infrastructure/ # Implementaciones (Cache, Datasources)
│   └── main.py             # Entrypoint
├── frontend/               # 🎨 React PWA
│   ├── src/
│   │   ├── components/     # Átomos y Moléculas UI
│   │   ├── pages/          # Vistas principales
│   │   └── store/          # Stores de Zustand
└── render.yaml             # ☁️ Configuración IaC para Render
```

---

## 🚀 Guía de Instalación (Local)

### Prerrequisitos

- Python 3.11+
- Node.js 18+
- Git

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Edita .env con tus API Keys (Football-Data.org, etc.)

# Iniciar servidor
uvicorn src.api.main:app --reload
```

### 2. Frontend

```bash
cd frontend
npm install

# Iniciar desarrollo
npm run dev
```

La app estará disponible en: `http://localhost:5173`

---

## ☁️ Despliegue en Render (Free Tier)

Este proyecto está pre-configurado para desplegarse en Render sin coste.

1.  Crea un nuevo **Web Service** en Render conectado a tu repo.
2.  Establece el **Build Command**: `pip install -r backend/requirements.txt`
3.  Establece el **Start Command**: `cd backend && uvicorn src.api.main:app --host 0.0.0.0 --port $PORT`
4.  **IMPORTANTE**: Configura las variables de entorno:
    - `DISABLE_ML_TRAINING` = `true` (Obligatorio para evitar OOM)
    - `PYTHON_VERSION` = `3.11.0`
    - `REDIS_URL` = `redis://...` (Opcional, recomendado para Dashboard)

---

## 🤖 Automatización (GitHub Actions)

El archivo `daily_training.yml`:

1.  Se activa todos los días a las **06:00 UTC**.
2.  Descarga el código y las dependencias.
3.  Ejecuta `scripts/train_model_standalone.py`.
4.  Genera un nuevo `ml_picks_classifier.joblib`.
5.  Hace **Commit & Push** automático al repositorio.
6.  Render detecta el cambio y re-despliega la API con el nuevo modelo.

---

## 📄 Licencia y Disclaimer

**MIT License** - Este software es **exclusivamente para fines educativos y de investigación**.

⚠️ **Aviso de Juego Responsable**:

- El juego puede ser adictivo. Juega con responsabilidad.
- Esta herramienta ofrece predicciones estadísticas, **no garantiza resultados**.
- No uses dinero que no puedas permitirte perder.

---

Desarrollado con ❤️ y mucho ☕ por [Jhorman Orozco](https://github.com/jhorman10).
