# -*- coding: utf-8 -*-
"""
Created on Thu Nov 14 15:21:19 2013
Main Widget for entering filter specifications

@author: beike, Christian Münker
"""
from __future__ import print_function, division, unicode_literals
import sys, os 
import numpy as np
from PyQt4 import QtGui
"""
Subwidget for entering filter type and parameter
"""


# import databroker from one level above if this file is run as __main__
# for test purposes
if __name__ == "__main__": 
    __cwd__ = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(__cwd__ + '/..')

import filterbroker as fb
from FilterFileReader import FilterFileReader
    
import input_filter, input_order, input_units
from plotWidgets import plot_all


class InputParams(QtGui.QWidget):
    
    def __init__(self, DEBUG = True):
        super(InputParams, self).__init__() 
#        self.setStyleSheet("margin:5px; border:1px solid rgb(0, 0, 0); ")
#        self.setStyleSheet("background-color: rgb(255,0,0); margin:5px; border:1px solid rgb(0, 255, 0); ")

        self.DEBUG = DEBUG  
        self.ffr = FilterFileReader('Init.txt', 'filterDesign', 
                                    commentChar = '#', DEBUG = DEBUG) #                                             
        self.initUI()
      
    def initUI(self): 
        """
        Create all widgets:

        sf : Select Filter with response type rt (LP, ...), 
              filter type ft (IIR, ...), and design method dm (cheby1, ...)
        fo : Filter Order (numeric or 'min')
        fspec : Frequency Specifications 
        ms : Magnitude Specifications with the subwidgets
            txt : only text field for comments / instruction
            val : infostring (title), Label, value
            unt : unit, label, value

        """ 

        self.sf = input_filter.SelectFilter(DEBUG = True)
        self.fo = input_order.InputOrder(DEBUG = True)
        # subwidget for Frequency Specs
        self.fspec = input_units.InputUnits(title = "Frequency Specifications",
                    units = ["Hz", "Normalize 0 to 1", "kHz", "MHz", "GHz"],
                    labels = ['f_S', 'F_pb', 'F_sb'],
                    DEBUG = False)
        # subwidget for Amplitude Specs        
        self.aspec = input_units.InputUnits(title = "Amplitude Specifications",
                    units = ["dB","Squared"], labels = ["A_pb","A_sb"],
                    DEBUG = False)
        # subwidget for Weight Specs                                           
        self.wspec = input_units.InputUnits(
                    title = "Weight Specifications",
                    units = "", labels = ["W_pb","W_sb"],
                    DEBUG = False)
        
        self.msg = QtGui.QLabel(self)
        self.msg.setText("Enter a weight value for each band below")
        self.msg.setWordWrap(True)

        self.msg.setVisible(True)
        self.wspec.setVisible(True)
        self.aspec.setVisible(True)
        
        self.butDesignFilt = QtGui.QPushButton("DESIGN FILTER", self)
        self.pltAll = plot_all.plotAll() # instantiate tabbed plot widgets 
        """
        LAYOUT      
        """
        self.layout=QtGui.QGridLayout()
        self.layout.addWidget(self.sf,0,0,1,2)  # Design method (IIR - ellip, ...)
        self.layout.addWidget(self.fo,1,0,1,2)  # Filter order
        self.layout.addWidget(self.fspec,2,0,1,2)  # Freq. specifications
        self.layout.addWidget(self.msg,3,0,1,2)  # Text message
        self.layout.addWidget(self.aspec,4,0)   # Amplitude specs
        self.layout.addWidget(self.wspec,4,1)   # Weight specs

        mainLayout = QtGui.QVBoxLayout(self)
        mainLayout.addLayout(self.layout)
        mainLayout.addStretch()
        mainLayout.addWidget(self.butDesignFilt, )   # Design Filter!
        self.setLayout(mainLayout)
        #----------------------------------------------------------------------
        # SIGNALS & SLOTS
        # Call chooseDesignMethod every time filter selection is changed: 
        self.fo.chkMin.clicked.connect(self.chooseDesignMethod)
        self.sf.comboResponseType.activated.connect(self.chooseDesignMethod)
        self.sf.comboFilterType.activated.connect(self.chooseDesignMethod)
        self.sf.comboDesignMethod.activated.connect(self.chooseDesignMethod)
        self.fo.chkMin.clicked.connect(self.chooseDesignMethod)
        self.butDesignFilt.clicked.connect(self.startDesignFilt)   

        self.chooseDesignMethod() # first time initialization
        
    def chooseDesignMethod(self):
        """
        Reads:  fb.gD['selFilter'] (currently selected filter), extracting info
                from fb.gD['filterTree']
        Writes:
        Depending on SelectFilter and frequency specs, the values of the 
        widgets fo, fspec are recreated. For widget ms, the visibility is changed
        as well.
        """

        # Read freq / amp / weight labels for current filter design
        rt = fb.gD['selFilter']['rt']
        ft = fb.gD['selFilter']['ft']
        dm = fb.gD['selFilter']['dm']
        fo = fb.gD['selFilter']['fo']  
        myParams = fb.gD['filterTree'][rt][ft][dm][fo]['par']
        myEnbWdg = fb.gD['filterTree'][rt][ft][dm][fo]['enb'] # enabled widgets

        # build separate parameter lists according to the first letter
        self.freqParams = [l for l in myParams if l[0] == 'F']
        self.ampParams = [l for l in myParams if l[0] == 'A']
        self.weightParams = [l for l in myParams if l[0] == 'W']
        if self.DEBUG:
            print("=== InputParams.chooseDesignMethod ===")
            print("selFilter:", fb.gD['selFilter'])
            print('myLabels:', myParams)
            print('ampLabels:', self.ampParams)
            print('freqLabels:', self.freqParams)
            print('weightLabels:', self.weightParams)

        # pass new labels to widgets
        # set invisible widgets if param list is empty
        self.fo.update()
        self.fspec.setElements(newLabels = self.freqParams) # update frequency spec labels
        self.aspec.setVisible(self.ampParams != [])
        self.aspec.setEnabled("aspec" in myEnbWdg)
        self.aspec.setElements(newLabels = self.ampParams)
        self.wspec.setVisible(self.weightParams != []) 
        self.wspec.setEnabled("wspec" in myEnbWdg)
        self.wspec.setElements(newLabels = self.weightParams)
            
    def writeAll(self):
        """
        Update global dict fb.gD['selFilter'] with currently selected filter 
        parameters, using the update methods of the classes
        """
        # collect data from widgets and write to fb.gD['selFilter']
        self.fo.update()    # filter order widget
        self.fspec.update() # frequency specification widget
        self.aspec.update() # magnitude specs with unit
        self.wspec.update() # weight specification  
            
        if self.DEBUG: print(fb.gD['selFilter'])
  
    def startDesignFilt(self):
        """
        Design Filter
        """
        self.writeAll() # input widgets -> fb.gD['selFilter'] 
        if self.DEBUG:
            print("--- pyFDA.py : startDesignFilter ---")
            print('Specs:', fb.gD['selFilter'])#params)
            print("fb.gD['selFilter']['dm']", fb.gD['selFilter']['dm']+"."+
                  fb.gD['selFilter']['rt']+fb.gD['selFilter']['fo'])
        # create filter object instance from design method (e.g. 'cheby1'):   
        self.myFilter = self.ffr.objectWizzard(fb.gD['selFilter']['dm'])
        # Now construct the instance method from the response type (e.g.
        # 'LP' -> cheby1.LP) and
        # design the filter by passing current specs to the method:
        getattr(self.myFilter, fb.gD['selFilter']['rt'] +
                                fb.gD['selFilter']['fo'])(fb.gD['selFilter'])
        self.fo.update()
        self.wspec.updateElements()
        
        # Read back filter coefficients and (zeroes, poles, k):
        fb.gD['zpk'] = self.myFilter.zpk # (zeroes, poles, k)
        if np.ndim(self.myFilter.coeffs) == 1:  # FIR filter: only b coeffs
            fb.gD['coeffs'] = (self.myFilter.coeffs, [1]) # add dummy a = [1]
            # This still has ndim == 1? 
        else:                                   # IIR filter: [b, a] coeffs
            fb.gD['coeffs'] = self.myFilter.coeffs 
        if self.DEBUG:
            print("=== pyFDA.py : startDesignFilter ===")
            print("zpk:" , fb.gD['zpk'])
            print('ndim gD:', np.ndim(fb.gD['coeffs']))
            print("b,a = ", fb.gD['coeffs'])
     
#        self.pltAll.update() is executed from pyFDA.py!
  
#------------------------------------------------------------------------------ 
   
if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    form = InputParams()
    form.show()
    form.writeAll()
   
    app.exec_()


   
        



 