mod spv_client_cell_message;
mod spv_client_rpc;
mod util;

use bitcoin::hashes::{sha256d};
use std::str::FromStr;
use clap::{App, Arg};
use async_trait::async_trait;
use jsonrpc_utils::{jsonrpc_core, rpc};
use jsonrpc_utils::axum_utils::jsonrpc_router;
use jsonrpc_utils::jsonrpc_core::MetaIoHandler;
use std::sync::{Arc};
use bitcoin::block::Header;

use ckb_bitcoin_spv_verifier::types::packed::{SpvClientReader, TransactionProofReader};

use ckb_types::prelude::{ Reader};
use jsonrpc_utils::stream::StreamServerConfig;

use jsonrpc_core::{Error, ErrorCode, Value};
use crate::spv_client_cell_message::{get_on_chain_spv_clients};
use crate::spv_client_rpc::SpvClientJsonRpc;
use crate::util::remove_prefix;

#[rpc]
#[async_trait]
trait CkbClientRpc {
    #[rpc(name = "get_ckb_client_message")]
    fn get_client_message(&self, ckb_url: String, code_hash: String, arg: String) -> Result<Vec<SpvClientJsonRpc>, Error>;


    #[rpc(name = "verify_tx")]
    fn verify_tx(&self, proof: String, btc_id: String, ckb_client_data: String) -> Result<Header, Error>;
}

#[derive(Clone)]
pub struct CkbClientRpcImpl {}

#[async_trait]
impl CkbClientRpc for CkbClientRpcImpl {
    fn get_client_message(&self, ckb_url: String, code_hash: String, arg: String) -> Result<Vec<SpvClientJsonRpc>, Error> {
        println!("get_client_message");

        let spv_client_vec = get_on_chain_spv_clients(ckb_url, remove_prefix(arg), remove_prefix(code_hash));
        let clients: Vec<SpvClientJsonRpc> = spv_client_vec.iter().map(|spv_client| SpvClientJsonRpc::from(spv_client.clone())).collect();
        Ok(clients)
    }

    fn verify_tx(&self, proof: String, btc_id: String, ckb_client_data: String) -> Result<Header, Error> {
        let hash = sha256d::Hash::from_str(remove_prefix(btc_id.clone()).as_str()).unwrap();
        let client = remove_prefix(ckb_client_data.clone());
        let proof_bin = hex::decode(remove_prefix(proof.clone())).expect("proof");
        let reader = TransactionProofReader::from_slice(proof_bin.as_slice()).unwrap();
        let client_bin = hex::decode(client.as_bytes()).expect("client");
        let client = SpvClientReader::from_slice(client_bin.as_slice()).unwrap().to_entity();
        let ret = client.verify_transaction(hash.as_ref(), reader, 1);
        match ret {
            Ok(header) => {
                Ok(header)
            }
            Err(err) => {
                let data = err as u8;
                Err(Error {
                    code: ErrorCode::ServerError(1i64),
                    message: "verify failed".to_string(),
                    data: Some(Value::String(format!("err:{data},proof:{proof},btc_id:{btc_id},ckb_client_data:{ckb_client_data}", ))),
                })
            }
        }
    }
}


#[tokio::main]
async fn main() {
    let matches = App::new("JSON-RPC Mock Server")
        .arg(Arg::with_name("bind")
            .short("b")
            .long("bind")
            .default_value("0.0.0.0:3000")
            .help("The address to bind the server to")
        )
        .get_matches();
    let bind_addr = matches.value_of("bind").unwrap();

    let mut rpc = MetaIoHandler::with_compatibility(jsonrpc_core::Compatibility::V2);
    let rpc_impl = CkbClientRpcImpl {};
    add_ckb_client_rpc_methods(&mut rpc, rpc_impl);
    let rpc = Arc::new(rpc);
    let stream_config = StreamServerConfig::default().with_keep_alive(true);
    let app = jsonrpc_router("/", rpc, stream_config);
    axum::Server::bind(&bind_addr.parse().unwrap())
        .serve(app.into_make_service())
        .await
        .unwrap();
}

