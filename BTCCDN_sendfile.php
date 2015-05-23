<?php
	require __DIR__ . '/BTCCDN_encode_lib.php';

	if($argc != 3) {
		printf("Usage:\n\tphp %s <addr> <file>\n", $argv[0]);
		exit;
	}

	@list($_, $addr, $fn) = $argv;

	send($addr, $fn);
?>
