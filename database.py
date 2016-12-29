#
#    The database looks as follows:
#    Time Type Id Val_1 Val_2
#
#              where type: GPS, CellTower, BlueTooth, Activity
#|   and the id is an index into the appropriate table
#        GPS:       Lat Lon (two floating point numbers)
#                (the speed and direction are in the raw data record)
#        CellTower: CountyCode Region Cell Tower (four integers)
#        BlueTooth  BT_ID (which is 12 char), bt_name (which is 20 char max) 
#        Label:    Label (which is a string)
#        Activity: String
#
#
#+-----------------------+
#| Tables_in_mine_myself |
#+-----------------------+
#| activity              |
#| bluetooth             |
#| celltowers            |
#| gps                   |
#| label                 |
#| raw_log               |
#| speed_dir             |
#| tower_location        |
#+-----------------------+
#mysql> describe activity;
#+---------+---------+------+-----+---------+----------------+
#| Field   | Type    | Null | Key | Default | Extra          |
#+---------+---------+------+-----+---------+----------------+
#| id      | int(11) |      | PRI | NULL    | auto_increment |
#| name    | int(11) |      |     | 0       |                |
#| param_1 | int(11) | YES  |     | NULL    |                |
#| param_2 | int(11) | YES  |     | NULL    |                |
#+---------+---------+------+-----+---------+----------------+
#4 rows in set (0.00 sec)
#
#mysql> describe bluetooth;
#+---------+-------------+------+-----+---------+----------------+
#| Field   | Type        | Null | Key | Default | Extra          |
#+---------+-------------+------+-----+---------+----------------+
#| id      | int(11)     |      | PRI | NULL    | auto_increment |
#| bt_id   | varchar(12) | YES  |     | NULL    |                |
#| bt_name | varchar(20) | YES  |     | NULL    |                |
#+---------+-------------+------+-----+---------+----------------+
#3 rows in set (0.00 sec)
#
#mysql> create table bluetooth_devices (id INT AUTO_INCREMENT NOT NULL, primary key (id), bt_id varchar(12), bt_name varchar(20), my_name varchar(32), dev_type varchar(8));
#mysql> describe bluetooth_devices;
#+----------+-------------+------+-----+---------+----------------+
#| Field    | Type        | Null | Key | Default | Extra          |
#+----------+-------------+------+-----+---------+----------------+
#| id       | int(11)     |      | PRI | NULL    | auto_increment |
#| bt_id    | varchar(12) | YES  |     | NULL    |                |
#| bt_name  | varchar(20) | YES  |     | NULL    |                |
#| my_name  | varchar(32) | YES  |     | NULL    |                |
#| dev_type | varchar(8)  | YES  |     | NULL    |                |
#+----------+-------------+------+-----+---------+----------------+
#   my_name is my personal name of the device whereas bt_name is the owner's name 
#   dev_type is 'unknown', 'person', 'place', 'thing'
#
#mysql> describe celltowers;
#+----------+---------+------+-----+---------+----------------+
#| Field    | Type    | Null | Key | Default | Extra          |
#+----------+---------+------+-----+---------+----------------+
#| id       | int(11) |      | PRI | NULL    | auto_increment |
#| country  | int(11) | YES  |     | NULL    |                |
#| network  | int(11) | YES  |     | NULL    |                |
#| location | int(11) | YES  |     | NULL    |                |
#| cell     | int(11) | YES  |     | NULL    |                |
#+----------+---------+------+-----+---------+----------------+
#5 rows in set (0.00 sec)
#mysql> describe gps;
#+-------+---------------+------+-----+---------+----------------+
#| Field | Type          | Null | Key | Default | Extra          |
#+-------+---------------+------+-----+---------+----------------+
#| id    | int(11)       |      | PRI | NULL    | auto_increment |
#| lat   | varchar(10)   |      |     | 0       |                |
#| lon   | varchar(10)   |      |     | 0       |                |
#+-------+---------------+------+-----+---------+----------------+
#3 rows in set (0.00 sec)
#
#mysql> describe label;
#+--------+-------------+------+-----+---------+----------------+
#| Field  | Type        | Null | Key | Default | Extra          |
#+--------+-------------+------+-----+---------+----------------+
#| id     | int(11)     |      | PRI | NULL    | auto_increment |
#| string | varchar(64) | YES  |     | NULL    |                |
#+--------+-------------+------+-----+---------+----------------+
#2 rows in set (0.00 sec)
#
#mysql> describe raw_log;
#+---------+------------+------+-----+-------------------+----------------+
#| Field   | Type       | Null | Key | Default           | Extra          |
#+---------+------------+------+-----+-------------------+----------------+
#| id      | int(11)    |      | PRI | NULL              | auto_increment |
#| time    | timestamp  | YES  |     | CURRENT_TIMESTAMP |                |
#| type    | varchar(8) |      |     |                   |                |
#| type_id | int(11)    |      |     | 0                 |                |
#| val_1   | int(11)    | YES  |     | NULL              |                |
#| val_2   | int(11)    | YES  |     | NULL              |                |
#+---------+------------+------+-----+-------------------+----------------+
#6 rows in set (0.01 sec)
#
#mysql> describe speed_dir;
#+-----------+---------------+------+-----+---------+----------------+
#| Field     | Type          | Null | Key | Default | Extra          |
#+-----------+---------------+------+-----+---------+----------------+
#| id        | int(11)       |      | PRI | NULL    | auto_increment |
#| speed     | varchar(10)   | YES  |     | NULL    |                |
#| dir       | varchar(10)   | YES  |     | NULL    |                |
#+-----------+---------------+------+-----+---------+----------------+
#3 rows in set (0.02 sec)
#
#mysql> describe tower_location;
#+------------+---------+------+-----+---------+----------------+
#| Field      | Type    | Null | Key | Default | Extra          |
#+------------+---------+------+-----+---------+----------------+
#| id         | int(11) |      | PRI | NULL    | auto_increment |
#| cell_tower | int(11) | YES  |     | NULL    |                |
#| gps        | int(11) | YES  |     | NULL    |                |
#+------------+---------+------+-----+---------+----------------+
#3 rows in set (0.02 sec)
#
#create table raw_log (id INT AUTO_INCREMENT NOT NULL, primary key (id), time TIMESTAMP, type varchar(8) NOT NULL, type_id INT NOT NULL, val_1 INT, val_2 INT); 
#
#update bluetooth set bt_name = "Larry OrgThinkPad" where ( bt_id = "001060a67435");




import MySQLdb
import time
import sys
import pickle
import types
import pdb

def connect_to_db():
    conn = None
    try:
	conn = MySQLdb.connect(host="localhost",
                           user="root",
                           passwd="sniggle",
                           db="mine_myself")
    except MySQLdb.Error, e:
	print "Error %d: %s" % (e.args[0], e.args[1])
	sys.exit(1)
    return conn


def celltower_id( ct ):
    """ ct is a two or four tuple.  Look it up to see if it 
        is in database (cell tower).  If no, insert it.
	Return id of cell tower"""
    if len(ct) == 2: ct = (310,260,ct[0],ct[1])
    print "in celltowers:",ct,
    cursor.execute("select id from celltowers where (country = %s and network = %s and location = %s and cell = %s)",ct)
    if int(cursor.rowcount) > 0: 
	id = str(cursor.fetchone()[0])
	print 'did not insert'
    else:	# insert missing cell tower
	cursor.execute("insert into celltowers (country, network, location, cell) values (%s, %s, %s, %s)",ct)
	id = str(cursor.lastrowid)
	print '********* inserted'
    return id

def gps_id( lat, lon ):
    lat = float(lat)
    lon = float(lon)
    s_lat = "%.6f"%lat
    s_lon = "%.6f"%lon
    print 'gps_id: ',lat,s_lat,lon,s_lon
    cursor.execute("select id from gps where (lat = %s and lon = %s)",(s_lat,s_lon))
    print "gps_id:",s_lat,s_lon,
    if int(cursor.rowcount) > 0: 
	id = str(cursor.fetchone()[0])
	print "did not insert"
    else:	
	print "********** inserted (%s, %s)"%(s_lat,s_lon)
	cursor.execute("insert into gps (lat, lon) values (%s, %s)",(s_lat,s_lon))
	id = str(cursor.lastrowid)
    return id

def speed_dir_id( speed, dir ):
    print 'speed_dir',speed,dir,
    s_speed = "%.6f"%speed
    s_dir = "%.6f"%dir
    cursor.execute("select id from speed_dir where (speed = %s and dir= %s)",(s_speed,s_dir))
    if int(cursor.rowcount) > 0: 
	id = str(cursor.fetchone()[0])
	print " did not insert"
    else:      
	print "******** inserted (%s, %s)"%(s_speed,s_dir)
	cursor.execute("insert into speed_dir (speed,dir) values (%s , %s)",(s_speed,s_dir))
	id = str(cursor.lastrowid)
    return id
    
def bluetooth_id( bt_id ):
    """ bt_id is a single value.  Look it up to see if it 
        is in database.  If not, insert it.
	Return id in either case"""
    bt_id = bt_id.encode('ascii')
    print "bluetooth_id ",
    cursor.execute("select id from bluetooth_devices where bt_id = %s",bt_id)
    if int(cursor.rowcount) > 0:
	id = str(cursor.fetchone()[0])
	print 'did not insert %s',bt_id
    else:
	cursor.execute("insert into bluetooth_devices (bt_id,bt_name,my_name,dev_type) values (%s,%s,%s,%s)",(bt_id,"","","unknown"))
	id = str(cursor.lastrowid)
	print ' ********* inserted ********'
    return id

def label_id( label ):
    cursor.execute("select id from label where string = %s",label)
    if int(cursor.rowcount) > 0:
	id = str(cursor.fetchone()[0])
    else:
	cursor.execute("insert into label (string) values (%s)",label)
	id = str(cursor.lastrowid)
    return id

def activity_id( act, param_1=-1, param_2=-1 ):
    cursor.execute("select id from activity where (name = %d and param_1 = %d and param_2 = %d)",(act,param_1,param_2))
    if int(cursor.rowcount) > 0:
	id = str(cursor.fetchone()[0])
    else:
	cursor.execute("insert into activity (name, param_1, param_2) values (%d,%d,%d)",(act,param_1,param_2))
	id = str(cursor.lastrowid)
    return id
    
def tower_location( cid, gid ):
    cursor.execute("select id from tower_location where (cell_tower = %s and gps = %s)",(cid,gid))
    if int(cursor.rowcount) > 0:
	id = str(cursor.fetchone()[0])
    else:
	cursor.execute("insert into tower_location  (cell_tower, gps) values (%s,%s)",(cid,gid))
	id = str(cursor.lastrowid)
    return id
    


def insert_raw( timestamp, type, type_id, val_1 = -1, val_2 = -1 ):
    cursor.execute("select id from raw_log where (time = %s and type = %s and type_id = %s and val_1 = %s and val_2 = %s)",(timestamp, type, type_id, val_1,val_2 ))
    if int(cursor.rowcount) > 0:
	id = str(cursor.fetchone()[0])
	print "did not insert"
    else:
	cursor.execute("insert into raw_log (time, type, type_id, val_1, val_2) values (%s,%s,%s,%s,%s)",(timestamp, type, type_id, val_1,val_2 ))
	print "insert into raw_log (time, type, type_id, val_1, val_2) values (%s,%s,%s,%s,%s)"%(timestamp, type, type_id, val_1,val_2 )
	id = str(cursor.lastrowid)
    return id

def update_bt_record(bt_id,new_bt_name=None,new_my_name=None,new_dev_type=None):
    # assume bt_id is non-null
    print 'update bt record',bt_id,new_bt_name,new_my_name,new_dev_type
    pythonbt_id = bt_id.encode('ascii')
	
    cursor.execute("select id,bt_name,my_name,dev_type from bluetooth_devices where bt_name = %s",bt_id)
    if int(cursor.rowcount) <= 0:
	print 'no bt record found'
	if new_bt_name == None: new_bt_name = bt_id
	if new_my_name == None: new_my_name = ""
	if new_dev_type == None: new_dev_type = "unknown"
	cursor.execute("insert into bluetooth_devices (bt_id,bt_name,my_name,dev_type) values (%s, %s,%s,%s)",(bt_id,new_bt_name,new_my_name,'unknown'))
	print '*******************  inserted *********'
    else:
	row = cursor.fetchone()
	print 'update bt record row:',row
	(id,bt_name,my_name,dev_type) = (row[0],row[1],row[2],row[3])

	if new_bt_name == None: new_bt_name = bt_name
	if new_my_name == None: new_my_name = my_name
	if new_dev_type == None: new_dev_type = dev_type
	cursor.execute("update bluetooth_devices set (bt_name = %s, my_name = %s, dev_type = %s) where ( id = %s)",(new_bt_name,new_my_name,new_dev_type,id))
	print 'uuuuuuuuuuuu  updated uuuuu'

def mycvt(dm):
        if type(dm) == types.StringType:
                dm = float(dm)
        D = int(dm/100)
        mm = dm-D*100
        m = mm/60
        return float(D+m)



def process_logs():
    f = open('logs.txt', 'r')
    raw = pickle.load(f)
    # format for a row list is [timestamp, tower_id, lat, long, speed, course]
    rows = []
    for record in raw:
	process_record(record)

### gps: gps only
#   gsc: gps with speed&direction
#   gpm: gps + gsm , to locate cell tower locations
#   gsm: gsm only

def process_record(record):
	print '                     processing record:',record
	(t,tag,g) = record
#        timestamp = time.strftime("%Y-%m-%d %H:%M:%S",time.gmtime(t))
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(t))
        if tag == 'gps':
	     
	    gid = gps_id( mycvt( g[0] ), -mycvt( g[1])  )
#	    insert_raw( timestamp, 'gps', gid , None, None )
	    insert_raw( timestamp, 'gps', gid )

        elif tag == 'gsc':
	    lat,lon = ( mycvt(g[0]), -mycvt(g[1]) )
	    gid = gps_id( lat, lon )
	    sid = speed_dir_id( g[2], g[3] )
#	    insert_raw( timestamp, 'gsc', gid , sid, None )
	    insert_raw( timestamp, 'gsc', gid , sid)

        elif tag == 'gpm':
	    (gg,cc) = g
	    cid = celltower_id( cc )
	    gid = gps_id( mycvt( gg[0] ), -mycvt( gg[1])  )
	    tower_location( cid, gid )
	    insert_raw( timestamp, 'gps', gid )
	    insert_raw( timestamp, 'gsm', cid )

        elif tag == 'gsm' or tag == 'gsm only, maxed out':
	    cid = celltower_id( g )
	    insert_raw( timestamp, 'gsm',cid)

	elif tag == 'BTdevs':
	    for bt_id in g:
		bid = bluetooth_id( bt_id )
		insert_raw( timestamp, 'bt',bid)

	elif tag == 'BTname':
	    bt_id = g[0]
	    bt_name = g[1]
	    if bt_name == u'': 
		bt_name = None
	    else:
		update_bt_record(bt_id,check_name(bt_name),None,None)

	elif tag == 'label':
	    lid = label_id( g )
	    insert_raw(timestamp,'label',lid)

        else:
            print "Unknown label: %s" % label

def check_name(name):
    n = ""
    for c in name[:19]:
	try:
	    cc = c.__str__()
	except:
	    cc = '.'
	n = n + cc
    



#
#  Main
#

conn = connect_to_db()

try:
    cursor = conn.cursor()
except:
    print 'failed to get cursor'

process_logs()

cursor.close()
conn.close()
