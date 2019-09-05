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
import threading
import time
import os
import subprocess
import PIL.Image
#import cups
import RPi.GPIO as GPIO

from pygame.locals import *
from time import sleep
from PIL import Image, ImageDraw

EVENT_NO_TYPE = 0
EVENT_TYPE_TAKE_PICTURE = 1
EVENT_TYPE_SHOW_LAST_PICTURE = 2
EVENT_TYPE_BROWSE_PICTURES = 3
EVENT_TYPE_RESTART = 4
EVENT_TYPE_STOP = 5

SECONDS_TO_WAIT_TO_SHOW_PICTURE_READY_TO_PRINT = 5

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

def init_environment():
    """Function that initialize environment"""
    environment = {}
    environment["output_photos_folder"] = "output_photos"
    environment["output_montages_photos_folder"] = "output_photos/montages"
    environment["tmp_photo_print_path"] = "/tmp/tempprint.png"
    environment["template_path"] = "images/template.png"
    environment["last_taken_picture_path"] = None
    result = subprocess.check_output("ls -lat "+str(environment["output_montages_photos_folder"])+"  | head -2 | tail -1 | awk '{print $9}'", shell=True)
    if result:
        environment["last_taken_picture_path"]=environment["output_montages_photos_folder"]+"/"+result.rstrip()

    #GPIO to use for the BP browse pictures
    environment["bp_to_launch_browse_pictures"] = 23
    #GPIO to use for the BP take picture
    environment["bp_to_launch_take_picture"] = 24
    #GPIO to use for the BP show last picture
    environment["bp_to_launch_show_last_picture"] = 25
    #GPIO to use for restarting the system
    environment["bp_to_restart"] = 26

    environment["camera_parameters"] = {}
    environment["camera_parameters"]["resolution"] = 1920, 1080
    environment["camera_parameters"]["rotation"] = 0
    environment["camera_parameters"]["hflip"] = False
    environment["camera_parameters"]["vflip"] = False
    #environment["camera_parameters"]["brightness"] = 50
    environment["camera_parameters"]["preview_alpha"] = 120
    environment["camera_parameters"]["preview_fullscreen"] = True
    environment["camera_parameters"]["video_stabilization"] = True
    environment["camera_pointer"] = None

    environment["picture_for_pasting_width"] = 550
    environment["picture_for_pasting_height"] = 360

    environment["montage_rebord"] = 30

    return environment

ImageShowed = False
Printing = False

def compute_picture_size_and_position(environment):
    """ Compute picture size and position to fit the screen """
    environment["picture_for_pasting_width"] = (environment["screen_w"] - (3 * environment["montage_rebord"]) ) /2
    environment["picture_for_pasting_height"] = (environment["screen_h"] - (3 * environment["montage_rebord"]) ) /2

    delta_x = environment["picture_for_pasting_width"] + (2 * environment["montage_rebord"])
    delta_y = environment["montage_rebord"]
    environment["picture_for_pasting_pos1"] = (delta_x, delta_y)
    delta_y = environment["picture_for_pasting_height"] + (2 * environment["montage_rebord"])
    environment["picture_for_pasting_pos2"] = (delta_x, delta_y)
    delta_x = environment["montage_rebord"]
    environment["picture_for_pasting_pos3"] = (delta_x, delta_y)

    lg.info("picture_for_pasting_width:"+str(environment["picture_for_pasting_width"]))
    lg.info("picture_for_pasting_height:"+str(environment["picture_for_pasting_height"]))
    lg.info("picture_for_pasting_pos1:"+str(environment["picture_for_pasting_pos1"]))
    lg.info("picture_for_pasting_pos2:"+str(environment["picture_for_pasting_pos2"]))
    lg.info("picture_for_pasting_pos3:"+str(environment["picture_for_pasting_pos3"]))

def setup_pygame(environment):
    """ Setup pygame environment """
    # Load the background template

    # initialise pygame
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

def unsetup_rpi_camera(environment):
    """ Unset up RPI camera"""
    if environment["camera_pointer"]:
        environment["camera_pointer"].close()

def setup_rpi_camera(environment):
    """ Set up RPI camera"""
    environment["camera_pointer"] = picamera.PiCamera()
    lg.info("We have initialized picamera")
    # Initialise the camera object
    environment["camera_pointer"].resolution = environment["camera_parameters"]["resolution"]
    environment["camera_pointer"].rotation = environment["camera_parameters"]["rotation"]
    environment["camera_pointer"].hflip = environment["camera_parameters"]["hflip"]
    environment["camera_pointer"].vflip = environment["camera_parameters"]["vflip"]
    #environment["camera_pointer"].brightness = environment["camera_parameters"]["brightness"]
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
    environment["camera_pointer"].video_stabilization = environment["camera_parameters"]["video_stabilization"]

def setup_rpi_gpio(environment):
    """ The RPI GPIO setup"""
    #Setup GPIO for BP
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(environment["bp_to_launch_browse_pictures"], GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(environment["bp_to_launch_take_picture"], GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(environment["bp_to_launch_show_last_picture"], GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(environment["bp_to_restart"], GPIO.IN, pull_up_down=GPIO.PUD_UP)

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

def init_folders(environment):

    update_display(environment, "", "Verification des dossiers", "", "", False)

    #check image folder existing, create if not exists
    if not os.path.isdir(environment["output_photos_folder"]):
        os.makedirs(environment["output_photos_folder"])

    if not os.path.isdir(environment["output_montages_photos_folder"]):
        os.makedirs(environment["output_montages_photos_folder"])

def UpdateDisplay(environment):
    global BackgroundColor
    global Numeral
    global Message
    global CountDownPhoto
    global ImageShowed

    display_config = {}
    display_config["background_color"] = BackgroundColor
    display_config["message"] = Message
    display_config["numeral"] = Numeral
    display_config["count_down_photo"] = CountDownPhoto
    display_config["image_showed"] = ImageShowed
    update_display(environment, BackgroundColor, Message, Numeral, CountDownPhoto, ImageShowed)

def update_display(environment, BackgroundColor, Message, Numeral, CountDownPhoto, ImageShowed):

    environment["background_screen_pointer"].fill(pygame.Color("white"))  # White background

    if BackgroundColor != "":
        #print(BackgroundColor)
        environment["background_screen_pointer"].fill(pygame.Color("black"))
    if Message != "":
        #print(displaytext)
        font = pygame.font.Font(None, 100)
        text = font.render(Message, 1, (227, 157, 200))
        textpos = text.get_rect()
        textpos.centerx = environment["background_screen_pointer"].get_rect().centerx
        textpos.centery = environment["background_screen_pointer"].get_rect().centery
        if Numeral != "":
            textpos.centery -= 300
        elif CountDownPhoto != "":
            textpos.centery -= 200
        if(ImageShowed):
            environment["background_screen_picture_pointer"].blit(text, textpos)
        else:
            environment["background_screen_pointer"].blit(text, textpos)

    if Numeral != "":
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

    if CountDownPhoto != "":
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

    if ImageShowed == True:
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
    environment["background_screen_picture_pointer"].blit(img, (0, 0))
    environment["screen_pointer"].blit(environment["background_screen_picture_pointer"], (0, 0))
    pygame.display.flip()  # update the display
    ImageShowed = True
    time.sleep(delay)

def show_image(environment, image_path):
    """Display an image on full screen"""
    environment["screen_pointer"].fill(pygame.Color("white")) # clear the screen
    img = pygame.image.load(image_path) # load the image
    img = img.convert()
    set_dimensions(environment, img.get_width(), img.get_height()) # set pixel dimensions based on image
    x = (environment["screen_w"] / 2) - (img.get_width() / 2)
    y = (environment["screen_h"] / 2) - (img.get_height() / 2)
    environment["screen_pointer"].blit(img, (x, y))
    pygame.display.flip()

def print_event(value):
    """Print event value"""
    if value == EVENT_TYPE_STOP:
        print("EVENT_TYPE_STOP:"+str(value))
        return
    if value == EVENT_TYPE_TAKE_PICTURE:
        print("EVENT_TYPE_TAKE_PICTURE:"+str(value))
        return
    if value == EVENT_TYPE_SHOW_LAST_PICTURE:
        print("EVENT_TYPE_SHOW_LAST_PICTURE:"+str(value))
        return
    if value == EVENT_TYPE_BROWSE_PICTURES:
        print("EVENT_TYPE_BROWSE_PICTURES:"+str(value))
        return
    if value == EVENT_TYPE_RESTART:
        print("EVENT_TYPE_RESTART:"+str(value))
        return
    if value == EVENT_TYPE_STOP:
        print("EVENT_TYPE_STOP:"+str(value))
        return
    print("EVENT_NO_TYPE:"+str(value))

def wait_for_event(environment):
    global pygame
    while True:
        if not GPIO.input(environment["bp_to_launch_browse_pictures"]):
            return EVENT_TYPE_BROWSE_PICTURES
        if not GPIO.input(environment["bp_to_launch_take_picture"]):
            return EVENT_TYPE_TAKE_PICTURE
        if not GPIO.input(environment["bp_to_launch_show_last_picture"]):
            return EVENT_TYPE_SHOW_LAST_PICTURE
        if not GPIO.input(environment["bp_to_restart"]):
            return EVENT_TYPE_RESTART
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return EVENT_TYPE_STOP
                elif event.key == pygame.K_F1:
                    return EVENT_TYPE_TAKE_PICTURE
                elif event.key == pygame.K_F2:
                    return EVENT_TYPE_SHOW_LAST_PICTURE
                elif event.key == pygame.K_F3:
                    return EVENT_TYPE_BROWSE_PICTURES
                elif event.key == pygame.K_F4:
                    return EVENT_TYPE_RESTART
                elif event.key == pygame.K_F5:
                    return EVENT_TYPE_STOP
                elif event.key == pygame.K_DOWN:
                    return EVENT_TYPE_TAKE_PICTURE
        time.sleep(0.1)
    return EVENT_NO_TYPE

def wait_for_allow_printing_event(environment, seconds_to_wait):
    """Wait for button press to allow to print image"""

    count_down_cent_milliseconds = seconds_to_wait*10
    while count_down_cent_milliseconds:
        if count_down_cent_milliseconds % 10:
            #update_display(environment, "", "Appuyez sur le bouton pour imprimer", "", str(int(count_down_cent_milliseconds/10)+1), False)
            update_display(environment, "", "Appuyez sur le bouton pour imprimer", str(int(count_down_cent_milliseconds/10)+1), "", False)
        if not GPIO.input(environment["bp_to_launch_take_picture"]):
            return True
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_DOWN:
                    return True
        time.sleep(0.1)
        count_down_cent_milliseconds -= 1
    return False

def print_picture(environment, filepath):
    """Print the filepath picture"""
    lg.info("Seems like printing has been asked")
    #Todo handle here
    if ENABLE_PRINTING:
        if os.path.isfile(filepath):
            # Open a connection to cups
            conn = cups.Connection()
            # get a list of printers
            printers = conn.getPrinters()
            # select printer 0
            printer_name = printers.keys()[0]
            update_display(environment, "", "Impression en cours...", "", "", False)
            time.sleep(1)
            # print the buffer file
            printqueuelength = len(conn.getJobs())
            if printqueuelength > 1:
                ShowPicture(environment, filepath, 3)
                conn.enablePrinter(printer_name)
                update_display(environment, "", "!! Impression impossible !!", "", "", False)
                time.sleep(1)
                update_display(environment, "", "Nous vous enverrons vos photos...", "", "", False)
                time.sleep(1)
            else:
                conn.printFile(printer_name, filepath, "PhotoBooth", {})
                time.sleep(40)
    else:
        update_display(environment, "", "!! Impression desactivee !!", "", "", False)
        time.sleep(1)
        update_display(environment, "", "Nous vous enverrons vos photos...", "", "", False)
        time.sleep(1)

def take_a_picture(environment, part):

    update_display(environment, "", "", "", str(part), False)
    time.sleep(1)

    update_display(environment, "", "", "", "", False)

    environment["background_screen_pointer"].fill(pygame.Color("black"))
    environment["screen_pointer"].blit(environment["background_screen_pointer"], (0, 0))
    #To see you correctly ??
    pygame.display.flip()
    environment["camera_pointer"].start_preview()

    for x in range(3, -1, -1):
        if x == 0:
            update_display(environment, "black", "PRENEZ LA POSE ", "", "", False)
        else:
            update_display(environment, "black", "PREPAREZ VOUS A PRENDRE LA POSE ("+str(part)+")", "", str(x), False)
        time.sleep(1)

    update_display(environment, "", "", "", "", False)
    ts = time.strftime('%Y%m%d_%H%M%S', time.localtime())
    filename_without_extension = os.path.join(environment["output_photos_folder"],str(ts)+'-photo')
    filename = filename_without_extension+".jpg"
    #filename = filename_without_extension+".png"
    environment["camera_pointer"].capture(filename, 'jpeg', use_video_port=True)
    environment["camera_pointer"].stop_preview()
    ShowPicture(environment, filename, 2)
    return filename

def creation_montage(environment, filename1, filename2, filename3):
    """Creation du montage photo"""
    image1 = PIL.Image.open(filename1).resize((environment["picture_for_pasting_width"], environment["picture_for_pasting_height"]))
    image1 = image1.resize((environment["picture_for_pasting_width"], environment["picture_for_pasting_height"]))
    image2 = PIL.Image.open(filename2).resize((environment["picture_for_pasting_width"], environment["picture_for_pasting_height"]))
    #image2 = image2.resize((environment["picture_for_pasting_width"], environment["picture_for_pasting_height"]))
    image3 = PIL.Image.open(filename3).resize((environment["picture_for_pasting_width"], environment["picture_for_pasting_height"]))
    #image3 = image3.resize((environment["picture_for_pasting_width"], environment["picture_for_pasting_height"]))

    background_image = PIL.Image.open(environment["template_path"])
    #background_image.paste(image1, (625, 30))
    #background_image.paste(image2, (625, 410))
    #background_image.paste(image3, (55, 410))

    background_image.paste(image1, environment["picture_for_pasting_pos1"])
    background_image.paste(image2, environment["picture_for_pasting_pos2"])
    background_image.paste(image3, environment["picture_for_pasting_pos3"])

    # Create the final filename
    ts = time.strftime('%Y%m%d_%H%M%S', time.localtime())
    montage_filename = os.path.join(environment["output_montages_photos_folder"], str(ts)+"-montage.png")
    # Save it to the usb drive
    background_image.save(montage_filename)
    return montage_filename

def take_pictures(environment):
    """Function that handle the scenario take a picture"""
    lg.info("SCENARIO : Take pictures")
    update_display(environment, "", "C EST PARTI POUR 3 PHOTOS", "", "", False)
    time.sleep(1)
    filename1 = take_a_picture(environment, "1/3")
    filename2 = take_a_picture(environment, "2/3")
    filename3 = take_a_picture(environment, "3/3")

    update_display(environment, "", "Montage en cours ...", "", "", False)


    # Save a temp file, its faster to print from the pi than usb
    environment["last_taken_picture_path"] = creation_montage(environment, filename1, filename2, filename3)

    show_image(environment, environment["last_taken_picture_path"])
    time.sleep(SECONDS_TO_WAIT_TO_SHOW_PICTURE_READY_TO_PRINT)
    printing_asked = wait_for_allow_printing_event(environment, 5)
    lg.info("printing_asked:"+str(printing_asked))
    if printing_asked:
        print_picture(environment, environment["last_taken_picture_path"])

def show_last_picture(environment):
    """Function that handle the scenario take a picture"""
    lg.info("SCENARIO : Show last picture")
    if environment["last_taken_picture_path"]:
        if False:
            ShowPicture(environment, environment["last_taken_picture_path"], SECONDS_TO_WAIT_TO_SHOW_PICTURE_READY_TO_PRINT)
        else:
            show_image(environment, environment["last_taken_picture_path"])
            time.sleep(SECONDS_TO_WAIT_TO_SHOW_PICTURE_READY_TO_PRINT)

        #ShowPicture(environment, environment["last_taken_picture_path"], 1)
        printing_asked = wait_for_allow_printing_event(environment, 5)
        lg.info("printing_asked:"+str(printing_asked))
        if printing_asked:
            print_picture(environment, environment["last_taken_picture_path"])
    else:
        lg.warning("No picture taken yet=>Take one !")

def browse_pictures(environment):
    """Function that handle the scenario take a picture"""
    lg.info("SCENARIO : Browse pictures")

def main_pygame(environment):

    while True:
        show_image(environment, 'images/start_camera.jpg')
        event_get = wait_for_event(environment)
        print_event(event_get)
        time.sleep(0.2)
        if event_get == EVENT_NO_TYPE:
            lg.warning("No event ?!")
        elif event_get == EVENT_TYPE_TAKE_PICTURE:
            take_pictures(environment)
        elif event_get == EVENT_TYPE_SHOW_LAST_PICTURE:
            show_last_picture(environment)
        elif event_get == EVENT_TYPE_BROWSE_PICTURES:
            browse_pictures(environment)
        elif event_get == EVENT_TYPE_RESTART:
            lg.info("Ask to restart the board")
            return
        elif event_get == EVENT_TYPE_STOP:
            lg.critical("Ask to stop the application")
            return
        else:
            lg.critical("We do not know the event : "+str(event_get))

    GPIO.cleanup()

class LaunchThread(threading.Thread):
    """ Class function that will handle running function in threading mode"""
    def __init__(self, target, *args):
        self.target = target
        self.args = args
        threading.Thread.__init__(self)

    def run(self):
        lg.info("!!!!!!!!!!!!!!!!! BEGIN !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        lg.info("Going to call in thread the function:"+str(self.target))
        self.target(*self.args)
        lg.info("!!!!!!!!!!!!!!!!!! END !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

def my_main(main_args):
    """Main function."""
    #
    # launch the main thread

    lg.info("camera capture in :"+str(main_args.width)+"x"+str(main_args.height))
    pygame.init()  # Initialise pygame
    environment = init_environment()
    setup_pygame(environment)
    init_folders(environment)
    setup_rpi_gpio(environment)
    setup_rpi_camera(environment)
    compute_picture_size_and_position(environment)
    main_thread = LaunchThread(main_pygame, environment)
    main_thread.start()
    main_thread.join()
    unsetup_rpi_camera(environment)
    pygame.quit()

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
        '-a', '--height',
        help="camera width capture, default:1",
        type=int,
        default=1080
    )
    parser.add_argument(
        '-b', '--width',
        help="camera width capture, default:1",
        type=int,
        default=1920
    )
    parser.add_argument(
        '-l', '--log',
        help="logging output",
        type=str,
        default=None
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
        #THE_DEBUG_FORMAT = '%(relativeCreated)6d %(threadName)s %(message)s'
        THE_DEBUG_FORMAT = '%(asctime)s:%(levelname)s-%(message)s'
        THE_DEBUG_FILENAME = ARGUMENTS.log
        THE_DEBUG_LEVEL = lg.INFO
        if ARGUMENTS.verbose:
            THE_DEBUG_LEVEL = lg.DEBUG
        lg.basicConfig(filename=THE_DEBUG_FILENAME, level=THE_DEBUG_LEVEL, format=THE_DEBUG_FORMAT)
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
