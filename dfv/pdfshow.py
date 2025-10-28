# Show Pdf imports
from threading import Thread
import fitz
import tkinter as tk
from tkinter import ttk

class ShowPdf():
    """ Imports PDF as scrollable image into tkinter  
    
    Summary of changes made by jacobchristensen346 to tkPDFViewer (https://github.com/Roshanpaswan/tkPDFViewer.git) 

    - Added __init__ function to ShowPdf class, moved img_object_li instance variable into __init__ function. This aids in garbage-collection avoidance upon reruns of code.
    - Added explicit anchor argument to self.display_msg = Label(master, textvariable=percentage_load)
    - Added new variable returned upon exit of pdf_view() function (self.img_object_li). This allows capture of image array which aids in garbage collection avoidance.

    """
    def __init__(self):
        self.img_object_li = []

    def pdf_view(self, master, width=1200, height=600, pdf_location="", bar=True, load="after"):

        self.frame = tk.Frame(master, width=width, height=height, bg="white")

        scroll_y = tk.Scrollbar(self.frame, orient="vertical")
        scroll_x = tk.Scrollbar(self.frame, orient="horizontal")

        scroll_x.pack(fill="x", side="bottom")
        scroll_y.pack(fill="y", side="right")

        percentage_view = 0
        percentage_load = tk.StringVar()

        if bar == True and load == "after":
            self.display_msg = tk.Label(master, textvariable=percentage_load)
            self.display_msg.pack(pady=10)

            loading = ttk.Progressbar(self.frame, orient=tk.HORIZONTAL, length=100, mode='determinate')
            loading.pack(side=tk.TOP, fill=tk.X)

        self.text = tk.Text(self.frame, yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set, width=width, height=height)
        self.text.pack(side="left")

        scroll_x.config(command=self.text.xview)
        scroll_y.config(command=self.text.yview)

        def add_img():
            precentage_dicide = 0
            open_pdf = fitz.open(pdf_location)

            for page in open_pdf:
                pix = page.get_pixmap()
                pix1 = fitz.Pixmap(pix, 0) if pix.alpha else pix
                img = pix1.tobytes("ppm")
                timg = ImageTk.PhotoImage(data=img)
                self.img_object_li.append(timg)
                if bar == True and load == "after":
                    precentage_dicide = precentage_dicide + 1
                    percentage_view = (float(precentage_dicide) / float(len(open_pdf)) * float(100))
                    loading['value'] = percentage_view
                    percentage_load.set(f"Please wait, the instruction manual is loading... {int(math.floor(percentage_view))}%")
            if bar == True and load == "after":
                loading.pack_forget()
                self.display_msg.pack_forget()

            for i in self.img_object_li:
                self.text.image_create(tk.END, image=i)
                self.text.insert(tk.END, "\n\n")
            self.text.configure(state="disabled")


        def start_pack():
            t1 = Thread(target=add_img)
            t1.start()

        if load == "after":
            master.after(250, start_pack)
        else:
            start_pack()
       
        return self.frame, self.img_object_li