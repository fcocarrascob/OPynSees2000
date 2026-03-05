# Análisis Estático Lineal en OpenSees

## Índice
1. [Introducción](#introducción)
2. [Configuración del Análisis](#configuración-del-análisis)
3. [Componentes del Sistema de Análisis](#componentes-del-sistema-de-análisis)
4. [Teoría del Análisis Estático](#teoría-del-análisis-estático)
5. [Ejemplos Paso a Paso](#ejemplos-paso-a-paso)

---

## Introducción

El **análisis estático lineal** resuelve el sistema de ecuaciones:

$$\mathbf{K} \cdot \mathbf{U} = \mathbf{F}$$

Donde:
- $\mathbf{K}$ = matriz de rigidez global (constante para análisis lineal)
- $\mathbf{U}$ = vector de desplazamientos (incógnitas)
- $\mathbf{F}$ = vector de cargas aplicadas

### Limitaciones

✅ **Válido cuando:**
- Materiales permanecen elásticos
- Deformaciones son pequeñas
- No hay contacto ni gaps
- Geometría no cambia significativamente

❌ **No válido para:**
- Plasticidad o fluencia
- Grandes deformaciones
- Pandeo no-lineal
- Efectos P-Delta (sin geomTransf apropiado)

---

## Configuración del Análisis

### Secuencia de Comandos

```python
# 1. Sistema de ecuaciones
ops.system(systemType)

# 2. Numerador de DOF
ops.numberer(numb ererType)

# 3. Manejador de restricciones
ops.constraints(constraintType)

# 4. Test de convergencia (opcional para lineal)
ops.test(testType, tol, maxIter)

# 5. Algoritmo de solución
ops.algorithm(algorithmType)

# 6. Integrador (controla incrementos de carga)
ops.integrator(integratorType, *args)

# 7. Tipo de análisis
ops.analysis(analysisType)

# 8. Ejecutar análisis
ops.analyze(numSteps)
```

---

## Componentes del Sistema de Análisis

### 1. Sistema de Ecuaciones

Determina el **solver** para $\mathbf{K} \mathbf{U} = \mathbf{F}$:

#### BandSPD
```python
ops.system('BandSPD')
```
- **SPD** = Symmetric Positive Definite
- Matriz en formato de banda
- Rápido para estructuras bien condicionadas
- **Usar cuando:** Modelo simétrico, bien soportado, sin mecanismos

#### ProfileSPD
```python
ops.system('ProfileSPD')
```
- Almacenamiento tipo perfil (skyline)
- Mejor para matrices con ancho de banda variable
- Más eficiente en memoria que BandSPD para modelos irregulares

#### UmfPack
```python
ops.system('UmfPack')
```
- Solver multifrontal no-simétrico
- **Usar cuando:** Matriz no-simétrica, problemas generales
- Más robusto pero más lento

#### Comparación

| Solver | Velocidad | Memoria | Uso |
|--------|-----------|---------|-----|
| BandSPD | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Pórticos regulares |
| ProfileSPD | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Estructuras irregulares |
| UmfPack | ⭐⭐⭐ | ⭐⭐⭐⭐ | Problemas no-simétricos |

---

### 2. Numberer (Numerador de DOF)

Determina el **orden de numeración** de los grados de libertad para minimizar ancho de banda:

#### RCM (Reverse Cuthill-McKee)
```python
ops.numberer('RCM')
```
- Algoritmo de renumeración que reduce ancho de banda
- **Recomendado** para la mayoría de casos
- Mejora eficiencia del solver

#### Plain
```python
ops.numberer('Plain')
```
- Numeración secuencial (sin optimización)
- Más rápido de configurar, pero análisis más lento
- Usar solo para modelos muy pequeños

---

### 3. Constraints Handler

Maneja **restricciones** (apoyos, equalDOF, diafragmas):

#### Plain
```python
ops.constraints('Plain')
```
- Para restricciones simples (`fix` únicamente)
- Más rápido
- **No funciona** con `equalDOF` o `rigidDiaphragm`

#### Transformation
```python
ops.constraints('Transformation')
```
- Maneja multi-point constraints (MPC)
- **Necesario** para `equalDOF`, `rigidDiaphragm`, `rigidLink`
- Métodos de transformación de coordenadas
- **Recomendado** para estructuras con diafragmas

#### Penalty
```python
ops.constraints('Penalty', alphaS, alphaM)
```
- Método de penalty (penalización)
- `alphaS`: Factor de penalidad para restricciones de una sola DOF
- `alphaM`: Factor de penalidad para MPC
- Aproximado (no exacto)
- Rara vez usado

---

### 4. Test de Convergencia

Para análisis lineal, **no es estrictamente necesario**, pero puede ayudar a detectar problemas:

```python
ops.test('NormDispIncr', tol, maxIter, printFlag)
```

- `tol`: Tolerancia (ej. 1.0e-6)
- `maxIter`: Iteraciones máximas
- `printFlag`: 0=sin salida, 1=resumen, 2=detallado

Para análisis **lineal puro**, con algoritmo `Linear`, converge en 1 iteración.

---

### 5. Algoritmo de Solución

#### Linear
```python
ops.algorithm('Linear')
```
- **Una sola iteración**
- Exacto para problemas lineales
- Usar para análisis estático lineal

#### Newton (solo si hay no-linealidad)
```python
ops.algorithm('Newton')
```
- Newton-Raphson completo
- Para análisis no-lineal

---

### 6. Integrator

Controla cómo se **incrementa la carga**:

#### LoadControl
```python
ops.integrator('LoadControl', dLambda)
```
- `dLambda`: Incremento del factor de carga
- **dLambda = 1.0** → Carga completa en un paso
- **dLambda = 0.1** → Carga en 10 pasos incrementales

**Para análisis lineal:**
```python
ops.integrator('LoadControl', 1.0)
ops.analyze(1)  # Un solo paso aplica 100% de carga
```

---

### 7. Tipo de Análisis

```python
ops.analysis('Static')
```

Para análisis estático (vs 'Transient' para dinámico).

---

## Teoría del Análisis Estático

### Ecuación de Equilibrio

En cada nodo, las fuerzas internas deben balancear las externas:

$$\sum \mathbf{F}_{int} = \sum \mathbf{F}_{ext}$$

En forma matricial:
$$\mathbf{K} \mathbf{U} = \mathbf{F}$$

### Proceso de Solución

**1. Ensamblaje de Rigidez Global**

Cada elemento contribuye con su matriz de rigidez:

$$\mathbf{K}_{global} = \bigcup_{e=1}^{n_{elem}} \mathbf{K}_e$$

**2. Aplicación de Condiciones de Borde**

DOF fijos se eliminan (condensación estática):

$$\begin{bmatrix} \mathbf{K}_{ff} & \mathbf{K}_{fs} \\ \mathbf{K}_{sf} & \mathbf{K}_{ss} \end{bmatrix} \begin{bmatrix} \mathbf{U}_f \\ \mathbf{U}_s \end{bmatrix} = \begin{bmatrix} \mathbf{F}_f \\ \mathbf{F}_s \end{bmatrix}$$

Donde:
- Subíndice $f$ = free (libres)
- Subíndice $s$ = support (apoyados, $\mathbf{U}_s = 0$)

Sistema reducido:
$$\mathbf{K}_{ff} \mathbf{U}_f = \mathbf{F}_f$$

**3. Solución del Sistema**

Descomposición LU o Cholesky:
$$\mathbf{K}_{ff} = \mathbf{L} \mathbf{U}$$

Sustitución hacia adelante y atrás para obtener $\mathbf{U}_f$.

**4. Cálculo de Reacciones**

$$\mathbf{F}_s = \mathbf{K}_{sf} \mathbf{U}_f$$

---

## Ejemplos Paso a Paso

### Ejemplo 1: Viga Simplemente Apoyada

```python
import openseespy.opensees as ops

# Limpiar
ops.wipe()
ops.model('basic', '-ndm', 2, '-ndf', 3)

# Nodos
ops.node(1, 0.0, 0.0)
ops.node(2, 3.0, 0.0)
ops.node(3, 6.0, 0.0)

# Apoyos
ops.fix(1, 1, 1, 0)  # Pin izquierdo
ops.fix(3, 0, 1, 0)  # Rodillo derecho

# Transformación geométrica
ops.geomTransf('Linear', 1)

# Propiedades
E = 200e6  # kPa
I = 2e-4   # m⁴
A = 0.01   # m²

# Elementos
ops.element('elasticBeamColumn', 1, 1, 2, A, E, I, 1)
ops.element('elasticBeamColumn', 2, 2, 3, A, E, I, 1)

# Carga puntual en centro
ops.timeSeries('Constant', 1)
ops.pattern('Plain', 1, 1)
ops.load(2, 0.0, -50.0, 0.0)  # 50 kN hacia abajo

# Recorders
ops.recorder('Node', '-file', 'disp.out', '-time', '-node', 2, '-dof', 2, 'disp')

# ============================================
# CONFIGURACIÓN DE ANÁLISIS ESTÁTICO
# ============================================
ops.system('BandSPD')              # 1. Sistema de ecuaciones
ops.numberer('RCM')                # 2. Numerador
ops.constraints('Plain')           # 3. Restricciones simples
ops.test('NormDispIncr', 1.0e-6, 10)  # 4. Test (opcional)
ops.algorithm('Linear')            # 5. Algoritmo lineal
ops.integrator('LoadControl', 1.0) # 6. Carga en 1 paso
ops.analysis('Static')             # 7. Análisis estático

# Ejecutar
success = ops.analyze(1)

if success == 0:
    print("✓ Análisis completado con éxito")
else:
    print("✗ Análisis falló")

# ============================================
# RESULTADOS
# ============================================
# Desplazamiento en centro
disp = ops.nodeDisp(2, 2)
print(f"Desplazamiento vertical en centro: {disp*1000:.3f} mm")

# Verificación analítica: δ = PL³/(48EI) para viga con carga central
P = 50.0  # kN
L = 6.0   # m (longitud total)
delta_teorico = -(P * L**3) / (48 * E * I)  # Negativo = hacia abajo
print(f"Desplazamiento teórico: {delta_teorico*1000:.3f} mm")

# Reacciones
R1y = ops.nodeReaction(1, 2)
R3y = ops.nodeReaction(3, 2)
print(f"\nReacciones:")
print(f"Apoyo izquierdo: {R1y:.2f} kN")
print(f"Apoyo derecho: {R3y:.2f} kN")
print(f"Suma de reacciones: {R1y + R3y:.2f} kN (debe ser ≈ 50 kN)")

ops.wipe()
```

**Salida esperada:**
```
✓ Análisis completado con éxito
Desplazamiento vertical en centro: -14.062 mm
Desplazamiento teórico: -14.062 mm

Reacciones:
Apoyo izquierdo: 25.00 kN
Apoyo derecho: 25.00 kN
Suma de reacciones: 50.00 kN (debe ser ≈ 50 kN)
```

---

### Ejemplo 2: Pórtico con Carga Lateral

```python
import openseespy.opensees as ops

ops.wipe()
ops.model('basic', '-ndm', 2, '-ndf', 3)

# Geometría
H = 4.0  # m, altura
L = 6.0  # m, luz

# Nodos
ops.node(1, 0.0, 0.0)  # Base izq
ops.node(2, L, 0.0)    # Base der
ops.node(3, 0.0, H)    # Tope izq
ops.node(4, L, H)      # Tope der

# Apoyos empotrados
ops.fix(1, 1, 1, 1)
ops.fix(2, 1, 1, 1)

# Transformación
ops.geomTransf('Linear', 1)

# Materiales y propiedades
E = 200e6  # kPa

# Columnas (perfil HEB 200)
A_col = 0.0078   # m²
I_col = 5.7e-5   # m⁴

# Viga (perfil IPE 300)
A_beam = 0.0054
I_beam = 8.36e-5

# Elementos
ops.element('elasticBeamColumn', 1, 1, 3, A_col, E, I_col, 1)  # Col izq
ops.element('elasticBeamColumn', 2, 2, 4, A_col, E, I_col, 1)  # Col der
ops.element('elasticBeamColumn', 3, 3, 4, A_beam, E, I_beam, 1) # Viga

# Cargas
ops.timeSeries('Constant', 1)
ops.pattern('Plain', 1, 1)

# Carga lateral en tope izquierdo
H_force = 30.0  # kN
ops.load(3, H_force, 0.0, 0.0)

# Análisis
ops.system('ProfileSPD')
ops.numberer('RCM')
ops.constraints('Plain')
ops.algorithm('Linear')
ops.integrator('LoadControl', 1.0)
ops.analysis('Static')

ops.analyze(1)

# Resultados
disp_x_3 = ops.nodeDisp(3, 1)
disp_x_4 = ops.nodeDisp(4, 1)

print(f"Desplazamiento horizontal nodo 3: {disp_x_3*1000:.2f} mm")
print(f"Desplazamiento horizontal nodo 4: {disp_x_4*1000:.2f} mm")

# Momentos en base de columna izquierda
forces_col1 = ops.eleForce(1)
# forces = [Nx_i, Vy_i, Mz_i, Nx_j, Vy_j, Mz_j] (local)
M_base = forces_col1[2]  # Momento en nodo i (base)
print(f"\nMomento en base columna izquierda: {M_base:.2f} kN·m")

ops.wipe()
```

---

### Ejemplo 3: Estructura 3D con Carga Gravitacional

```python
import openseespy.opensees as ops

ops.wipe()
ops.model('basic', '-ndm', 3, '-ndf', 6)

# Geometría (cubo simple)
L = 4.0  # m

# Nodos base
ops.node(1, 0.0, 0.0, 0.0)
ops.node(2, L, 0.0, 0.0)
ops.node(3, L, L, 0.0)
ops.node(4, 0.0, L, 0.0)

# Nodos tope
ops.node(5, 0.0, 0.0, L)
ops.node(6, L, 0.0, L)
ops.node(7, L, L, L)
ops.node(8, 0.0, L, L)

# Apoyos (empotrados en base)
for i in range(1, 5):
    ops.fix(i, 1, 1, 1, 1, 1, 1)

# Transformación para columnas verticales
ops.geomTransf('PDelta', 1, 1, 0, 0)

# Propiedades
E = 200e6
G = E / (2 * 1.3)
A = 0.01
I = 1e-4
J = 2e-4

# Columnas (verticales)
ops.element('elasticBeamColumn', 1, 1, 5, A, E, G, J, I, I, 1)
ops.element('elasticBeamColumn', 2, 2, 6, A, E, G, J, I, I, 1)
ops.element('elasticBeamColumn', 3, 3, 7, A, E, G, J, I, I, 1)
ops.element('elasticBeamColumn', 4, 4, 8, A, E, G, J, I, I, 1)

# Transformación para vigas horizontales
ops.geomTransf('Linear', 2, 0, 0, 1)

# Vigas en nivel superior
# En dirección X
ops.element('elasticBeamColumn', 5, 5, 6, A, E, G, J, I, I, 2)
ops.element('elasticBeamColumn', 6, 8, 7, A, E, G, J, I, I, 2)
# En dirección Y
ops.element('elasticBeamColumn', 7, 5, 8, A, E, G, J, I, I, 2)
ops.element('elasticBeamColumn', 8, 6, 7, A, E, G, J, I, I, 2)

# Cargas gravitacionales en nodos superiores
W = 100.0  # kN por nodo

ops.timeSeries('Constant', 1)
ops.pattern('Plain', 1, 1)

for i in range(5, 9):
    ops.load(i, 0.0, 0.0, -W, 0.0, 0.0, 0.0)

# Análisis
ops.system('UmfPack')  # Para 3D general
ops.numberer('RCM')
ops.constraints('Plain')
ops.algorithm('Linear')
ops.integrator('LoadControl', 1.0)
ops.analysis('Static')

ops.analyze(1)

# Resultados
print("Desplazamientos verticales en nodos superiores:")
for i in range(5, 9):
    disp_z = ops.nodeDisp(i, 3)
    print(f"  Nodo {i}: {disp_z*1000:.3f} mm")

# Verificar equilibrio
total_reaction = 0.0
for i in range(1, 5):
    R_z = ops.nodeReaction(i, 3)
    total_reaction += R_z
    print(f"Reacción vertical nodo {i}: {R_z:.2f} kN")

print(f"\nReacción total: {total_reaction:.2f} kN")
print(f"Carga total aplicada: {4*W:.2f} kN")
print(f"Error: {abs(total_reaction - 4*W):.2e} kN")

ops.wipe()
```

---

## Troubleshooting

### Problema: "Analysis failed"

**Causas comunes:**
1. **Mecanismo en la estructura** (insuficientes apoyos)
2. **Elementos mal conectados** (nodos duplicados)
3. **Propiedades cero o negativas** (E, A, I)

**Solución:**
```python
# Verificar eigenvalues para detectar mecanismos
eigenvalues = ops.eigen(10)
if any(ev <= 0 for ev in eigenvalues):
    print("⚠ Eigenvalues negativos o cero detectados - mecanismo posible")
```

### Problema: Resultados ilógicos

**Verificar:**
- Unidades consistentes
- Orientación de elementos (geomTransf)
- Suma de reacciones = suma de cargas

---

## Resumen

✅ **Sistema completo de análisis:**
```python
ops.system('BandSPD')
ops.numberer('RCM')
ops.constraints('Transformation')  # Si hay MPC
ops.algorithm('Linear')
ops.integrator('LoadControl', 1.0)
ops.analysis('Static')
ops.analyze(1)
```

✅ **Para estructuras regulares:** BandSPD + RCM  
✅ **Para diafragmas rígidos:** constraints('Transformation')  
✅ **Verificar equilibrio:** ΣReacciones = ΣCargas

---

## Próximo Capítulo

Continúa con **[Análisis Modal](08-analisis-modal.md)** para análisis dinámico de vibraciones libres.
