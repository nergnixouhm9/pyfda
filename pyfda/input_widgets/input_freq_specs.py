# -*- coding: utf-8 -*-
"""
Widget for entering frequency specifications

Author: Christian Münker
"""
from __future__ import print_function, division, unicode_literals, absolute_import
import sys
import logging
logger = logging.getLogger(__name__)

from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import pyqtSignal, QEvent

import pyfda.filterbroker as fb
from pyfda.pyfda_lib import rt_label
from pyfda.pyfda_rc import params # FMT string for QLineEdit fields, e.g. '{:.3g}'
from pyfda.simpleeval import simple_eval

class InputFreqSpecs(QtGui.QWidget):
    """
    Build and update widget for entering the frequency
    specifications like F_sb, F_pb etc.
    """

    # class variables (shared between instances if more than one exists)
    sigSpecsChanged = pyqtSignal() # emitted when filter has been changed

    def __init__(self, parent, title = "Frequency Specs"):

        super(InputFreqSpecs, self).__init__(parent)
        self.title = title

        self.qlabels = []    # list with references to QLabel widgets
        self.qlineedit = []  # list with references to QLineEdit widgets
        
        self.new_labels = [] # list with actual labels

        self.spec_edited = False # flag whether QLineEdit field has been edited

        self._construct_UI()

#-------------------------------------------------------------
    def _construct_UI(self):
        """
        Construct the User Interface
        """
        self.layVMain = QtGui.QVBoxLayout() # Widget main layout

        bfont = QtGui.QFont()
        bfont.setBold(True)
#            bfont.setWeight(75)
        self.lblTitle = QtGui.QLabel(self) # field for widget title
        self.lblTitle.setText(str(self.title))
        self.lblTitle.setFont(bfont)
        self.lblTitle.setWordWrap(True)
        self.layVMain.addWidget(self.lblTitle)
        
        # Create a gridLayout consisting of QLabel and QLineEdit fields
        # for the frequency specs:
        self.layGSpecs = QtGui.QGridLayout() # sublayout for spec fields        

        sfFrame = QtGui.QFrame()
        sfFrame.setFrameStyle(QtGui.QFrame.StyledPanel|QtGui.QFrame.Sunken)
        sfFrame.setLayout(self.layGSpecs)

        self.layVMain.addWidget(sfFrame)
        self.layVMain.setContentsMargins(1,1,1,1)
        self.setLayout(self.layVMain)
        
        self.n_cur_labels = 0 # number of currently visible labels / qlineedits        

        #----------------------------------------------------------------------
        # EVENT FILTER
        #----------------------------------------------------------------------
        # DYNAMIC SIGNAL SLOT CONNECTION:
        # Every time a field is edited, call self.store_entries 
        # This is achieved by dynamically installing and
        # removing event filters when creating / deleting subwidgets.
        # The event filter monitors the focus of the input fields.
        #----------------------------------------------------------------------
#------------------------------------------------------------------------------

    def eventFilter(self, source, event):
        """
        Filter all events generated by the QLineEdit widgets. Source and type
        of all events generated by monitored objects are passed to this eventFilter,
        evaluated and passed on to the next hierarchy level.

        - When a QLineEdit widget gains input focus (QEvent.FocusIn`), display
          the stored value from filter dict with full precision
        - When a key is pressed inside the text field, set the `spec_edited` flag
          to True.
        - When a QLineEdit widget loses input focus (QEvent.FocusOut`), store
          current value normalized to f_S with full precision (only if
          `spec_edited`== True) and display the stored value in selected format
        """
        if isinstance(source, QtGui.QLineEdit): # could be extended for other widgets
            if event.type() == QEvent.FocusIn:
                self.spec_edited = False
                self.load_entries()
            elif event.type() == QEvent.KeyPress:
                self.spec_edited = True # entry has been changed
                key = event.key()
                if key in {QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter}:
                    self._store_entry(source)
                elif key == QtCore.Qt.Key_Escape: # revert changes
                    self.spec_edited = False                    
                    self.load_entries()
                
            elif event.type() == QEvent.FocusOut:
                self._store_entry(source)
        # Call base class method to continue normal event processing:
        return super(InputFreqSpecs, self).eventFilter(source, event)


#------------------------------------------------------------------------------
    def _store_entry(self, event_source):
        """
        _store_entry is triggered by `QEvent.focusOut` in the eventFilter:        
        When the textfield of `widget` has been edited (`self.spec_edited` =  True),
        sort and store all entries in filter dict, then reload the text fields. 
        Finally, emit a SpecsChanged signal.
        """
        if self.spec_edited:
            f_label = str(event_source.objectName())
            f_value = simple_eval(event_source.text()) / fb.fil[0]['f_S']
            fb.fil[0].update({f_label:f_value})
            self.sort_dict_freqs()
            self.sigSpecsChanged.emit() # -> input_specs
            self.spec_edited = False # reset flag

#-------------------------------------------------------------
    def update_UI(self, new_labels = []):
        """
        Set labels and get corresponding values from filter dictionary.
        When number of entries has changed, the layout of subwidget is rebuilt,
        using

        - `self.qlabels`, a list with references to existing QLabel widgets,
        - `new_labels`, a list of strings from the filter_dict for the current
          filter design
        - 'num_new_labels`, their number
        - `self.n_cur_labels`, the number of currently visible labels / qlineedit
          fields
        """
        self.new_labels = new_labels
        num_new_labels = len(new_labels)
        if num_new_labels < self.n_cur_labels: # less new labels/qlineedit fields than before
            self._hide_entries(num_new_labels)

        elif num_new_labels > self.n_cur_labels: # more new labels, create / show new ones
            self._show_entries(num_new_labels)

        #---------------------------- logging -----------------------------
        logger.debug("update_UI: {0}-{1}-{2}".format(
                            fb.fil[0]["rt"],fb.fil[0]["dm"],fb.fil[0]["fo"]))

        for i in range(num_new_labels):
            # Update ALL labels and corresponding values 
            self.qlabels[i].setText(rt_label(new_labels[i]))

            self.qlineedit[i].setText(str(fb.fil[0][new_labels[i]]))
            self.qlineedit[i].setObjectName(new_labels[i])  # update ID

        self.n_cur_labels = num_new_labels # update number of currently visible labels
        self.sort_dict_freqs() # sort frequency entries in dictionary and update display


#-------------------------------------------------------------        
    def load_entries(self):
        """
        Reload textfields from filter dictionary 
        Transform the displayed frequency spec input fields according to the units
        setting (i.e. f_S). Spec entries are always stored normalized w.r.t. f_S 
        in the dictionary; when f_S or the unit are changed, only the displayed values
        of the frequency entries are updated, not the dictionary!

        load_entries is called during init and when the frequency unit or the
        sampling frequency have been changed.

        It should be called when sigSpecsChanged or sigFilterDesigned is emitted
        at another place, indicating that a reload is required.
        """

        # recalculate displayed freq spec values for (maybe) changed f_S
        logger.debug("exec load_entries")
        for i in range(len(self.qlineedit)):
            f_label = str(self.qlineedit[i].objectName())
            f_value = fb.fil[0][f_label] * fb.fil[0]['f_S']

            if not self.qlineedit[i].hasFocus():
                # widget has no focus, round the display
                self.qlineedit[i].setText(params['FMT'].format(f_value))
            else:
                # widget has focus, show full precision
                self.qlineedit[i].setText(str(f_value))


#-------------------------------------------------------------
    def _hide_entries(self, num_new_labels):
        """
        Hide subwidgets so that only `num_new_labels` subwidgets are visible
        """
        for i in range (num_new_labels, len(self.qlabels)):
            self.qlabels[i].hide()
            self.qlineedit[i].hide()

#------------------------------------------------------------------------
    def _show_entries(self, num_new_labels):
        """
        - check whether enough subwidgets (QLabel und QLineEdit) exist for the 
          the required number of `num_new_labels`: 
              - create new ones if required 
              - initialize them with dummy information
              - install eventFilter for new QLineEdit widgets so that the filter 
                  dict is updated automatically when a QLineEdit field has been 
                  edited.
        - if enough subwidgets exist already, make enough of them visible to
          show all spec fields
        """
        num_tot_labels = len(self.qlabels) # number of existing labels (vis. + invis.)

        if num_tot_labels < num_new_labels: # new widgets need to be generated
            for i in range(num_tot_labels, num_new_labels):                   
                self.qlabels.append(QtGui.QLabel(self))
                self.qlabels[i].setText(rt_label("dummy"))
    
                self.qlineedit.append(QtGui.QLineEdit(""))
                self.qlineedit[i].setObjectName("dummy")
                self.qlineedit[i].installEventFilter(self)  # filter events
    
                self.layGSpecs.addWidget(self.qlabels[i],(i+2),0)
                self.layGSpecs.addWidget(self.qlineedit[i],(i+2),1)

        else: # make the right number of widgets visible
            for i in range(self.n_cur_labels, num_new_labels):
                self.qlabels[i].show()
                self.qlineedit[i].show()


#------------------------------------------------------------------------------
    def sort_dict_freqs(self):
        """
        - Sort filter dict frequency spec entries with ascending frequency if 
        - Update the QLineEdit frequency widgets

        The method is called when:
        - update_UI has been called after changing the filter design algorithm                                # that the response type has been changed 
          eg. from LP -> HP, requiring a different order of frequency entries
        - a frequency spec field has been edited
        - the sort button has been clicked (from input_specs.py)
        """
        
        if fb.fil[0]['freq_specs_sort']:
            fSpecs = [fb.fil[0][str(self.qlineedit[i].objectName())]
                                            for i in range(len(self.qlineedit))]
            fSpecs.sort()
            
            for i in range(len(self.qlineedit)):
                fb.fil[0][str(self.qlineedit[i].objectName())] = fSpecs[i]
                
        self.load_entries()


#------------------------------------------------------------------------------

if __name__ == '__main__':

    app = QtGui.QApplication(sys.argv)
    mainw = InputFreqSpecs(None)

    mainw.update_UI(new_labels = ['F_SB','F_SB2','F_PB','F_PB2'])
#    mainw.update_UI(new_labels = ['F_PB','F_PB2'])

    app.setActiveWindow(mainw) 
    mainw.show()
    sys.exit(app.exec_())
