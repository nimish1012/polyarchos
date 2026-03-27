//! gRPC server — tonic implementation of `ComponentService`.

pub mod component_service;

// Include tonic-generated code from OUT_DIR.
pub mod proto {
    tonic::include_proto!("polyarchos.core.v1");
}

pub use component_service::GrpcComponentService;
