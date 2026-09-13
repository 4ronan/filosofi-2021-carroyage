# Carroyage Filosofi 2021 par commune

Données carroyées Insee Filosofi 2021 à 200 mètres, converties en coordonnées WGS84 et réparties par commune.

## Contenu

- `index.json` : manifeste national ;
- `communes/{département}/{code-insee}.json` : carreaux habités d'une commune ;
- `build_commune_files.py` : générateur reproductible.

Exemple : `communes/16/16166.json` pour L'Isle-d'Espagnac.

Chaque point est un tableau compact `[longitude, latitude, population]` :

```json
{"m":2021,"c":"16166","p":[[0.191628,45.651777,103.5]]}
```

Un carreau traversant plusieurs communes est rattaché au premier code de `lcog_geo`, correspondant à la plus grande surface d'intersection. Cela évite de compter plusieurs fois sa population.

Source : [Insee — Filosofi 2021, données carroyées](https://www.insee.fr/fr/statistiques/8735162?sommaire=8735243).
