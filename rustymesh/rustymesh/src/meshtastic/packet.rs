use byteorder::{LittleEndian, ReadBytesExt};
use std::io::Cursor;

type NodeId = u32;
type PacketId = u32;

pub struct MeshtasticPacketHeader {
    pub destination: NodeId,
    pub sender: NodeId,
    pub packet_id: PacketId,
    pub hop_limit: u8,
    pub hop_start: u8,
    pub want_ack: bool,
    pub via_mqtt: bool,
    pub channel_hash: u8,
    pub next_hop: u8,
    pub relay_node: u8,
}

impl MeshtasticPacketHeader {
    fn from_bytes(data: &[u8]) -> std::io::Result<(MeshtasticPacketHeader, usize)> {
        let mut cursor = Cursor::new(data);

        let destination = cursor.read_u32::<LittleEndian>()?;
        let sender = cursor.read_u32::<LittleEndian>()?;
        let packet_id = cursor.read_u32::<LittleEndian>()?;
        let flags = cursor.read_u8()?;
        let channel_hash = cursor.read_u8()?;
        let next_hop = cursor.read_u8()?;
        let relay_node = cursor.read_u8()?;

        let packet = MeshtasticPacketHeader {
            destination: destination,
            sender: sender,
            packet_id: packet_id,
            hop_limit: flags & 0b111,
            hop_start: (flags << 5) & 0b111,
            want_ack: (flags << 3) & 1 == 1,
            via_mqtt: (flags << 4) & 1 == 1,
            channel_hash: channel_hash,
            next_hop: next_hop,
            relay_node: relay_node,
        };
        return Ok((packet, 16));
    }
}
