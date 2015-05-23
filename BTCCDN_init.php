<?php
	require __DIR__ . '/BTCCDN_encode_lib.php';

	if($argc != 2) {
		printf("Usage:\n\tphp %s <addr>\n", $argv[0]);
		exit;
	}

	@list($_, $addr) = $argv;

	init($addr);
?>
