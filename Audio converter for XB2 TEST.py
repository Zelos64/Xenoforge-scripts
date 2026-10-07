import os
import subprocess
from pathlib import Path

script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load dependencies folder
dependenciesFolder = os.path.join(script_dir, "Xenoforge-dependencies")
if not os.path.exists(dependenciesFolder):
    print("The folder 'Xenoforge-dependencies' is missing")
    print("Download it from https://github.com/Zelos64/Xenoforge-dependencies")
    print("The folder must be in the same directory as Xenoforge-scripts like this : ")
    print(rf"  - {script_dir}\Xenoforge-scripts")
    print(rf"  - {script_dir}\Xenoforge-dependencies")
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

# Load nopus.exe
nopusLocation = os.path.join(dependenciesFolder, "nopus.exe")

def convertFileToWAV():
    global filePathOriginal
    global filePathWAV
    inputFile = filePathOriginal
    outputFile = filePathOriginal.with_name(filePathOriginal.stem + ".wav")
    filePathWAV = outputFile

    command = [
    ffmpegLocation,
    "-i", inputFile,
    "-ar", "48000",
    "-ac", "2",
    outputFile,
    ]

    subprocess.run(command, check=True)

def convertWAVtoOPUS():
    global filePathOriginal
    global filePathConverted
    inputFile = filePathOriginal
    outputFile = filePathOriginal.with_name(filePathOriginal.stem + " (ffmpeg).opus")
    filePathConverted = outputFile

    command = [
    nopusLocation,
    "make_opus",
    inputFile,
    outputFile,
    ]

    subprocess.run(command, check=True)

def calculateFrameChecksum(frame):
    varDecoder = decoder.create_state(48000, 2)
    decoder.decode(varDecoder, frame, len(frame), 960, False)
    frameChecksum = decoder.decoder_ctl(varDecoder, ctl.get_final_range)
    frameChecksum = frameChecksum.to_bytes(4, byteorder="big")
    return frameChecksum

def readFrameLength():
    print("")

def getFrameNumberAndLength():
    pos = 40
    while True:
        global frameNumber
        global frameLength
        global filePathOPUS
        filePathOPUSopen = filePathOPUS.open("r+b")
        filePathOPUSopen.seek(pos)
    
        data = int.from_bytes(filePathOPUSopen.read(4))

        if data == 0:
            break
        else:
            frameNumber += 1
            pos = pos + (data + 8)
    frameLength = pos
        

def addHeader():
    global frameNumber
    global frameLength
    sampleNumber = frameNumber * 960
    indexTableLength = frameNumber * 4
    global filePathOriginal
    global filePathWAV
    global filePathOPUS
    global filePathFinished

    filePathFinished     = filePathOriginal.with_name(filePathOriginal.stem + ".nop")
    filePathFinishedOpen = filePathFinished.open("w+b")
    filePathOPUSOpen     = filePathOPUS.open("r+b")
    filePathOPUSOpen.seek(0)
    save = filePathOPUSOpen.read()

    # NOP header
    filePathFinishedOpen.write(bytes.fromhex('73 61 64 66')) # sadf

    fileSize = 80 + 4 + indexTableLength + frameLength # File header + index table + payload
    fileSize = fileSize.to_bytes(4, "little")
    print("fileSize : ", fileSize)
    filePathFinishedOpen.write(fileSize) # File size

    filePathFinishedOpen.write(bytes.fromhex('6F 70 75 73')) # opus
    filePathFinishedOpen.write(bytes.fromhex('01 00 00 00')) # 1
    filePathFinishedOpen.write(bytes.fromhex('68 65 61 64')) # head
    filePathFinishedOpen.write(bytes.fromhex('80 00 00 00')) # seek table position
    filePathFinishedOpen.write(bytes.fromhex('02 00 00 00')) # channel count 1 or 2

    opusStartPosition = 80 + 4 + indexTableLength
    opusStartPosition = opusStartPosition.to_bytes(4, "little")
    filePathFinishedOpen.write(bytes.fromhex(opusStartPosition)) # Opus start position

    filePathFinishedOpen.write(bytes.fromhex(frameLength.to_bytes(4, "little"))) # Opus frames length

    filePathFinishedOpen.write(bytes.fromhex('80 BB 00 00')) # 48 000 : sample rate

    filePathFinishedOpen.write(bytes.fromhex(sampleNumber.to_bytes(4, "little"))) # Number of samples
    
    filePathFinishedOpen.write(bytes.fromhex('00 00 00 00')) # 0 ?
    
    filePathFinishedOpen.write(bytes.fromhex(sampleNumber.to_bytes(4, "little"))) # Number of samples (bis)

    filePathFinishedOpen.write(bytes.fromhex(frameLength.to_bytes(4, "little"))) # Opus frames length (bis)

    filePathFinishedOpen.write(bytes.fromhex('00 00 00 00')) # 0
    filePathFinishedOpen.write(bytes.fromhex('00 00 00 00')) # 0

    # filePathFinishedOpen.write(bytes.fromhex('?? ?? ?? ??')) # ???
                                              # 00 FA 00 00    = 64 000 = 68 000
                                              # 00 77 01 00	   = 96 000 = 99 000


    filePathFinishedOpen.write(bytes.fromhex('20 4E 00 00')) # 20 000 ?

    filePathFinishedOpen.write(bytes.fromhex('00 00 00 00')) # 0 ?

    filePathFinishedOpen.write(bytes.fromhex(frameNumber.to_bytes(4, "little"))) # number of frames (without the first and last word of seek table so it’s X-2)

    filePathFinishedOpen.write(bytes.fromhex(frameNumber.to_bytes(4, "little"))) # number of frames (bis)

    filePathFinishedOpen.write(bytes.fromhex('80 00 00 00')) # seek table position (bis)

    filePathFinishedOpen.write(bytes.fromhex(indexTableLength.to_bytes(4, "little"))) #  total length of the index table

    filePathFinishedOpen.write(bytes.fromhex('00 00 00 00')) # ?

    for i in range(32): filePathFinishedOpen.write(bytes.fromhex('00'))

    # Index table
    filePathFinishedOpen.write(bytes.fromhex('28 00 00 00')) # 28 : length of the opus header

    pos = 40
    while True:
        global frameNumber
        global frameLength
        filePathOPUSOpen.seek(pos)

        value = filePathOPUSOpen.read(4)
        length = int.from_bytes(value) + 8
        length = length.to_bytes(4, "little")
        filePathFinishedOpen.write(length) # current frame total length
        
        value = int.from_bytes(value)
        
        if value == 0:
            break
        else:
            pos = pos + (value + 8)

    # Opus frames
    filePathFinishedOpen.write(save)

    filePathOPUSOpen.close()
    filePathFinishedOpen.close()

frameNumber = 0
frameLength = 0

filePathOriginal = Path()
filePathWAV      = Path()
filePathOPUS     = Path()
filePathFinished = Path()

frame = b'\xF8\x7E\x7D\x16\xE5\x85\xCA\xE7\x21\x15\x8E\xF6\xC7\xEE\xFF\xD4\xD2\x02\x94\xB4\xD8\x74\x99\x79\x56\xCA\x12\xCB\x54\x8B\x56\x6A\x1F\xEB\xA5\x27\xCF\xF3\x3B\xAC\xAA\xA9\x27\xF7\xD5\xA3\xC8\xBF\xDE\xBB\x2B\x5F\xCB\x9A\xF0\x10\x75\x66\xDC\x5D\x4E\x84\xBD\x86\x3C\x46\x70\x97\xD4\xB0\xD4\xBE\x65\x2C\x72\x01\x09\xD8\xE0\x06\xFB\x54\xB4\x52\x1E\x61\x6D\x30\x90\x07\xF9\x31\x41\x92\x16\x18\x6A\x36\xE1\x77\x2A\x71\x93\xDE\x5F\xB0\x36\x7B\x32\xDB\x57\x4B\x41\x98\x5B\x80\xFC\xF4\x4B\x46\x90\x28\x4D\x64\xC7\x3F\x81\x45\x44\xAF\xD7\xD1\x98\xE7\x66\x48\xD4\x6E\x35\x18\xA1\xD6\x1D\x72\x6B\xE7\x5C\x6D\xFE\xDC\xB2\x40\x79\x7C\x1C\x5E\x5A\x18\x2D\xEC\x69\x3B\x49\x9D\x79\xB3\xC6\xD6\xEE\x71\xA5\xEC\x7B\xC2\x32\xF4\x5A\x19\xB8\xA9\x24\x7E\x39\x08\x1A\x7E\xDE\x47\x58\x1B\x7D\x7F\x2E\x69\x4B\x79\x50\xA7\x86\x3B\xF1\x02\xD2\xA4\x22\x56\x45\x52\xC6\x84\x78\x93\xB1\xFA\x9D\x44\xE8\xE6\x0D\x58\x7A\x0F\xEF\xF1\xBA\x4F\x5D\x49\xB8\xE4\x96\xDE\x84'
print(frame)
result = calculateFrameChecksum(frame)
result = result.hex(" ")
print(result)