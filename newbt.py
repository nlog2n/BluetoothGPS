#  this module looks for bt devices and returns as soon as it finds one
import aosocketnativenew as aos
import newdbg

class BtDiscoverLocations:
	
    def __init__(self,locations):
	self.dbg = newdbg.newdbg('BT-dis',0)
	self.dbg.enter('init')

	self.locations = locations
	self.r = aos.AoResolver()
	self.r.open()
	self.dbg.dbg('just opened resolver')
	self.dev_seen = []
	self.locations_seen = []
	self.searching = False
	self.dbg.exit('init')

    def start(self):
	self.dbg.enter('start')
	try:
	    self.r.discover_noresolve( self.discovered, None)
	    self.searching = True
	except:
	    self.searching = False
	    self.dbg.dbg( 'exception when invoking noresolve')
	return self.dbg.exit('start',self.searching)

    def discovered(self, error, address, name, data):
      try:
	self.dbg.enter('discovered')
	self.dbg.dbg('entering discovered: address:%s'%address)
	if error:
	    self.dbg.dbg('discovered error')
	    self.r.cancel()
	    self.r.close()
	    self.searching = False
	    return self.dbg.exit('discovered')
	self.dev_seen.append( address )
	if address in self.locations.keys():
	    self.locations_seen.append( self.locations[address] )
	self.r.next()
      except:
	  self.r.stop()
      return self.dbg.exit('discovered')


    def still_searching(self):
	return self.searching

    def results(self):
	return (self.dev_seen , self.locations_seen)

    def str(self):
	if  len( self.locations_seen ) > 0 :
	    return self.locations_seen[0]
	else:
	    return 'None'
	

if __name__ == "__main__":
    import e32
    d =BtDiscoverLocations( { "001060a6740c":"office" })
    print 'about to start the discovery process'
    tf= d.start()
    print 'returned from d.start, with',tf
    while d.still_searching():
	print 'still searching'
	e32.ao_sleep(1)
    print d.str()
    print d.results()
