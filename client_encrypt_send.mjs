// client_encrypt_send.mjs
import fs from 'node:fs';
import 'node:crypto'; // for randomness
import nacl from 'tweetnacl';
import { encode as b64e, decode as b64d } from 'base64-arraybuffer';
import fetch from 'node-fetch';

const ENDPOINT_ID = process.env.RP_ENDPOINT_ID;
const API_KEY     = process.env.RP_API_KEY;
const SERVER_PK_B64 = process.env.SERVER_PUBLIC_KEY_B64; // base64 (32 bytes)

const workflow = JSON.parse(fs.readFileSync('examples/minimal_text2img.json','utf8'));

// --- Envelope encrypt using nacl.box (curve25519-xsalsa20-poly1305) ---
const serverPk = new Uint8Array(b64d(SERVER_PK_B64));
const ephKeys  = nacl.box.keyPair();
const nonce    = nacl.randomBytes(nacl.box.nonceLength); // 24 bytes

const plaintext = new TextEncoder().encode(JSON.stringify(workflow));
const ciphertext = nacl.box(plaintext, nonce, serverPk, ephKeys.secretKey);

const payload = {
  encrypted: true,
  epk: b64e(ephKeys.publicKey),
  nonce: b64e(nonce),
  ciphertext: b64e(ciphertext),
  return_images: false
};

const url = `https://api.runpod.ai/v2/${ENDPOINT_ID}/runsync`; // or /run
const res = await fetch(url, {
  method: 'POST',
  headers: {
    'authorization': API_KEY,
    'content-type': 'application/json',
    'accept': 'application/json'
  },
  body: JSON.stringify({ input: payload })
});

if (!res.ok) {
  console.error('RunPod error:', res.status, await res.text());
  process.exit(1);
}
console.log(await res.json());