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
# pylint --disable=logging-not-lazy,broad-except --generate-rcfile > pylintrc
## install pip-autoremove
#pip install pip-autoremove
## remove "somepackage" plus its dependencies:
#pip-autoremove somepackage -y
"""
Program that display something
"""

#1.0.0 : Version initial

import argparse
import logging as lg
import pygame

VERSION = "1.0.0"


def my_main(args):
    """Main function."""
    #
    for one in range(0, args.count):
        print(str(one)+":"+args.message)

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
