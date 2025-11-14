# Mosaic Settings imports
import numpy as np
import tkinter as tk
from tkinter import ttk

# custom modules
from dfv import sizebinmos
from dfv import typebinmos

class MosaicSettings:
    """ Mosaic Settings Class """
    def __init__(self, mosaic_creator):

        self.mosaic_creator = mosaic_creator # instance MosaicSettings holds instance of MosaicCreator

        # many of these instance variables are copies of the corresponding passed variables
        # we operate on these variables instead of the MosaicCreator instance
        # ensures MosaicCreator instance is not immediately updated, but only when wanted within the GUI
        self.binning_ranges = self.mosaic_creator.binning_ranges  # the desired binning ranges given in um^2
        self.binning_colors = self.mosaic_creator.binning_colors  # the desired binning colors for size binning
        self.binning_type_colors = self.mosaic_creator.binning_type_colors  # the desired colors for defect type binning
        self.inf_bin_color = self.mosaic_creator.inf_bin_color  # the desired infinity bin color
        self.which_binning_show = self.mosaic_creator.which_binning_show  # determines which binning type to display on mosaic
        self.defect_label_text_choices = np.copy(self.mosaic_creator.defect_label_text_choices)  # create copy to avoid overwritting
        self.mosaic_settings_window = None  # tk window for mosaic settings
        self.font_size_defect_label = None  # will hold desired font size for defect labels on magnified tile
        self.defect_mark_size = None  # will hold desired defect marker size on canvas
        self.analysis_id = self.mosaic_creator.analysis_id  # allows for reselection of analysis ID in settings

        # call function to create initial settings panel
        self.main_mosaic_settings()

    def main_mosaic_settings(self):
        """ Create initial advanced mosaic settings panel """   
        # create the mosaic settings tkinter window
        self.mosaic_settings_window = tk.Toplevel()
        self.mosaic_settings_window.title('Mosaic Advanced Settings')

        # font size of defect label text
        self.font_size_defect_label = tk.StringVar(self.mosaic_settings_window, value=self.mosaic_creator.font_size_defect_label)
        tk.Label(self.mosaic_settings_window, text='Defect Label Font Size').grid(row=1, column=0, columnspan=1)
        entry_font_size_defect_label = tk.Entry(self.mosaic_settings_window, textvariable=self.font_size_defect_label, width=5)
        entry_font_size_defect_label.grid(row=1, column=1, columnspan=1)

        # change the size of the defect markers on the mosaic canvas
        self.defect_mark_size = tk.StringVar(self.mosaic_settings_window, value=self.mosaic_creator.defect_mark_size)
        tk.Label(self.mosaic_settings_window, text='Defect Mark Size').grid(row=2, column=0, columnspan=1)
        entry_mark_resize = tk.Entry(self.mosaic_settings_window, textvariable=self.defect_mark_size, width=5)
        entry_mark_resize.grid(row=2, column=1, columnspan=1)

        # change the analysis ID and replot defects
        analysis_options = np.insert(self.mosaic_creator.root.analysis_options, 0, 'Select Choice')
        self.analysis_id_change = tk.StringVar(self.mosaic_settings_window, value=analysis_options[0])
        tk.Label(self.mosaic_settings_window, text='Analysis ID').grid(row=3, column=0, columnspan=1)
        entry_analysis_id_change = ttk.OptionMenu(self.mosaic_settings_window, self.analysis_id_change, *analysis_options)
        entry_analysis_id_change.grid(row=3, column=1, columnspan=3, sticky='w')

        # button to open defect area binning window
        # pass instance of MosaicSettings to DefectSizeBinning
        button_defect_binning = tk.Button(self.mosaic_settings_window, text='Size Binning', width=10, 
                                          command=lambda: sizebinmos.DefectSizeBinning(self))
        button_defect_binning.grid(row=4, column=0)

        # button to open defect class binning window
        # pass instance of MosaicSettings to DefectTypeBinning
        button_defect_binning = tk.Button(self.mosaic_settings_window, text='Class Binning', width=10, 
                                          command=lambda: typebinmos.DefectTypeBinning(self))
        button_defect_binning.grid(row=5, column=0)

        # button to open defect text label options
        button_defect_label_text = tk.Button(self.mosaic_settings_window, text='Defect Text Options', width=16, command=self.defect_text_options)
        button_defect_label_text.grid(row=6, column=0)

        # button to apply settings
        button_accept = tk.Button(self.mosaic_settings_window, text='Accept', width=10, command=self.return_choices_mosaic)
        button_accept.grid(row=5, column=3)

        # button to close without saving
        button_close = tk.Button(self.mosaic_settings_window, text='Close', width=10, command=self.mosaic_settings_window.destroy)
        button_close.grid(row=6, column=3)

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

        checkbox_vars = np.array([])  # keep track of the checkbox variables
        converted_choices = self.defect_label_text_choices.astype(int)  # convert to int, tkinter does not like numpy booleans

        # now create the checkboxes
        for i, option in enumerate(options):
            checkbox_vars = np.append(checkbox_vars, tk.IntVar(text_options_window, value=converted_choices[i]))
            checkbox = tk.Checkbutton(text_options_window, text=option, variable=checkbox_vars[i])
            checkbox.pack()

        # button to apply settings
        button_accept = tk.Button(text_options_window, text='Set Options', 
                                  width=10, command=lambda arg=checkbox_vars: set_text_options(arg))
        button_accept.pack()

        # button to close without saving
        button_close = tk.Button(text_options_window, text='Close', width=10, command=text_options_window.destroy)
        button_close.pack()

    def return_choices_mosaic(self):
        """ Sends input settings back to MosaicCreator """  
        self.mosaic_creator.font_size_defect_label = self.font_size_defect_label.get()
        self.mosaic_creator.binning_ranges = self.binning_ranges
        self.mosaic_creator.binning_colors = self.binning_colors
        self.mosaic_creator.binning_type_colors = self.binning_type_colors
        self.mosaic_creator.which_binning_show = self.which_binning_show
        self.mosaic_creator.inf_bin_color = self.inf_bin_color
        self.mosaic_creator.defect_mark_size = self.defect_mark_size.get()
        self.mosaic_creator.defect_label_text_choices = np.copy(self.defect_label_text_choices)
        # update defect data if needed
        if self.mosaic_creator.analysis_id != self.analysis_id_change.get() and self.analysis_id_change.get() != 'Select Choice':
            self.mosaic_creator.analysis_id = self.analysis_id_change.get()
            self.mosaic_creator.defect_data = np.array(self.mosaic_creator.cur.execute(self.mosaic_creator.sql_cmd_def, 
                                                                                       (str(self.mosaic_creator.analysis_id),)).fetchall())  # fetch all data from defect table
            self.mosaic_creator.defect_type_data = np.array(self.mosaic_creator.cur.execute(self.mosaic_creator.sql_cmd_typ, 
                                                                                            (str(self.mosaic_creator.analysis_id),)).fetchall())  # fetch all data from detection class table

            # we must reset defect classification binning in both MosaicCreator and MosaicSettings
            # otherwise, if the MosaicSettings window is not closed between analysis ID changes the previous binning is remembered and applied to wrong analysis
            # we can leave area binning alone since it can apply in any analysis
            self.mosaic_creator.binning_type_colors = np.array([])
            self.binning_type_colors = np.array([])

            # now update the name of the window
            self.mosaic_creator.mosaic_window.title(self.mosaic_creator.sample_name + " || " + "Scan ID = " + 
                                                    str(self.mosaic_creator.root.scan_id.get()) + " || " + "Analysis ID = " + 
                                                    str(self.mosaic_creator.analysis_id))

        # re-plot the mosaic with the new settings
        # check if user has selected image view only
        if self.mosaic_creator.root.image_view_only.get() == 0:
            self.mosaic_creator.plot_defects()