import os
from pathlib import Path
import subprocess
import sys

# vgmstream directory, the folder that contain the executable must be simply named "vgmstream"
script_dir = os.path.dirname(os.path.abspath(__file__))
executable_name = "vgmstream-cli.exe" if sys.platform == "win32" else "vgmstream-cli"
vgmstreamPath = os.path.join(script_dir, "vgmstream", executable_name)

# Little description
print("This is a Python script that do a bulk conversion .nop to .wav audio files")
print("It use vgmstream-cli to work")
print("Made by Zelos https://github.com/Geo6453/Xenoforge")
print("")

folderPath = input("Set the directory of the folder that contain the .nop : ").strip()
newFolderBase = input("Where did you want to store the result ? (The tree structure will be the same) : ").strip()

folderName = os.path.basename(os.path.normpath(folderPath))
newFolder = os.path.join(newFolderBase, f"{folderName} - converted")

if not os.path.exists(newFolder):
    os.makedirs(newFolder)

for root, dirs, files in os.walk(folderPath):
    for file in files:
        filePath = os.path.join(root, file)

        if file.lower().endswith(".nop"):
            relPath = os.path.relpath(root, folderPath)
            destFolder = os.path.join(newFolder, relPath)

            if not os.path.exists(destFolder):
                os.makedirs(destFolder)

            print(filePath)
            filePathWAV = Path(file).stem + ".wav"
            filePathWAV = os.path.join(destFolder, filePathWAV)

            subprocess.run([
                vgmstreamPath,
                "-o", filePathWAV,
                filePath
            ], check=True, stdout=subprocess.DEVNULL)

print("Finish.")