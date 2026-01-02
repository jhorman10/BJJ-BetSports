# 🎯 BJJ - BetSports: Intelligent Betting Assistant

> **Sistema Avanzado de Predicción Deportiva con Persistencia SQL y Caché de Alto Rendimiento**

![BJJ BetSports](https://img.shields.io/badge/BJJ-BetSports-6366f1?style=for-the-badge&logo=dependabot&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11+-3776ab?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688?style=flat-square&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![React](https://img.shields.io/badge/React-19-61dafb?style=flat-square&logo=react&logoColor=white)
![Render](https://img.shields.io/badge/Render-Hosted-46E3B7?style=flat-square&logo=render&logoColor=white)

## 📋 Descripción General

**BJJ-BetSports** es una plataforma de análisis y predicción de fútbol diseñada para operar eficientemente en la nube, optimizando el consumo de recursos sin sacrificar la persistencia de datos históricos.

### Nueva Arquitectura Unificada (SSOT)

A diferencia de versiones anteriores, el sistema ahora utiliza una arquitectura de **Fuente Única de Verdad (Single Source of Truth)** centrada en base de datos relacional:

1.  **Persistencia Robusta**: Sustitución de Redis por **PostgreSQL**. Todos los resultados de entrenamiento, estadísticas globales y picks pre-calculados se almacenan de forma permanente en SQL.
2.  **Caché Multi-Capa (Ephemerality-Aware)**:
    - **L1 (Memoria)**: Acceso instantáneo en RAM para peticiones calientes.
    - **L2 (DiskCache)**: Almacenamiento local persistente vía SQLite para mitigar reinicios del servidor sin saturar la DB.
3.  **Entrenamiento Híbrido**:
    - **GitHub Actions**: Realiza el entrenamiento pesado diariamente, garantizando que el modelo `.joblib` esté actualizado.
    - **API Runtime**: Recupera estadísticas y predicciones directamente de PostgreSQL, eliminando la necesidad de cálculos CPU-intensivos en cada request.

---

## ✨ Características Principales

### 🧠 Inteligencia Artificial

- **Modelo**: Random Forest Classifier (Optimizado para baja latencia).
- **Inferencia Instantánea**: Los picks se pre-calculan y persisten, permitiendo tiempos de respuesta de milisegundos.
- **Continuous Learning**: Ajuste dinámico de pesos basado en el feedback de aciertos/errores de apuestas anteriores.

### 🏗️ Ingeniería de Datos

- **Pipelines de Sincronización**: Sincronización automática entre el entrenamiento en CI/CD y la base de datos de producción.
- **Eficiencia de Memoria**: Arquitectura diseñada para correr en entornos de **512MB RAM**, moviendo cargas pesadas a procesos en segundo plano.

---

## 🛠️ Stack Tecnológico Actualizado

| Área              | Tecnología                  | Rol                                               |
| :---------------- | :-------------------------- | :------------------------------------------------ |
| **Backend**       | **Python 3.11 + FastAPI**   | Motor de API asíncrono.                           |
| **Base de Datos** | **PostgreSQL**              | Persistencia de largo plazo (SSOT).               |
| **Caché**         | **DiskCache (SQLite)**      | Capa de aceleración local y persistencia efímera. |
| **ML Engine**     | **Scikit-learn**            | Inferencia y entrenamiento de modelos.            |
| **Frontend**      | **React 19 + Vite**         | Interfaz de usuario PWA de alto rendimiento.      |
| **Diseño**        | **Material UI v5**          | Sistema de componentes limpio y moderno.          |
| **Infra**         | **GitHub Actions + Render** | CI/CD, Entrenamiento y Hosting.                   |

---

## 📂 Estructura Crítica del Proyecto

```bash
backend/src/
├── api/                    # Endpoints y rutas (FastAPI)
├── application/            # Casos de uso y Orquestación (SSOT logic)
├── domain/                 # Entidades y Lógica de Negocio
└── infrastructure/         # Capas de persistencia
    ├── cache/              # CacheService (Memoria + DiskCache)
    ├── data_sources/       # Integración con APIs de Fútbol
    └── repositories/       # PersistenceRepository (PostgreSQL)
```

---

## 🚀 Despliegue en Render (Nueva Configuración)

1.  Crea un **Web Service** para el Backend y una base de datos **PostgreSQL**.
2.  Enlaza la base de datos y configura las variables de entorno:
    - `DATABASE_URL`: URL de conexión a tu instancia de Postgres.
    - `DISABLE_ML_TRAINING`: `true` (Para el servicio de la API).
    - `RENDER`: `true` (Activa salvaguardas de memoria).
3.  El sistema inicializará automáticamente las tablas en el primer arranque.

---

## 🤖 Ciclo de Vida del Modelo

El workflow `daily_training.yml` asegura que el sistema esté siempre al día:

1. Se activa diariamente a las **06:00 UTC**.
2. Entrena el modelo con los datos más recientes.
3. Sincroniza las estadísticas y resultados en **PostgreSQL**.
4. Actualiza el binario `.joblib` en el repositorio.
5. Render despliega el cambio de forma automática.

## 📄 Disclaimer

Este software es para fines **educativos e investigativos**. Las predicciones estadísticas no garantizan resultados financieros. Juega con responsabilidad.

---

Desarrollado con ❤️ por [Jhorman Orozco](https://github.com/jhorman10)
