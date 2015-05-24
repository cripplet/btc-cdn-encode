##
# cf. http://bitcoin.stackexchange.com/questions/25224/what-is-a-step-by-step-way-to-insert-data-in-op-return for Python motivation
# cf. https://bitcoin.org/en/developer-reference#transactions for a more in-depth explanation of Bitcoin transactions
# cf. https://github.com/coinspark/php-OP_RETURN for PHP source code upon which this was based
##

import json
import struct
import binascii

from decimal import Decimal as decimal

import bitcoin

from bitcoin.rpc import Proxy as btc_proxy
from bitcoin.wallet import P2PKHBitcoinAddress as btc_address
from bitcoin.core.script import CScriptOp
from bitcoin.core import b2lx as btc_btolx

MIN_TAX = 1000
MAX_DATA = 40

class InsufficientFunds(Exception):
	pass

# handler for binary data generated by using generaterawtransaction
class RawTx(object):
	# binary data stream
	# raw is hex-encoded data as generated by generaterawtransaction
	# blob is the binary-decoded unicode string of raw
	class BinaryStream(object):
		def __init__(self, raw):
			self._b = raw.decode('hex')
			self._p = 0

		@property
		def blob(self):
			return self._b

		def skip(self, n):
			self._p += n

		def pack(self, format, d):
			r = struct.pack(format, d)
			self._b += r
			return r

		def unpack(self, format, n):
			r = struct.unpack_from(format, self.blob, self._p)
			self.skip(n)
			return r

		@staticmethod
		def _pack_hex(s):
			s = ''.join([ s[i:i + 2] for i in range(0, len(s), 2) ][::-1])
			r = binascii.a2b_hex(s)
			return r			

		@staticmethod
		def _unpack_hex(s):
			r = binascii.b2a_hex(s)
			r = ''.join([ r[i:i + 2] for i in range(0, len(r), 2) ][::-1])
			return r

		def pack_hex(self, s):
			r = RawTx.BinaryStream._pack_hex(s)
			self._b += r
			return r

		def unpack_hex(self, n):
			r = RawTx.BinaryStream._unpack_hex(self.blob[self._p:self._p + n])
			self.skip(n)
			return r

		def pack_txid(self, txid):
			return self.pack_hex(txid)

		def unpack_txid(self):
			return self.unpack_hex(32)

		def pack_varint(self, f):
			if f > 0xffffffff:
				r = '\xff' + struct.pack('<Q', f)
			elif f > 0xffff:
				r = '\xfe' + struct.pack('<I', f)
			elif f > 0xfc:
				r = '\xfd' + struct.pack('<H', f)
			else:
				r = struct.pack('<B', f)
			self._b += r
			return r

		def unpack_varint(self):
			f = self.unpack('<B', 1)[0]
			if f == 0xff:
				f = self.unpack('<Q', 8)[0]
			elif f == 0xfe:
				f = self.unpack('<I', 4)[0]
			elif f == 0xfd:
				f = self.unpack('<H', 2)[0]
			return f

		def reset(self):
			self._p = 0

	def __init__(self, proxy, raw):
		self._r = raw
		self._stream = RawTx.BinaryStream(self.raw)
		self._proxy = proxy

	@property
	def stream(self):
		return self._stream

	@stream.setter
	def stream(self, s):
		self._stream = s
		self._r = s.blob.encode('hex')

	@property
	def raw(self):
		return self._r

	@property
	def proxy(self):
		return self._proxy

	@property
	def json(self):
		return self.proxy.decoderawtransaction(self.raw)

	# take the raw transaction and turn into an array of referrable data
	def unpack(self):
		self.stream.reset()
		d = { 'version' : self.stream.unpack('<L', 4)[0], 'vin' : [], 'vout' : [] }
		for x in xrange(self.stream.unpack_varint()):
			d['vin'].append({
				'txid' : self.stream.unpack_txid(),
				'vout' : self.stream.unpack('<L', 4)[0],
				'scriptSig' : self.stream.unpack_hex(self.stream.unpack_varint()),
				'sequence' : self.stream.unpack('<L', 4)[0],
			})
		for x in xrange(self.stream.unpack_varint()):
			d['vout'].append({
				'value' : self.stream.unpack('<Q', 8)[0] * 10 ** -8,
				'scriptPubKey' : self.stream.unpack_hex(self.stream.unpack_varint()),
			})
		d['locktime'] = self.stream.unpack('<L', 4)[0]
		return d

	def pack(self, d):
		s = RawTx.BinaryStream('')
		s.pack('<L', d['version'])
		s.pack_varint(len(d['vin']))
		for x in d['vin']:
			s.pack_txid(x['txid'])
			s.pack('<L', x['vout'])
			s.pack_varint(len(x['scriptSig']) / 2)
			s.pack_hex(x['scriptSig'])
			s.pack('<L', x['sequence'])
		s.pack_varint(len(d['vout']))
		for x in d['vout']:
			s.pack('<Q', x['value'] * 10 ** 8)
			s.pack_varint(len(x['scriptPubKey']) / 2)
			s.pack_hex(x['scriptPubKey'])
		s.pack('<L', d['locktime'])
		self.stream = s

class OPReturnTx(object):
	global MAX_DATA
	##
	# src and dest are bitcoin addresses; src may be '' to indicate no preference on single input
	# msg is binary data
	##
	def __init__(self, src, dest, msg):
		# as of BTC 0.10, OP_RETURN should only store at most 40 bytes of data
		assert(len(msg) <= MAX_DATA)
		self._s = src
		self._d = dest
		self._m = msg
		# populated after sendrawtransaction is called
		self.txid = ''

	@property
	def msg(self):
		return self._m

	@property
	def src(self):
		return self._s

	@property
	def dest(self):
		return self._d

	@property
	def proxy(self):
		if not getattr(OPReturnTx, '_proxy', None):
			self._proxy = btc_proxy()
		return self._proxy

	# returns list of inputs to use for the transaction
	# if self._s is specified, use ONLY funds in self._s for transaction
	def _i(self, v, t):
		candidates = self.proxy.listunspent()
		if self._s != '':
			candidates = filter(lambda x: x['address'] == btc_address(self._s), candidates)
		# highest number of confirmations should be listed first as preferred spending account
		candidates = sorted(candidates, lambda x, y: cmp(y['confirmations'], x['confirmations']))
		input = []
		total = 0
		for c in candidates:
			if total < v + t:
				input.append({ 'txid' : btc_btolx(c['outpoint'].hash), 'vout' : c['outpoint'].n } )
				total += c['amount']
		if total < v + t:
			raise InsufficientFunds
		return (input, total)

	# returns a dict of { address : amount } outputs
	# if self._s == '', create a new change address, otherwise send change back to self._src
	def _o(self, s, v, t, input):
		output = { self._d : s - t if self._s == self._d else v }
		if self._s == '':
			output[self.proxy.getrawchangeaddress().__str__()] = s - v - t
		for k in output:
			output[k] = output[k] * 10 ** -8
		return output

	# creates the transaction to send
	# cf. http://bitcoin.stackexchange.com/questions/25224/what-is-a-step-by-step-way-to-insert-data-in-op-return for how to implement on TESTNET
	# cf. https://github.com/coinspark/php-OP_RETURN for implementation on MAINNET in PHP
	def _create(self, i, o):
		tx = RawTx(self.proxy, self.proxy.createrawtransaction(i, o))
		return tx

	# return txid
	# amt and tax are both in satoshi units
	def send(self, amt=MIN_TAX, tax=MIN_TAX):
		(i, s) = self._i(amt, tax)
		o = self._o(s, amt, tax, i)
		tx = self._create(i, o)

		# get the unpacked data and edit to suit our needs
		d = tx.unpack()

		# get the payload
		p = CScriptOp.encode_op_pushdata(self.msg)

		# append OP_RETURN tx out
		d['vout'].append({
			'value' : 0,
			'scriptPubKey' : RawTx.BinaryStream._unpack_hex(p) + '6a',
		})
		tx.pack(d)

		# here
		# signed, sealed, delivered
		tx = RawTx(self.proxy, self.proxy._call('signrawtransaction', tx.raw)['hex'])
		self.txid = self.proxy._call('sendrawtransaction', tx.raw)
		return self.txid
