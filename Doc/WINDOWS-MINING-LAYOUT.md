# Windows-only mining layout

Both management and compute execute on Windows. The Mac runs SSH for development and observation; it is not a mining proxy, required API host or part of the share-submission path.

The current route is:

`Windows manager -> Windows SOAT or KRig -> 127.0.0.1 TLS helper on Windows -> original Kryptex PRL pool`

The helper performs explicit certificate-chain and hostname verification. It is an implementation choice for a common verified transport, not a consequence of remote management or separate computers.

The pinned KRig 1.5.12 help advertises 0% developer fee for recognized Kryptex endpoints and at least 3% elsewhere. Its tested localhost route actually logged 3%; moving software between the Mac and Windows does not alter this endpoint classification. Both upstream SOAT and our fork have no developer-fee round, including through the helper. The pool service fee is separate.

The local certificate probe used a self-signed localhost server. It establishes that this test endpoint accepted an untrusted chain. It does not establish recognized native-Kryptex hostname behavior. No native verification/CA toggle was found in the installed help; unsupported behavior is not inferred solely from missing documentation.

Legitimate native KRig use with its advertised zero developer fee is the economic reference. The open kernel must improve actual throughput and energy efficiency; the relay fee is not treated as an intrinsic closed-source cost or as proof that the open fork is more profitable. Existing raw measured route results and their quality limits remain recorded in `COMPUTE-BACKEND-COMPARISON.md`.
