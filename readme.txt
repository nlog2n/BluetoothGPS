
files in  bluetooth/:

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



How to decode GPS reading?

在NMEA GPS receiver中，GPGGA is not the only one to read GPS position, with all receivers, since not all receiver use it.

Should be able decode at least :
GPGGA
GPRMC
GPGLL
(注： 那些含有lon&lat的 sentence应该都可以)

