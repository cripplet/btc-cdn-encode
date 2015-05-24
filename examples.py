import binascii

import BTCCDN_op_return as cdnop
import BTCCDN_encode_lib as cdnen

# send a bitcoin transaction along with an OP_RETURN message
#
# SOURCE : either '' or a valid BTC address
#	if SOURCE = '', pull funds from wallet and change given back to wallet to a rawchangeaddress
#	else, pull funds directly from SOURCE and change given back SOURCE
# DESTINATION : valid BTC address
#	the target address to which AMOUNT will be deposited
# MESSAGE : binary data of at most 40 bytes as of BTC v0.10.0
# AMOUNT : BTC funds to transfer to DESTINATION in units of SATOSHIs (10 ** -8 BTC)
# TAX : additional draw from SOURCE for blockchain confirmation in units of SATOSHIs
#
# returns:
#	TX_ID of the successful transaction and raw TX hex string of the unsigned transaction
def send_op_return(source, destination, message, amount=cdnop.MIN_TAX, tax=cdnop.MIN_TAX, dummy=False):
	op_return_tx = cdnop.OPReturnTx(source, destination, message)
	sent_txid = op_return_tx.send(amount, tax, dummy)
	return { 'txid' : sent_txid, 'raw_tx' : op_return_tx.tx.raw }

def send_fild(fn):
	return cden.FileSendable(fn).send('', '', verbose=True, dummy=True)

if __name__ == '__main__':
	print "send OP_RETURN transaction : send_op_return('', '', 'MESSAGE')"
	print "check available SOURCE funds : cdnen.AddrLog(SOURCE, '').funds"
	print "output raw BTCCDN data : cdnen.BTCCDNCommand(cdnen.BTCCDNCommand.COMMAND['MSG'], binascii.b2a_hex('MESSAGE'), [ ('>L', 1 ) ]).data"
	print "send short ( <= 35bytes ) BTCCDN message : cdnen.AddrLog('', '', verbose=True).send(first=True, last=True, data='MESSAGE')"
	print "send longer BTCCDN message: cdnen.StringSendable('test.txt').send('', '', verbose=True)"
	print "send file via BTCCDN: send_file('test.txt.gz')"

	print send_op_return('', '', 'hello', dummy=True)
	# print send_file('test.txt.gz')
