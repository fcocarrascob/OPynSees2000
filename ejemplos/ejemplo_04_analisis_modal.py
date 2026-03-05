"""
Ejemplo 04: Análisis Modal de Edificio
=======================================

Objetivo:
- Realizar análisis de valores propios (eigenvalues)
- Calcular periodos y frecuencias naturales
- Obtener formas modales (mode shapes)
- Calcular factores de participación modal
- Verificar criterio de 90% de masa participante

Sistema de unidades: kN, m, s
"""

import openseespy.opensees as ops
import numpy as np
import matplotlib.pyplot as plt

# ============================================
# LIMPIEZA Y CONFIGURACIÓN
# ============================================
ops.wipe()
ops.model('basic', '-ndm', 2, '-ndf', 3)

print("="*60)
print("EJEMPLO 04: ANÁLISIS MODAL DE EDIFICIO")
print("="*60)

# ============================================
# GEOMETRÍA - EDIFICIO DE 5 PISOS
# ============================================
num_pisos = 5
L = 6.0         # Luz de viga [m]
H = 3.0         # Altura de entrepiso [m]

print(f"\nGeometría:")
print(f"  Número de pisos: {num_pisos}")
print(f"  Luz: {L} m")
print(f"  Altura por piso: {H} m")
print(f"  Altura total: {num_pisos*H} m")

# ============================================
# NODOS
# ============================================
# 2 columnas por piso
# Nodos base: 1, 2
# Piso i: nodos 2*i+1, 2*i+2

nodos_por_piso = {}

# Base
ops.node(1, 0.0, 0.0)
ops.node(2, L, 0.0)
ops.fix(1, 1, 1, 1)
ops.fix(2, 1, 1, 1)
nodos_por_piso[0] = [1, 2]

# Pisos
tag = 3
for piso in range(1, num_pisos + 1):
    y = piso * H
    ops.node(tag, 0.0, y)
    ops.node(tag+1, L, y)
    nodos_por_piso[piso] = [tag, tag+1]
    tag += 2

print(f"\nNodos creados: {tag-1}")

# ============================================
# MATERIALES Y SECCIONES
# ============================================
E = 25e6        # kN/m² (concreto)
G = 10.4e6      # kN/m²

# Columnas: 40x40 cm
b_col = 0.40
A_col = b_col * b_col
I_col = (b_col**4) / 12

# Vigas: 30x50 cm
b_viga = 0.30
h_viga = 0.50
A_viga = b_viga * h_viga
I_viga = (b_viga * h_viga**3) / 12

print(f"\nSecciones:")
print(f"  Columnas: {b_col*100:.0f}x{b_col*100:.0f} cm")
print(f"  Vigas:    {b_viga*100:.0f}x{h_viga*100:.0f} cm")

# ============================================
# TRANSFORMACIONES
# ============================================
ops.geomTransf('Linear', 1)

# ============================================
# ELEMENTOS
# ============================================
elem_tag = 1

# Columnas
for piso in range(num_pisos):
    node_base_izq = nodos_por_piso[piso][0]
    node_base_der = nodos_por_piso[piso][1]
    node_top_izq = nodos_por_piso[piso+1][0]
    node_top_der = nodos_por_piso[piso+1][1]
    
    # Columna izquierda
    ops.element('elasticBeamColumn', elem_tag, node_base_izq, node_top_izq,
                A_col, E, I_col, 1)
    elem_tag += 1
    
    # Columna derecha
    ops.element('elasticBeamColumn', elem_tag, node_base_der, node_top_der,
                A_col, E, I_col, 1)
    elem_tag += 1

# Vigas
for piso in range(1, num_pisos + 1):
    node_izq = nodos_por_piso[piso][0]
    node_der = nodos_por_piso[piso][1]
    
    ops.element('elasticBeamColumn', elem_tag, node_izq, node_der,
                A_viga, E, I_viga, 1)
    elem_tag += 1

print(f"Elementos creados: {elem_tag-1} ({2*num_pisos} columnas + {num_pisos} vigas)")

# ============================================
# MASAS
# ============================================
# Masa por nodo (ton = kN·s²/m)
masa_nodo = 20.0  # ton

for piso in range(1, num_pisos + 1):
    for node in nodos_por_piso[piso]:
        # Solo masa traslacional (X, Y)
        # Rotación se calcula automáticamente por OpenSees
        ops.mass(node, masa_nodo, masa_nodo, 0.0)

masa_total = 2 * num_pisos * masa_nodo
print(f"\nMasas:")
print(f"  Por nodo: {masa_nodo} ton")
print(f"  Total: {masa_total} ton")

# ============================================
# ANÁLISIS MODAL
# ============================================
print("\n" + "="*60)
print("ANÁLISIS MODAL")
print("="*60)

# Número de modos a calcular
num_modos = min(3 * num_pisos, 15)  # Suficientes modos

# Resolver eigenvalues
eigenvalues = ops.eigen(num_modos)

# Calcular periodos y frecuencias
periodos = []
frecuencias = []
omega = []

print(f"\nModos de vibración (primeros {num_modos}):")
print("-" * 60)
print(f"{'Modo':<6} {'ω [rad/s]':<12} {'f [Hz]':<12} {'T [s]':<12}")
print("-" * 60)

for i, eigenvalue in enumerate(eigenvalues, start=1):
    omega_i = np.sqrt(eigenvalue)
    freq_i = omega_i / (2 * np.pi)
    periodo_i = 1.0 / freq_i if freq_i > 0 else 0.0
    
    omega.append(omega_i)
    frecuencias.append(freq_i)
    periodos.append(periodo_i)
    
    print(f"{i:<6} {omega_i:<12.4f} {freq_i:<12.4f} {periodo_i:<12.4f}")

# ============================================
# FORMAS MODALES
# ============================================
print("\n" + "="*60)
print("FORMAS MODALES (Desplazamientos Normalizados)")
print("="*60)

# Extraer formas modales para los primeros 3 modos
num_modos_plot = min(3, num_modos)
mode_shapes = {}

for modo in range(1, num_modos_plot + 1):
    print(f"\nModo {modo} (T = {periodos[modo-1]:.4f} s):")
    print(f"{'Piso':<6} {'Nodo':<6} {'Ux':<12} {'Uy':<12} {'Rz':<12}")
    print("-" * 54)
    
    shape = []
    for piso in range(1, num_pisos + 1):
        for node in nodos_por_piso[piso]:
            # Obtener desplazamientos del modo
            # En OpenSees, después de eigen(), se puede usar nodeEigenvector
            ux = ops.nodeEigenvector(node, modo, 1)  # DOF 1 (X)
            uy = ops.nodeEigenvector(node, modo, 2)  # DOF 2 (Y)
            rz = ops.nodeEigenvector(node, modo, 3)  # DOF 3 (Rot)
            
            shape.append((piso, node, ux, uy, rz))
            print(f"{piso:<6} {node:<6} {ux:<12.6f} {uy:<12.6f} {rz:<12.6f}")
    
    mode_shapes[modo] = shape

# ============================================
# FACTORES DE PARTICIPACIÓN MODAL
# ============================================
print("\n" + "="*60)
print("FACTORES DE PARTICIPACIÓN MODAL")
print("="*60)

# Calcular manualmente: Γ_i = (φ_i^T · M · r) / (φ_i^T · M · φ_i)
# donde r = vector de influencia (todos 1 para dirección X)

factores_participacion = []
masa_efectiva = []
masa_acumulada = []
suma_masa = 0.0

print(f"\n{'Modo':<6} {'Γ':<12} {'Meff [ton]':<14} {'% Masa':<10} {'Acum %':<10}")
print("-" * 56)

for modo in range(1, num_modos + 1):
    # Numerador: Σ(m_i * φ_i)
    numerador = 0.0
    # Denominador: Σ(m_i * φ_i²)
    denominador = 0.0
    
    for piso in range(1, num_pisos + 1):
        for node in nodos_por_piso[piso]:
            phi = ops.nodeEigenvector(node, modo, 1)  # Dirección X
            m = masa_nodo
            
            numerador += m * phi
            denominador += m * phi * phi
    
    gamma = numerador / denominador if denominador != 0 else 0.0
    m_eff = (numerador**2) / denominador if denominador != 0 else 0.0
    
    factores_participacion.append(gamma)
    masa_efectiva.append(m_eff)
    
    percent = (m_eff / masa_total) * 100
    suma_masa += m_eff
    cumulative = (suma_masa / masa_total) * 100
    
    masa_acumulada.append(suma_masa)
    
    print(f"{modo:<6} {gamma:<12.6f} {m_eff:<14.2f} {percent:<10.2f} {cumulative:<10.2f}")

# Verificar criterio del 90%
print("\n" + "-" * 56)
porcentaje_90 = (suma_masa / masa_total) * 100
if porcentaje_90 >= 90.0:
    print(f"✓ Criterio de 90% cumplido: {porcentaje_90:.2f}%")
else:
    print(f"✗ NO cumple 90%: {porcentaje_90:.2f}% (Calcular más modos)")

# ============================================
# PERÍODO EMPÍRICO (COMPARACIÓN)
# ============================================
print("\n" + "="*60)
print("COMPARACIÓN CON PERÍODO EMPÍRICO")
print("="*60)

# Fórmulas empíricas
H_total = num_pisos * H

# ASCE 7 para pórticos de concreto: Ta = 0.0466 * H^0.9 (H en m, Ta en s)
T_empirico_ASCE = 0.0466 * (H_total ** 0.9)

# Rayleigh aproximado: T ≈ 0.1 * N (N = número de pisos)
T_rayleigh = 0.1 * num_pisos

# Período fundamental calculado
T1 = periodos[0]

print(f"\nPeríodo fundamental (T1):")
print(f"  Valor calculado:     {T1:.4f} s")
print(f"  ASCE 7 (empírico):   {T_empirico_ASCE:.4f} s")
print(f"  Rayleigh (0.1*N):    {T_rayleigh:.4f} s")
print(f"\nRelación T1/Ta:        {T1/T_empirico_ASCE:.2f}")

# ============================================
# VISUALIZACIÓN
# ============================================
print("\n" + "="*60)
print("GENERANDO GRÁFICAS...")
print("="*60)

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# -------------------------
# GRÁFICA 1: Periodos
# -------------------------
ax1 = axes[0, 0]
modos_plot = range(1, min(10, num_modos) + 1)
periodos_plot = periodos[:min(10, num_modos)]

ax1.plot(modos_plot, periodos_plot, 'o-', linewidth=2, markersize=8)
ax1.set_xlabel('Modo')
ax1.set_ylabel('Periodo [s]')
ax1.set_title('Periodos Naturales')
ax1.grid(True, alpha=0.3)
ax1.set_xticks(modos_plot)

# -------------------------
# GRÁFICA 2: Masa Efectiva
# -------------------------
ax2 = axes[0, 1]
modos_plot2 = range(1, min(10, num_modos) + 1)
masa_pct = [(m/masa_total)*100 for m in masa_efectiva[:min(10, num_modos)]]

bars = ax2.bar(modos_plot2, masa_pct, alpha=0.7, color='steelblue')
ax2.axhline(90, color='red', linestyle='--', linewidth=2, label='90% requerido')
ax2.set_xlabel('Modo')
ax2.set_ylabel('Masa Efectiva [%]')
ax2.set_title('Participación de Masa por Modo')
ax2.grid(True, alpha=0.3, axis='y')
ax2.legend()
ax2.set_xticks(modos_plot2)

# -------------------------
# GRÁFICA 3: Formas Modales
# -------------------------
ax3 = axes[1, 0]

alturas = [i * H for i in range(num_pisos + 1)]
colores = ['blue', 'red', 'green']

for modo in range(1, min(4, num_modos + 1)):
    # Extraer desplazamientos en X de columna izquierda
    desps = [0.0]  # Base
    for piso in range(1, num_pisos + 1):
        node_izq = nodos_por_piso[piso][0]
        disp_x = ops.nodeEigenvector(node_izq, modo, 1)
        desps.append(disp_x)
    
    # Normalizar por máximo
    max_disp = max(abs(d) for d in desps)
    if max_disp > 0:
        desps_norm = [d/max_disp for d in desps]
    else:
        desps_norm = desps
    
    ax3.plot(desps_norm, alturas, 'o-', linewidth=2, markersize=6,
             color=colores[modo-1], label=f'Modo {modo} (T={periodos[modo-1]:.3f}s)')

ax3.set_xlabel('Desplazamiento Normalizado')
ax3.set_ylabel('Altura [m]')
ax3.set_title('Formas Modales (Primeros 3 Modos)')
ax3.grid(True, alpha=0.3)
ax3.legend()
ax3.axvline(0, color='black', linewidth=0.8)

# -------------------------
# GRÁFICA 4: Masa Acumulada
# -------------------------
ax4 = axes[1, 1]
modos_plot4 = range(1, min(10, num_modos) + 1)
masa_acum_pct = [(m/masa_total)*100 for m in masa_acumulada[:min(10, num_modos)]]

ax4.plot(modos_plot4, masa_acum_pct, 'o-', linewidth=2, markersize=8, color='darkgreen')
ax4.axhline(90, color='red', linestyle='--', linewidth=2, label='90% requerido')
ax4.set_xlabel('Modo')
ax4.set_ylabel('Masa Acumulada [%]')
ax4.set_title('Masa Efectiva Acumulada')
ax4.grid(True, alpha=0.3)
ax4.legend()
ax4.set_ylim([0, 105])
ax4.set_xticks(modos_plot4)

plt.tight_layout()
plt.savefig('ejemplo_04_resultados.png', dpi=150)
print("\nGráfica guardada: ejemplo_04_resultados.png")
plt.show()

# ============================================
# RESUMEN
# ============================================
print("\n" + "="*60)
print("RESUMEN")
print("="*60)
print(f"Período fundamental:       {T1:.4f} s")
print(f"Frecuencia fundamental:    {frecuencias[0]:.4f} Hz")
print(f"Masa efectiva (modo 1):    {masa_efectiva[0]:.2f} ton ({masa_efectiva[0]/masa_total*100:.2f}%)")
print(f"Masa participante total:   {suma_masa:.2f} ton ({suma_masa/masa_total*100:.2f}%)")

if (suma_masa/masa_total) >= 0.90:
    print(f"\n✓ Se captura >90% de la masa en {len(masa_acumulada)} modos")
else:
    print(f"\n✗ Se requieren más modos (actualmente {suma_masa/masa_total*100:.2f}%)")

print("\n" + "="*60)
print("FIN DEL ANÁLISIS MODAL")
print("="*60)
