import os
import sys

from pyzolib.path import Path
from pyzolib import ssdf
from . import QtCore, QtGui

import iep
from iep import translate

from .tree import Tree
from . import proxies


class Browser(QtGui.QWidget):
    """ A browser consists of an address bar, and tree view, and other
    widets to help browse the file system. The browser object is responsible
    for tying the different browser-components together.
    
    It is also provides the API for dealing with starred dirs.
    """
    
    def __init__(self, parent, config, path=None):
        QtGui.QWidget.__init__(self, parent)
        
        # Store config
        self.config = config
        
        # Create star button
        self._projects = Projects(self)
        
        # Create path input/display lineEdit
        self._pathEdit = PathInput(self)
        
        # Create file system proxy
        self._fsProxy = proxies.NativeFSProxy()
        self.destroyed.connect(self._fsProxy.stop)
        
        # Create tree widget
        self._tree = Tree(self)
        self._tree.setPath(Path(self.config.path))
        
        # Create name filter
        self._nameFilter = NameFilter(self)
        #self._nameFilter.lineEdit().setToolTip('File filter pattern')  
        self._nameFilter.setToolTip(translate('filebrowser', 'Filename filter'))  
        self._nameFilter.setPlaceholderText(self._nameFilter.toolTip())
        
        # Create search filter
        self._searchFilter = SearchFilter(self)
        self._searchFilter.setToolTip(translate('filebrowser', 'Search in files'))
        self._searchFilter.setPlaceholderText(self._searchFilter.toolTip())
        
        # Signals to sync path. 
        # Widgets that can change the path transmit signal to _tree
        self._pathEdit.dirUp.connect(self._tree.setFocus)
        self._pathEdit.dirUp.connect(self._tree.setPathUp)
        self._pathEdit.dirChanged.connect(self._tree.setPath)
        self._projects.dirChanged.connect(self._tree.setPath)
        #
        self._nameFilter.filterChanged.connect(self._tree.onChanged) # == update
        self._searchFilter.filterChanged.connect(self._tree.onChanged)
        # The tree transmits signals to widgets that need to know the path
        self._tree.dirChanged.connect(self._pathEdit.setPath)
        self._tree.dirChanged.connect(self._projects.setPath)
        
        self._layout()
        
        # Set and sync path ...
        if path is not None:
            self._tree.SetPath(path)
        self._tree.dirChanged.emit(self._tree.path())
    
    
    def _layout(self):
        layout = QtGui.QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        #layout.setSpacing(6)
        self.setLayout(layout)
        #        
        layout.addWidget(self._projects)
        layout.addWidget(self._pathEdit)
        layout.addWidget(self._tree)
        #
        subLayout = QtGui.QHBoxLayout()
        subLayout.setSpacing(2)
        subLayout.addWidget(self._nameFilter, 5)
        subLayout.addWidget(self._searchFilter, 5)
        layout.addLayout(subLayout)
    
    def closeEvent(self, event):
        #print('Closing browser, stopping file system proxy')
        super().closeEvent(event)
        self._fsProxy.stop()
    
    def nameFilter(self):
        #return self._nameFilter.lineEdit().text()
        return self._nameFilter.text()
    
    def searchFilter(self):
        return {'pattern': self._searchFilter.text(),
                'matchCase': self.config.searchMatchCase,
                'regExp': self.config.searchRegExp,
                'subDirs': self.config.searchSubDirs,
                }
    
    @property
    def expandedDirs(self):
        """ The list of the expanded directories. 
        """
        return self.parent().config.expandedDirs
    
    @property
    def starredDirs(self):
        """ A list of the starred directories.
        """
        return [d.path for d in self.parent().config.starredDirs]
    
    def dictForStarredDir(self, path):
        """ Return the dict of the starred dir corresponding to
        the given path, or None if no starred dir was found.
        """
        if not path:
            return None
        for d in self.parent().config.starredDirs:
            if d['path'] == path:
                return d
        else:
            return None
    
    def addStarredDir(self, path):
        """ Add the given path to the starred directories.
        """
        # Create new dict
        newProject = ssdf.new()
        newProject.path = path.normcase() # Normalize case!
        newProject.name = path.basename
        newProject.addToPythonpath = False
        # Add it to the config
        self.parent().config.starredDirs.append(newProject)
        # Update list
        self._projects.updateProjectList()
    
    def removeStarredDir(self, path):
        """ Remove the given path from the starred directories.
        The path must exactlty match.
        """
        # Remove
        starredDirs = self.parent().config.starredDirs
        pathn = path.normcase()
        for d in starredDirs:
            if pathn == d.path:
                starredDirs.remove(d)
        # Update list
        self._projects.updateProjectList()
    
    def test(self, sort=False):
        items = []
        for i in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(i)
            items.append(item)
            #self._tree.removeItemWidget(item, 0)
        self._tree.clear()
        
        #items.sort(key=lambda x: x._path)
        items = [item for item in reversed(items)]
        
        for item in items:
            self._tree.addTopLevelItem(item)
    
    def currentProject(self):
        """ Return the ssdf dict for the current project, or None.
        """
        return self._projects.currentDict()


class LineEditWithToolButtons(QtGui.QLineEdit):
    """ Line edit to which tool buttons (with icons) can be attached.
    """
    
    def __init__(self, parent):
        QtGui.QLineEdit.__init__(self, parent)
        self._leftButtons = []
        self._rightButtons = []
    
    def addButtonLeft(self, icon, willHaveMenu=False):
        return self._addButton(icon, willHaveMenu, self._leftButtons)
    
    def addButtonRight(self, icon, willHaveMenu=False):
        return self._addButton(icon, willHaveMenu, self._rightButtons)
    
    def _addButton(self, icon, willHaveMenu, L):
        # Create button
        button = QtGui.QToolButton(self)
        L.append(button)
        # Customize appearance
        button.setIcon(icon)
        button.setIconSize(QtCore.QSize(16,16))
        button.setStyleSheet("QToolButton { border: none; padding: 0px; }")        
        #button.setStyleSheet("QToolButton { border: none; padding: 0px; background-color:red;}");
        # Set behavior
        button.setCursor(QtCore.Qt.ArrowCursor)
        button.setPopupMode(button.InstantPopup)
        # Customize alignment
        if willHaveMenu:
            button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
            if sys.platform.startswith('win'):
                button.setText(' ')
        # Update self
        self._updateGeometry()
        return button
    
    def setButtonVisible(self, button, visible):
        for but in self._leftButtons:
            if but is button:
                but.setVisible(visible)
        for but in self._rightButtons:
            if but is button:
                but.setVisible(visible)
        self._updateGeometry()
    
    def resizeEvent(self, event):
        QtGui.QLineEdit.resizeEvent(self, event)
        self._updateGeometry(True)
    
    def showEvent(self, event):
        QtGui.QLineEdit.showEvent(self, event)
        self._updateGeometry()
    
    def _updateGeometry(self, light=False):
        if not self.isVisible():
            return
        
        # Init
        rect = self.rect()
        
        # Determine padding and height
        paddingLeft, paddingRight, height = 1, 1, 0
        #
        for but in self._leftButtons:
            if but.isVisible():
                sz = but.sizeHint()
                height = max(height, sz.height())
                but.move(   1+paddingLeft,
                            (rect.bottom() + 1 - sz.height())/2 )
                paddingLeft += sz.width() + 1
        #
        for but in self._rightButtons:
            if but.isVisible():
                sz = but.sizeHint()
                paddingRight += sz.width() + 1
                height = max(height, sz.height())
                but.move(   rect.right()-1-paddingRight, 
                            (rect.bottom() + 1 - sz.height())/2 )
        
        # Set padding
        ss = "QLineEdit { padding-left: %ipx; padding-right: %ipx} "
        self.setStyleSheet( ss % (paddingLeft, paddingRight) );
        
        # Set minimum size
        if not light:
            fw = QtGui.qApp.style().pixelMetric(QtGui.QStyle.PM_DefaultFrameWidth)
            msz = self.minimumSizeHint()
            w = max(msz.width(), paddingLeft + paddingRight + 10)
            h = max(msz.height(), height + fw*2 + 2)
            self.setMinimumSize(w,h)



class PathInput(LineEditWithToolButtons):
    """ Line edit for selecting a path.
    """
    
    dirChanged = QtCore.Signal(Path)  # Emitted when the user changes the path (and is valid)
    dirUp = QtCore.Signal()  # Emitted when user presses the up button
    
    def __init__(self, parent):
        LineEditWithToolButtons.__init__(self, parent)
        
        # Create up button
        self._upBut = self.addButtonLeft(iep.icons.folder_parent)
        self._upBut.clicked.connect(self.dirUp)
        
        # To receive focus events
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        
        # Set completion mode
        self.setCompleter(QtGui.QCompleter())
        c = self.completer()
        c.setCompletionMode(c.InlineCompletion)
        
        # Set dir model to completer
        dirModel = QtGui.QDirModel(c)
        dirModel.setFilter(QtCore.QDir.Dirs | QtCore.QDir.NoDotAndDotDot)
        c.setModel(dirModel)
        
        # Connect signals
        #c.activated.connect(self.onActivated)
        self.textEdited.connect(self.onTextEdited)
        #self.textChanged.connect(self.onTextEdited)
        #self.cursorPositionChanged.connect(self.onTextEdited)
    
    
    def setPath(self, path):
        """ Set the path to display. Does nothing if this widget has focus.
        """
        if not self.hasFocus():
            self.setText(path)
            self.checkValid() # Reset style if it was invalid first
    
    
    def checkValid(self):
        # todo: This kind of violates the abstraction of the file system
        # ok for now, but we should find a different approach someday
        # Check
        text = self.text()
        dir = Path(text)
        isvalid = text and dir.isdir and os.path.isabs(dir)
        # Apply styling
        ss = self.styleSheet().replace('font-style:italic; ', '')
        if not isvalid:
            ss = ss.replace('QLineEdit {', 'QLineEdit {font-style:italic; ')
        self.setStyleSheet(ss)
        # Return
        return isvalid
    
    
    def event(self, event):
        # Capture key events to explicitly apply the completion and
        # invoke checking whether the current text is a valid directory.
        # Test if QtGui is not None (can happen when reloading tools)
        if QtGui and isinstance(event, QtGui.QKeyEvent):
            qt = QtCore.Qt
            if event.key() in [qt.Key_Tab, qt.Key_Enter, qt.Key_Return]:
                self.setText(self.text()) # Apply completion
                self.onTextEdited() # Check if this is a valid dir
                return True
        return super().event(event)
    
    
    def onTextEdited(self, dummy=None):
        text = self.text()
        if self.checkValid():            
            self.dirChanged.emit(Path(text))
    
    
    def focusOutEvent(self, event=None):
        """ focusOutEvent(event)
        On focusing out, make sure that the set path is correct.
        """
        if event is not None:
            QtGui.QLineEdit.focusOutEvent(self, event)
        
        path = self.parent()._tree.path()
        self.setPath(path)



class Projects(QtGui.QWidget):
    
    dirChanged = QtCore.Signal(Path) # Emitted when the user changes the project
    
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        
        # Init variables
        self._path = ''
        
        # Create combo button
        self._combo = QtGui.QComboBox(self)
        self._combo.setEditable(False)
        self.updateProjectList()
        
        # Create star button
        self._but = QtGui.QToolButton(self)
        self._but.setIcon( iep.icons.star3 )
        self._but.setStyleSheet("QToolButton { padding: 0px; }");
        self._but.setIconSize(QtCore.QSize(18,18))
        self._but.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self._but.setPopupMode(self._but.InstantPopup)
        #
        self._menu = QtGui.QMenu(self._but)
        self._menu.triggered.connect(self.onMenuTriggered)
        self.buildMenu()
        
        # Make equal height
        h = max(self._combo.sizeHint().height(), self._but.sizeHint().height())
        self._combo.setMinimumHeight(h);  self._but.setMinimumHeight(h)
        
        # Connect signals
        self._but.pressed.connect(self.onButtonPressed)
        self._combo.activated .connect(self.onProjectSelect)
        
        # Layout
        layout = QtGui.QHBoxLayout(self)
        self.setLayout(layout)        
        layout.addWidget(self._but)
        layout.addWidget(self._combo)
        layout.setSpacing(2)
        layout.setContentsMargins(0,0,0,0)
    
    
    def currentDict(self):
        """ Return the current project-dict, or None.
        """ 
        path = self._combo.itemData(self._combo.currentIndex())
        return self.parent().dictForStarredDir(path)
    
    
    def setPath(self, path):
        self._path = path
        # Find project index
        projectIndex, L = 0, 0
        pathn = path.normcase()
        for i in range(self._combo.count()):
            projectPath = self._combo.itemData(i)
            if pathn.startswith(projectPath) and len(projectPath) > L:
                projectIndex, L = i, len(projectPath)
        # Select project or not ...
        self._combo.setCurrentIndex(projectIndex)
        if projectIndex:
            self._but.setIcon( iep.icons.star2 )
            self._but.setMenu(self._menu)
        else:
            self._but.setIcon( iep.icons.star3 )
            self._but.setMenu(None)
    
    
    def updateProjectList(self):
        # Get sorted version of starredDirs
        starredDirs = self.parent().starredDirs
        starredDirs.sort(key=lambda p:p.lower())
        # Refill the combo box
        self._combo.clear()
        for p in starredDirs:
            name = self.parent().dictForStarredDir(p).name
            self._combo.addItem(name, p)
        # Insert dummy item
        if starredDirs:
            self._combo.insertItem(0, translate('filebrowser', 'Projects:'), '') # No-project item
        else:
            self._combo.addItem(
                translate('filebrowser', 'Click star to bookmark current dir'), '')
    
    
    def buildMenu(self):
        menu = self._menu
        menu.clear()
        
        # Add action to remove bookmark
        action = menu.addAction(translate('filebrowser', 'Remove project'))
        action._id = 'remove'
        action.setCheckable(False)
        
        # Add action to change name
        action = menu.addAction(translate('filebrowser', 'Change project name'))
        action._id = 'name'
        action.setCheckable(False)
        
        menu.addSeparator()
        
        # Add check action for adding to Pythonpath
        action = menu.addAction(translate('filebrowser', 'Add path to Python path'))
        action._id = 'pythonpath'
        action.setCheckable(True)
        d = self.currentDict()
        if d:
            checked = bool( d and d['addToPythonpath'] )
            action.setChecked(checked)
    
    
    def onMenuTriggered(self, action):
        d = self.currentDict()
        if not d:
            return
        
        if action._id == 'remove':
            # Remove this project
            self.parent().removeStarredDir(d.path)
        
        elif action._id == 'name':
            # Open dialog to ask for name
            name = QtGui.QInputDialog.getText(self.parent(), 
                                translate('filebrowser', 'Project name'),
                                translate('filebrowser', 'New project name:'),
                                text=d['name'],
                            )
            if isinstance(name, tuple):
                name = name[0] if name[1] else ''
            if name:
                d['name'] = name
        
        elif action._id == 'pythonpath':
            # Flip add-to-pythonpath flag
            d['addToPythonpath'] = not d['addToPythonpath']
    
    
    def onButtonPressed(self):
        if self._but.menu():
            # The directory is starred and has a menu. The user just
            # used the menu (or not). Update so it is up-to-date next time.
            self.buildMenu()
        else:
            # Not starred right now, create new project!
            self.parent().addStarredDir(self._path)
        # Update
        self.setPath(self._path)
    
    
    def onProjectSelect(self, index):
        path = self._combo.itemData(index)
        if path:
            # Go to dir
            self.dirChanged.emit(Path(path))
        else:
            # Dummy item, reset
            self.setPath(self._path)



class NameFilter(LineEditWithToolButtons):
    """ Combobox to filter by name.
    """
    
    filterChanged = QtCore.Signal()
    
    def __init__(self, parent):
        LineEditWithToolButtons.__init__(self, parent)
        
        # Create tool button, and attach the menu
        self._menuBut = self.addButtonRight(iep.icons['filter'], True)
        self._menu = QtGui.QMenu(self._menuBut)
        self._menu.triggered.connect(self.onMenuTriggered)
        self._menuBut.setMenu(self._menu)
        #
        # Add common patterns
        for pattern in ['*', '!*.pyc', 
                        '*.py *.pyw', '*.py *.pyw *.pyx *.pxd', 
                        '*.h *.c *.cpp']:
            self._menu.addAction(pattern)
        
        # Emit signal when value is changed
        self._lastValue = ''
        self.returnPressed.connect(self.checkFilterValue)
        self.editingFinished.connect(self.checkFilterValue)
        
        # Ensure the namefilter is in the config and initialize 
        config = self.parent().config
        if 'nameFilter' not in config:
            config.nameFilter = '!*.pyc'
        self.setText(config.nameFilter)
    
    def setText(self, value, test=False):
        """ To initialize the name filter.
        """ 
        QtGui.QLineEdit.setText(self, value)
        if test:
            self.checkFilterValue()
        self._lastValue = value
    
    def checkFilterValue(self):
        value = self.text()
        if value != self._lastValue:
            self.parent().config.nameFilter = value
            self._lastValue = value
            self.filterChanged.emit()
    
    def onMenuTriggered(self, action):
        self.setText(action.text(), True)



class SearchFilter(LineEditWithToolButtons):
    """ Line edit to do a search in the files.
    """ 
    
    filterChanged = QtCore.Signal()
    
    def __init__(self, parent):
        LineEditWithToolButtons.__init__(self, parent)
        
        # Create tool button, and attach the menu
        self._menuBut = self.addButtonRight(iep.icons['magnifier'], True)
        self._menu = QtGui.QMenu(self._menuBut)
        self._menu.triggered.connect(self.onMenuTriggered)
        self._menuBut.setMenu(self._menu)
        self.buildMenu()
        
        # Create cancel button
        self._cancelBut = self.addButtonRight(iep.icons['cancel'])
        self._cancelBut.setVisible(False)
        
        # Keep track of last value of search (initialized empty)
        self._lastValue = '' 
        
        # Connect signals
        self._cancelBut.pressed.connect(self.onCancelPressed)
        self.textChanged.connect(self.updateCancelButton)        
        self.editingFinished.connect(self.checkFilterValue)
        self.returnPressed.connect(self.forceFilterChanged)
    
    def onCancelPressed(self):
        """ Clear text or build menu.
        """
        if self.text():
            QtGui.QLineEdit.clear(self)
            self.checkFilterValue()
        else:
            self.buildMenu()
    
    def checkFilterValue(self):
        value = self.text()
        if value != self._lastValue:
            self._lastValue = value
            self.filterChanged.emit()
    
    def forceFilterChanged(self):
        self._lastValue = value = self.text()
        self.filterChanged.emit()
    
    def updateCancelButton(self, text):
        visible = bool(self.text())
        self.setButtonVisible(self._cancelBut, visible)
    
    def buildMenu(self):
        config = self.parent().config
        menu = self._menu
        menu.clear()
        
        map = [ ('searchMatchCase', False, translate("filebrowser", "Match case")),
                ('searchRegExp', False, translate("filebrowser", "RegExp")),
                ('searchSubDirs', True, translate("filebrowser", "Search in subdirs"))
              ]
        
        # Fill menu
        for option, default, description in map:
            if option is None:
                menu.addSeparator()
            else:
                # Make sure the option exists
                if option not in config:
                    config[option] = default
                # Make action in menu
                action = menu.addAction(description)
                action._option = option
                action.setCheckable(True)
                action.setChecked( bool(config[option]) )
    
    def onMenuTriggered(self, action):
        config = self.parent().config
        option = action._option
        # Swap this option
        if option in config:
            config[option] = not config[option]
        else:
            config[option] = True
        # Update
        self.filterChanged.emit()
