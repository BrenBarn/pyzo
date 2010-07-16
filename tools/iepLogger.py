import sys, os, code
from PyQt4 import QtCore, QtGui
import iep
from shell import BaseShell
from iepLogging import splitConsole


tool_name = "Logger"
tool_summary = "Logs messages, warnings and errors within IEP."
 

class IepLogger(BaseShell):
    """ Shell that logs all messages produced by IEP. It also 
    allows to look inside IEP, which can be handy for debugging
    and developing.
    """
    
    def __init__(self, parent):
        BaseShell.__init__(self, parent)
        
        # apply style        
        self.setStyle('loggerShell')
        #self._reduceFontSizeToMatch80Columns = False
        
        # Create interpreter to run code        
        locals = {'iep':iep, 'sys':sys, 'os':os}
        self._interpreter = code.InteractiveConsole(locals, "<logger>")
        
        # Show welcome text
        moreBanner = "This is the IEP logger shell." 
        self.write("Python %s on %s - %s\n\n" %
                       (sys.version[:5], sys.platform, moreBanner))
        self.writeErr(sys.ps1)
        
        # Split console
        history = splitConsole(self.write, self.writeErr)
        self.write(history)
    
    
    def executeCommand(self, command):
        """ Execute the command here! """
        # Use writeErr rather than sys.stdout.write. This prevents
        # the prompts to be logged by the history. Because if they
        # are, the text does not look good due to missing newlines
        # when loading the history.
        more = self._interpreter.push(command.rstrip('/n'))
        if more:
            BaseShell.writeErr(self, sys.ps2)
        else:            
            BaseShell.writeErr(self, sys.ps1)  
    
    
    def writeErr(self, text):
        """ Overload so that when an error is printed, we can  
        insert a new prompt. """
        # Write normally
        BaseShell.writeErr(self, text)
        # Goto end
        self.setPositionAndAnchor(self.length())
        
        
    # Note that I did not (yet) implement calltips
    
    def processAutoComp(self, aco):
        """ Processes an autocomp request using an AutoCompObject instance. 
        """
        
        # Try using buffer first
        if aco.tryUsingBuffer():
            return
        
        # Include buildins?
        if not aco.name:
            command = "__builtins__.keys()"
            try:
                names = eval(command, {}, self._interpreter.locals)
                aco.addNames(names)
            except Exception:
                pass
        
        # Query list of names
        command = "dir({})".format(aco.name)
        try:
            names = eval(command, {}, self._interpreter.locals)
            aco.addNames(names)
        except Exception:
            pass
        
        # Done
        aco.finish()