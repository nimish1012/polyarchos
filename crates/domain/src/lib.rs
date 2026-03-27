//! AUTOSAR domain types for the polyarchos platform.
//!
//! This crate defines the core domain model shared across all services.
//! It has no network dependencies and compiles to both native and WASM targets.

#![deny(clippy::all)]
#![deny(clippy::pedantic)]
#![deny(missing_docs)]

/// AUTOSAR software component types.
pub mod swc;

/// Port and interface definitions.
pub mod port;
