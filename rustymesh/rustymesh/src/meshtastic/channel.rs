pub fn channel_hash(name: &str, key: &[u8]) -> u8 {
    // https://github.com/meshtastic/firmware/blob/6f7149e9a2e54fcb85cfe14cfd2d1db1b25a05b0/src/mesh/Channels.cpp#L33-L50
    let mut res: u8 = 0;

    for &b in name.as_bytes().iter().chain(key.iter()) {
        res ^= b;
    }

    return res;
}
