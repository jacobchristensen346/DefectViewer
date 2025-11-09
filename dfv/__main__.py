""" 
Defect Viewer App
-----------------

A Python app for viewing scanned images and associated defects
from the Nanotronics nSpec tool

Provides a GUI powered by tk for a convenient experience to non-coders

Package is intended to be run as a program from the command line:
    
    $ python -m dfv
    
This will automatically run the root GUI window

If running directly in Python interpreter, users may import the root module:
    
    >>> from dfv import root
    >>> root.Root.root_wnd.mainloop()

This will activate the root GUI window

For distribution and convenience purposes, the package 
may be converted into an executable via pyinstaller:
    
    $ pyinstaller dfv/__main__.py
    
Or, to package all dependencies into a single file...
    
    $ pyinstaller --onefile dfv/__main__.py
    
Generally, individual modules are for utility purposes and not 
meant to be independently imported for use
"""

from dfv import root

def main():
    print("Starting new defect viewer GUI")
    root_obj = root.Root()
    root_obj.root_wnd.mainloop()

if __name__ == "__main__":
    main()
