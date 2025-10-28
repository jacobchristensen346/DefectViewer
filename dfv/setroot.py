# Root Settings imports
import tkinter as tk

# custom module
from dfv import sizebinroot

class RootSettings:
    """ Advanced Settings Class for Root Window """ 
    def __init__(self, root):
        
        self.root =  root  # RootSettings instance holds Root instance
        
        # instance variable initialization
        self.adv_window = None  # used for root settings tk window
        self.binning_colors = self.root.binning_colors  # set colors to the root values initially
        self.binning_ranges = self.root.binning_ranges  # set ranges to the root values initially
        self.inf_bin_color = self.root.inf_bin_color  # set infinity bin color to the root value initially
        
        self.initial_panel_root()  # call initial panel function

    def initial_panel_root(self):
        """ Create initial advanced settings panel from the Root window """   
        self.adv_window = tk.Toplevel()
        self.adv_window.title('Advanced Settings')
        
        # button to open window used to modify default size binning applied to all mosaics plotted from root
        # pass instance of RootSettings to DefectSizeBinningRoot
        button_defect_binning = tk.Button(self.adv_window, text='Default Size Binning', width=17, command=lambda: sizebinroot.DefectSizeBinningRoot(self))
        button_defect_binning.grid(row=0, column=0)

        # button to apply root settings
        button_accept = tk.Button(self.adv_window, text='Accept', width=10, command=self.return_choices_root)
        button_accept.grid(row=1, column=3)

        # button to close root settings window without applying changes
        button_close = tk.Button(self.adv_window, text='Close', width=10, command=self.adv_window.destroy)
        button_close.grid(row=2, column=3)
            
    def return_choices_root(self):
        """ Sends input settings back to Root """
        self.root.binning_ranges = self.binning_ranges
        self.root.binning_colors = self.binning_colors
        self.root.inf_bin_color = self.inf_bin_color