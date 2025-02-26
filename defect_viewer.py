# in this version I created two new classes. One for the mosaic creation, and one for the newly added settings of the mosaic
# now, in this version, you can create multiple mosaics that have settings that are entirely separate from one another!
# update the individual mosaic settings on the fly! Create new mosaics with their own settings on a whim!

# in this version I have also added new functions to allow for drawing circles on the zoomable tile image
# later I will have this output the area of the cirlces, and allow for updating circle to ellipse shape

import tkinter as tk
from tkinter import Tk, Canvas, mainloop
from tkinter import ttk
from tkinter import filedialog

import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from PIL import Image, ImageTk

import sqlite3

import os
import argparse
import shutil
import warnings
    
def defect_viewer(self):
    """Contains all the functionality of the app
    Only activates once inputs selected in gui"""
    image_origin = self.img_loc_var.get() + '/' # Here we gather our variables of interest entered into the gui
    db_origin = self.db_file_var.get()
    scan_id = self.scan_id_var.get()
    analysis_id = self.ana_id_var.get()
    tile_size = int(self.tile_size_var.get())        
 
    def clicked(self, event, image_data, defect_data):
        """ Contains all functionality to support click event
            Is called upon click event """
        print(event)

        # variables passed from the instance of Root
        # these variables must be adjusted back to initial values as defined in the Root object each time a click event happens
        label_font_size = int(self.font_size_input)
        
        # iterate through all image data rows, find selected image according to click event, image coords, and tile size
        for idx, img_row in enumerate(image_data):
            if ((int(img_row[8])*tile_size <= (event.x) <= (int(img_row[8])+1)*tile_size) and 
                (int(img_row[7])*tile_size <= (event.y) <= (int(img_row[7])+1)*tile_size)):
                
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
                        self.canvas.bind("<Return>", self.__destroy_circles) # remove all ellipse area measurements
                        self.canvas.bind('<ButtonPress-1>', self.__move_from)  # remember canvas position
                        self.canvas.bind('<B1-Motion>',     self.__move_to)  # move canvas to the new position
                        self.canvas.bind('<MouseWheel>', self.__wheel)  # zoom for Windows and MacOS, but not Linux
                        self.canvas.bind('<Button-5>',   self.__wheel)  # zoom for Linux, wheel scroll down
                        self.canvas.bind('<Button-4>',   self.__wheel)  # zoom for Linux, wheel scroll up
                        self.canvas.bind("<ButtonPress-3>", self.__on_right_click) # initiate ellipse area measurement
                        self.canvas.bind("<B3-Motion>", self.__on_right_click_drag) # enable dragging for drawing ellipse
                        self.canvas.bind("<ButtonRelease-3>", self.__on_right_click_release) # finalize ellipse area measurement
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
                            self.__image = Image.open(self.path)  # open image, but down't load it
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

                    def __show_defects(self):
                        """ Plots defects on selected image """
                        box_image = self.canvas.coords(self.container)  # get image area
                        
                        # now plot the defects on the current canvas image tile
                        for idx, def_row in enumerate(defect_data):
                                if float(def_row[1]) == float(img_row[0]):
                                    x = float(def_row[4])*box_image[2]/float(img_row[9]) # coordinates of defect scaled by image size
                                    y = float(def_row[5])*box_image[3]/float(img_row[10])
                                    scale = 30
                                    self.canvas.create_oval(x-box_image[2]/scale, y-box_image[3]/scale, x + box_image[2]/scale, y + box_image[3]/scale, 
                                                            outline = 'red', fill = "", width = 1)

                    def __show_labels(self):
                        """ Plots defect labels on selected image """
                        box_image = self.canvas.coords(self.container)  # get image area
                        
                        # now plot the defect labels on the current canvas image tile
                        for idx, def_row in enumerate(defect_data):
                                if float(def_row[1]) == float(img_row[0]):
                                    x = float(def_row[4])*box_image[2]/float(img_row[9]) # coordinates of defect label scaled by image size
                                    y = float(def_row[5])*box_image[3]/float(img_row[10])
                                    scale = 60
                                    #font_size = -int(10*((box_image[2]*box_image[3])/(self.imheight*self.imwidth)))
                                    self.canvas.create_text(x-box_image[2]/scale, y-box_image[3]/scale, 
                                                                                text = "X = " + def_row[4] + ", Y = " + def_row[5], 
                                                                                font=("Arial", -label_font_size), tags = "text")
                
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
                    
                    def __on_right_click(self, event):
                        self.start_x = self.canvas.canvasx(event.x)
                        self.start_y = self.canvas.canvasy(event.y)
                    
                    def __on_right_click_drag(self, event):
                      if self.start_x is not None and self.start_y is not None:
                        self.canvas.delete("temp_circle")
                        radius = ((self.canvas.canvasx(event.x) - self.start_x)**2 + (self.canvas.canvasy(event.y) - self.start_y)**2)**0.5
                        self.canvas.create_oval(self.start_x - radius, self.start_y - radius, 
                                                self.canvas.canvasx(event.x) + (radius - (self.canvas.canvasx(event.x)-self.start_x)), 
                                                self.canvas.canvasy(event.y) + (radius - (self.canvas.canvasy(event.y) - self.start_y)), 
                                                outline='black', tags="temp_circle")
                    
                    def __on_right_click_release(self, event):
                        if self.start_x is not None and self.start_y is not None:
                            self.canvas.delete("temp_circle")
                            radius = ((self.canvas.canvasx(event.x) - self.start_x)**2 + (self.canvas.canvasy(event.y) - self.start_y)**2)**0.5
                            self.canvas.create_oval(self.start_x - radius, self.start_y - radius, 
                                                    self.canvas.canvasx(event.x) + (radius - (self.canvas.canvasx(event.x)-self.start_x)), 
                                                    self.canvas.canvasy(event.y) + (radius - (self.canvas.canvasy(event.y) - self.start_y)), 
                                                    outline='black', tags="final_area_circle")
                            self.start_x = None
                            self.start_y = None

                    def __destroy_circles(self, event):
                        for item in self.canvas.find_withtag("final_area_circle"):
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
                            new_font_size = math.floor(rounding_indicator)
                        else:
                            new_font_size = math.ceil(rounding_indicator)
                        #print(label_font_size, rounding_indicator)
                        # once font size of 1 is reached, we need to make sure to keep track of scaling trends as we continue to demagnify image
                        # if not, we will scale the font size too quickly while magnifying the image
                        # the line of code below accomplishes the tracking by essentially recording the current number of scaling events
                        label_font_size = rounding_indicator 
                        # find all text objects according to "text" tag assigned to defect labels
                        for child_widget in self.canvas.find_withtag("text"):
                            self.canvas.itemconfigure(child_widget, font=("Arial", -new_font_size))
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
                    """ Main window class """
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
                app = TileWindow(tk.Toplevel(), path=filename, window_name = tile_name)
                app.mainloop()

    # This portion of defect_view function serves to plot the initial mosaic with associated defects
    # It is this mosaic where tiles can be selected from
    
    conn = sqlite3.connect(db_origin)
    cur = conn.cursor()
    
    sql_cmd_pos = "SELECT * FROM vwImages WHERE ScanID = ?;" 
    sql_cmd_def = "SELECT * FROM vwDefectsLegacy WHERE AnalysisID = ?;" 
    
    image_data = np.array(cur.execute(sql_cmd_pos,(str(scan_id),)).fetchall()) # fetch all data from image table
    defect_data = np.array(cur.execute(sql_cmd_def,(str(analysis_id),)).fetchall()) # fetch all data from defect table
    
    mosaic_window = tk.Toplevel()
    sample_name = (db_origin.split("/"))[-1]
    mosaic_window.title(sample_name + " || " + "Scan ID = " + str(scan_id) + " || " + "Analysis ID = " + str(analysis_id))
    
    class MosaicAdvanced:
        def __init__(self):
            self.initial_panel()

        def initial_panel(self):
            """ Create initial advanced settings panel """     
            self.adv_window = tk.Toplevel()
            self.adv_window.title('Advanced Settings')
    
            self.outline = tk.StringVar(self.adv_window, value='red')
            tk.Label(self.adv_window, text='Outline').grid(row=0, column = 0, columnspan = 1)
            self.e1 = tk.Entry(self.adv_window, textvariable = self.outline, width = 5)
            self.e1.grid(row = 0, column = 1, columnspan = 2)

            self.font_size_input = tk.StringVar(self.adv_window, value='6')
            tk.Label(self.adv_window, text='Font Size').grid(row=1, column = 0, columnspan = 1)
            self.e2 = tk.Entry(self.adv_window, textvariable = self.font_size_input, width = 5)
            self.e2.grid(row = 1, column = 1, columnspan = 2)
    
            button_accept = tk.Button(self.adv_window, text='Accept', width = 10,  
                                    command = lambda arg = self.outline, arg1 = self.font_size_input: self.return_choices(arg, arg1))
            button_accept.grid(row = 2, column = 3)
    
            button_close = tk.Button(self.adv_window, text='Close', width = 10, command=self.adv_window.destroy)
            button_close.grid(row = 3, column = 3)
            
        def return_choices(self, arg, arg1):
            """ Sends input settings back to Root """     
            newlol.outline = arg.get()
            newlol.font_size_input = arg1.get()
            newlol.lol()

    class LOL:
        def __init__(self):
            self.outline = "red"
            self.font_size_input = "6"
            self.lol()

        def call_advanced(self):
            MosaicAdvanced()
    
        def lol(self):

            for child in mosaic_window.winfo_children(): child.destroy()
            # create the canvas with size according to input tile size
            canvas = Canvas(mosaic_window, width = tile_size*(max((image_data[:,8:9]).astype(int))[0]+1), 
                            height = tile_size*(max((image_data[:,7:8]).astype(int))[0]+1), bd = 0)
        
            button_advanced = tk.Button(mosaic_window, text='Advanced', width = 10, command = self.call_advanced)
        
            # iterate through all rows of image data, plot each tile on the canvas
            self.images = []
            for idx, img_row in enumerate(image_data):
                image = Image.open(image_origin + img_row[2]) 
                image = image.resize((tile_size,tile_size),Image.LANCZOS) # resize tile and interpolate
                self.images.append(ImageTk.PhotoImage(image))
                canvas.create_image(int(img_row[8])*tile_size, int(img_row[7])*tile_size, anchor=tk.NW, image=self.images[idx]) 
        
            # iterate through all rows of defect data, plot each defect on the canvas
            for idx, def_row in enumerate(defect_data):
                row_index = np.where(np.any(image_data[:,0:1].astype(float) == float(def_row[1]), axis=1))[0] # find the tile where defect resides
                x = float(def_row[13]) * (tile_size / float((image_data[row_index,9])[0])) # scale defect coords according to image scale
                y = float(def_row[14]) * (tile_size / float((image_data[row_index,10])[0]))
                scale = 20
                canvas.create_oval(x-tile_size/scale, y-tile_size/scale, x + tile_size/scale, y + tile_size/scale, outline = self.outline, fill = "red")
            
            canvas.bind('<Button-1>', lambda event, arg = image_data, arg1 = defect_data: clicked(self, event, arg, arg1)) # makes mosaic selectable
            
            canvas.pack()
            button_advanced.pack()

    newlol = LOL()
    mosaic_window.mainloop()

class AdvancedSettings:
    """ Advanced Settings Class """ 
    def __init__(self):
        self.initial_panel()

    def initial_panel(self):
        """ Create initial advanced settings panel """     
        self.adv_window = tk.Toplevel()
        self.adv_window.title('Advanced Settings')

        self.font_size_input_adv = tk.StringVar(self.adv_window, value='6')
        tk.Label(self.adv_window, text='Defect Label Font Size').grid(row=0, column = 0, columnspan = 1)
        self.e1 = tk.Entry(self.adv_window, textvariable = self.font_size_input_adv, width = 5)
        self.e1.grid(row = 0, column = 1, columnspan = 2)

        button_accept = tk.Button(self.adv_window, text='Accept', width = 10,  
                                command = lambda arg = self.font_size_input_adv: self.return_choices(arg))
        button_accept.grid(row = 1, column = 3)

        button_close = tk.Button(self.adv_window, text='Close', width = 10, command=self.adv_window.destroy)
        button_close.grid(row = 2, column = 3)
        
    def return_choices(self, arg):
        """ Sends input settings back to Root """     
        root_obj.font_size_input = arg
        #Root.font_size_input = arg
        #Root.set_parameters(self, arg)

class Root:
    """ Class to create initial Root gui window """
    def __init__(self):
        
        self.root = tk.Tk()
        self.root.title('Defect View')

        # create variables for input in Root gui
        self.img_loc_var = tk.StringVar()
        self.db_file_var = tk.StringVar()
        self.scan_id_var = tk.StringVar()
        self.ana_id_var = tk.StringVar()
        self.tile_size_var = tk.StringVar()

        # initialize advanced settings variables to default values
        # will be overwritten by user input if desired
        self.font_size_input = tk.StringVar(self.root, value = '6')
        
        # create all the text entry labels and fields
        tk.Label(self.root, text='Image Location').grid(row = 0, column = 0, columnspan = 1)
        tk.Label(self.root, text='Database File').grid(row = 1, column = 0, columnspan = 1)
        tk.Label(self.root, text='Scan ID').grid(row = 2, column = 0, columnspan = 1)
        tk.Label(self.root, text='Analysis ID').grid(row = 3, column = 0, columnspan = 1)
        tk.Label(self.root, text='Tile Size').grid(row=4, column = 0, columnspan = 1)
        self.e1 = tk.Entry(self.root, textvariable = self.img_loc_var, width = 20)
        self.e2 = tk.Entry(self.root, textvariable = self.db_file_var, width = 20)
        self.e3 = tk.Entry(self.root, textvariable = self.scan_id_var, width = 10)
        self.e4 = tk.Entry(self.root, textvariable = self.ana_id_var, width = 10)
        self.e5 = tk.Entry(self.root, textvariable = self.tile_size_var, width = 10)
        self.e1.grid(row = 0, column = 2, columnspan = 2)
        self.e2.grid(row = 1, column = 2, columnspan = 2)
        self.e3.grid(row = 2, column = 2, columnspan = 1)
        self.e4.grid(row = 3, column = 2, columnspan = 1)
        self.e5.grid(row = 4, column = 2, columnspan = 1)
        
        # these buttons allow the file explorer to be opened to receive directory inputs
        button_file = tk.Button(self.root, text='...', width = 3, command=self.browse_file)
        button_directory = tk.Button(self.root, text='...', width = 3, command=self.browse_directory)
        button_file.grid(row = 1, column = 4)
        button_directory.grid(row = 0, column = 4)
        
        # this button opens up advanced settings
        button_advanced = tk.Button(self.root, text='Advanced', width = 10, command=self.advanced_settings)
        button_advanced.grid(row = 5, column = 0, columnspan = 1)
        
        # these two buttons either plot using the input info, or close out of the software
        # button_plot = tk.Button(self.root, text='Plot', width = 10,  
        #                         command = lambda arg = self.img_loc_var, arg1 = self.db_file_var, arg2 = self.scan_id_var, 
        #                         arg3 = self.ana_id_var, arg4 = self.tile_size_var: defect_viewer(self, arg, arg1, arg2, arg3, arg4))
        button_plot = tk.Button(self.root, text='Plot', width = 10, command = lambda: defect_viewer(self))
        button_close = tk.Button(self.root, text='Close', width = 10, command=self.root.destroy)
        button_plot.grid(row = 5, column = 5)
        button_close.grid(row = 6, column = 5)

    def advanced_settings(self):
        """ Creates instance of advanced settings class """  
        AdvancedSettings()
        
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

    #def set_parameters(self, arg):
    #    self.font_size_input = arg

if __name__ == "__main__": 
    root_obj = Root()
    root_obj.root.mainloop()
    #Root()
    #mainloop()
