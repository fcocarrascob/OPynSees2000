"""
Ejemplo 02: Pórtico 2D con Análisis de Deriva
==============================================

Objetivo:
- Modelar un pórtico simple de 2 pisos
- Aplicar carga lateral (simulando viento o sismo)
- Calcular derivas de entrepiso
- Verificar criterio de deriva (drift < 0.7%)

Sistema de unidades: kN, m, s
"""

import openseespy.opensees as ops
import numpy as np
import matplotlib.pyplot as plt

# ============================================
# LIMPIEZA Y CONFIGURACIÓN INICIAL
# ============================================
ops.wipe()
ops.model('basic', '-ndm', 2, '-ndf', 3)

print("="*60)
print("EJEMPLO 02: PÓRTICO 2D CON ANÁLISIS DE DERIVA")
print("="*60)

# ============================================
# GEOMETRÍA
# ============================================
L = 6.0         # Luz de viga [m]
H1 = 3.5        # Altura piso 1 [m]
H2 = 3.0        # Altura piso 2 [m]

# Nodos (Tag, X, Y)
#     5 ---- 6
#     |      |
#     3 ---- 4
#     |      |  
#     1 ---- 2

ops.node(1, 0.0, 0.0)
ops.node(2, L, 0.0)
ops.node(3, 0.0, H1)
ops.node(4, L, H1)
ops.node(5, 0.0, H1+H2)
ops.node(6, L, H1+H2)

print(f"\nGeometría:")
print(f"  Luz de viga: {L} m")
print(f"  Altura piso 1: {H1} m")
print(f"  Altura piso 2: {H2} m")

# ============================================
# CONDICIONES DE BORDE
# ============================================
ops.fix(1, 1, 1, 1)  # Base empotrada
ops.fix(2, 1, 1, 1)  # Base empotrada

# ============================================
# MATERIALES Y SECCIONES
# ============================================
# Acero estructural
E_steel = 200e6      # kN/m²
G_steel = 77e6       # kN/m²

# Secciones típicas (perfiles IPE/HEB europeos aproximados)
# Columnas: HEB 300 (A ≈ 0.0149 m², I ≈ 2.519e-4 m⁴)
A_col = 0.0149
I_col = 2.519e-4

# Vigas: IPE 300 (A ≈ 0.0054 m², I ≈ 8.356e-5 m⁴)
A_beam = 0.0054
I_beam = 8.356e-5

print(f"\nSecciones:")
print(f"  Columna HEB300: A={A_col} m², I={I_col} m⁴")
print(f"  Viga IPE300:    A={A_beam} m², I={I_beam} m⁴")

# ============================================
# TRANSFORMACIONES GEOMÉTRICAS
# ============================================
ops.geomTransf('Linear', 1)  # Para vigas y columnas

# ============================================
# ELEMENTOS
# ============================================
# Columnas piso 1
ops.element('elasticBeamColumn', 1, 1, 3, A_col, E_steel, I_col, 1)
ops.element('elasticBeamColumn', 2, 2, 4, A_col, E_steel, I_col, 1)

# Viga piso 1
ops.element('elasticBeamColumn', 3, 3, 4, A_beam, E_steel, I_beam, 1)

# Columnas piso 2
ops.element('elasticBeamColumn', 4, 3, 5, A_col, E_steel, I_col, 1)
ops.element('elasticBeamColumn', 5, 4, 6, A_col, E_steel, I_col, 1)

# Viga piso 2
ops.element('elasticBeamColumn', 6, 5, 6, A_beam, E_steel, I_beam, 1)

print(f"\nElementos creados: 6 (4 columnas + 2 vigas)")

# ============================================
# MASAS (para análisis dinámico futuro)
# ============================================
# Masa tributaria por nodo [ton = kN·s²/m]
mass_floor1 = 15.0   # ton por nodo
mass_floor2 = 12.0   # ton por nodo

for node in [3, 4]:
    ops.mass(node, mass_floor1, mass_floor1, 0.0)

for node in [5, 6]:
    ops.mass(node, mass_floor2, mass_floor2, 0.0)

# ============================================
# CASO DE CARGA 1: GRAVEDAD
# ============================================
print("\n" + "="*60)
print("CASO DE CARGA 1: GRAVEDAD")
print("="*60)

ops.timeSeries('Constant', 1)
ops.pattern('Plain', 100, 1)

# Cargas verticales en cada piso (carga muerta + viva)
P_floor1 = 150.0  # kN por nodo
P_floor2 = 120.0  # kN por nodo

ops.load(3, 0.0, -P_floor1, 0.0)
ops.load(4, 0.0, -P_floor1, 0.0)
ops.load(5, 0.0, -P_floor2, 0.0)
ops.load(6, 0.0, -P_floor2, 0.0)

print(f"Carga piso 1: {P_floor1} kN/nodo")
print(f"Carga piso 2: {P_floor2} kN/nodo")

# Sistema de análisis
ops.system('BandSPD')
ops.numberer('Plain')
ops.constraints('Plain')
ops.algorithm('Linear')
ops.integrator('LoadControl', 1.0)
ops.analysis('Static')

# Analizar
ops.analyze(1)

# Resultados gravedad
disp3_gravity = ops.nodeDisp(3, 2)
disp5_gravity = ops.nodeDisp(5, 2)

print(f"\nDesplazamientos verticales por gravedad:")
print(f"  Nodo 3 (piso 1): {disp3_gravity*1000:.2f} mm")
print(f"  Nodo 5 (piso 2): {disp5_gravity*1000:.2f} mm")

# Congelar cargas de gravedad
ops.loadConst('-time', 0.0)

# ============================================
# CASO DE CARGA 2: CARGA LATERAL
# ============================================
print("\n" + "="*60)
print("CASO DE CARGA 2: CARGA LATERAL")
print("="*60)

ops.timeSeries('Linear', 2)
ops.pattern('Plain', 200, 2)

# Cargas laterales proporcionales a masa (distribución triangular)
# Fuerza base total = 100 kN
F_base = 100.0  # kN

# Distribución según FEMA (Fi = Fx * (wi*hi) / Σ(wi*hi))
w1 = mass_floor1 * 9.81 * 2  # Peso piso 1 (2 nodos)
w2 = mass_floor2 * 9.81 * 2  # Peso piso 2

h1 = H1
h2 = H1 + H2

sum_wh = w1*h1 + w2*h2

F1 = F_base * (w1*h1) / sum_wh
F2 = F_base * (w2*h2) / sum_wh

# Aplicar mitad de la fuerza a cada nodo del piso
ops.load(3, F1/2, 0.0, 0.0)
ops.load(4, F1/2, 0.0, 0.0)
ops.load(5, F2/2, 0.0, 0.0)
ops.load(6, F2/2, 0.0, 0.0)

print(f"Fuerza base total: {F_base} kN")
print(f"  Piso 1: {F1:.2f} kN ({F1/F_base*100:.1f}%)")
print(f"  Piso 2: {F2:.2f} kN ({F2/F_base*100:.1f}%)")

# Analizar carga lateral
ops.analyze(1)

# ============================================
# CÁLCULO DE DERIVAS
# ============================================
print("\n" + "="*60)
print("ANÁLISIS DE DERIVAS")
print("="*60)

# Desplazamientos laterales
disp1 = 0.0  # Base (fija)
disp3 = ops.nodeDisp(3, 1)
disp5 = ops.nodeDisp(5, 1)

# Derivas de entrepiso
drift1 = abs(disp3 - disp1) / H1
drift2 = abs(disp5 - disp3) / H2

# Derivas en porcentaje
drift1_pct = drift1 * 100
drift2_pct = drift2 * 100

print(f"\nDesplazamientos laterales:")
print(f"  Piso 1 (nodo 3): {disp3*1000:.2f} mm")
print(f"  Piso 2 (nodo 5): {disp5*1000:.2f} mm")

print(f"\nDerivas de entrepiso:")
print(f"  Piso 1: {drift1:.6f} ({drift1_pct:.3f}%)")
print(f"  Piso 2: {drift2:.6f} ({drift2_pct:.3f}%)")

# Criterio de aceptación (típico: 0.7% para edificios)
drift_limit = 0.007

print(f"\nCriterio de deriva límite: {drift_limit*100}%")
if drift1 <= drift_limit and drift2 <= drift_limit:
    print("✓ Cumple con criterio de deriva")
else:
    print("✗ NO cumple con criterio de deriva")
    if drift1 > drift_limit:
        print(f"  Piso 1 excede límite: {drift1_pct:.3f}% > {drift_limit*100}%")
    if drift2 > drift_limit:
        print(f"  Piso 2 excede límite: {drift2_pct:.3f}% > {drift_limit*100}%")

# ============================================
# REACCIONES EN APOYOS
# ============================================
print("\n" + "="*60)
print("REACCIONES EN APOYOS")
print("="*60)

R1x = ops.nodeReaction(1, 1)
R1y = ops.nodeReaction(1, 2)
R2x = ops.nodeReaction(2, 1)
R2y = ops.nodeReaction(2, 2)

print(f"\nNodo 1 (apoyo izquierdo):")
print(f"  Rx = {R1x:.2f} kN")
print(f"  Ry = {R1y:.2f} kN")

print(f"\nNodo 2 (apoyo derecho):")
print(f"  Rx = {R2x:.2f} kN")
print(f"  Ry = {R2y:.2f} kN")

# Verificación de equilibrio
sum_Rx = R1x + R2x
sum_Ry = R1y + R2y
applied_Fx = F1 + F2
applied_Fy = -2*(P_floor1 + P_floor2)

print(f"\nVerificación de equilibrio:")
print(f"  ΣRx = {sum_Rx:.2f} kN (Debe ser ≈ {-applied_Fx:.2f} kN)")
print(f"  ΣRy = {sum_Ry:.2f} kN (Debe ser ≈ {-applied_Fy:.2f} kN)")

# ============================================
# VISUALIZACIÓN
# ============================================
print("\n" + "="*60)
print("GENERANDO GRÁFICAS...")
print("="*60)

# Factor de escala para visualización
scale_factor = 50

# Configuración deformada
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

# Configuración original
nodes_coord = {
    1: (0, 0), 2: (L, 0),
    3: (0, H1), 4: (L, H1),
    5: (0, H1+H2), 6: (L, H1+H2)
}

elements = [
    (1, 3), (2, 4),  # Columnas piso 1
    (3, 4),          # Viga piso 1
    (3, 5), (4, 6),  # Columnas piso 2
    (5, 6)           # Viga piso 2
]

# GRÁFICA 1: Configuración deformada
ax1.set_title('Configuración Deformada (Escala x{})'.format(scale_factor))
ax1.set_xlabel('X [m]')
ax1.set_ylabel('Y [m]')
ax1.grid(True, alpha=0.3)
ax1.axis('equal')

# Dibujar original
for elem in elements:
    n1, n2 = elem
    x = [nodes_coord[n1][0], nodes_coord[n2][0]]
    y = [nodes_coord[n1][1], nodes_coord[n2][1]]
    ax1.plot(x, y, 'b--', linewidth=1, alpha=0.5, label='Original' if elem == elements[0] else '')

# Dibujar deformada
nodes_deformed = {}
for node in [1, 2, 3, 4, 5, 6]:
    x_orig, y_orig = nodes_coord[node]
    dx = ops.nodeDisp(node, 1) * scale_factor
    dy = ops.nodeDisp(node, 2) * scale_factor
    nodes_deformed[node] = (x_orig + dx, y_orig + dy)

for elem in elements:
    n1, n2 = elem
    x = [nodes_deformed[n1][0], nodes_deformed[n2][0]]
    y = [nodes_deformed[n1][1], nodes_deformed[n2][1]]
    ax1.plot(x, y, 'r-', linewidth=2, label='Deformada' if elem == elements[0] else '')

ax1.legend()

# GRÁFICA 2: Derivas
ax2.set_title('Derivas de Entrepiso')
ax2.set_xlabel('Deriva [%]')
ax2.set_ylabel('Nivel')
ax2.grid(True, alpha=0.3)

pisos = ['Piso 1', 'Piso 2']
derivas = [drift1_pct, drift2_pct]
colores = ['green' if d <= drift_limit*100 else 'red' for d in derivas]

ax2.barh(pisos, derivas, color=colores, alpha=0.7)
ax2.axvline(drift_limit*100, color='orange', linestyle='--', linewidth=2, label=f'Límite ({drift_limit*100}%)')
ax2.legend()

# Añadir valores
for i, (piso, deriva) in enumerate(zip(pisos, derivas)):
    ax2.text(deriva + 0.01, i, f'{deriva:.3f}%', va='center')

plt.tight_layout()
plt.savefig('ejemplo_02_resultados.png', dpi=150)
print("\nGráfica guardada: ejemplo_02_resultados.png")
plt.show()

# ============================================
# RESUMEN FINAL
# ============================================
print("\n" + "="*60)
print("RESUMEN")
print("="*60)
print(f"Deriva máxima: {max(drift1_pct, drift2_pct):.3f}%")
print(f"Desplazamiento máximo: {disp5*1000:.2f} mm")
print(f"Cortante basal: {sum_Rx:.2f} kN")
if max(drift1, drift2) <= drift_limit:
    print("\n✓ Estructura cumple con criterio de deriva")
else:
    print("\n✗ Estructura NO cumple. Considerar:")
    print("  - Aumentar secciones de columnas")
    print("  - Agregar arriostramientos o muros")
    print("  - Aumentar rigidez de conexiones")

print("\n" + "="*60)
print("FIN DEL ANÁLISIS")
print("="*60)
