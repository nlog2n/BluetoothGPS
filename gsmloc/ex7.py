
###This example shows how to retrieve the GSM location information: 
# Mobile Country Code, Mobile Network Code, Location Area Code, Cell ID. 
# The location, appuifw and e32 modules are used.

import location
import appuifw
import e32

exitflag=0
appuifw.app.title = u'Location'
print u'Location Info:'
prevLoc = u''
while not exitflag:
	if prevLoc <> location.gsm_location():
		print location.gsm_location()
	prevLoc = location.gsm_location()
	e32.ao_sleep(0.1)
