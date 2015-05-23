import decimal
import os

MIN_TAX = decimal.Decimal(0.0001)
# as per v0.1.1
MAX_DATA = 40
LEN_HEAD = 1
VERSION = 0

class OPReturnTx:
	global MAX_DATA
	def __init__(self, src, dest, msg):
		assert(len(msg) <= MAX_DATA)
		self._s = src
		self._d = dest
		self._m = msg

	# return txid
	def send(self, tax):
		pass

class BTCCDNCommand:
	global VERSION
	COMMAND = {
		'MSG' : 32,
		'FILESTART' : 33,
		'FILETERM' : 34,
		'TERMACCT' : 34
	}
	v = VERSION

	# cmd is a string input
	# payload is array (?)
	def __init__(self, cmd, payload):
		global MAX_LENGTH
		assert(cmd in self.COMMAND)
		# ? assert(len(payload) <= MAX_DATA - LEN_HEAD)
		self._c = self.COMMAND[cmd]
		self._p = payload

	@property
	def command(self):
		for k, v in self.COMMAND:
			if self._c == v:
				return k

	@property
	def payload(self):
		return self._p

	@property
	def header(self):
		return self.v << 5 | self._c
		

class AddrLog:
	global MIN_TAX
	tax = MIN_TAX
	def __init__(self, address):
		self._addr = address
		# if log file does not exist, create it, get count
		self.count = 0

	@property
	def count(self):
		return self._c

	@count.setter
	def count(self, v):
		self._c = v
		# write to file

	@property
	def address(self):
		return self._addr

	# return how much spending potential the current ADDRESS has
	@property
	def funds(self):
		return 0

	# sends data to destination address; if final = True, terminate this account
	def send(self, dest, data):
		# check insufficient funds

		# send
		tx = []
		# for ...
		tx.append(OPReturnTx(self.address, dest, data[0::1]).send(self.tax))

		self.c += 0
		pass

	def term(self, next=''):
		OPReturnTx(self.address, self.address, next).send(self.tax)
		pass		

class File:
	def __init__(self, name):
		self._fn = name

	@property
	def name(self):
		return self._fn

	# returns the size of the file in bytes
	@property
	def size(self):
		return os.stat(self.name).st_size

	@property
	def data(self):
		return ''

	# sends self to the target address dest, with any leftover funds going to address change
	# throws NoFunds exception if insufficient funds
	# returns first txid of the transaction
	def send(self, change, dest):
		return AddrLog(change).send(dest, self.data)
