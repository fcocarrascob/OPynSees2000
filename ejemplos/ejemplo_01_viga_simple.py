"""
EJEMPLO 1: VIGA SIMPLEMENTE APOYADA
=====================================

Descripción:
  Viga de 6m de longitud, simplemente apoyada en ambos extremos,
  sometida a una carga puntual de 50 kN en el centro.

Objetivos de aprendizaje:
  - Crear un modelo 2D básico
  - Definir elementos elasticBeamColumn
  - Aplicar condiciones de borde simples
  - Realizar análisis estático lineal
  - Comparar con solución analítica

Solución analítica:
  δ_max = P*L³ / (48*E*I)  (deflexión en el centro)
  R1 = R2 = P/2             (reacciones en apoyos)

Sistema de unidades: kN - m - s
"""

import openseespy.opensees as ops
import math

# ============================================
# PARÁMETROS DEL PROBLEMA
# ============================================
# Geometría
L = 6.0     # m, longitud total de la viga
L_half = L / 2

# Propiedades de la sección (IPE 300)
E = 200e6   # kPa (200 GPa, acero estructural)
I = 8.36e-5 # m⁴ (momento de inercia mayor)
A = 5.38e-3 # m² (área de la sección)

# Carga
P = 50.0    # kN (carga puntual hacia abajo)

# ============================================
# INICIALIZACIÓN DEL MODELO
# ============================================
print("=" * 60)
print("EJEMPLO 1: VIGA SIMPLEMENTE APOYADA")
print("=" * 60)
print("\nInicializando modelo...")

ops.wipe()
ops.model('basic', '-ndm', 2, '-ndf', 3)

# ============================================
# DEFINIR NODOS
# ============================================
print("Creando nodos...")

ops.node(1, 0.0, 0.0)        # Apoyo izquierdo
ops.node(2, L_half, 0.0)     # Centro (donde va la carga)
ops.node(3, L, 0.0)          # Apoyo derecho

# ============================================
# CONDICIONES DE BORDE
# ============================================
print("Aplicando condiciones de borde...")

# Nodo 1: Pin (articulación) - restringido en X y Y, libre en rotación
ops.fix(1, 1, 1, 0)

# Nodo 3: Rodillo - libre en X, restringido en Y, libre en rotación
ops.fix(3, 0, 1, 0)

# ============================================
# TRANSFORMACIÓN GEOMÉTRICA
# ============================================
# Para viga horizontal, transformación lineal simple
ops.geomTransf('Linear', 1)

# ============================================
# DEFINIR ELEMENTOS
# ============================================
print("Creando elementos...")

# Elemento 1: Del nodo 1 al nodo 2
ops.element('elasticBeamColumn', 1, 1, 2, A, E, I, 1)

# Elemento 2: Del nodo 2 al nodo 3
ops.element('elasticBeamColumn', 2, 2, 3, A, E, I, 1)

# ============================================
# DEFINIR CARGAS
# ============================================
print("Aplicando cargas...")

# Time series constante
ops.timeSeries('Constant', 1)

# Pattern de carga
ops.pattern('Plain', 1, 1)

# Carga puntual en el centro (negativa = hacia abajo)
ops.load(2, 0.0, -P, 0.0)

# ============================================
# DEFINIR RECORDERS
# ============================================
# Guardar desplazamientos del nodo central
ops.recorder('Node', '-file', 'ejemplo01_disp.out', '-time', 
             '-node', 2, '-dof', 1, 2, 3, 'disp')

# Guardar reacciones en los apoyos
ops.recorder('Node', '-file', 'ejemplo01_reactions.out', '-time',
             '-node', 1, 3, '-dof', 1, 2, 3, 'reaction')

# ============================================
# CONFIGURAR ANÁLISIS
# ============================================
print("Configurando análisis estático...")

# Sistema de ecuaciones (matriz simétrica positiva definida, banda)
ops.system('BandSPD')

# Numerador (Reverse Cuthill-McKee para minimizar ancho de banda)
ops.numberer('RCM')

# Manejador de restricciones (Plain para restricciones simples)
ops.constraints('Plain')

# Test de convergencia (opcional para análisis lineal)
ops.test('NormDispIncr', 1.0e-6, 10)

# Algoritmo (Linear para análisis lineal elástico)
ops.algorithm('Linear')

# Integrador (LoadControl con factor 1.0 = aplicar 100% de carga en 1 paso)
ops.integrator('LoadControl', 1.0)

# Tipo de análisis
ops.analysis('Static')

# ============================================
# EJECUTAR ANÁLISIS
# ============================================
print("Ejecutando análisis...")

success = ops.analyze(1)

if success == 0:
    print("✓ Análisis completado exitosamente\n")
else:
    print("✗ Análisis falló\n")
    ops.wipe()
    exit()

# ============================================
# PROCESAR RESULTADOS
# ============================================
print("=" * 60)
print("RESULTADOS")
print("=" * 60)

# Desplazamientos en el nodo central
disp_x = ops.nodeDisp(2, 1)  # Horizontal
disp_y = ops.nodeDisp(2, 2)  # Vertical
rot_z = ops.nodeDisp(2, 3)   # Rotación

print(f"\nDesplazamientos en el centro de la viga (nodo 2):")
print(f"  Horizontal (X): {disp_x*1000:.4f} mm")
print(f"  Vertical (Y):   {disp_y*1000:.4f} mm")
print(f"  Rotación:       {rot_z:.6f} rad")

# Reacciones en los apoyos
R1_x = ops.nodeReaction(1, 1)
R1_y = ops.nodeReaction(1, 2)
M1_z = ops.nodeReaction(1, 3)

R3_x = ops.nodeReaction(3, 1)
R3_y = ops.nodeReaction(3, 2)
M3_z = ops.nodeReaction(3, 3)

print(f"\nReacciones en apoyo izquierdo (nodo 1):")
print(f"  Horizontal: {R1_x:.4f} kN")
print(f"  Vertical:   {R1_y:.4f} kN")
print(f"  Momento:    {M1_z:.4f} kN·m")

print(f"\nReacciones en apoyo derecho (nodo 3):")
print(f"  Horizontal: {R3_x:.4f} kN")
print(f"  Vertical:   {R3_y:.4f} kN")
print(f"  Momento:    {M3_z:.4f} kN·m")

# ============================================
# VERIFICACIÓN CON SOLUCIÓN ANALÍTICA
# ============================================
print("\n" + "=" * 60)
print("VERIFICACIÓN")
print("=" * 60)

# Deflexión en el centro (solución analítica)
delta_analytical = (P * L**3) / (48 * E * I)

print(f"\nDeflexión en el centro:")
print(f"  OpenSees:        {abs(disp_y)*1000:.4f} mm")
print(f"  Solución exacta: {delta_analytical*1000:.4f} mm")

error_disp = abs(abs(disp_y) - delta_analytical) / delta_analytical * 100
print(f"  Error relativo:  {error_disp:.4f} %")

# Reacciones (solución analítica)
R_analytical = P / 2

print(f"\nReacciones verticales:")
print(f"  OpenSees R1:     {R1_y:.4f} kN")
print(f"  OpenSees R2:     {R3_y:.4f} kN")
print(f"  Solución exacta: {R_analytical:.4f} kN")

error_R1 = abs(R1_y - R_analytical) / R_analytical * 100
error_R2 = abs(R3_y - R_analytical) / R_analytical * 100
print(f"  Error R1:        {error_R1:.4f} %")
print(f"  Error R2:        {error_R2:.4f} %")

# Equilibrio vertical (suma de reacciones = carga aplicada)
total_vertical = R1_y + R3_y
error_equilibrio = abs(total_vertical - P)

print(f"\nVerificación de equilibrio:")
print(f"  Suma de reacciones verticales: {total_vertical:.4f} kN")
print(f"  Carga aplicada:                {P:.4f} kN")
print(f"  Error:                         {error_equilibrio:.6f} kN")

if error_equilibrio < 1e-6:
    print("  ✓ Equilibrio satisfecho")
else:
    print("  ✗ Equilibrio NO satisfecho")

# ============================================
# FUERZAS EN ELEMENTOS
# ============================================
print("\n" + "=" * 60)
print("FUERZAS EN ELEMENTOS")
print("=" * 60)

# Obtener fuerzas en elemento 1 (coordenadas locales)
forces_ele1 = ops.eleForce(1)
# Formato: [Nx_i, Vy_i, Mz_i, Nx_j, Vy_j, Mz_j]

print(f"\nElemento 1 (nodo 1 → nodo 2):")
print(f"  Nodo i (1):")
print(f"    Axial:   {forces_ele1[0]:.4f} kN")
print(f"    Corte:   {forces_ele1[1]:.4f} kN")
print(f"    Momento: {forces_ele1[2]:.4f} kN·m")
print(f"  Nodo j (2):")
print(f"    Axial:   {forces_ele1[3]:.4f} kN")
print(f"    Corte:   {forces_ele1[4]:.4f} kN")
print(f"    Momento: {forces_ele1[5]:.4f} kN·m")

# Momento máximo en la viga (en el centro)
M_max_analytical = P * L / 4  # Para carga puntual en centro

print(f"\nMomento máximo en el centro de la viga:")
print(f"  OpenSees:        {abs(forces_ele1[5]):.4f} kN·m")
print(f"  Solución exacta: {M_max_analytical:.4f} kN·m")

error_moment = abs(abs(forces_ele1[5]) - M_max_analytical) / M_max_analytical * 100
print(f"  Error relativo:  {error_moment:.4f} %")

# ============================================
# CRITERIOS DE ACEPTACIÓN
# ============================================
print("\n" + "=" * 60)
print("VALIDACIÓN FINAL")
print("=" * 60)

tolerancia_error = 0.1  # 0.1%

tests = [
    ("Deflexión central", error_disp),
    ("Reacción R1", error_R1),
    ("Reacción R2", error_R2),
    ("Momento máximo", error_moment)
]

all_passed = True
for test_name, error in tests:
    status = "✓ PASS" if error < tolerancia_error else "✗ FAIL"
    print(f"{test_name:20s}: {error:6.4f}% | {status}")
    if error >= tolerancia_error:
        all_passed = False

if all_passed:
    print("\n✓✓✓ TODOS LOS TESTS PASARON ✓✓✓")
else:
    print("\n✗✗✗ ALGUNOS TESTS FALLARON ✗✗✗")

# ============================================
# LIMPIAR
# ============================================
ops.wipe()

print("\n" + "=" * 60)
print("Análisis completado. Archivos de salida generados:")
print("  - ejemplo01_disp.out (desplazamientos)")
print("  - ejemplo01_reactions.out (reacciones)")
print("=" * 60)
