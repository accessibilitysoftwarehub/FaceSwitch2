import sys 
from PyQt5.uic import loadUi
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtWidgets import QApplication, QDialog, QInputDialog, QMainWindow, QCheckBox, QWidget, QPushButton, QLabel, \
    QMessageBox, QDesktopWidget, QFileDialog, QErrorMessage, QInputDialog, QLineEdit
from PyQt5.QtGui import QIcon, QPalette, QColor, QPixmap, QImage
from PyQt5.QtCore import pyqtSlot, Qt, QPoint
from imutils import face_utils
from collections import deque
import cv2
import dlib
import win32com.client as comclt  # Used to insert keys
import os

import json  # for saving/loading settings
import msvcrt

class App(QDialog):
    def __init__(self):
        super(App, self).__init__()
        self.title = 'Face Switch 2.0'
        self.closeEvent = self.closeEvent
        self.setWindowIcon(QtGui.QIcon('interface/icon.png'))
        
        global app_dir  # Allow the variable to be used anywhere
        app_dir = os.environ['USERPROFILE'] + '/.FaceSwitch2'  # Path to application settings
        
        if not os.path.isdir(app_dir):  # Create the directory if it does not already exist
            try:
                os.mkdir(app_dir)  # Make the .FaceSwitch2 folder
            except OSError:
                print("Creation of the directory %s failed" % app_dir)
            else:
                print("Successfully created the directory %s " % app_dir)
        
        self.captureFacePositions = True
        self.capturedPositions = False
        self.faceShapePredictorActivated = False
        
        self.count = 0
        self.webcamActive = True
        
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # gives an error without CAP_DSHOW

        self.base_line = 0


        self.sparetxtvar = "Press a key to keybind"
        self.changesMade = False

        self.initUI()
        
        self.smileActivated = False
        self.openMouthActivated = False
        self.raiseEyebrowsActivated = False
        self.snarlActivated = False
        self.blinkActivated = False
        self.calibrate = False

        
        self.wsh = comclt.Dispatch("WScript.Shell")  # Open keytyper
        
        self.center()
        self.oldPos = self.pos()
        self.landmarks()
        
        self.openMouthVar = 0
        self.raiseEyebrowsVar = 0
        self.smileVar = 0
        self.snarlVar = 0
        self.blinkVar = 0

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def mousePressEvent(self, event):
        self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        delta = QPoint (event.globalPos() - self.oldPos)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.oldPos = event.globalPos()

    def landmarks(self):
        p = "resources/shape_predictor_68_face_landmarks.dat"  # p = our pre-trained model
        
        detector = dlib.get_frontal_face_detector()
        predictor = dlib.shape_predictor(p)

        gesture_arr = deque(maxlen=15)
        gesture_arr.extend([-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1])
        
        while self.webcamActive:
            # Getting out image by webcam 
            _, frame = self.cap.read()
            # Converting the image to gray scale
            if frame is not None:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                # Get faces into webcam's image
                rects = detector(gray, 0)
            else:
                print("Error connecting to webcam! Exiting...")
                sys.exit()
            
            # Activated
            if self.faceShapePredictorActivated:
                for (i, rect) in enumerate(rects):
                    # Make the prediction and transform it to numpy array
                    shape = predictor(gray, rect)
                    shape = face_utils.shape_to_np(shape)

                    for (x, y) in shape:
                        cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)  # (0, 255, 0) = Green
                    # Recognise gestures

                    if self.calibrate:
                        self.base_line = ((shape[16][0]) - (shape[0][0]))
                        print("Calibrated base_line to", self.base_line)
                        # turn off calibration
                        self.calibrate = not self.calibrate

                    # Open mouth
                    if self.openMouthActivated:
                        mouth_top = ((shape[61][1]) + (shape[62][1]) + (shape[63][1]))/3
                        mouth_bottom = ((shape[65][1]) + (shape[66][1]) + (shape[67][1]))/3
                        mouth_height = mouth_bottom - mouth_top
                        try:
                            if mouth_height/self.base_line > float(self.openMouthVar):
                                gesture_arr.append(0)
                        except:
                            pass
                    # Raise Eyebrow
                    if self.raiseEyebrowsActivated:
                        eye_top = ((shape[18][1]) + (shape[19][1]) + (shape[20][1]) + (shape[23][1])
                                   + (shape[24][1]) + (shape[25][1]))/6
                        eye_bottom = ((shape[27][1]) + (shape[28][1]))/2
                        eye_height = eye_bottom - eye_top
                        try:
                            if eye_height/self.base_line > float(self.raiseEyebrowsVar):
                                gesture_arr.append(1)
                        except:
                            pass
                    # Blink
                    if self.blinkActivated:
                        eyelid_top = ((shape[37][1]) + (shape[38][1]) + (shape[43][1]) + (shape[44][1]))/4
                        eyelid_bottom = ((shape[40][1]) + (shape[41][1]) + (shape[46][1]) + (shape[47][1]))/4
                        eyelid_height = eyelid_bottom - eyelid_top
                        try:
                            if eyelid_height/self.base_line < float(self.blinkVar):
                                gesture_arr.append(2)
                        except:
                            pass
                    # Smile
                    if self.smileActivated:
                        mouth_left = ((shape[48][0]) + (shape[49][0]) + (shape[59][0]) + (shape[60][0]))/4
                        mouth_right = ((shape[53][0]) + (shape[54][0]) + (shape[55][0]) + (shape[64][0]))/4
                        mouth_width = mouth_right - mouth_left
                        try:
                            if mouth_width/self.base_line > float(self.smileVar):
                                gesture_arr.append(3)
                        except:
                            pass
                    # Scrunch nose
                    if self.snarlActivated:
                        nose_top = ((shape[21][1]) + (shape[22][1]))/2
                        nose_bottom = ((shape[31][1]) + (shape[35][1]))/2
                        nose_height = nose_bottom - nose_top
                        try:
                            if nose_height/self.base_line < float(self.snarlVar):
                                gesture_arr.append(4)
                        except:
                            pass
                    
                    gesture_output = -1  # Set the default value to -1 (no gesture)
                    #  Get the most common number (gesture) from the array and set it to be the registered gesture
                    #  (eliminates noise)
                    if -1 not in gesture_arr:  #  Only if the array is full of gesture recognitions (i.e no default values)
                        gesture_output = max(set(gesture_arr), key=gesture_arr.count)
                    
                    if gesture_output == 0:
                        print("Mouth opened! - ", (mouth_height/self.base_line))
                        self.wsh.SendKeys(self.txtOpenMouth.toPlainText())
                        for t in range(60, 68, 1):
                            cv2.circle(frame, (shape[t][0], shape[t][1]), 2, (255, 0, 0), -1)
                        
                    elif gesture_output == 1:
                        print("Eyebrows raised! - ", (eye_height/self.base_line))
                        self.wsh.SendKeys(self.txtRaiseEyebrows.toPlainText())
                        for t in range(17, 27, 1):
                            cv2.circle(frame, (shape[t][0], shape[t][1]), 2, (255, 0, 0), -1)
                        
                    elif gesture_output == 2:
                        print("Eye close detected! - ", (eyelid_height/self.base_line))
                        self.wsh.SendKeys(self.txtBlink.toPlainText())
                        for t in range(36, 48, 1):
                            cv2.circle(frame, (shape[t][0], shape[t][1]), 2, (255, 0, 0), -1)
                        
                    elif gesture_output == 3:
                        print("Smile detected! - ", (mouth_width/self.base_line))
                        self.wsh.SendKeys(self.txtSmile.toPlainText())
                        for t in range(54, 60, 1):
                            cv2.circle(frame, (shape[t][0], shape[t][1]), 2, (255, 0, 0), -1)
                        cv2.circle(frame, (shape[48][0], shape[48][1]), 2, (255, 0, 0), -1)
                        
                    elif gesture_output == 4:
                        print("Anger detected! - ", (nose_height/self.base_line))
                        self.wsh.SendKeys(self.txtSnarl.toPlainText())
                        for t in range(27, 36, 1):
                            cv2.circle(frame, (shape[t][0], shape[t][1]), 2, (255, 0, 0), -1)
                
                    if 0 <= gesture_output <= 4:
                        gesture_arr = deque(maxlen=15)
                        gesture_arr.extend([-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1])
                        print(gesture_output)
                        
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = QImage(rgb_frame.tobytes(), 
                rgb_frame.shape[1],
                rgb_frame.shape[0],
                QImage.Format_RGB888)
            self.webcam.setPixmap(QPixmap.fromImage(image))
            self.webcam.show()
            
            k = cv2.waitKey(5) & 0xFF
            if k == 27:
                self.exit()
            # Press 'q' to break out of loop
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.exit()
                
        cv2.destroyAllWindows()
        self.cap.release()
        
    def initUI(self):
        loadUi('interface/fr.ui', self)
        
        # Load default settings
        self.value_changed()
        
        # Load previous state settings from file
        print("Checking for state settings...")
        state_settings_path = app_dir + '/state_settings.json'
        self.load_settings(state_settings_path)  # Load the last settings that were used
        self.changesMade = False  # this is so after the load settings is called, changes aren't considered to be made yet
        QApplication.setStyle("Fusion")
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        QApplication.setPalette(palette)

        # Text boxes
        #textEdit.mousePressEvent = text_click
        self.txtOpenMouth.mousePressEvent = self.get_userinput
        self.txtRaiseEyebrows.mousePressEvent = self.get_userinput1
        self.txtSmile.mousePressEvent = self.get_userinput2
        self.txtSnarl.mousePressEvent = self.get_userinput3
        self.txtBlink.mousePressEvent = self.get_userinput4

        # Checkboxes
        self.cboxOpenMouth.stateChanged.connect(lambda: self.btn_state(self.cboxOpenMouth))
        self.cboxRaiseEyebrows.stateChanged.connect(lambda: self.btn_state(self.cboxRaiseEyebrows))
        self.cboxSmile.stateChanged.connect(lambda: self.btn_state(self.cboxSmile))
        self.cboxSnarl.stateChanged.connect(lambda: self.btn_state(self.cboxSnarl))
        self.cboxBlink.stateChanged.connect(lambda: self.btn_state(self.cboxBlink))
        
        # Buttons
        self.btnInitialize.setToolTip('Toggle Gesture Detection ON/OFF')
        self.btnInitialize.clicked.connect(self.on_click_initialize)
        self.btnSave.setToolTip('Save Settings')		
        self.btnSave.clicked.connect(lambda: self.btn_save_settings(self.txtOpenMouth.toPlainText(),
                                                                    self.txtRaiseEyebrows.toPlainText(),
                                                                    self.txtSmile.toPlainText(),
                                                                    self.txtSnarl.toPlainText(),
                                                                    self.txtBlink.toPlainText(),
                                                                    self.openMouthVar,
                                                                    self.raiseEyebrowsVar,
                                                                    self.smileVar,
                                                                    self.snarlVar,
                                                                    self.blinkVar))
        self.btnLoad.setToolTip('Load Settings')
        self.btnLoad.clicked.connect(lambda: self.btn_load_settings())
        self.btnCalibrate.clicked.connect(lambda: self.btn_calibrate())

        # sliders
        self.sliderOpenMouth.valueChanged.connect(lambda: self.value_changed())
        self.sliderRaiseEyebrows.valueChanged.connect(lambda: self.value_changed())
        self.sliderSmile.valueChanged.connect(lambda: self.value_changed())
        self.sliderSnarl.valueChanged.connect(lambda: self.value_changed())
        self.sliderBlink.valueChanged.connect(lambda: self.value_changed())
        
        # webcam
        self.webcam.setText("Webcam")
        self.show()

        #       self.txtRaiseEyebrows.mousePressEvent = self.get_userinput1
        #       self.txtSmile.mousePressEvent = self.get_userinput2
        #       self.txtSnarl.mousePressEvent = self.get_userinput3
        #       self.txtBlink.mousePressEvent = self.get_userinput4

    def get_userinput(self, state):
        self.changesMade = not self.changesMade
        self.txtOpenMouth.setReadOnly(True)

        if self.changesMade:
            self.sparetxtvar = ""
            self.txtOpenMouth.setPlainText("Press to set new KeyBind")

        elif not self.changesMade:
            self.txtOpenMouth.setPlainText(self.sparetxtvar)
            self.txtOpenMouth.setReadOnly(False)

    def get_userinput1(self, state):
        self.changesMade = not self.changesMade
        self.txtRaiseEyebrows.setReadOnly(True)

        if self.changesMade:
            self.sparetxtvar = ""
            self.txtRaiseEyebrows.setPlainText("Press to set new KeyBind")

        elif not self.changesMade:
            self.txtRaiseEyebrows.setPlainText(self.sparetxtvar)
            self.txtRaiseEyebrows.setReadOnly(False)

    def get_userinput2(self, state):
        self.changesMade = not self.changesMade
        self.txtSmile.setReadOnly(True)
        if self.changesMade:
            self.sparetxtvar = ""
            self.txtSmile.setPlainText("Press to set new KeyBind")

        elif not self.changesMade:
            self.txtSmile.setPlainText(self.sparetxtvar)
            self.txtSmile.setReadOnly(False)

    def get_userinput3(self, state):
        self.changesMade = not self.changesMade
        self.txtSnarl.setReadOnly(True)
        if self.changesMade:
            self.sparetxtvar = ""
            self.txtSnarl.setPlainText("Press to set new KeyBind")

        elif not self.changesMade:
            self.txtSnarl.setPlainText(self.sparetxtvar)
            self.txtSnarl.setReadOnly(False)

    def get_userinput4(self, state):
        self.changesMade = not self.changesMade
        self.txtBlink.setReadOnly(True)
        if self.changesMade:
            self.sparetxtvar = ""
            self.txtBlink.setPlainText("Press to set new KeyBind")

        elif not self.changesMade:
            self.txtBlink.setPlainText(self.sparetxtvar)
            self.txtBlink.setReadOnly(False)

    def keyPressEvent(self, e):
        if self.changesMade:
            print(e.key())

            # Numerical
            if e.key() == Qt.Key_0:
                self.sparetxtvar += "0"
            elif e.key() == Qt.Key_1:
                self.sparetxtvar += "1"
            elif e.key() == Qt.Key_2:
                self.sparetxtvar += "2"
            elif e.key() == Qt.Key_3:
                self.sparetxtvar += "3"
            elif e.key() == Qt.Key_4:
                self.sparetxtvar += "4"
            elif e.key() == Qt.Key_5:
                self.sparetxtvar += "5"
            elif e.key() == Qt.Key_6:
                self.sparetxtvar += "6"
            elif e.key() == Qt.Key_7:
                self.sparetxtvar += "7"
            elif e.key() == Qt.Key_8:
                self.sparetxtvar += "8"
            elif e.key() == Qt.Key_9:
                self.sparetxtvar += "9"

            # Alphabetical
            elif e.key() == Qt.Key_A:
                self.sparetxtvar += "a"
            elif e.key() == Qt.Key_B:
                self.sparetxtvar += "b"
            elif e.key() == Qt.Key_C:
                self.sparetxtvar += "c"
            elif e.key() == Qt.Key_D:
                self.sparetxtvar += "d"
            elif e.key() == Qt.Key_E:
                self.sparetxtvar += "e"
            elif e.key() == Qt.Key_F:
                self.sparetxtvar += "f"
            elif e.key() == Qt.Key_G:
                self.sparetxtvar += "g"
            elif e.key() == Qt.Key_H:
                self.sparetxtvar += "h"
            elif e.key() == Qt.Key_I:
                self.sparetxtvar += "i"
            elif e.key() == Qt.Key_J:
                self.sparetxtvar += "j"
            elif e.key() == Qt.Key_K:
                self.sparetxtvar += "k"
            elif e.key() == Qt.Key_L:
                self.sparetxtvar += "l"
            elif e.key() == Qt.Key_M:
                self.sparetxtvar += "m"
            elif e.key() == Qt.Key_N:
                self.sparetxtvar += "n"
            elif e.key() == Qt.Key_O:
                self.sparetxtvar += "o"
            elif e.key() == Qt.Key_P:
                self.sparetxtvar += "p"
            elif e.key() == Qt.Key_Q:
                self.sparetxtvar += "q"
            elif e.key() == Qt.Key_R:
                self.sparetxtvar += "r"
            elif e.key() == Qt.Key_S:
                self.sparetxtvar += "s"
            elif e.key() == Qt.Key_T:
                self.sparetxtvar += "t"
            elif e.key() == Qt.Key_U:
                self.sparetxtvar += "u"
            elif e.key() == Qt.Key_V:
                self.sparetxtvar += "v"
            elif e.key() == Qt.Key_W:
                self.sparetxtvar += "w"
            elif e.key() == Qt.Key_X:
                self.sparetxtvar += "x"
            elif e.key() == Qt.Key_Y:
                self.sparetxtvar += "y"
            elif e.key() == Qt.Key_Z:
                self.sparetxtvar += "z"

            elif e.key() == Qt.Key_Space:
                self.sparetxtvar += " "

            # Modifiers
            elif e.key() == Qt.Key_Shift:
                self.sparetxtvar += "+"
            elif e.key() == Qt.Key_Control:
                self.sparetxtvar += "^"
            elif e.key() == Qt.Key_Alt:
                self.sparetxtvar += "%"

            # Left Right Up Down
            elif e.key() == Qt.Key_Left:
                self.sparetxtvar += "{LEFT}"
            elif e.key() == Qt.Key_Right:
                self.sparetxtvar += "{RIGHT}"
            elif e.key() == Qt.Key_Down:
                self.sparetxtvar += "{DOWN}"
            elif e.key() == Qt.Key_Up:
                self.sparetxtvar += "{UP}"

            # Function keys
            elif e.key() == Qt.Key_F1:
                self.sparetxtvar += "{F1}"
            elif e.key() == Qt.Key_F2:
                self.sparetxtvar += "{F2}"
            elif e.key() == Qt.Key_F3:
                self.sparetxtvar += "{F3}"
            elif e.key() == Qt.Key_F4:
                self.sparetxtvar += "{F4}"
            elif e.key() == Qt.Key_F5:
                self.sparetxtvar += "{F5}"
            elif e.key() == Qt.Key_F6:
                self.sparetxtvar += "{F6}"
            elif e.key() == Qt.Key_F7:
                self.sparetxtvar += "{F7}"
            elif e.key() == Qt.Key_F8:
                self.sparetxtvar += "{F8}"
            elif e.key() == Qt.Key_F9:
                self.sparetxtvar += "{F9}"
            elif e.key() == Qt.Key_F10:
                self.sparetxtvar += "{F10}"
            elif e.key() == Qt.Key_F11:
                self.sparetxtvar += "{F11}"
            elif e.key() == Qt.Key_F12:
                self.sparetxtvar += "{F12}"

            # Goes all the way to F16 if required.

            # Alternative keys:
            # {BACKSPACE}
            elif e.key() == Qt.Key_Backspace:
                self.sparetxtvar += "{F12}"
            # {CAPSLOCK}
            elif e.key() == Qt.Key_CapsLock:
                self.sparetxtvar += "{CAPSLOCK}"
            # {CLEAR}
            elif e.key() == Qt.Key_Clear:
                self.sparetxtvar += "{CLEAR}"
            # {DELETE}
            elif e.key() == Qt.Key_Delete:
                self.sparetxtvar += "{DELETE}"
            # {INSERT}
            elif e.key() == Qt.Key_Insert:
                self.sparetxtvar += "{INSERT}"
            # {END}
            elif e.key() == Qt.Key_End:
                self.sparetxtvar += "{END}"

            # {ENTER}
            elif e.key() == Qt.Key_Enter:
                self.sparetxtvar += "{ENTER}"

            # {ESCAPE}
            elif e.key() == Qt.Key_Escape:
                self.sparetxtvar += "{ESCAPE}"
            # {HELP}
            elif e.key() == Qt.Key_Help:
                self.sparetxtvar += "{HELP}"
            # {HOME}
            elif e.key() == Qt.Key_Home:
                self.sparetxtvar += "{HOME}"
            # {NUMLOCK}
            elif e.key() == Qt.Key_NumLock:
                self.sparetxtvar += "{NUMLOCK}"
            # {PGDN} / Page Down
            elif e.key() == Qt.Key_PageDown:
                self.sparetxtvar += "{PGDN}"
            # {PGUP} / Page Up
            elif e.key() == Qt.Key_PageUp:
                self.sparetxtvar += "{PGUP}"
            # {SCROLLLOCK}
            elif e.key() == Qt.Key_ScrollLock:
                self.sparetxtvar += "{SCROLLLOCK}"
            # {TAB}
            elif e.key() == Qt.Key_Tab:
                self.sparetxtvar += "{TAB}"

            # {BREAK}
            # {PRTSC} ## Print Screen


    def btn_calibrate(self):
        if self.faceShapePredictorActivated:
            self.calibrate = not self.calibrate
        else:
            print("Must be activated")

    def value_changed(self):
        self.openMouthVar = round(float(self.sliderOpenMouth.value()) / 277, 2)
        self.raiseEyebrowsVar = round(float(self.sliderRaiseEyebrows.value()) / 250, 2)
        self.smileVar = round(float(self.sliderSmile.value()) / 166, 2)
        self.snarlVar = round(float(self.sliderSnarl.value()) / 141, 3)
        self.blinkVar = round(float(self.sliderBlink.value()) / 1000, 3)
    
        self.lblOpenMouthT.setText(str(self.openMouthVar))
        self.lblRaiseEyebrowsT.setText(str(self.raiseEyebrowsVar))
        self.lblSmileT.setText(str(self.smileVar))
        self.lblSnarlT.setText(str(self.snarlVar))
        self.lblBlinkT.setText(str(self.blinkVar))
        self.changesMade = True
    
    def save_state(self, openMouthTxt, raiseEyebrowsTxt, smileTxt, snarlTxt, blinkTxt, openMouthVar, raiseEyebrowsVar, smileVar, snarlVar, blinkVar):
        openMouthKey = openMouthTxt
        raiseEyebrowsKey = raiseEyebrowsTxt
        smileKey = smileTxt
        snarlKey = snarlTxt
        blinkKey = blinkTxt
        openMouth = openMouthVar
        raiseEyebrows = raiseEyebrowsVar
        smile = smileVar
        snarl = snarlVar
        blink = blinkVar
        data = {'openMouthKey': openMouthKey, 'raiseEyebrowsKey': raiseEyebrowsKey,
                'smileKey': smileKey, 'snarlKey': snarlKey, 'blinkKey': blinkKey, 'openMouthVar': openMouth,
                'raiseEyebrowsVar': raiseEyebrows, 'smileVar': smile, 'snarlVar': snarl, 'blinkVar': blink
                }
        
        filepathwithextension = app_dir + '/state_settings.json'
        with open(filepathwithextension, 'w') as f:
            json.dump(data, f)
    
    def save_settings(self, path, fileName, data):
        filepathwithextension = path + '/' + fileName + '.json'
        with open(filepathwithextension, 'w') as f:
            json.dump(data, f)
        print("Settings file: '" + filepathwithextension + "' saved successfully!")
        
    def btn_save_settings(self, openMouthTxt, raiseEyebrowsTxt, smileTxt, snarlTxt, blinkTxt, openMouthVar, raiseEyebrowsVar, smileVar, snarlVar, blinkVar):
        openMouthKey = openMouthTxt
        raiseEyebrowsKey = raiseEyebrowsTxt
        smileKey = smileTxt
        snarlKey = snarlTxt
        blinkKey = blinkTxt
        openMouth = openMouthVar
        raiseEyebrows = raiseEyebrowsVar
        smile = smileVar
        snarl = snarlVar
        blink = blinkVar
        data_to_save = {'openMouthKey': openMouthKey, 'raiseEyebrowsKey': raiseEyebrowsKey, 'smileKey': smileKey,
                        'snarlKey': snarlKey, 'blinkKey': blinkKey, 'openMouthVar': openMouth,
                        'raiseEyebrowsVar': raiseEyebrows, 'smileVar': smile, 'snarlVar': snarl, 'blinkVar': blink
                        }
        name, ok = QInputDialog.getText(self, 'Save Settings', 'Enter your name:')
        
        if ok and name != '':
            self.save_settings(app_dir, name, data_to_save)
    
    def load_settings(self, fileName):
        data = {}
        name = fileName
        try:
            with open(name, 'r') as f:
                data = json.load(f)
                self.txtOpenMouth.setPlainText(str(data['openMouthKey']))
                self.txtRaiseEyebrows.setPlainText(str(data['raiseEyebrowsKey']))
                self.txtSmile.setPlainText(str(data['smileKey']))
                self.txtSnarl.setPlainText(str(data['snarlKey']))
                self.txtBlink.setPlainText(str(data['blinkKey']))
                self.sliderOpenMouth.setValue(int(data['openMouthVar']*277))
                self.sliderRaiseEyebrows.setValue(int(data['raiseEyebrowsVar']*250))
                self.sliderSmile.setValue(int(data['smileVar']*166))
                self.sliderSnarl.setValue(int(data['snarlVar']*141))
                self.sliderBlink.setValue(int(data['blinkVar']*1000))
                self.value_changed()
                print("Settings file: '" + name + "' loaded successfully!")
        except:
            print("Settings file: '" + name + "' not found!")
    
    def btn_load_settings(self):
        f, a = QFileDialog.getOpenFileName(self, "title", app_dir, "json files  (*.json)")  # returns two items
        if f != '':
            self.load_settings(f)  # pass the first item
    
    def btn_state(self, state):
        # checkBox activations
        # open mouth checkbox
        if state.objectName() == "cboxOpenMouth":
            if state.isChecked():
                if not self.openMouthActivated:
                    print("Open Mouth detection activated")
                    self.openMouthActivated = True
            else:
                self.openMouthActivated = False
                print("Open Mouth detection deactivated")
        # raise eyebrow checkbox
        if state.objectName() == "cboxRaiseEyebrows":
            if state.isChecked():
                if not self.raiseEyebrowsActivated:
                    print("Raise Eyebrows detection activated")
                    self.raiseEyebrowsActivated = True
            else:
                self.raiseEyebrowsActivated = False
                print("Raise Eyebrows detection deactivated")
        # smile checkbox
        if state.objectName() == "cboxSmile":
            if state.isChecked():
                if not self.smileActivated:
                    print("Smile detection activated")
                    self.smileActivated = True
            else:
                self.smileActivated = False
                print("Smile detection deactivated")	
                
        # snarl checkbox
        if state.objectName() == "cboxSnarl":
            if state.isChecked():
                if not self.snarlActivated:
                    print("Snarl detection activated")
                    self.snarlActivated = True
            else:
                self.snarlActivated = False
                print("Snarl detection deactivated")
        # blink checkbox
        if state.objectName() == "cboxBlink":
            if state.isChecked():
                if not self.blinkActivated:
                    print("Blink detection activated")
                    self.blinkActivated = True
            else:
                self.blinkActivated = False
                print("Blink detection deactivated")

    @pyqtSlot()
    def on_click_initialize(self):  # Used to turn the gesture detection ON or OFF
        if self.faceShapePredictorActivated:
            self.faceShapePredictorActivated = False
            print("Gesture detection Deactivated!")
            self.btnInitialize.setText("Activate")

        elif not self.faceShapePredictorActivated:
            self.faceShapePredictorActivated = True
            print("Gesture detection Activated!")
            self.btnInitialize.setText("Deactivate")

    def warningbox(self):
        pass

    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Message', "Are you sure you want to quit?", QMessageBox.Yes, QMessageBox.No)

        if reply == QMessageBox.Yes:
            # Save the settings before exiting
            print("Saving state settings...")
            self.save_state(self.txtOpenMouth.toPlainText(), self.txtRaiseEyebrows.toPlainText(),
                            self.txtSmile.toPlainText(), self.txtSnarl.toPlainText(),
                            self.txtBlink.toPlainText(), self.openMouthVar, self.raiseEyebrowsVar,
                            self.smileVar, self.snarlVar, self.blinkVar)
            print("State settings saved successfully!")
            self.webcamActive = False
            event.accept()
        else:
            event.ignore()


app = QApplication(sys.argv)
widget = App()
widget.show()
print("Now exiting")
sys.exit()
