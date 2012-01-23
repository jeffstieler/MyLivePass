#!/usr/bin/python

import my_live_pass
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

	# eventually this could have data for all resorts
	resorts = {
		"Park City": {
			"endpoint": "https://secure.parkcitymountain.com/mobile/",
			"lifts": {
				# AccessLocationDescription => vertical rise
				"PC: PayDay": 1278,
				"PC: Crescent": 1754,
				"PC: First Time": 270,
				"PC: Three Kings": 441,
				"PC: Town": 1170,
				"PC: Eagle": 1140
			}
		}
	}

	def __init__(self, resort=None, username=None, password=None):
		self.user = {}
		self.access_code = None
		self.scan_history = []
		self.server = self.resorts.get(resort, {}).get("endpoint")
		self.username, self.password = username, password
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

	def get_scan_history(self):
		request_body = """
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope" xmlns:a="http://www.w3.org/2005/08/addressing" xmlns:ch="http://schemas.compassion.com/common/headers/2005-04-05">
	<s:Header>
		<a:Action s:mustUnderstand="1">http://RTP.LivePass.CrmUserService/ICrmUserService/RetrieveIndividualAccessScanHistory</a:Action>
		<a:MessageID>urn:uuid:%s</a:MessageID>
		<a:ReplyTo>
			<a:Address>http://www.w3.org/2005/08/addressing/anonymous</a:Address>
		</a:ReplyTo>
		<a:To s:mustUnderstand="1">%sCrmUserService.svc</a:To>
		<ch:UICulture>en_US</ch:UICulture>
	</s:Header>
	<s:Body>
		<RetrieveIndividualAccessScanHistory xmlns="http://RTP.LivePass.CrmUserService">
			<accessCode>%s</accessCode>
		</RetrieveIndividualAccessScanHistory>
	</s:Body>
</s:Envelope>
		""" % (uuid.uuid1(), self.server, self.access_code)

		response = self.request("CrmUserService.svc", request_body)
		self.parse_scan_history(response)
		return self.scan_history

	def parse_scan_history(self, scan_history_response):
		root = etree.fromstring(scan_history_response)
		namespaces = root.nsmap.copy()
		namespaces['r'] = "http://RTP.LivePass.CrmUserService"
		scans = root.find("s:Body/r:RetrieveIndividualAccessScanHistoryResponse/r:RetrieveIndividualAccessScanHistoryResult/ScanHistory", namespaces)
		self.scan_history = [s.attrib for s in scans]

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
	my_live_pass = MyLivePass(sys.argv[1], sys.argv[2], sys.argv[3])
	my_live_pass.login()
	my_live_pass.get_access_code()
	my_live_pass.get_scan_history()
	total_height = 0
	print "\n%(FirstName)s %(LastName)s (%(CustomerId)s)\n" % my_live_pass.user
	print "Days:\t%s" % my_live_pass.user.get("PrepaidAccessScanSummary", {}).get("TotalDays")
	print "Scans:\t%s" % my_live_pass.user.get("PrepaidAccessScanSummary", {}).get("TotalUses")
	print "\nIndividual Scans:\n"
	resort_lifts = MyLivePass.resorts.get(sys.argv[1], {}).get("lifts", {})
	for s in my_live_pass.scan_history:
		total_height += resort_lifts.get(s["AccessLocationDescription"], 0)
		print "%(AccessLocationDescription)s\t%(AccessDate)s @ %(AccessTime)s" % s
	print "\nTotal Vertical Lift Height: %u feet.\n" % total_height