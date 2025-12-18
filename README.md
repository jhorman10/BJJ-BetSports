# 🎯 BJJ - BetSports

Bot de predicción de apuestas deportivas basado en inteligencia artificial y análisis estadístico.

![BJJ BetSports](https://img.shields.io/badge/BJJ-BetSports-6366f1?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11+-3776ab?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688?style=flat-square&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18+-61dafb?style=flat-square&logo=react&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.3+-3178c6?style=flat-square&logo=typescript&logoColor=white)

## 📋 Descripción

BJJ-BetSports es una aplicación web que utiliza algoritmos de machine learning y distribución de Poisson para predecir resultados de partidos de fútbol. El proyecto está diseñado con fines educativos.

### Características

- 🔮 **Predicciones de partidos**: Probabilidades de victoria local, empate y visitante
- ⚽ **Goles esperados**: Predicción de goles usando distribución de Poisson
- 📊 **Análisis Over/Under**: Probabilidades de más/menos de 2.5 goles
- 🌍 **Múltiples ligas**: Premier League, La Liga, Serie A, Bundesliga y más
- 🎨 **UI moderna**: Interfaz oscura con diseño glassmorphism

## 🏗️ Arquitectura

```
BJJ-BetSports/
├── backend/            # API FastAPI (Python)
│   ├── src/
│   │   ├── domain/     # Entidades, servicios, value objects
│   │   ├── application/# Casos de uso, DTOs
│   │   ├── infrastructure/# Fuentes de datos
│   │   └── api/        # Rutas FastAPI
│   └── tests/          # Tests unitarios
├── frontend/           # React 18 + TypeScript
│   └── src/
│       ├── components/ # Componentes UI
│       ├── hooks/      # Custom hooks
│       └── services/   # Cliente API
└── render.yaml         # Configuración de deploy
```

## 🚀 Inicio Rápido

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.api.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Visita: http://localhost:5174

## 📡 Fuentes de Datos

| Fuente              | Tipo | Datos                                |
| ------------------- | ---- | ------------------------------------ |
| Football-Data.co.uk | CSV  | Resultados históricos y cuotas       |
| API-Football        | REST | Partidos en vivo (opcional)          |
| Football-Data.org   | REST | Equipos y clasificaciones (opcional) |

## 🧪 Tests

```bash
cd backend
pytest tests/ -v
```

## 📄 Licencia

MIT License - Solo para fines educativos.

---

Desarrollado con ❤️ usando Python, FastAPI, React y Material UI.
