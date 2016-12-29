""" Periodically, this program wakes up, and probes for
       bluetooth dongles
       cell towers

       and then records what it found along with the current time

       to keep the size of log smallish, a table of locations is maintained
       and the log entries refer to that table (we could, but do not, make
       the time and location smaller by using diffs rather than wholes
"""

import socket
import e32,appuifw
from time import *
import location
from newgps import *
import pickle
#import sendToServer         ### commented by fanghui
import types
import sysinfo  # to get the imei info
import time
import btdis

def display_on_screen(what, str):
    def truefalse(val):
	if val == u'False': return u'False'
	if val ==  'False': return u'False'
	if val == 0:        return u'False'
	return u'True'
    global exit_flag
    global disp_gsm, disp_gsm_time, disp_gps, disp_gps_time, disp_off, disp_off_time, disp_err, disp_err_time
    global disp_up, disp_up_time, disp_stat, disp_stat_time, disp_sleep, disp_sleep_time, disp_msg, disp_msg_time
    global bed_time, disp_gps_warning

    if what == 'error': dbg(str,True)
#    print "Display on screen",what,str
    local_time = time.localtime()
    y,m,d,h,mn,s,x1,x2,x3 = local_time
    disp_time      = unicode( '%02d' % (mn) ) 
    disp_time_hm   = unicode( ' %d:%02d' % (h,mn) ) 
    disp_time_full = unicode( ' %d:%02d:%02d' % (h,mn,s) ) 
    if     what == 'gsm':  (disp_gsm, disp_gsm_time) = ( str , disp_time )
    elif   what == 'gps':  
	str = '%5.2f,%5.2f'% str
#	str = '%s,%s'% str
	(disp_gps, disp_gps_time) = ( str , disp_time )
    elif what == 'gpswarning':
	disp_gps_warning = str
    elif   what == 'office':  (disp_off, disp_off_time) = ( truefalse(str) , disp_time_full )
    elif   what == 'upload':  (disp_up, disp_up_time) = ( str , disp_time_full )	
    elif   what == 'status':  (disp_stat, disp_stat_time) = ( str , disp_time )
    elif   what == 'sleep':  
           (disp_sleep, disp_sleep_time) = ( str , disp_time )
	   bed_time = time.time()+str
    elif   what == 'mesg':  (disp_msg, disp_msg_time) = ( str , disp_time_hm )
    elif   what == 'error':  (disp_err, disp_err_time) = ( str , disp_time )
    else:  disp_msg =  u'wrong parameter to display\n %s, str: %s' % (what.__str__(),str.__str__())
#    print '((on screen:',str,"))"
#    print 'Current Time: %s\n' %  disp_time_full
#    print 'Cell Tower: %s \n'      % disp_gsm            
#    print 'GPS: %s -%s-\n'         % (disp_gps, disp_gps_time)                   
#    print 'Last Upload: %s \n'     % disp_up_time                             
#    print 'Office: %s -%s-\n'      % (disp_off, disp_off_time)                
#    print 'Secs to wakeup: %s (%s)\n' % (abs( bed_time - time.time() ),disp_sleep)           
#    print 'Status: %s \n'          % exit_flag                                    
#    print 'Mesg: %s -%s-\n'        % (disp_msg,disp_msg_time)                 
#    print 'Error Msg: %s -%s-\n'   % (disp_err, disp_err_time)

    msg_err_str = ""
    if not disp_err == 0 and disp_err_time == disp_time :
	    msg_err_str =  u'Error Msg: %s -%s-\n'   % (disp_err, disp_err_time) 
    display_str = u'Current Time: %s\n' %  disp_time_full  \
            + u'Cell Tower: %s \n'      % disp_gsm         \
	    + u'GPS: %s -%s- (%s)\n'         % (disp_gps, disp_gps_time, disp_gps_warning)  \
	    + u'Last Upload: %s \n'     % disp_up_time               \
	    + u'Office: %s -%s-\n'      % (disp_off, disp_off_time)  \
	    + u'Status: %s \n'          % exit_flag                  \
	    + u'Mesg: %s -%s-\n'        % (disp_msg,disp_msg_time)   \
	    + msg_err_str \
	    + u'Wakeup in: %s (%s)\n' % (abs( bed_time - time.time() ),disp_sleep)             


    appuifw.app.body = appuifw.Text(display_str)


def appendToTrace(label,val):
    global MainTrace
    t = int(time.time()) 
    MainTrace.append( (t, label, val ))

def get_gsm():
    try:
	(a,b,c,d) = location.gsm_location()
    except:
	return False
    display_on_screen('gsm', (c,d).__str__() )
    return (a,b,c,d)


def get_gps():
    global gps_handle

    lat,lon,speed,course = (-1.0,-1.3,0.0,0.0)
    display_on_screen('gpswarning','searching')
    display_on_screen('gps',(-1.1,-1.1))
    haveFix = False
    try:
	if not gps_handle:
	    gps_handle = my_gps()
	g = gps_handle
    except:
	display_on_screen('error','in get_gps, failute to get class')
	return False

    try:
	getFixReturn = g.get_fix()
	print 'get fix returned with value:',getFixReturn
    except:
	display_on_screen('error',"exception from get_fix: ")
	try:
	    gps_handle.disconnect_gps()
	except:
	    display_on_screen('error','gps except fix and disconnect')
	gps_handle = False
	return False

    print 'in get_gps, and getFixReturn is ',getFixReturn
    if getFixReturn == 'valid': 
	print "valid fix in aTrack"
	try:
	    fff = g.readings()
	    display_on_screen('gpswarning','valid')
	    display_on_screen('gps', (fff[0],fff[1]) )
	    haveFix = fff
	except:
	    display_on_screen('gpswarning','Error')
	    display_on_screen('error',"exception from g.readings:")
    elif getFixReturn == 'invalid':
	print 'about to display on screen'
	display_on_screen('gpswarning','Invalid')
	display_on_screen('gps',(-1.2,-1.2))
	print 'returned from display on screen'
	print 'setting haveFix to False and returning'
    else:
	display_on_screen('gpswarning','False')
	display_on_screen('gps',(-1.4,-1.4))
	try:
	    gps_handle.disconnect_gps()
	except:
	    display_on_screen('error','gps except fix and disconnect')
	gps_handle = False
    print 'returning from get_gps',haveFix
    return haveFix



def probe_g():
    global n_probes
    global n_no_gps
    global exit_flag,exitting

    if exit_flag:
	exitting = True
	return

    status = "%s"%n_probes
    gps = get_gps()
    gsm = get_gsm()

    interval = g_query_interval
    if gps and gsm:
	status = "gps & gsm"
	(lat,lon,speed,course) = gps
	ll = (lat,lon)
	appendToTrace('gpm',(ll,gsm))
	if gps[3] > 1.0:
	    appendToTrace('gsc',gps)
	n_no_gps = 0

    elif gps and not gsm:
	status = " gps"
	(lat,lon,speed,course) = gps
	appendToTrace('gps',gps)
	n_no_gps = 0
    elif not gps and gsm:
	status = " gsm"
	appendToTrace('gsm',gsm)
	if  n_no_gps > 5 : interval = g_max_query_interval
	else:  n_no_gps += 1
    elif not gps and not gsm:
	if  n_no_gps > 5 : interval = g_max_query_interval
	else:  n_no_gps += 1

    display_on_screen('status', status )
    try:
	bt = probe_bt()
    except:
	display_on_screen('error',u'exception probe bt')
	dbg('error','exception probe bt')
	

    if n_probes == 5:
	try:
	    record_bt_dev_seen()
	    record_to_server()
	except:
	    display_on_screen('error',u'exception record to server')
	n_probes = 0
    else:
	n_probes += 1
    

    if not exit_flag: 
	display_on_screen( 'sleep', interval)
	schedule_after(g_timer,interval, probe_g)	
	#g_timer.after(interval,probe_g)
	exitting = False
    else:
	display_on_screen( 'status', 'exitting')
	exitting = True
#	app.set_exit()

def schedule_after(t,interval,fun):
    global ticks
    global sleeping_threads
    ticks = interval+1
    sleeping_threads = sleeping_threads + 1
    ticktock()

def ticktock():
    global ticks
    global sleeping_threads

#    print 'sleeping threads:',sleeping_threads
    ticks = ticks - 1
    display_on_screen('status',' zzz ')
    if ticks <= 0:
	sleeping_threads = sleeping_threads - 1
	if ticks < -10:
	    display_on_screen('status','ticks < -10 ')
	probe_g()
    else:
	g_timer.after(1,ticktock)


def probe_g_now():
#    print 'cancelling the timer for the probe'
    g_timer.cancel()
#    print 'yielding'
    e32.ao_yield()
#    print 'calling probe'
    probe_g()

def append_to_bt_seen(new_devs):
    global bt_devices_discovered
    for d in new_devs:
	if not d in bt_devices_discovered:
	    bt_devices_discovered.append(d)
def record_bt_dev_seen():
    global bt_devices_discovered
    if len(bt_devices_discovered) > 0:
	appendToTrace('BTdevs',bt_devices_discovered)
	bt_devices_discovered = []

def probe_bt():
    # Add code to look for home as well
    global inOffice

    try:
	print 'in probe_bt .... '
	d = btdis.BtDiscoverLocations( 	{ "001060a6740c":"office" , 
					  "001060a8954c":"office" , 
					  "000f3d05749a":"office" 
					  }	)
#   the locs are locations input to discoverer; devs are other btid noticed.
#   we will send back unique devs	
	locs , devs = d.start()
	append_to_bt_seen(devs)
#	d.stop()

	inOffice = "office" in locs
	display_on_screen('office',inOffice)
	status = inOffice
    except:
	inOffice = False
	display_on_screen('office','False')
	status = False
    return status

def addLabel():
    lab = appuifw.query(u'Give a label for location',u'text')
    appendToTrace('label',lab)

def showGps():
    fix = get_gps()
#    if fix:
#	a,b,c,d = fix
#	display_on_screen('gpswarning','valid')
#	display_on_screen('gps' , (a,b) )
#    else:
#	display_on_screen('gpswarning','va')
#	display_on_screen('gps' , (-1.0,-1.2) )
	
def showGsm():
    display_on_screen('gsm',   get_gsm().__str__() )

def addGpsDevice():
    global gps_handle
    targets = [ '00:08:0D:15:5A:7F',u'00:0a:3a:1e:36:73',u'00:08:1b:8c:8f:06']

    i = appuifw.selection_list(targets)
    gps_handle.disconnect_gps()
    gps_handle = gpsgetfix( (targets[i],1) )
    gps_handle.connect_gps()


def changeIntervals():		    
    global g_query_interval, g_max_query_interval
    g_query_interval = appuifw.query(u'New value for probe interval',u'number',g_query_interval)
    g_max_query_interval = appuifw.query(u'New value for max probe interval',u'number',g_max_query_interval)

def changeDebugMode():		    
    global debugging_code
    debugging_code = appuifw.query(u'Debugging Code? (falase is 0)',u'number',debugging_code)


def write_tracedump():
    global Maintrace
    if debugging_code: return

    try:
       f = open(u'e:\\system\\apps\\python\\my\\tracedump.txt','w')
       mt = pickle.dumps( MainTrace )
    except:
       display_on_screen('error', "failed to open tracedump.txt")
       return pickle.dumps(MainTrace)
    try:
	f.write(mt)
    except:
       display_on_screen('error',"failed to write tracedump.txt")

    f.close()
    return pickle.dumps(MainTrace)

def myexit():
    global exit_flag
    exit_flag = True
    g_timer.cancel()
    display_on_screen('status','exiting')
    e32.ao_yield()
    main_lock.signal()




def record_to_server():
    global MainTrace,inOffice
    if debugging_code: return

#    print 'entering record to server'
    mt = pickle.dumps(MainTrace)
    print 'size of mt:',len(mt)
    write_tracedump()
    
    ss = ''
    for x in mt:
	xx = x.__str__()
	ss = ss + xx
#    fields = [ ('log',mt) ]
    fields = [ ('log',ss) ]
    print 'size of ss:',len(ss)    
    if inOffice:
	fields.append( ('office',"True") )
    display_on_screen('mesg',u'Sending %d to Server'%len(mt))
    try:
#	print 'about to sent to server'

##commentedy by fanghui: will store locally in mobile phone.
#	res = sendToServer.post_multipart("people.csail.mit.edu",'/rudolph/inc/simpleServer.py',fields)


#	print 'returned sending to server',res
	res = int(res)
	if res == len(mt):
	    MainTrace = []
	    display_on_screen('upload', res )
	    write_tracedump()
	else:
    	    display_on_screen('error', 'from server (%s != %s) ' % (res,len(mt)) )
    except:
	display_on_screen('error', 'Failed to send to server')


def try_probe_g():
    try:
	probe_g()
    except:
	display_on_screen('error',u'caught exception from probe_g')
#	print 'exception:',sys.exc_info()
#	try_probe_g()







###########################################
#   main #   main  #   main #   main #   main
###########################################

#print 'free ram:',sysinfo.free_ram(),' free drive', sysinfo.free_drivespace() 


debugging_code = False  # prevents sending to server or writing logs, if it is set to trye

global g_query_interval, g_max_query_interval, bt_query_interval, record_query_interval,bt_max_query_interval, record_max_query_interval
global inOffice
global n_probes
global n_no_gps
global exit_flag,exitting
global gps_handle
global sleeping_threads
sleeping_threads = 0

gps_handle = False

exit_flag = False
exitting = False
n_no_gps = 0
n_probes = 0
inOffice = False
filecount = 1


global disp_gsm, disp_gsm_time, disp_gps, disp_gps_time, disp_off, disp_off_time, disp_err, disp_err_time
global disp_up, disp_up_time, disp_stat, disp_stat_time, disp_sleep, disp_sleep_time, disp_msg, disp_msg_time
global bed_time, disp_gps_warning
global bt_devices_discovered

bt_devices_discovered = []

disp_gsm, disp_gsm_time, disp_gps, disp_gps_time, disp_off, disp_off_time, disp_err, disp_err_time = (0,0,0,0,0,0,0,0)
disp_up, disp_up_time, disp_stat, disp_stat_time, disp_sleep, disp_sleep_time, disp_msg, disp_msg_time = (0,0,0,0,0,0,0,0)
bed_time  = time.time()
disp_gps_warning = 2


oldexit = appuifw.app.exit_key_handler
oldmenu = appuifw.app.menu
oldbody = appuifw.app.body

version = "v 0.31"


display_on_screen('mesg',version + u'Starting')

try:
    f = open(u'e:\\system\\apps\\python\\my\\tracedump.txt','r')
    MainTrace = pickle.load(f)
    f.close()
except:
    MainTrace = []
    appendToTrace('label',"starting" )

display_on_screen('mesg',version + u'Initializing')
g_query_interval = 15
g_max_query_interval = 12*g_query_interval

record_query_interval = 654
record_max_query_interval = 4*record_query_interval

bt_query_interval = 300
bt_max_query_interval = 5*bt_query_interval

record_to_server()

#btprobe = newbt.BtDiscoverLocations( { "001060a6740c":"office" } )
#btprobe.start()

g_timer = e32.Ao_timer()
try_probe_g()

main_lock = e32.Ao_lock()
appuifw.app.menu = [ (u'Probe now',probe_g_now),
		     (u'Change Intervals', changeIntervals),
		     (u'Record to Server', record_to_server ),
		     (u'Show Gps locs', showGps),
		     (u'Show Gsm locs', showGsm),
		     (u'Add GPS device', addGpsDevice),
		     (u'Add Label',addLabel),
		     (u'Change Debug Mode',changeDebugMode),
		     (u'exit',myexit)
		     ]
appuifw.app.exit_key_handler = myexit

display_on_screen('mesg', version + u'Begin Event Loop')
main_lock.wait()
while not exitting:
    e32.ao_yield()
display_on_screen('mesg', u'that is all folks')
appuifw.app.exit_key_handler = oldexit
appuifw.app.menu = oldmenu
appuifw.app.body = oldbody

