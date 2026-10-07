import os
import subprocess
from pathlib import Path

parentFolder = os.path.basename(os.path.dirname(__file__))
if parentFolder != "Xenoforge-scripts":
    print("Warning")
    print(f"The current scripts is in a folder named '{parentFolder}' and not in 'Xenoforge-scripts'")
    print("Rename the parent folder or move the script to a folder named 'Xenoforge-scripts'")
    input("Press enter to exit")
    quit()

script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Load dependencies folder
dependenciesFolder = os.path.join(script_dir, "Xenoforge-dependencies")
if not os.path.exists(dependenciesFolder):
    print("The folder 'Xenoforge-dependencies' is missing")
    print("Download it from https://github.com/Zelos64/Xenoforge-dependencies")
    print("The folder must be in the same directory as 'Xenoforge-scripts' like this : ")
    print(rf"  - {os.path.dirname(__file__)}")
    print(rf"  - {dependenciesFolder}")
    input("Press enter to exit")
    quit()

# Load ffmpeg.exe
ffmpegLocation = os.path.join(dependenciesFolder, "ffmpeg.exe")
if not os.path.exists(ffmpegLocation):
    print("FFMPEG.exe is missing")
    print("Please read the README.md file")
    input("Press enter to open the README and exit this program")
    os.startfile(os.path.join(dependenciesFolder, "README.md"))
    quit()

# Load nopus.exe
nopusLocation = os.path.join(dependenciesFolder, "nopus.exe")

def convertFileToWav():
    global filePathOriginal
    global filePathWav
    filePathWav = filePathOriginal.with_name(filePathOriginal.stem + ".wav")

    command = [
    ffmpegLocation,
    "-i", filePathOriginal,
    "-ar", "48000",
    "-ac", "2",
    filePathWav,
    ]

    subprocess.run(command, check=True)

def convertWavToOpus():
    global filePathWav
    global filePathOpus
    filePathOpus = filePathOriginal.with_name(filePathOriginal.stem + ".opus")

    command = [
    nopusLocation,
    "make_opus",
    filePathWav,
    filePathOpus,
    ]

    subprocess.run(command, check=True)

    if filePathOriginal.suffix != ".wav":
        os.remove(filePathWav)

def generateIndexTable():
    global filePathOpus
    global filePathIndex
    global indexTableLength
    filePathOpusOpen = filePathOpus.open("r+b")
    filePathIndex = filePathOpus.with_name(filePathOpus.stem + " (index).nop")
    filePathIndexOpen = filePathIndex.open("w+b")

    global frameNumber
    global frameLength
    pos = 40
    filePathIndexOpen.write(bytes.fromhex('28 00 00 00'))
    while True:
        filePathOpusOpen.seek(pos)
        currentLength = int.from_bytes(filePathOpusOpen.read(4), "big")

        if currentLength == 0:
            break
        else:
            frameNumber += 1
            pos = pos + (currentLength + 8)

        filePathIndexOpen.write(pos.to_bytes(4, "little"))
    frameLength = pos

    paddingCheck = (frameNumber + 1) % 4
    if paddingCheck > 0 and paddingCheck < 4:
        paddingCheck = 4 - paddingCheck
    for i in range(paddingCheck):
        filePathIndexOpen.write(bytes.fromhex('E8 E8 E8 E8'))

    indexTableLength = filePathIndexOpen.tell()

    filePathOpusOpen.close()
    filePathIndexOpen.close()

def assembleNop():
    global frameNumber
    global frameLength
    filePadding = 0
    sampleNumber = frameNumber * 960
    global indexTableLength
    global filePathOriginal
    global filePathWav
    global filePathOpus
    global filePathFinished

    filePathOpusOpen     = filePathOpus.open("r+b")
    filePathOpusOpen.seek(0)
    opusSave = filePathOpusOpen.read()

    filePathIndexOpen = filePathIndex.open("r+b")
    indexSave = filePathIndexOpen.read()

    filePathFinished     = filePathOriginal.with_name(filePathOriginal.stem + ".nop")
    filePathFinishedOpen = filePathFinished.open("w+b")

    # Nop header
    filePathFinishedOpen.write(bytes.fromhex('73 61 64 66')) # sadf

    fileSize = 128 + indexTableLength + frameLength # File header + index table + payload
    filePadding = fileSize % 16
    if filePadding > 0 and filePadding < 16:
        fileSize += 16 - filePadding
    filePathFinishedOpen.write(fileSize.to_bytes(4, "little")) # File size

    filePathFinishedOpen.write(bytes.fromhex('6F 70 75 73')) # opus
    filePathFinishedOpen.write(bytes.fromhex('01 00 00 00')) # 1
    filePathFinishedOpen.write(bytes.fromhex('68 65 61 64')) # head
    filePathFinishedOpen.write(bytes.fromhex('80 00 00 00')) # index table position
    filePathFinishedOpen.write(bytes.fromhex('02 00 00 00')) # channel count 1 or 2

    opusStartPosition = 128 + indexTableLength
    # opusStartPosition = opusStartPosition.to_bytes(4, "little")
    filePathFinishedOpen.write(opusStartPosition.to_bytes(4, "little")) # Opus start position (hex)

    filePathFinishedOpen.write(frameLength.to_bytes(4, "little")) # Opus frames length
    filePathFinishedOpen.write(bytes.fromhex('80 BB 00 00')) # 48 000 : sample rate
    filePathFinishedOpen.write(sampleNumber.to_bytes(4, "little")) # Number of samples
    filePathFinishedOpen.write(bytes.fromhex('00 00 00 00')) # 0 ?
    filePathFinishedOpen.write(sampleNumber.to_bytes(4, "little")) # Number of samples (bis)
    filePathFinishedOpen.write(frameLength.to_bytes(4, "little")) # Opus frames length (bis)
    filePathFinishedOpen.write(bytes.fromhex('00 00 00 00')) # 0
    filePathFinishedOpen.write(bytes.fromhex('00 00 00 00')) # 0

    filePathFinishedOpen.write(bytes.fromhex('00 00 00 00')) # 0
    # filePathFinishedOpen.write(bytes.fromhex('?? ?? ?? ??')) # ???
                                              # 00 FA 00 00    = 64 000 = 68 000
                                              # 00 77 01 00	   = 96 000 = 99 000

    filePathFinishedOpen.write(bytes.fromhex('20 4E 00 00')) # 20 000 ?
    filePathFinishedOpen.write(bytes.fromhex('00 00 00 00')) # 0 ?
    filePathFinishedOpen.write(frameNumber.to_bytes(4, "little")) # number of frames
    filePathFinishedOpen.write(frameNumber.to_bytes(4, "little")) # number of frames (bis)
    filePathFinishedOpen.write(bytes.fromhex('80 00 00 00')) # index table position (bis)
    filePathFinishedOpen.write(indexTableLength.to_bytes(4, "little")) #  total length of the index table
    filePathFinishedOpen.write(bytes.fromhex('00 00 00 00')) # ?

    for i in range(32): filePathFinishedOpen.write(bytes.fromhex('00'))

    # Index table
    filePathFinishedOpen.write(indexSave)
    
    # Opus frames
    filePathFinishedOpen.write(opusSave)

    # File padding
    if filePadding > 0 and filePadding < 16:
        for i in range (16 - filePadding): filePathFinishedOpen.write(bytes.fromhex('00'))

    filePathOpusOpen.close()
    filePathFinishedOpen.close()

frameNumber = 0
frameLength = 0
indexTableLength = 0

filePathOriginal = Path()
filePathWav      = Path()
filePathOpus     = Path()
filePathIndex    = Path()
filePathFinished = Path()

userInput = input("Filepath to convert : ")
userInput = userInput.strip('"')
if os.path.exists(userInput):
    filePathOriginal = Path(userInput)
else:
    print("This file doesn't exist")
    input("Press enter to exit")
    quit()

if filePathOriginal.suffix == ".wav":
    filePathWav = filePathOriginal
    convertWavToOpus()
else:
    convertFileToWav()
    convertWavToOpus()

generateIndexTable()

assembleNop()
os.remove(filePathOpus)
os.remove(filePathIndex)