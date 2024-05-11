use ckb_bitcoin_spv_verifier::types::core::{SpvClient};
use ckb_bitcoin_spv_verifier::types::prelude::Unpack;
use jsonrpc_utils::jsonrpc_core::serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, PartialEq, Eq, Hash, Debug)]
pub struct SpvClientJsonRpc {
    pub id: usize,
    pub tip_block_hash: String,
    pub headers_mmr_root: HeaderDigestJsonRpc,
    pub target_adjust_info: TargetAdjustInfoJsonRpc,
}

#[derive(Serialize, Deserialize, PartialEq, Eq, Hash, Debug)]
pub struct HeaderDigestJsonRpc {
    pub min_height: usize,
    pub max_height: usize,
    pub partial_chain_work: String,
    pub children_hash: String,
}

#[derive(Serialize, Deserialize, PartialEq, Eq, Hash, Debug)]
pub struct TargetAdjustInfoJsonRpc {
    pub(crate) start_time: String,
    pub(crate) next_compact_target: String,
}

impl SpvClientJsonRpc {
    pub(crate) fn from(client: SpvClient) -> Self {
        return Self {
            id: client.id as usize,
            tip_block_hash: client.tip_block_hash.to_string(),
            headers_mmr_root: HeaderDigestJsonRpc {
                min_height: client.headers_mmr_root.min_height as usize,
                max_height: client.headers_mmr_root.max_height as usize,
                partial_chain_work: client.headers_mmr_root.partial_chain_work.to_string(),
                children_hash: client.headers_mmr_root.children_hash.to_string(),
            },

            target_adjust_info: TargetAdjustInfoJsonRpc {
                start_time: client.target_adjust_info.start_time().unpack().to_string(),
                next_compact_target: client.target_adjust_info.next_compact_target().unpack().to_string(),
            },
        };
    }
}

