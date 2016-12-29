# BluetoothGPS
This is a Python module receiving GPS readings or cell tower information over Bluetooth or directly from mobile phone, and save formatted data into MySQL database for further analysis. The project was ever tested on Symbian smart-phones. 


## How to decode GPS reading?

GPS readings can be obtained from the sentences sent by receivers. For example, the following sentences sent by NMEA GPS receiver contain GPS longitude and latitude information and can be decoded:
* GPGGA
* GPRMC
* GPGLL

### Included Files
* aTrack.py      :Main
* btdis.py       :discover bluetooth devices  (BtDiscoverLocations.py is old one)
* newbt.py       :
* newgps.py      :
* --------------------------------
* blue-sample2.py  - the script i wrote to run on phone, recording both gsm&gps readings.
*
* --------------------------------
* blue-sample.py   - tell how to connect phone &PC via bluetooth
* blue-sample.txt  - ..
* database.py      - record to mySQL 
* database_tables.txt - database table defintions


## How to get GSM location?

Retrieves GSM location information: Mobile Country Code, Mobile Network Code, Location Area
Code, and Cell ID. A location area normally consists of several base stations. It is the area where
the terminal can move without notifying the network about its exact position. mcc and mnc
together form a unique identification number of the network into which the phone is logged.

The location module offers APIs to location information related services. Currently, the location has
one function:
* gsm_location()

Prerequisite: PyS60 installed

Here is an example of how to use the location package to fetch the location information:

> import location

> print location.gsm_location()

>(525,5,12,55693)

The place is around Jurong west St65.


### Included Files in gsmloc Folder
* gsm_location.py - record cell id
* nmea_info.py  - show gps information and draw map
* ex7.py  - record cell id
* stumblestore.py - record cell id and draw map
* s60-nwtracker.py - record cell and bluetooth ids


## Database Tables
  Refer to database_tables.txt file
