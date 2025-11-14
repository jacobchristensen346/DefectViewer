# Root imports
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import os
import sqlite3
import numpy as np

# custom modules
from dfv import pdfshow
from dfv import createmos
from dfv import setroot

class Root:
    """ Class to create initial Root gui window """
    def __init__(self):
        
        # create root window
        self.root_wnd = tk.Tk()
        self.root_wnd.title('Defect Viewer v2.0')
        
        # instance variable initialization
        self.scan_options = np.array(['Select Choice'])  # list of scan IDs to choose from
        self.analysis_options = np.array(['Select Choice'])  # list of analysis IDs to choose from
        self.img_loc = None  # path to folder containing images for specific scan
        self.scan_dir = tk.StringVar()  # path to folder containing all scan folders
        self.db_file = tk.StringVar()  # path to database file
        self.scan_id = tk.StringVar(self.root_wnd, value = self.scan_options[0])  # specific scan ID to plot
        self.ana_id = tk.StringVar(self.root_wnd, value = self.analysis_options[0])  # specific analysis ID to draw defects from
        self.image_scale = tk.StringVar()  # image is scaled by dividing by this variable (integer)
        self.scan_dir_entry = None  # will be defined as text entry field for scan directory
        self.db_file_entry = None  # will be defined as text entry field for database file location
        self.scan_id_select = None  # will be defined as options menu to select scan ID choice
        self.ana_id_select = None  # will be defined as the options menu to select analysis ID choice
        self.image_view_only = None  # variable to hold checkbox choice whether to plot defects or images alone
        self.save_pdf_imgs = None  # variable to capture image output from ShowPdf (instructions manual)
        self.binning_ranges = np.array([16000, 32000, 64000, 112000, 160000]) # set bin size ranges to arbitrary values
        self.binning_colors = np.array(['aqua', 'chartreuse3', 'royalblue3', 'goldenrod1', 'magenta3']) # set bin colors to arbitrary values
        self.inf_bin_color = 'red'  # set infinity bin color to arbitrary value
        
        self.main_root_window()  # call function to modify root window
        
    def main_root_window(self):
        """ Modify the main root window """

        self.scan_id.trace('w', self.scan_select)  # cause scan selection to update analysis option menu

        # button to open embedded pdf of software manual
        button_open_instruct = tk.Button(self.root_wnd, text='?', width=3, command=self.open_instructions)
        button_open_instruct.grid(row=0, column=4, columnspan=1, sticky='e')
        
        # text field to enter location of directory containing scan folders
        tk.Label(self.root_wnd, text='Scans Directory').grid(row=0, column=0, columnspan=1)
        self.scan_dir_entry = tk.Entry(self.root_wnd, textvariable=self.scan_dir, width=20)
        self.scan_dir_entry.grid(row=0, column=2, columnspan=1)
        
        # text field to enter location of database file
        tk.Label(self.root_wnd, text='Database File').grid(row=1, column=0, columnspan=1)
        self.db_file_entry = tk.Entry(self.root_wnd, textvariable=self.db_file, width=20)
        self.db_file_entry.grid(row=1, column=2, columnspan=1)
        
        # dropdown menu to select scan ID
        tk.Label(self.root_wnd, text='Scan ID').grid(row=3, column=0, columnspan=1)
        self.scan_id_select = ttk.OptionMenu(self.root_wnd, self.scan_id, *self.scan_options)
        self.scan_id_select.grid(row=3, column=2, columnspan=1, sticky='w')
        
        # dropdown menu to select analysis ID
        tk.Label(self.root_wnd, text='Analysis ID').grid(row=4, column=0, columnspan=1)
        self.ana_id_select = ttk.OptionMenu(self.root_wnd, self.ana_id, *self.analysis_options)
        self.ana_id_select.grid(row=4, column=2, columnspan=1, sticky='w')
        
        # text field to enter image scale reduction factor
        tk.Label(self.root_wnd, text='Image Scale').grid(row=5, column=0, columnspan=1)
        image_scale_entry = tk.Entry(self.root_wnd, textvariable=self.image_scale, width=10)
        image_scale_entry.grid(row=5, column=2, columnspan=1, sticky='w')

        # button to set the image and database paths, updating scan and analysis option menus
        button_set_paths = tk.Button(self.root_wnd, text='Set Image and DB paths', command=self.set_paths)
        button_set_paths.grid(row=2, column=1, columnspan=3, sticky='w')
        
        # these buttons allow the file explorer to be opened to receive directory inputs
        button_file = tk.Button(self.root_wnd, text='...', width=3, command=self.browse_file)
        button_directory = tk.Button(self.root_wnd, text='...', width=3, command=self.browse_directory)
        button_file.grid(row=1, column=4, columnspan=1, sticky='w')
        button_directory.grid(row = 0, column=4, columnspan=1, sticky='w')

        # these buttons open windows displaying information about the currently selected scan/analysis IDs
        button_scan_props = tk.Button(self.root_wnd, text='Scan Props', command=self.scan_props)
        button_scan_props.grid(row=3, column=4, columnspan=1, sticky='w')
        button_analysis_props = tk.Button(self.root_wnd, text='Analysis Props', command=self.analysis_props)
        button_analysis_props.grid(row=4, column=4, columnspan=1, sticky='w')
        
        # this button opens up advanced settings, and passes instance of Root to RootSettings
        button_advanced = tk.Button(self.root_wnd, text='Advanced', width=10, command=lambda: setroot.RootSettings(self))
        button_advanced.grid(row=6, column=0, columnspan=1)
        
        # create a checkbox to signal when to only open image and not plot defects
        self.image_view_only = tk.IntVar(self.root_wnd, value=0)
        checkbox_seq = tk.Checkbutton(self.root_wnd, text='Image Viewer Only', variable=self.image_view_only)
        checkbox_seq.grid(row=7, column=0, columnspan=3, sticky='w')
        
        # these two buttons either plot using the input info, or close out of the software
        button_plot = tk.Button(self.root_wnd, text='Plot', width=10, command=self.call_mosaic_creator)
        button_close = tk.Button(self.root_wnd, text='Close', width=10, command=self.root_wnd.destroy)
        button_plot.grid(row=6, column=4, columnspan=1)
        button_close.grid(row=7, column=4, columnspan=1)
        
    def open_instructions(self):
        """ Displays an embedded pdf of the instruction manual """
        instruct_window = tk.Toplevel()
        instruct_window.geometry("700x780")
        instruct_window.title('Instruction Manual')
        
        v1 = pdfshow.ShowPdf()  # Create an object of Class ShowPdf
        
        # capture the image frame and also the image array to avoid garbage collection
        v2, self.save_pdf_imgs = v1.pdf_view(instruct_window, pdf_location="\\\\cam-vpnap-nas1\\nSpec\\Defect Viewer App\\v1.0\\defect_viewer_v1.0_tutorial.pdf", width=700, height=500)
        
        v2.pack(pady=10)  # Pack the PDF viewer in the GUI
    
    def call_mosaic_creator(self):
        """ Creates instance of MosaicCreator which initiates mosaic plotting """
        # check that all required fields are filled
        if self.ana_id.get() == 'Select Choice' or self.scan_id.get() == 'Select Choice' or not self.image_scale.get().isdigit():
            print('Please select a Scan ID, Analysis ID, and enter an integer for Image Scale before plotting')
        else:
            createmos.MosaicCreator(self)  # pass instance of Root to MosaicCreator

    def analysis_props(self):
        """ Displays analysis properties from currently selected analysis ID """
        if self.ana_id.get() == 'Select Choice':
            print('Please select an analysis ID first')
        else:    
            # connect to the database file
            conn = sqlite3.connect(self.db_file_entry.get())
            cur = conn.cursor()

            # sql query used to retrieve scan info
            sql_cmd_ana_prop = "SELECT * FROM AnalysisProperties WHERE AnalysisID = ?;"
            sql_cmd_analysis = "SELECT * FROM Analysis WHERE AnalysisID = ?;"
            sql_cmd_analyzer = "SELECT * FROM Analyzers;"

            ana_prop_info = np.array(cur.execute(sql_cmd_ana_prop, (str(self.ana_id.get()),)).fetchall())  # fetch all data from Analysis Properties table
            analysis_info = np.array(cur.execute(sql_cmd_analysis, (str(self.ana_id.get()),)).fetchall())  # fetch all data from Analysis table
            analyzer_info = np.array(cur.execute(sql_cmd_analyzer).fetchall())  # fetch all data from Analyzers table

            # create the properties window
            ana_prop_window = tk.Toplevel()
            ana_prop_window.title('Analysis Properties')

            # retrieve properties of interest
            analyzer_type = analyzer_info[np.where(analyzer_info[:, 0] == analysis_info[0][3])[0][0], 3]
            num_defects = analysis_info[0][10]

            prop_list = [analyzer_type, num_defects]  # place property variables into list

            output_labels = np.array(['Analyzer Type', 'Number of Defects'])  # property labels of interest in user-friendly form

            # create all labels and corresponding values
            for idx, label in enumerate(output_labels):
                tk.Label(ana_prop_window, text=f"{label:<30}").grid(row=2 * idx, column=0, columnspan=1, sticky='w')
                tk.Label(ana_prop_window, text=prop_list[idx]).grid(row=2 * idx, column=1, columnspan=1, sticky='w')
                ttk.Separator(ana_prop_window, orient='horizontal').grid(row=2 * idx + 1, column=0, columnspan=2, sticky='ew')

            # button to close window
            button_close = tk.Button(ana_prop_window, text='Close', width=10, command=ana_prop_window.destroy)
            button_close.grid(row=10, column=1, columnspan=1)

    def scan_props(self):
        """ Displays scan properties from currently selected scan ID """
        if self.scan_id.get() == 'Select Choice':
            print('Please select a scan ID first')
        else:    
            # connect to the database file
            conn = sqlite3.connect(self.db_file_entry.get())
            cur = conn.cursor()

            sql_cmd_scn_prop = "SELECT * FROM ScanProperties WHERE ScanID = ?;"  # sql query used to retrieve scan info
    
            scan_prop_info = np.array(cur.execute(sql_cmd_scn_prop, (str(self.scan_id.get()),)).fetchall())  # fetch all data from Scan Properties table

            # create the properties window
            scan_prop_window = tk.Toplevel()
            scan_prop_window.title('Scan Properties')
            
            # retrieve the properties of interest
            sample_id = scan_prop_info[np.where(scan_prop_info == "SampleID")[0][0], np.where(scan_prop_info == "SampleID")[1][0] + 1]
            lot_id = scan_prop_info[np.where(scan_prop_info == "LotID")[0][0], np.where(scan_prop_info == "LotID")[1][0] + 1]
            job_name = scan_prop_info[np.where(scan_prop_info == "JobName")[0][0], np.where(scan_prop_info == "JobName")[1][0] + 1]
            auto_focus_set = scan_prop_info[np.where(scan_prop_info == "Autofocus Set")[0][0], np.where(scan_prop_info == "Autofocus Set")[1][0] + 1]
            num_tiles = scan_prop_info[np.where(scan_prop_info == "Golden Tile Tiles per Device")[0][0], np.where(scan_prop_info == "Golden Tile Tiles per Device")[1][0] + 1]
            num_devices = scan_prop_info[np.where(scan_prop_info == "Golden Tile Number of Devices")[0][0], np.where(scan_prop_info == "Golden Tile Number of Devices")[1][0] + 1]
            scan_width_mic = scan_prop_info[np.where(scan_prop_info == "Scan Width Microns")[0][0], np.where(scan_prop_info == "Scan Width Microns")[1][0] + 1]
            scan_height_mic = scan_prop_info[np.where(scan_prop_info == "Scan Height Microns")[0][0], np.where(scan_prop_info == "Scan Height Microns")[1][0] + 1]
            die_width_mic = scan_prop_info[np.where(scan_prop_info == "DieWidth")[0][0], np.where(scan_prop_info == "DieWidth")[1][0] + 1]
            die_height_mic = scan_prop_info[np.where(scan_prop_info == "DieHeight")[0][0], np.where(scan_prop_info == "DieHeight")[1][0] + 1]

            # place property variables into list
            prop_list = [sample_id, lot_id, job_name, auto_focus_set, num_tiles, num_devices, scan_width_mic,
                        scan_height_mic, die_width_mic, die_height_mic]
            
            # property labels of interest in user-friendly form
            output_labels = np.array(['Sample ID', 'Lot ID', 'Job Name', 'Autofocus Set', 'Tiles per Device',
                                   'Number of Devices', 'Scan Width (Microns)', 'Scan Height (Microns)',
                                   'Die Width (Microns)', 'Die Height (Microns)'])
            
            # create all labels and corresponding values
            for idx, label in enumerate(output_labels):
                tk.Label(scan_prop_window, text=f"{label:<30}").grid(row=2 * idx, column=0, columnspan=1, sticky='w')
                tk.Label(scan_prop_window, text=prop_list[idx]).grid(row=2 * idx, column=1, columnspan=1, sticky='w')
                ttk.Separator(scan_prop_window, orient='horizontal').grid(row=2 * idx + 1, column=0, columnspan=2, sticky='ew')

            # button to close window
            button_close = tk.Button(scan_prop_window, text='Close', width=10, command=scan_prop_window.destroy)
            button_close.grid(row=2 * len(output_labels) + 1, column=1, columnspan=1)
    
    def set_paths(self):
        """ Sets the currently input database and image directory paths
            Updates the scan dropdown menu according to database file contents """
        
        # update scan and analysis ID input variables to default values
        self.ana_id.set('Select Choice')
        self.scan_id.set('Select Choice')
        
        # ensure the analysis and scan ID option menus are cleared
        self.ana_id_select["menu"].delete(0, "end")
        scan_menu = self.scan_id_select["menu"]
        scan_menu.delete(0, "end")
        
        # check validity of inputs
        if self.scan_dir_entry.get() == '' or self.db_file_entry.get() == '':
            print('Please fill out filepath fields first')
            return
        if not any(x.startswith('Scan_') for x in os.listdir(self.scan_dir_entry.get() + '/')):
            print('Scans Directory must contain image folders with naming convention \'Scan_XXX\'')
            return
        if self.db_file_entry.get().split('.db')[0].split('/')[-1] != self.scan_dir_entry.get().split('/')[-1]:
            print('WARNING: Scans Directory and Database File names do not match one another')
            print('Consider reviewing selections before proceeding, or error may occur')
        
        # connect to the currently selected database file
        conn = sqlite3.connect(self.db_file_entry.get())
        cur = conn.cursor()

        # sql queries used to retrieve scan info
        sql_cmd_scn = "SELECT * FROM Scans;"
        sql_cmd_scn_prop = "SELECT * FROM ScanProperties"

        scans_info = np.array(cur.execute(sql_cmd_scn).fetchall())  # fetch all data from Scans table
        scan_prop_info = np.array(cur.execute(sql_cmd_scn_prop).fetchall())  # fetch all data from Scan Properties table
        
        # get all of the scan IDs
        self.scan_options = scans_info[:,0]
        
        # update the scan ID option menu with choices
        for string in self.scan_options:
            scan_menu.add_command(label=string, command=lambda value=string: self.scan_id.set(value))
        
    def scan_select(self, *args):
        """ Updates the analysis option menu when scan is selected from its dropdown """
        self.ana_id.set('Select Choice')  # update analysis input variable to default
        # disable running any functionality when Scan ID has not been selected yet 
        if self.scan_id.get() != 'Select Choice':
            # set the location of the folder containing the scanned images for the chosen Scan ID
            scans_directory = self.scan_dir_entry.get() + '/'
            self.img_loc = scans_directory + 'Scan_' + f"{int(self.scan_id.get()):03d}"
            
            # connect to the currently selected database file
            conn = sqlite3.connect(self.db_file_entry.get())
            cur = conn.cursor()

            sql_cmd_anly = "SELECT * FROM Analysis"  # sql queries used to retrieve analysis info

            analysis_info = np.array(cur.execute(sql_cmd_anly).fetchall())  # fetch all data from Analysis table

            self.analysis_options = (analysis_info[analysis_info[:, 4] == self.scan_id.get()])[:, 0]  # filter list for Analysis IDs corresponding to the chosen Scan ID

            # update the analysis ID option menu with choices
            menu = self.ana_id_select["menu"]
            menu.delete(0, "end")
            for string in self.analysis_options:
                menu.add_command(label=string, command=lambda value=string: self.ana_id.set(value))
        
    def browse_file(self):
        """ Opens file explorer for file selection """       
        filename = filedialog.askopenfilename(filetypes=(("db files", "*.db"),))
        self.db_file_entry.delete(0, 'end')
        self.db_file_entry.insert(tk.END, filename) 
    
    def browse_directory(self):
        """ Opens file explorer for scans folder selection """     
        directory_name = filedialog.askdirectory()
        self.scan_dir_entry.delete(0, 'end')
        self.scan_dir_entry.insert(tk.END, directory_name)