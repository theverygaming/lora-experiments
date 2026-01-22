use std::vec;

pub struct LoraPacket {
    pub data: vec::Vec<u8>,
}

pub struct LoraPacketReceived {
    pub packet: LoraPacket,
    pub snr: f32, // SNR (dB)
    pub rssi: i16,  // RSSI (dBm)
    pub freq_error: i32, // frequency error in Hz
}

pub trait LoraReceiver {
    pub fn receive(
        packet: &[u8],
        snr: f32, // SNR (dB)
        rssi: i16, // RSSI (dBm)
        freq_error: i32, // frequency error in Hz
    ) {

    }
}
