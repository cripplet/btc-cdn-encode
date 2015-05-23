<?php
        require __DIR__ . '/libs/php-OP_RETURN/OP_RETURN.php';

	$MIN_AMOUNT = 0.0001;

	/**
	 * message length per tx
	 *	out of 40 bytes total, we reserve one byte for the header and four bytes for the counter
	 */
	$LENGTH = 35;

	$VERSION = 0;
	$COMMAND = array(
		'MSG' => 16,
		'FILESTART' => 1,
		/* fileterm: 10010, not 10002 */
		/* TODO: 10011 -> file start + term */
		'FILETERM' => 2,
		'TRANSFERACCT' => 0,
	);

	/**
	 * unit tests
	 */

	assert(itoh(0) == '00000000');
	assert(itoh(1) == '00000001');
	assert(itoh(16) == '00000010');
	assert(itoh(0, 1) == '00');
	assert(itoh(1, 10) == '01');

	/* string to hex */
	function stoh($s) {
		$h = '';
		for($i = 0; $i < strlen($s); $i++) {
			$h .= str_pad(dechex(ord($s[$i])), 2, '0', STR_PAD_LEFT);
		}
		return $h;
	}

	function htos($h) {
		$s = '';
		for($i = 0; $i < strlen($h) - 1; $i += 2) {
			$s .= chr(hexdec($h[$i] . $h[$i + 1]));
		}
		return $s;
	}

	/* int to arbitrary-length hex -- assume $i >= 0 */
	function itoh($i, $l = 4) {
		$_i = str_pad(dechex($i), $l * 2, '0', STR_PAD_LEFT);
		return $_i;
	}

	function get_fp($addr, $mode) {
		$fn = sprintf('_%s.log', $addr);
		$fp = fopen($fn, $mode);
		return $fp;
	}

	/* return the increment count for the associated address */
	function r($addr) {
		$fp = get_fp($addr, 'r');
		$v = intval(fread($fp, 1024));
		fclose($fp);
		return $v;
	}

	/* write to log file the increment count */
	function w($addr, $c = 0) {
		$fp = get_fp($addr, 'w');
		assert(fwrite($fp, strval($c)) == strlen(strval($c)));
		fclose($fp);
	}

	/* initialize a bitcoin address log file */
	function init($addr) {
		w($addr);
		assert(r($addr) == 0);
	}

	/* send file; assume $fn exists */
	function send($addr, $fn) {
		global $COMMAND, $LENGTH;
		$ofs = r($addr);
		$fp = fopen($fn, 'r');
		$d = array();
		$h = array();
		while(!feof($fp)) {
			$s = fread($fp, $LENGTH);
			$d[] = $s;
			$h[] = $COMMAND['MSG'];
		}
		fclose($fp);

		$h[0] |= $COMMAND['FILESTART'];
		$h[count($h) - 1] |= $COMMAND['FILETERM'];

		foreach($d as $k => $v) {
			$c = $ofs + $k;
			send_cmd($addr, $h[$k], itoh($c) . stoh($v));
		}
		w($addr, $ofs + $k + 2);
	}

	/**
	 * $c is command in int
	 * $d is data in hex string
	 */
	function send_cmd($addr, $c, $d) {
		global $VERSION;
		$_c = itoh($VERSION << 5 | $c, 1);
		$m = htos($_c) . htos($d);
		/* hex-encoded: each byte is 2 chars long */
		assert(strlen($m) <= 40);
		$res = _s($addr, $m);
		if(is_array($res) && array_key_exists('txid', $res)) {
			echo $res['txid'] . "\n";
		} else {
			echo "error: " . $m . "\n";
		}
	}

	function _s($addr, $m) {
		global $MIN_AMOUNT;
		return OP_RETURN_send($addr, $MIN_AMOUNT, $m);
	}
?>
