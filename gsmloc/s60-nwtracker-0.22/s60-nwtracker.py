# -*-python-*-
# $Id: s60-nwtracker.py,v 1.26 2006/09/18 07:29:26 asc Exp $

__package__    = "s60-nwtracker"
__version__    = "0.22"
__author__     = "Aaron Straup Cope"
__url__        = "http://www.aaronland.info/python/nwtracker/"
__cvsversion__ = "$Revision: 1.26 $"
__date__       = "$Date: 2006/09/18 07:29:26 $"
__copyright__  = "Copyright (c) 2006 Aaron Straup Cope. Perl Artistic License."

import e32
import anydbm
import appuifw
import time

import httplib
import urllib
import urlparse
import os
import os.path
import base64

if not e32.in_emulator() :
    import sysinfo    
    import location
    import aosocketnativenew
    from aosocket.symbian.bt_device_discoverer import *

#
#
#

def collect_bt_callback (error, devices, cb_param) :

    nw, ts = cb_param

    if error :
        nw.log("bt collection failed %s" % error)
        return

    labels = []
    
    for address, name in devices :
        labels.append(address)

    if len(labels) > 0 :
        nw.record('bt', ts, labels)
    
#
#
#

class nwtracker :

    def __init__ (self) :

        self.queue    = {}
        self.polling  = False
        self.flushing = False
        self.kill     = False
        self.__msg   = u""

        self.old_title = appuifw.app.title
        appuifw.app.title = u"nwtracker"
        appuifw.app.exit_key_handler = self.abort

        self.__logpath = u"e:\\nwtracker.txt"             
        self.__cfgpath = u"c:\\nwtracker.db"
        
        self.lock  = e32.Ao_lock()

        self.__options = [(u"Start recording", self.start_polling),
                          (u"Stop recording", self.stop_polling),
                          (u"Configure dispatcher", self.config_flushto),
                          (u"Configure frequency", self.config_poll_interval),                          
                          (u"Configure endpoint", self.config_endpoint),
                          (u"Configure credentials", self.config_login),
                          (u"Flush local log", self.flush_local_log_to_cloud),                          
                          (u"Delete local log", self.delete_local_log)]
        
    #
    #
    #

    def open_cfg (self) :
        self.log("Reading configs")

        if not os.path.exists(self.__cfgpath) :
            self.__cfg = anydbm.open(self.__cfgpath, "c")
            self.__cfg.close()

        self.__cfg = anydbm.open(self.__cfgpath, "w")
        return True

    #
    #
    #
    
    def store_cfg (self) :
        self.__cfg.close()

    #
    #
    #
    
    def abort(self) :
        self.kill = True
        self.old_title = appuifw.app.title

        self.store_cfg()        
        self.lock.signal()

    #
    #
    #
    
    def loop (self) :
        if self.setup() :
            self.run()
            
        self.lock.wait()

    #
    #
    #

    def setup (self) :
        self.open_cfg()

        if not self.__cfg.has_key('flushto') :
            if not self.config_flushto() :
                return False

        if self.__cfg['flushto'] == '1' :
            force = 0
            
            if not self.config_endpoint(force) :
                return False

        if not self.__cfg.has_key('interval') :
            self.config_poll_interval()
            
        appuifw.app.menu = self.__options            
        return True

    #
    #
    #
    
    def run (self) :
        self.clear_log()
        self.log("Okay. nwtracker (%s) is ready to go!" % __version__)
        self.log("Select 'Start recording' from the Options menu to begin")

    #
    #
    #

    def start_polling (self) :

        if self.polling :
            return True
        
        self.log("Recording started")        
        self.polling = True
        self.poll()

    #
    #
    #

    def stop_polling (self) :
        self.log("Recording stopped")
        self.polling = False
        
    #
    #
    #
    
    def poll (self) :

        if not self.polling :
            return True
        
        if self.kill :
            return False

        now = int(time.time())
        self.log("Polling : %s" % now)    
        
        self.collect_gsm_data(now)
        self.collect_bt_data(now)

        self.flush_queue()

        wait = int(self.__cfg['interval'])
        e32.ao_sleep(wait, self.poll)

    #
    #
    #

    def config_poll_interval (self) :
        default = 60
        current = default

        if self.__cfg.has_key('interval') :
            current = self.__cfg['interval']

        prompt = u"Number of seconds between polling"
        input  = appuifw.query(prompt, "text")

        if input == None :
            input = default

        if int(input) <= 0 :
            self.log("Interval can not be less than 0; using default")
            input = default

        input = unicode(input)
        
        self.log("Polling interval set to %s seconds" % input)            
        self.__cfg['interval'] = input
        return True
    
    #
    #
    #
    
    def config_flushto (self) :

        opts   = [u"Write to disk", u"Send to the intarweb"]
        prompt = u"Where should data be written?"
        
        dest  = appuifw.popup_menu(opts, prompt)

        if dest == None :
            if self.__cfg.has_key('flushto') :
                del(self.__cfg['flushto'])
            return False

        if dest == 0 :
            msg = u"Data will be written to %s" % self.__logpath
            appuifw.note(msg, "info")
            
        self.__cfg['flushto'] = unicode(dest)
        return True
            
    #
    #
    #
    
    def config_endpoint (self, force=1) :

        if not force and self.__cfg.has_key('host') and self.__cfg['host'] != '' :
            return True
        
        url = appuifw.query(u"Post to where", "text")

        if url == None :
            return False

        if not url.startswith("http://") :
            url = "http://%s" % url
            
        (scheme, netloc, path, query, fragment) = urlparse.urlsplit(url)
        
        if netloc == '' :
            return False

        self.__cfg['host']     = netloc
        self.__cfg['endpoint'] = path

        self.log("storing %s%s" % (self.__cfg['host'], self.__cfg['endpoint']))
        
        if fragment != '' :
            self.__cfg['endpoint'] = "%s?%s" % (self.__cfg['endpoint'], fragment)
            
        if query != '' :
            self.__cfg['endpoint'] = "%s?%s" % (self.__cfg['endpoint'], query)

        if not self.config_login() :
            return False

        return True
    
    #
    #
    #
    
    def config_login (self) :

        opts   = [u"No login required", u"Set username and password"]

        if self.__cfg.has_key('user') and self.__cfg['user'] != '' :
            opts.append(u"Use existing credentials")
            
        prompt = u"Credentials"
        
        login  = appuifw.popup_menu(opts, prompt)

        if login == None :
            return True

        if login == 2 :
            return True
        
        if login == 0 :
            self.__cfg['user'] = ''
            self.__cfg['pswd'] = ''
        else :
            user = appuifw.query(u"username", "text")
            pswd = appuifw.query(u"password", "text")

            if user == None :
                return False

            if pswd == None :
                return False

            self.__cfg['user'] = user
            self.__cfg['pswd'] = pswd
            
        return True
    
    #
    #
    #
    
    def collect_gsm_data (self, ts) :

        if e32.in_emulator() :
            return
        
        (mcc, mnc, lac, cellid) = location.gsm_location()
        data = [unicode(mcc), unicode(mnc), unicode(lac), unicode(cellid)]
        
        self.record('gsm', ts, data)

    #
    #
    #
    
    def collect_bt_data (self, ts) :

        if e32.in_emulator() :
            return
        
        self.__btlock = True
        self.__btdevices = []

        #
        
        lister = BtDeviceLister()
        lister.discover_all(collect_bt_callback, (self, ts))
                
    #
    #
    #

    def clear_log(self) :
        self.__msg = u""

    #
    #
    #
    
    def log (self, msg) :

        self.__msg += "%s\n" % msg
        self.write(unicode(self.__msg))

    #
    #
    #
    
    def write(self, txt) :

        if e32.in_emulator() :
            t = appuifw.Text()
            t.write(txt)
            appuifw.app.body = t

        else :
            appuifw.app.body = appuifw.Text(txt)
            
    #
    #
    #
    
    def record (self, source, ts, data) :

        msg = u"Store %s : '%s'" % (source, data)
        self.log(msg)
        
        if not self.queue.has_key(ts) :
            self.queue[ts] = {}

        self.queue[ts][source] = data

    #
    #
    #
    
    def flush_queue (self) :

        if self.flushing :
            return
        
        self.flushing = True
        
        purge = []
        
        for ts in self.queue :
            for source, data in self.queue[ts].items() :

                ok = False

                if self.__cfg['flushto'] == '1' :
                    ok = self.flush_to_cloud(ts, source, data)
                else :
                    ok = self.flush_to_disk(ts, source, data)
                
                if ok :
                    purge.append(ts)

        for ts in purge :
            # this shouldn't be necessary but...
            if self.queue.has_key(ts) :
                del(self.queue[ts])

        self.flushing = False

    #
    #
    #

    def flush_to_cloud (self, ts, source, data) :
        str_data = self.stringify_data(data)
        
        args   = {'ts':ts, 'src':source, 'data':str_data, 'interval' : self.__cfg['interval']}
        params = urllib.urlencode(args)
        return self.send_to_cloud(params)

    #
    #
    #
    
    def stringify_data (self, data) :
        return u";".join(data)
    
    #
    #
    #

    def flush_local_log_to_cloud (self) :

        if not self.__cfg.has_key('host') or self.__cfg['host'] == '' :
            if not self.config_endpoint() :
                self.log("No endpoint defined.")
                return False

        if self.flushing :
            self.log("Already in the process of flushing data")
            return False
        
        self.flushing = True

        try :
            fh = open(self.__logpath, 'r')
        except Exception, e :
            self.log("Failed to open local log, %s" % e)
            return False
    
        for ln in fh.readlines() :
            ln    = ln.rstrip()
            input = ln.split(";")
            
            ts    = input[0]
            src   = input[1]
            data  = input[2:]

            self.log("Sending %s data for %s" % (src, ts))
            
            if not self.flush_to_cloud(ts, src, data) :
                self.log("Unable to send %s data for %s; adding it back to the queue" % (src, ts))
                self.record(ts, src, data)

        fh.close()

        self.log("Finished flushing local log")
        
        try :
            os.unlink(self.__logpath)
        except Exception, e :
            self.log("Failed to delete local log, %s" % e)
            
        self.flushing = False
        return True

    #
    #
    #
    
    def delete_local_log (self) :

        if os.path.exists(self.__logpath) :

            try :
                os.unlink(self.__logpath) 
            except Exception, e :
                self.log("Failed to delete %s : %s" % (self.__logpath, e))
                return False
            
        return True
    #
    #
    #
    
    def flush_to_disk (self, ts, source, data) :

        str_data = self.stringify_data(data)
        
        try :
            fh = open(self.__logpath, "a")
        except :
            return False
        
        fh.write("%s;%s;%s;%s\n" % (ts, self.__cfg['interval'], source, str_data))
        fh.close()
        
    #
    #
    #

    def send_to_cloud (self, params) :

        if not e32.in_emulator and sysinfo.signal == 0 :
            self.log("No signal")
            return False
        
        headers = {}

        if self.__cfg['pswd'] :
            base64string = base64.encodestring('%s:%s' % (self.__cfg['user'], self.__cfg['pswd']))[:-1]            
            headers = {"Authorization":"Basic %s" % base64string}

        try :
            conn = httplib.HTTPConnection(self.__cfg['host'])
            conn.request('POST', self.__cfg['endpoint'], params, headers)
        except Exception, e :
            self.log("HTTP request failed : %s" % e)
            return False
        
        res = conn.getresponse()

        if res.status != 200 :

            if res.status == 403 :
                if appuifw.query(u"Login failed. Reconfigure?", "query") :
                    if self.config_login() :
                        return self.send_to_cloud(params)

            self.log("Unable to send to cloud, failed with error : %s" % res.status)

            #
            # just a little bit of hoop-jumping to
            # prevent the app from always sending
            # the same bad data over and over...
            #
            
            if res.status == 400 :
                return True
            
            return False

        return True
    
    #
    #
    #
    
if __name__ == "__main__" :
    app = nwtracker()
    app.loop()
