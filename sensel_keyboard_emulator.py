# ==============================================================================
# SENSEL MORPH GESTURE KEYBOARD
#
# Generates a word for each gesture following the line formed by letters of a
# desired word on a standard QWERTY keyboard.
# ==============================================================================

import sensel
import pygame
import string
import numpy as np
import math
import sys
import re
import webbrowser
import win32api # For mouse movement emulation
import win32con # For mouse button emulation
from win32con import * # For scroll wheel emulation
import win32com.client # For keypress emulation

# === Sensel Keyboard Emulator =================================================
# Uses the Sensel device to input words with a gesture-based interface
# ==============================================================================

class SenselKeyboardEmulator:

    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # INITIALIZATION ROUTINES
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    # --------------------------------------------------------------------------
    # Initilize class variables
    def __init__(self):

        # Define "magic number" parameters
        self.deadband = 10                # Minimum noticed gesture length (mm)
        self.vector_resolution = 20       # Segments in a comparison vector
        self.screen_size = (500, 500)     # Size of GUI
        self.use_gui = True               # Activate the GUI
        self.max_led_level = 100          # Value for full power Sensel LEDs
        self.use_optimized_layout = False # Use optimized keyboard layout
        self.num_options = 7              # Compute this many best words
        self.mouse_multiplier = 5.0
        self.backspace_min_dist = 20
        self.keyboard = (5, 151, 1, 118)
        self.trackpad = (161, 224, 1, 85)
        self.buttons = (161, 224, 92, 118)

        # Define more variables
        self.running = True               # Will flag the program to stop
        self.word_list = []               # List of known words & their vectors
        self.num_leds = 16                # Number of LEDs on the Sensel
        self.device_width = 1             # Initialize to non zero value
        self.device_height = 1            # Initialize to non zero value
        self.prev_word_len = 0

        # Initialize subcomponents
        if self.use_gui:
            self.init_gui()               # Start the GUI
        self.init_word_vectors()          # Generate the word list
        self.shell = win32com.client.Dispatch("WScript.Shell") # For keypress

    # --------------------------------------------------------------------------
    # Initialize the GUI
    def init_gui(self):
        pygame.init()
        self.screen = pygame.display.set_mode(self.screen_size)

    # --------------------------------------------------------------------------
    # Initialize the list of known words
    def init_word_vectors(self):

        # Calculate ideal letter coordinates
        letter_coords = {}
        for c in "abcdefghijklmnopqrstuvwxyz":
            letter_coords[c] = self.get_letter_coords(c)

        # Calculate comparison vector for all known words
        try:
            word_file = open('words.txt', 'r')
        except IOError:
            print("Error! Could not open known words file!")
            self.stop()
        word = re.sub(r'[^a-z]', '', word_file.readline().lower())
        i = 1
        while word:
            word_coords = []
            for c in word:
                word_coords.append(letter_coords[c])
            word_vector = self.process_word(word_coords)
            self.word_list.append((word_vector, word))
            word = re.sub(r'[^a-z]', '', word_file.readline().lower())
            i = i + 1
        word_file.close()

    # --------------------------------------------------------------------------
    # Define the coordinates of letters on a keyboard
    def get_letter_coords(self, c):

        # Define keyboard geometry
        if self.use_optimized_layout == True:
            r1 = "dghpasjrkn"
            r2 = "iqvuwclxm"
            r3 = "tybezfo"
            key_spacing = 3
            r2_offset = 1.5
            r3_offset = 4.5
        else: # Default to QWERTY layout
            r1 = "qwertyuiop"
            r2 = "asdfghjkl"
            r3 = "zxcvbnm"
            key_spacing = 3
            r2_offset = 1
            r3_offset = 2

        # Find letter location
        pos = str.find(r1, c)
        if not pos == -1:
            return (pos * key_spacing * self.deadband, 0.0)
        pos = str.find(r2, c)
        if not pos == -1:
            return ((pos * key_spacing + r2_offset) *
                        self.deadband, key_spacing * self.deadband)
        pos = str.find(r3, c)
        if not pos == -1:
            return ((pos * key_spacing + r3_offset) *
                        self.deadband, 2 * key_spacing * self.deadband)
        return (0,0)

    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # VECTOR-BASED WORD RECOGNITION ROUTINES
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    # --------------------------------------------------------------------------
    # Calculate the vector of a given coordinate sequence
    def process_word(self, coords):

        # Remove coordinates that are too close together
        i = 0
        while i < len(coords):
            if i > 0 and self.distance(coords[i], coords[i-1]) < self.deadband:
                coords.pop(i)
            else:
                i = i + 1

        # Find the total lenth of the traced path
        i = 1
        length = 0;
        while i < len(coords):
            length = length + self.distance(coords[i], coords[i-1]);
            i = i + 1

        # Create the vector from the angles of the path at constant intervals
        vector = [0] * self.vector_resolution
        if not length == 0:
            dist_increment = length / (self.vector_resolution - 1)
            current_dist = 0 # Keep track of current distance along path
            current_index = 1 # Keep track of place in vector
            vector[0] = self.make_positive(math.atan2(coords[1][1]-coords[0][1],
                                                   coords[1][0]-coords[0][0]))
            i = 1
            while i < len(coords):
                current_dist = current_dist + \
                                    self.distance(coords[i], coords[i-1])
                while current_dist >= current_index * dist_increment \
                        and current_index < self.vector_resolution - 1:
                    vector[current_index] = self.make_positive(
                            math.atan2(coords[i][1]-coords[i-1][1],
                                       coords[i][0]-coords[i-1][0]))
                    current_index = current_index + 1
                i = i + 1
            i = len(coords) - 1
            vector[self.vector_resolution - 1] = self.make_positive(
                            math.atan2(coords[i][1]-coords[i-1][1],
                                       coords[i][0]-coords[i-1][0]))
        return vector

    # --------------------------------------------------------------------------
    # Calculate the squared error between two vector paths on the xy plane
    def serror(self, v1, v2):
        i = 0
        px1 = 0
        py1 = 0
        px2 = 0
        py2 = 0
        err = 0
        while i < len(v1):
            nx1 = px1 + math.cos(v1[i])
            ny1 = py1 + math.sin(v1[i])
            nx2 = px2 + math.cos(v2[i])
            ny2 = py2 + math.sin(v2[i])
            err = err + (py1-py2)**2 + (px1-px2)**2
            px1 = nx1
            py1 = ny1
            px2 = nx2
            py2 = ny2
            i = i + 1
        return err

    # --------------------------------------------------------------------------
    # Calculate the cosine similarity between two vectors (DEPRECATED)
    def similarity(self, v1, v2):
        result = np.dot(v1, v2)
        n1 = np.linalg.norm(v1)
        if not np.count_nonzero(v1) == 0:
            result = result / n1
        n2 = np.linalg.norm(v2)
        if not n2 == np.count_nonzero(v2) == 0:
            result = result / n2
        if np.count_nonzero(v1) == 0 and np.count_nonzero(v2) == 0:
            result = 1
        return result

    # --------------------------------------------------------------------------
    # Find the closest match to the given word vector
    def get_closest_word(self, vector):

        closest_options = []
        i = len(self.word_list)-1
        while i >= 0:
            temp_sim_val = self.serror(vector, self.word_list[i][0])
            closest_options.append((i, temp_sim_val))
            closest_options.sort(key=lambda tup: tup[1])
            if len(closest_options) > self.num_options:
                closest_options.pop(len(closest_options)-1)
            i = i - 1
        return closest_options

    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # MAIN ROUTINE
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    # --------------------------------------------------------------------------
    # The main program loop
    def run(self):

        # Connect to the Sensel device
        device = sensel.SenselDevice()
        if device.openConnection():
            print("Connected to Sensel.");
        else:
            print("Error! Could not connect to Sensel board!")
            self.stop()
        device.setFrameContentControl(sensel.SENSEL_FRAME_CONTACTS_FLAG)
        device.startScanning()

        # Initialize Sensel property variables
        (self.device_width, self.device_height) = \
                device.getSensorActiveAreaDimensionsUM()
        self.device_width = self.device_width / 1000 # Convert to mm
        self.device_height = self.device_height / 1000 # Convert to mm
        self.device_max_contacts = max(device.getMaxContacts(), 1)
        
        self.current_contacts = [[]] * self.device_max_contacts
        self.contact_types = [[]] * self.device_max_contacts
        self.num_contact_types = [0,0,0,0]

        print("==============================================================");
        print("Device info: %s" % device.getDeviceInfo())
        print("Device dimensions: (%d, %d)" % (self.device_width,
                                               self.device_height))
        print("Max contacts: %d" % self.device_max_contacts)
        print("Serial number: %s" % device.getSerialNumber())
        print("Battery voltage (mV): %d" % device.getBatteryVoltagemV())
        print("==============================================================");
        
        # Main loop
        while self.running:

            # Poll GUI
            if self.use_gui:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False

            # Read contacts from Sensel
            contacts = device.readContacts()
            if len(contacts) == 0:
                continue

            # Initialize array
            led_array = [0] * self.num_leds

            has_back = False

            # Iterate through contacts
            for c in contacts:
                if c.type == sensel.SENSEL_EVENT_CONTACT_INVALID:
                    pass 
                elif c.type == sensel.SENSEL_EVENT_CONTACT_START:
                    if self.in_keyboard((c.x_pos_mm, c.y_pos_mm)):
                        self.num_contact_types[1] = self.num_contact_types[1] + 1
                        led_array[self.get_led_at(c.x_pos_mm)] = self.max_led_level
                        self.current_contacts[c.id].append((c.x_pos_mm, c.y_pos_mm))
                        self.contact_types[c.id] = 1
                    if self.in_trackpad((c.x_pos_mm, c.y_pos_mm)):
                        led_array[self.get_led_at(c.x_pos_mm)] = self.max_led_level
                        self.current_contacts[c.id].append((c.x_pos_mm, c.y_pos_mm))
                        self.current_contacts[c.id].append((c.x_pos_mm, c.y_pos_mm))
                        self.contact_types[c.id] = 2
                        self.num_contact_types[2] = self.num_contact_types[2] + 1
                    if self.in_buttons((c.x_pos_mm, c.y_pos_mm)):
                        led_array[self.get_led_at(c.x_pos_mm)] = self.max_led_level
                        self.contact_types[c.id] = 3
                        self.num_contact_types[3] = self.num_contact_types[3] + 1
                elif c.type == sensel.SENSEL_EVENT_CONTACT_MOVE:
                    if self.contact_types[c.id] == 1:
                        led_array[self.get_led_at(c.x_pos_mm)] = self.max_led_level
                        self.current_contacts[c.id].append((c.x_pos_mm, c.y_pos_mm))
                    if self.contact_types[c.id] == 2 and self.distance((c.x_pos_mm, c.y_pos_mm), self.current_contacts[c.id][1]) < self.deadband:
                        led_array[self.get_led_at(c.x_pos_mm)] = self.max_led_level
                        dx = c.x_pos_mm - (self.current_contacts[c.id][1][0])
                        dy = c.y_pos_mm - self.current_contacts[c.id][1][1]
                        self.current_contacts[c.id].pop(1)
                        self.current_contacts[c.id].append((c.x_pos_mm, c.y_pos_mm))
                        curr = win32api.GetCursorPos()
                        nx = int(curr[0]+dx*self.mouse_multiplier)
                        ny = int(curr[1]+dy*self.mouse_multiplier)
                        win32api.SetCursorPos((nx, ny))
                elif c.type == sensel.SENSEL_EVENT_CONTACT_END:
                    if self.contact_types[c.id] == 2 and self.distance((c.x_pos_mm, c.y_pos_mm), self.current_contacts[c.id][0]) < self.deadband:
                        curr = win32api.GetCursorPos()
                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN,curr[0],curr[1],0,0)
                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,curr[0],curr[1],0,0)
                    if self.contact_types[c.id] == 3:
                        if c.x_pos_mm < 193:
                            webbrowser.open("https://www.google.com/")
                        else:
                            self.shell.SendKeys("{ENTER}")
                    if self.contact_types[c.id] == 1:
                        if self.num_contact_types[1] <= 1 or True:
                            vi = self.process_word(self.current_contacts[c.id])
                            self.current_contacts[c.id] = [];
                            if self.use_gui:
                                self.clear_screen()
                            options = self.get_closest_word(vi)
                            i = 0
                            c_inc = int(math.floor(255/self.num_options))
                            while i < len(options):
                                vf = self.word_list[options[i][0]][0]
                                if self.use_gui:
                                    self.draw_vector(vf, (i*c_inc,i*c_inc,i*c_inc))
                                print("%s - %f" % (self.word_list[options[i][0]][1],
                                           options[i][1]))
                                self.prev_word_len = len(self.word_list[options[i][0]][1])+1
                                i = i + 1
                            if self.use_gui:
                                self.draw_vector(vi, (255,0,0))
                            print("====================")
                            self.shell.SendKeys(self.word_list[options[0][0]][1]+ " ")
                        else:
                            has_back = True
                            for i in range(len(self.current_contacts)):
                                if self.contact_types[i] == 1:
                                    dist = self.current_contacts[i][0][1]-self.current_contacts[i][len(self.current_contacts[i])-1][1]
                                    win32api.mouse_event(MOUSEEVENTF_WHEEL, x, y, 1, 0)
                                    print "A"
                                    if dist < self.backspace_min_dist:
                                        back_flag = False;
                                    self.contact_types[i] = 0
                                    self.current_contacts[i] = []
                                    self.num_contact_types[1] = 0
                                    

                            
                    self.current_contacts[c.id] = []
                    self.contact_types[c.id] = 0
                else:
                    event = "Error! Unknown contact type!";

            # Set lights
            device.setLEDBrightnessArr(led_array);

        # Disconnect from the Sensel
        device.stopScanning();
        device.closeConnection();
        self.stop()
        
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # UTILITY ROUTINES
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    # --------------------------------------------------------------------------
    # Clear the GUI
    def clear_screen(self):
        if self.use_gui:
            self.screen.fill((0,0,0))
            pygame.display.update()

    # --------------------------------------------------------------------------
    # Draw a vector on the GUI with the given color
    def draw_vector(self, vector, color):
        if self.use_gui:
            length_increment = self.screen_size[0] / self.vector_resolution * .5
            px = self.screen_size[0] / 2
            py = self.screen_size[1] / 2
            for i in range(len(vector) - 1):
                nx = px + math.cos(vector[i])*length_increment
                ny = py + math.sin(vector[i])*length_increment
                pygame.draw.lines(self.screen,color,False,[(px,py),(nx,ny)],1)
                px = nx
                py = ny
            pygame.display.update()

    # --------------------------------------------------------------------------
    # Find the distance between two points
    def distance(self, p1, p2):
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

    # --------------------------------------------------------------------------
    # Find the squared distance between two points
    def distance_squared(self, p1, p2):
        return (p1[0] - p2[0])**2 + (p1[1] - p2[1])**2

    # --------------------------------------------------------------------------
    # Get the index of the LED at the given x position on the board
    def get_led_at(self, pos):
        return int(self.coerce(math.floor(
                        self.num_leds * pos / self.device_width), 0, 15))

    # --------------------------------------------------------------------------
    # Fit a value into a specified range
    def coerce(self, val, min_val, max_val):
        return min(max(val, min_val), max_val)

    # --------------------------------------------------------------------------
    # Make radian angles positive
    def make_positive(self, theta):
        while theta < 0:
            theta = theta + 2 * math.pi
        return theta

    # --------------------------------------------------------------------------
    # Determine whether point is in keyboard area
    def in_keyboard(self, p):
        return self.keyboard[0] < p[0] < self.keyboard[1] and \
                self.keyboard[2] < p[1] < self.keyboard[3];

    # --------------------------------------------------------------------------
    # Determine whether point is in trackpad area
    def in_trackpad(self, p):
        return self.trackpad[0] < p[0] < self.trackpad[1] and \
                self.trackpad[2] < p[1] < self.trackpad[3];
    
    # --------------------------------------------------------------------------
    # Determine whether point is in buttons area
    def in_buttons(self, p):
        return self.buttons[0] < p[0] < self.buttons[1] and \
                self.buttons[2] < p[1] < self.buttons[3];

    # --------------------------------------------------------------------------
    # Exit the program
    def stop(self):
        pygame.quit()
        sys.exit()

# === MAIN =====================================================================
# Program entrance point
# ==============================================================================

if __name__ == "__main__":
    ske = SenselKeyboardEmulator()
    ske.run()

# Finis
