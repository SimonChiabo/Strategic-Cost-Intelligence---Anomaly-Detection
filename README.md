# 📈 Strategic Cost Intelligence & Predictive Audit Sink

### A high-performance financial forecasting ecosystem with SOX-compliant auditing and Prophet-driven intelligence.

---

## ⚡ Core Tech Stack
Este ecosistema ha sido diseñado bajo principios de **High-Performance Computing** y **Type Safety**, garantizando la integridad de las proyecciones financieras críticas.

*   **[Polars](https://pola.rs/)**: Motor de procesamiento de datos ultra-veloz basado en Rust para la limpieza y agregación masiva de transacciones.
*   **[Prophet](https://facebook.github.io/prophet/)**: Motor de inferencia bayesiana para la generación de series temporales con estacionalidad compleja.
*   **[Pydantic v2](https://docs.pydantic.dev/latest/)**: Capa de validación estricta y contratos de datos para asegurar el intercambio íntegro entre servicios.
*   **[ConnectorX](https://github.com/sfu-db/connectorx)**: Driver de acceso a base de datos de alto rendimiento para la extracción masiva de datos desde PostgreSQL.

---

## 🛠️ Engineering Highlights

### 🧠 Intelligence Sink & Reliability Matrix
El sistema no solo proyecta costos, sino que audita la calidad de su propia inferencia. Utilizamos una métrica ponderada de confianza para determinar la viabilidad del pronóstico:

$$Index = \max(0, 1 - (0.7 \cdot MAPE_{norm} + 0.3 \cdot \text{Volatility}))$$

Donde $MAPE_{norm}$ representa el error porcentual absoluto medio normalizado y la "Volatility" mide la amplitud del intervalo de confianza relativo al valor predicho.

### 🛡️ Defensive Burn Rate (Cold Start Protection)
Para evitar falsos positivos en el análisis de consumo, el sistema implementa una lógica de protección defensiva:
- **Requisito Mínimo**: Se requiere una base histórica de $\geq 3$ meses para habilitar el análisis de **Burn Rate**.
- **Cold Start**: Ante datos insuficientes, el Auditor bloquea las proyecciones para evitar conclusiones erróneas en centros de costo nuevos o con data inconsistente.

### 🇦🇷 Regional & Seasonal Context
Integración nativa de **feriados nacionales de Argentina** y estacionalidades locales. Esto permite al motor de auditoría detectar anomalías de flujo de caja durante periodos críticos (e.g., cuellos de botella por feriados puente o festividades regionales).

---

## 🏗️ Architecture & Decoupling
El proyecto sigue una arquitectura de servicios desacoplada, facilitando la migración futura a microservicios a través de FastAPI:

1.  **Forecaster Service**: Orquestador de Polars y Prophet encargado de la ingeniería de datos y persistencia.
2.  **Audit Service**: Motor de reglas de negocio y cálculo de confiabilidad (Intelligence Report).
3.  **Streamlit UI**: Interfaz de comando centralizada para la visualización interactiva y gestión de escenarios.

---

## 🚀 Usage & Portability

### Demo Mode (Zero DB Setup)
El sistema cuenta con detección automática de entorno. Si no existe una `DATABASE_URL` configurada, el "Command Center" activa el **Mock Mode**:
- Carga automática de escenarios de simulación.
- Generación de datos sintéticos con patrones de negocio realistas.
- Ideal para demostraciones rápidas y validación de UI/UX.

### Compliance & SOX Readiness
Diseñado para entornos financieros auditables:
- **Timestamps Inmutables**: Cada ejecución queda registrada con marcas de tiempo precisas.
- **Model Versioning**: Trazabilidad completa de la versión del algoritmo utilizado para cada punto de dato proyectado.

---
> [!NOTE]
> **Minimalismo y Resultados**: Este ecosistema prioriza la entrega de insights accionables sobre el volumen de datos, permitiendo a los departamentos financieros tomar decisiones basadas en evidencia probabilística.
