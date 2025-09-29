# Defect Viewer Version 1.6.4
# fixed bug with circle and line marker tools where length and area labels were in pixels instead of microns
# Added in new class called ShowPdf which converts pdf to scrollable image in tkinter (previously imported as module)
# ShowPdf is part of python module found here https://github.com/Roshanpaswan/tkPDFViewer.git
# Modifications were made since module was out-of-date
# Summary of changes to ShowPdf...
# Added __init__ function to ShowPdf class, moved img_object_li instance variable into __init__ function. This aids in garbage-collection avoidance upon reruns of code.
# Added explicit anchor argument to self.display_msg = Label(master, textvariable=percentage_load)
# Added new variable returned upon exit of pdf_view() function (self.img_object_li). This allows capture of image array which aids in garbage collection avoidance.

import tkinter as tk
from tkinter import Tk, Canvas, mainloop
from tkinter import ttk
from tkinter import filedialog
import fitz

import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from PIL import Image, ImageTk
from io import BytesIO
import cv2

import sqlite3

import os
import argparse
import shutil
import warnings
import time
from threading import Thread

Image.MAX_IMAGE_PIXELS = None

""" 
This script is used to plot images and analysis results measured by the Nanotronics nSpec tool 
The user inputs directories to the scanned images and the database file containing analysis information
Images are output in a mosaic with defects overlaid

"""
    
def defect_viewer(self):
    """ Contains all the functionality of the app post root window
    Activates once mosaic is plotted from root window gui """
    image_origin = self.img_loc_var + '/' # Here we gather our variables of interest entered into the root window gui
    db_origin = self.db_file_var.get()
    scan_id = self.scan_id_var.get()
    analysis_id = self.ana_id_var.get()
    image_scale = int(self.image_scale_var.get())
    image_view_only = self.image_view_only.get()
    # set the default binning ranges and colors to those received by the root window
    default_binning_ranges = self.binning_ranges
    default_binning_colors = self.binning_colors
    default_inf_bin_color = self.inf_bin_color
 
    def clicked(self, event):
        """ Contains all functionality to support click event
            This function is called upon click event """
        print(event)

        # variables passed from the instance of MosaicCreator
        # these variables must be adjusted back to initial values as defined in the MosaicCreator object each time a click event happens
        defect_binning_ranges = self.binning_ranges # binning ranges for defects, based on defect area
        defect_binning_colors = self.binning_colors # binning colors for defects based on defect area
        defect_binning_type_colors = self.binning_type_colors # binning colors for defects based on defect classification
        defect_inf_bin_color = self.inf_bin_color # color for the defect bin which goes to infinity
        label_font_size = int(self.font_size_defect_label) # font size for defect labels
        defect_data = self.defect_data # array containing all relevant defect data
        defect_type_data = self.defect_type_data # array containing relevant defect classification information
        which_binning_show = self.which_binning_show # variable tells which defect binning to show by default
        image_data = self.image_data # array containing all relevant image data
        scan_properties = self.scan_properties # array containing information relevant to scan
        mos_tile_width = self.mos_tile_width # width and height of mosaic canvas tile
        mos_tile_height = self.mos_tile_height
        
        # iterate through all image data rows, find selected image according to click event, image coords, and tile size
        for idx, img_row in enumerate(image_data):

            tile_row = float(img_row[7]) # find the Row and Column of the tile in the mosaic image
            tile_column = float(img_row[8])

            # find the ranges of values where tile exists inside mosaic canvas
            x_bottom = tile_column * mos_tile_width 
            x_top = (tile_column * mos_tile_width) + mos_tile_width
            y_bottom = tile_row * mos_tile_height
            y_top = (tile_row * mos_tile_height) + mos_tile_height
                
            if ((x_bottom <= (event.x) <= x_top) and (y_bottom <= (event.y) <= y_top)):
                
                class AutoScrollbar(ttk.Scrollbar):
                    """ A scrollbar that hides itself if it's not needed. Works only for grid geometry manager """
                    def set(self, lo, hi):
                        if float(lo) <= 0.0 and float(hi) >= 1.0:
                            self.grid_remove()
                        else:
                            self.grid()
                            ttk.Scrollbar.set(self, lo, hi)
                
                    def pack(self, **kw):
                        raise tk.TclError('Cannot use pack with the widget ' + self.__class__.__name__)
                
                    def place(self, **kw):
                        raise tk.TclError('Cannot use place with the widget ' + self.__class__.__name__)
                
                class CanvasImage:
                    """ Display and zoom image """
                    def __init__(self, placeholder, path):
                        """ Initialize the ImageFrame """
                        self.hide_defect_labels = None # tracks user's choice to display defect labels
                        self.hide_defect_marks = None # tracks user's choice to display defect marks
                        # the which_binning_show variable passed from MosaicCreator must be updated to instance variable status 
                        self.which_binning_show = which_binning_show # this allows active changes to this variable while tile is open
                        self.measure_choice = None # variable tracks user's choice of manual measurement on tile canvas
                        self.start_x = None # coordinates which aid in the class functions for drawing areas
                        self.start_y = None
                        self.__new_font_size = None # initialize shared variable for adjusting font sizes upon zoom
                        self.imscale = 1.0  # scale for the canvas image zoom, public for outer classes
                        self.__delta = 1.3  # zoom magnitude
                        self.__filter = Image.LANCZOS  # could be: NEAREST, BILINEAR, BICUBIC and ANTIALIAS
                        self.__previous_state = 0  # previous state of the keyboard
                        self.path = path  # path to the image, should be public for outer classes
                        # Create ImageFrame in placeholder widget
                        self.__imframe = ttk.Frame(placeholder)  # placeholder of the ImageFrame object
                        # Vertical and horizontal scrollbars for canvas
                        hbar = AutoScrollbar(self.__imframe, orient='horizontal')
                        vbar = AutoScrollbar(self.__imframe, orient='vertical')
                        hbar.grid(row=1, column=0, sticky='we')
                        vbar.grid(row=0, column=1, sticky='ns')
                        # Create canvas and bind it with scrollbars. Public for outer classes
                        self.canvas = tk.Canvas(self.__imframe, highlightthickness=0,
                                                xscrollcommand=hbar.set, yscrollcommand=vbar.set)
                        self.canvas.grid(row=0, column=0, sticky='nswe')
                        self.canvas.update()  # wait till canvas is created
                        hbar.configure(command=self.__scroll_x)  # bind scrollbars to the canvas
                        vbar.configure(command=self.__scroll_y)
                        # Bind events to the Canvas
                        self.canvas.bind('<Configure>', lambda event: self.__show_image())  # canvas is resized
                        self.canvas.bind("<Return>", self.__destroy_measure_markers) # remove all placed measurement marks
                        self.canvas.bind('<ButtonPress-1>', self.__move_from)  # remember canvas position
                        self.canvas.bind('<B1-Motion>',     self.__move_to)  # move canvas to the new position
                        self.canvas.bind('<MouseWheel>', self.__wheel)  # zoom for Windows and MacOS, but not Linux
                        self.canvas.bind('<Button-5>',   self.__wheel)  # zoom for Linux, wheel scroll down
                        self.canvas.bind('<Button-4>',   self.__wheel)  # zoom for Linux, wheel scroll up
                        self.canvas.bind("<ButtonPress-3>", self.__on_right_click) # initiate user measurement
                        self.canvas.bind("<B3-Motion>", self.__on_right_click_drag) # enable dragging for drawing measurement mark
                        self.canvas.bind("<ButtonRelease-3>", self.__on_right_click_release) # finalize measurement mark
                        # Handle keystrokes in idle mode, because program slows down on a weak computers,
                        # when too many key stroke events in the same time
                        self.canvas.bind('<Key>', lambda event: self.canvas.after_idle(self.__keystroke, event))
                        # Decide if this image huge or not
                        self.__huge = False  # huge or not
                        self.__huge_size = 14000  # define size of the huge image
                        self.__band_width = 1024  # width of the tile band
                        Image.MAX_IMAGE_PIXELS = 1000000000  # suppress DecompressionBombError for the big image
                        with warnings.catch_warnings():  # suppress DecompressionBombWarning
                            warnings.simplefilter('ignore')
                            self.__image = Image.open(self.path)  # open image, but don't load it
                        self.imwidth, self.imheight = self.__image.size  # public for outer classes
                        if self.imwidth * self.imheight > self.__huge_size * self.__huge_size and \
                           self.__image.tile[0][0] == 'raw':  # only raw images could be tiled
                            self.__huge = True  # image is huge
                            self.__offset = self.__image.tile[0][2]  # initial tile offset
                            self.__tile = [self.__image.tile[0][0],  # it have to be 'raw'
                                           [0, 0, self.imwidth, 0],  # tile extent (a rectangle)
                                           self.__offset,
                                           self.__image.tile[0][3]]  # list of arguments to the decoder
                        self.__min_side = min(self.imwidth, self.imheight)  # get the smaller image side
                        # Create image pyramid
                        self.__pyramid = [self.smaller()] if self.__huge else [Image.open(self.path)]
                        # Set ratio coefficient for image pyramid
                        self.__ratio = max(self.imwidth, self.imheight) / self.__huge_size if self.__huge else 1.0
                        self.__curr_img = 0  # current image from the pyramid
                        self.__scale = self.imscale * self.__ratio  # image pyramide scale
                        self.__reduction = 2  # reduction degree of image pyramid
                        w, h = self.__pyramid[-1].size
                        while w > 512 and h > 512:  # top pyramid image is around 512 pixels in size
                            w /= self.__reduction  # divide on reduction degree
                            h /= self.__reduction  # divide on reduction degree
                            self.__pyramid.append(self.__pyramid[-1].resize((int(w), int(h)), self.__filter))
                        # Put image into container rectangle and use it to set proper coordinates to the image
                        self.container = self.canvas.create_rectangle((0, 0, self.imwidth, self.imheight), width=0)
                        self.__show_image()  # show image on the canvas
                        self.__create_option_buttons() # create the option buttons next to the canvas
                        # check if user has selected image view only
                        if mosaic_obj.image_view_only == 0:
                            self.__show_defects()  # show defects on the canvas
                            self.__show_labels() # show defect labels on the canvas
                        self.canvas.focus_set()  # set focus on the canvas
                
                    def smaller(self):
                        """ Resize image proportionally and return smaller image """
                        w1, h1 = float(self.imwidth), float(self.imheight)
                        w2, h2 = float(self.__huge_size), float(self.__huge_size)
                        aspect_ratio1 = w1 / h1
                        aspect_ratio2 = w2 / h2  # it equals to 1.0
                        if aspect_ratio1 == aspect_ratio2:
                            image = Image.new('RGB', (int(w2), int(h2)))
                            k = h2 / h1  # compression ratio
                            w = int(w2)  # band length
                        elif aspect_ratio1 > aspect_ratio2:
                            image = Image.new('RGB', (int(w2), int(w2 / aspect_ratio1)))
                            k = h2 / w1  # compression ratio
                            w = int(w2)  # band length
                        else:  # aspect_ratio1 < aspect_ration2
                            image = Image.new('RGB', (int(h2 * aspect_ratio1), int(h2)))
                            k = h2 / h1  # compression ratio
                            w = int(h2 * aspect_ratio1)  # band length
                        i, j, n = 0, 1, round(0.5 + self.imheight / self.__band_width)
                        while i < self.imheight:
                            print('\rOpening image: {j} from {n}'.format(j=j, n=n), end='')
                            band = min(self.__band_width, self.imheight - i)  # width of the tile band
                            self.__tile[1][3] = band  # set band width
                            self.__tile[2] = self.__offset + self.imwidth * i * 3  # tile offset (3 bytes per pixel)
                            self.__image.close()
                            self.__image = Image.open(self.path)  # reopen / reset image
                            self.__image.size = (self.imwidth, band)  # set size of the tile band
                            self.__image.tile = [self.__tile]  # set tile
                            cropped = self.__image.crop((0, 0, self.imwidth, band))  # crop tile band
                            image.paste(cropped.resize((w, int(band * k)+1), self.__filter), (0, int(i * k)))
                            i += band
                            j += 1
                        print('\r' + 30*' ' + '\r', end='')  # hide printed string
                        return image
                
                    def redraw_figures(self):
                        """ Dummy function to redraw figures in the children classes """
                        pass
                
                    def grid(self, **kw):
                        """ Put CanvasImage widget on the parent widget """
                        self.__imframe.grid(**kw)  # place CanvasImage widget on the grid
                        self.__imframe.grid(sticky='nswe')  # make frame container sticky
                        self.__imframe.rowconfigure(0, weight=1)  # make canvas expandable
                        self.__imframe.columnconfigure(0, weight=1)
                
                    def pack(self, **kw):
                        """ Exception: cannot use pack with this widget """
                        raise Exception('Cannot use pack with the widget ' + self.__class__.__name__)
                
                    def place(self, **kw):
                        """ Exception: cannot use place with this widget """
                        raise Exception('Cannot use place with the widget ' + self.__class__.__name__)
                
                    # noinspection PyUnusedLocal
                    def __scroll_x(self, *args, **kwargs):
                        """ Scroll canvas horizontally and redraw the image """
                        self.canvas.xview(*args)  # scroll horizontally
                        self.__show_image()  # redraw the image
                
                    # noinspection PyUnusedLocal
                    def __scroll_y(self, *args, **kwargs):
                        """ Scroll canvas vertically and redraw the image """
                        self.canvas.yview(*args)  # scroll vertically
                        self.__show_image()  # redraw the image
                        
                    def __poly_oval(self, x0, y0, x1, y1, steps=40, rotation=0):
                        """ OLD VERSION (uses loops): Return an oval as coordinates suitable for create_polygon """
                        # x0,y0,x1,y1 are as create_oval
                        # rotation is in degrees anti-clockwise, convert to radians
                        rotation = rotation * np.pi / 180.0
                        # major and minor axes
                        a = (x1 - x0) / 2.0
                        b = (y1 - y0) / 2.0
                        # center
                        xc = x0 + a
                        yc = y0 + b

                        point_list = []

                        # create the oval as a list of points
                        for i in range(steps):
                            # Calculate the angle for this step
                            # 360 degrees == 2 pi radians
                            theta = (math.pi * 2) * (float(i) / steps)
                            x1 = a * math.cos(theta)
                            y1 = b * math.sin(theta)
                            # rotate x, y
                            x = (x1 * math.cos(rotation)) + (y1 * math.sin(rotation))
                            y = (y1 * math.cos(rotation)) - (x1 * math.sin(rotation))

                            point_list.append(round(x + xc))
                            point_list.append(round(y + yc))

                        return point_list
                    
                    def __poly_oval_v2(self, x0, y0, x1, y1, steps=50, rotation=0):
                        """ NEW VERSION (uses numpy): Return an oval as coordinates suitable for create_polygon """
                        # x0,y0,x1,y1 as from create_oval
                        # rotation is in degrees, convert to radians
                        # counter-clockwise rotation
                        rotation = rotation * np.pi / 180.0
                        a = (x1 - x0) / 2.0 # major and minor axes
                        b = (y1 - y0) / 2.0
                        xc = x0 + a # center
                        yc = y0 + b
                        
                        # Calculate the angle for all steps
                        # 360 degrees == 2 pi radians
                        theta = (np.pi * 2) * (np.arange(steps) / steps)
                        x1 = a * np.cos(theta)
                        y1 = b * np.sin(theta)
                        x = (x1 * np.cos(rotation)) + (y1 * np.sin(rotation)) + xc # rotate x, y
                        y = (y1 * np.cos(rotation)) - (x1 * np.sin(rotation)) + yc
                        
                        # create an oval as a list of points...
                        point_list = (np.column_stack([x,y])).flatten()
                        
                        return point_list

                    def __show_defects(self):
                        """ Plots defects on selected image """
                        box_image = self.canvas.coords(self.container)  # get image area
                        
                        # now plot the defects on the current canvas image tile
                        for idx, def_row in enumerate(defect_data):
                                if float(def_row[1]) == float(img_row[0]):
                                    x = float(def_row[4])*box_image[2]/float(img_row[9]) # coordinates of defect scaled by image size
                                    y = float(def_row[5])*box_image[3]/float(img_row[10]) # also converted to image pixels from microns
                                    scale = 30
                                    
                                    # we will plot multiple copies of each defect overlaid on each other
                                    # each copy will have a different defect mark color for the different binning types we can choose
                                    # then we can simply toggle the defect visibility to the user by using tags for each bin type

                                    bin_range_index = np.searchsorted(defect_binning_ranges, float(def_row[8])) # get index corresponding to binning range of defect area
                                    # set size-based defect mark color based on binning color corresponding to index found above
                                    if (bin_range_index > (len(defect_binning_ranges) - 1)) or (defect_binning_ranges.size == 0):
                                        bin_outline_color = defect_inf_bin_color
                                    else:
                                        bin_outline_color = defect_binning_colors[bin_range_index]
                                        
                                    # set class-based defect mark color based on user binning input
                                    if defect_binning_type_colors.size == 0 or defect_type_data.size == 0:
                                        mark_type_outline_color = defect_inf_bin_color
                                    else:
                                        mark_type_outline_color = defect_binning_type_colors[np.where(defect_type_data[:,0:1].flatten() == def_row[15])][0]
                                    
                                    # ovals cannot be rotated in tkinter
                                    # convert oval coordinates to polygon and add in rotation defined by "Orientation" from database file
                                    # the factor of 2 multiplied on here ensures the oval encircles the entire defect
                                    # width is y-direction length, height is x-direction length according to nSpec
                                    x0 = x - (float(def_row[7])*2)/2
                                    y0 = y - (float(def_row[6])*2)/2
                                    x1 = x + (float(def_row[7])*2)/2
                                    y1 = y + (float(def_row[6])*2)/2
                                    
                                    # now plot the defect on the mosaic, we plot multiple overlaid copies for each binning type
                                    self.canvas.create_polygon(tuple(self.__poly_oval_v2(x0, y0, x1, y1, 
                                                rotation = float(def_row[12]))), outline = bin_outline_color, fill = "", width = 2, tags = "DEFECT_TILE_MARK_SIZE_BINNING")
                                    self.canvas.create_polygon(tuple(self.__poly_oval_v2(x0, y0, x1, y1, 
                                                rotation = float(def_row[12]))), outline = mark_type_outline_color, fill = "", width = 2, tags = "DEFECT_TILE_MARK_CLASS_BINNING")
                                    self.canvas.itemconfigure("DEFECT_TILE_MARK_SIZE_BINNING", state="hidden")
                                    self.canvas.itemconfigure("DEFECT_TILE_MARK_CLASS_BINNING", state="hidden")
                                    
                        # by default show the defect marks associated with the user's current choice on the mosaic
                        if self.which_binning_show == "SIZE":
                            self.canvas.itemconfigure("DEFECT_TILE_MARK_SIZE_BINNING", state="normal")
                        if self.which_binning_show == "CLASS":
                            self.canvas.itemconfigure("DEFECT_TILE_MARK_CLASS_BINNING", state="normal")
                            
                    def __toggle_binning(self, toggle_choice):
                        """ Toggles visibility for the desired set of defect binning colors """
                        self.which_binning_show = toggle_choice # we must update global variable for binning visibility
                        if toggle_choice == "SIZE":
                            self.canvas.itemconfigure("DEFECT_TILE_MARK_SIZE_BINNING", state="normal")
                            self.canvas.itemconfigure("DEFECT_TILE_MARK_CLASS_BINNING", state="hidden")
                        if toggle_choice == "CLASS":
                            self.canvas.itemconfigure("DEFECT_TILE_MARK_SIZE_BINNING", state="hidden")
                            self.canvas.itemconfigure("DEFECT_TILE_MARK_CLASS_BINNING", state="normal")

                    def __show_labels(self):
                        """ Plots defect labels on selected image """
                        box_image = self.canvas.coords(self.container)  # get image area
                        
                        # now plot the defect labels on the current canvas image tile
                        for idx, def_row in enumerate(defect_data):
                                if float(def_row[1]) == float(img_row[0]):
                                    x = float(def_row[4])*box_image[2]/float(img_row[9]) # coordinates of defect label scaled by image size
                                    y = float(def_row[5])*box_image[3]/float(img_row[10]) # also converted to image pixels from microns
                                    scale = 60
                                    #font_size = -int(10*((box_image[2]*box_image[3])/(self.imheight*self.imwidth)))
                                    # this array contains all defect info that can be output on the defect label text line
                                    defect_all_info = np.array(["DefectID = " + def_row[0], "ImageID = " + def_row[1], "AnalysisID = " + def_row[2],
                                                                "DeviceID = " + def_row[3], "X = " + def_row[4], "Y = " + def_row[5],
                                                                "W = " + def_row[6], "H = " + def_row[7], "Area = " + def_row[8],
                                                                "Intensity = " + def_row[9], "IntensityDeviation = " + def_row[10],
                                                                "Eccentricity = " + def_row[11], "Orientation = " + def_row[12],
                                                                "XinDevice = " + def_row[13], "YinDevice = " + def_row[14], "ClassID = " + def_row[15],
                                                                "Score = " + def_row[16], "Contour = " + def_row[17]])
                                    defect_select_info = defect_all_info[mosaic_obj.defect_label_text_choices] # filter info array to user selections
                                    defect_label_text = ", ".join(defect_select_info) # combine all elements into one string
                                    self.canvas.create_text(x-box_image[2]/scale, y-box_image[3]/scale, 
                                                            text = defect_label_text, font=("Arial", -label_font_size), tags = ("text", "DEFECT_TILE_LABEL"))

                    def __defect_mark_vis(self, *args):
                        """ Hides or reveals defect labels and/or marks when toggled """
                        if self.hide_defect_marks.get() == 1:
                            self.canvas.itemconfig("DEFECT_TILE_MARK_SIZE_BINNING", state="hidden")
                            self.canvas.itemconfig("DEFECT_TILE_MARK_CLASS_BINNING", state="hidden")
                            #self.canvas.itemconfig("DEFECT_TILE_MARK", state="hidden")
                        else:
                            if self.which_binning_show == "SIZE":
                                self.canvas.itemconfig("DEFECT_TILE_MARK_SIZE_BINNING", state="normal")
                            if self.which_binning_show == "CLASS":
                                self.canvas.itemconfig("DEFECT_TILE_MARK_CLASS_BINNING", state="normal")
                            #self.canvas.itemconfig("DEFECT_TILE_MARK", state="normal")
                            
                        if self.hide_defect_labels.get() == 1:
                            self.canvas.itemconfig("DEFECT_TILE_LABEL", state="hidden")
                        else:
                            self.canvas.itemconfig("DEFECT_TILE_LABEL", state="normal")
                                    
                    def __show_image(self):
                        """ Show image on the Canvas """
                        box_image = self.canvas.coords(self.container)  # get image area
                        box_canvas = (self.canvas.canvasx(0),  # get visible area of the canvas
                                      self.canvas.canvasy(0),
                                      self.canvas.canvasx(self.canvas.winfo_width()),
                                      self.canvas.canvasy(self.canvas.winfo_height()))
                        box_img_int = tuple(map(int, box_image))  # convert to integer or it will not work properly
                        # Get scroll region box
                        box_scroll = [min(box_img_int[0], box_canvas[0]), min(box_img_int[1], box_canvas[1]),
                                      max(box_img_int[2], box_canvas[2]), max(box_img_int[3], box_canvas[3])]
                        # Horizontal part of the image is in the visible area
                        if  box_scroll[0] == box_canvas[0] and box_scroll[2] == box_canvas[2]:
                            box_scroll[0]  = box_img_int[0]
                            box_scroll[2]  = box_img_int[2]
                        # Vertical part of the image is in the visible area
                        if  box_scroll[1] == box_canvas[1] and box_scroll[3] == box_canvas[3]:
                            box_scroll[1]  = box_img_int[1]
                            box_scroll[3]  = box_img_int[3]
                        # Convert scroll region to tuple and to integer
                        self.canvas.configure(scrollregion=tuple(map(int, box_scroll)))  # set scroll region
                        x1 = max(box_canvas[0] - box_image[0], 0)  # get coordinates (x1,y1,x2,y2) of the image tile
                        y1 = max(box_canvas[1] - box_image[1], 0)
                        x2 = min(box_canvas[2], box_image[2]) - box_image[0]
                        y2 = min(box_canvas[3], box_image[3]) - box_image[1]
                        if int(x2 - x1) > 0 and int(y2 - y1) > 0:  # show image if it in the visible area
                            if self.__huge and self.__curr_img < 0:  # show huge image
                                h = int((y2 - y1) / self.imscale)  # height of the tile band
                                self.__tile[1][3] = h  # set the tile band height
                                self.__tile[2] = self.__offset + self.imwidth * int(y1 / self.imscale) * 3
                                self.__image.close()
                                self.__image = Image.open(self.path)  # reopen / reset image
                                self.__image.size = (self.imwidth, h)  # set size of the tile band
                                self.__image.tile = [self.__tile]
                                image = self.__image.crop((int(x1 / self.imscale), 0, int(x2 / self.imscale), h))
                            else:  # show normal image
                                image = self.__pyramid[max(0, self.__curr_img)].crop(  # crop current img from pyramid
                                                    (int(x1 / self.__scale), int(y1 / self.__scale),
                                                     int(x2 / self.__scale), int(y2 / self.__scale)))
                            #
                            imagetk = ImageTk.PhotoImage(image.resize((int(x2 - x1), int(y2 - y1)), self.__filter))
                            imageid = self.canvas.create_image(max(box_canvas[0], box_img_int[0]),
                                                               max(box_canvas[1], box_img_int[1]),
                                                               anchor='nw', image=imagetk)

                            self.canvas.lower(imageid)  # set image into background
                            self.canvas.imagetk = imagetk  # keep an extra reference to prevent garbage-collection
                            
                    def __create_option_buttons(self):
                        """ Create option buttons off to the side of the canvas """
                        # these labels/buttons relate to manual measurement tools
                        tk.Label(self.__imframe, text='Measurement Tool').grid(row=1, column = 1, columnspan = 1)
                        button_select_circle = tk.Button(self.__imframe, text='Circle', width = 10, 
                                                         command = lambda arg = "Circle": self.__set_measure_choice(arg))
                        button_select_circle.grid(row=2, column=1, sticky='nswe')

                        button_select_line = tk.Button(self.__imframe, text='Line', width = 10, 
                                                       command = lambda arg = "Line": self.__set_measure_choice(arg))
                        button_select_line.grid(row=3, column=1, sticky='nswe')
                        
                        # checkbox to toggle defect mark visibility
                        self.hide_defect_marks = tk.IntVar(self.__imframe, value = 0)
                        self.hide_defect_marks.trace('w', self.__defect_mark_vis) # call visibility function upon value change
                        checkbox_mark_vis = tk.Checkbutton(self.__imframe, text='Hide Defect Marks', variable=self.hide_defect_marks)
                        checkbox_mark_vis.grid(row = 2, column = 0, columnspan = 1, sticky = 'w')
                        
                        # checkbox to toggle defect label visibility
                        self.hide_defect_labels = tk.IntVar(self.__imframe, value = 0)
                        self.hide_defect_labels.trace('w', self.__defect_mark_vis) # call visibility function upon value change
                        checkbox_label_vis = tk.Checkbutton(self.__imframe, text='Hide Defect Labels', variable=self.hide_defect_labels)
                        checkbox_label_vis.grid(row = 3, column = 0, columnspan = 1, sticky = 'w')
                        
                        # button for toggling visibility of size-binned defect colors
                        button_size_binning = tk.Button(self.__imframe, text='Size Binning', width = 10, command = lambda: self.__toggle_binning("SIZE"))
                        button_size_binning.grid(row=4, column=0, sticky='w')
            
                        # button for toggling visibility of class-binned defect colors
                        button_class_binning = tk.Button(self.__imframe, text='Class Binning', width = 10, command = lambda: self.__toggle_binning("CLASS"))
                        button_class_binning.grid(row=5, column=0, sticky='w')
                    
                    def __set_measure_choice(self, arg):
                        """ Set which kind of object to draw with the measuring tool """
                        self.measure_choice = arg
                    
                    def __on_right_click(self, event):
                        """ Initializes the measurement upon click """
                        self.start_x = self.canvas.canvasx(event.x)
                        self.start_y = self.canvas.canvasy(event.y)
                    
                    def __on_right_click_drag(self, event):
                        """ Allows for measurement size modification through mouse drag """
                        if self.measure_choice == "Circle":
                            if self.start_x is not None and self.start_y is not None:
                                self.canvas.delete("temp_circle")
                                radius = ((self.canvas.canvasx(event.x) - self.start_x)**2 + (self.canvas.canvasy(event.y) - self.start_y)**2)**0.5
                                self.canvas.create_oval(self.start_x - radius, self.start_y - radius, 
                                                        self.canvas.canvasx(event.x) + (radius - (self.canvas.canvasx(event.x)-self.start_x)), 
                                                        self.canvas.canvasy(event.y) + (radius - (self.canvas.canvasy(event.y) - self.start_y)), 
                                                        outline='red', tags="temp_circle")
                                
                        elif self.measure_choice == "Line":
                            if self.start_x is not None and self.start_y is not None:
                                self.canvas.delete("temp_line")
                                length = ((self.canvas.canvasx(event.x) - self.start_x)**2 + (self.canvas.canvasy(event.y) - self.start_y)**2)**0.5
                                self.canvas.create_line(self.start_x, self.start_y, self.canvas.canvasx(event.x), self.canvas.canvasy(event.y),
                                                        fill='red', width = 2, tags="temp_line")
                    
                    def __on_right_click_release(self, event):
                        """ Finalizes measurement upon release of mouse click """
                        if self.measure_choice == "Circle":
                            if self.start_x is not None and self.start_y is not None:
                                self.canvas.delete("temp_circle")
                                # radius of circle
                                radius = ((self.canvas.canvasx(event.x) - self.start_x)**2 + (self.canvas.canvasy(event.y) - self.start_y)**2)**0.5
                                self.canvas.create_oval(self.start_x - radius, self.start_y - radius, 
                                                        self.canvas.canvasx(event.x) + (radius - (self.canvas.canvasx(event.x)-self.start_x)), 
                                                        self.canvas.canvasy(event.y) + (radius - (self.canvas.canvasy(event.y) - self.start_y)), 
                                                        outline='red', tags="final_area_circle")
                                
                                # now we calculate the area to be displayed next to the circle marker on the canvas
                                # convert x and y to microns using image size in pixels vs microns
                                # also, scale according to the current image magnification
                                micron_radius = (((self.canvas.canvasx(event.x) - self.start_x)*(float(img_row[9])/float(img_row[11])))**2 
                                          + ((self.canvas.canvasy(event.y) - self.start_y)*(float(img_row[10])/float(img_row[12])))**2)**0.5
                                scaled_radius = (micron_radius / self.imscale)
                                area = (np.pi*scaled_radius**2)

                                # create area label, which uses the same font size as defect labels for now
                                # check if new font size applied due to zoom, if not apply default font size
                                if self.__new_font_size == None:
                                    area_font_size = label_font_size
                                else:
                                    area_font_size = self.__new_font_size
                                self.canvas.create_text(self.start_x - radius, self.start_y - radius, text=("Area = " + str(area)), 
                                                            font=("Arial", -area_font_size), tags = ("text", "final_area_circle"))
                                self.start_x = None
                                self.start_y = None
                        
                        elif self.measure_choice == "Line":
                            if self.start_x is not None and self.start_y is not None:
                                self.canvas.delete("temp_line")
                                # create the line on the canvas
                                self.canvas.create_line(self.start_x, self.start_y, self.canvas.canvasx(event.x), self.canvas.canvasy(event.y),
                                                        fill='red', width = 2, tags="final_line_length")
                                
                                # now we find the length of the line in microns using image size in pixels vs microns
                                # we also scale according to current image magnification
                                micron_length = (((self.canvas.canvasx(event.x) - self.start_x)*(float(img_row[9])/float(img_row[11])))**2 
                                          + ((self.canvas.canvasy(event.y) - self.start_y)*(float(img_row[10])/float(img_row[12])))**2)**0.5
                                scaled_length = (micron_length / self.imscale)

                                # create text label, which uses the same font size as defect labels for now
                                # check if new font size applied due to zoom, if not apply default font size
                                if self.__new_font_size == None:
                                    line_font_size = label_font_size
                                else:
                                    line_font_size = self.__new_font_size
                                self.canvas.create_text(self.start_x, self.start_y, text=("Length = " + str(scaled_length)), 
                                                            font=("Arial", -line_font_size), tags = ("text", "final_line_length"))
                                self.start_x = None
                                self.start_y = None

                    def __destroy_measure_markers(self, event):
                        """ Removes any measurement markers on the canvas """
                        for item in self.canvas.find_withtag("final_area_circle"):
                            self.canvas.delete(item)
                        for item in self.canvas.find_withtag("final_line_length"):
                            self.canvas.delete(item)
                
                    def __move_from(self, event):
                        """ Remember previous coordinates for scrolling with the mouse """
                        self.canvas.scan_mark(event.x, event.y)
                
                    def __move_to(self, event):
                        """ Drag (move) canvas to the new position """
                        self.canvas.scan_dragto(event.x, event.y, gain=1)
                        self.__show_image()  # zoom tile and show it on the canvas
                
                    def outside(self, x, y):
                        """ Checks if the point (x,y) is outside the image area """
                        bbox = self.canvas.coords(self.container)  # get image area
                        if bbox[0] < x < bbox[2] and bbox[1] < y < bbox[3]:
                            return False  # point (x,y) is inside the image area
                        else:
                            return True  # point (x,y) is outside the image area
                
                    def __wheel(self, event):
                        """ Zoom with mouse wheel """
                        x = self.canvas.canvasx(event.x)  # get coordinates of the event on the canvas
                        y = self.canvas.canvasy(event.y)
                        if self.outside(x, y): return  # zoom only inside image area
                        scale = 1.0
                        # Respond to Linux (event.num) or Windows (event.delta) wheel event
                        if event.num == 5 or event.delta == -120:  # scroll down, smaller
                            if round(self.__min_side * self.imscale) < 30: return  # image is less than 30 pixels
                            self.imscale /= self.__delta
                            scale        /= self.__delta
                        if event.num == 4 or event.delta == 120:  # scroll up, bigger
                            i = min(self.canvas.winfo_width(), self.canvas.winfo_height()) >> 1
                            if i < self.imscale: return  # 1 pixel is bigger than the visible area
                            self.imscale *= self.__delta
                            scale        *= self.__delta
                        # Take appropriate image from the pyramid
                        k = self.imscale * self.__ratio  # temporary coefficient
                        self.__curr_img = min((-1) * int(math.log(k, self.__reduction)), len(self.__pyramid) - 1)
                        self.__scale = k * math.pow(self.__reduction, max(0, self.__curr_img))
                        #
                        self.canvas.scale('all', x, y, scale, scale)  # rescale all objects
                        # below we scale the text
                        box_image = self.canvas.coords(self.container)  # get image area
                        #self.font_size = -int(10*((box_image[2]*box_image[3])/(self.imheight*self.imwidth))) # rescale text
                        nonlocal label_font_size
                        rounding_indicator = label_font_size * scale
                        # we will increase or decrease font size based on rounding indicator
                        # if the indicator is larger than font size (scale is inc), inc font size
                        # if the indicator is smaller (scale is dec), dec font size
                        # built-in protection against decreasing font size to zero
                        if rounding_indicator < label_font_size and rounding_indicator >= 1:
                            self.__new_font_size = math.floor(rounding_indicator)
                        else:
                            self.__new_font_size = math.ceil(rounding_indicator)
                        # once font size of 1 is reached, we need to make sure to keep track of scaling trends as we continue to demagnify image
                        # if not, we will scale the font size too quickly while magnifying the image
                        # the line of code below accomplishes the tracking by essentially recording the current number of scaling events
                        label_font_size = rounding_indicator 
                        # find all text objects according to "text" tag assigned to defect labels
                        for child_widget in self.canvas.find_withtag("text"):
                            self.canvas.itemconfigure(child_widget, font=("Arial", -self.__new_font_size))
                        # Redraw some figures before showing image on the screen
                        self.redraw_figures()  # method for child classes
                        self.__show_image()
                
                    def __keystroke(self, event):
                        """ Scrolling with the keyboard.
                            Independent from the language of the keyboard, CapsLock, <Ctrl>+<key>, etc. """
                        if event.state - self.__previous_state == 4:  # means that the Control key is pressed
                            pass  # do nothing if Control key is pressed
                        else:
                            self.__previous_state = event.state  # remember the last keystroke state
                            # Up, Down, Left, Right keystrokes
                            if event.keycode in [68, 39, 102]:  # scroll right: keys 'D', 'Right' or 'Numpad-6'
                                self.__scroll_x('scroll',  1, 'unit', event=event)
                            elif event.keycode in [65, 37, 100]:  # scroll left: keys 'A', 'Left' or 'Numpad-4'
                                self.__scroll_x('scroll', -1, 'unit', event=event)
                            elif event.keycode in [87, 38, 104]:  # scroll up: keys 'W', 'Up' or 'Numpad-8'
                                self.__scroll_y('scroll', -1, 'unit', event=event)
                            elif event.keycode in [83, 40, 98]:  # scroll down: keys 'S', 'Down' or 'Numpad-2'
                                self.__scroll_y('scroll',  1, 'unit', event=event)
                
                    def crop(self, bbox):
                        """ Crop rectangle from the image and return it """
                        if self.__huge:  # image is huge and not totally in RAM
                            band = bbox[3] - bbox[1]  # width of the tile band
                            self.__tile[1][3] = band  # set the tile height
                            self.__tile[2] = self.__offset + self.imwidth * bbox[1] * 3  # set offset of the band
                            self.__image.close()
                            self.__image = Image.open(self.path)  # reopen / reset image
                            self.__image.size = (self.imwidth, band)  # set size of the tile band
                            self.__image.tile = [self.__tile]
                            return self.__image.crop((bbox[0], 0, bbox[2], band))
                        else:  # image is totally in RAM
                            return self.__pyramid[0].crop(bbox)
                
                    def destroy(self):
                        """ ImageFrame destructor """
                        self.__image.close()
                        map(lambda i: i.close, self.__pyramid)  # close all pyramid images
                        del self.__pyramid[:]  # delete pyramid list
                        del self.__pyramid  # delete pyramid variable
                        self.canvas.destroy()
                        self.__imframe.destroy()
                
                class TileWindow(ttk.Frame):
                    """ Main tile window class """
                    def __init__(self, mainframe, path, window_name):
                        """ Initialize the main Frame """
                        ttk.Frame.__init__(self, master=mainframe)
                        self.master.title(window_name)
                        self.master.geometry('800x600')  # size of the main window
                        self.master.rowconfigure(0, weight=1)  # make the CanvasImage widget expandable
                        self.master.columnconfigure(0, weight=1)
                        canvas = CanvasImage(self.master, path)  # create widget
                        canvas.grid(row=0, column=0)  # show widget
        
                
                filename = image_origin + img_row[2]  # place path to your image here
                tile_name = img_row[2] # get the name of the currently selected tile 
                print(tile_name)
                # create an object of the TileWindow class
                app = TileWindow(tk.Toplevel(), path=filename, window_name = tile_name)
                app.mainloop()

    class DefectSizeBinning:
        """ Defect Size Binning Class """
        def __init__(self):       
            # instance variable initialization
            self.defect_binning_window = None
            self.row_num = None
            self.list_of_entry_fields = None
            self.button_set_binning = None
            self.button_close = None
            self.inf_bin_color = None
            
            # call for initial panel creation
            self.main_binning_window()
            
        def main_binning_window(self):
            """ Create defect binning settings panel """
            # create the defect binning tkinter window
            self.defect_binning_window = tk.Toplevel()
            self.defect_binning_window.title('Defect Size Binning')

            self.row_num = len(mosaic_obj.mosaic_settings_obj.binning_colors) # dummy variable keeps track of number of defect binning ranges
            self.list_of_entry_fields = np.empty((0,2)) # list to hold all entry variables for referencing
            
            # button used to add another defect binning range
            button_add_range = tk.Button(self.defect_binning_window, text='Add Range', width = 11, command = self.add_binning_range)
            button_add_range.grid(row = 0, column = 0)

            # button to remove defect binning range
            button_remove_range = tk.Button(self.defect_binning_window, text='Remove Range', width = 11, command = self.remove_binning_range)
            button_remove_range.grid(row = 0, column = 1)

            # button to accept binning and send to main mosaic settings window
            self.button_set_binning = tk.Button(self.defect_binning_window, text='Set Binning', width = 10, command = self.set_binning_options)
            self.button_set_binning.grid(row = self.row_num + 2, column = 3)

            # button to close window without setting new binning
            self.button_close = tk.Button(self.defect_binning_window, text='Close', width = 10, command=self.defect_binning_window.destroy)
            self.button_close.grid(row = self.row_num + 3, column = 3)

            # labels for the two columns, binning ceiling value and binning color value
            tk.Label(self.defect_binning_window, text='Bin Ceiling').grid(row=1, column = 0, columnspan = 1)
            tk.Label(self.defect_binning_window, text='Bin Color').grid(row=1, column = 1, columnspan = 1)

            # add in infinity bin (bin that starts at final finite bin ceiling and goes to infinity)
            self.inf_bin_color = tk.Entry(self.defect_binning_window, 
                                          textvariable = tk.StringVar(self.defect_binning_window, value = mosaic_obj.mosaic_settings_obj.inf_bin_color), width = 8)
            tk.Label(self.defect_binning_window, text='Infinity Bin Color').grid(row=0, column = 3, columnspan = 1)
            self.inf_bin_color.grid(row=0, column=4)

            # populate with previously saved choices...
            for i in range(self.row_num):
                self.list_of_entry_fields = np.append(self.list_of_entry_fields,
                                            [[tk.Entry(self.defect_binning_window, textvariable = tk.StringVar(self.defect_binning_window, value = mosaic_obj.mosaic_settings_obj.binning_ranges[i]), width = 10),
                                              tk.Entry(self.defect_binning_window, textvariable = tk.StringVar(self.defect_binning_window, value = mosaic_obj.mosaic_settings_obj.binning_colors[i]), width = 10)]],axis = 0)
                self.list_of_entry_fields[-1][0].grid(row=i+2, column=0)
                self.list_of_entry_fields[-1][1].grid(row=i+2, column=1)
            
        def add_binning_range(self):
            """ Adds a new defect binning range entry """
            # iterate the number of fields we have
            self.row_num = self.row_num + 1
           
            self.list_of_entry_fields = np.append(self.list_of_entry_fields,
                                            [[tk.Entry(self.defect_binning_window, width = 10),
                                              tk.Entry(self.defect_binning_window, width = 10)]],axis = 0)
            
            # after appending we can use -1 to reference the last item appened
            self.list_of_entry_fields[-1][0].grid(row=self.row_num + 1, column=0)
            self.list_of_entry_fields[-1][1].grid(row=self.row_num + 1, column=1)
            # now update the location of the accept and close buttons
            self.button_set_binning.grid(row = self.row_num + 2, column = 3)
            self.button_close.grid(row = self.row_num + 3, column = 3)

        def remove_binning_range(self):
            """ Removes most recent defect binning range entry """
            if len(self.list_of_entry_fields) > 0:
                (self.defect_binning_window.winfo_children()[-1]).destroy()
                (self.defect_binning_window.winfo_children()[-1]).destroy()
                # update the number of fields
                self.list_of_entry_fields = self.list_of_entry_fields[:-1]
                self.row_num = self.row_num - 1
                # now update the location of the accept and close buttons
                self.button_set_binning.grid(row = self.row_num + 2, column = 3)
                self.button_close.grid(row = self.row_num + 3, column = 3)
            else:
                print('No binning ranges to remove')

        def set_binning_options(self):
            """ Send current binning options back to MosaicSettings """
            def get_var_value(x):
                return x.get()
            
            # we vectorize a function to get values out of StringVar
            vectorized = np.vectorize(get_var_value)
            if self.list_of_entry_fields.size == 0:
                mosaic_obj.mosaic_settings_obj.binning_ranges = np.array([])
                mosaic_obj.mosaic_settings_obj.binning_colors = np.array([])
            else:
                mosaic_obj.mosaic_settings_obj.binning_ranges = vectorized(self.list_of_entry_fields[:,0:1]).flatten().astype(float)
                mosaic_obj.mosaic_settings_obj.binning_colors = vectorized(self.list_of_entry_fields[:,1:2]).flatten()
            mosaic_obj.mosaic_settings_obj.inf_bin_color = self.inf_bin_color.get()
            mosaic_obj.mosaic_settings_obj.which_binning_show = "SIZE"
    
    class DefectTypeBinning:
        """ Defect Type Binning Class """
        def __init__(self):     
            # instance variable initialization
            self.defect_binning_window = None
            self.row_num = None
            self.list_of_entry_fields = None
            self.button_set_binning = None
            self.button_close = None
    
            # call for initial panel creation
            self.main_binning_window()
            
        def main_binning_window(self):
            """ Create defect type binning settings panel """
            # create the defect binning tkinter window
            self.defect_binning_window = tk.Toplevel()
            self.defect_binning_window.title('Defect Class Binning')

            self.row_num = len(mosaic_obj.defect_type_data) # dummy variable records number of defect classification bins
            self.list_of_entry_fields = np.empty((0,2)) # list to hold all entry variables for referencing

            # button to accept binning and send to main mosaic settings window
            self.button_set_binning = tk.Button(self.defect_binning_window, text='Set Binning', width = 10, command = self.set_binning_options)
            self.button_set_binning.grid(row = self.row_num + 2, column = 3)

            # button to close window without setting new binning
            self.button_close = tk.Button(self.defect_binning_window, text='Close', width = 10, command=self.defect_binning_window.destroy)
            self.button_close.grid(row = self.row_num + 3, column = 3)

            # labels for the two columns, binning color value and bin class name
            tk.Label(self.defect_binning_window, text='Bin Class Color').grid(row=1, column = 1, columnspan = 1)
            tk.Label(self.defect_binning_window, text='Bin Class Name').grid(row=1, column = 0, columnspan = 1)
        
            # populate with previously saved choices...
            # the number of entries is automatically set by the number of defect class names in the chosen analysis
            # also check first if defect classes exist for chosen analysis ID
            if mosaic_obj.defect_type_data.size == 0:
                tk.Label(self.defect_binning_window, text='---NO CLASSES IN CHOSEN ANALYSIS---').grid(row=2, column = 0, columnspan = 2)
            else:
                for i, type_entry in enumerate(mosaic_obj.defect_type_data[:,[0, 2]]):
                    if mosaic_obj.mosaic_settings_obj.binning_type_colors.size == 0:
                        self.list_of_entry_fields = np.append(self.list_of_entry_fields,
                                                    [[tk.Label(self.defect_binning_window, text = type_entry[1]),
                                                      tk.Entry(self.defect_binning_window, textvariable = tk.StringVar(self.defect_binning_window), width = 10)]],axis = 0)
                    else:
                        self.list_of_entry_fields = np.append(self.list_of_entry_fields,
                                                    [[tk.Label(self.defect_binning_window, text = type_entry[1]),
                                                      tk.Entry(self.defect_binning_window, textvariable = tk.StringVar(self.defect_binning_window, value = mosaic_obj.mosaic_settings_obj.binning_type_colors[i]), width = 10)]],axis = 0)    
                    self.list_of_entry_fields[-1][0].grid(row=i+2, column=0)
                    self.list_of_entry_fields[-1][1].grid(row=i+2, column=1)

        def set_binning_options(self):
            """ Send current binning options back to MosaicSettings """
            # check first if defect classes exist for chosen analysis ID
            if mosaic_obj.defect_type_data.size == 0:
                return
            else:
                def get_var_value(x):
                    return x.get()

                # we vectorize a function to get values out of StringVar
                vectorized = np.vectorize(get_var_value)
                mosaic_obj.mosaic_settings_obj.binning_type_colors = vectorized(self.list_of_entry_fields[:,1:2]).flatten()
                mosaic_obj.mosaic_settings_obj.which_binning_show = "CLASS"
    
    class MosaicSettings:
        """ Mosaic Settings Class """
        def __init__(self):
            # the binning ranges and colors below are received by the DefectBinning class (defect binning settings)
            self.binning_ranges = mosaic_obj.binning_ranges # the desired binning ranges given in um^2
            self.binning_colors = mosaic_obj.binning_colors # the desired binning colors for size binning
            self.binning_type_colors = mosaic_obj.binning_type_colors # the desired colors for defect type binning
            self.inf_bin_color = mosaic_obj.inf_bin_color # the desired infinity bin color
            self.which_binning_show = mosaic_obj.which_binning_show # determines which binning type to display on mosaic
            
            # instance variable initialization
            self.mosaic_settings_window = None
            self.font_size_defect_label = None
            self.defect_size_binning_obj = None
            self.defect_type_binning_obj = None
            self.defect_mark_size = None
            self.defect_label_text_choices = np.copy(mosaic_obj.defect_label_text_choices) # create copy to avoid overwritting
            self.analysis_id = mosaic_obj.analysis_id
            
            # call function to create initial settings panel
            self.main_mosaic_settings()

        def main_mosaic_settings(self):
            """ Create initial advanced mosaic settings panel """   
            # create the mosaic settings tkinter window
            self.mosaic_settings_window = tk.Toplevel()
            self.mosaic_settings_window.title('Mosaic Advanced Settings')

            # font size of defect label text
            self.font_size_defect_label = tk.StringVar(self.mosaic_settings_window, value = mosaic_obj.font_size_defect_label)
            tk.Label(self.mosaic_settings_window, text='Defect Label Font Size').grid(row=1, column = 0, columnspan = 1)
            entry_font_size_defect_label = tk.Entry(self.mosaic_settings_window, textvariable = self.font_size_defect_label, width = 5)
            entry_font_size_defect_label.grid(row = 1, column = 1, columnspan = 1)
            
            # change the size of the defect markers on the mosaic canvas
            self.defect_mark_size = tk.StringVar(self.mosaic_settings_window, value = mosaic_obj.defect_mark_size)
            tk.Label(self.mosaic_settings_window, text='Defect Mark Size').grid(row=2, column = 0, columnspan = 1)
            entry_mark_resize = tk.Entry(self.mosaic_settings_window, textvariable = self.defect_mark_size, width = 5)
            entry_mark_resize.grid(row = 2, column = 1, columnspan = 1)

            # change the analysis ID and replot defects
            analysis_options = np.insert(root_obj.analysis_options, 0, 'Select Choice')
            self.analysis_id_change = tk.StringVar(self.mosaic_settings_window, value = analysis_options[0])
            tk.Label(self.mosaic_settings_window, text='Analysis ID').grid(row=3, column = 0, columnspan = 1)
            entry_analysis_id_change = ttk.OptionMenu(self.mosaic_settings_window, self.analysis_id_change, *analysis_options)
            entry_analysis_id_change.grid(row = 3, column = 1, columnspan = 3, sticky = 'w')
            # self.analysis_id_change = tk.StringVar(self.mosaic_settings_window, value = mosaic_obj.analysis_id)
            # tk.Label(self.mosaic_settings_window, text='Analysis ID').grid(row=3, column = 0, columnspan = 2)
            # entry_analysis_id_change = tk.Entry(self.mosaic_settings_window, textvariable = self.analysis_id_change, width = 5)
            # entry_analysis_id_change.grid(row = 3, column = 2, columnspan = 2)

            # button to open defect area binning window
            button_defect_binning = tk.Button(self.mosaic_settings_window, text='Size Binning', width = 10, command = self.call_size_binning)
            button_defect_binning.grid(row = 4, column = 0)
            
            # button to open defect class binning window
            button_defect_binning = tk.Button(self.mosaic_settings_window, text='Class Binning', width = 10, command = self.call_type_binning)
            button_defect_binning.grid(row = 5, column = 0)
            
            # button to open defect text label options
            button_defect_label_text = tk.Button(self.mosaic_settings_window, text='Defect Text Options', width = 16, command = self.defect_text_options)
            button_defect_label_text.grid(row = 6, column = 0)

            # button to apply settings
            button_accept = tk.Button(self.mosaic_settings_window, text='Accept', width = 10, command = self.return_choices_mosaic)
            button_accept.grid(row = 5, column = 3)

            # button to close without saving
            button_close = tk.Button(self.mosaic_settings_window, text='Close', width = 10, command=self.mosaic_settings_window.destroy)
            button_close.grid(row = 6, column = 3)

        def call_size_binning(self):
            """ Creates instance of DefectSizeBinning class """
            self.defect_size_binning_obj = DefectSizeBinning()
            
        def call_type_binning(self):
            """ Creates instance of DefectTypeBinning class """
            self.defect_type_binning_obj = DefectTypeBinning()
            
        def defect_text_options(self):
            """ Creates window with defect label text options """
            text_options_window = tk.Toplevel()
            text_options_window.title('Defect Label Text Options')
            
            def set_text_options(checkbox_vars):
                """ Set the current text display options """
                for idx, value in enumerate(checkbox_vars):
                    self.defect_label_text_choices[idx] = bool(value.get())
            
            options = ["DefectID", "ImageID", "AnalysisID", "DeviceID", 
                      "X", "Y", "W", "H", "Area", "Intensity", "IntensityDeviation",
                     "Eccentricity", "Orientation", "XinDevice", "YinDevice", "ClassID",
                     "Score", "Contour"]
            
            checkbox_vars = np.array([]) # keep track of the checkbox variables
            converted_choices = self.defect_label_text_choices.astype(int) # convert to int, tkinter does not like numpy booleans
            
            # now create the checkboxes
            for i, option in enumerate(options):
                checkbox_vars = np.append(checkbox_vars, tk.IntVar(text_options_window, value = converted_choices[i]))
                checkbox = tk.Checkbutton(text_options_window, text=option, variable=checkbox_vars[i])
                checkbox.pack()
            
            # button to apply settings
            button_accept = tk.Button(text_options_window, text='Set Options', 
                                      width = 10, command = lambda arg = checkbox_vars: set_text_options(arg))
            button_accept.pack()
            
            # button to close without saving
            button_close = tk.Button(text_options_window, text='Close', width = 10, command=text_options_window.destroy)
            button_close.pack()
            
            #text_options_window.mainloop()
            
        def return_choices_mosaic(self):
            """ Sends input settings back to MosaicCreator """  
            mosaic_obj.font_size_defect_label = self.font_size_defect_label.get()
            mosaic_obj.binning_ranges = self.binning_ranges
            mosaic_obj.binning_colors = self.binning_colors
            mosaic_obj.binning_type_colors = self.binning_type_colors
            mosaic_obj.which_binning_show = self.which_binning_show
            mosaic_obj.inf_bin_color = self.inf_bin_color
            mosaic_obj.defect_mark_size = self.defect_mark_size.get()
            mosaic_obj.defect_label_text_choices = np.copy(self.defect_label_text_choices)
            # update defect data if needed
            if mosaic_obj.analysis_id != self.analysis_id_change.get() and self.analysis_id_change.get() != 'Select Choice':
                mosaic_obj.analysis_id = self.analysis_id_change.get()
                mosaic_obj.update_analysis_info()
            
            # re-plot the mosaic with the new settings
            # check if user has selected image view only
            if mosaic_obj.image_view_only == 0:
                mosaic_obj.plot_defects()

    class MosaicCreator:
        """ Create Mosaic With Selectable Tiles """
        def __init__(self):
            # initialize variables to default values, may be overwritten by advanced mosaic settings
            self.font_size_defect_label = "20"
            self.defect_mark_size = "3"
            
            # set the ranges and colors for defect size binning to the default received by the root object
            # this may be overwritten by the mosaic settings
            self.binning_ranges = default_binning_ranges 
            self.binning_colors = default_binning_colors 
            self.inf_bin_color = default_inf_bin_color
            
            self.binning_type_colors = np.array([]) # colors for defect classification binning (no default unlike size binning)
            self.which_binning_show = 'SIZE' # determines which color binning to show
            # this array keeps track of the defect info which will be output on the defect label text line
            self.defect_label_text_choices = np.array([False, False, False, False, True, True, False, False, True, False,
                                                       False, False, False, False, False, False, False, False])

            # this instance variable is initially set to what was passed from root
            # may be overwritten by mosaic settings
            self.analysis_id = analysis_id # analysis ID set to instance variable to allow change after plotting
            
            # retrieve user choice of viewing image only (no defect plotting)
            self.image_view_only = root_obj.image_view_only.get()
            
            # more instance variable initializations
            self.canvas = None
            self.binning_frame = None
            self.images = None
            self.mosaic_settings_obj = None
            self.mosaic_image = None
            self.mos_source_width = None
            self.mos_source_height = None
            self.num_defects_type_binning = None
            self.num_defects_size_binning = None

            # create a new tkinter window for plotting the mosaic of the scans
            self.mosaic_window = tk.Toplevel()
            self.sample_name = (db_origin.split("/"))[-1]
            self.mosaic_window.title(self.sample_name + " || " + "Scan ID = " + str(scan_id) + " || " + "Analysis ID = " + str(self.analysis_id))

            # connect to the database containing analysis and scan information
            self.conn = sqlite3.connect(db_origin)
            self.cur = self.conn.cursor()
        
            # sql queries used to retrieve defect and image data
            self.sql_cmd_pos = "SELECT * FROM vwImages WHERE ScanID = ?;" 
            self.sql_cmd_def = "SELECT * FROM vwDefectsLegacy WHERE AnalysisID = ?;" 
            self.sql_cmd_scn = "SELECT * FROM ScanProperties WHERE ScanID = ?"
            self.sql_cmd_typ = "SELECT * FROM DetectionClasses WHERE AnalysisID = ?"
            
            self.image_data = np.array(self.cur.execute(self.sql_cmd_pos,(str(scan_id),)).fetchall()) # fetch all data from image table
            self.defect_data = np.array(self.cur.execute(self.sql_cmd_def,(str(self.analysis_id),)).fetchall()) # fetch all data from defect table
            self.scan_properties = np.array(self.cur.execute(self.sql_cmd_scn,(str(scan_id),)).fetchall()) # fetch all data from scan properties table
            self.defect_type_data = np.array(self.cur.execute(self.sql_cmd_typ,(str(self.analysis_id),)).fetchall()) # fetch all data from detection class table
            
            # call image plotting function upon class object creation
            self.plot_mosaic()

        def update_analysis_info(self):
            """ Function to update defect data, called from MosaicSettings Class """
            self.defect_data = np.array(self.cur.execute(self.sql_cmd_def,(str(self.analysis_id),)).fetchall()) # fetch all data from defect table
            self.defect_type_data = np.array(self.cur.execute(self.sql_cmd_typ,(str(self.analysis_id),)).fetchall()) # fetch all data from detection class table

            # we must reset defect classification binning in both MosaicCreator and MosaicSettings
            # otherwise, if the MosaicSettings window is not closed between analysis ID changes the previous binning is remembered and applied to wrong analysis
            # we can leave area binning alone since it can apply in any analysis
            self.binning_type_colors = np.array([])
            mosaic_obj.mosaic_settings_obj.binning_type_colors = np.array([])
            
            # now update the name of the window
            self.mosaic_window.title(self.sample_name + " || " + "Scan ID = " + str(scan_id) + " || " + "Analysis ID = " + str(self.analysis_id))

        def call_mosaic_settings(self):
            """ Creates instance of MosaicSettings class """
            self.mosaic_settings_obj = MosaicSettings()

        def plot_defects(self):
            """ Plot the defects onto the mosaic created by plot_mosaic function """
            self.canvas.delete("DEFECT_MARK_SIZE_BINNING") # deletes all current defect marks to allow for re-plotting
            self.canvas.delete("DEFECT_MARK_CLASS_BINNING")

            self.num_defects_size_binning = np.zeros([len(self.binning_colors)+1]) # initialize array to hold number of defects per bin for size binning
            self.num_defects_type_binning = np.zeros([len(self.binning_type_colors)+1]) # initialize array to hold number of defects per bin for type binning

            for idx, def_row in enumerate(self.defect_data):

                tile_row_index = np.where(np.any(self.image_data[:,0:1].astype(float) == float(def_row[1]), axis=1))[0] # find the tile where defect resides
                tile_row = float(self.image_data[tile_row_index, 7][0]) # find the Row and Column of the tile in the mosaic image
                tile_column = float(self.image_data[tile_row_index, 8][0])
                tile_width_um = float(self.image_data[tile_row_index, 9][0]) # find width and height of tile in um
                tile_height_um = float(self.image_data[tile_row_index, 10][0])
                tile_width_pix = float(self.image_data[tile_row_index, 11][0]) # find width and height of tile in pixels
                tile_height_pix = float(self.image_data[tile_row_index, 12][0])
                def_x_tile = float(def_row[4]) # obtain the coordinates of defect within its image tile (um)
                def_y_tile = float(def_row[5])

                # find defect coordinates in mosaic, convert to pixels, and scale by number of rows/cols in the mosaic
                x_mosaic = self.mos_tile_width * ((def_x_tile + (tile_column * tile_width_um)) * (tile_width_pix / tile_width_um)) / tile_width_pix
                y_mosaic = self.mos_tile_height * ((def_y_tile + (tile_row * tile_height_um)) * (tile_height_pix / tile_height_um)) / tile_height_pix

                size_adj = float(self.defect_mark_size) # arbitrary scaling value used to control size of defect mark on mosaic
                
                # we will plot multiple copies of each defect overlaid on each other
                # each copy will have a different defect mark color for the different binning types we can choose
                # then we can simply toggle the defect visibility to the user by using tags for each bin type
                
                # get index corresponding to binning range of defect area
                bin_range_index = np.searchsorted(self.binning_ranges, float(def_row[8]))
                # set size-based defect mark color based on binning color corresponding to index found above
                if (bin_range_index > (len(self.binning_ranges) - 1)) or (self.binning_ranges.size == 0):
                    mark_color = self.inf_bin_color
                    self.num_defects_size_binning[len(self.binning_colors)] += 1 # iterate defect count for infinity bin
                else:
                    mark_color = self.binning_colors[bin_range_index]
                    self.num_defects_size_binning[bin_range_index] += 1 # iterate defect count for specific bin
                    
                # set class-based defect mark color based on user binning input
                if self.binning_type_colors.size == 0 or self.defect_type_data.size == 0:
                    mark_type_color = self.inf_bin_color
                    self.num_defects_type_binning[len(self.binning_type_colors)] += 1 # iterate defect count for infinity bin
                else:
                    mark_type_color = self.binning_type_colors[np.where(self.defect_type_data[:,0:1].flatten() == def_row[15])][0]
                    self.num_defects_type_binning[np.where(self.defect_type_data[:,0:1].flatten() == def_row[15])] += 1 # iterate defect count for specific bin
                
                # now plot the defect on the mosaic, we plot multiple overlaid copies for each binning type
                self.canvas.create_oval(x_mosaic - size_adj, y_mosaic - size_adj, 
                                        x_mosaic + size_adj, y_mosaic + size_adj, 
                                        outline = mark_color, fill = mark_color, tags = "DEFECT_MARK_SIZE_BINNING")
                self.canvas.create_oval(x_mosaic - size_adj, y_mosaic - size_adj, 
                                        x_mosaic + size_adj, y_mosaic + size_adj, 
                                        outline = mark_type_color, fill = mark_type_color, tags = "DEFECT_MARK_CLASS_BINNING")
                self.canvas.itemconfigure("DEFECT_MARK_SIZE_BINNING", state="hidden")
                self.canvas.itemconfigure("DEFECT_MARK_CLASS_BINNING", state="hidden")
            
            # by default we will show the defect size binning 
            if self.which_binning_show == "SIZE":
                self.canvas.itemconfigure("DEFECT_MARK_SIZE_BINNING", state="normal")
            if self.which_binning_show == "CLASS":
                self.canvas.itemconfigure("DEFECT_MARK_CLASS_BINNING", state="normal")
                
        def toggle_binning(self, toggle_choice):
            """ Toggles visibility for the desired set of defect binning colors """
            self.which_binning_show = toggle_choice # we must update variable for binning visibility, bug fix
            if toggle_choice == "SIZE":
                self.canvas.itemconfigure("DEFECT_MARK_SIZE_BINNING", state="normal")
                self.canvas.itemconfigure("DEFECT_MARK_CLASS_BINNING", state="hidden")
            if toggle_choice == "CLASS":
                self.canvas.itemconfigure("DEFECT_MARK_SIZE_BINNING", state="hidden")
                self.canvas.itemconfigure("DEFECT_MARK_CLASS_BINNING", state="normal")
                
        def analysis_stats(self):
            """ Displays statistics about the current analysis in new window """   
            # create the statistics window
            ana_stats_window = tk.Toplevel()
            ana_stats_window.title('Analysis Statistics')
    
            # create labels for current binning information and defect counts to display in window
            # check which binning mode is currently selected
            # if defect binning selection is "SIZE"...
            if self.which_binning_show == "SIZE":
                tk.Label(ana_stats_window, text="Bin Ceiling").grid(row=0, column = 0) # create headers
                tk.Label(ana_stats_window, text="Bin Color").grid(row=0, column = 1)
                tk.Label(ana_stats_window, text="Number of Defects").grid(row=0, column = 2)
                ttk.Separator(ana_stats_window, orient = 'horizontal').grid(row = 1, column = 0, columnspan = 3, sticky = 'ew')
                # iterate through all the ranges/colors and create labels for each
                for i in range(len(self.binning_colors)):
                    tk.Label(ana_stats_window, text=str(self.binning_ranges[i])).grid(row=i+2, column = 0)
                    tk.Label(ana_stats_window, text=str(self.binning_colors[i]), fg=str(self.binning_colors[i])).grid(row=i+2, column = 1)
                    tk.Label(ana_stats_window, text=str(int(self.num_defects_size_binning[i]))).grid(row=i+2, column = 2)
                tk.Label(ana_stats_window, text="Infinity").grid(row=len(self.binning_colors)+3, column = 0)
                tk.Label(ana_stats_window, text=str(self.inf_bin_color), fg=str(self.inf_bin_color)).grid(row=len(self.binning_colors)+3, column = 1)
                tk.Label(ana_stats_window, text=str(int(self.num_defects_size_binning[-1]))).grid(row=len(self.binning_colors)+3, column = 2)
    
                # button to close window
                button_close = tk.Button(ana_stats_window, text='Close', width = 10, command=ana_stats_window.destroy)
                button_close.grid(row = len(self.binning_colors)+4, column = 2, columnspan = 1)

            # if defect binning selection is "CLASS"...
            if self.which_binning_show == "CLASS":
                tk.Label(ana_stats_window, text="Defect Class Name").grid(row=0, column = 0) # create headers
                tk.Label(ana_stats_window, text="Bin Color").grid(row=0, column = 1)
                tk.Label(ana_stats_window, text="Number of Defects").grid(row=0, column = 2)
                ttk.Separator(ana_stats_window, orient = 'horizontal').grid(row = 1, column = 0, columnspan = 3, sticky = 'ew')
                # first check if any class binning has been applied (or if classes even exist for this analysis)
                if len(self.binning_type_colors) == 0:
                    tk.Label(ana_stats_window, text="No Binning Set Yet!").grid(row=2, column = 0)
                    tk.Label(ana_stats_window, text=str(self.inf_bin_color), fg=str(self.inf_bin_color)).grid(row=2, column = 1)
                    tk.Label(ana_stats_window, text=str(int(self.num_defects_type_binning[-1]))).grid(row=2, column = 2)
                else:
                    # iterate through all the colors/class names and create labels for each
                    for i in range(len(self.binning_type_colors)):
                        tk.Label(ana_stats_window, text=str(self.defect_type_data[i][2])).grid(row=i+2, column = 0)
                        tk.Label(ana_stats_window, text=str(self.binning_type_colors[i]), fg=str(self.binning_type_colors[i])).grid(row=i+2, column = 1)
                        tk.Label(ana_stats_window, text=str(int(self.num_defects_type_binning[i]))).grid(row=i+2, column = 2)
        
                # button to close window
                button_close = tk.Button(ana_stats_window, text='Close', width = 10, command=ana_stats_window.destroy)
                button_close.grid(row = len(self.binning_type_colors)+3, column = 2, columnspan = 1)
        
        def plot_mosaic(self):
            """ Plot the mosaic onto a selectable canvas """                
            # create new label in root window which tracks image loading progress
            # first destroy previous loading progress label
            for child in root_obj.root.winfo_children():
                if "LOAD_PROGRESS" in child.bindtags():
                    child.destroy()
            load_progress = tk.Label(root_obj.root, text='Loading Image...')
            load_progress.bindtags(load_progress.bindtags() + ("LOAD_PROGRESS",)) # add custom tag for deletion purposes
            load_progress.grid(row=6, column = 2, columnspan = 2)
            root_obj.root.update()

            list_of_images = np.array(next(os.walk(image_origin))[2]) # list of images from directory
            mosaic_image_name = list_of_images[np.flatnonzero(np.core.defchararray.find(list_of_images,'Mosaic')!=-1)[0]]
            image = Image.open(image_origin + mosaic_image_name)
            self.mos_source_width, self.mos_source_height = image.size # get the native size of the mosaic image
            image = image.resize((round(self.mos_source_width/image_scale),round(self.mos_source_height/image_scale)),Image.LANCZOS) # resize mosaic image and interpolate
            self.mos_resize_width, self.mos_resize_height = image.size # get the new size of mosaic image

            # create the canvas with size according to resized mosaic image
            self.canvas = Canvas(self.mosaic_window, width = self.mos_resize_width, height = self.mos_resize_height, bd = 0)

            # button for advanced settings
            button_advanced = tk.Button(self.mosaic_window, text='Advanced', width = 10, command = self.call_mosaic_settings)

            # button for opening analysis statistics window
            button_analy_stats = tk.Button(self.mosaic_window, text='Analysis Stats', width = 10, command = self.analysis_stats)
            
            # button for showing size-binned defect colors
            button_size_binning = tk.Button(self.mosaic_window, text='Size Binning', width = 10, command = lambda: self.toggle_binning("SIZE"))
            
            # button for showing class-binned defect colors
            button_class_binning = tk.Button(self.mosaic_window, text='Class Binning', width = 10, command = lambda: self.toggle_binning("CLASS"))
            
            self.mosaic_image = ImageTk.PhotoImage(image) # create tkinter photo object
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.mosaic_image, tags = "IMAGE_TILE")
            
            # now prepare for plotting defects onto canvas
            # for the given scan image data, find the max number of rows and columns
            # this will be used to scale an individual tile image within the mosaic
            row_numbers = (self.image_data[:,7:8]).astype(int)
            col_numbers = (self.image_data[:,8:9]).astype(int)
            max_rows = max(row_numbers)[0] + 1
            max_cols = max(col_numbers)[0] + 1

            # obtain size of one tile in pixels in the mosaic
            # based on the number of rows and columns in the mosaic
            self.mos_tile_width = self.mos_resize_width / max_cols
            self.mos_tile_height = self.mos_resize_height / max_rows
            
            # check if user has selected image view only
            if self.image_view_only == 0: 
                self.plot_defects() # function that plots the defects onto the canvas created above
                
            self.canvas.bind('<Button-1>', lambda event: clicked(self, event)) # makes mosaic selectable
            
            load_progress.config(text = 'Done Loading!') # update root window upon image load completion
            root_obj.root.update()

            # place all the items according to grid
            self.canvas.grid(row = 0, column = 0)
            button_advanced.grid(row = 1, column = 0)
            button_size_binning.grid(row = 1, column = 0, sticky = 'e')
            button_class_binning.grid(row = 2, column = 0, sticky = 'e')
            button_analy_stats.grid(row = 3, column = 0, sticky = 'e')

    # create object of MosaicCreator
    mosaic_obj = MosaicCreator()
    mosaic_obj.mosaic_window.mainloop()

class DefectSizeBinningRoot:
    """ Class for selecting default colors and ranges for defect size binning
        Will be applied to all mosaics plotted from root window """
    def __init__(self):       
        # instance variable initialization
        self.defect_binning_window = None
        self.row_num = None
        self.list_of_entry_fields = None
        self.button_set_binning = None
        self.button_close = None
        self.inf_bin_color = None

        # call for initial panel creation
        self.main_binning_window()

    def main_binning_window(self):
        """ Create defect binning settings panel """
        # create the defect binning tkinter window
        self.defect_binning_window = tk.Toplevel()
        self.defect_binning_window.title('Defect Size Binning')

        self.row_num = len(root_obj.root_settings_obj.binning_colors) # dummy variable keeps track of number of defect binning ranges
        self.list_of_entry_fields = np.empty((0,2)) # list to hold all entry variables for referencing

        # button used to add another defect binning range
        button_add_range = tk.Button(self.defect_binning_window, text='Add Range', width = 11, command = self.add_binning_range)
        button_add_range.grid(row = 0, column = 0)

        # button to remove defect binning range
        button_remove_range = tk.Button(self.defect_binning_window, text='Remove Range', width = 11, command = self.remove_binning_range)
        button_remove_range.grid(row = 0, column = 1)

        # button to accept binning and send to main mosaic settings window
        self.button_set_binning = tk.Button(self.defect_binning_window, text='Set Binning', width = 10, command = self.set_binning_options)
        self.button_set_binning.grid(row = self.row_num + 2, column = 3)

        # button to close window without setting new binning
        self.button_close = tk.Button(self.defect_binning_window, text='Close', width = 10, command=self.defect_binning_window.destroy)
        self.button_close.grid(row = self.row_num + 3, column = 3)

        # labels for the two columns, binning ceiling value and binning color value
        tk.Label(self.defect_binning_window, text='Bin Ceiling').grid(row=1, column = 0, columnspan = 1)
        tk.Label(self.defect_binning_window, text='Bin Color').grid(row=1, column = 1, columnspan = 1)

        # add in infinity bin (bin that starts at final finite bin ceiling and goes to infinity)
        self.inf_bin_color = tk.Entry(self.defect_binning_window, 
                                      textvariable = tk.StringVar(self.defect_binning_window, value = root_obj.root_settings_obj.inf_bin_color), width = 8)
        tk.Label(self.defect_binning_window, text='Infinity Bin Color').grid(row=0, column = 3, columnspan = 1)
        self.inf_bin_color.grid(row=0, column=4)

        # populate with previously saved choices...
        for i in range(self.row_num):
            self.list_of_entry_fields = np.append(self.list_of_entry_fields,
                                        [[tk.Entry(self.defect_binning_window, textvariable = tk.StringVar(self.defect_binning_window, value = root_obj.root_settings_obj.binning_ranges[i]), width = 10),
                                          tk.Entry(self.defect_binning_window, textvariable = tk.StringVar(self.defect_binning_window, value = root_obj.root_settings_obj.binning_colors[i]), width = 10)]],axis = 0)
            self.list_of_entry_fields[-1][0].grid(row=i+2, column=0)
            self.list_of_entry_fields[-1][1].grid(row=i+2, column=1)

    def add_binning_range(self):
        """ Adds a new defect binning range entry """
        # iterate the number of fields we have
        self.row_num = self.row_num + 1

        self.list_of_entry_fields = np.append(self.list_of_entry_fields,
                                        [[tk.Entry(self.defect_binning_window, width = 10),
                                          tk.Entry(self.defect_binning_window, width = 10)]],axis = 0)

        # after appending we can use -1 to reference the last item appened
        self.list_of_entry_fields[-1][0].grid(row=self.row_num + 1, column=0)
        self.list_of_entry_fields[-1][1].grid(row=self.row_num + 1, column=1)
        # now update the location of the accept and close buttons
        self.button_set_binning.grid(row = self.row_num + 2, column = 3)
        self.button_close.grid(row = self.row_num + 3, column = 3)

    def remove_binning_range(self):
        """ Removes most recent defect binning range entry """
        if len(self.list_of_entry_fields) > 0:
            (self.defect_binning_window.winfo_children()[-1]).destroy()
            (self.defect_binning_window.winfo_children()[-1]).destroy()
            # update the number of fields
            self.list_of_entry_fields = self.list_of_entry_fields[:-1]
            self.row_num = self.row_num - 1
            # now update the location of the accept and close buttons
            self.button_set_binning.grid(row = self.row_num + 2, column = 3)
            self.button_close.grid(row = self.row_num + 3, column = 3)
        else:
            print('No binning ranges to remove')

    def set_binning_options(self):
        """ Send current binning options back to MosaicSettings """
        def get_var_value(x):
            return x.get()

        # we vectorize a function to get values out of StringVar
        vectorized = np.vectorize(get_var_value)
        if self.list_of_entry_fields.size == 0:
            root_obj.root_settings_obj.binning_ranges = np.array([])
            root_obj.root_settings_obj.binning_colors = np.array([])
        else:
            root_obj.root_settings_obj.binning_ranges = vectorized(self.list_of_entry_fields[:,0:1]).flatten().astype(float)
            root_obj.root_settings_obj.binning_colors = vectorized(self.list_of_entry_fields[:,1:2]).flatten()
        root_obj.root_settings_obj.inf_bin_color = self.inf_bin_color.get()
    
class RootSettings:
    """ Advanced Settings Class for Root Window """ 
    def __init__(self):
        
        # instance variable initialization
        self.adv_window = None
        self.binning_colors = root_obj.binning_colors # set the colors and ranges for size binning to the root initially
        self.binning_ranges = root_obj.binning_ranges
        self.inf_bin_color = root_obj.inf_bin_color
        self.defect_root_size_binning_obj = None
        
        # call initial panel function
        self.initial_panel_root()

    def initial_panel_root(self):
        """ Create initial advanced settings panel from the Root window """   
        self.adv_window = tk.Toplevel()
        self.adv_window.title('Advanced Settings')
        
        # button to open window used to modify default size binning applied to all mosaics plotted from root
        button_defect_binning = tk.Button(self.adv_window, text='Default Size Binning', width = 17, command = self.call_defect_binning_root)
        button_defect_binning.grid(row = 0, column = 0)

        button_accept = tk.Button(self.adv_window, text='Accept', width = 10, command = self.return_choices_root)
        button_accept.grid(row = 1, column = 3)

        button_close = tk.Button(self.adv_window, text='Close', width = 10, command=self.adv_window.destroy)
        button_close.grid(row = 2, column = 3)
    
    def call_defect_binning_root(self):
            """ Creates instance of DefectSizeBinningRoot class """
            self.defect_root_size_binning_obj = DefectSizeBinningRoot()
            
    def return_choices_root(self):
        """ Sends input settings back to Root """
        root_obj.binning_ranges = self.binning_ranges
        root_obj.binning_colors = self.binning_colors
        root_obj.inf_bin_color = self.inf_bin_color
         
class Root:
    """ Class to create initial Root gui window """
    def __init__(self):
        
        # instance variable initialization
        self.root = None
        self.img_loc_var = None # path to folder containing images for specific scan
        self.scan_dir_var = None # path to folder containing all scan folders
        self.db_file_var = None
        self.scan_id_var = None
        self.ana_id_var = None
        self.image_scale_var = None
        self.root_settings_obj = None
        self.e1 = None
        self.e2 = None
        self.e3 = None
        self.e4 = None
        self.e5 = None
        self.font_size_input = None
        self.image_view_only = None
        self.scan_options = np.array(['Select Choice'])
        self.analysis_options = np.array(['Select Choice'])
        # colors and ranges for defect size binning, here set to some arbitrary values
        # can be modified in root settings window and act as defaults that are passed to the mosaic object upon plotting
        self.binning_ranges = np.array([16000, 32000, 64000, 112000, 160000])
        self.binning_colors = np.array(['aqua', 'chartreuse3', 'royalblue3', 'goldenrod1', 'magenta3'])
        self.inf_bin_color = 'red'
        #self.disable_first_call = 0 # this variable ensures the scan_choice function is not called upon scan_id_var initialization
        
        # call function to create main panel
        self.main_root_window()
        
    def main_root_window(self):
        """ Create the main root panel """
        
        self.root = tk.Tk()
        self.root.title('Defect Viewer v1.6.4')

        # create variables for input in Root gui
        self.scan_dir_var = tk.StringVar() # path to folder containing all scan folders
        self.db_file_var = tk.StringVar() # path to database file
        self.scan_id_var = tk.StringVar(self.root, value = self.scan_options[0]) # Scan ID
        self.scan_id_var.trace('w', self.scan_select) # cause scan selection to update analysis option menu
        self.ana_id_var = tk.StringVar(self.root, value = self.analysis_options[0]) # Analysis ID
        self.image_scale_var = tk.StringVar() # Desired size of tiles in mosaic
        
        # initialize advanced settings variables to default values
        # will be overwritten by user input if desired
        self.font_size_input = tk.StringVar(self.root, value = '6')

        # button to open embedded pdf of software manual
        button_open_instruct = tk.Button(self.root, text='?', width = 3, command=self.open_instructions)
        button_open_instruct.grid(row = 0, column = 4, columnspan = 1, sticky = 'e')
        
        # text field to enter location of directory containing scan folders
        tk.Label(self.root, text='Scans Directory').grid(row = 0, column = 0, columnspan = 1)
        self.e1 = tk.Entry(self.root, textvariable = self.scan_dir_var, width = 20)
        self.e1.grid(row = 0, column = 2, columnspan = 1)
        
        # text field to enter location of database file
        tk.Label(self.root, text='Database File').grid(row = 1, column = 0, columnspan = 1)
        self.e2 = tk.Entry(self.root, textvariable = self.db_file_var, width = 20)
        self.e2.grid(row = 1, column = 2, columnspan = 1)
        
        # dropdown menu to select scan ID
        tk.Label(self.root, text='Scan ID').grid(row = 3, column = 0, columnspan = 1)
        self.e3 = ttk.OptionMenu(self.root, self.scan_id_var, *self.scan_options)
        self.e3.grid(row = 3, column = 2, columnspan = 1, sticky = 'w')
        
        # dropdown menu to select analysis ID
        tk.Label(self.root, text='Analysis ID').grid(row = 4, column = 0, columnspan = 1)
        self.e4 = ttk.OptionMenu(self.root, self.ana_id_var, *self.analysis_options)
        self.e4.grid(row = 4, column = 2, columnspan = 1, sticky = 'w')
        
        # text field to enter image scale reduction factor
        tk.Label(self.root, text='Image Scale').grid(row=5, column = 0, columnspan = 1)
        self.e5 = tk.Entry(self.root, textvariable = self.image_scale_var, width = 10)
        self.e5.grid(row = 5, column = 2, columnspan = 1, sticky = 'w')

        # button to set the image and database paths, updating scan and analysis option menus
        button_set_paths = tk.Button(self.root, text='Set Image and DB paths', command=self.set_paths)
        button_set_paths.grid(row = 2, column = 1, columnspan = 3, sticky = 'w')
        
        # these buttons allow the file explorer to be opened to receive directory inputs
        button_file = tk.Button(self.root, text='...', width = 3, command=self.browse_file)
        button_directory = tk.Button(self.root, text='...', width = 3, command=self.browse_directory)
        button_file.grid(row = 1, column = 4, columnspan = 1, sticky = 'w')
        button_directory.grid(row = 0, column = 4, columnspan = 1, sticky = 'w')

        # these buttons open windows displaying information about the currently selected scan/analysis IDs
        button_scan_props = tk.Button(self.root, text='Scan Props', command=self.scan_props)
        button_scan_props.grid(row = 3, column = 4, columnspan = 1, sticky = 'w')
        button_analysis_props = tk.Button(self.root, text='Analysis Props', command=self.analysis_props)
        button_analysis_props.grid(row = 4, column = 4, columnspan = 1, sticky = 'w')
        
        # this button opens up advanced settings
        button_advanced = tk.Button(self.root, text='Advanced', width = 10, command=self.advanced_settings)
        button_advanced.grid(row = 6, column = 0, columnspan = 1)
        
        # create a checkbox to signal when to only open image and not plot defects
        self.image_view_only = tk.IntVar(self.root, value = 0)
        checkbox_seq = tk.Checkbutton(self.root, text='Image Viewer Only', variable=self.image_view_only)
        checkbox_seq.grid(row = 7, column = 0, columnspan = 3, sticky = 'w')
        
        # these two buttons either plot using the input info, or close out of the software
        # button_plot = tk.Button(self.root, text='Plot', width = 10,  
        #                         command = lambda arg = self.img_loc_var, arg1 = self.db_file_var, arg2 = self.scan_id_var, 
        #                         arg3 = self.ana_id_var, arg4 = self.image_scale_var: defect_viewer(self, arg, arg1, arg2, arg3, arg4))
        button_plot = tk.Button(self.root, text='Plot', width = 10, command =  self.call_defect_viewer)
        button_close = tk.Button(self.root, text='Close', width = 10, command=self.root.destroy)
        button_plot.grid(row = 6, column = 4, columnspan = 1)
        button_close.grid(row = 7, column = 4, columnspan = 1)
        
    def open_instructions(self):
        """ Displays an embedded pdf of the instruction manual """
        instruct_window = tk.Toplevel()
        instruct_window.geometry("700x780")
        instruct_window.title('Instruction Manual')
        
        # Create an object of Class ShowPdf
        v1 = ShowPdf()
        
        # Add the PDF to the GUI
        # simultaneously we capture the image array and save it to an instance variable to avoid garbage collection
        v2, self.save_pdf_imgs = v1.pdf_view(instruct_window, pdf_location="\\\\cam-vpnap-nas1\\nSpec\\Defect Viewer App\\v1.0\\defect_viewer_v1.0_tutorial.pdf", width=700, height=500)
        
        # Pack the PDF viewer in the GUI
        v2.pack(pady=10)
    
    def call_defect_viewer(self):
        """ Calls the defect_viewer function which initiates mosaic plotting """
        # check that all required fields are filled
        if self.ana_id_var.get() == 'Select Choice' or self.scan_id_var.get() == 'Select Choice' or not self.image_scale_var.get().isdigit():
            print('Please select a Scan ID, Analysis ID, and enter an integer for Image Scale before plotting')
        else:
            defect_viewer(self)

    def analysis_props(self):
        """ Displays analysis properties from currently selected analysis ID """
        if self.ana_id_var.get() == 'Select Choice':
            print('Please select an analysis ID first')
        else:    
            conn = sqlite3.connect(self.e2.get())
            cur = conn.cursor()

            # sql query used to retrieve scan info
            sql_cmd_ana_prop = "SELECT * FROM AnalysisProperties WHERE AnalysisID = ?;"
            sql_cmd_analysis = "SELECT * FROM Analysis WHERE AnalysisID = ?;"
            sql_cmd_analyzer = "SELECT * FROM Analyzers;"

            ana_prop_info = np.array(cur.execute(sql_cmd_ana_prop,(str(self.ana_id_var.get()),)).fetchall()) # fetch all data from Analysis Properties table
            analysis_info = np.array(cur.execute(sql_cmd_analysis,(str(self.ana_id_var.get()),)).fetchall()) # fetch all data from Analysis table
            analyzer_info = np.array(cur.execute(sql_cmd_analyzer).fetchall()) # fetch all data from Analyzers table

            # create the properties window
            ana_prop_window = tk.Toplevel()
            ana_prop_window.title('Analysis Properties')

            # retrieve properties of interest
            analyzer_type = analyzer_info[np.where(analyzer_info[:,0] == analysis_info[0][3])[0][0], 3]
            num_defects = analysis_info[0][10]

            # place property variables into list
            prop_list = [analyzer_type, num_defects]

            # property labels of interest in user-friendly form
            output_labels = np.array(['Analyzer Type', 'Number of Defects'])

            # create all labels and corresponding values
            for idx, label in enumerate(output_labels):
                tk.Label(ana_prop_window, text = f"{label:<30}").grid(row = 2 * idx, column = 0, columnspan = 1, sticky = 'w')
                tk.Label(ana_prop_window, text = prop_list[idx]).grid(row = 2 * idx, column = 1, columnspan = 1, sticky = 'w')
                ttk.Separator(ana_prop_window, orient = 'horizontal').grid(row = 2 * idx + 1, column = 0, columnspan = 2, sticky = 'ew')

            # button to close window
            button_close = tk.Button(ana_prop_window, text='Close', width = 10, command=ana_prop_window.destroy)
            button_close.grid(row = 10, column = 1, columnspan = 1)

    def scan_props(self):
        """ Displays scan properties from currently selected scan ID """
        if self.scan_id_var.get() == 'Select Choice':
            print('Please select a scan ID first')
        else:    
            conn = sqlite3.connect(self.e2.get())
            cur = conn.cursor()

            # sql query used to retrieve scan info
            sql_cmd_scn_prop = "SELECT * FROM ScanProperties WHERE ScanID = ?;"
    
            scan_prop_info = np.array(cur.execute(sql_cmd_scn_prop,(str(self.scan_id_var.get()),)).fetchall()) # fetch all data from Scan Properties table

            # create the properties window
            scan_prop_window = tk.Toplevel()
            scan_prop_window.title('Scan Properties')
            
            # retrieve the properties of interest
            sampleID = scan_prop_info[np.where(scan_prop_info == "SampleID")[0][0], np.where(scan_prop_info == "SampleID")[1][0] + 1]
            lotID = scan_prop_info[np.where(scan_prop_info == "LotID")[0][0], np.where(scan_prop_info == "LotID")[1][0] + 1]
            job_name = scan_prop_info[np.where(scan_prop_info == "JobName")[0][0], np.where(scan_prop_info == "JobName")[1][0] + 1]
            auto_focus_set = scan_prop_info[np.where(scan_prop_info == "Autofocus Set")[0][0], np.where(scan_prop_info == "Autofocus Set")[1][0] + 1]
            num_tiles = scan_prop_info[np.where(scan_prop_info == "Golden Tile Tiles per Device")[0][0], np.where(scan_prop_info == "Golden Tile Tiles per Device")[1][0] + 1]
            num_devices = scan_prop_info[np.where(scan_prop_info == "Golden Tile Number of Devices")[0][0], np.where(scan_prop_info == "Golden Tile Number of Devices")[1][0] + 1]
            scan_width_mic = scan_prop_info[np.where(scan_prop_info == "Scan Width Microns")[0][0], np.where(scan_prop_info == "Scan Width Microns")[1][0] + 1]
            scan_height_mic = scan_prop_info[np.where(scan_prop_info == "Scan Height Microns")[0][0], np.where(scan_prop_info == "Scan Height Microns")[1][0] + 1]
            die_width_mic = scan_prop_info[np.where(scan_prop_info == "DieWidth")[0][0], np.where(scan_prop_info == "DieWidth")[1][0] + 1]
            die_height_mic = scan_prop_info[np.where(scan_prop_info == "DieHeight")[0][0], np.where(scan_prop_info == "DieHeight")[1][0] + 1]

            # place property variables into list
            prop_list = [sampleID, lotID, job_name, auto_focus_set, num_tiles, num_devices, scan_width_mic,
                        scan_height_mic, die_width_mic, die_height_mic]
            
            # property labels of interest in user-friendly form
            output_labels = np.array(['Sample ID', 'Lot ID', 'Job Name', 'Autofocus Set', 'Tiles per Device',
                                   'Number of Devices', 'Scan Width (Microns)', 'Scan Height (Microns)',
                                   'Die Width (Microns)', 'Die Height (Microns)'])
            
            # create all labels and corresponding values
            for idx, label in enumerate(output_labels):
                tk.Label(scan_prop_window, text = f"{label:<30}").grid(row = 2 * idx, column = 0, columnspan = 1, sticky = 'w')
                tk.Label(scan_prop_window, text = prop_list[idx]).grid(row = 2 * idx, column = 1, columnspan = 1, sticky = 'w')
                ttk.Separator(scan_prop_window, orient = 'horizontal').grid(row = 2 * idx + 1, column = 0, columnspan = 2, sticky = 'ew')

            # button to close window
            button_close = tk.Button(scan_prop_window, text='Close', width = 10, command=scan_prop_window.destroy)
            button_close.grid(row = 2 * len(output_labels) + 1, column = 1, columnspan = 1)
    
    def set_paths(self):
        """ Sets the currently input database and image directory paths
            Updates the scan dropdown menu according to database file contents """
        
        # update scan and analysis input variables to default values since new db file was provided
        self.ana_id_var.set('Select Choice')
        self.scan_id_var.set('Select Choice')
        
        # ensure the analysis and scan ID option menus are cleared of any options from previously entered paths
        self.e4["menu"].delete(0, "end")
        scan_menu = self.e3["menu"]
        scan_menu.delete(0, "end")
        
        # check that the inputs are valid
        if self.e1.get() == '' or self.e2.get() == '':
            print('Please fill out filepath fields first')
            return
        if not any(x.startswith('Scan_') for x in os.listdir(self.e1.get() + '/')):
            print('Scans Directory must contain image folders with naming convention \'Scan_XXX\'')
            return
        if self.e2.get().split('.db')[0].split('/')[-1] != self.e1.get().split('/')[-1]:
            print('WARNING: Scans Directory and Database File names do not match one another')
            print('Consider reviewing selections before proceeding, or error may occur')
        
        # connect to the currently selected database file
        conn = sqlite3.connect(self.e2.get())
        cur = conn.cursor()

        # sql queries used to retrieve scan info
        sql_cmd_scn = "SELECT * FROM Scans;" 
        sql_cmd_scn_prop = "SELECT * FROM ScanProperties"

        scans_info = np.array(cur.execute(sql_cmd_scn).fetchall()) # fetch all data from Scans table
        scan_prop_info = np.array(cur.execute(sql_cmd_scn_prop).fetchall()) # fetch all data from Scan Properties table
        
        # get all of the scan IDs
        self.scan_options = scans_info[:,0]
        
        # update the scan ID option menu with choices
        for string in self.scan_options:
            scan_menu.add_command(label=string, 
                             command=lambda value=string: self.scan_id_var.set(value))
        
    def scan_select(self, *args):
        """ Updates the analysis option menu when scan is selected from its dropdown """
        
        # update analysis input variable to default, since new scan ID was selected
        self.ana_id_var.set('Select Choice')
        # disable running any functionality when Scan ID has not been selected yet 
        if self.scan_id_var.get() != 'Select Choice':
            # set the location of the folder containing the scanned images for the chosen Scan ID
            scans_directory = self.e1.get() + '/'
            self.img_loc_var = scans_directory + 'Scan_' + f"{int(self.scan_id_var.get()):03d}"
            
            # connect to the currently selected database file
            conn = sqlite3.connect(self.e2.get())
            cur = conn.cursor()

            # sql queries used to retrieve analysis info
            sql_cmd_anly = "SELECT * FROM Analysis"

            analysis_info = np.array(cur.execute(sql_cmd_anly).fetchall()) # fetch all data from Analysis table

            # filter list for Analysis IDs corresponding to the chosen Scan ID
            self.analysis_options = (analysis_info[analysis_info[:, 4] == self.scan_id_var.get()])[:,0]

            # update the analysis ID option menu with choices
            menu = self.e4["menu"]
            menu.delete(0, "end")
            for string in self.analysis_options:
                menu.add_command(label=string, 
                                 command=lambda value=string: self.ana_id_var.set(value))
                
        #self.disable_first_call += 1 # now iterate variable to allow functionality to proceed during next call

    def advanced_settings(self):
        """ Creates instance of advanced settings class """  
        self.root_settings_obj = RootSettings()
        
    def browse_file(self):
        """ Opens file explorer for file selection """       
        filename =filedialog.askopenfilename(filetypes=(("db files","*.db"),))
        self.e2.delete(0, 'end')
        self.e2.insert(tk.END, filename) 
    
    def browse_directory(self):
        """ Opens file explorer for folder selection """     
        directory_name =filedialog.askdirectory()
        self.e1.delete(0, 'end')
        self.e1.insert(tk.END, directory_name)
        
class ShowPdf():
    """ Imports PDF as scrollable image into tkinter  
    
    Summary of changes made by jacobchristensen346 to tkPDFViewer (https://github.com/Roshanpaswan/tkPDFViewer.git) 

    - Added __init__ function to ShowPdf class, moved img_object_li instance variable into __init__ function. This aids in garbage-collection avoidance upon reruns of code.
    - Added explicit anchor argument to self.display_msg = Label(master, textvariable=percentage_load)
    - Added new variable returned upon exit of pdf_view() function (self.img_object_li). This allows capture of image array which aids in garbage collection avoidance.

    """

    #img_object_li = []
    def __init__(self):
        self.img_object_li = []

    def pdf_view(self, master, width = 1200, height = 600, pdf_location = "", bar = True, load = "after"):

        self.frame = tk.Frame(master, width = width, height = height, bg = "white")

        scroll_y = tk.Scrollbar(self.frame, orient = "vertical")
        scroll_x = tk.Scrollbar(self.frame, orient = "horizontal")

        scroll_x.pack(fill = "x", side = "bottom")
        scroll_y.pack(fill = "y", side = "right")

        percentage_view = 0
        percentage_load = tk.StringVar()

        if bar == True and load == "after":
            self.display_msg = tk.Label(master, textvariable = percentage_load)
            self.display_msg.pack(pady = 10)

            loading = ttk.Progressbar(self.frame, orient = tk.HORIZONTAL, length = 100, mode = 'determinate')
            loading.pack(side = tk.TOP, fill = tk.X)

        self.text = tk.Text(self.frame, yscrollcommand = scroll_y.set, xscrollcommand = scroll_x.set, width = width, height = height)
        self.text.pack(side = "left")

        scroll_x.config(command = self.text.xview)
        scroll_y.config(command = self.text.yview)

        def add_img():
            precentage_dicide = 0
            open_pdf = fitz.open(pdf_location)

            for page in open_pdf:
                pix = page.get_pixmap()
                pix1 = fitz.Pixmap(pix, 0) if pix.alpha else pix
                img = pix1.tobytes("ppm")
                timg = ImageTk.PhotoImage(data = img)
                self.img_object_li.append(timg)
                if bar == True and load == "after":
                    precentage_dicide = precentage_dicide + 1
                    percentage_view = (float(precentage_dicide)/float(len(open_pdf))*float(100))
                    loading['value'] = percentage_view
                    percentage_load.set(f"Please wait, the instruction manual is loading... {int(math.floor(percentage_view))}%")
            if bar == True and load == "after":
                loading.pack_forget()
                self.display_msg.pack_forget()

            for i in self.img_object_li:
                self.text.image_create(tk.END,image = i)
                self.text.insert(tk.END, "\n\n")
            self.text.configure(state = "disabled")


        def start_pack():
            t1 = Thread(target = add_img)
            t1.start()

        if load == "after":
            master.after(250, start_pack)
        else:
            start_pack()
       
        return self.frame, self.img_object_li

if __name__ == "__main__": 
    root_obj = Root()
    root_obj.root.mainloop()
