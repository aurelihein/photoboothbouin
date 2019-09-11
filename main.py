#!!/usr/bin/python3
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

#To start it automatically at start, think about adding sudo crontab -e @reboot ...

"""
Program that display something
"""

#1.0.0 : Version initial

VERSION = "1.0.0"

ENABLE_PRINTING = True

import argparse
import logging as lg
import threading
import time
import os
import subprocess
import glob
from shutil import copyfile
import PIL.Image
from PIL import Image, ImageDraw
import pygame
from pygame.locals import *
import cups
import RPi.GPIO as GPIO
import picamera

EVENT_NO_TYPE = 0
EVENT_TYPE_TAKE_PICTURE = 1
EVENT_TYPE_SHOW_LAST_PICTURE = 2
EVENT_TYPE_BROWSE_PICTURES = 3
EVENT_TYPE_RESTART = 4
EVENT_TYPE_STOP = 5

SECONDS_TO_WAIT_TO_SHOW_PICTURE_READY_TO_PRINT = 5
SECONDS_TO_WAIT_TO_SHOW_PICTURE_AFTER_A_SHOOT = 2
SECONDS_TO_WAIT_IN_BROWSING_MODE = 5

def get_all_montages(environment):
    """Get all montages files"""
    #return subprocess.check_output("ls -lat "+str(environment["output_montages_photos_folder"])+" | grep -v d | awk '{print $9}'", shell=True)
    files = list(filter(os.path.isfile, glob.glob(environment["output_montages_photos_folder"] + "/*")))
    files.sort(key=lambda x: os.path.getmtime(x))
    return files

def init_environment(main_args):
    """Function that initialize environment"""
    environment = {}
    environment["output_base_save_dir"] = "/media/pi/aurelienhd/"
    environment["start_picture_filename"] = '/tmp/start_camera.jpg'
    environment["original_start_picture_filename"] = 'images/start_camera.jpg'
    environment["background_browse_filename"] = 'images/browse_background.jpg'
    environment["output_photos_folder"] = environment["output_base_save_dir"]+"output_photos/singles_photos"
    environment["output_montages_photos_folder"] = environment["output_base_save_dir"]+"output_photos/montages"
    environment["tmp_photo_print_path"] = "/tmp/tempprint.png"
    environment["template_path"] = "images/template.png"
    environment["start_sound"] = "sounds/polaroid.wav"
    environment["shoot_sound"] = "sounds/double_shoots.wav"
    environment["buzz_sound"] = "sounds/buzz.wav"
    environment["page_flip_sound"] = "sounds/page_flip.wav"
    environment["page_flip_sound_back"] = "sounds/page_flip_back.wav"

    environment["printer_selected"] = "hp_locale"
    environment["printer_options"] = {'media':'A6', 'print-quality':'4'}
    environment["printer_tmp_filepath"] = "/tmp/to_be_printed.png"
    #-o print-quality=3
    #-o print-quality=4
    #-o print-quality=5
    #Specifies the output quality - draft (3), normal (4), or best (5).
    environment["reboot_enabled"] = main_args.reboot
    if environment["reboot_enabled"]:
        lg.warning("Reboot is enabled")
    else:
        lg.info("Reboot is disabled")
    environment["printer_enabled"] = main_args.printer
    if environment["printer_enabled"]:
        lg.warning("Printer is enabled")
    else:
        lg.info("Printer is disabled")
    environment["last_taken_picture_path"] = None

    #GPIO to use for relay of spot left
    environment["relay_spot_left"] = 17

    #GPIO to use for relay of spot right
    environment["relay_spot_right"] = 18

    #GPIO to use for relay of unknown function
    environment["relay_unknown"] = 19

    #GPIO to use for relay of BP browse pictures
    environment["relay_bp_to_launch_browse_pictures"] = 20

    #GPIO to use for relay of BP take pictures
    environment["relay_bp_to_launch_take_pictures"] = 21

    #GPIO to use for relay of BP show last picture
    environment["relay_bp_to_launch_show_last_picture"] = 22

    #GPIO to use for the BP browse pictures
    environment["bp_to_launch_browse_pictures"] = 23
    #GPIO to use for the BP take pictures
    environment["bp_to_launch_take_pictures"] = 24
    #GPIO to use for the BP show last picture
    environment["bp_to_launch_show_last_picture"] = 25
    #GPIO to use for restarting the system
    environment["bp_to_restart"] = 26

    environment["camera_parameters"] = {}
    environment["camera_parameters"]["resolution"] = 1920, 1080
    environment["camera_parameters"]["framerate"] = 30
    environment["camera_parameters"]["rotation"] = 0
    environment["camera_parameters"]["hflip"] = False
    environment["camera_parameters"]["vflip"] = False
    #environment["camera_parameters"]["brightness"] = 50
    environment["camera_parameters"]["preview_alpha"] = 120
    environment["camera_parameters"]["preview_fullscreen"] = True
    environment["camera_parameters"]["video_stabilization"] = True
    environment["camera_pointer"] = None

    #Now computed depending on montage_rebord
    environment["picture_for_pasting_width"] = 550
    environment["picture_for_pasting_height"] = 360

    environment["montage_rebord"] = 30
    environment["browsing_down_up_bar"] = 50

    environment["last_picture_pos_start_in_start_screen"] = (1410, 526)
    environment["last_picture_pos_end_in_start_screen"] = (1808, 770)
    environment["picture_for_pasting_width_start_screen"] = 0
    environment["picture_for_pasting_height_start_screen"] = 0

    result = get_all_montages(environment)
    if result:
        environment["last_taken_picture_path"] = result[-1]

    return environment

def compute_picture_size_and_position(environment):
    """ Compute picture size and position to fit the screen """
    environment["picture_for_pasting_width"] = int((environment["screen_w"] - (3 * environment["montage_rebord"])) /2)
    environment["picture_for_pasting_height"] = int((environment["screen_h"] - (3 * environment["montage_rebord"])) /2)

    delta_x = int(environment["picture_for_pasting_width"] + (2 * environment["montage_rebord"]))
    delta_y = int(environment["montage_rebord"])
    environment["picture_for_pasting_pos1"] = (delta_x, delta_y)
    delta_y = int(environment["picture_for_pasting_height"] + (2 * environment["montage_rebord"]))
    environment["picture_for_pasting_pos2"] = (delta_x, delta_y)
    delta_x = int(environment["montage_rebord"])
    environment["picture_for_pasting_pos3"] = (delta_x, delta_y)

    environment["picture_for_pasting_width_start_screen"] = int(environment["last_picture_pos_end_in_start_screen"][0] - environment["last_picture_pos_start_in_start_screen"][0])
    environment["picture_for_pasting_height_start_screen"] = int(environment["last_picture_pos_end_in_start_screen"][1] - environment["last_picture_pos_start_in_start_screen"][1])
    if False:
        lg.info("picture_for_pasting_width:"+str(environment["picture_for_pasting_width"]))
        lg.info("picture_for_pasting_height:"+str(environment["picture_for_pasting_height"]))
        lg.info("picture_for_pasting_pos1:"+str(environment["picture_for_pasting_pos1"]))
        lg.info("picture_for_pasting_pos2:"+str(environment["picture_for_pasting_pos2"]))
        lg.info("picture_for_pasting_pos3:"+str(environment["picture_for_pasting_pos3"]))
        lg.info("picture_for_pasting_width_start_screen:"+str(environment["picture_for_pasting_width_start_screen"]))
        lg.info("picture_for_pasting_height_start_screen:"+str(environment["picture_for_pasting_height_start_screen"]))

def setup_pygame(environment):
    """ Setup pygame environment """
    # Load the background template

    # initialise pygame
    pygame.mouse.set_visible(False) #hide the mouse cursor

    info_object = pygame.display.Info()
    environment["screen_w"] = info_object.current_w # save screen width
    environment["screen_h"] = info_object.current_h # save screen height

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

#https://github.com/contractorwolf/RaspberryPiPhotobooth
#gphoto2
#pkill gvfs

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
    environment["camera_pointer"].framerate = environment["camera_parameters"]["framerate"]
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

    environment["relay_spot_left"] = 17
    environment["relay_spot_right"] = 18
    environment["relay_unknown"] = 19
    environment["relay_bp_to_launch_browse_pictures"] = 20
    environment["relay_bp_to_launch_take_pictures"] = 21
    environment["relay_bp_to_launch_show_last_picture"] = 22

    GPIO.setwarnings(False)

    GPIO.setup(environment["relay_spot_left"], GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(environment["relay_spot_right"], GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(environment["relay_unknown"], GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(environment["relay_bp_to_launch_browse_pictures"], GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(environment["relay_bp_to_launch_take_pictures"], GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(environment["relay_bp_to_launch_show_last_picture"], GPIO.OUT, initial=GPIO.LOW)

    GPIO.setup(environment["bp_to_launch_browse_pictures"], GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(environment["bp_to_launch_take_pictures"], GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(environment["bp_to_launch_show_last_picture"], GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(environment["bp_to_restart"], GPIO.IN, pull_up_down=GPIO.PUD_UP)

def init_folders(environment):
    """init folders"""

    update_display(environment, "", "Verification des dossiers", "", "", False)

    #check image folder existing, create if not exists
    if not os.path.isdir(environment["output_photos_folder"]):
        os.makedirs(environment["output_photos_folder"])

    if not os.path.isdir(environment["output_montages_photos_folder"]):
        os.makedirs(environment["output_montages_photos_folder"])


def update_display(environment, background_color, the_message, the_number, count_down_photo, is_the_image_show):
    """Update display with text"""

    environment["background_screen_pointer"].fill(pygame.Color("white"))  # White background

    if background_color != "":
        #print(background_color)
        environment["background_screen_pointer"].fill(pygame.Color("black"))
    if the_message != "":
        #print(displaytext)
        font = pygame.font.Font(None, 100)
        text = font.render(the_message, 1, (227, 157, 200))
        textpos = text.get_rect()
        textpos.centerx = environment["background_screen_pointer"].get_rect().centerx
        textpos.centery = environment["background_screen_pointer"].get_rect().centery
        if the_number != "":
            textpos.centery -= 300
        elif count_down_photo != "":
            textpos.centery -= 200
        if is_the_image_show:
            environment["background_screen_picture_pointer"].blit(text, textpos)
        else:
            environment["background_screen_pointer"].blit(text, textpos)

    if the_number != "":
        #print(displaytext)
        font = pygame.font.Font(None, 800)
        text = font.render(the_number, 1, (227, 157, 200))
        textpos = text.get_rect()
        textpos.centerx = environment["background_screen_pointer"].get_rect().centerx
        textpos.centery = environment["background_screen_pointer"].get_rect().centery
        if is_the_image_show:
            environment["background_screen_picture_pointer"].blit(text, textpos)
        else:
            environment["background_screen_pointer"].blit(text, textpos)

    if count_down_photo != "":
        #print(displaytext)
        font = pygame.font.Font(None, 500)
        text = font.render(count_down_photo, 1, (227, 157, 200))
        textpos = text.get_rect()
        textpos.centerx = environment["background_screen_pointer"].get_rect().centerx
        textpos.centery = environment["background_screen_pointer"].get_rect().centery
        if is_the_image_show:
            environment["background_screen_picture_pointer"].blit(text, textpos)
        else:
            environment["background_screen_pointer"].blit(text, textpos)

    if is_the_image_show:
        environment["screen_picture_pointer"].blit(environment["background_screen_picture_pointer"], (0, 0))
    else:
        environment["screen_pointer"].blit(environment["background_screen_pointer"], (0, 0))

    pygame.display.flip()
    return

def show_image_with_size_and_pos(environment, image_path, width, height, pos_x, pos_y):
    """Display an image on full screen"""
    img = pygame.image.load(image_path) # load the image
    img = pygame.transform.scale(img, (width, height))
    img = img.convert()
    environment["screen_pointer"].blit(img, (pos_x, pos_y))
    pygame.display.flip()

def show_image(environment, image_path):
    """Display an image on full screen"""
    environment["screen_pointer"].fill(pygame.Color("white")) # clear the screen
    img = pygame.image.load(image_path) # load the image
    img = img.convert()
    delta_x = (environment["screen_w"] / 2) - (img.get_width() / 2)
    delta_y = (environment["screen_h"] / 2) - (img.get_height() / 2)
    environment["screen_pointer"].blit(img, (delta_x, delta_y))
    pygame.display.flip()

def print_event(value):
    """Print event value"""
    if value == EVENT_TYPE_STOP:
        lg.info("EVENT_TYPE_STOP:"+str(value))
        return
    if value == EVENT_TYPE_TAKE_PICTURE:
        lg.info("EVENT_TYPE_TAKE_PICTURE:"+str(value))
        return
    if value == EVENT_TYPE_SHOW_LAST_PICTURE:
        lg.info("EVENT_TYPE_SHOW_LAST_PICTURE:"+str(value))
        return
    if value == EVENT_TYPE_BROWSE_PICTURES:
        lg.info("EVENT_TYPE_BROWSE_PICTURES:"+str(value))
        return
    if value == EVENT_TYPE_RESTART:
        lg.info("EVENT_TYPE_RESTART:"+str(value))
        return
    if value == EVENT_TYPE_STOP:
        lg.info("EVENT_TYPE_STOP:"+str(value))
        return
    lg.info("EVENT_NO_TYPE:"+str(value))

def execute_relay_command_with_dict(what_to_do=None):
    """
    Function to turn off/on all relays
    what_to_do : {17:True, 18:False}
    """
    if what_to_do:
        for one in what_to_do.keys():
            GPIO.output(one, what_to_do[one])

def wait_for_event(environment, during_seconds):
    """Wait for BP events"""

    if not during_seconds:
        loop = True
    else:
        lg.debug("Will wait in event for "+str(during_seconds)+" sec")
        loop = int(during_seconds)*10
    while loop:
        if not GPIO.input(environment["bp_to_launch_browse_pictures"]):
            return EVENT_TYPE_BROWSE_PICTURES
        if not GPIO.input(environment["bp_to_launch_take_pictures"]):
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
        if not isinstance(loop, bool):
            loop -= 1
        time.sleep(0.1)
    return EVENT_NO_TYPE

def wait_for_allow_printing_event(environment, seconds_to_wait):
    """Wait for button press to allow to print image"""
    command_on = {}
    command_on[environment["relay_bp_to_launch_take_pictures"]] = True
    command_off = {}
    command_off[environment["relay_bp_to_launch_take_pictures"]] = False
    execute_relay_command_with_dict(command_on)

    count_down_cent_milliseconds = seconds_to_wait*10
    while count_down_cent_milliseconds:
        if count_down_cent_milliseconds % 10:
            #update_display(environment, "", "Appuyez sur le bouton pour imprimer", "", str(int(count_down_cent_milliseconds/10)+1), False)
            update_display(environment, "", "Appuyez sur le bouton pour imprimer", str(int(count_down_cent_milliseconds/10)+1), "", False)
        if not GPIO.input(environment["bp_to_launch_take_pictures"]):
            execute_relay_command_with_dict(command_off)
            return True
        if not GPIO.input(environment["bp_to_restart"]):
            execute_relay_command_with_dict(command_off)
            return False
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_DOWN:
                    execute_relay_command_with_dict(command_off)
                    return True
                if event.key == pygame.K_ESCAPE:
                    execute_relay_command_with_dict(command_off)
                    return False
        time.sleep(0.1)
        count_down_cent_milliseconds -= 1
    execute_relay_command_with_dict(command_off)
    return False

def print_picture(environment, filepath):
    """Print the filepath picture"""
    lg.info("Seems like printing has been asked")
    #Todo handle here
    if ENABLE_PRINTING and environment["printer_enabled"]:
        if os.path.isfile(filepath):
            # Open a connection to cups
            conn = cups.Connection()
            # get a list of printers
            printers = conn.getPrinters()
            # select printer 0
            printer_name = environment["printer_selected"]
            my_printer = printers.get(environment["printer_selected"], None)
            if my_printer is None:
                lg.critical("The printer "+str(printer_name)+" does not exists in list:"+str(printers.keys()))
                update_display(environment, "", "!! Impression impossible !!", "", "", False)
                time.sleep(1)
                update_display(environment, "", "Nous vous enverrons vos photos...", "", "", False)
                time.sleep(1)
            cups.setUser('pi')
            # print the buffer file
            printqueuelength = len(conn.getJobs())
            if printqueuelength > 1:
                play_a_sound(environment["buzz_sound"])
                #show_image(environment, filepath)
                #time.sleep(3)
                conn.enablePrinter(printer_name)
                update_display(environment, "", "!! Impression impossible !!", "", "", False)
                time.sleep(1)
                update_display(environment, "", "Nous vous enverrons vos photos...", "", "", False)
                time.sleep(1)
            else:
                update_display(environment, "", "Impression en cours...", "", "", False)
                tmp_filepath = creation_montage_to_print_a_format(filepath, environment["printer_tmp_filepath"])
                conn.printFile(printer_name, tmp_filepath, "PhotoBoothBouin", environment["printer_options"])
                time.sleep(20)
    else:
        play_a_sound(environment["buzz_sound"])
        update_display(environment, "", "!! Impression desactivee !!", "", "", False)
        time.sleep(1)
        update_display(environment, "", "Nous vous enverrons vos photos...", "", "", False)
        time.sleep(1)

def take_a_picture(environment, part):
    """Take a picture"""

    command_on = {}
    command_on[environment["relay_spot_left"]] = True
    command_on[environment["relay_spot_right"]] = True
    command_off = {}
    command_off[environment["relay_spot_left"]] = False
    command_off[environment["relay_spot_right"]] = False

    update_display(environment, "", "", "", str(part), False)
    time.sleep(1)
    update_display(environment, "", "", "", "", False)
    environment["background_screen_pointer"].fill(pygame.Color("black"))
    environment["screen_pointer"].blit(environment["background_screen_pointer"], (0, 0))
    #To see you correctly ??
    pygame.display.flip()
    environment["camera_pointer"].start_preview()

    for one in range(3, -1, -1):
        if one == 0:
            update_display(environment, "black", "PRENEZ LA POSE ", "", "", False)
        else:
            update_display(environment, "black", "PREPAREZ VOUS A PRENDRE LA POSE ("+str(part)+")", "", str(one), False)
            time.sleep(1)

    execute_relay_command_with_dict(command_on)
    time.sleep(0.3)
    execute_relay_command_with_dict(command_off)
    time.sleep(0.3)

    update_display(environment, "", "", "", "", False)
    timestamp = time.strftime('%Y%m%d_%H%M%S', time.localtime())
    filename = os.path.join(environment["output_photos_folder"], str(timestamp)+'-photo.jpg')
    execute_relay_command_with_dict(command_on)
    play_a_sound(environment["shoot_sound"])
    environment["camera_pointer"].capture(filename, 'jpeg', use_video_port=True)
    environment["camera_pointer"].stop_preview()
    execute_relay_command_with_dict(command_off)
    show_image(environment, filename)
    time.sleep(SECONDS_TO_WAIT_TO_SHOW_PICTURE_AFTER_A_SHOOT)
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
    timestamp = time.strftime('%Y%m%d_%H%M%S', time.localtime())
    montage_filename = os.path.join(environment["output_montages_photos_folder"], str(timestamp)+"-montage.png")
    # Save it to the usb drive
    background_image.save(montage_filename)
    return montage_filename

def creation_montage_start_screen(environment, last_picture_filename):
    """Creation du montage photo d'image de depart"""
    if last_picture_filename:
        background_image = PIL.Image.open(environment["original_start_picture_filename"])
        image1 = PIL.Image.open(last_picture_filename).resize((environment["picture_for_pasting_width_start_screen"], environment["picture_for_pasting_height_start_screen"]))
        background_image.paste(image1, environment["last_picture_pos_start_in_start_screen"])
        background_image.save(environment["start_picture_filename"])
        return True
    copyfile(environment["original_start_picture_filename"], environment["start_picture_filename"])
    return False

def creation_montage_to_print_a_format(filepath, tmp_filepath):
    """Creation du montage photo d'image de depart"""
    if filepath:
        background_image = PIL.Image.new("RGB", (1920, 1358), color='white')
        image1 = PIL.Image.open(filepath)
        background_image.paste(image1, (0, 139))
        background_image.save(tmp_filepath)
        return tmp_filepath
    return None

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
    if printing_asked:
        print_picture(environment, environment["last_taken_picture_path"])

    creation_montage_start_screen(environment, environment["last_taken_picture_path"])

def show_last_picture(environment):
    """Function that handle the scenario take a picture"""
    lg.info("SCENARIO : Show last picture")
    if environment["last_taken_picture_path"]:
        show_image(environment, environment["last_taken_picture_path"])
        time.sleep(SECONDS_TO_WAIT_TO_SHOW_PICTURE_READY_TO_PRINT)
        printing_asked = wait_for_allow_printing_event(environment, 5)
        if printing_asked:
            print_picture(environment, environment["last_taken_picture_path"])
    else:
        lg.warning("No picture taken yet=>Take one !")

def browse_pictures(environment):
    """Function that handle the scenario take a picture"""
    lg.info("SCENARIO : Browse pictures")
    all_montages_filename = get_all_montages(environment)
    #lg.info("all_montages_filename:"+str(all_montages_filename))
    #lg.info("len(all_montages_filename):"+str(len(all_montages_filename)))
    pointer = len(all_montages_filename) - 1
    event_get = EVENT_TYPE_BROWSE_PICTURES
    show_image(environment, environment["background_browse_filename"])
    width = 1600
    height = 900
    delta_x = (environment["screen_w"] / 2) - (width / 2)
    delta_y = environment["browsing_down_up_bar"]

    while event_get != EVENT_NO_TYPE:
        #lg.info("pointer:"+str(pointer))
        if pointer < 0:
            pointer = 0
        if pointer >= len(all_montages_filename):
            pointer = len(all_montages_filename)-1
        #show_image(environment, all_montages_filename[pointer])
        show_image_with_size_and_pos(environment, all_montages_filename[pointer], width, height, delta_x, delta_y)
        command_on = {}
        command_on[environment["relay_bp_to_launch_browse_pictures"]] = True
        command_on[environment["relay_bp_to_launch_show_last_picture"]] = True
        command_off = {}
        command_off[environment["relay_bp_to_launch_browse_pictures"]] = False
        command_off[environment["relay_bp_to_launch_show_last_picture"]] = False
        execute_relay_command_with_dict(command_on)
        event_get = wait_for_event(environment, SECONDS_TO_WAIT_IN_BROWSING_MODE)
        execute_relay_command_with_dict(command_off)
        #print_event(event_get)
        if event_get == EVENT_TYPE_BROWSE_PICTURES:
            pointer -= 1
            play_a_sound(environment["page_flip_sound_back"])
        elif event_get == EVENT_TYPE_SHOW_LAST_PICTURE:
            pointer += 1
            play_a_sound(environment["page_flip_sound"])
        if event_get == EVENT_TYPE_TAKE_PICTURE or event_get == EVENT_TYPE_RESTART or event_get == EVENT_TYPE_STOP:
            return

def play_a_sound(filepath):
    """play a sound file"""
    os.system("aplay -q "+str(filepath)+" &")

def main_pygame(environment):
    """pygame main function"""
    play_a_sound(environment["start_sound"])
    creation_montage_start_screen(environment, environment["last_taken_picture_path"])

    while True:
        show_image(environment, environment["start_picture_filename"])
        command_on = {}
        command_on[environment["relay_bp_to_launch_browse_pictures"]] = True
        command_on[environment["relay_bp_to_launch_take_pictures"]] = True
        command_on[environment["relay_bp_to_launch_show_last_picture"]] = True
        command_off = {}
        command_off[environment["relay_bp_to_launch_browse_pictures"]] = False
        command_off[environment["relay_bp_to_launch_take_pictures"]] = False
        command_off[environment["relay_bp_to_launch_show_last_picture"]] = False
        execute_relay_command_with_dict(command_on)
        event_get = wait_for_event(environment, 0)
        execute_relay_command_with_dict(command_off)
        #print_event(event_get)
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
            lg.info("Ask to restart the system")
            if environment["reboot_enabled"]:
                os.system("sudo reboot")
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
    environment = init_environment(main_args)
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
        help="Message to print",
        type=str,
        default="hello world"
    )
    parser.add_argument(
        '-p', '--printer',
        help="Enable printer",
        action='store_true',
    )
    parser.add_argument(
        '-r', '--reboot',
        help="Enable reboot",
        action='store_true',
    )
    parser.add_argument(
        '-c', '--count',
        help="number of time to print the Message, default:1",
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
