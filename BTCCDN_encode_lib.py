import BTCCDN_op_return

import os
import binascii
import struct
import csv

from tempfile import NamedTemporaryFile as tempfile
from itertools import chain
from shutil import move

from bitcoin.rpc import Proxy as btc_proxy
from bitcoin.wallet import P2PKHBitcoinAddress as btc_address

LEN_HEAD = 1
VERSION = 0
MAX_COUNTER = 0xffffffff
MAX_MSG = 35

assert(LEN_HEAD > 0)
assert(VERSION >= 0)
assert(MAX_COUNTER >= 0)

class BTCCDNCommand(object):
	global VERSION
	COMMAND = {
		'MSG' : 16,
		'FILESTART' : 17,
		'FILETERM' : 18,
		'TERMACCT' : 1,
	}
	v = VERSION

	##
	# CMD is numerical input
	# payload is a hex-encoded string
	##
	def __init__(self, cmd, payload, aux=None):
		self._c = cmd
		self._p = payload
		if not aux:
			aux = []
		self._a = aux

	@property
	def aux(self):
		return self._a

	@property
	def command(self):
		for k, v in self.COMMAND:
			if self._c == v:
				return k

	@property
	def data(self):
		body = ''.join([ struct.pack(f, d) for (f, d) in self.aux ]) + self._p
		return self.header + body

	# return the command header as a hex string
	@property
	def header(self):
		return struct.pack('>B', self.v << 5 | self._c)

class AddrLog(object):
	@staticmethod
	def _counter_log_name(dest, dummy):
		return 'logs/%s.%scounter' % (dest, '' if not dummy else 'dummy.')

	@staticmethod
	def _verbose_log_name(dest, dummy):
		return 'logs/%s.%slog' % (dest, '' if not dummy else 'dummy.')

	# FAST : if we should check the counter log after every tx
	# VERBOSE : if a { TXID : OP_RETURN DATA } log should be kept
	# SRC and DEST may be set to '' or valid BTC addresses
	# if SRC = '', funds are drawn from any address in the wallet
	# if DEST = '', a random destination address will be picked for you to use until address expiration (COUNTER overflow) 
	def __init__(self, src, dest, verbose=False, fast=False, dummy=False):
		self._s = src
		self._d = dest
		self._p = btc_proxy()
		self._dummy = dummy

		if self.dest == '':
			self._d = str(self.proxy.getnewaddress())

		# set source address
		if self.src == '':
			candidates = sorted(self.proxy.listunspent(), lambda x, y: cmp(y['amount'], x['amount']))
			if not len(candidates):
				raise BTCCDN_op_return.InsufficientFunds
			self._s = str(candidates[0]['address'])

		# populated next AddrLog in case SELF.COUNT overflows
		self._n = None

		# if log file does not exist, create it, get count
		if not os.path.isfile(self.counter_log_name):
			with open(self.counter_log_name, 'w') as fp:
				pass

		self._c = self.read()

		# initialize the verbose log
		if not os.path.isfile(self.verbose_log_name):
			with open(self.verbose_log_name, 'w'):
				pass

		self._f = fast
		self._v = verbose

	@property
	def dummy(self):
		return self._dummy

	@property
	def verbose(self):
		return self._v

	@property
	def fast(self):
		return self._f

	@property
	def counter_log_name(self):
		return AddrLog._counter_log_name(self.dest, self.dummy)

	@property
	def verbose_log_name(self):
		return AddrLog._verbose_log_name(self.dest, self.dummy)

	@property
	def proxy(self):
		return self._p

	@property
	def next(self):
		return self._n

	# money from which BTC is drawn SRC = '' is allowed
	@property
	def src(self):
		return self._s

	# where messages will be sent
	@property
	def dest(self):
		return self._d

	@property
	def count(self):
		return self._c

	@count.setter
	def count(self, v):
		self._c = v
		if not self.fast:
			self.write()

	def read(self):
		with open(self.counter_log_name, 'r') as fp:
			r = csv.reader(fp, delimiter='\t')
			for (addr, c) in r:
				if self.src == addr:
					return int(c)
		return 0

	def write(self):
		found = False
		t = tempfile(delete=False)
		with open(self.counter_log_name, 'r') as fp, t:
			r = csv.reader(fp, delimiter='\t')
			w = csv.writer(t, delimiter='\t')
			for (addr, c) in r:
				if self.src == addr:
					found = True
					c = self.count
				w.writerow((addr, c))
			if not found:
				w.writerow((self.src, self.count))
			move(t.name, self.counter_log_name)

	def log(self, data):
		with open(self.verbose_log_name, 'a') as fp:
			fp.write(data + '\n')
		

	# return how much spending potential the current ADDRESS has
	@property
	def funds(self):
		candidates = self.proxy.listunspent()
		if self.src != '':
			candidates = filter(lambda x: x['address'] == btc_address(self.src), candidates)
		return sum([ x['amount'] for x in candidates ])

	# checks to see if self.DEST is in own wallet
	@property
	def belongs(self):
		return self.src == self.dest

	def _get_quanta(self, n):
		n_send = n * (not self.belongs)
		n_fees = n
		return n_send + n_fees

	# verify that we have enough funds to follow through with the entire tx chain
	def verify(self, n):
		n_msgs = n
		n_term = n / (MAX_COUNTER + 1) + ((self.count + n % (MAX_COUNTER + 1)) > MAX_COUNTER)
		f = max(2, self._get_quanta(n_msgs) + self._get_quanta(n_term) + self.belongs) * BTCCDN_op_return.MIN_TAX
		if f > self.funds:
			raise BTCCDN_op_return.InsufficientFunds
		return f

	# sends hex-encoded data to destination address; if final = True, terminate this account
	def send(self, first, last, data, final=False):
		global MAX_COUNTER
		assert(self.count <= MAX_COUNTER)

		# ensure have enough funds to transmit this OP_RETURN and possible TERMACCT transaction
		self.verify(1)

		c = BTCCDNCommand.COMMAND['MSG']
		if first:
			c |= BTCCDNCommand.COMMAND['FILESTART']
		if last:
			c |= BTCCDNCommand.COMMAND['FILETERM']

		d = BTCCDNCommand(c, data, [ ('>L', self.count) ]).data

		txid = BTCCDN_op_return.OPReturnTx(self.src, self.dest, d).send(dummy=self.dummy)

		if self.verbose:
			self.log('\t'.join([ self.src, txid, binascii.b2a_hex(d) ]))
		if self.count == MAX_COUNTER or (last and final):
			if not final:
				self._n = AddrLog(self.src, '', fast=self.fast, verbose=self.verbose, dummy=self.dummy)
			self.term('' if final else self.next.dest)
		else:
			self.count += 1
			# update file
			if last:
				self.write()
		return txid

	# terminates this account
	def term(self, next=''):
		self.write()
		d = BTCCDNCommand(BTCCDNCommand.COMMAND['TERMACCT'], next).data
		txid = BTCCDN_op_return.OPReturnTx(self.src, self.dest, d).send(dummy=self.dummy)
		if self.verbose:
			self.log('\t'.join([ self.src, txid, binascii.b2a_hex(d) ]))
		return txid

class BaseSendable(object):
	def __init__(self, *args, **kwargs):
		pass

	# returns the size of the data in bytes
	@property
	def size(self):
		raise NotImplemented

	# return list of strings at most 35-bytes long for each term
	@property
	def data(self):
		raise NotImplemented

	# sends binary representation of data[] into DEST with funds drawn from SRC
	# set VERBOSE for a record of all txids and data written to the blockchain
	# throws InsufficentFund if not enough BTC in SRC to fund transactions
	#
	# returns:
	#	first TXID of the transaction
	#	SRC and DEST addresses of the transaction
	#	NEXT destination address to send to in case the account is not closed
	def send(self, src, dest, verbose=False, fast=False, dummy=False, final=False):
		global MAX_MSG
		self.addr = AddrLog(src, dest, verbose=verbose, fast=fast, dummy=dummy)
		# self.addr.dest changes in case AddrLog.TERM() is called
		dest = self.addr.dest
		self.addr.verify(self.size / MAX_MSG + (self.size % MAX_MSG > 0))
		txid = ''
		for k, v in enumerate(self.data):
			tmp_txid = self.addr.send(k == 0, k == len(self.data) - 1, v, final=final)
			if k == 0:
				txid = tmp_txid
			if self.addr.next:
				self.addr = self.addr.next
		return { 'txid' : txid, 'next' : '' if final else self.addr.dest, 'src' : self.addr.src, 'dest' : dest }

class StringSendable(BaseSendable):
	def __init__(self, s):
		self._s = s
		super(StringSendable, self).__init__()

	@property
	def size(self):
		return len(self._s)

	@property
	def data(self):
		if not getattr(self, '_d', None):
			self._d = []
			c = 0
			while c < self.size:
				self._d.append(self._s[c:c + MAX_MSG])
				c += MAX_MSG
		return self._d

class FileSendable(StringSendable):
	def __init__(self, name):
		self._fn = name
		with open(self.name, 'rb') as fp:
			s = ''.join(fp.readlines())
		super(FileSendable, self).__init__(s)

	@property
	def name(self):
		return self._fn

	@property
	def size(self):
		return os.stat(self.name).st_size
