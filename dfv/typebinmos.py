# Mosaic Type Binning imports
import tkinter as tk
import numpy as np

class DefectTypeBinning:
    """ Defect Type Binning Class """
    def __init__(self, mosaic_settings):     
        
        self.mosaic_settings = mosaic_settings  # DefectTypeBinning instance holds instance of MosaicSettings
        
        # instance variable initialization
        self.defect_binning_window = None  # for creating the defect binning tk window
        self.row_num = None  # will hold the total number of rows in the defect binning
        self.list_of_entry_fields = None  # list of Entry tk objects for binning
        self.button_set_binning = None  # will be set as button for accepting binning
        self.button_close = None  # will be set as button to close binning window

        self.main_binning_window()  # call for initial panel creation

    def main_binning_window(self):
        """ Create defect type binning settings panel """
        # create the defect binning tkinter window
        self.defect_binning_window = tk.Toplevel()
        self.defect_binning_window.title('Defect Class Binning')

        self.row_num = len(self.mosaic_settings.mosaic_creator.defect_type_data)  # dummy variable records number of defect classification bins
        self.list_of_entry_fields = np.empty((0, 2))  # list to hold all entry variables for referencing

        # button to accept binning and send to main mosaic settings window
        self.button_set_binning = tk.Button(self.defect_binning_window, text='Set Binning', width=10, command=self.set_binning_options)
        self.button_set_binning.grid(row=self.row_num + 2, column=3)

        # button to close window without setting new binning
        self.button_close = tk.Button(self.defect_binning_window, text='Close', width=10, command=self.defect_binning_window.destroy)
        self.button_close.grid(row=self.row_num + 3, column=3)

        # labels for the two columns, binning color value and bin class name
        tk.Label(self.defect_binning_window, text='Bin Class Color').grid(row=1, column=1, columnspan=1)
        tk.Label(self.defect_binning_window, text='Bin Class Name').grid(row=1, column=0, columnspan=1)

        # populate with previously saved choices...
        # the number of entries is automatically set by the number of defect class names in the chosen analysis
        # also check first if defect classes exist for chosen analysis ID
        if self.mosaic_settings.mosaic_creator.defect_type_data.size == 0:
            tk.Label(self.defect_binning_window, text='---NO CLASSES IN CHOSEN ANALYSIS---').grid(row=2, column=0, columnspan=2)
        else:
            for i, type_entry in enumerate(self.mosaic_settings.mosaic_creator.defect_type_data[:, [0, 2]]):
                if self.mosaic_settings.binning_type_colors.size == 0:
                    self.list_of_entry_fields = np.append(self.list_of_entry_fields,
                                                [[tk.Label(self.defect_binning_window, text=type_entry[1]),
                                                  tk.Entry(self.defect_binning_window, textvariable=tk.StringVar(self.defect_binning_window), width=10)]], axis=0)
                else:
                    self.list_of_entry_fields = np.append(self.list_of_entry_fields,
                                                [[tk.Label(self.defect_binning_window, text=type_entry[1]),
                                                  tk.Entry(self.defect_binning_window, textvariable=tk.StringVar(self.defect_binning_window, value=self.mosaic_settings.binning_type_colors[i]), width=10)]], axis=0)    
                self.list_of_entry_fields[-1][0].grid(row=i + 2, column=0)
                self.list_of_entry_fields[-1][1].grid(row=i + 2, column=1)

    def set_binning_options(self):
        """ Send current binning options back to MosaicSettings """
        # check first if defect classes exist for chosen analysis ID
        if self.mosaic_settings.mosaic_creator.defect_type_data.size == 0:
            return
        else:
            def get_var_value(x):
                return x.get()

            # we vectorize a function to get values out of StringVar
            vectorized = np.vectorize(get_var_value)
            self.mosaic_settings.binning_type_colors = vectorized(self.list_of_entry_fields[:, 1:2]).flatten()
            self.mosaic_settings.which_binning_show = "CLASS"