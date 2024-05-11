use ckb_bitcoin_spv_verifier::molecule;
use ckb_bitcoin_spv_verifier::types::core::{SpvClient, SpvTypeArgs};


use ckb_bitcoin_spv_verifier::types::packed::{SpvClientReader, SpvTypeArgsReader};
use ckb_bitcoin_spv_verifier::types::prelude::Unpack;


use ckb_types::prelude::{Builder, Pack, Reader};


use ckb_sdk::traits::{CellQueryOptions, PrimaryScriptType};
use ckb_types::core::ScriptHashType;
use ckb_types::packed::ScriptBuilder;


use ckb_sdk::CkbRpcClient;
use ckb_sdk::rpc::ckb_indexer::{Cell, Order, SearchKey};


#[derive(Clone)]
pub struct SpvClientCellMessage {
    pub arg: SpvTypeArgs,
    pub data: SpvClient,
}

impl SpvClientCellMessage {
    pub fn new(spv_type_args: SpvTypeArgs, client: SpvClient) -> Self {
        Self {
            arg: spv_type_args,
            data: client,
            // input_type: (),
            // output_type: (),
        }
    }

    pub(crate) fn from_by_cell(cell: Cell) -> Self {
        let (arg, data) = {
            let (arg, data) = get_data(cell);
            let arg = SpvTypeArgsReader::from_slice(&arg).unwrap().to_entity();
            let data = SpvClientReader::from_slice(&data).unwrap().to_entity();
            (arg, data)
        };
        return SpvClientCellMessage::new(arg.unpack(), data.unpack());
    }
}


pub fn get_data(cell: Cell) -> (molecule::bytes::Bytes, molecule::bytes::Bytes) {
    let args = cell.output.type_.unwrap().args.into_bytes();
    let data = cell.output_data.unwrap().into_bytes();
    return (args, data);
}


pub fn get_on_chain_spv_clients(ckb_client_url: String, arg: String, code_hash: String) -> Vec<SpvClient> {
    let ret = tokio::task::block_in_place(|| -> Vec<Cell> {
        let ckb_client = CkbRpcClient::new(ckb_client_url.as_str());
        // Decode hex string argument into binary
        let arg_bin = hex::decode(arg).expect("Failed to decode arg hex string");
        let code_hash = hex::decode(code_hash).expect("failed decode code hash ");
        let mut result = [0u8; 32];
        for i in 0..32 {
            result[i] = code_hash.get(i).unwrap().clone()
        }

        // Build script for SPV type
        let spv_type_script = ScriptBuilder::default()
            .code_hash(result.pack())
            .hash_type(ScriptHashType::Type.into())
            .args(arg_bin.pack())
            .build();

        // Create cell query options
        let query = CellQueryOptions::new(spv_type_script.clone(), PrimaryScriptType::Type);
        let order = Order::Desc;
        let search_key = SearchKey::from(query);
        return ckb_client
            .get_cells(search_key, order, u32::MAX.into(), None)
            .expect("Failed to find cells")
            .objects;
    });


    //  spvInfo cell bytes < 20  ,so should remove it
    ret.into_iter().
        filter(|cell| cell.clone().output_data.unwrap().as_bytes().len() > 20)
        .map(|cell| {
            let client = SpvClientCellMessage::from_by_cell(cell);
            client.data
        })
        .collect()
}

