# adapted from the application skeleton in the sdk

import e32
import appuifw
import location

class gsm_location :
	def __init__(self) :
		self.text = u""

	def gsm_location(self) :
		(self.mcc, self.mnc, self.lac, self.cellid) = location.gsm_location()
		self.text = u"MCC: %s\nMNC: %s\nLAC: %s\nCell id: %s\n" % (self.mcc, self.mnc, self.lac, self.cellid)
		return self.text

	def close(self) :
		pass

e32.ao_yield() 

class gsm_location_app:
    def __init__(self):
        self.lock = e32.Ao_lock()

        self.old_title = appuifw.app.title
        appuifw.app.title = u"GSM Location"

        self.exit_flag = False
        appuifw.app.exit_key_handler = self.abort

        self.db = gsm_location()
		
        appuifw.app.body = appuifw.Text()
        appuifw.app.menu = [(u"Refresh", self.refresh)] 

    def loop(self):
        try:
            self.refresh()
            self.lock.wait()
            while not self.exit_flag:
                self.refresh()
                self.lock.wait()
        finally:
            self.db.close()

    def close(self):
        appuifw.app.menu = []
        appuifw.app.body = None
        appuifw.app.exit_key_handler = None
        appuifw.app.title = self.old_title

    def abort(self):
        # Exit-key handler.
        self.exit_flag = True
        self.lock.signal()

    def refresh(self):
		self.db.gsm_location()
		appuifw.app.body.set(self.db.text)

def main():
    app = gsm_location_app()
    try:
        app.loop()
    finally:
        app.close()

if __name__ == "__main__":
    main()
 

