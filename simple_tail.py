import os, time
import traceback

class SimpleTail(object):
    def __init__(self, filename):
        self.filename = filename
        self.file = None
        self.inode = None
        
    def readline(self, sleep_on_empty=False):
        line = None
        try:
            # 1) open the file if it's not open
            if not self.file:
                self.open_file()
            
            # 2) try to read a line of the file
            line = self.file.readline()
            
            # 3a) if a line is read, update the timestamp of the last line read
            if line:
                self.last_read = time.time()
            elif time.time() - self.last_read > 10:
                # 3b) If no changes to the file in 10 seconds reopen it.
                try:
                    self.file.close()
                except:
                    traceback.print_exc()
                    
                self.open_file()
        except ValueError:
            # 4) if we got a ValueError than it means that readline() was probably closed
            try:
                # 5) try to close it again
                self.file.close()
            except:
                traceback.print_exc()
            
            # 6) reopen
            self.open_file()
        except:
            traceback.print_exc()
            time.sleep(5)
        
        # 7) if line is empty, and we sleep on empty lines.. sleep
        if line == '' and sleep_on_empty:
            time.sleep(1)
        
        # 8) if we threw an exception line will be None, set it to empty string
        if line == None:
            line = ''

        # 9) return value
        return line
        
    def open_file(self):
        self.file = open(self.filename,'r')
        
        st_results = os.stat(self.filename)
        st_size = st_results[6]
        inode = st_results[1]
        
        inode_has_not_changed = inode == self.inode or self.inode == None
        
        if inode_has_not_changed:
            # seek to end of file if we just started tailing, or are
            # 
            self.file.seek(st_size)
        else:
            # do not seek to the end of the file, since it's a new file which
            # in theory contains new items to tail
            pass
            
        # store last inode
        self.inode = st_results[1]
        self.last_read = time.time()

if __name__ == '__main__':
    a = SimpleTail("/var/log/test.log")
    
    while True:
        print a.readline(sleep_on_empty=True)