#  this module looks for bt devices and returns as soon as it finds one
#  v1.5
import appuifw
import e32
import aosocketnativenew as aos

class BtDiscoverLocations:
	
    def __init__(self,locations):

	self.dev_seen = []
	self.locations = locations
	self.lock = e32.Ao_lock()
	self.r = aos.AoResolver()
	self.r.open()
	print 'just opened resolver'
	self.locations_seen = []
	appuifw.note(u'myBtDiscover v1.5','info')

    def start(self):
	appuifw.app.exit_key_handler = self.my_exit_handler
	try:
	    self.r.discover_noresolve( self.discovered, None)
	    print 'back from call to discover with no resolve'
	    self.lock.wait()
	except:
	    print 'exception when invoking noresolve'
	return (self.locations_seen,self.dev_seen)

    def discovered(self, error, address, name, data):
      try:
	print 'entering discovered',address
	if error:
	    print 'discovered error'
	    self.r.cancel()
	    self.r.close()
	    self.lock.signal()
	    return
	print 'discovered',address
	self.dev_seen.append( address )
	print 'past dev seen append'
	if address in self.locations.keys():
	    print "found interesting location"
	    self.locations_seen.append( self.locations[address] )
	print 'after appending to dev seen'
	self.r.next()
	print 'after r.next in discovered'
      except:
	  print 'in exception handler of discovered'
	  self.r.stop()
	  self.lock.signal()



    def my_exit_handler(self):
	    self.r.close()
	    self.lock.signal()
	
    def stop(self):
	self.r.cancel()
	self.r.close()

    def results(self):
	return self.locations_seen

if __name__ == "__main__":
    d =BtDiscoverLocations( { "001060a6740c":"office" })
    print 'about to start the discovery process'
    a,b = d.start()
    print 'returned from d.start, with',a,b
    d.stop()
    print 'stopped it and leaving'
