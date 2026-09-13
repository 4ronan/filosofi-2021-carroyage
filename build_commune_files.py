#!/usr/bin/env python3
"""Transforme le CSV carroyé Filosofi 2021 en fichiers JSON par commune.

Usage:
    python build_commune_files.py Filosofi2021_carreaux_200m_csv.zip public

Les coordonnées produites sont les centres des carreaux, en WGS84.
Un carreau intersectant plusieurs communes est affecté à la première commune
de ``lcog_geo`` (intersection surfacique la plus importante, ordre Insee).
"""

from __future__ import annotations

import csv
import io
import json
import re
import sys
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from pyproj import Transformer


GRID_RE = re.compile(r"^CRS(?P<epsg>\d+)RES200mN(?P<north>\d+)E(?P<east>\d+)$")
SOURCE_MEMBERS = {
    "carreaux_200m_met.csv": 3035,
    "carreaux_200m_mart.csv": 5490,
    "carreaux_200m_reun.csv": 2975,
}


def department(code: str) -> str:
    if code.startswith(("2A", "2B")):
        return code[:2]
    if code.startswith(("97", "98")):
        return code[:3]
    return code[:2]


class CommuneWriter:
    def __init__(self, output: Path):
        self.output = output
        self.points: dict[str, list[str]] = defaultdict(list)
        self.stats: dict[str, dict[str, float | int | str]] = {}

    def _path(self, code: str) -> Path:
        return self.output / "communes" / department(code) / f"{code}.json"

    def write(self, code: str, longitude: float, latitude: float, population: str) -> None:
        stat = self.stats.setdefault(code, {"department": department(code), "cells": 0, "population": 0.0})
        self.points[code].append(f"[{longitude:.6f},{latitude:.6f},{population}]")
        stat["cells"] = int(stat["cells"]) + 1
        stat["population"] = float(stat["population"]) + float(population)

    def close(self) -> None:
        for code in sorted(self.points):
            path = self._path(code)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8", newline="") as handle:
                handle.write('{"m":2021,"c":"' + code + '","p":[')
                handle.write(",".join(self.points[code]))
                handle.write("]}\n")


def process_member(archive: zipfile.ZipFile, member: str, epsg: int, writer: CommuneWriter) -> int:
    transformer = Transformer.from_crs(epsg, 4326, always_xy=True)
    count = 0
    with archive.open(member) as raw:
        text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
        rows = csv.DictReader(text)
        for row in rows:
            match = GRID_RE.match(row["idcar_200m"])
            if not match:
                raise ValueError(f"Identifiant de carreau inattendu: {row['idcar_200m']}")
            if int(match.group("epsg")) != epsg:
                raise ValueError(f"Projection inattendue dans {member}: {row['idcar_200m']}")
            # L'identifiant indique le coin inférieur gauche : +100 m donne le centre.
            east = int(match.group("east")) + 100
            north = int(match.group("north")) + 100
            longitude, latitude = transformer.transform(east, north)
            code = row["lcog_geo"].split(",", 1)[0].strip()
            if not code:
                continue
            writer.write(code, longitude, latitude, row["ind"])
            count += 1
    return count


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: build_commune_files.py SOURCE.zip DOSSIER_SORTIE")
    source = Path(sys.argv[1]).resolve()
    output = Path(sys.argv[2]).resolve()
    output.mkdir(parents=True, exist_ok=True)

    writer = CommuneWriter(output)
    source_rows: dict[str, int] = {}
    with zipfile.ZipFile(source) as archive:
        for member, epsg in SOURCE_MEMBERS.items():
            source_rows[member] = process_member(archive, member, epsg, writer)
    writer.close()

    communes = []
    total_population = 0.0
    total_cells = 0
    for code in sorted(writer.stats):
        stat = writer.stats[code]
        item = {
            "code": code,
            "department": stat["department"],
            "cells": stat["cells"],
            "population": round(float(stat["population"]), 1),
            "url": f"communes/{stat['department']}/{code}.json",
        }
        communes.append(item)
        total_cells += int(stat["cells"])
        total_population += float(stat["population"])

    manifest = {
        "dataset": "Filosofi 2021 - carreaux de 200 m",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "coordinate_system": "EPSG:4326",
        "point": ["longitude", "latitude", "population"],
        "commune_assignment": "first lcog_geo code (largest intersected area)",
        "commune_count": len(communes),
        "cell_count": total_cells,
        "population_sum": round(total_population, 1),
        "source_rows": source_rows,
        "communes": communes,
    }
    with (output / "index.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, separators=(",", ":"))
        handle.write("\n")


if __name__ == "__main__":
    main()
