On va d'abord check si le fichier est un vrai WAV
Si ce n'est pas le cas, alors on le convertit avec FFMPEG


Si c'est déjà un WAV, on peut passer à l'étape suivante directement

On prends le fichier WAV et on le passe dans nopus.exe
L'exécutable nous donnera un .nop / opus
nopus make_opus ".../input.wav" ".../output.opus"

Les .nop sont en VBR (Variant Bit Rate), donc les frames ne font pas la même taille

4 octets (big endian) sont utilisés pour indiquer la taille de la frame
4 octets (little endian) indiquent le checksum de la frame opus

Il faut modifier les quatres octets (de l'offset 0x1C à 0x1F) 38 01 00 00 -> 78 00 00 00, il s'agit du nombre de samples à skip

---------------------------------------------------------------------------------------------------------------------------------------
---------------------------------------------------------------------------------------------------------------------------------------
---------------------------------------------------------------------------------------------------------------------------------------

Cet algo servira à calculer la longueur des paquets opus

Le header a une longueur de 96 octets

Le padding fait 32 octets

La table d'index commence à l'offset 0x80
Pour calculer si la table d'index est valide, il faut diviser par 4 le nombre total d'octets
Cela donnera le nombre de frames
Ensuite il faut rediviser par 4 afin de savoir si le padding est correct
Donc si le nombre de frames n'a pas pour diviseur 4, il faudra lui ajouter (1 à 3) 'E8 E8 E8 E8'
(Il faut considérer que le dernier 'E8 E8 E8 E8' représente la fin de la table d'index)

Si % = 0.25 alors il faut ajouter 3 fois 'E8 E8 E8 E8'
Si % = 0.50 alors il faut ajouter 2 fois 'E8 E8 E8 E8'
Si % = 0.75 alors il faut ajouter 1 fois 'E8 E8 E8 E8'

Tout sera lu en Little Endian (donc les valeurs hexa sont lues en inversé) sauf exception
Ensuite le calcul sera Paire N+1 - Paire N = Longueur du paquet N

Les trames sont repérables grâce à leur entête qui est '00 00' ou '00 00 00'
Si un '00 00' se situe entre 2 '00 00' alors que la trame précédente n'est pas finie
alors considérer que c'est une erreur et passer à la suite

On va plutôt analyser frame par frame étant donné qu'elles se suivent.
La première frame est connue et invariable


# Values check 
"""
sadf = getVarHeader(0x0)
totalSize = getVarHeader(0x4)
opus = getVarHeader(0x8)
fourth = getVarHeader(0xc)

head = getVarHeader(0x10)
indexPosition1 = getVarHeader(0x14)
channelCount = getVarHeader(0x18)
opusStream = getVarHeader(0x1c)

opusLength1 = getVarHeader(0x20)
sampleRate = getVarHeader(0x24)
sampleNumber1 = getVarHeader(0x28)
#

sampleNumber2 = getVarHeader(0x30)
opusLength2 = getVarHeader(0x34)
#
#

#
forthFourth = getVarHeader(0x44)
#
frameNumber1 = getVarHeader(0x4c)

frameNumber2 = getVarHeader(0x50)
indexPosition2 = getVarHeader(0x54)
indexLength = getVarHeader(0x58)
#

headerPadding = getVarHeader(0x60, 32)
"""
