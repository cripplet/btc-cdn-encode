# btc-cdn-encode

official file uploader for the [BTC-CDN protocol](https://github.com/cripplet/btc-cdn)

This code conforms to v.0.1.1 of the [BTC-CDN protocol]

Installation
----

```bash
git clone https://github.com/cripplet/btc-cdn-encode.git
cd btc-cdn-encode.git
git submodule update --init --recursive
```

Example
----

```bash
php BTCCDN_init.php 1AU6kp7Cb5pmocQcVNqwdAbRq9HLwaZoW1
php BTCCDN_sendfile.php 1AU6kp7Cb5pmocQcVNqwdAbRq9HLwaZoW1 test.txt
php BTCCDN_sendfile.php 1AU6kp7Cb5pmocQcVNqwdAbRq9HLwaZoW1 test.txt.gz
```
