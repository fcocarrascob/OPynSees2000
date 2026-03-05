# Guía Completa de OpenSeesPy

## Construcción de Modelos 3D y Análisis Estructural

Esta documentación proporciona una guía completa para construir modelos estructurales 3D en OpenSeesPy y realizar diversos tipos de análisis. Está diseñada para ingenieros estructurales con conocimientos intermedios en análisis estructural.

---

## 📚 Contenido

### Fundamentos y Teoría

1. **[Fundamentos de OpenSees](01-fundamentos.md)**
   - Workflow general de modelado
   - Teoría del Método de Elementos Finitos
   - Sistemas de coordenadas y grados de libertad
   - Inicialización de modelos

2. **[Materiales y Secciones](02-materiales-y-secciones.md)**
   - Materiales uniaxiales (Elastic, Steel02, Concrete01/02)
   - Secciones elásticas y de fibra
   - Teoría constitutiva y comportamiento no-lineal
   - Ejemplos de definición

3. **[Elementos Estructurales](03-elementos.md)**
   - Elementos de viga-columna (elastic, force-based, displacement-based)
   - Elementos tipo truss
   - Elementos shell
   - Teoría y comparación

4. **[Construcción de Modelos 3D](04-modelo-3d.md)**
   - Definición de nodos en 3D
   - Sistemas de coordenadas locales y globales
   - Transformaciones geométricas
   - Orientación de elementos

### Condiciones de Borde y Cargas

5. **[Condiciones de Borde](05-condiciones-de-borde.md)**
   - Apoyos fijos y articulados
   - Vínculos rígidos (equalDOF)
   - Diafragmas rígidos
   - Offsets de conexión

6. **[Cargas y Patrones](06-cargas.md)**
   - Cargas muertas y vivas
   - Cargas distribuidas en elementos
   - Patrones de carga y time series
   - Combinaciones de carga

### Análisis Estructural

7. **[Análisis Estático Lineal](07-analisis-estatico.md)**
   - Configuración del análisis
   - Solvers y algoritmos
   - Teoría del análisis estático
   - Ejemplos completos paso a paso

8. **[Análisis Modal](08-analisis-modal.md)**
   - Análisis de valores propios
   - Extracción de períodos y frecuencias
   - Formas modales
   - Participación modal
   - Ejemplos prácticos

9. **[Análisis Sísmico](09-analisis-sismico.md)**
   - Análisis espectral (implementación manual)
   - Análisis tiempo-historia
   - Excitación uniforme
   - Combinación modal (CQC, SRSS)
   - Ejemplos de aplicación

### Resultados y Optimización

10. **[Recorders y Resultados](10-recorders.md)**
    - Recorders de nodos y elementos
    - Extracción de desplazamientos y fuerzas
    - Post-procesamiento de datos
    - Visualización de resultados

11. **[Buenas Prácticas](11-buenas-practicas.md)**
    - Consistencia de unidades
    - Refinamiento de malla
    - Criterios de convergencia
    - Debugging y validación
    - Errores comunes

---

## 🎯 Ejemplos Prácticos

Todos los ejemplos están en la carpeta [`ejemplos/`](../ejemplos/):

- **[Ejemplo 1: Viga Simple](../ejemplos/ejemplo_01_viga_simple.py)** - Viga simplemente apoyada con carga puntual
- **[Ejemplo 2: Pórtico 2D](../ejemplos/ejemplo_02_portico_2d.py)** - Pórtico plano con análisis estático
- **[Ejemplo 3: Pórtico 3D](../ejemplos/ejemplo_03_portico_3d.py)** - Marco espacial con cargas gravitacionales
- **[Ejemplo 4: Análisis Modal](../ejemplos/ejemplo_04_analisis_modal.py)** - Extracción de modos de vibración
- **[Ejemplo 5: Espectro de Respuesta](../ejemplos/ejemplo_05_espectro_respuesta.py)** - Implementación de análisis espectral

---

## 🚀 Inicio Rápido

### Instalación

```bash
pip install openseespy
```

### Primer Modelo - Viga en Voladizo

```python
import openseespy.opensees as ops
import numpy as np

# 1. Inicializar modelo
ops.wipe()
ops.model('basic', '-ndm', 2, '-ndf', 3)

# 2. Definir nodos
ops.node(1, 0.0, 0.0)
ops.node(2, 3.0, 0.0)

# 3. Condiciones de borde
ops.fix(1, 1, 1, 1)  # Empotramiento

# 4. Transformación geométrica
ops.geomTransf('Linear', 1)

# 5. Definir elemento
E = 200e9  # Pa
I = 1e-4   # m⁴
A = 0.01   # m²
ops.element('elasticBeamColumn', 1, 1, 2, A, E, I, 1)

# 6. Cargas
ops.timeSeries('Constant', 1)
ops.pattern('Plain', 1, 1)
ops.load(2, 0.0, -10000.0, 0.0)  # 10 kN hacia abajo

# 7. Análisis
ops.system('BandSPD')
ops.numberer('RCM')
ops.constraints('Plain')
ops.algorithm('Linear')
ops.integrator('LoadControl', 1.0)
ops.analysis('Static')
ops.analyze(1)

# 8. Resultados
disp = ops.nodeDisp(2, 2)
print(f"Desplazamiento vertical en extremo libre: {disp*1000:.2f} mm")

ops.wipe()
```

---

## 📖 Cómo Usar Esta Documentación

### Para Principiantes en OpenSees
1. Comienza con **[Fundamentos](01-fundamentos.md)** para entender el workflow
2. Estudia **[Materiales y Secciones](02-materiales-y-secciones.md)** y **[Elementos](03-elementos.md)**
3. Practica con **[Análisis Estático](07-analisis-estatico.md)** y los ejemplos básicos
4. Avanza a análisis dinámicos cuando domines lo básico

### Para Usuarios Intermedios
1. Revisa **[Construcción de Modelos 3D](04-modelo-3d.md)** para estructuras espaciales
2. Estudia **[Análisis Modal](08-analisis-modal.md)** y **[Sísmico](09-analisis-sismico.md)**
3. Consulta **[Buenas Prácticas](11-buenas-practicas.md)** para optimizar tus modelos

### Para Referencia Rápida
- Usa el índice de cada archivo para saltar a secciones específicas
- Los ejemplos incluyen código completo y comentado
- Cada sección de teoría está vinculada con su aplicación práctica

---

## 🎓 Requisitos Previos

### Conocimientos Recomendados
- Mecánica de sólidos y resistencia de materiales
- Análisis estructural básico (método de rigidez)
- Programación básica en Python
- Conceptos de dinámica estructural (para análisis modal/sísmico)

### Software
- Python 3.7 o superior
- OpenSeesPy (última versión)
- Librerías opcionales: numpy, matplotlib (para post-procesamiento)

---

## 📝 Convenciones

### Sistemas de Unidades
Esta documentación utiliza principalmente el **Sistema Internacional (SI)** con:
- Fuerza: kN (kilonewton)
- Longitud: m (metro)
- Tiempo: s (segundo)
- Masa: tonelada (kN·s²/m)
- Esfuerzo: kPa, MPa, GPa

**Importante:** OpenSees es agnóstico a unidades. El usuario debe mantener consistencia.

### Notación
- `ops.comando()` - Comandos de OpenSeesPy
- **Negrita** - Conceptos importantes
- *Cursiva* - Variables y parámetros
- `código` - Código inline

---

## 🔗 Referencias

### Documentación Oficial
- [OpenSees Command Language Manual](https://opensees.berkeley.edu/)
- [OpenSeesPy Documentation](https://openseespydoc.readthedocs.io/)
- [OpenSees Wiki](https://opensees.berkeley.edu/wiki/)

### Teoría y Fundamentos
- McKenna, F., Fenves, G. L., & Scott, M. H. (2000). *Open System for Earthquake Engineering Simulation*. University of California, Berkeley.
- Neuenhofer, A., & Filippou, F. C. (1997). *Evaluation of Nonlinear Frame Finite-Element Models*. Journal of Structural Engineering.

### Códigos de Diseño Sísmico
- ASCE 7 (American Society of Civil Engineers)
- Eurocode 8
- NCh433 (Chile) / E.030 (Perú) / NSR-10 (Colombia)

---

## 🤝 Contribuciones

Esta documentación está en constante desarrollo. Las sugerencias y correcciones son bienvenidas.

---

## ⚠️ Disclaimer

Esta documentación es con fines educativos. Los modelos y análisis realizados con OpenSees deben ser verificados y validados por ingenieros calificados antes de su uso en proyectos reales.

---

**Última actualización:** Marzo 2026  
**Versión:** 1.0  
**Autor:** Documentación técnica para OPynSees2000
