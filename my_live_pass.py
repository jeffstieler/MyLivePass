import uuid
import urllib2
import gzip
import StringIO
import sys

# have urllib2 automatically add received cookies to subsequent requests
urllib2.install_opener(urllib2.build_opener(urllib2.HTTPCookieProcessor))

class MyLivePass(object):

	def __init__(self, server=None, username=None, password=None):
		self.cookies = {}
		self.session_id = None
		self.access_code = None
		self.server, self.username, self.password = server, username, password
		if self.server and self.username and self.password:
			pass

	def login(self):
		request_body = """
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope" xmlns:a="http://www.w3.org/2005/08/addressing" xmlns:ch="http://schemas.compassion.com/common/headers/2005-04-05">
	<s:Header>
		<a:Action s:mustUnderstand="1">http://RTP.LivePass.Authentication/ILivePassAuthenticationService/Authenticate</a:Action>
		<a:MessageID>urn:uuid:%s</a:MessageID>
		<a:ReplyTo>
			<a:Address>http://www.w3.org/2005/08/addressing/anonymous</a:Address>
		</a:ReplyTo>
		<a:To s:mustUnderstand="1">%sLivePassAuthenticationService.svc</a:To>
		<ch:UICulture>en_US</ch:UICulture>
	</s:Header>
	<s:Body>
		<Authenticate xmlns="http://RTP.LivePass.Authentication">
			<userName>%s</userName>
			<password>%s</password>
			<sessionCulture>en-US</sessionCulture>
		</Authenticate>
	</s:Body>
</s:Envelope>
		""" % (uuid.uuid1(), self.server, self.username, self.password)

		response = self.request("LivePassAuthenticationService.svc", request_body)
		print response

	def request(self, path, request_body):
		headers = {
			"User-Agent": "Park City 2.0 (iPhone; iPhone OS 5.0.1; en_US)",
			"RTP-Session-Type": "Cache",
			"Content-Type": "application/x-gzip"
		}
		url = self.server + path
		data = self.compress(request_body)
		request = urllib2.Request(url, data, headers)
		stream = urllib2.urlopen(request)
		response = stream.read()
		return self.decompress(response)

	# trick using "duck typing" to get around gzip's lack of a string compression method
	# StringIO provides a file-like object with a string storage mechanism
	def compress(self, data):
		s = StringIO.StringIO()
		f = gzip.GzipFile(fileobj=s, mode="w", compresslevel=9)
		f.write(data)
		f.close()
		return s.getvalue()

	def decompress(self, data):
		s = StringIO.StringIO(data)
		f = gzip.GzipFile(fileobj=s, mode="r", compresslevel=9)
		decompressed = f.read()
		f.close()
		return decompressed

if __name__ == "__main__":
	my_live_pass = MyLivePass("https://secure.parkcitymountain.com/mobile/", sys.argv[1], sys.argv[2])
	my_live_pass.login()