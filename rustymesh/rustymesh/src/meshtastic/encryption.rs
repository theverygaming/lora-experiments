use aes::cipher::{KeyIvInit, StreamCipher, StreamCipherError};
use base64::prelude::*;

type Aes128Ctr32LE = ctr::Ctr32LE<aes::Aes128>;
type Aes256Ctr32LE = ctr::Ctr32LE<aes::Aes256>;

pub enum Cipher {
    AES128(Aes128Ctr32LE),
    AES256(Aes256Ctr32LE),
}

impl Cipher {
    pub fn crypt(&mut self, buf: &mut [u8]) {
        match self {
            Cipher::AES128(c) => c.apply_keystream(buf),
            Cipher::AES256(c) => c.apply_keystream(buf),
        }
    }

    pub fn crypt_b2b(&mut self, buf1: &[u8], buf2: &mut [u8]) -> Result<(), StreamCipherError> {
        match self {
            Cipher::AES128(c) => c.apply_keystream_b2b(buf1, buf2),
            Cipher::AES256(c) => c.apply_keystream_b2b(buf1, buf2),
        }
    }
}

pub fn cipher(key: &[u8], packet_id: u32, packet_sender: u32) -> Cipher {
    // the nonce is the packet ID, zeros, then the sender node ID and then zeros again
    let nonce_i: u128 = packet_id as u128 | ((packet_sender as u128) << 64);
    let nonce: [u8; 16] = nonce_i.to_le_bytes();
    
    if key.len() == 16 {
        Cipher::AES128(Aes128Ctr32LE::new(key.into(), &nonce.into()))
    } else {
        Cipher::AES256(Aes256Ctr32LE::new(key.into(), &nonce.into()))
    }
}

pub fn psk_to_key(psk_str: &str) -> Option<Vec<u8>> {
    // https://github.com/meshtastic/firmware/blob/6f7149e9a2e54fcb85cfe14cfd2d1db1b25a05b0/src/mesh/Channels.cpp#L206-L254

    // https://github.com/meshtastic/firmware/blob/6f7149e9a2e54fcb85cfe14cfd2d1db1b25a05b0/src/mesh/Channels.h#L141-L143
    let psk_default: [u8; 16] = [0xd4, 0xf1, 0xbb, 0x3a, 0x20, 0x29, 0x07, 0x59, 0xf0, 0xbc, 0xff, 0xab, 0xcf, 0x4e, 0x69, 0x01];

    let psk = BASE64_STANDARD.decode(psk_str).ok()?;

    if psk.len() == 0 {
        panic!("no PSK provided for a channel! In the meshtastic firmware for the primary channel this means encryption off and for the secondary channels the firmware will use the primary channel key. We don't do any of that. If you want to turn encryption off please provide a key with the value zero");
    }

    // standard key
    if psk.len() == 16 || psk.len() == 32 {
        return Some(psk);
    }

    // single-byte keys are handled specially
    if psk.len() == 1 {
        // zero key = no encryption
        if psk[0] == 0 {
            return None;
        }
        // modified default key encryption
        else {
            let mut ret = psk_default;
            ret[ret.len() - 1] += psk[0] - 1;
            return Some(ret.to_vec());
        }
    }
    // pad short 128-bit keys
    else if psk.len() < 16 {
        // TODO: log WARNING zero-padding short AES128 key
        let mut ret = vec![0u8; 16 - psk.len()];
        ret.extend(psk);
        return Some(ret);
    }
    // pad short 256-bit keys
    else if psk.len() < 32 {
        // TODO: log WARNING zero-padding short AES256 key
        let mut ret = vec![0u8; 32 - psk.len()];
        ret.extend(psk);
        return Some(ret);
    }

    return None;
}
