"""
dfv.exceptions
--------------

This module provides classes for handling exceptions across the package
"""

# Exceptions imports
import numpy as np
import tkinter as tk

class CheckSizeBinning:
    """ Checks user inputs for the mosaic's defect size binning """
    
    def __init__(self, list_of_entry_fields, inf_bin_color_entry):
        self.list_of_entry_fields = list_of_entry_fields
        self.inf_bin_color_entry = inf_bin_color_entry
        
    def get_var_value(self, x):
        """ Simple helper function for vectorization """
        return x.get()
    
    def check_field_inputs(self) -> bool:
        """ Tests the user's inputs for validity """
        # first check if there are no bin range fields
        if self.list_of_entry_fields.size == 0: 
            return True
        
        # we vectorize a function to get values out of StringVar
        vectorized = np.vectorize(self.get_var_value)
        # bin range and color inputs
        range_inputs = vectorized(self.list_of_entry_fields[:, 0:1]).flatten()
        color_inputs = vectorized(self.list_of_entry_fields[:, 1:2]).flatten()  
        color_test = tk.Toplevel()  # create temporary window for color testing
        try:
            # if the color is invalid, a TclError will be raised
            tk.Label(color_test, bg=self.inf_bin_color_entry.get())
            for color in color_inputs:
                tk.Label(color_test, bg=color)
            # test if bin range array values can be converted to float
            range_inputs.astype(float)
            # test if range values are strictly increasing
            if np.all(np.diff(range_inputs.astype(float)) > 0):
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