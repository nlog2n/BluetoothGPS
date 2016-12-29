# Script to upload tracks recorded with nmea_info.py
#
# Allows you to browse the recorded tracks, and upload them over bluetooth
# When uploading, you have a choice of upload formats:
#  * raw NMEA (as stored)
#  * gpx
#  (more to come)
# You can optionally also delete the file after upload
#
# To get nmea_info.py, see http://gagravarr.org/code/
#
# GPL
#
# Nick Burch - v0.12 (12/05/2007)

# Core imports
import os
import appuifw
import e32
import time
import socket

# So we can compress stuff
import zlib

# All of our preferences live in a dictionary called 'pref'
pref = {}

# Do we have an E: disk (memory card?)
pref['disk'] = 'e:'
if not os.path.exists('e:\\System'):
	pref['disk'] = 'c:'

# Where we expect our files to be
pref['base_dir'] = pref['disk'] + '\\System\\Apps\\NMEA_Info\\'

# Should we default to delete after upload?
pref['delete_after'] = 0;

# What's the default export format?
pref['export_format'] = 'nmea'

#############################################################################

# Ensure our data directory exists
if not os.path.exists(pref['base_dir']):
	os.makedirs(pref['base_dir'])

#############################################################################

appuifw.app.screen='normal'
appuifw.app.title=u'NMEA Uploader'

#############################################################################

def format_latlong(data,nsew):
	"""Turn (H)HHMM.nnnn into HH.ddddddd"""

	# Defaults, in case it all goes horribly wrong
	hours = '0'
	mins = 0.0

	# Check to see if it's HMM.nnnn or HHMM.nnnn or HHHMM.nnnn
	try:
		if data[5:6] == '.':
			hours = data[0:3]
			mins = float(data[3:])
		elif data[3:4] == '.':
			hours = data[0:1]
			mins = float(data[1:])
		else:
			if len(data) >= 3:
				hours = data[0:2]
				mins = float(data[2:])
	except ValueError:
		print "Bad hours and minutes field '%s'" % data

	# Strip off leading 0s
	if hours == '000' or hours == '00' or hours == '0':
		hours = '0'
	else:
		if hours[0:2] == '00':
			hours = hours[2:]
		if hours[0:1] == '0':
			hours = hours[1:]

	# Handle NSEW -> +-
	if nsew == 'S' or nsew == 'W':
		hours = '-' + hours

	dec = mins / 60.0 * 100.0
	# Cap at 6 digits - currently nn.nnnnnnnn
	dec = dec * 10000.0
	str_dec = "%06d" % dec
	return hours + "." + str_dec

def parse_gga(line):
	"""Get the location from a GGA sentence"""
    
	location = {}
	location['time'] = '(unknown)'
	location['valid'] = 0

	# Remove a checksum, if present, and split on ,s
	data = line.split('*')
	d = data[0].split(',')

	if len(d) < 10:
		# Invalid sentence
		return location
	if d[6] == '0':
		# Invalid location
		return location
	else:
		# Good, is a valid location
		pass

	location['valid'] = 1
	location['type'] = 'GGA'
	location['lat'] = "%s" % format_latlong(d[2],d[3])
	location['long'] = "%s" % format_latlong(d[4],d[5])
	location['lat_raw'] = "%s%s" % (d[2],d[3])
	location['long_raw'] = "%s%s" % (d[4],d[5])
	location['alt'] = "%s" % d[9] # d[10] should be M

	# Also grab some fix related information
	try:
		location['num_sats'] = "%d" % int(d[7])
	except ValueError:
		location['num_sats'] = "0"
	location['hdop'] = "%s" % d[8]

	# Format the time
	time = d[1]
	hh = time[0:2]
	mm = time[2:4]
	ss = time[4:]
	location['time'] = "%s:%s:%s" % (hh,mm,ss)

	return location

#############################################################################

_gzip_header = (
	"\037\213" # magic
	"\010" # compression method
	"\000" # flags
	"\000\000\000\000" # time, who cares?
	"\002"
	"\377" )
class GZip:
	"""Helper for writing GZip files, using libz"""
	def __init__(self,out_fd=None):
		self.out_fd = out_fd
		self.started = False
		self.co = zlib.compressobj(9, zlib.DEFLATED, -zlib.MAX_WBITS,
									zlib.DEF_MEM_LEVEL, 0)
		self.len = 0
		self.crc = 0

	def compress(self,data):
		ret = ""
		if not self.started:
			self.started = True
			ret += _gzip_header
		self.len += len(data)
		self.crc = zlib.crc32(data,self.crc)
		ret += self.co.compress(data)
		return ret

	def write(self,data):
		assert self.out_fd != None, "Can only call write if passed a fd when opened"
		self.out_fd.write(self.compress(data))

	def flush(self):
		pass

	def close(self):
		import struct
		closing_data = self.co.flush() + struct.pack("<ll", self.crc, self.len)
		if self.out_fd == None:
			return closing_data
		self.out_fd.write(closing_data)
		self.out_fd.flush()
		self.out_fd.close()

#############################################################################

def compress_file(abs_picked_file, base_name):
	"""Compresses the supplied file, and returns the filename"""

	appuifw.note(u'Compressing',"info")
	
	# Open the NMEA file, read only
	inp_fd = open(abs_picked_file,'r')

	# Open the GZip temp file for writing
	gz_file = "c:\\System\\Temp\\" + base_name + ".txt.gz"
	out_fd = open(gz_file,'w')

	# Start the GZip
	gzip = GZip()

	# Loop over the NMEA file, compressing
	while 1:
		thisline = inp_fd.readline()
		if not thisline:
			break
		out_fd.write(gzip.compress(thisline))

	# Finish up
	out_fd.write( gzip.close() )

	# Close
	out_fd.flush()
	out_fd.close()
	inp_fd.close()

	out_fd = None
	inp_fd = None

	# Ensure everything has caught up
	e32.ao_yield()

	# Return the file name
	return gz_file

#############################################################################

def convert_to_gpx(nmea_file,base_name,compress):
	"""Converts the supplied NMEA file into GPX, and returns the filename"""

	appuifw.note(u'Converting to GPX',"info")

	# Open the NMEA file, read only
	inp_fd = open(nmea_file,'r')

	# Open the GPX temp file for writing
	gpx_file = "c:\\System\\Temp\\" + base_name + ".gpx"
	if compress:
		gpx_file += ".gz"
	out_fd = open(gpx_file,'w')

	# Start the GZip
	if compress:
		out_fd = GZip(out_fd)

	# Decide what date to use - base on file mtime (no ctime on symbian)
	mtime = os.stat(nmea_file)[8]
	mtime_t = time.localtime(mtime)
	date = time.strftime("%Y-%m-%d", mtime_t)

	# Write out the GPX header
	out_fd.write('<?xml version="1.0"?>\n')
	out_fd.write('<gpx\nversion="1.0"\ncreator="upload_track.py - http://gagravarr.org/code/#upload_track"\nxmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\nxmlns="http://www.topografix.com/GPX/1/0"\nxsi:schemaLocation="http://www.topografix.com/GPX/1/0 http://www.topografix.com/GPX/1/0/gpx.xsd">\n')
	out_fd.write('<time>' + time.strftime("%Y-%m-%dT%H:%M:%SZ") + '</time>\n')
	out_fd.write('<trk><trkseg>\n')

	# Loop over the NMEA file, outputting GPX
	while 1:
		thisline = inp_fd.readline()
		if not thisline:
			break
		location = parse_gga(thisline)
		if location['valid']:
			out_fd.write(' <trkpt lat="' + location['lat'] + '" lon="' + location['long'] + '">\n')
			out_fd.write('  <ele>' + location['alt'] + '</ele>\n')
			out_fd.write('  <time>' + date + 'T' + location['time'] + 'Z</time>\n' )
			out_fd.write('  <fix>3d</fix>\n')
			out_fd.write('  <sat>' + location['num_sats'] + '</sat>\n')
			out_fd.write('  <hdop>' + location['hdop'] + '</hdop>\n')
			out_fd.write(' </trkpt>\n')

	# Finish the GPX
	out_fd.write('</trkseg></trk></gpx>\n')

	# Close
	out_fd.flush()
	out_fd.close()
	inp_fd.close()

	out_fd = None
	inp_fd = None

	# Ensure everything has caught up
	e32.ao_yield()

	# Return the file name
	return gpx_file

#############################################################################

files_list = []
files = []

def build_files_list():
	"""Gets a list of all the files that could be uploaded"""
	global files_list
	global files

	# Get the file listing in the directory
	all_files = os.listdir(pref['base_dir'])

	# Exclude files we know came from a .sis install
	files = []
	for file in all_files:
		if (file[-3:] == ".py") or (file[-3:] == ".db") or (file[-4:] == ".aif") or (file[-4:] == ".app") or (file[-4:] == ".rsc"):
			# Skip these files
			pass
		else:
			# Add this one to the list
			files.append(file)

	# Now build something we can give to a listbox based on these
	files_list = []
	for file in files:
		name = unicode(file)
		path = pref['base_dir'] + '\\' + file
		size = os.stat(path)[6]
		size_str = "%4.1f kb" % (size/1024.0)
		files_list.append( (name,unicode(size_str)) )

build_files_list()

#############################################################################

options_values = [
	[ '' ],
	['NMEA','GPX'],
	['No','Yes'],
	['No','Yes'] 
]
options_list = [
	(u'File Name',           unicode('')),
	(u'Format',              unicode(options_values[1][0])),
	(u'Compress',            unicode(options_values[2][0])),
	(u'Delete After Upload', unicode(options_values[3][0]))
]

#############################################################################

picked_file = ''
picking_file = 1

listbox = ''

def ignore_selection():
	"""Listbox helper, that does nothing"""
	pass

def handle_selection(ind=None):
	"""Handle selections in the listbox"""
	global listbox
	global picked_file
	global picking_file
	global options_values
	global options_list

	if not ind == None:
		index = ind
	else:
		index = listbox.current()

	if picking_file:
		picked_file = files[index]
		handle_picked_file()
	else:
		# Set upload options

		# Which option are we on?
		cur_option = options_list[index][1]
		next_idx = 0
		for idx in range(len(options_values[index])):
			pos_option = options_values[index][idx]
			if unicode(pos_option) == cur_option:
				next_idx = idx+1
		if next_idx >= len(options_values[index]):
			next_idx = 0
		options_list[index] = ( options_list[index][0], unicode(options_values[index][next_idx]) )

		# Refresh the display
		set_listbox_to_options(1)

def handle_picked_file():
	"""Handle the stuff once a file has been picked"""
	global picked_file
	global picking_file
	global options_values
	global options_list

	picking_file = 0

	# Pop the filename in as the first option
	options_values[0] = [unicode(picked_file)]
	options_list[0] = (options_list[0][0], unicode(picked_file))

	# New display
	set_listbox_to_options(0)

def handle_upload():
	"""Does the upload, based on the current upload options"""
	global picked_file
	global options_list

	# What format did we opt for?
	format = options_list[1][1]
	# Do they want it compressed?
	compress = options_list[2][1]
	# And should we delete after upload?
	delete = options_list[3][1]

	# Add on the directory
	abs_picked_file = pref['base_dir'] + picked_file

	# Turn compress into a true/false
	if compress == u'Yes':
		compress = True
	else:
		compress = False

	# Do any conversion, as required
	base_name = picked_file[0:-4]
	if format == u'GPX':
		# Convert
		upload_file = convert_to_gpx(abs_picked_file, base_name, compress)
	else:
		if compress:
			upload_file = compress_file(abs_picked_file, base_name)
		else:	
			# Sent the file as-is
			upload_file = abs_picked_file

	# Where do they want it to go?
	bt_addr,services = socket.bt_obex_discover()
	service = services.values()[0]

	# Print out what we're up to
	print "Uploading to %s at service %d" % (bt_addr,service)
	print "File is %s" % upload_file

	# Upload the file
	socket.bt_obex_send_file(bt_addr, service, unicode(upload_file))
	print "Upload completed"

	# If we made a temp file, delete that
	if not upload_file == abs_picked_file:
		os.remove(upload_file)
	
	# Delete, if required
	if delete == u'Yes':
		print "Deleting %s" % abs_picked_file
		os.remove(abs_picked_file)
		build_files_list()

	# All done
	appuifw.note(u'Upload Complete',"info")
	print ""
	set_listbox_to_files_list()

def handle_details():
	"""Show the details of the selected file"""
	global listbox
	global picked_file

	index = listbox.current()
	picked_file = files[index]

	do_handle_details(picked_file)

def do_handle_details(picked_file):
	"""Show the details of the specified file"""
	abs_file = pref['base_dir'] + picked_file

	stat = os.stat(abs_file)

	# Get the size
	size = stat[6]
	size_str = "%4.1f kb" % (size/1024.0)

	# Get the last modified time
	last_mod = time.ctime(stat[8])

	# Open the file
	fd = open(abs_file,'r')
	firstline = fd.readline()
	lastline = ''
	lines = 1
	
	# Get the number of points
	while 1:
		thisline = fd.readline()
		if not thisline:
			break
		lastline = thisline
		lines = lines + 1
	fd.close()
	fd = None

	# Get the oldest timestamp
	first_loc = parse_gga(firstline)

	# Get the newest timestamp
	last_loc = parse_gga(lastline)

	# Build up the display list
	display = [
		(u'File Name', unicode(picked_file)),
		(u'Track Points', unicode(lines)),
		(u'File Size', unicode(size_str)),
		(u'Last Modified', unicode(last_mod)),
		(u'First Track @', unicode(first_loc['time'])),
		(u'Last Track @', unicode(last_loc['time']))
	]

	# Have it displayed
	set_listbox_to_details(display)

def handle_rename_file():
	"""Handle the request to rename a file"""
	global picked_file

	# Prompt them for new name
	str = "Rename %s to?" % picked_file
	new_name = appuifw.query(unicode(str), 'text', u'.txt')

	if new_name != None and len(new_name):
		if not new_name[-4:] == '.txt':
			new_name += '.txt'
		abs_file_name = pref['base_dir'] + picked_file
		new_file_name = pref['base_dir'] + new_name

		if os.path.exists(new_file_name):
			appuifw.note(u"That file already exists", "error")
			handle_rename_file()

		os.rename(abs_file_name,new_file_name)
		build_files_list()
		appuifw.note(u'File renamed',"info")

	set_listbox_to_files_list()

def handle_delete_file():
	"""Handle the request to delete a file"""
	global picked_file

	# Prompt them to confirm
	str = "Really delete %s ?" % picked_file
	ok = appuifw.query(unicode(str), 'query')

	if ok:
		abs_file = pref['base_dir'] + picked_file
		os.remove(abs_file)
		build_files_list()
		appuifw.note(u'File deleted',"info")

	set_listbox_to_files_list()

#############################################################################

# Menu when on the file listing screen
main_menu = [
	(u'Select', lambda: handle_selection(None)),
	(u'Details', handle_details)
]

def set_listbox_to_files_list():
	"""Sets the listbox to be the file list view"""
	global listbox
	global picked_file
	global picking_file

	listbox = appuifw.Listbox(files_list, handle_selection)
	appuifw.app.body = listbox
	appuifw.app.menu = main_menu

	# Reset the picking state
	picked_file = ''
	picking_file = 1

#############################################################################

# Menu when on the upload options screen
upload_menu = [
	(u'Change', lambda: handle_selection(None)), 
	(u'Upload', handle_upload), 
	(u'Details', lambda: do_handle_details(picked_file)),
	(u'Pick Again', set_listbox_to_files_list)
]

def set_listbox_to_options(keep_pos):
	"""Sets the listbox to be the upload options view"""
	global listbox
	global options_list

	if keep_pos:
		# Do a set_list, so we can affect the position
		new_pos = listbox.current()
		listbox.set_list(options_list, new_pos)
	else:
		# Reset the whole list
		listbox = appuifw.Listbox(options_list, handle_selection)
		appuifw.app.body = listbox

	# Change the menu
	appuifw.app.menu = upload_menu

details_menu = [
	(u'Upload', handle_picked_file), 
	(u'Rename', handle_rename_file), 
	(u'Delete', handle_delete_file), 
	(u'Pick Again', set_listbox_to_files_list)
]
def set_listbox_to_details(display):
	"""Sets the listbox to be the details display"""
	global listbox

	listbox = appuifw.Listbox(display, ignore_selection)
	appuifw.app.body = listbox
	appuifw.app.menu = details_menu

#############################################################################

# Get a lock, so we won't just exit
lock = e32.Ao_lock()

# Set up the listbox - start on file list
set_listbox_to_files_list()

# Wait until we're done
running = 1
def request_exit():
	global running
	appuifw.app.exit_key_handler = None
	lock.signal()
	running = 0
appuifw.app.exit_key_handler = request_exit

while running:
	lock.wait()
