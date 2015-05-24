import binascii

import BTCCDN_op_return as cdnop
import BTCCDN_encode_lib as cdnen

##
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
#	TX_ID of the successful transaction
##
def send_op_return(source, destination, message, amount=cdnop.MIN_TAX, tax=cdnop.MIN_TAX):
	tx = cdnop.OPReturnTx(source, destination, message)
	tx.send(amount, tax)
	return tx.txid

if __name__ == '__main__':
	print "send OP_RETURN transaction : send_op_return(SOURCE, DESTINATION, MESSAGE)"
	print "check available SOURCE funds : AddrLog(SOURCE, DESTINATION).funds"
	print "output raw BTCCDN data : cdnen.BTCCDNCommand(cdnen.BTCCDNCommand.COMMAND['MSG'], binascii.b2a_hex('hello'), [ ('>L', 1 ) ]).data"
	print "send short BTCCDN message : cdnen.AddrLog('1AU6kp7Cb5pmocQcVNqwdAbRq9HLwaZoW1', '1AU6kp7Cb5pmocQcVNqwdAbRq9HLwaZoW1').send(True, True, 'message')"
	cdnen.AddrLog('1AU6kp7Cb5pmocQcVNqwdAbRq9HLwaZoW1', '1AU6kp7Cb5pmocQcVNqwdAbRq9HLwaZoW1').send(True, True, 'message')
