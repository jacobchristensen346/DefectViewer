# Mosaic Creator imports
import tkinter as tk
from PIL import Image, ImageTk
from tkinter import ttk
from tkinter import Tk, Canvas, mainloop
import warnings
import numpy as np
import sqlite3
import os

# custom modules
from dfv import setmos
from dfv import tileclick

class MosaicCreator:
    """ Create Mosaic With Selectable Tiles """
    def __init__(self, root):

        self.root = root  # MosaicCreator instance holds instance of Root 

        self.font_size_defect_label = "20"  # text size of defect labels on clicked tile
        self.defect_mark_size = "3"  # defect marker size on mosaic
        self.binning_ranges = self.root.binning_ranges  # set ranges to default received by root
        self.binning_colors = self.root.binning_colors  # set colors to default received by root
        self.binning_type_colors = np.array([])  # colors for defect classification binning (no default unlike size binning)
        self.inf_bin_color = self.root.inf_bin_color  # set infinity bin color to default received by root
        self.which_binning_show = 'SIZE'  # determines which color binning to show
        
        # this array keeps track of the defect info which will be output on the defect label text line
        self.defect_label_text_choices = np.array([False, False, False, False, True, True, False, False, True, False,
                                                   False, False, False, False, False, False, False, False])
        
        # set unique analysis ID instance variable for MosaicCreator
        # allows analysis ID change without affecting Root window
        self.analysis_id = self.root.ana_id.get()

        # more instance variable initializations
        self.canvas = None  # canvas to plot mosaic image and defects
        self.mosaic_image = None  # will be used to creat tk photo image object
        self.mos_source_width = None  # will be used to store native width of the mosaic image
        self.mos_source_height = None  # will be used to store native height of the mosaic image
        # arrays to hold number of defects per bin for size/type binning
        self.num_defects_type_binning = None
        self.num_defects_size_binning = None

        # create a new tkinter window for plotting the mosaic of the scans
        self.mosaic_window = tk.Toplevel()
        self.sample_name = (self.root.db_file.get().split("/"))[-1]
        self.mosaic_window.title(self.sample_name + " || " + "Scan ID = " + str(self.root.scan_id.get()) + " || " + "Analysis ID = " + str(self.analysis_id))

        # connect to the database containing analysis and scan information
        self.conn = sqlite3.connect(self.root.db_file.get())
        self.cur = self.conn.cursor()

        # sql queries used to retrieve defect and image data
        self.sql_cmd_pos = "SELECT * FROM vwImages WHERE ScanID = ?;" 
        self.sql_cmd_def = "SELECT * FROM vwDefectsLegacy WHERE AnalysisID = ?;" 
        self.sql_cmd_scn = "SELECT * FROM ScanProperties WHERE ScanID = ?"
        self.sql_cmd_typ = "SELECT * FROM DetectionClasses WHERE AnalysisID = ?"

        self.image_data = np.array(self.cur.execute(self.sql_cmd_pos, (str(self.root.scan_id.get()),)).fetchall())  # fetch all data from image table
        self.defect_data = np.array(self.cur.execute(self.sql_cmd_def, (str(self.analysis_id),)).fetchall())  # fetch all data from defect table
        self.scan_properties = np.array(self.cur.execute(self.sql_cmd_scn, (str(self.root.scan_id.get()),)).fetchall())  # fetch all data from scan properties table
        self.defect_type_data = np.array(self.cur.execute(self.sql_cmd_typ, (str(self.analysis_id),)).fetchall())  # fetch all data from detection class table

        # call image plotting function upon class object creation
        self.plot_mosaic()

    def plot_defects(self):
        """ Plot the defects onto the mosaic created by plot_mosaic function """
        self.canvas.delete("DEFECT_MARK_SIZE_BINNING")  # deletes all current defect marks to allow for re-plotting
        self.canvas.delete("DEFECT_MARK_CLASS_BINNING")

        # initialize arrays to hold number of defects per bin for size/type binning
        self.num_defects_size_binning = np.zeros([len(self.binning_colors) + 1])  
        self.num_defects_type_binning = np.zeros([len(self.binning_type_colors) + 1])  

        for idx, def_row in enumerate(self.defect_data):

            tile_row_index = np.where(np.any(self.image_data[:, 0:1].astype(float) == float(def_row[1]), axis=1))[0]  # find the tile where defect resides
            tile_row = float(self.image_data[tile_row_index, 7][0])  # find the Row and Column of the tile in the mosaic image
            tile_column = float(self.image_data[tile_row_index, 8][0])
            tile_width_um = float(self.image_data[tile_row_index, 9][0])  # find width and height of tile in um
            tile_height_um = float(self.image_data[tile_row_index, 10][0])
            tile_width_pix = float(self.image_data[tile_row_index, 11][0])  # find width and height of tile in pixels
            tile_height_pix = float(self.image_data[tile_row_index, 12][0])
            def_x_tile = float(def_row[4])  # obtain the coordinates of defect within its image tile (um)
            def_y_tile = float(def_row[5])

            # find defect coordinates in mosaic, convert to pixels, and scale by number of rows/cols in the mosaic
            x_mosaic = self.mos_tile_width * ((def_x_tile + (tile_column * tile_width_um)) * (tile_width_pix / tile_width_um)) / tile_width_pix
            y_mosaic = self.mos_tile_height * ((def_y_tile + (tile_row * tile_height_um)) * (tile_height_pix / tile_height_um)) / tile_height_pix

            size_adj = float(self.defect_mark_size)  # arbitrary scaling value used to control size of defect mark on mosaic

            # we will plot multiple copies of each defect overlaid on each other
            # each copy will have a different defect mark color for the different available binning types
            # then we can simply toggle the defect visibility by using tags for each bin type

            # get index corresponding to binning range of defect area
            bin_range_index = np.searchsorted(self.binning_ranges, float(def_row[8]))
            # set size-based defect mark color based on binning color corresponding to index found above
            if (bin_range_index > (len(self.binning_ranges) - 1)) or (self.binning_ranges.size == 0):
                mark_color = self.inf_bin_color
                self.num_defects_size_binning[len(self.binning_colors)] += 1  # iterate defect count for infinity bin
            else:
                mark_color = self.binning_colors[bin_range_index]
                self.num_defects_size_binning[bin_range_index] += 1  # iterate defect count for specific bin

            # set class-based defect mark color based on user binning input
            if self.binning_type_colors.size == 0 or self.defect_type_data.size == 0:
                mark_type_color = self.inf_bin_color
                self.num_defects_type_binning[len(self.binning_type_colors)] += 1  # iterate defect count for infinity bin
            else:
                mark_type_color = self.binning_type_colors[np.where(self.defect_type_data[:, 0:1].flatten() == def_row[15])][0]
                self.num_defects_type_binning[np.where(self.defect_type_data[:, 0:1].flatten() == def_row[15])] += 1  # iterate defect count for specific bin

            # now plot the defect on the mosaic, we plot multiple overlaid copies for each binning type
            self.canvas.create_oval(x_mosaic - size_adj, y_mosaic - size_adj, 
                                    x_mosaic + size_adj, y_mosaic + size_adj, 
                                    outline=mark_color, fill=mark_color, tags="DEFECT_MARK_SIZE_BINNING")
            self.canvas.create_oval(x_mosaic - size_adj, y_mosaic - size_adj, 
                                    x_mosaic + size_adj, y_mosaic + size_adj, 
                                    outline=mark_type_color, fill=mark_type_color, tags="DEFECT_MARK_CLASS_BINNING")
            self.canvas.itemconfigure("DEFECT_MARK_SIZE_BINNING", state="hidden")
            self.canvas.itemconfigure("DEFECT_MARK_CLASS_BINNING", state="hidden")

        # by default we will show the defect size binning 
        if self.which_binning_show == "SIZE":
            self.canvas.itemconfigure("DEFECT_MARK_SIZE_BINNING", state="normal")
        if self.which_binning_show == "CLASS":
            self.canvas.itemconfigure("DEFECT_MARK_CLASS_BINNING", state="normal")

    def toggle_binning(self, toggle_choice):
        """ Toggles visibility for the desired set of defect binning colors """
        self.which_binning_show = toggle_choice  # we must update variable for binning visibility, bug fix
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

        # create labels for current bin info and defect counts, check current binning mode
        # if defect binning selection is "SIZE"...
        if self.which_binning_show == "SIZE":
            tk.Label(ana_stats_window, text="Bin Ceiling").grid(row=0, column=0)  # create headers
            tk.Label(ana_stats_window, text="Bin Color").grid(row=0, column=1)
            tk.Label(ana_stats_window, text="Number of Defects").grid(row=0, column=2)
            ttk.Separator(ana_stats_window, orient='horizontal').grid(row=1, column=0, columnspan=3, sticky='ew')
            # iterate through all the ranges/colors and create labels for each
            for i in range(len(self.binning_colors)):
                tk.Label(ana_stats_window, text=str(self.binning_ranges[i])).grid(row=i + 2, column=0)
                tk.Label(ana_stats_window, text=str(self.binning_colors[i]), fg=str(self.binning_colors[i])).grid(row=i + 2, column=1)
                tk.Label(ana_stats_window, text=str(int(self.num_defects_size_binning[i]))).grid(row=i + 2, column=2)
            tk.Label(ana_stats_window, text="Infinity").grid(row=len(self.binning_colors) + 3, column=0)
            tk.Label(ana_stats_window, text=str(self.inf_bin_color), fg=str(self.inf_bin_color)).grid(row=len(self.binning_colors) + 3, column=1)
            tk.Label(ana_stats_window, text=str(int(self.num_defects_size_binning[-1]))).grid(row=len(self.binning_colors) + 3, column=2)

            # button to close window
            button_close = tk.Button(ana_stats_window, text='Close', width=10, command=ana_stats_window.destroy)
            button_close.grid(row=len(self.binning_colors) + 4, column=2, columnspan=1)

        # if defect binning selection is "CLASS"...
        if self.which_binning_show == "CLASS":
            tk.Label(ana_stats_window, text="Defect Class Name").grid(row=0, column=0)  # create headers
            tk.Label(ana_stats_window, text="Bin Color").grid(row=0, column=1)
            tk.Label(ana_stats_window, text="Number of Defects").grid(row=0, column=2)
            ttk.Separator(ana_stats_window, orient = 'horizontal').grid(row=1, column=0, columnspan=3, sticky='ew')
            # first check if any class binning has been applied (or if classes even exist for this analysis)
            if len(self.binning_type_colors) == 0:
                tk.Label(ana_stats_window, text="No Binning Set Yet!").grid(row=2, column=0)
                tk.Label(ana_stats_window, text=str(self.inf_bin_color), fg=str(self.inf_bin_color)).grid(row=2, column=1)
                tk.Label(ana_stats_window, text=str(int(self.num_defects_type_binning[-1]))).grid(row=2, column=2)
            else:
                # iterate through all the colors/class names and create labels for each
                for i in range(len(self.binning_type_colors)):
                    tk.Label(ana_stats_window, text=str(self.defect_type_data[i][2])).grid(row=i + 2, column=0)
                    tk.Label(ana_stats_window, text=str(self.binning_type_colors[i]), fg=str(self.binning_type_colors[i])).grid(row=i + 2, column=1)
                    tk.Label(ana_stats_window, text=str(int(self.num_defects_type_binning[i]))).grid(row=i + 2, column=2)

            # button to close window
            button_close = tk.Button(ana_stats_window, text='Close', width = 10, command=ana_stats_window.destroy)
            button_close.grid(row = len(self.binning_type_colors)+3, column=2, columnspan=1)

    def plot_mosaic(self):
        """ Plot the mosaic onto a selectable canvas """                
        # create new label in root window which tracks image loading progress
        # first destroy previous loading progress label
        for child in self.root.root_wnd.winfo_children():
            if "LOAD_PROGRESS" in child.bindtags():
                child.destroy()
        load_progress = tk.Label(self.root.root_wnd, text='Loading Image...')
        load_progress.bindtags(load_progress.bindtags() + ("LOAD_PROGRESS",))  # add custom tag for deletion purposes
        load_progress.grid(row=6, column=2, columnspan=2)
        self.root.root_wnd.update()

        list_of_images = np.array(next(os.walk(self.root.img_loc + '/'))[2])  # list of images from directory
        mosaic_image_name = list_of_images[np.flatnonzero(np.char.find(list_of_images,'Mosaic') != -1)[0]]  # find mosaic image in list
        image = Image.open(self.root.img_loc + '/' + mosaic_image_name)  # open initial mosaic image from file
        self.mos_source_width, self.mos_source_height = image.size  # get the native size of the mosaic image
        # resize mosaic image and interpolate
        image = image.resize((round(self.mos_source_width / int(self.root.image_scale.get())), round(self.mos_source_height / int(self.root.image_scale.get()))), Image.LANCZOS)
        self.mos_resize_width, self.mos_resize_height = image.size  # get the new size of mosaic image

        # create the canvas with size according to resized mosaic image
        self.canvas = Canvas(self.mosaic_window, width=self.mos_resize_width, height=self.mos_resize_height, bd=0)

        # button for advanced settings, passes instance of MosaicCreator to MosaicSettings
        button_advanced = tk.Button(self.mosaic_window, text='Advanced', width=10, command=lambda: setmos.MosaicSettings(self))

        # button for opening analysis statistics window
        button_analy_stats = tk.Button(self.mosaic_window, text='Analysis Stats', width=10, command=self.analysis_stats)

        # button for showing size-binned defect colors
        button_size_binning = tk.Button(self.mosaic_window, text='Size Binning', width=10, command=lambda: self.toggle_binning("SIZE"))

        # button for showing class-binned defect colors
        button_class_binning = tk.Button(self.mosaic_window, text='Class Binning', width=10, command=lambda: self.toggle_binning("CLASS"))

        self.mosaic_image = ImageTk.PhotoImage(image)  # create tkinter photo object
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.mosaic_image, tags="IMAGE_TILE")

        # now prepare for plotting defects onto canvas
        # find max # rows and columns -> will be used to scale individual mosaic tile
        row_numbers = (self.image_data[:, 7:8]).astype(int)
        col_numbers = (self.image_data[:, 8:9]).astype(int)
        max_rows = max(row_numbers)[0] + 1
        max_cols = max(col_numbers)[0] + 1

        # obtain size of one mosaic tile in pixels (based on # mosaic rows and columns)
        self.mos_tile_width = self.mos_resize_width / max_cols
        self.mos_tile_height = self.mos_resize_height / max_rows

        # check if user has selected image view only
        if self.root.image_view_only.get() == 0: 
            self.plot_defects()  # function that plots the defects onto the canvas created above

        self.canvas.bind('<Button-1>', lambda event: tileclick.Clicked(self, event))  # makes mosaic selectable

        load_progress.config(text='Done Loading!')  # update root window upon image load completion
        self.root.root_wnd.update()

        # place all the items according to grid
        self.canvas.grid(row=0, column=0)
        button_advanced.grid(row=1, column=0)
        button_size_binning.grid(row=1, column=0, sticky='e')
        button_class_binning.grid(row=2, column=0, sticky='e')

        button_analy_stats.grid(row=3, column=0, sticky='e')
