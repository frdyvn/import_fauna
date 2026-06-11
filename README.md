# Import Fauna (SINP) — Plugin QGIS

Plugin QGIS pour importer les fichiers CSV exportés depuis le portail [observatoire-fauna.fr](https://observatoire-fauna.fr) en couches vecteur.

---

## Fonctionnalités

- **Détection automatique** des fichiers CSV Fauna dans un dossier, par analyse du contenu (indépendamment du nom des fichiers)
- **Prise en charge de plusieurs fichiers** par type de géométrie (ex. `point_site1.csv`, `point_site2.csv`)
- **Liste des fichiers détectés** avec type de géométrie, nombre d'entités et cases à cocher pour sélectionner ce qui sera importé
- **Jointure des métadonnées** : si un fichier `Metadonnees.csv` est présent, ses champs sont dénormalisés directement dans la table attributaire de chaque couche (clé `IdJdd` ↔ `IdJeuDonnees`) ; plusieurs fichiers de métadonnées sont fusionnés automatiquement avec déduplication
- **Export GeoPackage optionnel** : toutes les couches sont écrites dans un `.gpkg`, puis chargées depuis ce fichier plutôt que comme couches temporaires
- **Groupement automatique** des couches importées et zoom sur l'emprise globale
- Projection **Lambert 93 (EPSG:2154)**

---

## Utilisation

1. Ouvrir le plugin via le menu **Extensions → Import Fauna (SINP)** ou l'icône dans la barre d'outils
2. **Parcourir** pour sélectionner le dossier contenant les exports CSV Fauna
3. Cliquer sur **Scanner** — le plugin détecte automatiquement les fichiers d'observation (points, linéaires, polygones) et les éventuels fichiers de métadonnées
4. Cocher les fichiers à importer
5. Configurer les options :
   - **Joindre les métadonnées** (si un fichier de métadonnées est détecté)
   - **Exporter en GeoPackage** (optionnel)
6. Cliquer sur **Charger les données sélectionnées**

---

## Format des fichiers source

Les fichiers attendus sont les exports tabulés (`.csv` délimité par tabulation) produits par le portail Fauna. Le plugin reconnaît les fichiers d'observation à la présence d'une colonne `GeomWkt` contenant les géométries en WKT (format `SRID=2154;TYPENAME(...)`).

Les fichiers de métadonnées sont détectés par leur nom (`metadonn*`, `metadata*`) ou par la présence de la colonne `NomJeuDonnees`.

---

## Configuration requise

- QGIS ≥ 3.16
- Python ≥ 3.7 (inclus dans QGIS)

---

## Auteur

Frédérick YVONNE — [CEN Nouvelle-Aquitaine](https://cen-na.org)

## Licence

Ce plugin est distribué sous licence [GNU GPL v2](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html), conformément aux conditions du dépôt officiel des extensions QGIS.
