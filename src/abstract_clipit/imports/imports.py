#!/usr/bin/env python3
# gui_frontend.py (with a toggleable log console)
from __future__ import annotations

# ─── Standard library ─────────────────────────────────────────────────────────
import ast,datetime,json,glob,re,sys,traceback,os, re, textwrap
from pathlib import Path
from abstract_gui.QT6 import*
from PyQt6 import QtGui


import pytesseract
from pdf2image import convert_from_path

# ─── Local application ─────────────────────────────────────────────────────────
from abstract_pandas import get_df
from abstract_utilities import *
from abstract_modules.trace_module import *
from abstract_utilities import *
