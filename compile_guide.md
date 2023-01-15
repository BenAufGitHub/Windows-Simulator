# Compiling the program to an runnable exe-application


## Copmpiling the python program

If no modifications to the given python library is made, skip this step.

1. Install pyinstaller

    pip installer pyinstaller

2. Compile the app

    pyinstaller --onefile '.\programs\capturer\src\py_communicator.py'

3. A build folder with the file 'py_communicator.exe' should appear.
Head to the build branch of this application and swap the file '.\programs\py_communicator.exe' with your own.


## Setting up the final steps

1. Move to the 'build' branch
2. If you want to add/change files within the electron process, you can now do so without any setups.

3. Integrate all contents of 'package.help.json' to your' package.json. (Don't delete dependencies from your 'package.json' tho)
4. For any files added to the pyBridge process, those must be listed under 'extraFiles' in your 'package.json'.


## Compile

1. Install electron-builder

    npm install electron-builder

2. Compile

    npm run dist

A dist folder should appear, which is the installer folder.


## Install to user/pc

Run the  file 'WinSimulator Setup 1.0.0.exe' to install it to the user or whole pc and get a desktop icon.
