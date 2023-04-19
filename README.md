# Caisse AP over IP protocol server and client

This project provides a server and client for the Caisse AP over IP protocol under the [GPL licence](https://www.gnu.org/licenses/gpl-3.0.html).

The [Caisse AP protocol](https://www.associationdupaiement.fr/protocoles/protocole-caisse/) is a vendor-independent protocol used in France to communicate between a point of sale and a payment terminal. It is implemented by [Ingenico](https://ingenico.com/fr/produits-et-services/terminaux-de-paiement) payment terminals, [Verifone](https://www.verifone.com/) payment terminal and other brands of payment terminals. This protocol is designed by a French association called [Association du paiement](https://www.associationdupaiement.fr/), abbreviated as **AP**. Note that the Caisse-AP protocol is used by Ingenico payment terminals deployed in France, but not by the same model of Ingenico payment terminals deployed in other countries!

The Caisse-AP protocol was initially written for serial and USB. Since the Caisse AP protocol version 3.x, it also supports IP. When used over IP, the client (point of sale) and the server (payment terminal) exchange simple text data encoded as ASCII over a raw TCP socket.

This project provides two Python 3 scripts:

- a client `caisse-ap-ip-client.py` that can simulate a point of sale,
- a server `caisse-ap-ip-server.py` that can simulate a payment terminal.

When developers implement the Caisse-AP IP protocol in a point of sale software, they need a real payment terminal to perform tests and, if they want to test a successful payment transaction, they need to make a real payment with a credit card. With this project, developers can now simulate a payment terminal and don't need a real payment terminal and a real credit card to perform payment transaction tests. This project can also be useful to develop a fully automated test suite that cover the code that implement to Caisse-AP IP protocol.

# Installation

The client needs the [iso4217](https://github.com/dahlia/iso4217) Python lib (not needed when using `EUR` only).

    pip3 install iso4217

The server requires the [Twisted](https://twisted.org/) Python lib:

    pip3 install Twisted

# Usage

The client and server script both have an option `--help` (or `-h`) that display the full list of the available options.

The server can be configured to simulate successful payment transaction, but also payment failures or timeouts.

# Tests

To develop this project, we used an **Ingenico Desk/5000** (with application `CONCERT V3` version `8400740115`) with check printer **Ingenico i2200**. We made real card payments and printed real checks.

# Author

- Rémi de Lattre
