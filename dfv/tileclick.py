# clicked imports
import math
from tkinter import ttk
import tkinter as tk
from PIL import Image, ImageTk
import warnings
import numpy as np

def clicked(mosaic_creator, event):
    """ Contains all functionality to support click event
        This function is called upon click event """
    print(event)

    # variables passed from the instance of MosaicCreator
    # these variables must be adjusted back to initial values as defined in the MosaicCreator object each time a click event happens
    # we make copies of these variables to ensure we do not overwrite the MosaicCreator instance from whence they came
    binning_ranges = mosaic_creator.binning_ranges  # binning ranges for defects, based on defect area
    binning_colors = mosaic_creator.binning_colors  # binning colors for defects based on defect area
    binning_type_colors = mosaic_creator.binning_type_colors  # binning colors for defects based on defect classification
    inf_bin_color = mosaic_creator.inf_bin_color  # color for the defect bin which goes to infinity
    font_size_defect_label = int(mosaic_creator.font_size_defect_label)  # font size for defect labels
    defect_data = mosaic_creator.defect_data  # array containing all relevant defect data
    defect_type_data = mosaic_creator.defect_type_data  # array containing relevant defect classification information
    which_binning_show = mosaic_creator.which_binning_show  # variable tells which defect binning to show by default
    image_data = mosaic_creator.image_data  # array containing all relevant image data
    scan_properties = mosaic_creator.scan_properties  # array containing information relevant to scan
    mos_tile_width = mosaic_creator.mos_tile_width  # width of mosaic canvas tile
    mos_tile_height = mosaic_creator.mos_tile_height  #  height of mosaic canvas tile
    defect_label_text_choices = mosaic_creator.defect_label_text_choices  #  list of info to include in each defect label
    image_view_only = mosaic_creator.root.image_view_only.get()  # variable determining whether to plot defects at all

    # iterate through all image data rows, find selected image according to click event, image coords, and tile size
    for idx, img_row in enumerate(mosaic_creator.image_data):

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
                    self.hide_defect_labels = None  # tracks user's choice to display defect labels
                    self.hide_defect_marks = None  # tracks user's choice to display defect marks
                    # the which_binning_show variable passed from MosaicCreator must be updated to instance variable status 
                    self.which_binning_show = which_binning_show  # this allows active changes to this variable while tile is open
                    self.measure_choice = None  # variable tracks user's choice of manual measurement on tile canvas
                    self.start_x = None  # coordinates which aid in the class functions for drawing areas
                    self.start_y = None
                    self.__new_font_size = None  # initialize shared variable for adjusting font sizes upon zoom
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
                    self.canvas.bind("<Return>", self.__destroy_measure_markers)  # remove all placed measurement marks
                    self.canvas.bind('<ButtonPress-1>', self.__move_from)  # remember canvas position
                    self.canvas.bind('<B1-Motion>',     self.__move_to)  # move canvas to the new position
                    self.canvas.bind('<MouseWheel>', self.__wheel)  # zoom for Windows and MacOS, but not Linux
                    self.canvas.bind('<Button-5>',   self.__wheel)  # zoom for Linux, wheel scroll down
                    self.canvas.bind('<Button-4>',   self.__wheel)  # zoom for Linux, wheel scroll up
                    self.canvas.bind("<ButtonPress-3>", self.__on_right_click) # initiate user measurement
                    self.canvas.bind("<B3-Motion>", self.__on_right_click_drag)  # enable dragging for drawing measurement mark
                    self.canvas.bind("<ButtonRelease-3>", self.__on_right_click_release)  # finalize measurement mark
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
                    if image_view_only == 0:
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
                    x = (x1 * np.cos(rotation)) + (y1 * np.sin(rotation)) + xc  # rotate x, y
                    y = (y1 * np.cos(rotation)) - (x1 * np.sin(rotation)) + yc

                    # create an oval as a list of points...
                    point_list = (np.column_stack([x, y])).flatten()

                    return point_list

                def __show_defects(self):
                    """ Plots defects on selected image """
                    box_image = self.canvas.coords(self.container)  # get image area

                    # now plot the defects on the current canvas image tile
                    for idx, def_row in enumerate(defect_data):
                            if float(def_row[1]) == float(img_row[0]):
                                x = float(def_row[4]) * box_image[2] / float(img_row[9])  # coordinates of defect scaled by image size
                                y = float(def_row[5]) * box_image[3] / float(img_row[10])  # also converted to image pixels from microns
                                scale = 30

                                # we will plot multiple copies of each defect overlaid on each other
                                # each copy will have a different defect mark color for the different binning types we can choose
                                # then we can simply toggle the defect visibility to the user by using tags for each bin type

                                bin_range_index = np.searchsorted(binning_ranges, float(def_row[8]))  # get index corresponding to binning range of defect area
                                # set size-based defect mark color based on binning color corresponding to index found above
                                if (bin_range_index > (len(binning_ranges) - 1)) or (binning_ranges.size == 0):
                                    bin_outline_color = inf_bin_color
                                else:
                                    bin_outline_color = binning_colors[bin_range_index]

                                # set class-based defect mark color based on user binning input
                                if binning_type_colors.size == 0 or defect_type_data.size == 0:
                                    mark_type_outline_color = inf_bin_color
                                else:
                                    mark_type_outline_color = binning_type_colors[np.where(defect_type_data[:, 0:1].flatten() == def_row[15])][0]

                                # ovals cannot be rotated in tkinter
                                # convert oval coordinates to polygon and add in rotation defined by "Orientation" from database file
                                # the factor of 2 multiplied on here ensures the oval encircles the entire defect
                                # width is y-direction length, height is x-direction length according to nSpec
                                x0 = x - (float(def_row[7]) * 2) / 2
                                y0 = y - (float(def_row[6]) * 2) / 2
                                x1 = x + (float(def_row[7]) * 2) / 2
                                y1 = y + (float(def_row[6]) * 2) / 2

                                # now plot the defect on the mosaic, we plot multiple overlaid copies for each binning type
                                self.canvas.create_polygon(tuple(self.__poly_oval_v2(x0, y0, x1, y1, 
                                            rotation=float(def_row[12]))), outline=bin_outline_color, fill="", width=2, tags="DEFECT_TILE_MARK_SIZE_BINNING")
                                self.canvas.create_polygon(tuple(self.__poly_oval_v2(x0, y0, x1, y1, 
                                            rotation=float(def_row[12]))), outline=mark_type_outline_color, fill="", width=2, tags="DEFECT_TILE_MARK_CLASS_BINNING")
                                self.canvas.itemconfigure("DEFECT_TILE_MARK_SIZE_BINNING", state="hidden")
                                self.canvas.itemconfigure("DEFECT_TILE_MARK_CLASS_BINNING", state="hidden")

                    # by default show the defect marks associated with the user's current choice on the mosaic
                    if self.which_binning_show == "SIZE":
                        self.canvas.itemconfigure("DEFECT_TILE_MARK_SIZE_BINNING", state="normal")
                    if self.which_binning_show == "CLASS":
                        self.canvas.itemconfigure("DEFECT_TILE_MARK_CLASS_BINNING", state="normal")

                def __toggle_binning(self, toggle_choice):
                    """ Toggles visibility for the desired set of defect binning colors """
                    self.which_binning_show = toggle_choice  # we must update global variable for binning visibility
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
                                x = float(def_row[4]) * box_image[2] / float(img_row[9])  # coordinates of defect label scaled by image size
                                y = float(def_row[5]) * box_image[3] / float(img_row[10])  # also converted to image pixels from microns
                                scale = 60
                                # this array contains all defect info that can be output on the defect label text line
                                defect_all_info = np.array(["DefectID = " + def_row[0], "ImageID = " + def_row[1], "AnalysisID = " + def_row[2],
                                                            "DeviceID = " + def_row[3], "X = " + def_row[4], "Y = " + def_row[5],
                                                            "W = " + def_row[6], "H = " + def_row[7], "Area = " + def_row[8],
                                                            "Intensity = " + def_row[9], "IntensityDeviation = " + def_row[10],
                                                            "Eccentricity = " + def_row[11], "Orientation = " + def_row[12],
                                                            "XinDevice = " + def_row[13], "YinDevice = " + def_row[14], "ClassID = " + def_row[15],
                                                            "Score = " + def_row[16], "Contour = " + def_row[17]])
                                defect_select_info = defect_all_info[defect_label_text_choices]  # filter info array to user selections
                                defect_label_text = ", ".join(defect_select_info)  # combine all elements into one string
                                self.canvas.create_text(x - box_image[2] / scale, y - box_image[3] / scale, 
                                                        text=defect_label_text, font=("Arial", -font_size_defect_label), tags=("text", "DEFECT_TILE_LABEL"))

                def __defect_mark_vis(self, *args):
                    """ Hides or reveals defect labels and/or marks when toggled """
                    if self.hide_defect_marks.get() == 1:
                        self.canvas.itemconfig("DEFECT_TILE_MARK_SIZE_BINNING", state="hidden")
                        self.canvas.itemconfig("DEFECT_TILE_MARK_CLASS_BINNING", state="hidden")
                    else:
                        if self.which_binning_show == "SIZE":
                            self.canvas.itemconfig("DEFECT_TILE_MARK_SIZE_BINNING", state="normal")
                        if self.which_binning_show == "CLASS":
                            self.canvas.itemconfig("DEFECT_TILE_MARK_CLASS_BINNING", state="normal")

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
                        box_scroll[0] = box_img_int[0]
                        box_scroll[2] = box_img_int[2]
                    # Vertical part of the image is in the visible area
                    if  box_scroll[1] == box_canvas[1] and box_scroll[3] == box_canvas[3]:
                        box_scroll[1] = box_img_int[1]
                        box_scroll[3] = box_img_int[3]
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
                    tk.Label(self.__imframe, text='Measurement Tool').grid(row=1, column=1, columnspan=1)
                    button_select_circle = tk.Button(self.__imframe, text='Circle', width=10, 
                                                     command=lambda arg="Circle": self.__set_measure_choice(arg))
                    button_select_circle.grid(row=2, column=1, sticky='nswe')

                    button_select_line = tk.Button(self.__imframe, text='Line', width=10, 
                                                   command=lambda arg="Line": self.__set_measure_choice(arg))
                    button_select_line.grid(row=3, column=1, sticky='nswe')

                    # checkbox to toggle defect mark visibility
                    self.hide_defect_marks = tk.IntVar(self.__imframe, value=0)
                    self.hide_defect_marks.trace('w', self.__defect_mark_vis)  # call visibility function upon value change
                    checkbox_mark_vis = tk.Checkbutton(self.__imframe, text='Hide Defect Marks', variable=self.hide_defect_marks)
                    checkbox_mark_vis.grid(row=2, column=0, columnspan=1, sticky='w')

                    # checkbox to toggle defect label visibility
                    self.hide_defect_labels = tk.IntVar(self.__imframe, value=0)
                    self.hide_defect_labels.trace('w', self.__defect_mark_vis)  # call visibility function upon value change
                    checkbox_label_vis = tk.Checkbutton(self.__imframe, text='Hide Defect Labels', variable=self.hide_defect_labels)
                    checkbox_label_vis.grid(row=3, column=0, columnspan=1, sticky='w')

                    # button for toggling visibility of size-binned defect colors
                    button_size_binning = tk.Button(self.__imframe, text='Size Binning', width=10, command=lambda: self.__toggle_binning("SIZE"))
                    button_size_binning.grid(row=4, column=0, sticky='w')

                    # button for toggling visibility of class-binned defect colors
                    button_class_binning = tk.Button(self.__imframe, text='Class Binning', width=10, command=lambda: self.__toggle_binning("CLASS"))
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
                                                    self.canvas.canvasx(event.x) + (radius - (self.canvas.canvasx(event.x) - self.start_x)), 
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
                                                    self.canvas.canvasx(event.x) + (radius - (self.canvas.canvasx(event.x) - self.start_x)), 
                                                    self.canvas.canvasy(event.y) + (radius - (self.canvas.canvasy(event.y) - self.start_y)), 
                                                    outline='red', tags="final_area_circle")

                            # now we calculate the area to be displayed next to the circle marker on the canvas
                            # convert x and y to microns using image size in pixels vs microns
                            # also, scale according to the current image magnification
                            micron_radius = (((self.canvas.canvasx(event.x) - self.start_x) * (float(img_row[9]) / float(img_row[11])))**2 
                                      + ((self.canvas.canvasy(event.y) - self.start_y) * (float(img_row[10]) / float(img_row[12])))**2)**0.5
                            scaled_radius = (micron_radius / self.imscale)
                            area = (np.pi*scaled_radius**2)

                            # create area label, which uses the same font size as defect labels for now
                            # check if new font size applied due to zoom, if not apply default font size
                            if self.__new_font_size == None:
                                area_font_size = font_size_defect_label
                            else:
                                area_font_size = self.__new_font_size
                            self.canvas.create_text(self.start_x - radius, self.start_y - radius, text=("Area = " + str(area)), 
                                                        font=("Arial", -area_font_size), tags=("text", "final_area_circle"))
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
                            micron_length = (((self.canvas.canvasx(event.x) - self.start_x) * (float(img_row[9]) / float(img_row[11])))**2 
                                      + ((self.canvas.canvasy(event.y) - self.start_y) * (float(img_row[10]) / float(img_row[12])))**2)**0.5
                            scaled_length = (micron_length / self.imscale)

                            # create text label, which uses the same font size as defect labels for now
                            # check if new font size applied due to zoom, if not apply default font size
                            if self.__new_font_size == None:
                                line_font_size = font_size_defect_label
                            else:
                                line_font_size = self.__new_font_size
                            self.canvas.create_text(self.start_x, self.start_y, text=("Length = " + str(scaled_length)), 
                                                        font=("Arial", -line_font_size), tags=("text", "final_line_length"))
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
                    x = self.canvas.canvasx(event.x) # get coordinates of the event on the canvas
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
                    nonlocal font_size_defect_label
                    rounding_indicator = font_size_defect_label * scale
                    # we will increase or decrease font size based on rounding indicator
                    # if the indicator is larger than font size (scale is inc), inc font size
                    # if the indicator is smaller (scale is dec), dec font size
                    # built-in protection against decreasing font size to zero
                    if rounding_indicator < font_size_defect_label and rounding_indicator >= 1:
                        self.__new_font_size = math.floor(rounding_indicator)
                    else:
                        self.__new_font_size = math.ceil(rounding_indicator)
                    # once font size of 1 is reached, we need to make sure to keep track of scaling trends as we continue to demagnify image
                    # if not, we will scale the font size too quickly while magnifying the image
                    # the line of code below accomplishes the tracking by essentially recording the current number of scaling events
                    font_size_defect_label = rounding_indicator 
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
                    if self.__huge:  # image is huge and takes up RAM
                        band = bbox[3] - bbox[1]  # width of the tile band
                        self.__tile[1][3] = band  # set the tile height
                        self.__tile[2] = self.__offset + self.imwidth * bbox[1] * 3  # set offset of the band
                        self.__image.close()
                        self.__image = Image.open(self.path)  # reopen / reset image
                        self.__image.size = (self.imwidth, band)  # set size of the tile band
                        self.__image.tile = [self.__tile]
                        return self.__image.crop((bbox[0], 0, bbox[2], band))
                    else:  # image is within RAM limit
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


            filename = mosaic_creator.root.img_loc + '/' + img_row[2]  # path to the image
            tile_name = img_row[2]  # get the name of the currently selected tile 
            print(tile_name)
            # create an object of the TileWindow class
            app = TileWindow(tk.Toplevel(), path=filename, window_name=tile_name)
            app.mainloop()