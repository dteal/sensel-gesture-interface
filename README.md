# SenselGestureKeyboard
An application that uses the Sensel Morph platform as a keyboard (and mouse) by mapping gestures to words.

Like a swiping keyboard - but no absolute key locations. Plus a trackpad and shortcut buttons, just for grins.

So you have this Sensel Morph- an amazingly well-built and functional piece of hardware that's pretty much the best gigantic digital touchpad ever invented. We thought, well, iOS and Android have the Swype app - a keyboard that allows one to type a word by moving a finger along the path through the letters - so why not this?

So we devised an algorithm to take a sequence of vectors (a finger swiped around the Sensel) and find the word whose letters are closest along that trajectory. We compute a vector of constant length and store the angle at constant distances around the gesture, creating a representation completely free of both x/y position and scale. This is compared to a precompiled database of the most common English words.

We also threw in a touchpad, just for fun. We 3D printed a custom overlay for the Sensel to divide the area into a keyboard area in which gestures are drawn, a touchpad, and a shortcut area. One can type words by forming gestures in the keyboard area, move the cursor via the trackpad (press to click), and open the default web browser or hit enter with a shortcut.

The list of words and frequencies used in this project was provided by <http://www.wordfrequency.info/top5000.asp>.
This project is built in Python with the Sensel API.

This project only works on Windows (due to keyboard emulation functions) under Python 2.7. Furthermore, Pygame, Numpy, and the Python for Win32 Extension are necessary.

Run this program by connecting a Sensel device and running "sensel_keyboard_emulator.py".
