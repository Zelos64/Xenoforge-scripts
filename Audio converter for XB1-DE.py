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

# Load Opus.dll
dll_dir = os.path.normpath(dependenciesFolder)
os.add_dll_directory(dll_dir)
os.environ['PATH'] = dll_dir + os.pathsep + os.environ['PATH']

import opuslib.api.ctl as ctl
import opuslib.api.decoder as decoder

def convertFileToOpus():
    global filePathOriginal
    global filePathConverted
    filePathConverted = filePathOriginal.with_name(filePathOriginal.stem + " (ffmpeg).opus")

    command = [
    ffmpegLocation,
    "-i", filePathOriginal,
    "-map", "0:a",
    "-map", "-0:v",
    "-map_metadata", "-1",
    "-map_metadata:s:a:0", "-1",
    "-c:a", "libopus",
    "-ar", "48000",
    "-ac", "2",
    "-b:a", "192k",
    "-vbr", "off", 
    "-frame_duration", "20",
    "-application", "lowdelay",
    "-fflags", "+bitexact",
    "-write_xing", "0",
    "-f", "ogg",
    filePathConverted,
    ]

    subprocess.run(command, check=True)

def calculateFrameChecksum(frame):
    varDecoder = decoder.create_state(48000, 2)
    decoder.decode(varDecoder, frame, len(frame), 960, False)
    frameChecksum = decoder.decoder_ctl(varDecoder, ctl.get_final_range)
    frameChecksum = frameChecksum.to_bytes(4, byteorder="big")
    return frameChecksum

frameNumberTotal = 0
def rewriteFile():
    global frameNumberTotal
    global filePathOriginal
    global filePathConverted
    global filePathCleaned
    frameNumberTotal = 0

    filePathConvertedOpen = filePathConverted.open("r+b")
    filePathCleaned       = filePathConverted.with_name(filePathOriginal.stem + " (cleaned)" + filePathConverted.suffix)
    filePathCleanedOpen   = filePathCleaned.open("w+b")

    endFile = filePathConvertedOpen.seek(0, 2) # 2 = last offset
    posCursor = 121

    while posCursor < endFile:
        posCursor += 26
        filePathConvertedOpen.seek(posCursor)
        skipLength = int.from_bytes(filePathConvertedOpen.read(1))
        frameNumberTotal += skipLength // 2
        posCursor += skipLength + 1
        filePathConvertedOpen.seek(posCursor)

        frameNumberPage = skipLength // 2
        for i in range(frameNumberPage):
            frame = filePathConvertedOpen.read(480)
            posCursor += 480
            filePathCleanedOpen.write(bytes.fromhex('00 00 01 E0'))
            filePathCleanedOpen.write(calculateFrameChecksum(frame))
            filePathCleanedOpen.write(frame)
    filePathConvertedOpen.close()
    filePathCleanedOpen.close()

def addHeader():
    global frameNumberTotal
    global filePathOriginal
    global filePathConverted
    global filePathCleaned
    global filePathFinished

    filePathFinished     = filePathOriginal.with_name(filePathOriginal.stem + ".wem")
    filePathFinishedOpen = filePathFinished.open("w+b")
    filePathCleanedOpen  = filePathCleaned.open("r+b")
    filePathCleanedOpen.seek(0)
    save = filePathCleanedOpen.read()

    filePathFinishedOpen.write(bytes.fromhex('52 49 46 46')) # RIFF

    # Minus 8 because it consider the size only after his own offset
    fileSizeMinus8 = 68 + (frameNumberTotal * 4) + (frameNumberTotal * 488) - 8
        # File header + index table + payload
    fileSizeMinus8 = fileSizeMinus8.to_bytes(4, "little")
    print("fileSize - 8 : ", fileSizeMinus8)
    filePathFinishedOpen.write(fileSizeMinus8) # File size

    filePathFinishedOpen.write(bytes.fromhex('57 41 56 45')) # WAVE
    filePathFinishedOpen.write(bytes.fromhex('66 6D 74 20')) # fmt
    filePathFinishedOpen.write(bytes.fromhex('28 00 00 00')) # 'fmt' chunk size
    filePathFinishedOpen.write(bytes.fromhex('39 30 02 00')) # Codec + stereo
    filePathFinishedOpen.write(bytes.fromhex('80 BB 00 00')) # Hz
    filePathFinishedOpen.write(bytes.fromhex('00 EE 02 00')) # bitrate
    filePathFinishedOpen.write(bytes.fromhex('04 00 10 00 06 00')) # idk but it's constant
    filePathFinishedOpen.write(bytes.fromhex('C0 03'))       # Number of samples per frame
    filePathFinishedOpen.write(bytes.fromhex('02 31 00 00')) # Opus (unknown?) parameter

    sampleNumber = (frameNumberTotal - 1) * 960
    sampleNumber = sampleNumber.to_bytes(8, "little")
    print("sampleNumber : ", sampleNumber)
    filePathFinishedOpen.write(sampleNumber) # Number of samples
    # newFilePathOpen.write(bytes.fromhex('00 00 00 00')) # Padding or sample 2nd chunk ?

    payloadSize = frameNumberTotal * 488
    payloadSize = payloadSize.to_bytes(4, "little")
    print("payloadSize : ", payloadSize)
    filePathFinishedOpen.write(payloadSize) # Payload size

    indexTableSize = frameNumberTotal * 4
    indexTableSize = indexTableSize.to_bytes(4, "little")
    filePathFinishedOpen.write(indexTableSize) # Index table size

    filePathFinishedOpen.write(bytes.fromhex('64 61 74 61')) # data

    fileSizeAfter = int.from_bytes(indexTableSize, "little") + int.from_bytes(payloadSize, "little")
    fileSizeAfter = fileSizeAfter.to_bytes(4, "little")
    print("fileSizeAfter : ", fileSizeAfter)
    filePathFinishedOpen.write(fileSizeAfter) # File size after this offset

    # index table
    for i in range(frameNumberTotal):
        indexValue = 488 * i
        indexValue = indexValue.to_bytes(4, "little")
        filePathFinishedOpen.write(indexValue)

    filePathFinishedOpen.write(save)

    filePathCleanedOpen.close()
    filePathFinishedOpen.close()

filePathOriginal  = Path()
filePathConverted = Path()
filePathCleaned   = Path()
filePathFinished  = Path()

userInput = input("Filepath to convert : ")
userInput = userInput.strip('"')
if os.path.exists(userInput):
    filePathOriginal = Path(userInput)
else:
    print("This file doesn't exist")
    input("Press enter to exit")
    quit()

convertFileToOpus()
rewriteFile()
os.remove(filePathConverted)
addHeader()
os.remove(filePathCleaned)
print(f"Done ! The result file is '{filePathFinished}'.")