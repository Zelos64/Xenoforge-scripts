# Convertisseur WEM → XB1-WEM (Opus)

## Objectif

Ce script convertit un fichier audio quelconque en un fichier
`.wem` utilisant le codec OPUS. Contrairement à un Opus classique,
ce format ne s'appuie pas sur les pages Ogg : chaque frame Opus est précédée
de son propre en-tête de 8 octets, et le conteneur RIFF référence directement
une table d'index pointant vers chaque frame.

Le script fonctionne en trois étapes séquentielles, chacune produisant un
fichier intermédiaire :

1. **`convertFileToOpus()`** — encodage du fichier source en `.opus` (conteneur Ogg) via ffmpeg.
2. **`rewriteFile()`** — extraction des frames Opus brutes depuis les pages Ogg, et ajout d'un en-tête de 8 octets par frame.
3. **`addHeader()`** — construction de l'en-tête RIFF/WEM final et assemblage du fichier `.wem` complet.

Les fichiers intermédiaires (`.opus` et `(cleaned)`) sont supprimés automatiquement en fin de traitement ; seul le `.wem` final est conservé.

---

## Prérequis et dépendances

- **ffmpeg.exe**, attendu dans `../Dependencies/ffmpeg.exe` relativement au script.
- **Opus.dll** (et bibliothèques associées), attendue dans `../Dependencies/`.
- Le module Python **`opuslib`**, utilisé pour décoder chaque frame Opus et en extraire un *checksum* (voir plus bas).

Je ne peux pas confirmer la version exacte de `opuslib` ni de `ffmpeg` attendue par le script : ces informations ne figurent pas dans le code et je ne les invente pas.

---

## Étape 1 — `convertFileToOpus()`

Encode le fichier source en Opus via ffmpeg, avec la commande suivante :

```
ffmpeg -i <entrée>
  -map 0:a -map -0:v
  -map_metadata -1 -map_metadata:s:a:0 -1
  -c:a libopus -ar 48000 -ac 2 -b:a 192k
  -vbr off -frame_duration 20 -application lowdelay
  -fflags +bitexact -write_xing 0
  -f ogg "<stem> (ffmpeg).opus"
```

Points clés :
- **`-vbr off`** : débit constant, nécessaire pour obtenir des frames de taille constante.
- **`-frame_duration 20`** associé à `-ar 48000` donne des frames de **960 échantillons** (20 ms à 48 kHz), cohérent avec la valeur `C0 03` (960 en little-endian) inscrite plus tard dans l'en-tête WEM.
- **`-map_metadata -1`** sert à supprimer un maximum de métadonnées.
- **`-fflags +bitexact`** et **`-write_xing 0`** limitent les variations binaires non essentielles (identifiants d'encodeur, page Xiph `OggS` de résumé, etc.).

Le fichier produit est nommé `<nom_original> (ffmpeg).opus` et stocké dans la même variable globale `filePathConverted`.

---

## Étape 2 — `rewriteFile()`

Cette fonction parcourt le fichier Ogg/Opus produit par ffmpeg, **retire l'encapsulation Ogg** (pages, en-têtes `OggS`, CRC de page, etc.) et ne conserve que les frames Opus brutes, chacune précédée d'un en-tête.

### Lecture des pages Ogg

Le parcours du fichier Ogg repose sur la structure fixe d'une page Ogg :

- `posCursor = 121` : position de départ, qui saute l'en-tête de fichier et les deux premières pages Ogg (en-têtes OpusHead et OpusTags) pour atteindre la première page de données audio.
- `posCursor += 26` : skip les premiers octets de la page opus, il n'y a pas de données utiles pour nous.
- `skipLength = ...read(1)` : lit cet octet et indique combien il y a d'octets dans la table d'index de la page Opus.
- `frameNumberTotal += skipLength // 2` : La taille de 1 frame est indiqué en 2 octets dans la table d'index de la page opus, donc si on divise par deux la taille de la table d'index on trouve logiquement le nombre de frames (tout le temps 50 sauf à la dernière page ou il y a 1 à 49 frames)
- `posCursor += skipLength + 1` : saute la table d'index (de taille `skipLength`) plus l'octet actuel lui-même, pour atteindre le début des données audio de la page.

### Extraction des frames et en-tête XB1

Pour chaque frame de la page (`frameNumberPage` frames, chacune de **480 octets**) :

1. Lecture de 480 octets de données Opus brutes.
2. Écriture de 4 octets fixes `00 00 01 E0` (en-tête constant).
3. Écriture de 4 octets de *checksum*, calculés par `calculateFrameChecksum()`.
4. Écriture des 480 octets de la frame elle-même.

Chaque frame occupe donc **8 + 480 = 488 octets** dans le fichier `(cleaned)`, valeur que l'on retrouve dans `addHeader()`.

### `calculateFrameChecksum(frame)`

```python
varDecoder = decoder.create_state(48000, 2)
decoder.decode(varDecoder, frame, len(frame), 960, False)
frameChecksum = decoder.decoder_ctl(varDecoder, ctl.get_final_range)
```

Le script instancie un décodeur Opus (48 kHz, stéréo), décode la frame pour forcer le calcul interne du *range coder*, puis lit le **`final_range`** du décodeur via l'appel de contrôle `OPUS_GET_FINAL_RANGE`. Cette valeur sert de "checksum" par frame dans le format XB1-WEM — c'est une valeur de contrôle interne au codec Opus, pas un CRC classique. Elle est convertie en 4 octets big-endian.

Résultat : le fichier `(cleaned)` contient uniquement une suite de blocs `[4 octets constants][4 octets checksum][480 octets de frame]`, sans plus aucune trace de la structure Ogg.

---

## Étape 3 — `addHeader()`

Construit l'en-tête RIFF/WAVE/WEM final à partir du nombre total de frames (`frameNumberTotal`) calculé à l'étape précédente, puis y ajoute le contenu du fichier `(cleaned)`.

### Structure de l'en-tête écrit (68 octets avant la table d'index)

| Offset | Taille | Contenu                      | Signification |
|--------|-------:|-------------------------------|----------------|
| 0x00   | 4      | `RIFF`                        | Identifiant du conteneur |
| 0x04   | 4      | taille totale − 8 (little-endian) | Taille du fichier après ce champ |
| 0x08   | 4      | `WAVE`                         | Type de conteneur |
| 0x0C   | 4      | `fmt `                         | Début du bloc format |
| 0x10   | 4      | `28 00 00 00` (= 40)            | Taille du bloc `fmt` |
| 0x14   | 2      | `39 30`                         | Codec Wwise Opus (identifiant propriétaire) |
| 0x16   | 2      | `02 00`                         | Nombre de canaux (stéréo) |
| 0x18   | 4      | `80 BB 00 00` (= 48000)          | Fréquence d'échantillonnage |
| 0x1C   | 4      | `00 EE 02 00` (= 192000)         | Débit déclaré (octets/s) |
| 0x20   | 2      | `04 00`                         | `block_align` (constante) |
| 0x22   | 2      | `10 00`                         | Bits/échantillon déclarés (constante) |
| 0x24   | 2      | `06 00`                         | Taille des données supplémentaires |
| 0x26   | 2      | `C0 03` (= 960)                  | Échantillons par frame |
| 0x28   | 4      | `02 31 00 00`                    | Paramètre Wwise/Opus (valeur fixe, rôle exact non élucidé) |
| 0x2C   | 8      | `(frameNumberTotal − 1) × 960`   | Nombre total d'échantillons |
| 0x34   | 4      | `frameNumberTotal × 488`         | Taille du flux audio encodé (payload) |
| 0x38   | 4      | `frameNumberTotal × 4`           | Taille de la table d'index |
| 0x3C   | 4      | `data`                           | Début du chunk de données |
| 0x40   | 4      | taille table + taille payload   | Taille totale après ce champ |
| 0x44   | 4 × n  | table d'index                   | Offset de chaque frame dans le payload |
| ...    | —      | payload                         | Frames (en-tête 8 octets + 480 octets de données), issues du fichier `(cleaned)` |

Remarques :
- **`frameNumberTotal × 488`** : chaque frame complète (en-tête de 8 octets inclus) fait 488 octets.
- **Nombre d'échantillons = `(frameNumberTotal − 1) × 960`** : même si la première (ou la dernière) frame existe techniquement, le fichier en déclare toujours une de moins.
- **Table d'index** : chaque entrée est un offset de 4 octets, en pas constants de 488 (puisque toutes les frames font la même taille), du début du payload (0) jusqu'à `488 × (frameNumberTotal − 1)`.
- Le bloc `04 00 10 00 06 00` (offsets 0x20–0x25) est constant mais son rôle est inconnu.

Le fichier final est nommé `<nom_original>.wem` et écrit dans le même dossier que le fichier source.

---

## Déroulement global (`__main__`)

```python
userInput = input("Filepath to convert : ")
userInput = userInput.strip('"')
filePathOriginal = Path(userInput)

convertFileToOpus()   # étape 1 : .wav -> .opus (ffmpeg)
rewriteFile()         # étape 2 : .opus -> (cleaned) (frames + en-têtes XB1)
os.remove(filePathConverted)
addHeader()            # étape 3 : (cleaned) -> .wem (en-tête RIFF final)
os.remove(filePathCleaned)
print("Done ! The result file is '", filePathFinished, "'.")
```

Le script :
1. Demande interactivement le chemin du fichier à convertir (les guillemets copiés-collés depuis l'explorateur Windows sont retirés).
2. Encode ce fichier en Opus.
3. Extrait les frames et calcule leur checksum, en supprimant la structure Ogg.
4. Supprime le fichier `.opus` intermédiaire.
5. Construit l'en-tête WEM final à partir des frames extraites.
6. Supprime le fichier `(cleaned)` intermédiaire.
7. Affiche le chemin du fichier `.wem` final.

Cette documentation a été organisée et corrigée par IA.
L'utilisation de l'IA dans le script a été utilisée uniquement pour expliquer/détailler des fonctions.