//use meshtastic::protobufs;
//use meshtastic::Message;

pub fn add(left: u64, right: u64) -> u64 {
    //let d = meshtastic::protobufs::Data::decode(&b"hello worldxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"[..]).expect("decode err");
    //d.portnum();
    left + right
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn it_works() {
        let result = add(2, 2);
        assert_eq!(result, 4);
    }
}

pub mod encryption;
pub mod channel;
pub mod packet;

pub trait LoraTransmitter {
    fn transmit(&self, packet: &[u8]);
}

pub trait MeshtasticDB {

}

pub struct Meshtastic {
    tx: Box<dyn LoraTransmitter>,
    db: Box<dyn MeshtasticDB>,
}

impl Meshtastic {
    pub fn receive(
        packet: &[u8],
        snr: f32, // SNR (dB)
        rssi: i16, // RSSI (dBm)
        freq_error: i32, // frequency error in Hz
    ) {

    }
}
