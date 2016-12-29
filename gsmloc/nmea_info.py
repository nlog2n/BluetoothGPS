doc = """
Graphical script to talk to a NMEA bluetooth GPS, and display all
 sorts of useful information from it.

Shows where the satellites are in the sky, and what signal strength
 they have (two different views)
Converts your position into OSGB 36 values, and then generates OS
 easting and northing values + six figure grid ref
Also allows you to log your journeys to a file. In future, the logging
 details will be configurable, and you'll be able send this to another
 bluetooth device (eg a computer), but for now this functionality is
 handled by upload_track.py.
Optionally also logs the GSM location to the file used by stumblestore,
 which you can later uplaod with stumblestore to http://gsmloc.org/
Can take photos which have the exif GPS tags, which indicate where and
 when they were taken.

In future, should have a config pannel
In future, the OS co-ords stuff should be made more general, to handle
 other countries
In future, some of the messages out to be translated into other languages

For now, on the main screen, hit * to increase logging frequency, # to
 decrease it, 0 to immediately log a point, and 8 to toggle logging 
 on and off. Use 5 to toggle stumblestore GSM logging on and off
On the Direction Of screen, use 1 and 3 to move between waypoints, 5
 to add a waypoint for the current location, and 8 to delete the
 current waypoint

GPL
  Contributions from Cashman Andrus and Christopher Schmit

Nick Burch - v0.21 (11/03/2007)
"""

# Core imports - special ones occur later
import appuifw
import e32
import e32db
import math
import socket
import time
import os
import sysinfo
import thread
from location import gsm_location

# All of our preferences live in a dictionary called 'pref'
pref = {}


# Default bluetooth address to connect to
# If blank, will prompt you to pick one
pref['def_gps_addr']=''


# How many GGA sentences between logging
# Set to 0 to prevent logging
pref['gga_log_interval'] = 5

# Threshhold change in GGA sentence to log again 
#  (lessens redundant entries while stationary)
# Values for lat and long are in minutes of arc, as stored in 
#  location['lat_dec'] and location['long_dec'].
#  eg 0.00005 is ~5.6 meters at the equator)  
# Value for alt is in meters.
pref['gga_log_min_lat'] = 0.0
pref['gga_log_min_long'] = 0.0
pref['gga_log_min_alt'] = 0.0
#pref['gga_log_min_lat'] = 0.0001
#pref['gga_log_min_long'] = 0.0001
#pref['gga_log_min_alt'] = 6.0

# Where we store our data and settings
pref['base_dir'] = 'e:\\System\\Apps\\NMEA_Info\\'

# File to log GGA sentences into
# May optionally contain macros for datetime elements, as used in
#  time.strftime, eg "file_%y-%m-%d_%H:%M.txt"
# Should end in .txt, so the send script will spot them
pref['gga_log_file'] = pref['base_dir'] + 'nmea_gga_log.txt'
#pref['gga_log_file'] = pref['base_dir'] + 'nmea_gga_log_%y-%m-%d.txt'

# File to log debug info into
pref['debug_log_file'] = ''
#pref['debug_log_file'] = pref['base_dir'] + 'nmea_debug_log_%y-%m-%d.txt'

# DB file to hold waypoints for direction-of stuff
pref['waypoints_db'] = pref['base_dir'] + 'waypoints.db'


# Should we also log GSM+lat+long in the stumblestore log file?
# See http://gsmloc.org/ for more details
pref['gsmloc_logging'] = 0


# We want icons etc
# Set this to 'large' if you want the whole screen used
pref['app_screen'] = 'normal'

# Define title etc
pref['app_title'] = "NMEA Info Disp"

# Default location for "direction of"
pref['direction_of_lat'] = '51.858141'
pref['direction_of_long'] = '-1.480210'
pref['direction_of_name'] = '(default)'

#############################################################################

# Ensure our helper libraries are found
try:
	from geo_helper import *
except ImportError:
	appuifw.note(u"geo_helper.py module wasn't found!\nDownload at http://gagravarr.org/code/", "error")
	print "\n"
	print "Error: geo_helper.py module wasn't found\n"
	print "Please download it from http://gagravarr.org/code/ and install, before using program"
	# Try to exit without a stack trace - doesn't always work!
	import sys
	sys.__excepthook__=None
	sys.excepthook=None
	sys.exit()

has_pexif = None
try:
	from pexif import JpegFile
	has_pexif = True
except ImportError:
	# Will alert them later on
	has_pexif = False

has_camera = None
try:
	import camera
	has_camera = True
except ImportError:
	# Will alert them later on
	has_camera = False


#############################################################################

# Set the screen size, and title
appuifw.app.screen=pref['app_screen']
appuifw.app.title=unicode(pref['app_title'])

#############################################################################

# Ensure our data directory exists
if not os.path.exists(pref['base_dir']):
	os.makedirs(pref['base_dir'])

# Load the settings
# TODO

#############################################################################

waypoints = []
current_waypoint = 0

# Path to DB needs to be in unicode
pref['waypoints_db'] = unicode(pref['waypoints_db'])

def open_waypoints_db():
	"""Open the waypoints DB file, creating if needed"""
	global prefs

	db = e32db.Dbms()
	try:
		db.open(pref['waypoints_db'])
	except:
		# Doesn't exist yet
		db.create(pref['waypoints_db'])
		db.open(pref['waypoints_db'])
		db.execute(u"CREATE TABLE waypoints (name VARCHAR, lat FLOAT, long FLOAT, added TIMESTAMP)")
	return db

def add_waypoint(name,lat,long):
	"""Adds a waypoint to the database"""
	global waypoints
	global current_waypoint

	# Escape the name
	name = name.replace(u"'",u"`")

	# Add to the db
	db = open_waypoints_db()
	sql = "INSERT INTO waypoints (name,lat,long,added) VALUES ('%s',%f,%f,#%s#)" % ( name, lat, long, e32db.format_time(time.time()) )
	print sql
	db.execute( unicode(sql) )
	db.close()

	# We would update the waypoints array, but that seems to cause a 
	#  s60 python crash!
	##waypoints.append( (unicode(name), lat, long) )
	##current_waypoint = len(waypoints) - 1
	current_waypoint = -1

def delete_current_waypoint():
	"""Deletes the current waypoint from the database"""
	global waypoints
	global current_waypoint

	if current_waypoint == 0:
		return
	name = waypoints[current_waypoint][0]

	# Delete from the array
	for waypoint in waypoints:
		if waypoint[0] == name:
			waypoints.remove(waypoint)
	current_waypoint = 0

	# Delete from the db
	db = open_waypoints_db()
	sql = "DELETE FROM waypoints WHERE name='%s'" % ( name )
	print sql
	db.execute( unicode(sql) )
	db.close()

def load_waypoints():
	"""Loads our direction-of waypoints"""
	global waypoints
	global current_waypoint

	# First up, go with the default
	waypoints = []
	waypoints.append( (pref['direction_of_name'],pref['direction_of_lat'],pref['direction_of_long']) )

	# Now load from disk
	db = open_waypoints_db()
	dbv = e32db.Db_view()
	dbv.prepare(db, u"SELECT name, lat, long FROM waypoints ORDER BY name ASC")
	dbv.first_line()
	for i in range(dbv.count_line()):
		dbv.get_line()
		waypoints.append( (dbv.col(1), dbv.col(2), dbv.col(3)) )
		dbv.next_line()
	db.close()

# Load our direction-of waypoints
load_waypoints()

#############################################################################

# This is set to 0 to request a quit
going = 1
# Our current location
location = {}
location['valid'] = 1 # Default to valid, in case no GGA/GLL sentences
# Our current motion
motion = {}
# What satellites we're seeing
satellites = {}
# Warnings / errors
disp_notices = ''
disp_notices_count = 0
# Our last written location (used to detect position changes)
last_location = {}
# Our logging parameters
gga_log_interval = 0
gga_log_count = 0
gga_log_fh = ''
debug_log_fh = ''
gsm_log_fh = ''
# Photo parameters
all_photo_sizes = None
photo_size = None
preview_photo = None
# How many times have we shown the current preview?
photo_displays = 0
# Are we currently (in need of) taking a preview photo?
taking_photo = 0

#############################################################################

# Generate the checksum for some data
# (Checksum is all the data XOR'd, then turned into hex)
def generate_checksum(data):
	"""Generate the NMEA checksum for the supplied data"""
	csum = 0
	for c in data:
		csum = csum ^ ord(c)
	hex_csum = "%02x" % csum
	return hex_csum.upper()

# Format a NMEA timestamp into something friendly
def format_time(time):
	"""Generate a friendly form of an NMEA timestamp"""
	hh = time[0:2]
	mm = time[2:4]
	ss = time[4:]
	return "%s:%s:%s UTC" % (hh,mm,ss)

# Format a NMEA date into something friendly
def format_date(date):
	"""Generate a friendly form of an NMEA date"""
	months = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
	dd = date[0:2]
	mm = date[2:4]
	yy = date[4:6]
	yyyy = int(yy) + 2000
	return "%s %s %d" % (dd, months[(int(mm)-1)], yyyy)

# NMEA data is HHMM.nnnn where nnnn is decimal part of second
def format_latlong(data):
	"""Turn HHMM.nnnn into HH:MM.SS"""

	# Check to see if it's HMM.nnnn or HHMM.nnnn or HHHMM.nnnn
	if data[5:6] == '.':
		# It's HHHMM.nnnn
		hh_mm = data[0:3] + ":" + data[3:5]
		dddd = data[6:]
	elif data[3:4] == '.':
		# It's HMM.nnnn
		hh_mm = data[0:1] + ":" + data[1:3]
		dddd = data[4:]
	else:
		# Assume HHMM.nnnn
		hh_mm = data[0:2] + ":" + data[2:4]
		dddd = data[5:]

	# Turn from decimal into seconds, and strip off last 2 digits
	sec = int( float(dddd) / 100.0 * 60.0 / 100.0 )
	return hh_mm + ":" + str(sec)

def format_latlong_dec(data):
	"""Turn HHMM.nnnn into HH.ddddd"""
	
	# Check to see if it's HMM.nnnn or HHMM.nnnn or HHHMM.nnnn
	if data[5:6] == '.':
		hours = data[0:3]
		mins = float(data[3:])
	elif data[3:4] == '.':
		hours = data[0:1]
		mins = float(data[1:])
	else:
		hours = data[0:2]
		mins = float(data[2:])

	dec = mins / 60.0 * 100.0
	# Cap at 6 digits - currently nn.nnnnnnnn
	dec = dec * 10000.0
	str_dec = "%06d" % dec
	return hours + "." + str_dec

def get_latlong_floats():
	global location
	wgs_lat = location['lat_dec'];
	wgs_long = location['long_dec'];
	if wgs_lat[-1:] == 'S':
		wgs_lat = '-' + wgs_lat;
	if wgs_long[-1:] == 'W':
		wgs_long = '-' + wgs_long;
	wgs_lat = float(wgs_lat[0:-1])
	wgs_long = float(wgs_long[0:-1])

	return (wgs_lat,wgs_long)

#############################################################################

def readline(sock):
	"""Read one single line from the socket"""
	line = ""
	while 1:
		char = sock.recv(1)
		if not char: break
		line += char
		if char == "\n": break
	return line

#############################################################################

def do_gga_location(data):
	"""Get the location from a GGA sentence"""
	global location

	d = data.split(',')
	location['type'] = 'GGA'
	location['lat'] = "%s%s" % (format_latlong(d[1]),d[2])
	location['long'] = "%s%s" % (format_latlong(d[3]),d[4])
	location['lat_dec'] = "%s%s" % (format_latlong_dec(d[1]),d[2])
	location['long_dec'] = "%s%s" % (format_latlong_dec(d[3]),d[4])
	location['lat_raw'] = "%s%s" % (d[1],d[2])
	location['long_raw'] = "%s%s" % (d[3],d[4])
	location['alt'] = "%s %s" % (d[8],d[9])
	location['time'] = format_time(d[0])
	if d[5] == '0':
		location['valid'] = 0
	else:
		location['valid'] = 1

def do_gll_location(data):
	"""Get the location from a GLL sentence"""
	global location

	d = data.split(',')
	location['type'] = 'GLL'
	location['lat'] = "%s%s" % (format_latlong(d[0]),d[1])
	location['long'] = "%s%s" % (format_latlong(d[2]),d[3])
	location['lat_dec'] = "%s%s" % (format_latlong_dec(d[0]),d[1])
	location['long_dec'] = "%s%s" % (format_latlong_dec(d[2]),d[3])
	location['lat_raw'] = "%s%s" % (d[0],d[1])
	location['long_raw'] = "%s%s" % (d[2],d[3])
	location['time'] = format_time(d[4])
	if d[5] == 'A':
		location['valid'] = 1
	elif d[5] == 'V':
		location['valid'] = 0

def do_rmc_location(data):
	"""Get the location from a RMC sentence"""
	global location

	d = data.split(',')
	location['type'] = 'RMC'
	location['lat'] = "%s%s" % (format_latlong(d[2]),d[3])
	location['long'] = "%s%s" % (format_latlong(d[4]),d[5])
	location['lat_dec'] = "%s%s" % (format_latlong_dec(d[2]),d[3])
	location['long_dec'] = "%s%s" % (format_latlong_dec(d[4]),d[5])
	location['lat_raw'] = "%s%s" % (d[2],d[3])
	location['long_raw'] = "%s%s" % (d[4],d[5])
	location['time'] = format_time(d[0])

#############################################################################

def do_gsv_satellite_view(data):
	"""Get the list of satellites we can see from a GSV sentence"""
	global satellites
	d = data.split(',')

	# Are we starting a new set of sentences, or continuing one?
	full_view_in = d[0]
	sentence_no = d[1]
	tot_in_view = d[2]

	if int(sentence_no) == 1:
		satellites['building_list'] = []

	# Loop over the satellites in the sentence, grabbing their data
	sats = d[3:]
	while len(sats) > 0:
		prn_num = sats[0]
		elevation = sats[1]
		azimuth = sats[2]
		sig_strength = sats[3]

		satellites[prn_num] = {
			'prn':prn_num,
			'elevation':elevation,
			'azimuth':azimuth,
			'sig_strength':sig_strength
		}

		satellites['building_list'].append(prn_num)
		sats = sats[4:]

	# Have we got all the details from this set?
	if sentence_no == full_view_in:
		satellites['in_view'] = satellites['building_list']
		satellites['in_view'].sort()
		satellites['building_list'] = []
	# All done

def do_gsa_satellites_used(data):
	"""Get the list of satellites we are using to get the fix"""
	global satellites
	d = data.split(',')

	sats = d[2:13]
	overall_dop = d[14]
	horiz_dop = d[15]
	vert_dop = d[16]

	while (len(sats) > 0) and (not sats[-1]):
		sats.pop()

	satellites['in_use'] = sats
	satellites['in_use'].sort()
	satellites['overall_dop'] = overall_dop
	satellites['horiz_dop'] = horiz_dop
	satellites['vert_dop'] = vert_dop

def do_vtg_motion(data):
	"""Get the current motion, from the VTG sentence"""
	global motion
	d = data.split(',')

	motion['speed'] = d[6] + " kmph"
	motion['true_heading'] = d[0]

	motion['mag_heading'] = ''
	if d[2] and int(d[2]) > 0:
		motion['mag_heading'] = d[2]

#############################################################################

def expand_log_file_name(proto):
	"""Expand a filename prototype, which optionally includes date and time macros."""
	# eg "%y/%m/%d %H:%M"
	expanded = time.strftime(proto, time.localtime(time.time()))
	return expanded

def rename_current_gga_log(new_name):
	"""Swap the current position log, for one with the new name"""
	global pref

	close_gga_log()
	pref['gga_log_file'] = new_name
	init_gga_log()

def init_gga_log():
	"""Initialize the position log, using pref information"""
	global pref
	global gga_log_count
	global gga_log_interval
	global gga_log_fh

	gga_log_count = 0
	gga_log_interval = pref['gga_log_interval']

	if pref['gga_log_file']:
		# Open the GGA log file, in append mode
		gga_log_fh = open(expand_log_file_name(pref['gga_log_file']),'a');
	else:
		# Set the file handle to False
		gga_log_fh = ''

def close_gga_log():
	"""Close the position log file, if it's open"""
	global gga_log_fh
	if gga_log_fh:
		gga_log_fh.flush()
		gga_log_fh.close()
		gga_log_fh = ''

def init_debug_log():
	"""Initialise the debug log, using pref information"""
	global pref
	global debug_log_fh

	if pref['debug_log_file']:
		# Open the debug log file, in append mode
		debug_log_fh = open(expand_log_file_name(pref['debug_log_file']),'a')
		debug_log_fh.write("Debug Log Opened at %s\n" % time.strftime('%H:%M:%S, %Y-%m-%d', time.localtime(time.time())))
	else:
		# Set the file handle to False
		debug_log_fh = ''

def close_debug_log():
	global debug_log_fh
	if debug_log_fh:
		debug_log_fh.write("Debug Log Closed at %s\n" % time.strftime('%H:%M:%S, %Y-%m-%d', time.localtime(time.time())))
		debug_log_fh.close()
		debug_log_fh = ''

def init_stumblestore_gsm_log():
	"""Initialise the stumblestore GSM log file"""
	global gsm_log_fh
	gsm_log_fh = open("E:\\gps.log",'a')
def close_stumblestore_gsm_log():
	global gsm_log_fh
	if gsm_log_fh:
		gsm_log_fh.close()
		gsm_log_fh = ''

#############################################################################

def location_changed(location, last_location):
	"""Checks to see if the location has changed (enough) since the last write"""
	if (not 'lat_dec' in location) or (not 'long_dec' in location):
		return 1
	if (not 'lat_dec' in last_location) or (not 'long_dec' in last_location):
		return 1
	llat = float(location['lat_dec'][:-1])
	llong = float(location['long_dec'][:-1])
	lalt = float(location['alt'][:-2])
	plat = float(last_location['lat_dec'][:-1])
	plong = float(last_location['long_dec'][:-1])
	palt = float(last_location['alt'][:-2])
	if (abs(llat-plat) < pref['gga_log_min_lat']) and (abs(llong-plong) < pref['gga_log_min_long']) and (abs(lalt-palt) < pref['gga_log_min_alt']):
		return 0
	return 1

def gga_log(rawdata):
	"""Periodically log GGA data to a file, optionally only if it has changed"""
	global pref
	global gga_log_count
	global gga_log_interval
	global gga_log_fh
	global location
	global last_location

	# If we have a fix, and the location has changed enough, and
	#  we've waited long enough, write out the current position
	if location['valid']:
		gga_log_count = gga_log_count + 1
		if gga_log_count >= gga_log_interval:
			gga_log_count = 0
			if location_changed(location, last_location):
				if gga_log_fh:
					gga_log_fh.write(rawdata)
				if pref['gsmloc_logging']:
					gsm_stumblestore_log()
				# Save this location, so we can check changes from it
				last_location['lat_dec'] = location['lat_dec']
				last_location['long_dec'] = location['long_dec']
				last_location['alt'] = location['alt']

def debug_log(rawdata):
	"""Log debug data to a file when requested (if enabled)"""
	global debug_log_fh

	if debug_log_fh:
		debug_log_fh.write(rawdata+"\n")

def gsm_stumblestore_log():
	"""Log the GSM location + GPS location to the stumblestore log file"""
	global location
	global gsm_log_fh

	# Ensure we have our log file open
	if not gsm_log_fh:
		init_stumblestore_gsm_log()

	# Grab the details of what cell we're on
	cell = gsm_location()

	# Write this out
	gsm_log_fh.write("%s,%s,%s,%s,%s,%s,%s,%s\n"%(cell[0],cell[1],cell[2],cell[3],sysinfo.signal(),location['lat_raw'],location['long_raw'],time.time()))

# Kick of logging, if required
init_gga_log()
init_debug_log()

#############################################################################

# Lock, so python won't exit during non canvas graphical stuff
lock = e32.Ao_lock()

def exit_key_pressed():
	"""Function called when the user requests exit"""
	global going
	going = 0
	appuifw.app.exit_key_handler = None
	lock.signal()

def callback(event):
	global gga_log_count
	global gga_log_interval
	global current_waypoint
	global waypoints
	global current_state
	global all_photo_sizes
	global photo_size
	global taking_photo
	global pref

	# If they're on the main page, handle changing logging frequency
	if current_state == 'main':
		if event['type'] == appuifw.EEventKeyDown:
			# * -> more frequently
			if event['scancode'] == 42:
				if gga_log_interval > 0:
					gga_log_interval -= 1;
			# # -> less frequently
			if event['scancode'] == 127:
				if gga_log_interval > 0:
					gga_log_interval += 1;
			# 0 -> log a point right now
			if event['scancode'] == 48:
				gga_log_count = gga_log_interval
			# 8 -> toggle on/off
			if event['scancode'] == 56:
				if gga_log_interval > 0:
					gga_log_interval = 0;
				else:
					gga_log_interval = 10;
					gga_log_count = 0;
			# 5 -> toggle stumblestore on/off
			if event['scancode'] == 53:
				if pref['gsmloc_logging']:
					pref['gsmloc_logging'] = 0
				else:
					pref['gsmloc_logging'] = 1
	if current_state == 'direction_of':
		if event['type'] == appuifw.EEventKeyUp:
			# 1 - prev waypoint
			if event['scancode'] == 49:
				current_waypoint = current_waypoint - 1
				if current_waypoint < 0:
					current_waypoint = len(waypoints) - 1
			# 3 - next waypoint
			if event['scancode'] == 51:
				current_waypoint = current_waypoint + 1
				if current_waypoint >= len(waypoints):
					current_waypoint = 0
			# 5 - make this a waypoint
			if event['scancode'] == 53:
				do_add_as_waypoint()
				# No redraw just yet
				return
			# 8 - remove this waypoint
			if event['scancode'] == 56:
				delete_current_waypoint()
	if current_state == 'take_photo':
		if event['type'] == appuifw.EEventKeyUp:
			size_index = 0
			for i in range(len(all_photo_sizes)):
				if photo_size == all_photo_sizes[i]:
					size_index = i

			# 1 - prev resolution
			if event['scancode'] == 49:
				size_index = size_index - 1
				if size_index < 0:
					size_index = len(all_photo_sizes) - 1
				photo_size = all_photo_sizes[size_index]
			# 3 - next resolution
			if event['scancode'] == 51:
				size_index = size_index + 1
				if size_index >= len(all_photo_sizes):
					size_index = 0
				photo_size = all_photo_sizes[size_index]
			# 0 or enter - take photo
			if event['scancode'] == 48 or event['scancode'] == 167:
				# Request the main thread take it
				# (Takes too long to occur in the event thread)
				taking_photo = 2

	# Whatever happens request a re-draw
	draw_state()

def do_nothing(picked):
	"""Does nothing"""

def draw_main():
	global location
	global motion
	global satellites
	global gps_addr
	global gga_log_interval
	global disp_notices
	global disp_notices_count
	global connected

	canvas.clear()
	yPos = 12

	canvas.text( (0,yPos), u'GPS', 0x008000)
	if connected:
		canvas.text( (60,yPos), unicode(gps_addr))
	else:
		canvas.text( (30,yPos), u"-waiting-"+unicode(gps_addr), 0xdd0000)

	yPos += 12
	canvas.text( (0,yPos), u'Time:', 0x008000)
	if not location.has_key('time'):
		cur_time = u'(unavailable)'
	else:
		cur_time = unicode(location['time'])
	canvas.text( (60,yPos), cur_time)

	yPos += 12
	canvas.text( (0,yPos), u'Speed', 0x008000)
	if motion.has_key('speed'):
		cur_speed = unicode(motion['speed'])
	else:
		cur_speed = u'(unavailable)'
	canvas.text( (60,yPos), cur_speed)

	yPos += 12
	canvas.text( (0,yPos), u'Heading', 0x008000)
	if motion.has_key('true_heading'):
		if motion.has_key('mag_heading') and motion['mag_heading']:
			mag = 'True: ' + motion['true_heading']
			mag = mag + '    Mag: ' + motion['mag_heading']
		else:
			mag = motion['true_heading'] + " deg"
		mag = unicode(mag)
	else:
		mag = u'(unavailable)'
	canvas.text( (60,yPos), mag)

	yPos += 12
	canvas.text( (0,yPos), u'Location', 0x008000)
	if location.has_key('alt'):
		canvas.text( (105,yPos), unicode(location['alt']) )
	if (not location.has_key('lat')) or (not location.has_key('long')):
		cur_loc = u'(unavailable)'
	else:
		if location['valid'] == 0:
			cur_loc = u'(invalid location)'
		else:
			cur_loc = unicode(location['lat']) + '  ' + unicode(location['long'])
	canvas.text( (10,yPos+12), cur_loc)

	yPos += 24
	canvas.text( (0, yPos), u'Satellites in view', 0x008000)
	if satellites.has_key('in_view'):
		canvas.text( (105,yPos), unicode( len(satellites['in_view']) ))
		canvas.text( (10,yPos+12), unicode(' '.join(satellites['in_view'])) )
	else:
		canvas.text( (10,yPos+12), u'(unavailable)')

	yPos += 24
	canvas.text( (0, yPos), u'Satellites used', 0x008000)
	if satellites.has_key('in_use'):
		used = len(satellites['in_use'])
		if satellites.has_key('overall_dop'):
			used = str(used) + "  err " + satellites['overall_dop']
		canvas.text( (105,yPos), unicode(used) )
		canvas.text( (10,yPos+12), unicode(' '.join(satellites['in_use'])) )
	else:
		canvas.text( (10,yPos+12), u'(unavailable)')

	yPos += 24
	canvas.text( (0, yPos), u'Logging locations', 0x008000)
	if gga_log_interval > 0:
		logging = unicode(gga_log_interval) + u' secs'
	else:
		logging = u'no'
	if pref['gsmloc_logging']:
		logging = logging + u'  +GSM'
	canvas.text( (105,yPos), logging)

	if not disp_notices == '':
		yPos += 12
		canvas.text( (0,yPos), unicode(disp_notices), 0x000080)
		disp_notices_count = disp_notices_count + 1
		if disp_notices_count > 60:
			disp_notices = ''
			disp_notices_count = 0

def draw_sat_list():
	global satellites

	canvas.clear()
	if not satellites.has_key('in_view'):
		canvas.text( (0,12), u'No satellites in view', 0x008000)
		return

	sats_in_use = []
	if satellites.has_key('in_use'):
		sats_in_use = satellites['in_use']

	pos = 0
	for sat in satellites['in_view']:
		if not satellites.has_key(sat):
			continue
		pos = pos + 12

		# Draw signal strength on back
		# Strength should be between 0 and 99
		str_len = 0
		if (not satellites[sat]['sig_strength'] == '') and (int(satellites[sat]['sig_strength']) > 0):
			str_len = int( 120.0 * float(satellites[sat]['sig_strength']) / 100.0 )
		if str_len > 0:
			canvas.rectangle( [50,pos-10, 50+str_len,pos], outline=0xbb0000, fill=0xbb0000 )

		# Draw info on front. Used satellites get a different colour
		if sat in sats_in_use:
			canvas.text( (0,pos), unicode('Sat ' + sat), 0x00dd00)
		else:
			canvas.text( (0,pos), unicode('Sat ' + sat), 0x003000)
		canvas.text( (50,pos), unicode('e' + satellites[sat]['elevation'] + ' a' + satellites[sat]['azimuth'] + '   sig ' + satellites[sat]['sig_strength'] ) )

	# Display if we have a valid fix or now
	pos = pos + 24
	if pos < 144:
		if location['valid'] == 0:
			canvas.text( (50,pos), u"no position lock", 0x800000)
		else:
			canvas.text( (50,pos), u"valid position", 0x00dd00)

def draw_sat_view():
	global satellites

	canvas.clear()
	if not satellites.has_key('in_view'):
		canvas.text( (0,12), u'No satellites in view', 0x008000)
		return

	# Draw the outer and inner circle
	canvas.ellipse([00,00,150,150], outline=0x000000, width=2)
	canvas.ellipse([45,45,105,105], outline=0x000000, width=1)

	# Draw on N-S, E-W
	canvas.line([75,00,75,150], outline=0x000000, width=1)
	canvas.line([0,75,150,75], outline=0x000000, width=1)
	canvas.text( (72,12), u'N' )

	# Render each of the satelites
	# Elevation in deg, 0=edge, 90=centre
	# Azimuth in deg, 0=top, round clockwise
	for sat in satellites['in_view']:
		if not satellites.has_key(sat):
			continue
		if not satellites[sat]['elevation']:
			continue
		if not satellites[sat]['azimuth']:
			continue

		# Where to draw the point
		x_pos = 75 - 2 # Offset so nice and central
		y_pos = 75 + 6 # Can't write at y=0, so offset everything

		elev = float(satellites[sat]['elevation']) / 360.0 * 2 * math.pi
		azim = float(satellites[sat]['azimuth']) / 360.0 * 2 * math.pi

		# azim gives us round the circle
		# elev gives us how far in or out
		#  (elev=0 -> edge, elev=90 -> centre)

		radius = 75.0 * math.cos(elev)

		y_disp = radius * math.cos(azim)
		x_disp = radius * math.sin(azim)

		x_pos = x_pos + x_disp
		y_pos = y_pos - y_disp # 0 is at the top

		canvas.text( (x_pos,y_pos), unicode(sat), 0x008000 )

def draw_os_data():
	global location

	# We pick up these values as we go
	wgs_height = 0
	wgs_lat = None
	wgs_long = None

	canvas.clear()
	if (not location.has_key('lat')) or (not location.has_key('long')):
		canvas.text( (0,12), u'No location data available', 0x008000)
		return

	yPos = 12
	canvas.text( (0,yPos), u'Location (WGS84)', 0x008000)
	if location.has_key('alt'):
		canvas.text( (105,yPos), unicode(location['alt']) )

		# Remove ' M'
		wgs_height = location['alt']
		wgs_height = wgs_height[0:-1]
		if wgs_height[-1:] == '':
			wgs_height = wgs_height[0:-1]
	if location['valid'] == 0:
		canvas.text( (10,yPos+12), u'(invalid location)' )
	else:
		canvas.text( (10,yPos+12), unicode(location['lat']) )
		canvas.text( (90,yPos+12), unicode(location['long']) )
		yPos += 12
		canvas.text( (10,yPos+12), unicode(location['lat_dec']) )
		canvas.text( (90,yPos+12), unicode(location['long_dec']) )

		# remove N/S E/W
		wgs_ll = get_latlong_floats();
		wgs_lat = wgs_ll[0]
		wgs_long = wgs_ll[1]

	# Convert these values from WGS 84 into OSGB 36
	osgb_data = []
	if (not wgs_lat == None) and (not wgs_long == None):
		osgb_data = turn_wgs84_into_osgb36(wgs_lat,wgs_long,wgs_height)
	# And display
	yPos += 24
	canvas.text( (0,yPos), u'Location (OSGB 36)', 0x008000)
	if osgb_data == []:
		canvas.text( (10,yPos+12), u'(invalid location)' )
	else:
		osgb_lat = "%02.06f" % osgb_data[0]
		osgb_long = "%02.06f" % osgb_data[1]
		canvas.text( (10,yPos+12), unicode(osgb_lat) )
		canvas.text( (90,yPos+12), unicode(osgb_long) )

	# And from OSG36 into easting and northing values
	en = []
	if not osgb_data == []:
		en = turn_osgb36_into_eastingnorthing(osgb_data[0],osgb_data[1])	
	# And display
	yPos += 24
	canvas.text( (0,yPos), u'OS Easting and Northing', 0x008000)
	if en == []:
		canvas.text( (10,yPos+12), u'(invalid location)' )
	else:
		canvas.text( (10,yPos+12), unicode('E ' + str(int(en[0]))) )
		canvas.text( (90,yPos+12), unicode('N ' + str(int(en[1]))) )

	# Now do 6 figure grid ref
	yPos += 24
	canvas.text( (0,yPos), u'OS 6 Figure Grid Ref', 0x008000)
	if en == []:
		canvas.text( (10,yPos+12), u'(invalid location)' )
	else:
		six_fig = turn_easting_northing_into_six_fig(en[0],en[1])
		canvas.text( (10,yPos+12), unicode(six_fig) )

	# Now do the speed in mph
	yPos += 24
	canvas.text( (0,yPos), u'Speed', 0x008000)
	done_speed = 0
	if motion.has_key('speed'):
		space_at = motion['speed'].find(' ')
		if space_at > 1:
			speed = float( motion['speed'][0:space_at] )
			speed_mph = speed / 8.0 * 5.0
			mph_speed = "%0.2f mph" % speed_mph

			canvas.text( (10,yPos+12), unicode(mph_speed))
			canvas.text( (90,yPos+12), unicode(motion['speed']))
			done_speed = 1
	if done_speed == 0:
		cur_speed = u'(unavailable)'
		canvas.text( (10,yPos+12), u'(unavailable)')

def draw_direction_of():
	global current_waypoint
	global new_waypoints
	global waypoints
	global location
	global motion
	global pref

	canvas.clear()
	if (not location.has_key('lat')) or (not location.has_key('long')):
		canvas.text( (0,12), u'No location data available', 0x008000)
		return
	if (not motion.has_key('true_heading')):
		canvas.text( (0,12), u'No movement data available', 0x008000)
		return

	# Do we need to refresh the list?
	if current_waypoint == -1:
		load_waypoints()
		current_waypoint = len(waypoints)-1

	# Grab the waypoint of interest
	waypoint = waypoints[current_waypoint]

	# Ensure we're dealing with floats
	direction_of_lat = float(waypoint[1])
	direction_of_long = float(waypoint[2])

	wgs_ll = get_latlong_floats();
	wgs_lat = wgs_ll[0]
	wgs_long = wgs_ll[1]

	# How far is it to where we're going?
	dist_bearing = calculate_distance_and_bearing(wgs_lat,wgs_long,direction_of_lat,direction_of_long)
	if dist_bearing[0] > 100000:
		distance = "%4d km" % (dist_bearing[0]/1000.0)
	else:
		if dist_bearing[0] < 2000:
			distance = "%4d m" % dist_bearing[0]
		else:
			distance = "%3.02f km" % (dist_bearing[0]/1000.0)
	bearing = dist_bearing[1]
	if bearing < 0:
		bearing = bearing + 360
	bearing = "%03d" % bearing
	heading = "%03d" % float(motion['true_heading'])

	# Display
	yPos = 12
	canvas.text( (0,yPos), u'Location (WGS84)', 0x008000)
	if location['valid'] == 0:
		canvas.text( (10,yPos+12), u'(invalid location)' )
	else:
		canvas.text( (10,yPos+12), unicode(location['lat_dec']) )
		canvas.text( (90,yPos+12), unicode(location['long_dec']) )

	# Where are we going?
	yPos += 24
	canvas.text( (0,yPos), u'Heading to (WGS84)', 0x008000)
	heading_lat = "%02.06f" % direction_of_lat
	heading_long = "%02.06f" % direction_of_long
	canvas.text( (10,yPos+12), unicode(heading_lat) )
	canvas.text( (90,yPos+12), unicode(heading_long) )

	# Draw our big(ish) circle
	#  radius of 45, centered on 55,95
	canvas.ellipse([10,50,100,140], outline=0x000000, width=2)
	canvas.point([55,95], outline=0x000000, width=1)

	def do_line(radius,angle):
		rads = float( angle ) / 360.0 * 2.0 * math.pi
		radius = float(radius)
		t_x = radius * math.sin(rads) + 45 + 10
		t_y = -1.0 * radius * math.cos(rads) + 45 + 50 
		b_x = radius * math.sin(rads + math.pi) + 45 + 10
		b_y = -1.0 * radius * math.cos(rads + math.pi) + 45 + 50
		return (t_x,t_y,b_x,b_y)


	# What't this waypoint called?
	canvas.text( (110,60), unicode(waypoint[0]), 0x000080)

	# How far, and what dir?
	canvas.text( (110,72), u'Distance', 0x008000)
	canvas.text( (110,84), unicode(distance) )
	canvas.text( (110,96), u'Cur Dir', 0x008000)
	canvas.text( (110,108), unicode(heading) )
	canvas.text( (110,120), u'Head In', 0x008000)
	canvas.text( (110,132), unicode(bearing), 0x800000 )

	# The way we are going is always straight ahead
	# Draw a line + an arrow head
	canvas.line([55,50,55,140], outline=0x000000,width=3)
	canvas.line([55,50,60,55], outline=0x000000,width=3)
	canvas.line([55,50,50,55], outline=0x000000,width=3)

	# Make sure the true heading is a float
	true_heading = float(motion['true_heading'])

	# Draw NS-EW lines, relative to current direction
	ns_coords = do_line(45, 0 - true_heading)
	ew_coords = do_line(45, 0 - true_heading + 90)

	n_pos = do_line(49, 0 - true_heading)
	e_pos = do_line(49, 0 - true_heading + 90)
	s_pos = do_line(49, 0 - true_heading + 180)
	w_pos = do_line(49, 0 - true_heading + 270)

	canvas.line( ns_coords, outline=0x008000, width=2)
	canvas.line( ew_coords, outline=0x008000, width=2)
	canvas.text( (n_pos[0]-2,n_pos[1]+4), u'N', 0x008000 )
	canvas.text( (s_pos[0]-2,s_pos[1]+4), u'S', 0x008000 )
	canvas.text( (e_pos[0]-2,e_pos[1]+4), u'E', 0x008000 )
	canvas.text( (w_pos[0]-2,w_pos[1]+4), u'W', 0x008000 )

	# Draw on the aim-for line
	# Make it relative to the heading
	bearing_coords = do_line(45, dist_bearing[1] - true_heading)
	b_a_coords = do_line(40, dist_bearing[1] - true_heading + 8)
	b_b_coords = do_line(40, dist_bearing[1] - true_heading - 8)
	b_a = (bearing_coords[0],bearing_coords[1],b_a_coords[0],b_a_coords[1])
	b_b = (bearing_coords[0],bearing_coords[1],b_b_coords[0],b_b_coords[1])

	canvas.line( bearing_coords, outline=0x800000, width=2)
	canvas.line( b_a, outline=0x800000, width=2)
	canvas.line( b_b, outline=0x800000, width=2)

def draw_take_photo():
	global location
	global all_photo_sizes
	global photo_size
	global preview_photo
	global photo_displays
	global taking_photo

	canvas.clear()

	# Do we have pexif?
	if not has_pexif:
		canvas.text( (0,12), u'pexif not found', 0x800000)
		canvas.text( (0,36), u'Please download and install', 0x800000)
		canvas.text( (0,48), u'so photos can be gps tagged', 0x800000)
		canvas.text( (0,72), u'http://benno.id.au/code/pexif/', 0x008000)
		return

	# Grab photo sizes if needed
	if all_photo_sizes == None:
		all_photo_sizes = camera.image_sizes()
		photo_size = all_photo_sizes[0]

	# Display current photo resolution and fix
	yPos = 12
	canvas.text( (0,yPos), u'Location (WGS84)', 0x008000)
	if location['valid'] == 0:
		canvas.text( (10,yPos+12), u'(invalid location)' )
	else:
		canvas.text( (10,yPos+12), unicode(location['lat_dec']) )
		canvas.text( (90,yPos+12), unicode(location['long_dec']) )
	yPos += 24

	canvas.text( (0,yPos), u'Resolution', 0x008000)
	canvas.text( (90,yPos), unicode(photo_size))
	yPos += 12

	# Display a photo periodically
	if (taking_photo == 0) and (photo_displays > 15 or preview_photo == None):
		taking_photo = 1

	# Only increase the count after the photo's taken
	if (taking_photo == 0):
		photo_displays = photo_displays + 1

	# Only display if we actually have a photo to show
	if not preview_photo == None:
		canvas.blit(preview_photo,target=(5,yPos))


# Handle config entry selections
config_lb = ""
def config_menu():
	# Do nothing for now
	global config_lb
	global canvas
	appuifw.body = canvas

# Select the right draw state
current_state = 'main'
def draw_state():
	"""Draw the currently selected screen"""
	global current_state
	if current_state == 'sat_list':
		draw_sat_list()
	elif current_state == 'sat_view':
		draw_sat_view()
	elif current_state == 'os_data':
		draw_os_data()
	elif current_state == 'direction_of':
		draw_direction_of()
	elif current_state == 'take_photo' and has_camera:
		draw_take_photo()
	else:
		draw_main()

# Menu selectors
def pick_main():
	global current_state
	current_state = 'main'
	draw_state()
def pick_sat_list():
	global current_state
	current_state = 'sat_list'
	draw_state()
def pick_sat_view():
	global current_state
	current_state = 'sat_view'
	draw_state()
def pick_os_data():
	global current_state
	current_state = 'os_data'
	draw_state()
def pick_direction_of():
	global current_state
	current_state = 'direction_of'
	draw_state()
def pick_take_photo():
	global current_state
	current_state = 'take_photo'
	draw_state()
def pick_config():
	"""TODO: Make me work!"""
	global config_lb
	config_entries = [ u"GPS", u"Default GPS",
		u"Logging Interval", u"Default Logging" ]
	#config_lb = appuifw.Listbox(config_entries,config_menu)
	#appuifw.body = config_lb
	appuifw.note(u'Configuration menu not yet supported!\nEdit script header to configure',"info")
def pick_upload():
	"""TODO: Implement me!"""
	appuifw.note(u'Please use upload_track.py\nSee http://gagravarr.org/code/', "info")
def pick_new_file():
	do_pick_new_file(u"_nmea.txt")
def do_pick_new_file(def_name):
	global pref

	# Get new filename
	new_name = appuifw.query(u"Name for new file?", "text", def_name)

	if len(new_name) > 0:
		# Check it doesn't exist
		new_file_name = pref['base_dir'] + new_name
		if os.path.exists(new_file_name):
			appuifw.note(u"That file already exists", "error")
			pick_new_file(new_name)
	
		# Rename
		rename_current_gga_log(new_file_name)
		appuifw.note(u"Now logging to new file")

def do_add_as_waypoint():
	"""Prompt for a name, then add a waypoint for the current location"""
	global location

	name = appuifw.query(u'Waypoint name?', 'text')
	if name:
		wgs_ll = get_latlong_floats();
		lat = wgs_ll[0]
		long = wgs_ll[1]

		add_waypoint(name, lat, long)
		appuifw.note(u'Waypoint Added','info')

#############################################################################

# Decide where to connect to
if not pref['def_gps_addr'] == '':
	gps_addr = pref['def_gps_addr']
	target=(gps_addr,1)

	# Alert them to the GPS we're going to connect to automatically
	appuifw.note(u"Will connect to GPS %s" % gps_addr, 'info')
else:
	# Prompt them to select a bluetooth GPS
	gps_addr,services=socket.bt_discover()
	target=(gps_addr,services.values()[0])

# Not yet connected
connected = 0

#############################################################################

# Enable these displays, no all prompts are over
canvas=appuifw.Canvas(event_callback=callback,
		redraw_callback=lambda rect:draw_state())
appuifw.app.body=canvas

# TODO: Make canvas and Listbox co-exist without crashing python
appuifw.app.menu=[
	(u'Main Screen',pick_main), (u'Satellite List',pick_sat_list), 
	(u'Satellite View',pick_sat_view), (u'OS Data',pick_os_data),
	(u'Direction Of',pick_direction_of), (u'Take Photo',pick_take_photo),
	(u'Upload',pick_upload), (u'Configuration',pick_config), 
	(u'New Log File', pick_new_file)]

#############################################################################

# Start the lock, so python won't exit during non canvas graphical stuff
lock = e32.Ao_lock()

# Loop while active
appuifw.app.exit_key_handler = exit_key_pressed
while going == 1:
	# Connect to the GPS, if we're not already connected
	if not connected:
		try:
			# Connect to the bluetooth GPS using the serial service
			sock = socket.socket(socket.AF_BT, socket.SOCK_STREAM)
			sock.connect(target)
			connected = 1
			debug_log("CONNECTED to GPS: target=%s at %s" % (str(target), time.strftime('%H:%M:%S', time.localtime(time.time()))))
			disp_notices = "Connected to GPS."
			appuifw.note(u"Connected to the GPS")
		except socket.error, inst:
			connected = 0
			disp_notices = "Connect to GPS failed.  Retrying..."
			#appuifw.note(u"Could not connected to the GPS. Retrying in 5 seconds...")
			#time.sleep(5)
			continue

	# Take a preview photo, if they asked for one
	# (Need to do it in this thread, otherwise it screws up the display)
	if taking_photo == 1:
		new_photo = camera.take_photo(mode='RGB12', size=(160,120), 
									flash='none', zoom=0, exposure='auto', 
									white_balance='auto', position=0)
		preview_photo = new_photo
		if taking_photo == 1:
			# In case they requested a photo take while doing the preview
			taking_photo = 0
		photo_displays = 0
	# Take a real photo, and geo-tag it
	# (Need to do it in this thread, otherwise it screws up the display)
	if taking_photo == 2:
		new_photo = camera.take_photo(mode='RGB16', size=photo_size,
									flash='none', zoom=0, exposure='auto', 
									white_balance='auto', position=0)
		# Write out
		filename = "E:\\Images\\GPS-%d.jpg" % int(time.time())
		new_photo.save(filename, format='JPEG',
							quality=75, bpp=24, compression='best')
		# Grab the lat and long, and trim to 4dp
		# (Otherwise we'll cause a float overflow in pexif)
		wgs_ll = get_latlong_floats();
		print "Tagging as %s %s" % (wgs_ll[0],wgs_ll[1])
		# Geo Tag it
		geo_photo = JpegFile.fromFile(filename)
		geo_photo.set_geo( wgs_ll[0], wgs_ll[1] )
		geo_photo.writeFile(filename)
		# Done
		appuifw.note(u"Taken photo", 'info')
		taking_photo = 0

	# If we are connected to the GPS, read a line from it
	if connected:
		try:
			rawdata = readline(sock)
		except socket.error, inst:
			# GPS has disconnected, bummer
			connected = 0
			debug_log("DISCONNECTED from GPS: socket.error %s at %s" % (str(inst), time.strftime('%H:%M:%S, %Y-%m-%d', time.localtime(time.time()))))
			location = {}
			location['valid'] = 1
			appuifw.note(u"Disconnected from the GPS. Retrying...")
			continue

		# Try to process the data from the GPS
		# If it's gibberish, skip that line and move on
		# (Not all bluetooth GPSs are created equal....)
		try:
			data = rawdata.strip()

			# Discard fragmentary sentences -  start with the last '$'
			startsign = rawdata.rfind('$')
			data = data[startsign:]

			# Ensure it starts with $GP
			if not data[0:3] == '$GP':
				continue

			# If it has a checksum, ensure that's correct
			# (Checksum follows *, and is XOR of everything from
			#  the $ to the *, exclusive)
			if data[-3] == '*':
				exp_checksum = generate_checksum(data[1:-3])
				if not exp_checksum == data[-2:]:
					disp_notices = "Invalid checksum %s, expecting %s" % (data[-2:], exp_checksum)
					continue
				
				# Strip the checksum
				data = data[:-3]

			# Grab the parts of the sentence
			talker = data[1:3]
			sentence_id = data[3:6]
			sentence_data = data[7:]

			# Do we need to re-draw the screen?
			redraw = 0

			# The NMEA location sentences we're interested in are:
			#  GGA - Global Positioning System Fix Data
			#  GLL - Geographic Position
			#  RMC - GPS Transit Data
			if sentence_id == 'GGA':
				do_gga_location(sentence_data)
				redraw = 1

				# Log GGA packets periodically
				gga_log(rawdata)
			if sentence_id == 'GLL':
				do_gll_location(sentence_data)
				redraw = 1
			if sentence_id == 'RMC':
				do_rmc_location(sentence_data)
				redraw = 1

			# The NMEA satellite sentences we're interested in are:
			#  GSV - Satellites in view
			#  GSA - Satellites used for positioning
			if sentence_id == 'GSV':
				do_gsv_satellite_view(sentence_data)
				redraw = 1
			if sentence_id == 'GSA':
				do_gsa_satellites_used(sentence_data)
				redraw = 1

			# The NMEA motion sentences we're interested in are:
			#  VTG - Track made good
			# (RMC - GPS Transit - only in knots)
			if sentence_id == 'VTG':
				do_vtg_motion(sentence_data)
				redraw = 1

		# Catch exceptions cased by the GPS sending us crud
		except (RuntimeError, TypeError, NameError, ValueError, ArithmeticError, LookupError, AttributeError), inst:
			print "Exception: %s" % str(inst)
			debug_log("EXCEPTION: %s" % str(inst))

		# Update the state display
		if redraw == 1:
			draw_state()

else:
	# All done
	sock.close()
	close_gga_log()
	close_debug_log()
	close_stumblestore_gsm_log()

print "All done"
#appuifw.app.set_exit()
