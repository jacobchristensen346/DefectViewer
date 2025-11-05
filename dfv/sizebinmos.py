# Mosaic Size Binning imports
import tkinter as tk
import numpy as np

class DefectSizeBinning:
    """ Defect Size Binning Class """
    def __init__(self, mosaic_settings):     
        
        self.mosaic_settings = mosaic_settings  # instance of DefectSizeBinning holds instance of MosaicSettings
        
        # instance variable initialization
        self.defect_binning_window = None  # will be used for creating tk defect binning window
        self.row_num = None  # will hold the total number of rows in binning
        self.list_of_entry_fields = None  # will be list of Entry tk objects
        self.button_set_binning = None  # button to set binning options
        self.button_close = None  # button to close window
        self.inf_bin_color = None  # will hold the infinity bin color choice

        self.main_binning_window()  # call for initial panel creation

    def main_binning_window(self):
        """ Create defect binning settings panel """
        # create the defect binning tkinter window
        self.defect_binning_window = tk.Toplevel()
        self.defect_binning_window.title('Defect Size Binning')

        self.row_num = len(self.mosaic_settings.binning_colors)  # dummy variable keeps track of number of defect binning ranges
        self.list_of_entry_fields = np.empty((0, 2))  # list to hold all entry variables for referencing

        # button used to add another defect binning range
        button_add_range = tk.Button(self.defect_binning_window, text='Add Range', width=11, command=self.add_binning_range)
        button_add_range.grid(row=0, column=0)

        # button to remove defect binning range
        button_remove_range = tk.Button(self.defect_binning_window, text='Remove Range', width=11, command=self.remove_binning_range)
        button_remove_range.grid(row=0, column=1)

        # button to accept binning and send to main mosaic settings window
        self.button_set_binning = tk.Button(self.defect_binning_window, text='Set Binning', width=10, command=self.set_binning_options)
        self.button_set_binning.grid(row=self.row_num + 2, column=3)

        # button to close window without setting new binning
        self.button_close = tk.Button(self.defect_binning_window, text='Close', width=10, command=self.defect_binning_window.destroy)
        self.button_close.grid(row=self.row_num + 3, column=3)

        # labels for the two columns, binning ceiling value and binning color value
        tk.Label(self.defect_binning_window, text='Bin Ceiling').grid(row=1, column=0, columnspan=1)
        tk.Label(self.defect_binning_window, text='Bin Color').grid(row=1, column=1, columnspan=1)

        # add in infinity bin (bin that starts at final finite bin ceiling and goes to infinity)
        self.inf_bin_color = tk.Entry(self.defect_binning_window, 
                                      textvariable=tk.StringVar(self.defect_binning_window, value=self.mosaic_settings.inf_bin_color), width=8)
        tk.Label(self.defect_binning_window, text='Infinity Bin Color').grid(row=0, column=3, columnspan=1)
        self.inf_bin_color.grid(row=0, column=4)

        # populate with previously saved choices...
        for i in range(self.row_num):
            self.list_of_entry_fields = np.append(self.list_of_entry_fields,
                                        [[tk.Entry(self.defect_binning_window, textvariable=tk.StringVar(self.defect_binning_window, value=self.mosaic_settings.binning_ranges[i]), width=10),
                                          tk.Entry(self.defect_binning_window, textvariable=tk.StringVar(self.defect_binning_window, value=self.mosaic_settings.binning_colors[i]), width=10)]], axis=0)
            self.list_of_entry_fields[-1][0].grid(row=i + 2, column=0)
            self.list_of_entry_fields[-1][1].grid(row=i + 2, column=1)

    def add_binning_range(self):
        """ Adds a new defect binning range entry """
        self.row_num += 1  # iterate the number of fields we have

        # add new entry fields to list
        self.list_of_entry_fields = np.append(self.list_of_entry_fields,
                                        [[tk.Entry(self.defect_binning_window, width=10),
                                          tk.Entry(self.defect_binning_window, width=10)]], axis=0)

        # after appending we can use -1 to reference the last item
        self.list_of_entry_fields[-1][0].grid(row=self.row_num + 1, column=0)
        self.list_of_entry_fields[-1][1].grid(row=self.row_num + 1, column=1)
        # now update the location of the accept and close buttons
        self.button_set_binning.grid(row=self.row_num + 2, column=3)
        self.button_close.grid(row=self.row_num + 3, column=3)

    def remove_binning_range(self):
        """ Removes most recent defect binning range entry """
        if len(self.list_of_entry_fields) > 0:
            (self.defect_binning_window.winfo_children()[-1]).destroy()
            (self.defect_binning_window.winfo_children()[-1]).destroy()
            # update the number of fields
            self.list_of_entry_fields = self.list_of_entry_fields[:-1]
            self.row_num -= 1
            # now update the location of the accept and close buttons
            self.button_set_binning.grid(row=self.row_num + 2, column=3)
            self.button_close.grid(row=self.row_num + 3, column=3)
        else:
            print('No binning ranges to remove')
            
    def get_var_value(self, x):
        """ Simple helper function for vectorization """
        return x.get()
    
    def check_field_inputs(self) -> bool:
        """ Tests the user's inputs for validity """
        # first check if there are no bin range fields
        if self.list_of_entry_fields.size == 0: 
            return True
        
        vectorized = np.vectorize(self.get_var_value)  # we vectorize a function to get values out of StringVar
        range_inputs = vectorized(self.list_of_entry_fields[:, 0:1]).flatten()  # bin range inputs
        color_inputs = vectorized(self.list_of_entry_fields[:, 1:2]).flatten()  # bin color inputs
        color_test = tk.Toplevel()  # create temporary window for color testing
        try:
            # if the color is invalid, a TclError will be raised
            tk.Label(color_test, bg=self.inf_bin_color.get())
            for color in color_inputs:
                tk.Label(color_test, bg=color)
            range_inputs.astype(float)  # test if bin range array values can be converted to float
            if np.all(np.diff(range_inputs.astype(float)) > 0):  # test if range values are strictly increasing
                return True
            else:
                print("Error, bin range values are not strictly increasing")
                return False
        except tk.TclError:
            print("Invalid color input")
            return False
        except ValueError:
            print("Invalid input, please enter decimal numbers for binning ranges")
            return False
        except Exception as e:  # Catch any other unexpected errors
            print(f"The following error occurred from user input: {e}")
            return False
        finally:
            color_test.destroy()  # ensure test window is destroyed

    def set_binning_options(self):
        """ Send current binning options back to MosaicSettings """
        # check user inputs for validity
        if self.check_field_inputs():
            # if user inputs pass validity test proceed with saving the values
            if self.list_of_entry_fields.size == 0:
                self.mosaic_settings.binning_ranges = np.array([])
                self.mosaic_settings.binning_colors = np.array([])
            else:
                vectorized = np.vectorize(self.get_var_value)  # we vectorize a function to get values out of StringVar
                self.mosaic_settings.binning_ranges = vectorized(self.list_of_entry_fields[:, 0:1]).flatten().astype(float)
                self.mosaic_settings.binning_colors = vectorized(self.list_of_entry_fields[:, 1:2]).flatten()
            self.mosaic_settings.inf_bin_color = self.inf_bin_color.get()
            self.mosaic_settings.which_binning_show = "SIZE"
        else:
            pass
