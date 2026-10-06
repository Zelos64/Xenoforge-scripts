import os
import shutil
from pathlib import Path

def checkFile(pathOutput):
    extensionFile = Path(filePath).suffix
    extensionFile = extensionFile.lower()
    if(extensionFile != ".opus"):
        pathOutput.close
        print(filePath + " is not a .OPUS file")
        return False

    pathOutput.seek(0)
    condition = pathOutput.read(4)
    if(condition == b'\x01\x00\x00\x80'):
        pathOutput.close
        print(filePath + " is already formated")
        return False

    pathOutput.seek(0)
    condition = pathOutput.read(4)
    if(condition != b'\x73\x61\x64\x66'):
        pathOutput.close
        print(filePath + " is not a true Nintendo Opus file")
        return False

    return True

def modifyFile(pathOutput):
    # SAVE
    nopHeader = bytes(0x80)
    opusHeaderA = "01 00 00 80 18 00 00 00 00"
    opusHeaderA = bytes.fromhex(opusHeaderA)
    opusHeaderB = "00 00 80 BB 00 00 20 00 00 00 00 00 00 00 00 00 00 00 78 00 00 00 04 00 00 80"
    opusHeaderB = bytes.fromhex(opusHeaderB)
    pathOutput.seek(0x9)
    channelCount = pathOutput.read(1)
    pathOutput.seek(0x24)
    opusStream = pathOutput.read()
    pathOutput.seek(0)

    # FILL
    pathOutput.write(nopHeader + opusHeaderA + channelCount + opusHeaderB + opusStream)
    pathOutput.close

    def getVar(offset, size = 4):
        hex(offset)
        pathOutput.seek(offset)
        data = pathOutput.read(size)
        return data

    indexNOP = bytearray()
    indexNOP = (b'\x28\x00\x00\x00')

    def bytesForIndex(a, b):
        a = int.from_bytes(a, "little")
        b = int.from_bytes(b, "big") + 8
        # "+ 8" Because the frame's length doesn't count itself and the next 4 bytes so it's not fully representative of opus frame
        result = a + b
        result = result.to_bytes(4, "little")
        return result

    indexOffset = 0x80
    def saveBefore():
        pathOutput.seek(0)
        before = pathOutput.read(indexOffset)
        return before
    def saveAfter():
        pathOutput.seek(indexOffset)
        after = pathOutput.read()
        return after
    pathOutput.seek(0)

    opusLength = int.from_bytes(getVar(0xA4), "little")
    opusCheck = 0
    cursor = 0xA8
    a = 0
    b = 4
    frameNumber = 0
    while(opusLength >= opusCheck):
        # print(opusCheck, "<", opusLength)
        currentFrameLength = getVar(cursor)
        if(currentFrameLength == b'\x00\x00\x00\x00'):
            break
        frameNumber += 1
        indexNOP = indexNOP + bytesForIndex(indexNOP[a : b], currentFrameLength)
        a += 4
        b += 4
        currentFrameLength = int.from_bytes(currentFrameLength)
        cursor += currentFrameLength + 8
        opusCheck += currentFrameLength + 8

    indexNOPlength = len(indexNOP)
    modulo = indexNOPlength/4/4%1
    addIndexPadding = 0
    if(modulo != 0):
        if(modulo == 0.75):
            addIndexPadding = 1
        if(modulo == 0.5):
            addIndexPadding = 2
        if(modulo == 0.25):
            addIndexPadding = 3
        for i in range(addIndexPadding):
            indexNOP += b'\xE8\xE8\xE8\xE8'
        indexNOPlength = len(indexNOP)
    else:
        addIndexPadding = 0

    pathOutput.seek(indexOffset)
    indexBefore = saveBefore()
    indexAfter = saveAfter()
    pathOutput = open(filePath, "w+b")
    pathOutput.write(indexBefore + indexNOP + indexAfter)
    pathOutput.close

    pathOutput = open(filePath, "r+b")
    cursor = 0
    def jump():
        global cursor
        cursor = pathOutput.tell()
        cursor += 4
        pathOutput.seek(cursor)

    # Get informations
    fileLength = len(pathOutput.read()).to_bytes(4, "little")
    opusStart = (indexNOPlength + 128).to_bytes(4, "little")
    indexNOPlength = indexNOPlength.to_bytes(4, "little")
    opusLength = (opusLength + 40).to_bytes(4, "little")
    samplesNumber = (frameNumber * 960).to_bytes(4, "little")
    frameNumber = (frameNumber).to_bytes(4, "little")
    channelCount += b'\x00\x00\x00'

    # Set informations to NOP header
    pathOutput.seek(cursor)
    pathOutput.write(b'\x73\x61\x64\x66')
    pathOutput.write(fileLength)
    pathOutput.write(b'\x6F\x70\x75\x73')
    pathOutput.write(b'\x01\x00\x00\x00')
    pathOutput.write(b'\x68\x65\x61\x64')
    pathOutput.write(b'\x80\x00\x00\x00')
    pathOutput.write(channelCount)
    pathOutput.write(opusStart)
    pathOutput.write(opusLength)
    pathOutput.write(b'\x80\xBB\x00\x00')
    pathOutput.write(samplesNumber)
    jump() # null
    pathOutput.write(samplesNumber)
    pathOutput.write(opusLength)
    jump() # null
    jump() # null
    jump() # idk
    pathOutput.write(b'\x20\x4E\x00\x00')
    jump()
    pathOutput.write(frameNumber)
    pathOutput.write(frameNumber)
    pathOutput.write(b'\x80\x00\x00\x00')
    pathOutput.write(indexNOPlength)
    jump() # null

    print("Done")
    input()

def deleteHeader(filePath):
    pathOutput = open(filePath, "rb")
    pathOutput.seek(28)
    opusPosition = pathOutput.read(4)
    print(opusPosition)
    opusPosition = int.from_bytes(opusPosition, "little")
    print(opusPosition)
    pathOutput.seek(opusPosition)
    save = pathOutput.read()

    pathOutput = open(filePath, "wb")
    pathOutput.write(save)
    print("Header deleted")

folderPath = input("folder : ")
for file in os.listdir(folderPath):
    filePath = os.path.join(folderPath, file)
    if os.path.isfile(filePath):
        pathOutput = open(filePath, "r+b")
        if not checkFile(pathOutput):
            pathOutput.close()
            continue
        deleteHeader(filePath)
        pathOutput.close()

