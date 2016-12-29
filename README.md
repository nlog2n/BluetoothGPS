# BluetoothGPS
Python module receiving GPS over Bluetooth


## How to decode GPS reading?

在NMEA GPS receiver中，GPGGA is not the only one to read GPS position, with all receivers, since not all receiver use it.

Should be able decode at least :
GPGGA
GPRMC
GPGLL
(注： 那些含有lon&lat的 sentence应该都可以)




## Included Files

aTrack.py      -Main
btdis.py       -discover bluetooth devices  (BtDiscoverLocations.py is old one)
newbt.py       -
newgps.py      -
--------------------------------
blue-sample2.py  - the script i wrote to run on phone, recording both gsm&gps readings.

--------------------------------
blue-sample.py   - tell how to connect phone &PC via bluetooth
blue-sample.txt  - ..
database.py      - record to mySQL 
database_tables.txt - ..


## Database Tables

mysql> show tables;
+-------------------+
| Tables_in_gsmloc  |
+-------------------+
| activity          | 
| bluetooth         | 
| bluetooth_devices | 
| celltowers        | 
| gps               | 
| label             | 
| raw_log           | 
| raw_log_localtime | 
| speed_dir         | 
| tower_location    | 
+-------------------+
10 rows in set (0.00 sec)


mysql> describe activity ;
+---------+---------+------+-----+---------+----------------+
| Field   | Type    | Null | Key | Default | Extra          |
+---------+---------+------+-----+---------+----------------+
| id      | int(11) | NO   | PRI | NULL    | auto_increment | 
| name    | int(11) | NO   |     | 0       |                | 
| param_1 | int(11) | YES  |     | NULL    |                | 
| param_2 | int(11) | YES  |     | NULL    |                | 
+---------+---------+------+-----+---------+----------------+
4 rows in set (0.00 sec)

mysql> describe bluetooth ;
+---------+-------------+------+-----+---------+----------------+
| Field   | Type        | Null | Key | Default | Extra          |
+---------+-------------+------+-----+---------+----------------+
| id      | int(11)     | NO   | PRI | NULL    | auto_increment | 
| bt_id   | varchar(12) | YES  |     | NULL    |                | 
| bt_name | varchar(20) | YES  |     | NULL    |                | 
+---------+-------------+------+-----+---------+----------------+
3 rows in set (0.00 sec)

mysql> describe bluetooth_devices ;
+----------+-------------+------+-----+---------+----------------+
| Field    | Type        | Null | Key | Default | Extra          |
+----------+-------------+------+-----+---------+----------------+
| id       | int(11)     | NO   | PRI | NULL    | auto_increment | 
| bt_id    | varchar(12) | YES  |     | NULL    |                | 
| bt_name  | varchar(20) | YES  |     | NULL    |                | 
| my_name  | varchar(32) | YES  |     | NULL    |                | 
| dev_type | varchar(8)  | YES  |     | NULL    |                | 
+----------+-------------+------+-----+---------+----------------+
5 rows in set (0.00 sec)

mysql> describe celltowers ;
+----------+---------+------+-----+---------+----------------+
| Field    | Type    | Null | Key | Default | Extra          |
+----------+---------+------+-----+---------+----------------+
| id       | int(11) | NO   | PRI | NULL    | auto_increment | 
| country  | int(11) | YES  |     | NULL    |                | 
| network  | int(11) | YES  |     | NULL    |                | 
| location | int(11) | YES  |     | NULL    |                | 
| cell     | int(11) | YES  |     | NULL    |                | 
+----------+---------+------+-----+---------+----------------+
5 rows in set (0.00 sec)

mysql> describe gps ;
+-------+-------------+------+-----+---------+----------------+
| Field | Type        | Null | Key | Default | Extra          |
+-------+-------------+------+-----+---------+----------------+
| id    | int(11)     | NO   | PRI | NULL    | auto_increment | 
| lat   | varchar(10) | YES  |     | NULL    |                | 
| lon   | varchar(10) | YES  |     | NULL    |                | 
+-------+-------------+------+-----+---------+----------------+
3 rows in set (0.00 sec)

mysql> describe label ;
+--------+-------------+------+-----+---------+----------------+
| Field  | Type        | Null | Key | Default | Extra          |
+--------+-------------+------+-----+---------+----------------+
| id     | int(11)     | NO   | PRI | NULL    | auto_increment | 
| string | varchar(64) | YES  |     | NULL    |                | 
+--------+-------------+------+-----+---------+----------------+
2 rows in set (0.00 sec)

mysql> describe raw_log ;
+---------+------------+------+-----+-------------------+----------------+
| Field   | Type       | Null | Key | Default           | Extra          |
+---------+------------+------+-----+-------------------+----------------+
| id      | int(11)    | NO   | PRI | NULL              | auto_increment | 
| time    | timestamp  | YES  |     | CURRENT_TIMESTAMP |                | 
| type    | varchar(8) | NO   |     |                   |                | 
| type_id | int(11)    | NO   |     | 0                 |                | 
| val_1   | int(11)    | YES  |     | NULL              |                | 
| val_2   | int(11)    | YES  |     | NULL              |                | 
+---------+------------+------+-----+-------------------+----------------+
6 rows in set (0.00 sec)

mysql> select * from raw_log ;
...
| 92906 | 2007-01-22 13:08:40 | bt   |       2 |    -1 |    -1 | 
| 92907 | 2007-01-22 13:08:40 | bt   |      17 |    -1 |    -1 | 
+-------+---------------------+------+---------+-------+-------+
92907 rows in set (0.50 sec)


mysql> describe raw_log_localtime ;
+---------+------------+------+-----+-------------------+----------------+
| Field   | Type       | Null | Key | Default           | Extra          |
+---------+------------+------+-----+-------------------+----------------+
| id      | int(11)    | NO   | PRI | NULL              | auto_increment | 
| time    | timestamp  | YES  |     | CURRENT_TIMESTAMP |                | 
| type    | varchar(8) | NO   |     |                   |                | 
| type_id | int(11)    | NO   |     | 0                 |                | 
| val_1   | int(11)    | YES  |     | NULL              |                | 
| val_2   | int(11)    | YES  |     | NULL              |                | 
+---------+------------+------+-----+-------------------+----------------+
6 rows in set (0.00 sec)

mysql> describe speed_dir ;
+-------+-------------+------+-----+---------+----------------+
| Field | Type        | Null | Key | Default | Extra          |
+-------+-------------+------+-----+---------+----------------+
| id    | int(11)     | NO   | PRI | NULL    | auto_increment | 
| speed | varchar(10) | YES  |     | NULL    |                | 
| dir   | varchar(10) | YES  |     | NULL    |                | 
+-------+-------------+------+-----+---------+----------------+
3 rows in set (0.00 sec)

mysql> describe tower_location ;
+------------+---------+------+-----+---------+----------------+
| Field      | Type    | Null | Key | Default | Extra          |
+------------+---------+------+-----+---------+----------------+
| id         | int(11) | NO   | PRI | NULL    | auto_increment | 
| cell_tower | int(11) | YES  |     | NULL    |                | 
| gps        | int(11) | YES  |     | NULL    |                | 
+------------+---------+------+-----+---------+----------------+
3 rows in set (0.00 sec)

