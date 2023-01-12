# The WinRecreator (for Microsoft Windows)

    Original German Name: WinSimulationen (für Microsoft Windows)
    Author: Ben Mette
    E-Mail: bmette.api@gmail.com
    Version: 1.0.0

    Compatability: Microsoft Windows 10+11 (below might work, have not tried tho)
    Function: Recording and simulating desktop and applications.
    Feature: Makes sure conditions of simulation are met and guides user through the process.


## HOW TO: A guide to the UI

After the first initialization, you find yourself on the home screen (index.html).
Before using, please read the short users-manual on the info-page.

To get started:

    Make a name for your savefile
    Press Record, do some stuff
    To get back, press 'f2' (never the icon in the taskbar please :>)
    Then, select the simulation and let it play out.
    ...you can also interrupt your simulation by pressing 'f2'...

In the settings you may...

    ...choose your language
    ...toggle whether you want windows to be controlled and adjusted before simulation (recommended)
    ...toggle whether the app can take screenshots of programs while running (helps user identifying them later)
    ...delete cache files
    ...delete all recordings

To see which windows are pressed and needed for the simulation, click details on the simulation's cogwheel.


## Run it yourself

### Setup

1. get repository onto your local machine
2. execute 'npm init'
3. execute 'npm install --save-dev electron'
4. execute 'npm install ini'
5. in your package.json, configure the following:

    "main": "src/main.js",
    "scripts": {
    "start": "electron ."
    }

6. now use 'npm start' to run

### pip modules (python)

    pip install pywinatuto
    pip install pynput
    pip install pyWin32


## Additional information

1. Want to compile it yourself? Try 'compile_guide.md' for help.
2. Third-Party licenses can be found in 'license_notice.md'.


## How the app functions

There are 3 (technically 4) processes running from this app.

At first we have the python process. It handles of the controlling and capturing, and also the flow of the sessions.

Then there are two electron processes, one being the root, the main process, the other being the renderer process, which includes
the front-end code. The main process has controll over the renderer process and holds the required information, like a website's
backend.

At last, technically also a process, is the middle-man between main and python: pyBridge.js.
It converts python and nodejs messages into one another and sorts out conflicting instructions.
As some requirements for the app have changed during the developement process, there is rewrite potential
as one could put pyBridge.js as an additional file into the main process, making the IPC less verbose.

The hierarchy looks like this:
    
    renderer <- ( main ) -> pyBridge -> python


### Communication between processes
Disclaimer: Very experimental, copying not recommended.

This is only informational, the libraries 'request_helper.py' and 'protocolConversion.js' do it automatically.

#### ID_NUMBER: 

<strong>0 Information</strong>
only from python to pyBridge, used to print to console

    "0 Hello this will print to console!"

<strong>1 Command</strong>
Doesn't return anything, synchronous

    main -> bridge
        "1 command | args"
    bridge -> main
        "1 one_word_command one_word_str_argument"

<strong>id > 1 Request</strong>
wait for return value, asynchrounous 

    main -> bridge -> python
        "id request | args"

requests are answered by sending same id:

    python -> bridge -> main
    failure: "same_id 1 failure_reason"
    success: "same_id 0 args_answer"

if main sends request-answers to renderer, it mostly follows this pattern

    object = {isSuccessful: boolean, id: number, answer: string}

#### args

    null/None : "n"
    integer: "i number"
    text: "t amount_chars text
    text array: at <amount_chars1> <text1><amount_chars2> <text2>...
    int array: ai num1, num2, num3, num4
