"""
Modelo de datos interno de OPynSees2000.

Dataclasses que representan los objetos del modelo estructural
sin dependencia de OpenSeesPy. Sirven como capa intermedia entre
la GUI y la generación de scripts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MaterialType(Enum):
    """Tipos de material uniaxial soportados."""
    ELASTIC = "Elastic"
    STEEL02 = "Steel02"
    CONCRETE01 = "Concrete01"
    CONCRETE02 = "Concrete02"
    ELASTIC_PP = "ElasticPP"
    HYSTERETIC = "Hysteretic"


class SectionType(Enum):
    """Tipos de sección."""
    ELASTIC_2D = "Elastic2D"
    ELASTIC_3D = "Elastic3D"
    FIBER = "Fiber"


class ElementType(Enum):
    """Tipos de elemento."""
    ELASTIC_BEAM_COLUMN = "elasticBeamColumn"
    FORCE_BEAM_COLUMN = "forceBeamColumn"
    DISP_BEAM_COLUMN = "dispBeamColumn"
    TRUSS = "Truss"
    COROT_TRUSS = "corotTruss"
    SHELL_MITC4 = "ShellMITC4"


class TransfType(Enum):
    """Tipos de transformación geométrica."""
    LINEAR = "Linear"
    PDELTA = "PDelta"
    COROTATIONAL = "Corotational"


class FixityDOF(Enum):
    """Grados de libertad para condiciones de borde (3D, 6 DOF)."""
    FREE = 0
    FIXED = 1


# ---------------------------------------------------------------------------
# Dataclasses del modelo
# ---------------------------------------------------------------------------

@dataclass
class Node:
    """Nodo del modelo."""
    tag: int
    x: float
    y: float
    z: float = 0.0
    fixity: tuple[int, ...] = ()      # (dx, dy, dz, rx, ry, rz) → 0=libre, 1=fijo
    mass: tuple[float, ...] = ()      # masa nodal por DOF

    @property
    def coords(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)

    @property
    def is_fixed(self) -> bool:
        return any(f == 1 for f in self.fixity)

    @property
    def is_fully_fixed(self) -> bool:
        return all(f == 1 for f in self.fixity) and len(self.fixity) > 0

    def to_dict(self) -> dict:
        """Serializa el nodo a diccionario."""
        return {
            "tag": self.tag,
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "fixity": list(self.fixity),
            "mass": list(self.mass),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Node":
        """Crea un nodo desde diccionario."""
        return cls(
            tag=d["tag"],
            x=d["x"],
            y=d["y"],
            z=d.get("z", 0.0),
            fixity=tuple(d.get("fixity", ())),
            mass=tuple(d.get("mass", ())),
        )


@dataclass
class Material:
    """Material uniaxial."""
    tag: int
    name: str
    mat_type: MaterialType
    params: dict = field(default_factory=dict)
    # params varía según tipo. Ej: Steel02 → {Fy, E0, b, R0, cR1, cR2}

    def to_dict(self) -> dict:
        return {
            "tag": self.tag,
            "name": self.name,
            "mat_type": self.mat_type.value,
            "params": dict(self.params),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Material":
        return cls(
            tag=d["tag"],
            name=d["name"],
            mat_type=MaterialType(d["mat_type"]),
            params=d.get("params", {}),
        )


@dataclass
class Section:
    """Sección transversal."""
    tag: int
    name: str
    sec_type: SectionType
    params: dict = field(default_factory=dict)
    # Ej Elastic3D: {A, E, Iz, Iy, G, J}

    def to_dict(self) -> dict:
        return {
            "tag": self.tag,
            "name": self.name,
            "sec_type": self.sec_type.value,
            "params": dict(self.params),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Section":
        return cls(
            tag=d["tag"],
            name=d["name"],
            sec_type=SectionType(d["sec_type"]),
            params=d.get("params", {}),
        )


@dataclass
class GeomTransf:
    """Transformación geométrica."""
    tag: int
    transf_type: TransfType
    vecxz: tuple[float, float, float] = (0.0, 0.0, 1.0)

    def to_dict(self) -> dict:
        return {
            "tag": self.tag,
            "transf_type": self.transf_type.value,
            "vecxz": list(self.vecxz),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "GeomTransf":
        return cls(
            tag=d["tag"],
            transf_type=TransfType(d["transf_type"]),
            vecxz=tuple(d.get("vecxz", (0.0, 0.0, 1.0))),
        )


@dataclass
class Element:
    """Elemento estructural."""
    tag: int
    elem_type: ElementType
    node_i: int
    node_j: int
    node_k: Optional[int] = None      # Para Shell (4 nodos)
    node_l: Optional[int] = None      # Para Shell (4 nodos)
    section_tag: Optional[int] = None
    transf_tag: Optional[int] = None
    params: dict = field(default_factory=dict)

    @property
    def is_shell(self) -> bool:
        """True si es un elemento de área (Shell)."""
        return self.elem_type == ElementType.SHELL_MITC4

    @property
    def node_tags(self) -> tuple[int, ...]:
        """Retorna todos los tags de nodos del elemento."""
        if self.is_shell:
            return (self.node_i, self.node_j, self.node_k or 0, self.node_l or 0)
        return (self.node_i, self.node_j)

    def to_dict(self) -> dict:
        d = {
            "tag": self.tag,
            "elem_type": self.elem_type.value,
            "node_i": self.node_i,
            "node_j": self.node_j,
            "section_tag": self.section_tag,
            "transf_tag": self.transf_tag,
            "params": dict(self.params),
        }
        if self.node_k is not None:
            d["node_k"] = self.node_k
        if self.node_l is not None:
            d["node_l"] = self.node_l
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Element":
        return cls(
            tag=d["tag"],
            elem_type=ElementType(d["elem_type"]),
            node_i=d["node_i"],
            node_j=d["node_j"],
            node_k=d.get("node_k"),
            node_l=d.get("node_l"),
            section_tag=d.get("section_tag"),
            transf_tag=d.get("transf_tag"),
            params=d.get("params", {}),
        )


@dataclass
class NodalLoad:
    """Carga nodal."""
    node_tag: int
    fx: float = 0.0
    fy: float = 0.0
    fz: float = 0.0
    mx: float = 0.0
    my: float = 0.0
    mz: float = 0.0

    def to_dict(self) -> dict:
        return {
            "node_tag": self.node_tag,
            "fx": self.fx, "fy": self.fy, "fz": self.fz,
            "mx": self.mx, "my": self.my, "mz": self.mz,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "NodalLoad":
        return cls(
            node_tag=d["node_tag"],
            fx=d.get("fx", 0.0), fy=d.get("fy", 0.0), fz=d.get("fz", 0.0),
            mx=d.get("mx", 0.0), my=d.get("my", 0.0), mz=d.get("mz", 0.0),
        )


@dataclass
class LoadPattern:
    """Patrón de carga."""
    tag: int
    name: str
    time_series_type: str = "Constant"
    loads: list[NodalLoad] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "tag": self.tag,
            "name": self.name,
            "time_series_type": self.time_series_type,
            "loads": [load.to_dict() for load in self.loads],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "LoadPattern":
        return cls(
            tag=d["tag"],
            name=d["name"],
            time_series_type=d.get("time_series_type", "Constant"),
            loads=[NodalLoad.from_dict(ld) for ld in d.get("loads", [])],
        )


# ---------------------------------------------------------------------------
# Contenedor principal del modelo
# ---------------------------------------------------------------------------

@dataclass
class StructuralModel:
    """
    Contenedor central de todos los objetos del modelo.
    Es el 'documento' que la GUI edita.
    """
    ndm: int = 3                                # dimensiones del modelo
    ndf: int = 6                                # grados de libertad por nodo

    nodes: dict[int, Node] = field(default_factory=dict)
    materials: dict[int, Material] = field(default_factory=dict)
    sections: dict[int, Section] = field(default_factory=dict)
    geom_transfs: dict[int, GeomTransf] = field(default_factory=dict)
    elements: dict[int, Element] = field(default_factory=dict)
    load_patterns: dict[int, LoadPattern] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def next_node_tag(self) -> int:
        return max(self.nodes.keys(), default=0) + 1

    def next_material_tag(self) -> int:
        return max(self.materials.keys(), default=0) + 1

    def next_section_tag(self) -> int:
        return max(self.sections.keys(), default=0) + 1

    def next_element_tag(self) -> int:
        return max(self.elements.keys(), default=0) + 1

    def next_transf_tag(self) -> int:
        return max(self.geom_transfs.keys(), default=0) + 1

    def next_pattern_tag(self) -> int:
        return max(self.load_patterns.keys(), default=0) + 1

    def to_dict(self) -> dict:
        """Serializa el modelo completo a diccionario."""
        return {
            "ndm": self.ndm,
            "ndf": self.ndf,
            "nodes": {str(k): v.to_dict() for k, v in self.nodes.items()},
            "materials": {str(k): v.to_dict() for k, v in self.materials.items()},
            "sections": {str(k): v.to_dict() for k, v in self.sections.items()},
            "geom_transfs": {str(k): v.to_dict() for k, v in self.geom_transfs.items()},
            "elements": {str(k): v.to_dict() for k, v in self.elements.items()},
            "load_patterns": {str(k): v.to_dict() for k, v in self.load_patterns.items()},
        }

    @classmethod
    def from_dict(cls, d: dict) -> "StructuralModel":
        """Crea un modelo desde diccionario."""
        model = cls(ndm=d.get("ndm", 3), ndf=d.get("ndf", 6))
        for k, v in d.get("nodes", {}).items():
            model.nodes[int(k)] = Node.from_dict(v)
        for k, v in d.get("materials", {}).items():
            model.materials[int(k)] = Material.from_dict(v)
        for k, v in d.get("sections", {}).items():
            model.sections[int(k)] = Section.from_dict(v)
        for k, v in d.get("geom_transfs", {}).items():
            model.geom_transfs[int(k)] = GeomTransf.from_dict(v)
        for k, v in d.get("elements", {}).items():
            model.elements[int(k)] = Element.from_dict(v)
        for k, v in d.get("load_patterns", {}).items():
            model.load_patterns[int(k)] = LoadPattern.from_dict(v)
        return model

    def clear(self) -> None:
        """Borra todo el modelo."""
        self.nodes.clear()
        self.materials.clear()
        self.sections.clear()
        self.geom_transfs.clear()
        self.elements.clear()
        self.load_patterns.clear()

    # ------------------------------------------------------------------
    # Demo: pórtico 3D  2 vanos × 2 vanos × 2 pisos
    # ------------------------------------------------------------------

    @classmethod
    def create_demo(cls) -> "StructuralModel":
        """Crea un pórtico 3D de demostración."""
        model = cls(ndm=3, ndf=6)

        # --- Parámetros geométricos ---
        spans_x = [0.0, 5.0, 10.0]         # 2 vanos en X de 5 m
        spans_y = [0.0, 4.0, 8.0]          # 2 vanos en Y de 4 m
        heights = [0.0, 3.5, 7.0]          # 2 pisos de 3.5 m

        # --- Nodos ---
        tag = 1
        node_grid: dict[tuple[int, int, int], int] = {}
        for iz, z in enumerate(heights):
            for iy, y in enumerate(spans_y):
                for ix, x in enumerate(spans_x):
                    fixity = (1, 1, 1, 1, 1, 1) if iz == 0 else ()
                    node = Node(tag=tag, x=x, y=y, z=z, fixity=fixity)
                    model.nodes[tag] = node
                    node_grid[(ix, iy, iz)] = tag
                    tag += 1

        # --- Material & Sección demo ---
        model.materials[1] = Material(
            tag=1, name="Concreto f'c=28 MPa",
            mat_type=MaterialType.ELASTIC,
            params={"E": 24_821_000.0}  # kN/m²
        )
        model.sections[1] = Section(
            tag=1, name="Columna 40×40",
            sec_type=SectionType.ELASTIC_3D,
            params={"A": 0.16, "E": 24_821_000.0,
                    "Iz": 2.1333e-3, "Iy": 2.1333e-3,
                    "G": 10_342_000.0, "J": 3.6053e-3}
        )
        model.sections[2] = Section(
            tag=2, name="Viga 30×50",
            sec_type=SectionType.ELASTIC_3D,
            params={"A": 0.15, "E": 24_821_000.0,
                    "Iz": 3.125e-3, "Iy": 1.125e-3,
                    "G": 10_342_000.0, "J": 3.516e-3}
        )

        # --- Transformaciones ---
        model.geom_transfs[1] = GeomTransf(
            tag=1, transf_type=TransfType.PDELTA, vecxz=(1.0, 0.0, 0.0)
        )  # columnas
        model.geom_transfs[2] = GeomTransf(
            tag=2, transf_type=TransfType.LINEAR, vecxz=(0.0, 0.0, 1.0)
        )  # vigas

        # --- Elementos ---
        elem_tag = 1

        # Columnas (verticales)
        for iz in range(len(heights) - 1):
            for iy in range(len(spans_y)):
                for ix in range(len(spans_x)):
                    ni = node_grid[(ix, iy, iz)]
                    nj = node_grid[(ix, iy, iz + 1)]
                    model.elements[elem_tag] = Element(
                        tag=elem_tag,
                        elem_type=ElementType.ELASTIC_BEAM_COLUMN,
                        node_i=ni, node_j=nj,
                        section_tag=1, transf_tag=1,
                    )
                    elem_tag += 1

        # Vigas en X
        for iz in range(1, len(heights)):
            for iy in range(len(spans_y)):
                for ix in range(len(spans_x) - 1):
                    ni = node_grid[(ix, iy, iz)]
                    nj = node_grid[(ix + 1, iy, iz)]
                    model.elements[elem_tag] = Element(
                        tag=elem_tag,
                        elem_type=ElementType.ELASTIC_BEAM_COLUMN,
                        node_i=ni, node_j=nj,
                        section_tag=2, transf_tag=2,
                    )
                    elem_tag += 1

        # Vigas en Y
        for iz in range(1, len(heights)):
            for ix in range(len(spans_x)):
                for iy in range(len(spans_y) - 1):
                    ni = node_grid[(ix, iy, iz)]
                    nj = node_grid[(ix, iy + 1, iz)]
                    model.elements[elem_tag] = Element(
                        tag=elem_tag,
                        elem_type=ElementType.ELASTIC_BEAM_COLUMN,
                        node_i=ni, node_j=nj,
                        section_tag=2, transf_tag=2,
                    )
                    elem_tag += 1

        return model
