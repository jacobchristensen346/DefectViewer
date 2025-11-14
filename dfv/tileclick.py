"""
dfv.tileclicked
--------------

This module provides classes and functions which create an
interactive tile image displaying defects.
The tile image can be panned, scrolled, and zoomed.
This module triggers upon click event on the mosaic canvas
to then display the appropriate tile based on click location.
"""

# tileclick.py imports
import math
from tkinter import ttk
import tkinter as tk
from PIL import Image, ImageTk
import numpy as np


class Clicked:
    """Initiate individual tile view upon click event.
    
    Copy instance variables passed from MosaicCreator.
    Check which tile to plot in the tile window.
    """
    
    def __init__(self, mosobj, event):
        """Receive event and instance related to click event
        
        Parameters
        ----------
        mosobj : class instance
            MosaicCreator class instance holding attributes relevant
            to the click event.
        event : tk event object
            Holds information relevant to the click event on the mosaic canvas.

        Returns -> None.
        """
        self.mos_click_event = event
        print(event)
    
        # variables passed from the instance of MosaicCreator
        # these variables must be adjusted back to initial values as defined 
        # in the MosaicCreator object each time a click event happens
        # we make copies of these variables to ensure we do 
        # not overwrite the MosaicCreator instance from whence they came
        # binning ranges for defects, based on defect area
        self.binning_ranges = mosobj.binning_ranges
        # binning colors for defects based on defect area
        self.binning_colors = mosobj.binning_colors
        # binning colors for defects based on defect classification
        self.binning_type_colors = mosobj.binning_type_colors
        # color for the defect bin which goes to infinity
        self.inf_bin_color = mosobj.inf_bin_color
        # font size for defect labels
        self.label_fsize = int(mosobj.font_size_defect_label)
        # array containing all relevant defect data
        self.defect_data = mosobj.defect_data
        # array containing relevant defect classification information
        self.defect_type_data = mosobj.defect_type_data
        # variable tells which defect binning to show by default
        self.which_binning_show = mosobj.which_binning_show
        # width of mosaic canvas tile
        self.mos_tile_width = mosobj.mos_tile_width
        # height of mosaic canvas tile
        self.mos_tile_height = mosobj.mos_tile_height
        # list of info to include in each defect label
        self.text_choices = mosobj.defect_label_text_choices
        # variable determining whether to plot defects at all
        self.image_view_only = mosobj.root.image_view_only.get()
        # mosaic image directory
        self.img_loc = mosobj.root.img_loc + '/'
        # image data from the database file
        self.image_data = mosobj.image_data
        # initialize a variable to indicate the selected image row in database
        self.sel_irow = None
        
        self.tile_check()

    def tile_check(self):
        """Check which tile was clicked.

        Determines if mosaic tile has actual image tile
        and is not a blank space between separate die.
        
        Returns -> None.
        """
        # iterate through all image data rows, 
        # find selected image according to click event,
        # image coords, and tile size
        for idx, img_row in enumerate(self.image_data):
    
            # find the Row and Column of the tile in the mosaic image
            tile_row = float(img_row[7])
            tile_column = float(img_row[8])
    
            # find the ranges of values where tile exists inside mosaic canvas
            x_bottom = tile_column * self.mos_tile_width 
            x_top = (tile_column * self.mos_tile_width) + self.mos_tile_width
            y_bottom = tile_row * self.mos_tile_height
            y_top = (tile_row * self.mos_tile_height) + self.mos_tile_height
    
            if ((x_bottom <= (self.mos_click_event.x) <= x_top) 
                    and (y_bottom <= (self.mos_click_event.y) <= y_top)):
                self.sel_irow = img_row  # record selected image row
                # path to the image
                filename = self.img_loc + img_row[2]
                # get the name of the currently selected tile 
                tile_name = img_row[2]
                print(tile_name)
                # create an object of the TileWindow class
                TileWindow(self, tk.Toplevel(), path=filename, 
                           window_name=tile_name)
              
                
class TileWindow(ttk.Frame):
    """Creates tile window and initiates tile canvas creation."""
    
    def __init__(self, click_obj, tilewindow, path, window_name):
        """Initialize the window and master frame.

        Parameters
        ----------
        click_obj : class instance
            Instance of Clicked class passed along.
        tilewindow : tk window object
            The top level tk window object used to show tile image.
        path : string
            Directory filepath to clicked tile image.
        window_name : string
            Name for the tile window, based on image scanning order.

        Returns -> None.
        """
        ttk.Frame.__init__(self, master=tilewindow)
        self.master.title(window_name)
        self.master.geometry('800x600')  # size of the main window
        # make the canvas widget expandable
        self.master.rowconfigure(0, weight=1)
        self.master.columnconfigure(0, weight=1)
        # create widget for master window
        canvas_widget = TileCanvas(click_obj, self.master, path)
        canvas_widget.grid_(row=0, column=0)  # show widget in window
        
            
class SmartScrollbar(ttk.Scrollbar):
    """A scrollbar that hides when scrolling is not needed.
    Sublcass of ttk.Scrollbar.
    """
    def set(self, lo, hi):
        if float(lo) <= 0.0 and float(hi) >= 1.0:
            self.grid_remove()
        else:
            self.grid()
            ttk.Scrollbar.set(self, lo, hi)


class TileCanvas:
    """Create and display a scrollable 
    and zoomable tile image on a canvas.
    """
    
    def __init__(self, click_obj, placeholder, path):
        """Initialize the image frame and canvas.

        Parameters
        ----------
        click_obj : class instance
            Instance of Clicked class passed along. Certain attributes will
            be unloaded and copied here.
        placeholder : tk window object
            The top level tk window frame object passed along to hold 
            tile image and any other relevant widgets.
        path : string
            Directory filepath to clicked image tile.

        Returns -> None.
        """
        # TileCanvas holds instance containing 
        # copies of MosaicCreator variables
        self.clob = click_obj
        self.hide_defect_labels = None  # tracks choice to show defect labels
        self.hide_defect_marks = None  # tracks choice to show defect marks
        # the which_binning_show variable passed from MosaicCreator 
        # must be updated to instance variable status 
        # this allows active changes to this variable while tile is open
        # self.which_binning_show = click_obj.which_binning_show
        # variable tracks user's choice of manual measurement on tile canvas
        self.measure_choice = None
        # coordinates which aid in the methods for drawing areas
        self.start_x = None
        self.start_y = None
        # initialize shared variable for adjusting font sizes upon zoom
        self.new_font_size = None
        # scale for the canvas image zoom, start at 1.0
        # will retain all zoom events within its value
        self.imscale = 1.0
        self.delta = 1.3  # factor by which to scale for a single zoom event
        self.previous_state = 0  # previous state of the keyboard
        self.path = path  # path to the image
        # create frame in master window to hold tile canvas
        self.imframe = ttk.Frame(placeholder)
        
        # vertical and horizontal scrollbars for canvas
        hbar = SmartScrollbar(self.imframe, orient='horizontal')
        vbar = SmartScrollbar(self.imframe, orient='vertical')
        hbar.grid(row=1, column=0, sticky='we')
        vbar.grid(row=0, column=1, sticky='ns')
        
        # create the option buttons next to the canvas
        self.create_option_buttons()
        
        # create canvas and place scrollbars
        self.canvas = tk.Canvas(self.imframe, highlightthickness=0,
                                xscrollcommand=hbar.set, 
                                yscrollcommand=vbar.set)
        self.canvas.grid(row=0, column=0, sticky='nswe')
        self.canvas.update()  # ensure canvas exists before continuing
        
        hbar.configure(command=self.scroll_x)  # bind scrollbars to the canvas
        vbar.configure(command=self.scroll_y)
        
        # bind events to the canvas
        # for resizing the canvas
        self.canvas.bind('<Configure>', lambda event: self.show_image())
        # remove all placed measurement marks
        self.canvas.bind("<Return>", self.destroy_measure_markers)
        # remember canvas position
        self.canvas.bind('<ButtonPress-1>', self.move_from)
        # move canvas to the new position
        self.canvas.bind('<B1-Motion>', self.move_to)
        # zoom for Windows and Linux
        self.canvas.bind('<MouseWheel>', self.wheel)
        self.canvas.bind('<Button-5>', self.wheel)
        self.canvas.bind('<Button-4>', self.wheel)
        # initiate user measurement
        self.canvas.bind("<ButtonPress-3>", self.on_right_click)
        # enable dragging for drawing measurement mark
        self.canvas.bind("<B3-Motion>", self.on_right_click_drag)
        # finalize measurement mark
        self.canvas.bind("<ButtonRelease-3>", self.on_right_click_release)
        # scrolling with keyboard
        self.canvas.bind('<Key>', lambda event: 
                         self.canvas.after_idle(self.keystroke, event))
            
        self.image = Image.open(self.path)  # open the clicked tile image
        # get native size of clicked tile image
        self.imwidth = self.image.size[0]
        self.imheight = self.image.size[1]
        self.min_side = min(self.imwidth, self.imheight)  # smaller image dim
        
        # We will build an image pyramid to handle the slowdown
        # caused by attempting to resize and interpolate the 
        # original high-res tile image over and over during zoom
        self.pyramid = [self.image]  # init pyramid list with native image
        self.curr_img = 0  # tracks which pyramid image to use during zoom
        # the factor by which to shrink image size
        # if we set this equal to the zoom scale factor
        # then we have a one-to-one selection of pyramid
        # image resolution to total scaling from zoom
        # using the logarithmic function 
        # log(curr zoom image scale, pyramid scale factor) = pyramid list index
        self.reduce_factor = 1.3
        w, h = self.pyramid[0].size  # starting width and height
        pyr_cutoff = 512  # the pixel size to stop reducing beyond
        while w > pyr_cutoff and h > pyr_cutoff:
            w = w / self.reduce_factor
            h = h / self.reduce_factor
            reduced_image = self.pyramid[-1].resize((int(w), int(h)), 
                                                    Image.LANCZOS)
            # append scaled image to pyramid list
            self.pyramid.append(reduced_image)
        # self.scale will track the "total" amount of scaling
        # needed when cropping and displaying the pyramid image
        # it will factor in the zoom events (self.imscale)
        # along with the reduction scale of the specific pyramid image
        # for now we will initialize to the same value as self.imscale
        self.scale = self.imscale
            
        # this invisible rectangle will be used to track the image 
        # location and size on the canvas
        # set the rectangle initially to the original image size
        # it will remain on the canvas at all times, so we always
        # know how to properly scale and place the image after
        # selection from the image pyramid during zoom/scrolling
        self.container = self.canvas.create_rectangle((0, 0, self.imwidth, 
                                                       self.imheight), width=0)
        
        # call the method used to scale and show image
        # this method will be repeatably called anytime
        # a zoom or scroll event occurs
        self.show_image()
        # check if user has selected image view only
        if self.clob.image_view_only == 0:
            self.show_defects()  # show defects on the canvas
            self.show_labels() # show defect labels on the canvas
        self.canvas.focus_set()  # set focus on the canvas
        
    def grid_(self, **kw):
        """Put CanvasImage widget on the parent widget.
        
        Parameters
        ----------
        **kw : keyword arguments
            Intended to receive arguments appropriate for the
            tk grid() command, such as row and column number.

        Returns -> None.
        """
        self.imframe.grid(**kw)  # place CanvasImage widget on the grid
        self.imframe.grid(sticky='nswe')  # make frame container sticky
        self.imframe.rowconfigure(0, weight=1)  # make canvas expandable
        self.imframe.columnconfigure(0, weight=1)

    def scroll_x(self, *args, **kwargs):
        """Scroll canvas horizontally and redraw the image.

        Parameters
        ----------
        *args, **kwargs : arguments
            Arguments appropriate for xview() tk command.

        Returns -> None
        """
        self.canvas.xview(*args)  # scroll horizontally
        self.show_image()  # redraw the image on new visible canvas location

    def scroll_y(self, *args, **kwargs):
        """Scroll canvas vertically and redraw the image.

        Parameters
        ----------
        *args, **kwargs : arguments
            Pass arguments appropriate for the yview() tk command.

        Returns -> None
        """
        self.canvas.yview(*args)  # scroll vertically
        self.show_image()  # redraw the image on new visible canvas location

    def poly_oval_v2(self, x0, y0, x1, y1, steps=50, rotation=0):
        """NEW VERSION (uses numpy): Return an oval as 
        coordinates suitable for create_polygon.

        Parameters
        ----------
        x0, y0, x1, y1 : float
            Coordinates for the top left (x0, y0) and bottom right (x1, y1)
            of the boudning rectangle for the intended oval.
        steps : int, optional
            The number of sides to include in the polygon. The default is 50.
        rotation : float, optional
            Degree of rotation for bounding rectangle. The default is 0.

        Returns
        -------
        point_list : numpy array of floats
            Array containing [x, y] pairs representing polygon points.
        """
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
        x = (x1 * np.cos(rotation)) + (y1 * np.sin(rotation)) + xc  # rotate xy
        y = (y1 * np.cos(rotation)) - (x1 * np.sin(rotation)) + yc

        # create an oval as a list of points...
        point_list = (np.column_stack([x, y])).flatten()

        return point_list

    def show_defects(self):
        """Plot defects on the selected image.
        
        Returns -> None
        """
        # get image coordinates on canvas 
        # based on our always-present rectangle
        box_image = self.canvas.coords(self.container)

        # now plot the defects on the currently cropped image region
        for idx, def_row in enumerate(self.clob.defect_data):
            if float(def_row[1]) == float(self.clob.sel_irow[0]):
                # coordinates of defect scaled by image size
                x = (float(def_row[4]) * box_image[2] 
                     / float(self.clob.sel_irow[9]))
                # also converted to image pixels from microns
                y = (float(def_row[5]) * box_image[3] 
                     / float(self.clob.sel_irow[10]))

                # we will plot multiple copies of each defect overlaid
                # each copy will have a different defect mark color
                # tags are used to toggle defect visibility for bin type

                # get index corresponding to binning range of defect area
                bin_range_index = np.searchsorted(self.clob.binning_ranges, 
                                                  float(def_row[8]))
                # set size-based defect mark color based on 
                # binning color corresponding to index found above
                if ((bin_range_index > (len(self.clob.binning_ranges) - 1)) 
                        or (self.clob.binning_ranges.size == 0)):
                    binc_outline = self.clob.inf_bin_color
                else:
                    binc_outline = self.clob.binning_colors[bin_range_index]

                # set class-based defect mark color based on user binning input
                if (self.clob.binning_type_colors.size == 0 
                    or self.clob.defect_type_data.size == 0):
                    mark_type_outline = self.clob.inf_bin_color
                else:
                    btc = self.clob.binning_type_colors
                    dtd = self.clob.defect_type_data[:, 0:1].flatten()
                    mark_type_outline = btc[np.where(dtd == def_row[15])][0]

                # ovals cannot be rotated in tkinter
                # convert oval coordinates to polygon and add in 
                # rotation defined by "Orientation" from database file
                # the factor of 2 multiplied on here ensures 
                # the oval encircles the entire defect
                # width is y-direction length 
                # height is x-direction length
                x0 = x - (float(def_row[7]) * 2) / 2
                y0 = y - (float(def_row[6]) * 2) / 2
                x1 = x + (float(def_row[7]) * 2) / 2
                y1 = y + (float(def_row[6]) * 2) / 2

                # plot multiple overlaid copies for each binning type
                self.canvas.create_polygon(
                    tuple(self.poly_oval_v2(x0, y0, x1, y1,
                                            rotation=float(def_row[12]))),
                    outline=binc_outline, fill="", width=2,
                    tags="DEFECT_TILE_MARK_SIZE_BINNING")
                self.canvas.create_polygon(
                    tuple(self.poly_oval_v2(x0, y0, x1, y1,
                                            rotation=float(def_row[12]))),
                    outline=mark_type_outline, fill="", width=2,
                    tags="DEFECT_TILE_MARK_CLASS_BINNING")
                self.canvas.itemconfigure("DEFECT_TILE_MARK_SIZE_BINNING",
                                          state="hidden")
                self.canvas.itemconfigure("DEFECT_TILE_MARK_CLASS_BINNING",
                                          state="hidden")

        # by default show current defect binning choice from the mosaic
        if self.clob.which_binning_show == "SIZE":
            self.canvas.itemconfigure("DEFECT_TILE_MARK_SIZE_BINNING",
                                      state="normal")
        if self.clob.which_binning_show == "CLASS":
            self.canvas.itemconfigure("DEFECT_TILE_MARK_CLASS_BINNING",
                                      state="normal")

    def toggle_binning(self, toggle_choice):
        """Toggle visibility for the desired set of defect binning colors.
        
        Parameters
        ----------
        toggle_choice : string
            A string that describes the choice of binning type, such
            as "SIZE" or "CLASS".

        Returns -> None
        """
        self.clob.which_binning_show = toggle_choice  # update visibility
        if toggle_choice == "SIZE":
            self.canvas.itemconfigure("DEFECT_TILE_MARK_SIZE_BINNING",
                                      state="normal")
            self.canvas.itemconfigure("DEFECT_TILE_MARK_CLASS_BINNING",
                                      state="hidden")
        if toggle_choice == "CLASS":
            self.canvas.itemconfigure("DEFECT_TILE_MARK_SIZE_BINNING",
                                      state="hidden")
            self.canvas.itemconfigure("DEFECT_TILE_MARK_CLASS_BINNING",
                                      state="normal")

    def show_labels(self):
        """Plot defect labels on selected image.
        
        Returns -> None
        """
        # get image coordinates on canvas 
        # based on our always-present rectangle
        box_image = self.canvas.coords(self.container)

        # now plot the defect labels on the current canvas image tile
        for idx, def_row in enumerate(self.clob.defect_data):
            if float(def_row[1]) == float(self.clob.sel_irow[0]):
                # coordinates of defect label scaled by image size
                x = (float(def_row[4]) * box_image[2] 
                     / float(self.clob.sel_irow[9]))
                # also converted to image pixels from microns
                y = (float(def_row[5]) * box_image[3] 
                     / float(self.clob.sel_irow[10]))
                scale = 60
                # this array contains all defect info that can be displayed
                defect_all_info = np.array(
                    ["DefectID = " + def_row[0],
                     "ImageID = " + def_row[1],
                     "AnalysisID = " + def_row[2],
                     "DeviceID = " + def_row[3],
                     "X = " + def_row[4],
                     "Y = " + def_row[5],
                     "W = " + def_row[6],
                     "H = " + def_row[7],
                     "Area = " + def_row[8], 
                     "Intensity = " + def_row[9],
                     "IntensityDeviation = " + def_row[10],
                     "Eccentricity = " + def_row[11],
                     "Orientation = " + def_row[12],
                     "XinDevice = " + def_row[13],
                     "YinDevice = " + def_row[14],
                     "ClassID = " + def_row[15],
                     "Score = " + def_row[16],
                     "Contour = " + def_row[17]]
                )
                # filter info array to user selections
                defect_select_info = defect_all_info[self.clob.text_choices]
                # combine all elements into one string
                label_text = ", ".join(defect_select_info)
                self.canvas.create_text(
                    x - box_image[2] / scale, y - box_image[3] / scale, 
                    text=label_text, font=("Arial", -self.clob.label_fsize), 
                    tags=("text", "DEFECT_TILE_LABEL"))

    def defect_mark_vis(self):
        """Hide or reveal defect labels and/or marks when toggled.

        Returns -> None
        """
        if self.hide_defect_marks.get() == 1:
            self.canvas.itemconfig("DEFECT_TILE_MARK_SIZE_BINNING",
                                   state="hidden")
            self.canvas.itemconfig("DEFECT_TILE_MARK_CLASS_BINNING",
                                   state="hidden")
        else:
            if self.clob.which_binning_show == "SIZE":
                self.canvas.itemconfig("DEFECT_TILE_MARK_SIZE_BINNING",
                                       state="normal")
            if self.clob.which_binning_show == "CLASS":
                self.canvas.itemconfig("DEFECT_TILE_MARK_CLASS_BINNING",
                                       state="normal")

        if self.hide_defect_labels.get() == 1:
            self.canvas.itemconfig("DEFECT_TILE_LABEL", state="hidden")
        else:
            self.canvas.itemconfig("DEFECT_TILE_LABEL", state="normal")

    def show_image(self):
        """Show image on the canvas.
        
        Performs scaling based on scroll and zoom.
        
        Returns -> None
        """
        # get image coordinates on the canvas 
        # based on our rectangle stand-in for the image
        # and how that rectangle's coordinates have changed
        box_image = self.canvas.coords(self.container)
        # get visible area of the canvas
        # these coords are relative to the window coords
        # which shift as we scroll the window across the canvas
        box_canvas = (self.canvas.canvasx(0),
                      self.canvas.canvasy(0),
                      self.canvas.canvasx(self.canvas.winfo_width()),
                      self.canvas.canvasy(self.canvas.winfo_height())
                      )
        box_img_int = tuple(map(int, box_image))  # convert image area to int 
        
        # get the region where scrolling will be allowed
        # choose whichever dimensions will give
        # the larger scrolling region among the coordinates
        # of the visible canvas and image regions
        box_scroll = [min(box_img_int[0], box_canvas[0]), 
                      min(box_img_int[1], box_canvas[1]),
                      max(box_img_int[2], box_canvas[2]), 
                      max(box_img_int[3], box_canvas[3])
                      ]
        # if the horizontal visible region of the canvas
        # is outside the image region on both ends
        # the scroll region need not be set that large
        # reset to just the image region extent, instead
        if  box_scroll[0] == box_canvas[0] and box_scroll[2] == box_canvas[2]:
            box_scroll[0] = box_img_int[0]
            box_scroll[2] = box_img_int[2]
        # do the same for the vertical scroll region
        if  box_scroll[1] == box_canvas[1] and box_scroll[3] == box_canvas[3]:
            box_scroll[1] = box_img_int[1]
            box_scroll[3] = box_img_int[3]
        # now set scroll region on the canvas officially
        self.canvas.configure(scrollregion=tuple(map(int, box_scroll)))
        
        # get coordinates of the region of the image that
        # we should crop and show based on the visible region of the
        # canvas (scrolling) and the current scale of the image itself (zoom)
        # for example, for the upper left corner, if the visible canvas 
        # region is outside of the image region on the canvas
        # the upper left corner (x1, y1) is set to (0, 0)
        # so we crop all the way to the left and top sides of the image
        x1 = max(box_canvas[0] - box_image[0], 0)
        y1 = max(box_canvas[1] - box_image[1], 0)
        x2 = min(box_canvas[2], box_image[2]) - box_image[0]
        y2 = min(box_canvas[3], box_image[3]) - box_image[1]
        
        # only show the image if it is in the visible canvas region
        if int(x2 - x1) > 0 and int(y2 - y1) > 0:
            # select and crop the appropriate image from the pyramid
            # cropping is done to only return the area of the image
            # that would be visible based on the scroll/zoom of the canvas
            # we must scale the dimensions to crop based on the
            # reduction factor of the currently selected image
            image = self.pyramid[max(0, self.curr_img)].crop(
                    (int(x1 / self.scale), int(y1 / self.scale),
                     int(x2 / self.scale), int(y2 / self.scale)))
            
            # we have the correct region of the pyramid image cropped
            # but the image is reduced compared to the original image
            # now resize the reduced pyramid image to fit the size
            # of the currently scrolled/zoomed canvas region
            imagetk = ImageTk.PhotoImage(
                image.resize((int(x2 - x1), int(y2 - y1)), Image.LANCZOS))
            # and place the image on the canvas
            imageid = self.canvas.create_image(
                max(box_canvas[0], box_img_int[0]), 
                max(box_canvas[1], box_img_int[1]), 
                anchor='nw', image=imagetk)

            self.canvas.lower(imageid)  # set image into background
            # make a copy to prevent garbage collection
            self.canvas.imagetk = imagetk

    def create_option_buttons(self):
        """Create option buttons off to the side of the canvas.

        Returns -> None
        """
        # these labels/buttons relate to manual measurement tools
        tk.Label(self.imframe, text='Measurement Tool').grid(row=1, column=1, 
                                                             columnspan=1)
        button_select_circle = tk.Button(
            self.imframe, text='Circle', width=10, 
            command=lambda arg="Circle": self.set_measure_choice(arg))
        button_select_circle.grid(row=2, column=1, sticky='nswe')

        button_select_line = tk.Button(
            self.imframe, text='Line', width=10, 
            command=lambda arg="Line": self.set_measure_choice(arg))
        button_select_line.grid(row=3, column=1, sticky='nswe')

        # checkbox to toggle defect mark visibility
        self.hide_defect_marks = tk.IntVar(self.imframe, value=0)
        # call visibility function upon value change
        self.hide_defect_marks.trace('w', self.defect_mark_vis)
        cbox_mark_vis = tk.Checkbutton(self.imframe, text='Hide Defect Marks', 
                                       variable=self.hide_defect_marks)
        cbox_mark_vis.grid(row=2, column=0, columnspan=1, sticky='w')

        # checkbox to toggle defect label visibility
        self.hide_defect_labels = tk.IntVar(self.imframe, value=0)
        # call visibility function upon value change
        self.hide_defect_labels.trace('w', self.defect_mark_vis)
        cbox_lab_vis = tk.Checkbutton(self.imframe, text='Hide Defect Labels',
                                      variable=self.hide_defect_labels)
        cbox_lab_vis.grid(row=3, column=0, columnspan=1, sticky='w')

        # button for toggling visibility of size-binned defect colors
        button_size_binning = tk.Button(
            self.imframe, text='Size Binning',
            width=10, command=lambda: self.toggle_binning("SIZE"))
        button_size_binning.grid(row=4, column=0, sticky='w')

        # button for toggling visibility of class-binned defect colors
        button_class_binning = tk.Button(
            self.imframe, text='Class Binning',
            width=10, command=lambda: self.toggle_binning("CLASS"))
        button_class_binning.grid(row=5, column=0, sticky='w')

    def set_measure_choice(self, arg):
        """Set which kind of object to draw with the measuring tool.
        
        Parameters
        ----------
        arg : string
            String representing the type of object to draw on canvas
            For example, "Circle" or "Line".

        Returns -> None
        """
        self.measure_choice = arg

    def on_right_click(self, event):
        """Initialize the measurement tool use upon right mouse click.
        
        Parameters
        ----------
        event : tk event object
            Contains the relevant button press event info, such as coordinates.

        Returns -> None
        """
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)

    def on_right_click_drag(self, event):
        """Allows for measurement size modification through dragging
        the mouse while holding right mouse button.
        
        Parameters
        ----------
        event : tk event object
            Contains the relevant motion event info, such as coordinates.

        Returns -> None
        """
        evx = self.canvas.canvasx(event.x) # load into less verbose variables
        evy = self.canvas.canvasy(event.y)
        if self.measure_choice == "Circle":
            if self.start_x is not None and self.start_y is not None:
                self.canvas.delete("temp_circle")
                radius = ((evx - self.start_x)**2 
                          + (evy - self.start_y)**2)**0.5
                x1 = self.start_x - radius
                y1 = self.start_y - radius
                x2 = (evx + (radius - (evx - self.start_x)))
                y2 = (evy + (radius - (evy - self.start_y)))
                self.canvas.create_oval(x1, y1, x2, y2, outline='red',
                                        tags="temp_circle")

        elif self.measure_choice == "Line":
            if self.start_x is not None and self.start_y is not None:
                self.canvas.delete("temp_line")
                self.canvas.create_line(self.start_x, self.start_y, evx, evy,
                                        fill='red', width = 2, 
                                        tags="temp_line")

    def on_right_click_release(self, event):
        """Finalize measurement upon release of right mouse click.
        
        Parameters
        ----------
        event : tk event object
            Contains the relevant release event info, such as coordinates.

        Returns -> None
        """
        evx = self.canvas.canvasx(event.x) # load into less verbose variables
        evy = self.canvas.canvasy(event.y)
        if self.measure_choice == "Circle":
            if self.start_x is not None and self.start_y is not None:
                self.canvas.delete("temp_circle")
                # radius of circle
                radius = ((evx - self.start_x)**2
                          + (evy - self.start_y)**2)**0.5
                x1 = self.start_x - radius
                y1 = self.start_y - radius
                x2 = (evx + (radius - (evx - self.start_x)))
                y2 = (evy + (radius - (evy - self.start_y)))
                self.canvas.create_oval(x1, y1, x2, y2, outline='red', 
                                        tags="final_area_circle")

                # calculate the area to display next to circle marker on canvas
                # convert x, y to microns using image size in pixels vs microns
                micx = ((evx - self.start_x)
                        * (float(self.clob.sel_irow[9])
                           / float(self.clob.sel_irow[11])))
                micy = ((evy - self.start_y)
                        * (float(self.clob.sel_irow[10])
                           / float(self.clob.sel_irow[12])))
                micron_radius = (micx**2 + micy**2)**0.5
                # also, scale according to the current image magnification
                scaled_radius = (micron_radius / self.imscale)
                area = (np.pi*scaled_radius**2)

                # create area label, same font size as defect labels
                # check if new font size from zoom, if not apply default
                if self.new_font_size == None:
                    area_font_size = self.clob.label_fsize
                else:
                    area_font_size = self.new_font_size
                self.canvas.create_text(x1, y1, text=("Area = " + str(area)),
                                        font=("Arial", -area_font_size),
                                        tags=("text", "final_area_circle"))
                self.start_x = None
                self.start_y = None

        elif self.measure_choice == "Line":
            if self.start_x is not None and self.start_y is not None:
                self.canvas.delete("temp_line")
                # create the line on the canvas
                self.canvas.create_line(self.start_x, self.start_y, evx, evy,
                                        fill='red', width = 2, 
                                        tags="final_line_length")

                # line length in microns using image size in pixels vs microns
                # we also scale according to current image magnification
                micx = ((evx - self.start_x)
                        * (float(self.clob.sel_irow[9])
                           / float(self.clob.sel_irow[11])))
                micy = ((evy - self.start_y)
                        * (float(self.clob.sel_irow[10])
                           / float(self.clob.sel_irow[12])))
                micron_len = (micx**2 + micy**2)**0.5
                scaled_len = (micron_len / self.imscale)

                # create text label, same font size as defect labels for now
                # check if new font size from zoom, if not apply default
                if self.new_font_size == None:
                    line_font_size = self.clob.label_fsize
                else:
                    line_font_size = self.new_font_size
                self.canvas.create_text(self.start_x, self.start_y, 
                                        text=("Length = " + str(scaled_len)), 
                                        font=("Arial", -line_font_size), 
                                        tags=("text", "final_line_length"))
                self.start_x = None
                self.start_y = None

    def destroy_measure_markers(self, event):
        """Remove any measurement markers on the canvas.

        Parameters
        ----------
        event : tk event object
            Contains the relevant button press event info.

        Returns -> None
        """
        for item in self.canvas.find_withtag("final_area_circle"):
            self.canvas.delete(item)
        for item in self.canvas.find_withtag("final_line_length"):
            self.canvas.delete(item)

    def move_from(self, event):
        """Remember previous coordinates for scrolling with left mouse click.

        Parameters
        ----------
        event : tk event object
            Contains the relevant button press event info, such as coordinates.

        Returns -> None
        """
        self.canvas.scan_mark(event.x, event.y)

    def move_to(self, event):
        """Drag canvas to the new position while holding left mouse click.
        
        Parameters
        ----------
        event : tk event object
            Contains the relevant motion/drag event info, such as coordinates.

        Returns -> None
        """
        self.canvas.scan_dragto(event.x, event.y, gain=1)
        # crop and show new image region based on scrolling
        self.show_image()

    def outside(self, x, y):
        """Checks if the point (x,y) is outside the image area.
        Used to determine whether to zoom or not.
        
        Parameters
        ----------
        x, y : floats
            Coordinates of mouse wheel zoom event on canvas.

        Returns
        -------
        bool
            "True" if point is within image area, "False" otherwise.
        """
        # get image coordinates on canvas based on rectangle stand-in
        bbox = self.canvas.coords(self.container)
        if bbox[0] < x < bbox[2] and bbox[1] < y < bbox[3]:
            return False  # point (x,y) is inside the image area
        else:
            return True  # point (x,y) is outside the image area

    def wheel(self, event):
        """Zoom on the tile with mouse wheel.
        
        Parameters
        ----------
        event : tk event object
            Contains the relevant mouse wheel event info, such as coordinates,
            and whether mouse wheel was spun up or down.

        Returns -> None
        """
        x = self.canvas.canvasx(event.x) # get coordinates canvas event
        y = self.canvas.canvasy(event.y)
        # allow zoom only on image
        # so users don't get lost or confused
        if self.outside(x, y):
            return
        # local variable scale_inst tracks this instance of scaling
        # resets each time a zoom even occurs
        # self.imscale, in contrast, is not reset
        # and retains past zoom events in its value
        scale_inst = 1.0
        
        # respond to Linux (event.num) or Windows (event.delta) wheel event
        # mouse wheel down, scale image smaller
        if event.num == 5 or event.delta == -120:
            # do not zoom any smaller if less than 30 pixels
            if round(self.min_side * self.imscale) < 30: 
                return
            self.imscale = self.imscale / self.delta
            scale_inst = scale_inst / self.delta
        # mouse wheel up, scale image larger
        if event.num == 4 or event.delta == 120:
            # if a single image pixel is larger than the visible area
            # do not allow any more zooming
            i = min(self.canvas.winfo_width(), self.canvas.winfo_height()) // 2
            # the current image scale is the relative size of one pixel
            if i < self.imscale: 
                return
            self.imscale = self.imscale * self.delta
            scale_inst = scale_inst * self.delta
        # take appropriate image from the pyramid
        log_chooser = int(math.log(self.imscale, self.reduce_factor))
        self.curr_img = min((-1) * log_chooser, len(self.pyramid) - 1)
        # self.imscale alone determines the scale from
        # only the zoom events that have occured
        # below we factor in the total reduction scale
        # of the selected pyramid image by multiplying the total 
        # zoom scale by the reduction factor a number of times equal to
        # the index of the pyramid image in the pyramid list
        self.scale = self.imscale * self.reduce_factor**(max(0, self.curr_img))
        # rescale all objects in canvas using scale_inst
        self.canvas.scale('all', x, y, scale_inst, scale_inst)
        
        # below we scale the text
        rounding_indicator = self.clob.label_fsize * scale_inst
        # we will increase or decrease font size based on rounding indicator
        # if indicator is larger than font size (scale is inc), inc font size
        # if the indicator is smaller (scale is dec), dec font size
        # built-in protection against decreasing font size to zero
        if (rounding_indicator < self.clob.label_fsize 
                and rounding_indicator >= 1):
            self.new_font_size = math.floor(rounding_indicator)
        else:
            self.new_font_size = math.ceil(rounding_indicator)
        # once font size of 1 is reached, we need to make sure to 
        # keep track of scaling trends as we continue to demagnify image
        # if not, we will scale the font size 
        # too quickly while magnifying the image
        # the line of code below accomplishes the tracking by 
        # essentially recording the current number of scaling events
        self.clob.label_fsize = rounding_indicator 
        # find all text objects according to "text" tag
        for child_widget in self.canvas.find_withtag("text"):
            self.canvas.itemconfigure(child_widget, 
                                      font=("Arial", -self.new_font_size))
        # Redraw some figures before showing image on the screen
        self.show_image()

    def keystroke(self, event):
        """Scrolling with the keyboard.
        Independent from the language of the keyboard,
        CapsLock, <Ctrl>+<key>, etc.
        
        Parameters
        ----------
        event : tk event object
            Contains the relevant button press event info.

        Returns -> None
        """
        if event.state - self.previous_state == 4:  # Control key is pressed
            pass  # do nothing if Control key is pressed
        else:
            self.previous_state = event.state  # remember the last keystroke
            # Up, Down, Left, Right keystrokes
            # scroll right: keys 'D', 'Right' or 'Numpad-6'
            if event.keycode in [68, 39, 102]:
                self.scroll_x('scroll',  1, 'unit', event=event)
            # scroll left: keys 'A', 'Left' or 'Numpad-4'
            elif event.keycode in [65, 37, 100]:
                self.scroll_x('scroll', -1, 'unit', event=event)
            # scroll up: keys 'W', 'Up' or 'Numpad-8'
            elif event.keycode in [87, 38, 104]:
                self.scroll_y('scroll', -1, 'unit', event=event)
            # scroll down: keys 'S', 'Down' or 'Numpad-2'
            elif event.keycode in [83, 40, 98]:
                self.scroll_y('scroll',  1, 'unit', event=event)

    def destroy(self):
        """Destroy image list, frame, and canvas.
        Currently not in use.

        Returns -> None
        """
        self.image.close()
        map(lambda i: i.close, self.pyramid)  # close all pyramid images
        del self.pyramid[:]  # delete pyramid list
        del self.pyramid  # delete pyramid variable
        self.canvas.destroy()
        self.imframe.destroy()
