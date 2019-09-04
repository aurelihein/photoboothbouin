#!/usr/bin/env python
# -*- coding: utf-8 -*-
# author : aurelien BOUIN
# date : 19/06/2019
# VIRTUALENV
# pip in virtualenv :
# virtualenv -p python3 new_virtualenv
# source new_virtualenv/bin/activate
# deactivate
# retrieve pip install needed : pip install -r requirements.txt
# save previous pip install : pip freeze > requirements.txt
# UNIT TEST :
# http://sametmax.com/un-gros-guide-bien-gras-sur-les-tests-unitaires-en-python-partie-3/
# Test case like unittest with : (it will use all methode starting with test_
# Use py.test -s
# Format code checking
# Check python formating with :
# pylint
# you can create a file with exception :
# pylint --disable=logging-not-lazy,broad-except,line-too-long --generate-rcfile > pylintrc
## install pip-autoremove
#pip install pip-autoremove
## remove "somepackage" plus its dependencies:
#pip-autoremove somepackage -y
"""
Program that display something
"""

#1.0.0 : Version initial

VERSION = "1.0.0"

ENABLE_PRINTING = False

import argparse
import logging as lg
import picamera
import pygame
import time
import os
import PIL.Image
#import cups
import RPi.GPIO as GPIO

from threading import Thread
from pygame.locals import *
from time import sleep
from PIL import Image, ImageDraw

environment = {}

# initialise global variables
Numeral = ""  # Numeral is the number display
Message = ""  # Message is a fullscreen message
BackgroundColor = ""
CountDownPhoto = ""
CountPhotoOnCart = ""
SmallMessage = ""  # SmallMessage is a lower banner message
TotalImageCount = 0  # Counter for Display and to monitor paper usage
PhotosPerCart = 30  # Selphy takes 16 sheets per tray
imagecounter = 0

environment["output_photos_folder"] = "output_photos"
environment["output_montages_photos_folder"] = "output_photos/images"
environment["tmp_photo_print_path"] = "/tmp/tempprint.png"
environment["template_path"] = "images/template.png"

#GPIO to use for the BP
environment["bp_to_launch"] = 25

environment["camera_parameters"] = {}
environment["camera_parameters"]["resolution"] = 1920, 1080
environment["camera_parameters"]["rotation"] = 0
environment["camera_parameters"]["hflip"] = True
environment["camera_parameters"]["vflip"] = False
environment["camera_parameters"]["brightness"] = 50
environment["camera_parameters"]["preview_alpha"] = 120
environment["camera_parameters"]["preview_fullscreen"] = True
environment["camera_pointer"] = None

ImageShowed = False
Printing = False
#IMAGE_WIDTH = 558
#IMAGE_HEIGHT = 374
IMAGE_WIDTH = 550
IMAGE_HEIGHT = 360

def setup_pygame(environment):
    """ Setup pygame environment """
    # Load the background template

    # initialise pygame
    pygame.init()  # Initialise pygame
    pygame.mouse.set_visible(False) #hide the mouse cursor

    infoObject = pygame.display.Info()
    environment["screen_w"] = infoObject.current_w # save screen width
    environment["screen_h"] = infoObject.current_h # save screen height

    environment["screen_pointer"] = pygame.display.set_mode((environment["screen_w"], environment["screen_h"]), pygame.FULLSCREEN)  # Full screen
    background = pygame.Surface(environment["screen_pointer"].get_size())  # Create the background object
    environment["background_screen_pointer"] = background.convert()  # Convert it to a background

    environment["screen_picture_pointer"] = pygame.display.set_mode((environment["screen_w"], environment["screen_h"]), pygame.FULLSCREEN)  # Full screen
    backgroundPicture = pygame.Surface(environment["screen_picture_pointer"].get_size())  # Create the background object
    #TODO : Check if it is not backgroundPicture that needs to be get !
    environment["background_screen_picture_pointer"] = backgroundPicture.convert()  # Convert it to a background
    #environment["background_screen_picture_pointer"] = background.convert()  # Convert it to a background

    environment["replay_picture_scale_w"] = environment["screen_w"] # how wide to scale the jpg when replaying
    environment["replay_picture_scale_h"] = environment["screen_h"] # how high to scale the jpg when replaying

    #update camera resolution ?!
    environment["camera_parameters"]["resolution"] = environment["screen_w"], environment["screen_h"]

def setup_rpi_camera(environment):
    environment["camera_pointer"] = picamera.PiCamera()
    # Initialise the camera object
    environment["camera_pointer"].resolution = environment["camera_parameters"]["resolution"]
    environment["camera_pointer"].rotation = environment["camera_parameters"]["rotation"]
    environment["camera_pointer"].hflip = environment["camera_parameters"]["hflip"]
    environment["camera_pointer"].vflip = environment["camera_parameters"]["vflip"]
    environment["camera_pointer"].brightness = environment["camera_parameters"]["brightness"]
    environment["camera_pointer"].preview_alpha = environment["camera_parameters"]["preview_alpha"]
    environment["camera_pointer"].preview_fullscreen = environment["camera_parameters"]["preview_fullscreen"]
    #environment["camera_pointer"].framerate             = 24
    #environment["camera_pointer"].sharpness             = 0
    #environment["camera_pointer"].contrast              = 8
    #environment["camera_pointer"].saturation            = 0
    #environment["camera_pointer"].ISO                   = 0
    #environment["camera_pointer"].video_stabilization   = False
    #environment["camera_pointer"].exposure_compensation = 0
    #environment["camera_pointer"].exposure_mode         = 'auto'
    #environment["camera_pointer"].meter_mode            = 'average'
    #environment["camera_pointer"].awb_mode              = 'auto'
    #environment["camera_pointer"].image_effect          = 'none'
    #environment["camera_pointer"].color_effects         = None
    #environment["camera_pointer"].crop                  = (0.0, 0.0, 1.0, 1.0)

def setup_rpi_gpio(environment):
    """ The RPI GPIO setup"""
    #Setup GPIO for BP
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(environment["bp_to_launch"], GPIO.IN, pull_up_down=GPIO.PUD_UP)

# A function to handle keyboard/mouse/device input events
def input(events):
    for event in events:  # Hit the ESC key to quit the slideshow.
        if (event.type == QUIT or
                (event.type == KEYDOWN and event.key == K_ESCAPE)):
            pygame.quit()


# set variables to properly display the image on screen at right ratio
def set_dimensions(environment, img_w, img_h):
    # Note this only works when in booting in desktop mode.
    # When running in terminal, the size is not correct (it displays small). Why?

    # connect to global vars
    global offset_y, offset_x

    # based on output screen resolution, calculate how to display
    ratio_h = (environment["screen_w"] * img_h) / img_w

    if (ratio_h < environment["screen_h"]):
        #Use horizontal black bars
        #print "horizontal black bars"
        environment["replay_picture_scale_h"] = ratio_h
        environment["replay_picture_scale_w"] = environment["screen_w"]
        offset_y = (environment["screen_h"] - ratio_h) / 2
        offset_x = 0
    elif (ratio_h > environment["screen_h"]):
        #Use vertical black bars
        #print "vertical black bars"
        environment["replay_picture_scale_w"] = (environment["screen_h"] * img_w) / img_h
        environment["replay_picture_scale_h"] = environment["screen_h"]
        offset_x = (environment["screen_w"] - environment["replay_picture_scale_w"]) / 2
        offset_y = 0
    else:
        #No need for black bars as photo ratio equals screen ratio
        #print "no black bars"
        environment["replay_picture_scale_w"] = environment["screen_w"]
        environment["replay_picture_scale_h"] = environment["screen_h"]
        offset_y = offset_x = 0

def InitFolder(environment):
    global Message

    Message = 'Folder Check...'
    UpdateDisplay(environment)
    Message = ''

    #check image folder existing, create if not exists
    if not os.path.isdir(environment["output_photos_folder"]):
        os.makedirs(environment["output_photos_folder"])

    if not os.path.isdir(environment["output_montages_photos_folder"]):
        os.makedirs(environment["output_montages_photos_folder"])

def UpdateDisplay(environment):
    # init global variables from main thread
    global Numeral
    global Message
    global screen
    global pygame
    global ImageShowed
    global screenPicture
    global CountDownPhoto

    environment["background_screen_pointer"].fill(pygame.Color("white"))  # White background

    if (BackgroundColor != ""):
        #print(BackgroundColor)
        environment["background_screen_pointer"].fill(pygame.Color("black"))
    if (Message != ""):
        #print(displaytext)
        font = pygame.font.Font(None, 100)
        text = font.render(Message, 1, (227, 157, 200))
        textpos = text.get_rect()
        textpos.centerx = environment["background_screen_pointer"].get_rect().centerx
        textpos.centery = environment["background_screen_pointer"].get_rect().centery
        if(ImageShowed):
            environment["background_screen_picture_pointer"].blit(text, textpos)
        else:
            environment["background_screen_pointer"].blit(text, textpos)

    if (Numeral != ""):
        #print(displaytext)
        font = pygame.font.Font(None, 800)
        text = font.render(Numeral, 1, (227, 157, 200))
        textpos = text.get_rect()
        textpos.centerx = environment["background_screen_pointer"].get_rect().centerx
        textpos.centery = environment["background_screen_pointer"].get_rect().centery
        if(ImageShowed):
            environment["background_screen_picture_pointer"].blit(text, textpos)
        else:
            environment["background_screen_pointer"].blit(text, textpos)

    if (CountDownPhoto != ""):
        #print(displaytext)
        font = pygame.font.Font(None, 500)
        text = font.render(CountDownPhoto, 1, (227, 157, 200))
        textpos = text.get_rect()
        textpos.centerx = environment["background_screen_pointer"].get_rect().centerx
        textpos.centery = environment["background_screen_pointer"].get_rect().centery
        if(ImageShowed):
            environment["background_screen_picture_pointer"].blit(text, textpos)
        else:
            environment["background_screen_pointer"].blit(text, textpos)

    if(ImageShowed == True):
        environment["screen_picture_pointer"].blit(environment["background_screen_picture_pointer"], (0, 0))
    else:
        environment["screen_pointer"].blit(environment["background_screen_pointer"], (0, 0))

    pygame.display.flip()
    return


def ShowPicture(environment, file, delay):
    global pygame
    global screenPicture
    global ImageShowed
    environment["background_screen_picture_pointer"].fill((0, 0, 0))
    img = pygame.image.load(file)
    # Make the image full screen
    img = pygame.transform.scale(img, environment["screen_picture_pointer"].get_size())
    #environment["background_screen_picture_pointer"].set_alpha(200)
    environment["background_screen_picture_pointer"].blit(img, (0,0))
    environment["screen_pointer"].blit(environment["background_screen_picture_pointer"], (0, 0))
    pygame.display.flip()  # update the display
    ImageShowed = True
    time.sleep(delay)

# display one image on screen
def show_image(environment, image_path):
    environment["screen_pointer"].fill(pygame.Color("white")) # clear the screen
    img = pygame.image.load(image_path) # load the image
    img = img.convert()	
    set_dimensions(environment, img.get_width(), img.get_height()) # set pixel dimensions based on image
    x = (environment["screen_w"] / 2) - (img.get_width() / 2)
    y = (environment["screen_h"] / 2) - (img.get_height() / 2)
    environment["screen_pointer"].blit(img, (x, y))
    pygame.display.flip()

def CapturePicture(environment):
    global imagecounter
    global Numeral
    global Message
    global screen
    global screenPicture
    global pygame
    global ImageShowed
    global CountDownPhoto
    global BackgroundColor

    BackgroundColor = ""
    Numeral = ""
    Message = ""
    UpdateDisplay(environment)
    time.sleep(1)
    CountDownPhoto = ""
    UpdateDisplay(environment)
    environment["background_screen_pointer"].fill(pygame.Color("black"))
    environment["screen_pointer"].blit(environment["background_screen_pointer"], (0, 0))
    pygame.display.flip()
    environment["camera_pointer"].start_preview()
    BackgroundColor = "black"

    for x in range(3, -1, -1):
        if x == 0:
            Numeral = ""
            Message = "PRENEZ LA POSE"
        else:
            Numeral = str(x)
            Message = ""
        UpdateDisplay(environment)
        time.sleep(1)

    BackgroundColor = ""
    Numeral = ""
    Message = ""
    UpdateDisplay(environment)
    imagecounter = imagecounter + 1
    ts = time.time()
    filename = os.path.join(environment["output_photos_folder"], str(imagecounter)+"_"+str(ts) + '.png')
    environment["camera_pointer"].capture(filename, resize=(IMAGE_WIDTH, IMAGE_HEIGHT))
    environment["camera_pointer"].stop_preview()
    ShowPicture(environment, filename, 2)
    ImageShowed = False
    return filename

def TakePictures(environment):
    global imagecounter
    global Numeral
    global Message
    global screen
    global pygame
    global ImageShowed
    global CountDownPhoto
    global BackgroundColor
    global Printing
    global PhotosPerCart
    global TotalImageCount

    input(pygame.event.get())
    CountDownPhoto = "1/3"
    filename1 = CapturePicture(environment)

    CountDownPhoto = "2/3"
    filename2 = CapturePicture(environment)

    CountDownPhoto = "3/3"
    filename3 = CapturePicture(environment)

    CountDownPhoto = ""
    Message = "Attendez svp..."
    UpdateDisplay(environment)

    image1 = PIL.Image.open(filename1)
    image2 = PIL.Image.open(filename2)
    image3 = PIL.Image.open(filename3)
    TotalImageCount = TotalImageCount + 1

    background_image = PIL.Image.open(environment["template_path"])
    background_image.paste(image1, (625, 30))
    background_image.paste(image2, (625, 410))
    background_image.paste(image3, (55, 410))
    # Create the final filename
    ts = time.time()
    Final_Image_Name = os.path.join(environment["output_montages_photos_folder"], "Final_" + str(TotalImageCount)+"_"+str(ts) + ".png")
    # Save it to the usb drive
    background_image.save(Final_Image_Name)
    # Save a temp file, its faster to print from the pi than usb
    background_image.save(environment["tmp_photo_print_path"])
    ShowPicture(environment, environment["tmp_photo_print_path"], 3)
    background_image2 = background_image.rotate(90)
    background_image2.save(environment["tmp_photo_print_path"])
    ImageShowed = False
    Message = "Appuyez sur le bouton pour imprimer"
    UpdateDisplay(environment)
    time.sleep(1)
    Message = ""
    UpdateDisplay(environment)
    Printing = False
    WaitForPrintingEvent(environment)
    Numeral = ""
    Message = ""
    print("Printing:"+str(Printing))
    if Printing:
        #Todo handle here
        if (TotalImageCount <= PhotosPerCart) and ENABLE_PRINTING:
            if os.path.isfile(environment["tmp_photo_print_path"]):
                # Open a connection to cups
                conn = cups.Connection()
                # get a list of printers
                printers = conn.getPrinters()
                # select printer 0
                printer_name = printers.keys()[0]
                Message = "Impression en cours..."
                UpdateDisplay(environment)
                time.sleep(1)
                # print the buffer file
                printqueuelength = len(conn.getJobs())
                if printqueuelength > 1:
                    ShowPicture(environment, environment["tmp_photo_print_path"], 3)
                    conn.enablePrinter(printer_name)
                    Message = "Impression impossible"
                    UpdateDisplay(environment)
                    time.sleep(1)
                else:
                    conn.printFile(printer_name, environment["tmp_photo_print_path"], "PhotoBooth", {})
                    time.sleep(40)
        else:
            Message = "Nous vous enverrons vos photos"
            Numeral = ""
            UpdateDisplay(environment)
            time.sleep(1)
            
    Message = ""
    Numeral = ""
    ImageShowed = False
    UpdateDisplay(environment)
    time.sleep(1)

def MyCallback(environment, channel):
    global Printing
    GPIO.remove_event_detect(environment["bp_to_launch"])
    Printing = True

def WaitForPrintingEvent(environment):
    global BackgroundColor
    global Numeral
    global Message
    global Printing
    global pygame
    countDown = 5
    GPIO.add_event_detect(environment["bp_to_launch"], GPIO.RISING)
    GPIO.add_event_callback(environment["bp_to_launch"], MyCallback)
    
    while Printing == False and countDown > 0:
        if Printing == True:
            return
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_DOWN:
                    GPIO.remove_event_detect(environment["bp_to_launch"])
                    Printing = True
                    return        
        BackgroundColor = ""
        Numeral = str(countDown)
        Message = ""
        UpdateDisplay(environment)
        countDown = countDown - 1
        time.sleep(1)

    GPIO.remove_event_detect(environment["bp_to_launch"])

def WaitForEvent():
    global pygame
    NotEvent = True
    while NotEvent:
        input_state = GPIO.input(environment["bp_to_launch"])
        if input_state == False:
            NotEvent = False
            return
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                if event.key == pygame.K_DOWN:
                    NotEvent = False
                    return
        time.sleep(0.2)

def main(threadName, *args):
    setup_pygame(environment)
    InitFolder(environment)
    setup_rpi_gpio(environment)
    setup_rpi_camera(environment)
    while True:
        show_image(environment, 'images/start_camera.jpg')
        WaitForEvent()
        time.sleep(0.2)
        TakePictures(environment)
    GPIO.cleanup()

# launch the main thread
Thread(target=main, args=('Main', 1)).start()


def my_main(args):
    """Main function."""
    #
def parse_arguments():
    """Parse arguments function."""
    parser = argparse.ArgumentParser(
        description="simple script to print something"
    )

    parser.add_argument(
        '-m', '--message',
        help="message to print",
        type=str,
        default="hello world"
    )
    parser.add_argument(
        '-c', '--count',
        help="number of time to print the message, default:1",
        type=int,
        default=1
    )
    parser.add_argument(
        "-v", "--verbose",
        action='store_true',
        help="""Make the application talk!"""
    )
    return parser.parse_args()

if __name__ == '__main__':
    try:
        # instruction qui risque de lever une erreur
        ARGUMENTS = parse_arguments()
        if ARGUMENTS.verbose:
            #warning by default
            lg.basicConfig(level=lg.DEBUG)
        #import pdb; pdb.set_trace()
    except Exception as e_h:
        lg.error('If any exception occured ... here I AM ')
        lg.critical("The exception is: %s", e_h)
    except:
        # Instruction exécutée dans le cas d'une autre erreur
        lg.warning('Une autre erreur est survenue')
    else:
        # Instruction exécutée si l'instruction dans try est vraie
        lg.debug("Going to launch something")
        my_main(ARGUMENTS)
    finally:
        # Instruction exécutée dans tous les cas
        lg.info("Fin")
