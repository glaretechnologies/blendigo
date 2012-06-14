from email_credentials import SMTPserver, sender, USERNAME, PASSWORD

import sys
import os
import re

from smtplib import SMTP_SSL as SMTP	# this invokes the secure SMTP protocol (port 465, uses SSL)
from email.mime.text import MIMEText

def send_release_email(version, url, blender_version='2.6', additional_text=''):
	content="""\
Hi,

Blendigo-2.5 version %(VER)s has been packaged and uploaded to:
%(URL)s

This exporter requires Blender version %(BL_VER)s

%(AT)s

Regards,
The Blendigo Release Robot
""" % {'VER':version, 'URL':url, 'BL_VER':blender_version, 'AT':additional_text}

	try:
		msg = MIMEText(content, 'plain')
		msg['Subject'] = "Blendigo-2.5 v%s Release Notification" % version
		msg['From'] = sender # some SMTP servers will do this automatically, not all
		
		conn = SMTP()
		conn.set_debuglevel(False)
		conn.connect(SMTPserver, 465)
		conn.ehlo()
		conn.login(USERNAME, PASSWORD)
		
		try:
			conn.sendmail(
				sender,
				[
					'support@indigorenderer.com',
					'doughammond@hamsterfight.co.uk'
				],
				msg.as_string()
			)
		finally:
			conn.close()
	
	except Exception as exc:
		sys.exit( "mail failed; %s" % str(exc) ) # give a error message
		raise exc

if __name__ == '__main__':
	try:
		if len(sys.argv) < 4:
			raise Exception('Not enough args, need version number and download URL and blender version')
		
		version = sys.argv[1]
		url = sys.argv[2]
		bl_ver = sys.argv[3]
		
		send_release_email(version, url, bl_ver)
	
	except Exception as err:
		print("ERROR: %s" % err)
		sys.exit(-1)
