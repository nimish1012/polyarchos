fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Vendor protoc so no system install is required.
    let protoc = protoc_bin_vendored::protoc_bin_path()?;
    std::env::set_var("PROTOC", protoc);

    tonic_build::configure()
        .build_server(true)
        .build_client(false)
        // Map google.protobuf.Timestamp to prost_types::Timestamp
        .extern_path(".google.protobuf.Timestamp", "::prost_types::Timestamp")
        .compile_protos(
            &[
                "../../proto/polyarchos/core/v1/component.proto",
                "../../proto/polyarchos/core/v1/service.proto",
            ],
            &["../../proto"],
        )?;
    Ok(())
}
