import uuid
import urllib2
import gzip
import StringIO
import sys
from lxml import etree
import zlib

# have urllib2 automatically add received cookies to subsequent requests
urllib2.install_opener(urllib2.build_opener(urllib2.HTTPCookieProcessor))

class MyLivePass(object):

	def __init__(self, server=None, username=None, password=None):
		self.user = {}
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
		self.parse_user_info(response)
		return self.user

	def get_access_code(self):
		if self.access_code:
			return self.access_code
		# TODO: check for logged in user, perhaps just a self.user check
		request_body = """
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope" xmlns:a="http://www.w3.org/2005/08/addressing" xmlns:ch="http://schemas.compassion.com/common/headers/2005-04-05">
	<s:Header>
		<a:Action s:mustUnderstand="1">http://RTP.LivePass.CrmUserService/ICrmUserService/RetrievePrepaidAccessProducts</a:Action>
		<a:MessageID>urn:uuid:%s</a:MessageID>
		<a:ReplyTo>
			<a:Address>http://www.w3.org/2005/08/addressing/anonymous</a:Address>
		</a:ReplyTo>
		<a:To s:mustUnderstand="1">%sCrmUserService.svc</a:To>
		<ch:UICulture>en_US</ch:UICulture>
	</s:Header>
	<s:Body>
		<RetrievePrepaidAccessProducts xmlns="http://RTP.LivePass.CrmUserService">
			<customerId>%s</customerId>
		</RetrievePrepaidAccessProducts>
	</s:Body>
</s:Envelope>
		""" % (uuid.uuid1(), self.server, self.user.get('CustomerId'))

		response = self.request("CrmUserService.svc", request_body)
		self.parse_user_access_code(response)
		return self.access_code

	def parse_user_access_code(self, access_code_response):
		root = etree.fromstring(access_code_response)
		namespaces = root.nsmap.copy()
		namespaces['r'] = "http://RTP.LivePass.CrmUserService"
		access_products = root.find("s:Body/r:RetrievePrepaidAccessProductsResponse/r:RetrievePrepaidAccessProductsResult/AccessProducts", namespaces)
		if len(access_products):
			product = access_products[0]
			self.access_code = product.find('AccessCode').text

	def parse_user_info(self, login_response):
		root = etree.fromstring(login_response)
		namespaces = root.nsmap.copy()
		namespaces['r'] = "http://RTP.LivePass.Authentication"
		user_info = root.find("s:Body/r:AuthenticateResponse/r:AuthenticateResult/User", namespaces)
		self.user = self.tree_to_dict(user_info)

	def tree_to_dict(self, tree):
		dict = {}
		for element in tree:
			value = element.text
			if len(element):
				value = self.tree_to_dict(element)
			dict[element.tag] = value
		return dict

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

	# use zlib to decompress the server responses since python's gzip module can't handle trailing garbage
	# see: http://stackoverflow.com/questions/4928560/how-can-i-work-with-gzip-files-which-contain-extra-data
	def decompress(self, data):
		return zlib.decompress(data[10:], -zlib.MAX_WBITS)

if __name__ == "__main__":
	my_live_pass = MyLivePass("https://secure.parkcitymountain.com/mobile/", sys.argv[1], sys.argv[2])
	my_live_pass.login()
	print my_live_pass.user