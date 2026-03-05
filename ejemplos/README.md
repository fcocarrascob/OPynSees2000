# Ejemplos Prácticos de OpenSeesPy

Este directorio contiene ejemplos completos y ejecutables de modelos estructurales en OpenSeesPy.

## 📚 Lista de Ejemplos

### Básicos

1. **[ejemplo_01_viga_simple.py](ejemplo_01_viga_simple.py)**
   - Viga simplemente apoyada con carga puntual
   - Comparación con solución analítica
   - Análisis estático lineal

2. **[ejemplo_02_portico_2d.py](ejemplo_02_portico_2d.py)**
   - Pórtico plano con carga lateral
   - Elementos beam-column
   - Cálculo de derivas

### Intermedios

3. **[ejemplo_03_portico_3d.py](ejemplo_03_portico_3d.py)**
   - Marco espacial de 2 pisos
   - Diafragmas rígidos
   - Cargas gravitacionales

4. **[ejemplo_04_analisis_modal.py](ejemplo_04_analisis_modal.py)**
   - Edificio de 3 pisos
   - Extracción de períodos y formas modales
   - Participación modal

### Avanzados

5. **[ejemplo_05_espectro_respuesta.py](ejemplo_05_espectro_respuesta.py)**
   - Implementación manual de análisis espectral
   - Combinación modal (CQC)
   - Espectro de diseño según código

## 🚀 Cómo Usar

### Requisitos
```bash
pip install openseespy numpy matplotlib
```

### Ejecutar Ejemplos
```bash
python ejemplo_01_viga_simple.py
```

## 📖 Estructura de Cada Ejemplo

Cada script incluye:
- ✅ Comentarios detallados
- ✅ Verificación de resultados
- ✅ Comparación con soluciones conocidas
- ✅ Buenas prácticas de codificación
- ✅ Manejo de unidades consistente

## 🎯 Aprendizaje Progresivo

**Principiantes:** Empezar con ejemplos 01-02  
**Intermedios:** Continuar con ejemplos 03-04  
**Avanzados:** Estudiar ejemplo 05

---

**Nota:** Todos los ejemplos usan el sistema de unidades kN-m-s.
