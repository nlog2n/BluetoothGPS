# Christopher Schmidt, Copyright 2006
# Released under the MIT License - Share and Enjoy
import select
import socket
import appuifw
import e32
from location import gsm_location
import time
import sysinfo

location = {}
cell = []
class App:
    def connect(self):
        self.sock=socket.socket(socket.AF_BT,socket.SOCK_STREAM)
        address,services=socket.bt_discover()
        print "Discovered: %s, %s"%(address,services)
        target=(address,services.values()[0])        

        print "Connecting to "+str(target)
        self.sock.connect(target)
    def close(self):
        self.sock.close()
    def readposition(self):
        try:
            length = 0
            while (select.select([self.sock], [],[],0.1) != ([],[],[])):
                length += len(self.sock.recv(8192))
            e32.ao_sleep(1)
            while 1:
                buffer=""
                ch=self.sock.recv(1)
                while(ch!='$'):
                    ch=self.sock.recv(1)
                while 1:
                    if (ch=='\r'):

                        break
                    buffer+=ch
                    ch=self.sock.recv(1)
                talker = buffer[1:3]
                sentence_id = buffer[3:6]
                sentence_data = buffer[7:]
                if (buffer[0:6]=="$GPGGA"):
                    self.do_gga_location(sentence_data)
                    return (location['lat'], location['long'])
        except Exception, E:
            appuifw.note(u"%s"%E,"error")
            return None
    def do_gga_location(self,data):
        """Get the location from a GGA sentence"""
        global location

        d = data.split(',')
        location['type'] = 'GGA'
        location['lat'] = "%s%s" % (d[1],d[2])
        location['long'] = "%s%s" % (d[3],d[4])
        location['alt'] = "%s %s" % (d[8],d[9])
        location['time'] = self.format_time(d[0])
        location['sats'] = d[7]
    def __init__(self):
        self.lock = e32.Ao_lock()
        self.loc = []
        drives = e32.drive_list()
        self.filename = "E:\\gps.log"
        if not u"E:" in drives:
                self.filename = "C:\\gps.log"
        self.file = open(self.filename, "a")
        self.running = 0
        self.old_exit_key = appuifw.app.exit_key_handler
        appuifw.app.exit_key_handler = self.exit_handler
        self.connect()
        appuifw.app.title = u"Cellstumbling!"
        appuifw.app.menu = [(u"Stumble", self.start),
                            (u"Upload", self.upload),
                            (u"Exit", self.exit_handler)]
        canvas=appuifw.Canvas(redraw_callback=lambda rect:self.draw_main())
        appuifw.app.body=canvas
        self.lock.wait()
    def start(self):
        self.running = 1
        appuifw.app.menu = [(u"Stop", self.pause),
                            (u"Upload", self.upload),
                            (u"Exit", self.exit_handler)]
        self.run()
    def upload(self):
        self.running = 0
        canvas = appuifw.app.body
        canvas.text( (40,100), u'Uploading data...')
        self.file.close()
        import urllib
        tmpfile = open(self.filename, "r")
        data = tmpfile.read()
        urllib.urlopen("http://gsmloc.org/upload", urllib.urlencode( { 'upload': data })).close()
        tmpfile.close()
        appuifw.note(u"Upload Complete!", "info")
        self.file = open(self.filename, "w")
        self.running = 1
    def pause(self):
        self.running = 0
        appuifw.app.menu = [(u"Stumble", self.start),
                            (u"Upload", self.upload),
                            (u"Exit", self.exit_handler)]
    def exit_handler(self):
        self.running = 0
        self.file.close()
        self.close()
        self.lock.signal()
    def run(self):
        if (self.running):
            (lat,long) = self.readposition()
            global cell,location
            cell = gsm_location()
            self.draw_main()
            if float(location['sats']) < 31:
                if (self.file.closed):
                    self.file = open(self.filename, "a")
                self.file.write("%s,%s,%s,%s,%s,%s,%s,%s\n"%(cell[0],cell[1],cell[2],cell[3],sysinfo.signal(),lat,long,time.time()))
            e32.ao_sleep(1, self.run)
    def format_time(self, time):
        """Generate a friendly form of an NMEA timestamp"""
        hh = time[0:2]
        mm = time[2:4]
        ss = time[4:]
        return "%s:%s:%s UTC" % (hh,mm,ss)
        
    def draw_main(self):
        global location
        global cell
        canvas = appuifw.app.body
        canvas.clear()
        yPos = 12
        if hasattr(canvas, 'text'):
            canvas.text( (0,yPos), u'Time:', 0x008000)
            if not location.has_key('time'):
                    cur_time = u'(unavailable)'
            else:
                    cur_time = unicode(location['time'])
            canvas.text( (60,yPos), cur_time)
            yPos += 12

            canvas.text( (0,yPos), u'Location', 0x008000)
            if location.has_key('alt'):
                    canvas.text( (105,yPos), unicode(location['alt']) )
            if (not location.has_key('lat')) or (not location.has_key('long')):
                    cur_loc = u'(unavailable)'
            else:
                    if location['lat'] == '0000.0000N' and location['long'] == '0000.0000E':
                            cur_loc = u'(invalid location)'
                    else:
                            cur_loc = unicode(location['lat']) + '  ' + unicode(location['long'])
            canvas.text( (10,yPos+12), cur_loc)
            yPos += 24
            canvas.text( (0,yPos), u'Accuracy:', 0x008000)
            if (not location.has_key('sats')):
                    canvas.text( (60,yPos), u'Unavailable')
            else:
                    canvas.text( (60,yPos), u'%s' % (location['sats']))
            
            yPos += 12
            canvas.text( (0,yPos), u'Cell:', 0x008000)
            if (len(cell)):
                    canvas.text( (40,yPos), u'%s,%s,%s,%s' % (cell[0],cell[1],cell[2],cell[3]))
            yPos += 12
        
A = App()
